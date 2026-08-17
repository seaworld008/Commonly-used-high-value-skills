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

            <!-- LOCAL-CURATION-SUPPLEMENT:START -->
            ## Repository Contract

            Preserve this reviewed local rule.
            <!-- LOCAL-CURATION-SUPPLEMENT:END -->
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
        self.assertIn("Preserve this reviewed local rule.", merged)

    def test_repository_adaptation_rewrites_addyosmani_shared_references(self):
        module = load_module()

        adapted = module.apply_repository_adaptations(
            "See `../../references/definition-of-done.md`.\n",
            {"repo": "addyosmani/agent-skills"},
        )
        untouched = module.apply_repository_adaptations(
            "See `../../references/definition-of-done.md`.\n",
            {"repo": "owner/repo"},
        )

        self.assertEqual(
            "See `references/definition-of-done.md`.\n",
            adapted,
        )
        self.assertEqual(
            "See `../../references/definition-of-done.md`.\n",
            untouched,
        )

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

    def test_check_upstream_changes_reports_successful_no_change(self):
        module = load_module()
        local = "---\nname: demo\n---\n# Same Body\n"
        original_fetch = module.fetch_url
        module.fetch_url = lambda _url, _token: local
        try:
            result = module.check_upstream_changes(
                {
                    "name": "demo",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "main",
                    "upstream_path": "SKILL.md",
                    "local_content": local,
                },
                token=None,
            )
        finally:
            module.fetch_url = original_fetch

        self.assertIsNotNone(result)
        self.assertEqual("none", result["changes"])

    def test_check_upstream_changes_compares_repository_adapted_body(self):
        module = load_module()
        local = "# Demo\n\nSee `references/definition-of-done.md`.\n"
        upstream = "# Demo\n\nSee `../../references/definition-of-done.md`.\n"
        original_fetch = module.fetch_url
        module.fetch_url = lambda _url, _token, **_kwargs: upstream
        try:
            result = module.check_upstream_changes(
                {
                    "name": "demo",
                    "category": "ai-workflow",
                    "repo": "addyosmani/agent-skills",
                    "ref": "main",
                    "upstream_path": "skills/demo/SKILL.md",
                    "local_content": local,
                },
                token=None,
            )
        finally:
            module.fetch_url = original_fetch

        self.assertIsNotNone(result)
        self.assertEqual("none", result["changes"])

    def test_monitor_checkpoint_skips_false_positive_for_curated_body(self):
        module = load_module()
        original_commit_sha = module.github_commit_sha
        original_fetch = module.fetch_url
        module.github_commit_sha = lambda _repo, _ref, _token: "reviewed-sha"
        module.fetch_url = lambda *_args, **_kwargs: self.fail(
            "matching monitor checkpoint should not fetch or compare the curated body"
        )
        try:
            result = module.check_upstream_changes(
                {
                    "name": "curated-skill",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "main",
                    "upstream_path": "README.md",
                    "sync_mode": "monitor",
                    "last_synced_commit": "reviewed-sha",
                    "local_content": "# Original in-house rewrite\n",
                },
                token=None,
            )
        finally:
            module.github_commit_sha = original_commit_sha
            module.fetch_url = original_fetch

        self.assertIsNotNone(result)
        self.assertEqual("none", result["changes"])

    def test_monitor_checkpoint_reports_upstream_rollback_without_body_diff(self):
        module = load_module()
        original_commit_sha = module.github_commit_sha
        original_compare = module.github_compare_relation
        original_fetch = module.fetch_url
        module.github_commit_sha = lambda _repo, _ref, _token: "older-head"
        module.github_compare_relation = lambda *_args, **_kwargs: {
            "status": "behind",
            "ahead_by": 0,
            "behind_by": 42,
        }
        module.fetch_url = lambda *_args, **_kwargs: self.fail(
            "an upstream rollback should not be compared as a body update"
        )
        try:
            result = module.check_upstream_changes(
                {
                    "name": "curated-skill",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "main",
                    "upstream_path": "README.md",
                    "sync_mode": "monitor",
                    "last_synced_commit": "reviewed-sha",
                    "local_content": "# Original in-house rewrite\n",
                },
                token=None,
            )
        finally:
            module.github_commit_sha = original_commit_sha
            module.github_compare_relation = original_compare
            module.fetch_url = original_fetch

        self.assertIsNotNone(result)
        self.assertEqual("upstream_rollback", result["changes"])
        self.assertEqual("older-head", result["current_commit"])
        self.assertEqual(42, result["behind_by"])

    def test_github_compare_relation_returns_commit_relationship(self):
        module = load_module()
        original_api_get = module.github_api_get
        module.github_api_get = lambda _url, _token: {
            "status": "behind",
            "ahead_by": 0,
            "behind_by": 7,
        }
        try:
            relation = module.github_compare_relation(
                "owner/repo",
                "reviewed-sha",
                "older-head",
                token=None,
            )
        finally:
            module.github_api_get = original_api_get

        self.assertEqual(
            {"status": "behind", "ahead_by": 0, "behind_by": 7},
            relation,
        )

    def test_update_mapping_after_check_only_syncs_equal_body(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            mapping = Path(tmpdir) / "source.skills.json"
            mapping.write_text(
                json.dumps(
                    {
                        "video": {"checked_at": "2026-01-01"},
                        "skills": [
                            {
                                "upstream": {
                                    "last_checked_at": "2026-01-01",
                                    "last_synced_at": "2026-01-01",
                                }
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            base_skill = {"mapping_path": mapping, "mapping_entry_index": 0}

            module.update_mapping_after_check({"skill": base_skill, "changes": "body_changed"})
            changed = json.loads(mapping.read_text(encoding="utf-8"))
            self.assertEqual("2026-01-01", changed["skills"][0]["upstream"]["last_synced_at"])
            self.assertEqual(module.date.today().isoformat(), changed["skills"][0]["upstream"]["last_checked_at"])

            module.update_mapping_after_check({"skill": base_skill, "changes": "none"})
            equal = json.loads(mapping.read_text(encoding="utf-8"))
            self.assertEqual(module.date.today().isoformat(), equal["skills"][0]["upstream"]["last_synced_at"])

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

    def test_monitor_rollback_guidance_preserves_reviewed_checkpoint(self):
        module = load_module()
        result = {
            "changes": "upstream_rollback",
            "current_commit": "older-head",
            "behind_by": 42,
            "skill": {
                "name": "nlpm-audit",
                "repo": "xiaolai/nlpm",
                "ref": "main",
                "last_synced_commit": "reviewed-sha",
            },
        }

        guidance = "\n".join(module.monitor_rollback_guidance(result))

        self.assertIn("upstream ref moved backward by 42 commits", guidance)
        self.assertIn("Current head: older-head", guidance)
        self.assertIn("Reviewed checkpoint: reviewed-sha", guidance)
        self.assertIn("Do not move the checkpoint backward", guidance)

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
