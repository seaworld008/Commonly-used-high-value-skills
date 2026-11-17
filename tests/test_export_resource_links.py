"""Exercise installed flat bundles with isolated, on-disk Markdown resources."""
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

from scripts import check_skill_references as references
from scripts import export_openclaw_skills as exporter
from scripts import validate_repository as validation

REPO = Path(__file__).resolve().parents[1]


def write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def fixture(root):
    write(root, 'skills/design/landing/SKILL.md', '''---
name: landing
description: Build landing pages.
---
[Compete](../../growth/compete/SKILL.md#research "On demand")
[Own](<references/my guide.md#own> 'Own title')
[Encoded](references/my%20guide.md#own)
[Anchor](#local)
[Repository](../../../docs/sources/provenance.json#lock "Source")
[Web](https://example.com/a?q=b#part "Web")
`[inline](../../growth/compete/SKILL.md)`
````markdown
[example](../../growth/compete/SKILL.md)
```
[still example](../../growth/compete/SKILL.md)
````
~~~markdown
[tilde](../../growth/compete/SKILL.md)
~~~
''')
    write(root, 'skills/design/landing/references/my guide.md', '''# Own
[Resource](../../../growth/compete/references/a%20b(1).md#detail "Data")
[Angle](<../../../growth/compete/references/a b(1).md?mode=read#detail> 'Angle title')
[Alias][other]
[other]: <../../../growth/compete/SKILL.md#research> 'Reference title'
''')
    write(root, 'skills/growth/compete/SKILL.md', '# Research\n[Data](references/a%20b(1).md#detail)\n')
    write(root, 'skills/growth/compete/references/a b(1).md', '# Detail\n[Cycle](../SKILL.md)\n')
    write(root, 'docs/sources/provenance.json', '{}')
    return root / 'skills', root / 'openclaw-skills'


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_flat_export_links_preserve_syntax_source_and_idempotence(tmp_path):
    source, output = fixture(tmp_path)
    before = snapshot(source)
    assert references.check(tmp_path) == []
    exporter.export_openclaw_skills(source, output)
    text = (output / 'landing/SKILL.md').read_text()
    assert '[Compete](../compete/SKILL.md#research "On demand")' in text
    assert '[Own](<references/my guide.md#own> \'Own title\')' in text
    assert '[Encoded](references/my%20guide.md#own)' in text
    assert '[Anchor](#local)' in text
    assert '[Web](https://example.com/a?q=b#part "Web")' in text
    assert '`[inline](../../growth/compete/SKILL.md)`' in text
    original = (source / 'design/landing/SKILL.md').read_text()
    assert text[text.index('````markdown'):] == original[original.index('````markdown'):]
    assert 'https://github.com/seaworld008/Commonly-used-high-value-skills/blob/main/docs/sources/provenance.json#lock "Source"' in text
    resource = (output / 'landing/references/my guide.md').read_text()
    assert '(../../compete/references/a%20b(1).md#detail "Data")' in resource
    assert "(<../../compete/references/a%20b(1).md?mode=read#detail> 'Angle title')" in resource
    assert "[other]: <../../compete/SKILL.md#research> 'Reference title'" in resource
    assert snapshot(source) == before
    assert references.check(tmp_path, include_exports=True) == []
    first = snapshot(output)
    exporter.export_openclaw_skills(source, output)
    assert snapshot(output) == first


def test_exported_resource_closure_and_package_boundary(tmp_path):
    source, output = fixture(tmp_path)
    exporter.export_openclaw_skills(source, output)
    write(tmp_path, 'outside.md', '# Outside')
    write(tmp_path, 'openclaw-skills/compete/references/a b(1).md', '[escape](../../../outside.md)\n[missing](missing.md)')
    failures = references.check(tmp_path, include_exports=True)
    assert any('outside.md' in message for message in failures)
    assert any('missing.md' in message for message in failures)
    assert references.check(tmp_path) == []
    result = subprocess.run([sys.executable, str(REPO / 'scripts/check_skill_references.py'),
                             '--root', str(tmp_path), '--include-exports'], capture_output=True, text=True)
    assert result.returncode == 1
    assert 'missing.md' in result.stdout


def test_explicit_exports_flag_requires_export_tree_and_entries(tmp_path):
    fixture(tmp_path)
    assert references.check(tmp_path) == []
    failures = references.check(tmp_path, include_exports=True)
    assert any('openclaw-skills' in message for message in failures)
    write(tmp_path, 'openclaw-skills/landing/SKILL.md', '# Landing')
    assert any('compete/SKILL.md' in message for message in references.check(tmp_path, include_exports=True))


