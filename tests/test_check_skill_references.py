import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check_skill_references.py'
spec = importlib.util.spec_from_file_location('skill_reference_check', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_existing_resource_and_anchor(tmp_path):
    skill = tmp_path / 'skills/category/skill'; skill.mkdir(parents=True)
    (skill / 'ref.md').write_text('# Heading\n')
    (skill / 'SKILL.md').write_text('[detail](ref.md#heading)')
    assert module.check(tmp_path) == []


def test_missing_bundled_resource_is_not_silent(tmp_path):
    skill = tmp_path / 'skills/category/skill'; skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('[detail](references/missing.md)')
    assert 'references/missing.md' in module.check(tmp_path)[0]


def test_code_examples_and_external_urls_are_excluded():
    text = '```markdown\n[x](example-file.md)\n```\n[x](https://example.com/a)\n[x](#section)\n[x](mailto:user@example.com)'
    assert list(module.local_links(text)) == []
    assert list(module.local_links('Do not invent links such as `[x](missing.md)`.')) == []


def test_encoded_spaces_and_markdown_title():
    assert list(module.local_links('[x](a%20b.md "title")')) == [(1, 'a b.md')]
    assert list(module.local_links('[x](<a b.md>)')) == [(1, 'a b.md')]


def test_explicit_project_template_variable_is_not_a_bundle_claim():
    assert list(module.local_links('[result]({{reviewed_document_url}})')) == []


def test_resource_cannot_escape_root(tmp_path):
    skill = tmp_path / 'skills/category/skill'; skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('[x](../../../../outside.md)')
    assert len(module.check(tmp_path)) == 1
