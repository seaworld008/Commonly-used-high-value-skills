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

    def test_merge_frontmatter_preserves_local_curation_and_description(self):
        module = load_module()

        local = textwrap.dedent(
            """\
            ---
            name: firebase-security-rules-auditor
            description: "Audit Firebase rules plus repository-specific safety extensions."
            version: "1.2.3"
            ---
            # Old Body

            <!-- LOCAL-QUALITY-SUPPLEMENT:START -->
            ## Old Generated Notes

            This generic block may be rebuilt.
            <!-- LOCAL-QUALITY-SUPPLEMENT:END -->

            <!-- LOCAL-CURATION-SUPPLEMENT:START -->
            ## Repository Safety Extensions

            Preserve this hand-curated Firebase and LinkedIn safety guidance.
            <!-- LOCAL-CURATION-SUPPLEMENT:END -->
            """
        )
        upstream = textwrap.dedent(
            """\
            ---
            name: firebase-security-rules-auditor
            description: "Audit Firebase rules."
            ---
            # New Upstream Body
            """
        )

        merged = module.merge_frontmatter(local, upstream)

        self.assertIn(
            'description: "Audit Firebase rules plus repository-specific safety extensions."',
            merged,
        )
        self.assertIn("# New Upstream Body", merged)
        self.assertNotIn("# Old Body", merged)
        self.assertIn("LOCAL-CURATION-SUPPLEMENT:START", merged)
        self.assertIn("Preserve this hand-curated Firebase and LinkedIn safety guidance.", merged)
        self.assertNotIn("This generic block may be rebuilt.", merged)
        self.assertEqual(1, merged.count("LOCAL-QUALITY-SUPPLEMENT:START"))

    def test_check_upstream_changes_uses_exact_provenance_path(self):
        module = load_module()
        seen_urls = []
        resolved_commit = "a" * 40

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
        original_resolve = module.resolve_github_ref
        module.fetch_url = fake_fetch
        module.resolve_github_ref = lambda _repo, _ref, _token: resolved_commit
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
            module.resolve_github_ref = original_resolve

        self.assertIsNotNone(update)
        self.assertEqual(resolved_commit, update["resolved_commit"])
        self.assertEqual(
            [f"https://raw.githubusercontent.com/owner/repo/{resolved_commit}/nested/source.md"],
            seen_urls,
        )

    def test_check_upstream_changes_reports_commit_only_update_for_mapped_skill(self):
        module = load_module()
        resolved_commit = "9" * 40

        original_fetch = module.fetch_url
        original_resolve = module.resolve_github_ref
        module.fetch_url = lambda _url, _token, **_kwargs: "# Same Body\n"
        module.resolve_github_ref = lambda _repo, _ref, _token: resolved_commit
        try:
            update = module.check_upstream_changes(
                {
                    "name": "same-body",
                    "category": "ai-workflow",
                    "repo": "owner/repo",
                    "ref": "main",
                    "upstream_path": "same-body/SKILL.md",
                    "local_content": "# Same Body\n",
                    "last_synced_commit": "8" * 40,
                    "mapping_path": Path("source.skills.json"),
                },
                token=None,
            )
        finally:
            module.fetch_url = original_fetch
            module.resolve_github_ref = original_resolve

        self.assertIsNotNone(update)
        self.assertEqual("upstream_commit_changed", update["changes"])
        self.assertEqual(resolved_commit, update["resolved_commit"])

    def test_check_upstream_changes_does_not_fetch_a_moving_ref_when_resolution_fails(self):
        module = load_module()
        fetched = []

        original_fetch = module.fetch_url
        original_resolve = module.resolve_github_ref
        module.fetch_url = lambda url, _token, **_kwargs: fetched.append(url)
        module.resolve_github_ref = lambda _repo, _ref, _token: None
        try:
            skill = {
                "name": "demo",
                "category": "ai-workflow",
                "repo": "owner/repo",
                "ref": "main",
                "upstream_path": "demo/SKILL.md",
                "local_content": "# Demo\n",
            }
            update = module.check_upstream_changes(skill, token=None)
        finally:
            module.fetch_url = original_fetch
            module.resolve_github_ref = original_resolve

        self.assertIsNone(update)
        self.assertEqual([], fetched)
        self.assertTrue(skill["_upstream_fetch_failed"])

    def test_expand_auxiliary_updates_includes_unchanged_skills_from_updated_repo(self):
        module = load_module()
        resolved_commit = "7" * 40
        changed = {
            "name": "changed",
            "repo": "owner/repo",
            "source": "github:owner/repo",
            "upstream_path": "changed/SKILL.md",
            "local_path": Path("skills/changed/SKILL.md"),
            "ref": "main",
            "resolved_commit": resolved_commit,
        }
        unchanged = {
            "name": "unchanged",
            "repo": "owner/repo",
            "source": "github:owner/repo",
            "upstream_path": "unchanged/SKILL.md",
            "local_path": Path("skills/unchanged/SKILL.md"),
            "ref": "main",
            "resolved_commit": resolved_commit,
        }
        other_repo = {
            "name": "other",
            "repo": "other/repo",
            "source": "github:other/repo",
            "upstream_path": "other/SKILL.md",
            "local_path": Path("skills/other/SKILL.md"),
            "ref": "main",
            "resolved_commit": "6" * 40,
        }
        updates = [
            {
                "skill": changed,
                "upstream_path": changed["upstream_path"],
                "upstream_content": "# changed\n",
                "changes": "body_changed",
                "resolved_commit": resolved_commit,
            }
        ]

        expanded = module.expand_related_auxiliary_updates(
            updates,
            [changed, unchanged, other_repo],
        )

        self.assertEqual(["changed", "unchanged"], [u["skill"]["name"] for u in expanded])
        self.assertEqual("related_repo_auxiliary_sync", expanded[1]["changes"])
        self.assertEqual(resolved_commit, expanded[1]["resolved_commit"])

    def test_resolve_github_ref_returns_full_commit_sha(self):
        module = load_module()
        resolved_commit = "b" * 40
        seen_urls = []

        def fake_api_get(url, _token):
            seen_urls.append(url)
            return {"sha": resolved_commit}

        original_api_get = module.github_api_get
        module.github_api_get = fake_api_get
        try:
            result = module.resolve_github_ref("owner/repo", "feature/test", token=None)
            cached_result = module.resolve_github_ref("owner/repo", "feature/test", token=None)
        finally:
            module.github_api_get = original_api_get

        self.assertEqual(resolved_commit, result)
        self.assertEqual(resolved_commit, cached_result)
        self.assertEqual(
            ["https://api.github.com/repos/owner/repo/commits/feature%2Ftest"],
            seen_urls,
        )

    def test_update_mapping_after_sync_records_resolved_commit(self):
        module = load_module()
        resolved_commit = "c" * 40

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
                                    "last_synced_commit": "old",
                                }
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            module.update_mapping_after_sync(
                {
                    "resolved_commit": resolved_commit,
                    "skill": {
                        "mapping_path": mapping,
                        "mapping_entry_index": 0,
                    },
                }
            )

            updated = json.loads(mapping.read_text(encoding="utf-8"))

        self.assertEqual(
            resolved_commit,
            updated["skills"][0]["upstream"]["last_synced_commit"],
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

    def test_fetch_url_bytes_rejects_incomplete_binary_payload(self):
        module = load_module()

        class IncompleteResponse:
            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb):
                return False

            def read(self):
                raise module.http.client.IncompleteRead(b"partial", 20)

        original_urlopen = module.urllib.request.urlopen
        original_fallback = module.fetch_github_raw_via_api_bytes
        module.urllib.request.urlopen = lambda _req, timeout: IncompleteResponse()
        module.fetch_github_raw_via_api_bytes = lambda _url, _token: None
        try:
            result = module.fetch_url_bytes(
                "https://raw.githubusercontent.com/owner/repo/abc/asset.png",
                retries=0,
            )
        finally:
            module.urllib.request.urlopen = original_urlopen
            module.fetch_github_raw_via_api_bytes = original_fallback

        self.assertIsNone(result)

    def test_fetch_url_rejects_incomplete_canonical_text(self):
        module = load_module()

        class IncompleteResponse:
            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb):
                return False

            def read(self):
                raise module.http.client.IncompleteRead(b"# truncated", 200)

        original_urlopen = module.urllib.request.urlopen
        original_fallback = module.fetch_github_raw_via_api
        module.urllib.request.urlopen = lambda _req, timeout: IncompleteResponse()
        module.fetch_github_raw_via_api = lambda _url, _token: None
        try:
            result = module.fetch_url(
                "https://raw.githubusercontent.com/owner/repo/abc/SKILL.md",
                retries=0,
            )
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

            def fake_fetch_url_bytes(url, _token):
                if url.endswith("helper.py"):
                    return b"print('helper')\n"
                return b"# Lowercase upstream skill\n"

            original_api_get = module.github_api_get
            original_fetch_url_bytes = module.fetch_url_bytes
            module.github_api_get = fake_api_get
            module.fetch_url_bytes = fake_fetch_url_bytes
            try:
                synced = module.sync_github_auxiliary_files(
                    {
                        "repo": "owner/repo",
                        "ref": "main",
                        "local_path": canonical,
                        "repo_root": Path(tmpdir),
                    },
                    "graphify/skill-codex.md",
                    token=None,
                )
            finally:
                module.github_api_get = original_api_get
                module.fetch_url_bytes = original_fetch_url_bytes

            self.assertEqual(1, synced)
            self.assertEqual("# Canonical\n", canonical.read_text(encoding="utf-8"))
            lowercase_skill = local_dir / "skill.md"
            if lowercase_skill.exists():
                self.assertTrue(lowercase_skill.samefile(canonical))
            self.assertEqual("print('helper')\n", (local_dir / "helper.py").read_text(encoding="utf-8"))

    def test_auxiliary_sync_recurses_prunes_and_preserves_nested_skill_legal_and_binary_files(self):
        module = load_module()
        resolved_commit = "d" * 40

        with tempfile.TemporaryDirectory() as tmpdir:
            local_dir = Path(tmpdir) / "skills" / "developer-engineering" / "graphify"
            local_dir.mkdir(parents=True)
            canonical = local_dir / "SKILL.md"
            canonical.write_text("# Canonical\n", encoding="utf-8")
            (local_dir / "LICENSE").write_text("local license\n", encoding="utf-8")
            (local_dir / "NOTICE.txt").write_text("local notice\n", encoding="utf-8")
            (local_dir / "stale.txt").write_text("stale\n", encoding="utf-8")
            stale_nested = local_dir / "references" / "obsolete.md"
            stale_nested.parent.mkdir()
            stale_nested.write_text("obsolete\n", encoding="utf-8")

            def fake_api_get(url, _token):
                if "/contents/graphify/assets?" in url:
                    return [
                        {
                            "type": "file",
                            "name": "logo.png",
                            "download_url": "https://example.test/logo.png",
                        }
                    ]
                if "/contents/graphify/skills/codex?" in url:
                    return [
                        {
                            "type": "file",
                            "name": "skill.md",
                            "download_url": "https://example.test/nested-skill.md",
                        }
                    ]
                if "/contents/graphify/skills?" in url:
                    return [{"type": "dir", "name": "codex"}]
                if "/contents/graphify?" in url:
                    self.assertIn(f"ref={resolved_commit}", url)
                    return [
                        {
                            "type": "file",
                            "name": "skill.md",
                            "download_url": "https://example.test/root-skill.md",
                        },
                        {
                            "type": "file",
                            "name": "helper.py",
                            "download_url": "https://example.test/helper.py",
                        },
                        {
                            "type": "file",
                            "name": "LICENSE",
                            "download_url": "https://example.test/upstream-license",
                        },
                        {"type": "dir", "name": "assets"},
                        {"type": "dir", "name": "skills"},
                    ]
                self.fail(f"unexpected API URL: {url}")

            payloads = {
                "https://example.test/helper.py": b"print('helper')\n",
                "https://example.test/logo.png": b"\x89PNG\r\n\x1a\n\xff\x00",
                "https://example.test/nested-skill.md": b"# Nested skill\n",
            }

            def fake_fetch_url_bytes(url, _token):
                if url == "https://example.test/root-skill.md":
                    self.fail("root skill.md must not be downloaded over canonical SKILL.md")
                if url == "https://example.test/upstream-license":
                    self.fail("existing local legal files must not be overwritten")
                return payloads[url]

            original_api_get = module.github_api_get
            original_fetch_url_bytes = module.fetch_url_bytes
            module.github_api_get = fake_api_get
            module.fetch_url_bytes = fake_fetch_url_bytes
            try:
                synced = module.sync_github_auxiliary_files(
                    {
                        "repo": "owner/repo",
                        "ref": "main",
                        "local_path": canonical,
                        "repo_root": Path(tmpdir),
                    },
                    "graphify/skill-codex.md",
                    token=None,
                    ref=resolved_commit,
                )
            finally:
                module.github_api_get = original_api_get
                module.fetch_url_bytes = original_fetch_url_bytes

            self.assertEqual(3, synced)
            self.assertEqual("# Canonical\n", canonical.read_text(encoding="utf-8"))
            self.assertEqual("local license\n", (local_dir / "LICENSE").read_text(encoding="utf-8"))
            self.assertEqual("local notice\n", (local_dir / "NOTICE.txt").read_text(encoding="utf-8"))
            self.assertEqual(b"\x89PNG\r\n\x1a\n\xff\x00", (local_dir / "assets" / "logo.png").read_bytes())
            self.assertEqual("# Nested skill\n", (local_dir / "skills" / "codex" / "skill.md").read_text())
            self.assertFalse((local_dir / "stale.txt").exists())
            self.assertFalse((local_dir / "references").exists())

    def test_auxiliary_sync_does_not_prune_when_recursive_listing_is_incomplete(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            local_dir = Path(tmpdir) / "skill"
            local_dir.mkdir()
            canonical = local_dir / "SKILL.md"
            canonical.write_text("# Canonical\n", encoding="utf-8")
            downloaded_before_failure = local_dir / "fresh.md"
            downloaded_before_failure.write_text("old auxiliary\n", encoding="utf-8")
            stale = local_dir / "stale.md"
            stale.write_text("keep until a complete mirror succeeds\n", encoding="utf-8")

            def fake_api_get(url, _token):
                if "/contents/root/nested?" in url:
                    return None
                return [
                    {
                        "type": "file",
                        "name": "fresh.md",
                        "download_url": "https://example.test/fresh.md",
                    },
                    {"type": "dir", "name": "nested"},
                ]

            original_api_get = module.github_api_get
            original_fetch_url_bytes = module.fetch_url_bytes
            module.github_api_get = fake_api_get
            module.fetch_url_bytes = lambda _url, _token: b"new auxiliary\n"
            try:
                synced = module.sync_github_auxiliary_files(
                    {
                        "repo": "owner/repo",
                        "ref": "main",
                        "local_path": canonical,
                        "repo_root": Path(tmpdir),
                    },
                    "root/SKILL.md",
                    token=None,
                    canonical_content="# New Canonical\n",
                )
            finally:
                module.github_api_get = original_api_get
                module.fetch_url_bytes = original_fetch_url_bytes

            self.assertEqual(1, synced)
            self.assertEqual("# Canonical\n", canonical.read_text(encoding="utf-8"))
            self.assertEqual(
                "old auxiliary\n",
                downloaded_before_failure.read_text(encoding="utf-8"),
            )
            self.assertTrue(stale.exists())

    def test_auxiliary_sync_does_not_follow_existing_target_symlink(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            local_dir = root / "skill"
            local_dir.mkdir()
            canonical = local_dir / "SKILL.md"
            canonical.write_text("# Canonical\n", encoding="utf-8")
            outside = root / "outside.txt"
            outside.write_text("outside must remain unchanged\n", encoding="utf-8")
            target = local_dir / "helper.py"
            target.symlink_to(outside)

            def fake_api_get(_url, _token):
                return [
                    {
                        "type": "file",
                        "name": "helper.py",
                        "download_url": "https://example.test/helper.py",
                    }
                ]

            original_api_get = module.github_api_get
            original_fetch_url_bytes = module.fetch_url_bytes
            module.github_api_get = fake_api_get
            module.fetch_url_bytes = lambda _url, _token: b"print('safe')\n"
            try:
                synced = module.sync_github_auxiliary_files(
                    {
                        "repo": "owner/repo",
                        "ref": "main",
                        "local_path": canonical,
                        "repo_root": root,
                    },
                    "root/SKILL.md",
                    token=None,
                )
            finally:
                module.github_api_get = original_api_get
                module.fetch_url_bytes = original_fetch_url_bytes

            self.assertEqual(1, synced)
            self.assertEqual("outside must remain unchanged\n", outside.read_text(encoding="utf-8"))
            self.assertFalse(target.is_symlink())
            self.assertEqual("print('safe')\n", target.read_text(encoding="utf-8"))

    def test_auxiliary_sync_rejects_repo_relative_parent_symlink_escape(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo_root = root / "repo"
            repo_root.mkdir()
            outside = root / "outside"
            outside.mkdir()
            (repo_root / "skills").symlink_to(outside, target_is_directory=True)

            local_dir = repo_root / "skills" / "demo"
            local_dir.mkdir()
            canonical = local_dir / "SKILL.md"
            canonical.write_text("# Outside Canonical\n", encoding="utf-8")
            sentinel = local_dir / "helper.py"
            sentinel.write_text("outside must remain unchanged\n", encoding="utf-8")

            original_api_get = module.github_api_get
            module.github_api_get = lambda _url, _token: self.fail(
                "network fetch must not start through a repo-relative parent symlink"
            )
            try:
                synced = module.sync_github_auxiliary_files(
                    {
                        "repo": "owner/repo",
                        "ref": "main",
                        "local_path": canonical,
                        "repo_root": repo_root,
                    },
                    "demo/SKILL.md",
                    token=None,
                    canonical_content="# New Canonical\n",
                )
            finally:
                module.github_api_get = original_api_get

            self.assertEqual(0, synced)
            self.assertFalse(local_dir.is_symlink())
            self.assertEqual("# Outside Canonical\n", canonical.read_text(encoding="utf-8"))
            self.assertEqual("outside must remain unchanged\n", sentinel.read_text(encoding="utf-8"))

    def test_apply_exits_nonzero_and_keeps_body_when_auxiliary_transaction_fails(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            canonical = Path(tmpdir) / "SKILL.md"
            canonical.write_text("# Old Body\n", encoding="utf-8")
            skill = {
                "name": "demo",
                "category": "ai-workflow",
                "repo": "owner/repo",
                "source": "github:owner/repo",
                "upstream_path": "demo/SKILL.md",
                "local_path": canonical,
                "local_content": "# Old Body\n",
                "ref": "main",
            }
            update = {
                "skill": skill,
                "upstream_path": "demo/SKILL.md",
                "upstream_content": "# New Body\n",
                "changes": "body_changed",
                "resolved_commit": "f" * 40,
            }

            original_argv = module.sys.argv
            original_token = module.resolve_github_token
            original_load = module.load_skills_with_upstream
            original_check = module.check_upstream_changes
            original_expand = module.expand_related_auxiliary_updates
            original_sync = module.sync_github_auxiliary_files
            module.sys.argv = ["sync_upstream.py", "--apply"]
            module.resolve_github_token = lambda: None
            module.load_skills_with_upstream = lambda: [skill]
            module.check_upstream_changes = lambda _skill, _token: update
            module.expand_related_auxiliary_updates = lambda updates, _skills: updates

            def fail_sync(skill_arg, _path, _token, **_kwargs):
                skill_arg["_auxiliary_sync_complete"] = False
                return 0

            module.sync_github_auxiliary_files = fail_sync
            try:
                with self.assertRaises(SystemExit) as exc:
                    module.main()
            finally:
                module.sys.argv = original_argv
                module.resolve_github_token = original_token
                module.load_skills_with_upstream = original_load
                module.check_upstream_changes = original_check
                module.expand_related_auxiliary_updates = original_expand
                module.sync_github_auxiliary_files = original_sync

            self.assertEqual(1, exc.exception.code)
            self.assertEqual("# Old Body\n", canonical.read_text(encoding="utf-8"))

    def test_auxiliary_sync_materializes_direct_common_references_inside_skill(self):
        module = load_module()
        resolved_commit = "e" * 40

        with tempfile.TemporaryDirectory() as tmpdir:
            local_dir = Path(tmpdir) / "skill"
            local_dir.mkdir()
            canonical = local_dir / "SKILL.md"
            canonical.write_text(
                "# Skill\n\nFollow `_common/OPERATIONAL.md`.\n",
                encoding="utf-8",
            )

            def fake_api_get(url, _token):
                if "/contents/demo?" in url:
                    return [
                        {
                            "type": "file",
                            "name": "SKILL.md",
                            "download_url": "https://example.test/root-skill.md",
                        }
                    ]
                if "/contents/_common/OPERATIONAL.md?" in url:
                    return {
                        "type": "file",
                        "encoding": "base64",
                        "content": "IyBPcGVyYXRpb25hbAo=",
                    }
                self.fail(f"unexpected API URL: {url}")

            original_api_get = module.github_api_get
            module.github_api_get = fake_api_get
            try:
                synced = module.sync_github_auxiliary_files(
                    {
                        "repo": "owner/repo",
                        "ref": "main",
                        "local_path": canonical,
                        "repo_root": Path(tmpdir),
                    },
                    "demo/SKILL.md",
                    token=None,
                    ref=resolved_commit,
                )
            finally:
                module.github_api_get = original_api_get

            self.assertEqual(1, synced)
            self.assertEqual(
                "# Operational\n",
                (local_dir / "_common" / "OPERATIONAL.md").read_text(encoding="utf-8"),
            )

    def test_auxiliary_sync_materializes_transitive_common_and_skill_root_reference_closure(self):
        module = load_module()
        resolved_commit = "1" * 40

        with tempfile.TemporaryDirectory() as tmpdir:
            local_dir = Path(tmpdir) / "skill"
            local_dir.mkdir()
            canonical = local_dir / "SKILL.md"
            canonical.write_text(
                "# Skill\n\nFollow `_common/A.md`; ignore `sibling/reference/nope.md`.\n",
                encoding="utf-8",
            )
            fetched = []
            payloads = {
                "_common/A.md": b"See `_common/B.md` and `reference/detail.md`.\n",
                "_common/B.md": b"Cycle back to `_common/A.md`.\n",
                "demo/reference/detail.md": b"# Detail\n",
            }

            def fake_api_get(url, _token):
                if "/contents/demo?" in url:
                    return [
                        {
                            "type": "file",
                            "name": "SKILL.md",
                            "download_url": "https://example.test/root-skill.md",
                        }
                    ]
                self.fail(f"unexpected API URL: {url}")

            def fake_repo_file(_repo, path, _ref, _token):
                fetched.append(path)
                return payloads.get(path)

            original_api_get = module.github_api_get
            original_repo_file = module._fetch_github_repo_file
            module.github_api_get = fake_api_get
            module._fetch_github_repo_file = fake_repo_file
            skill = {
                "repo": "owner/repo",
                "ref": "main",
                "local_path": canonical,
                "repo_root": Path(tmpdir),
            }
            try:
                synced = module.sync_github_auxiliary_files(
                    skill,
                    "demo/SKILL.md",
                    token=None,
                    ref=resolved_commit,
                )
            finally:
                module.github_api_get = original_api_get
                module._fetch_github_repo_file = original_repo_file

            self.assertEqual(3, synced)
            self.assertEqual(
                {"_common/A.md", "_common/B.md", "demo/reference/detail.md"},
                set(fetched),
            )
            self.assertTrue(all(fetched.count(path) == 1 for path in set(fetched)))
            self.assertEqual("Cycle back to `_common/A.md`.\n", (local_dir / "_common" / "B.md").read_text())
            self.assertEqual("# Detail\n", (local_dir / "reference" / "detail.md").read_text())
            self.assertNotIn("sibling/reference/nope.md", fetched)
            self.assertEqual([], skill["_upstream_reference_defects"])

    def test_auxiliary_sync_rejects_dependency_escape_without_fetching_it(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            local_dir = Path(tmpdir) / "skill"
            local_dir.mkdir()
            canonical = local_dir / "SKILL.md"
            canonical.write_text(
                "# Skill\n\nDo not fetch `_common/../outside.md` or `reference/../../escape.md`.\n",
                encoding="utf-8",
            )

            original_api_get = module.github_api_get
            original_repo_file = module._fetch_github_repo_file
            module.github_api_get = lambda _url, _token: []
            module._fetch_github_repo_file = lambda *_args: self.fail(
                "unsafe dependency paths must not be fetched"
            )
            skill = {
                "repo": "owner/repo",
                "ref": "main",
                "local_path": canonical,
                "repo_root": Path(tmpdir),
            }
            try:
                synced = module.sync_github_auxiliary_files(
                    skill,
                    "demo/SKILL.md",
                    token=None,
                    ref="2" * 40,
                )
            finally:
                module.github_api_get = original_api_get
                module._fetch_github_repo_file = original_repo_file

            self.assertEqual(0, synced)
            self.assertEqual(
                ["_common/../outside.md", "reference/../../escape.md"],
                sorted(skill["_unsafe_reference_paths"]),
            )
            self.assertFalse((Path(tmpdir) / "outside.md").exists())

    def test_auxiliary_sync_records_missing_upstream_reference_as_nonfatal_defect(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            local_dir = Path(tmpdir) / "skill"
            local_dir.mkdir()
            canonical = local_dir / "SKILL.md"
            canonical.write_text("# Skill\n\nSee `_common/MISSING.md`.\n", encoding="utf-8")

            original_api_get = module.github_api_get
            original_repo_file = module._fetch_github_repo_file
            module.github_api_get = lambda _url, _token: []
            module._fetch_github_repo_file = lambda *_args: None
            skill = {
                "repo": "owner/repo",
                "ref": "main",
                "local_path": canonical,
                "repo_root": Path(tmpdir),
            }
            try:
                synced = module.sync_github_auxiliary_files(
                    skill,
                    "demo/SKILL.md",
                    token=None,
                    ref="3" * 40,
                )
            finally:
                module.github_api_get = original_api_get
                module._fetch_github_repo_file = original_repo_file

            self.assertEqual(0, synced)
            self.assertTrue(skill["_auxiliary_sync_complete"])
            self.assertEqual(
                ["SKILL.md -> _common/MISSING.md"],
                skill["_upstream_reference_defects"],
            )
            self.assertFalse((local_dir / "_common" / "MISSING.md").exists())

    def test_reference_closure_enforces_fetch_limit(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            staging = Path(tmpdir)
            (staging / "SKILL.md").write_text(
                "See `_common/A.md` and `_common/B.md`.\n",
                encoding="utf-8",
            )
            fetched = []

            def fake_fetch(_repo, path, _ref, _token):
                fetched.append(path)
                return b"# dependency\n"

            original_fetch = module._fetch_github_repo_file
            original_limit = module._MAX_REFERENCE_FETCHES
            module._fetch_github_repo_file = fake_fetch
            module._MAX_REFERENCE_FETCHES = 1
            try:
                added, defects, unsafe, complete = module._materialize_reference_closure(
                    staging,
                    "owner/repo",
                    "demo",
                    "4" * 40,
                    token=None,
                )
            finally:
                module._fetch_github_repo_file = original_fetch
                module._MAX_REFERENCE_FETCHES = original_limit

            self.assertEqual(1, added)
            self.assertEqual(1, len(fetched))
            self.assertFalse(complete)
            self.assertEqual([], unsafe)
            self.assertIn("reference closure fetch limit exceeded (1 files)", defects)


if __name__ == "__main__":
    unittest.main()