def test_nested_installed_entrypoints_require_their_own_resources(tmp_path):
    write(tmp_path, 'skills/category/parent/SKILL.md', '# Parent\nChild is selected by name.\n')
    write(tmp_path, 'skills/category/parent/child/SKILL.md', '[Constraint](references/spec.yaml)\n')
    write(tmp_path, 'skills/category/parent/child/references/spec.yaml', 'version: 1\n')
    exporter.export_openclaw_skills(tmp_path / 'skills', tmp_path / 'openclaw-skills')
    assert references.check(tmp_path, include_exports=True) == []
    (tmp_path / 'openclaw-skills/parent/child/references/spec.yaml').unlink()
    assert any('spec.yaml' in message for message in references.check(tmp_path, include_exports=True))
    (tmp_path / 'openclaw-skills/parent/child/SKILL.md').unlink()
    assert any('missing exported entrypoint' in message and 'parent/child/SKILL.md' in message
               for message in references.check(tmp_path, include_exports=True))


def test_canonical_resources_are_checked_recursively_with_cycles(tmp_path):
    fixture(tmp_path)
    write(tmp_path, 'skills/growth/compete/references/a b(1).md', '[broken](absent.md)')
    assert any('absent.md' in message for message in references.check(tmp_path))


def test_ci_pipeline_executes_export_reference_gate(tmp_path):
    run = Mock(return_value=Mock(returncode=0))
    assert validation.run_pipeline(tmp_path, run=run) == 0
    commands = [call.args[0] for call in run.call_args_list]
    assert any('scripts/check_skill_references.py' in command and '--include-exports' in command for command in commands)


def test_reported_cross_category_regression_rejects_stale_export(tmp_path):
    source_path = REPO / 'skills/product-design/landing-page-generator/SKILL.md'
    target = '../../growth-operations-xiaohongshu/compete/SKILL.md'
    assert any(destination == target for _, _, _, destination in references.markdown_destinations(source_path.read_text()))
    write(tmp_path, 'skills/product-design/landing-page-generator/SKILL.md', f'[Compete]({target})\n')
    write(tmp_path, 'skills/growth-operations-xiaohongshu/compete/SKILL.md', '# Compete\n')
    write(tmp_path, 'openclaw-skills/landing-page-generator/SKILL.md', f'[Compete]({target})\n')
    write(tmp_path, 'openclaw-skills/compete/SKILL.md', '# Compete\n')
    assert references.check(tmp_path) == []
    assert any(target in failure for failure in references.check(tmp_path, include_exports=True))
    exporter.export_openclaw_skills(tmp_path / 'skills', tmp_path / 'openclaw-skills')
    assert references.check(tmp_path, include_exports=True) == []
    assert '[Compete](../compete/SKILL.md)' in (tmp_path / 'openclaw-skills/landing-page-generator/SKILL.md').read_text()


def test_missing_repository_files_are_not_disguised_as_remote_urls(tmp_path):
    write(tmp_path, 'skills/category/demo/SKILL.md', '[Missing](../../../docs/absent.md)\n')
    exporter.export_openclaw_skills(tmp_path / 'skills', tmp_path / 'openclaw-skills')
    assert (tmp_path / 'openclaw-skills/demo/SKILL.md').read_text().endswith('[Missing](../../../docs/absent.md)\n')
    assert any('docs/absent.md' in failure for failure in references.check(tmp_path, include_exports=True))


def test_direct_cli_export_and_reference_check_from_other_directory(tmp_path):
    source, output = fixture(tmp_path)
    before = snapshot(source)
    exported = subprocess.run([sys.executable, str(REPO / 'scripts/export_openclaw_skills.py'),
                               '--source-root', str(source), '--output-root', str(output)],
                              cwd=tmp_path, capture_output=True, text=True)
    assert exported.returncode == 0, exported.stderr
    checked = subprocess.run([sys.executable, str(REPO / 'scripts/check_skill_references.py'),
                              '--root', str(tmp_path), '--include-exports'],
                             cwd=tmp_path, capture_output=True, text=True)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert '0 missing resource(s)' in checked.stdout
    assert snapshot(source) == before


def test_unmodified_owned_markdown_resources_keep_original_bytes(tmp_path):
    write(tmp_path, 'skills/category/demo/SKILL.md', '[Guide](references/guide.md)\n')
    resource = write(tmp_path, 'skills/category/demo/references/guide.md', '')
    payload = b'# Guide\r\n\r\n```md\r\n[x](not-a-resource.md)\r\n```\r\n'
    resource.write_bytes(payload)
    exporter.export_openclaw_skills(tmp_path / 'skills', tmp_path / 'openclaw-skills')
    assert (tmp_path / 'openclaw-skills/demo/references/guide.md').read_bytes() == payload
    assert references.check(tmp_path, include_exports=True) == []
