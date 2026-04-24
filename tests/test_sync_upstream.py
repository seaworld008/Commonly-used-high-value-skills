import importlib.util
import json
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync_upstream.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sync_upstream", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SyncUpstreamTests(unittest.TestCase):
    def test_loads_exact_upstream_paths_from_source_mappings(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            skill = repo / "skills" / "ai-workflow" / "demo-skill"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: demo-skill
                    description: Local skill.
                    source: "github:owner/repo"
                    ---

                    # Demo
                    """
                ),
                encoding="utf-8",
            )

            mapping = repo / "docs" / "sources" / "owner-repo.skills.json"
            mapping.parent.mkdir(parents=True)
            mapping.write_text(
                json.dumps(
                    {
                        "video": {"url": "https://github.com/owner/repo"},
                        "skills": [
                            {
                                "video_name": "demo-skill",
                                "repo_skill": "skills/ai-workflow/demo-skill/SKILL.md",
                                "upstream": {
                                    "repo": "owner/repo",
                                    "path": "custom/path/SKILL.md",
                                    "ref": "main",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            module.REPO_ROOT = repo
            module.SKILLS_DIR = repo / "skills"
            module.SOURCE_MAPPINGS_DIR = repo / "docs" / "sources"
            module.PROVENANCE_FILE = repo / "docs" / "sources" / "in-house.skills.json"

            loaded = module.load_skills_with_upstream()

            self.assertEqual(1, len(loaded))
            self.assertEqual("owner/repo", loaded[0]["repo"])
            self.assertEqual("custom/path/SKILL.md", loaded[0]["upstream_path"])
            self.assertEqual(skill / "SKILL.md", loaded[0]["local_path"])

    def test_merge_frontmatter_preserves_local_metadata_and_replaces_body(self):
        module = load_module()

        local = textwrap.dedent(
            """\
            ---
            name: demo-skill
            description: "Old description."
            version: "1.2.3"
            source: "github:owner/repo"
            tags: ["demo"]
            upstream_slug: demo-skill
            ---
            # Old Body
            """
        )
        upstream = textwrap.dedent(
            """\
            ---
            name: demo-skill
            description: New upstream description.
            ---
            # New Body
            """
        )

        merged = module.merge_frontmatter(local, upstream)

        self.assertIn('description: "New upstream description."', merged)
        self.assertIn('version: "1.2.4"', merged)
        self.assertIn("upstream_slug: demo-skill", merged)
        self.assertIn("# New Body", merged)
        self.assertNotIn("# Old Body", merged)
        self.assertIn("LOCAL-QUALITY-SUPPLEMENT:START", merged)

    def test_check_upstream_changes_uses_exact_provenance_path(self):
        module = load_module()
        seen_urls = []

        def fake_fetch(url, token):
            seen_urls.append(url)
            return textwrap.dedent(
                """\
                ---
                name: demo-skill
                description: Remote.
                ---
                # Remote Body
                """
            )

        original_fetch = module.fetch_url
        module.fetch_url = fake_fetch
        try:
            update = module.check_upstream_changes(
                {
                    "name": "demo-skill",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "dev",
                    "upstream_path": "nested/source.md",
                    "local_content": "# Local Body\n",
                },
                token=None,
            )
        finally:
            module.fetch_url = original_fetch

        self.assertIsNotNone(update)
        self.assertEqual(
            ["https://raw.githubusercontent.com/owner/repo/dev/nested/source.md"],
            seen_urls,
        )

    def test_quality_supplement_is_not_duplicated(self):
        module = load_module()

        content = textwrap.dedent(
            """\
            ---
            name: compact-skill
            description: Compact.
            ---
            # Compact
            """
        )

        once = module.ensure_quality_floor(content, "compact-skill")
        twice = module.ensure_quality_floor(once, "compact-skill")

        self.assertEqual(once, twice)
        self.assertEqual(1, twice.count("LOCAL-QUALITY-SUPPLEMENT:START"))
        self.assertIn("```text", twice)

    def test_comparable_body_ignores_local_quality_supplement(self):
        module = load_module()

        upstream = "# Compact\n"
        local = module.ensure_quality_floor(
            textwrap.dedent(
                """\
                ---
                name: compact-skill
                description: Compact skill with local supplement.
                ---
                # Compact
                """
            ),
            "compact-skill",
        )

        self.assertEqual(upstream.strip(), module.comparable_body(local))

    def test_parse_frontmatter_collapses_folded_scalars(self):
        module = load_module()

        parsed = module.parse_frontmatter(
            textwrap.dedent(
                """\
                ---
                name: folded
                description: >
                  Audit skills for risky behavior
                  before installing them.
                ---
                # Body
                """
            )
        )

        self.assertEqual(
            "Audit skills for risky behavior before installing them.",
            parsed["description"],
        )


if __name__ == "__main__":
    unittest.main()
