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
                                "sync_mode": "monitor",
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
            self.assertEqual("monitor", loaded[0]["sync_mode"])
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

    def test_monitor_review_guidance_includes_compare_and_curation_checklist(self):
        module = load_module()

        update = {
            "upstream_path": "README.md",
            "skill": {
                "name": "nlpm-audit",
                "repo": "xiaolai/nlpm",
                "ref": "main",
                "sync_mode": "monitor",
                "last_synced_commit": "abc123",
                "local_path": Path("skills/ai-workflow/nlpm-audit/SKILL.md"),
            },
        }

        guidance = "\n".join(module.monitor_review_guidance(update))

        self.assertIn("nlpm-audit requires manual monitor review", guidance)
        self.assertIn("https://github.com/xiaolai/nlpm/blob/main/README.md", guidance)
        self.assertIn("https://github.com/xiaolai/nlpm/compare/abc123...main", guidance)
        self.assertIn("durable method, install, scoring, CI, security, or compatibility", guidance)
        self.assertIn("update the curated SKILL.md, bump version/updated_at", guidance)
        self.assertIn("record why in provenance verification_attempts or the automation memory", guidance)

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

    def test_comparable_body_ignores_local_curation_supplement(self):
        module = load_module()

        local = textwrap.dedent(
            """\
            ---
            name: curated
            description: Curated.
            ---
            # Compact

            <!-- LOCAL-CURATION-SUPPLEMENT:START -->
            ## Local Review Checklist

            - Keep this repository-specific checklist without treating it as upstream drift.
            <!-- LOCAL-CURATION-SUPPLEMENT:END -->
            """
        )

        self.assertEqual("# Compact", module.comparable_body(local))

    def test_comparable_body_ignores_trailing_whitespace(self):
        module = load_module()

        self.assertEqual(
            "# Body\n\nA line",
            module.comparable_body("# Body   \n\nA line  \n"),
        )

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

    def test_fetch_url_treats_ssl_errors_as_recoverable_fetch_failures(self):
        module = load_module()

        def fake_urlopen(_req, timeout):
            raise module.ssl.SSLError("handshake timed out")

        original_urlopen = module.urllib.request.urlopen
        original_fallback = module.fetch_github_raw_via_api
        module.urllib.request.urlopen = fake_urlopen
        module.fetch_github_raw_via_api = lambda _url, _token: None
        try:
            result = module.fetch_url("https://raw.githubusercontent.com/owner/repo/main/SKILL.md")
        finally:
            module.urllib.request.urlopen = original_urlopen
            module.fetch_github_raw_via_api = original_fallback

        self.assertIsNone(result)

    def test_auxiliary_sync_skips_case_variant_skill_markdown(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            local_dir = Path(tmpdir) / "skills" / "developer-engineering" / "graphify"
            local_dir.mkdir(parents=True)
            canonical = local_dir / "SKILL.md"
            canonical.write_text("# Canonical\n", encoding="utf-8")

            def fake_api_get(_url, _token):
                return [
                    {
                        "type": "file",
                        "name": "skill.md",
                        "download_url": "https://example.test/skill.md",
                    },
                    {
                        "type": "file",
                        "name": "helper.py",
                        "download_url": "https://example.test/helper.py",
                    },
                ]

            def fake_fetch_url(url, _token):
                if url.endswith("helper.py"):
                    return "print('helper')\n"
                return "# Lowercase upstream skill\n"

            original_api_get = module.github_api_get
            original_fetch_url = module.fetch_url
            module.github_api_get = fake_api_get
            module.fetch_url = fake_fetch_url
            try:
                synced = module.sync_github_auxiliary_files(
                    {
                        "repo": "owner/repo",
                        "ref": "main",
                        "local_path": canonical,
                    },
                    "graphify/skill-codex.md",
                    token=None,
                )
            finally:
                module.github_api_get = original_api_get
                module.fetch_url = original_fetch_url

            self.assertEqual(1, synced)
            self.assertEqual("# Canonical\n", canonical.read_text(encoding="utf-8"))
            lowercase_skill = local_dir / "skill.md"
            if lowercase_skill.exists():
                self.assertTrue(lowercase_skill.samefile(canonical))
            self.assertEqual("print('helper')\n", (local_dir / "helper.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
