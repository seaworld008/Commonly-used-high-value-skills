import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "auto_curate_skills.py"


def load_module():
    spec = importlib.util.spec_from_file_location("auto_curate_skills", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AutoCurateSkillsTests(unittest.TestCase):
    def test_ranked_candidates_prefer_trusted_sources_and_actionable_names(self):
        module = load_module()

        report = {
            "discoveries": [
                {
                    "name": "infra-automation",
                    "source": "skills.sh (vercel-labs/agent-skills)",
                    "url": "https://skills.sh/example/infra-automation",
                    "repo_stars": 50,
                    "description": "Production-ready runbooks and CI guidance",
                },
                {
                    "name": "random-helper",
                    "source": "Unknown",
                    "url": "https://example.com/random-helper",
                    "repo_stars": 5000,
                    "description": "misc",
                },
                {
                    "name": "test-driven-development",
                    "source": "skills.sh (obra/superpowers)",
                    "url": "https://skills.sh/example/test-driven-development",
                    "repo_stars": 100000,
                    "description": "already in repo",
                },
            ]
        }

        ranked, skipped = module.rank_discoveries(
            report,
            existing_names={"test-driven-development"},
            limit=10,
        )

        self.assertEqual("infra-automation", ranked[0]["name"])
        self.assertEqual("random-helper", ranked[1]["name"])
        self.assertNotIn("test-driven-development", [item["name"] for item in ranked])
        self.assertEqual("already_indexed", skipped[0]["reason"])
        self.assertGreater(ranked[0]["curation_score"], ranked[1]["curation_score"])

    def test_build_execution_plan_syncs_before_discovery_and_pipeline(self):
        module = load_module()

        plan = module.build_execution_plan(
            python_cmd=["python"],
            discovery_output="docs/sources/reports/discovery.json",
            candidate_output="docs/sources/reports/curation-candidates.json",
            sync_mode="apply",
            top=5,
            min_score=20,
            policy_path="docs/sources/curation-policy.json",
        )

        rendered = [" ".join(step["cmd"]) for step in plan]
        self.assertEqual("gh auth status", rendered[0])
        self.assertIn("python scripts/sync_upstream.py --apply", rendered[1])
        self.assertIn("python scripts/discover_new_skills.py --output docs/sources/reports/discovery.json", rendered[2])
        self.assertTrue(
            any("python scripts/enrich_frontmatter.py" in command for command in rendered),
            rendered,
        )
        self.assertTrue(
            any("python scripts/check_readme_sync.py" in command for command in rendered),
            rendered,
        )
        self.assertIn("python -m unittest discover tests -v", rendered[-1])

    def test_resolve_github_token_falls_back_to_gh_cli(self):
        module = load_module()

        with mock.patch.dict(module.os.environ, {}, clear=True):
            completed = mock.Mock(returncode=0, stdout="gho_example_token\n")
            with mock.patch.object(module.subprocess, "run", return_value=completed) as run:
                token = module.resolve_github_token()

        self.assertEqual("gho_example_token", token)
        run.assert_called_once()

    def test_curate_dry_run_writes_candidate_report(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            discovery_path = repo / "docs" / "sources" / "reports" / "discovery.json"
            discovery_path.parent.mkdir(parents=True, exist_ok=True)
            discovery_path.write_text(
                json.dumps(
                    {
                        "discoveries": [
                            {
                                "name": "platform-best-practices",
                                "source": "skills.sh (vercel-labs/agent-skills)",
                                "url": "https://skills.sh/example/platform-best-practices",
                                "repo_stars": 1200,
                                "description": "Operational patterns with examples",
                            },
                            {
                                "name": "blocked-skill",
                                "source": "skills.sh (bad/repo)",
                                "url": "https://skills.sh/example/blocked-skill",
                                "repo_stars": 9999,
                                "description": "Should be filtered",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            policy_path = repo / "docs" / "sources" / "curation-policy.json"
            policy_path.parent.mkdir(parents=True, exist_ok=True)
            policy_path.write_text(
                json.dumps(
                    {
                        "deny_repos": ["bad/repo"],
                        "prefer_repos": {"vercel-labs/agent-skills": 20},
                        "min_repo_stars": 100,
                    }
                ),
                encoding="utf-8",
            )

            report = module.curate_candidates(
                repo_root=repo,
                discovery_output=discovery_path,
                candidate_output=repo / "docs" / "sources" / "reports" / "curation-candidates.json",
                top=10,
                min_score=1,
                policy=module.load_curation_policy(policy_path),
            )

            self.assertEqual(1, report["selected_count"])
            self.assertEqual("platform-best-practices", report["selected"][0]["name"])
            self.assertEqual(1, report["skipped_count"])
            self.assertEqual("blocked-skill", report["skipped"][0]["name"])
            self.assertEqual("deny_repo", report["skipped"][0]["reason"])

    def test_build_branch_name_uses_codex_prefix(self):
        module = load_module()
        branch = module.build_branch_name("skills-curation")
        self.assertTrue(branch.startswith("codex/"))
        self.assertIn("skills-curation", branch)

    def test_rank_discoveries_applies_policy_preferences_and_filters(self):
        module = load_module()

        policy = {
            "allow_repos": [],
            "deny_repos": ["bad/repo"],
            "prefer_repos": {"trusted/repo": 30},
            "min_repo_stars": 50,
            "min_score_override": None,
        }
        ranked, skipped = module.rank_discoveries(
            {
                "discoveries": [
                    {
                        "name": "preferred-skill",
                        "source": "skills.sh (trusted/repo)",
                        "url": "https://skills.sh/trusted/repo/preferred-skill",
                        "repo_stars": 100,
                        "description": "Useful automation patterns",
                    },
                    {
                        "name": "denied-skill",
                        "source": "skills.sh (bad/repo)",
                        "url": "https://skills.sh/bad/repo/denied-skill",
                        "repo_stars": 1000,
                        "description": "Should not pass policy",
                    },
                    {
                        "name": "tiny-signal",
                        "source": "skills.sh (small/repo)",
                        "url": "https://skills.sh/small/repo/tiny-signal",
                        "repo_stars": 2,
                        "description": "Too small",
                    },
                ]
            },
            existing_names=set(),
            limit=10,
            min_score=1,
            policy=policy,
        )

        self.assertEqual(["preferred-skill"], [item["name"] for item in ranked])
        self.assertEqual({"denied-skill", "tiny-signal"}, {item["name"] for item in skipped})
        reasons = {item["name"]: item["reason"] for item in skipped}
        self.assertEqual("deny_repo", reasons["denied-skill"])
        self.assertEqual("below_min_repo_stars", reasons["tiny-signal"])

    def test_write_pr_summary_includes_candidates_and_results(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "curation-pr.md"
            module.write_pr_summary(
                output,
                candidate_report={
                    "selected_count": 2,
                    "selected": [
                        {"name": "alpha-skill", "curation_score": 42, "recommended_category": "developer-engineering"},
                        {"name": "beta-skill", "curation_score": 35, "recommended_category": "devops-sre"},
                    ],
                },
                ingest_result={
                    "ingested": [{"name": "alpha-skill", "path": "skills/developer-engineering/alpha-skill"}],
                    "skipped": [{"name": "beta-skill", "reason": "upstream_markdown_not_found"}],
                    "unlicensed_rewrites": [
                        {
                            "name": "gamma-skill",
                            "path": "skills/developer-engineering/gamma-skill",
                            "source_repo": "owner/repo",
                            "curation_score": 55,
                        }
                    ],
                },
                sync_mode="apply",
                branch_name="codex/skills-curation-20260327-120000",
                base_branch="main",
            )

            body = output.read_text(encoding="utf-8")
            self.assertIn("Skills curation automation", body)
            self.assertIn("alpha-skill", body)
            self.assertIn("upstream_markdown_not_found", body)
            self.assertIn("Auto-Rewritten Unlicensed Candidates", body)
            self.assertIn("gamma-skill", body)
            self.assertIn("codex/skills-curation-20260327-120000", body)

    def test_assert_clean_worktree_raises_when_repo_is_dirty(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / ".git").mkdir()
            dirty = repo / "dirty.txt"
            dirty.write_text("changed", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "dirty worktree"):
                module.assert_clean_worktree(repo, status_output=" M dirty.txt")

    def test_resolve_candidate_license_prefers_frontmatter_license(self):
        module = load_module()

        markdown = "---\nname: licensed\nlicense: MIT\n---\n# Licensed\n"

        self.assertEqual("MIT", module.resolve_candidate_license(markdown, "missing/repo"))

    def test_resolve_candidate_license_uses_github_repo_license(self):
        module = load_module()

        markdown = "---\nname: licensed\n---\n# Licensed\n"
        with mock.patch.object(
            module,
            "github_api_get",
            return_value={"license": {"key": "apache-2.0"}},
        ):
            self.assertEqual("Apache-2.0", module.resolve_candidate_license(markdown, "owner/repo"))

    def test_resolve_candidate_license_rejects_missing_license(self):
        module = load_module()

        markdown = "---\nname: unlicensed\n---\n# Unlicensed\n"
        with mock.patch.object(module, "github_api_get", return_value={"license": None}):
            self.assertIsNone(module.resolve_candidate_license(markdown, "owner/repo"))

    def test_ingest_candidates_skips_low_signal_unlicensed_external_candidates(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "scripts").mkdir()
            (repo / "skills").mkdir()
            report = {
                "selected": [
                    {
                        "name": "unlicensed-skill",
                        "slug": "unlicensed-skill",
                        "recommended_category": "developer-engineering",
                        "url": "https://skills.sh/owner/repo/unlicensed-skill",
                        "source_repo": "owner/repo",
                        "curation_score": 10,
                    }
                ]
            }
            markdown = "---\nname: unlicensed-skill\n---\n" + "\n".join(f"line {i}" for i in range(60))

            with mock.patch.object(module, "fetch_candidate_markdown", return_value=(markdown, "owner/repo")), \
                mock.patch.object(module, "resolve_candidate_license", return_value=None):
                result = module.ingest_candidates(
                    repo_root=repo,
                    report=report,
                    limit=1,
                    python_cmd=["python"],
                )

            self.assertEqual([], result["ingested"])
            self.assertEqual("missing_or_unapproved_license", result["skipped"][0]["reason"])
            self.assertEqual([], result["unlicensed_rewrites"])
            self.assertFalse((repo / "skills" / "developer-engineering" / "unlicensed-skill").exists())
            log_path = repo / "docs" / "sources" / "reports" / "license-rewrite-log.json"
            self.assertTrue(log_path.exists())
            log = json.loads(log_path.read_text(encoding="utf-8"))
            self.assertEqual(0, log["rewrite_count"])

    def test_ingest_candidates_auto_rewrites_high_signal_unlicensed_candidates(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "scripts").mkdir()
            (repo / "skills").mkdir()
            report = {
                "selected": [
                    {
                        "name": "unlicensed-best-practices",
                        "slug": "unlicensed-best-practices",
                        "description": "Production-grade workflow guidance for agent automation.",
                        "recommended_category": "developer-engineering",
                        "url": "https://skills.sh/owner/repo/unlicensed-best-practices",
                        "source_repo": "owner/repo",
                        "curation_score": 70,
                        "score_reasons": ["trusted_registry:github", "keyword:best-practices"],
                    }
                ]
            }
            upstream_phrase = "DO NOT COPY THIS UNIQUE UPSTREAM SENTENCE"
            markdown = "---\nname: unlicensed-best-practices\n---\n" + "\n".join(
                [upstream_phrase] + [f"line {i}" for i in range(90)]
            )

            with mock.patch.object(module, "fetch_candidate_markdown", return_value=(markdown, "owner/repo")), \
                mock.patch.object(module, "resolve_candidate_license", return_value=None), \
                mock.patch.object(module, "run_command") as run_command:
                result = module.ingest_candidates(
                    repo_root=repo,
                    report=report,
                    limit=1,
                    python_cmd=["python"],
                    policy={"unlicensed_auto_rewrite_min_score": 55, "unlicensed_auto_rewrite_min_lines": 80},
                )

            skill_path = repo / "skills" / "developer-engineering" / "unlicensed-best-practices" / "SKILL.md"
            content = skill_path.read_text(encoding="utf-8")
            self.assertEqual([], result["skipped"])
            self.assertEqual("unlicensed-best-practices", result["unlicensed_rewrites"][0]["name"])
            self.assertIn('source: "in-house"', content)
            self.assertIn("license: MIT", content)
            self.assertNotIn(upstream_phrase, content)
            run_command.assert_called()

    def test_write_license_rewrite_log_records_candidates(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            module.write_license_rewrite_log(
                repo,
                [
                    {
                        "name": "rewrite-me",
                        "source_repo": "owner/repo",
                        "reason": "auto_rewritten_from_unlicensed_high_quality_candidate",
                    }
                ],
            )

            log = json.loads(
                (repo / "docs" / "sources" / "reports" / "license-rewrite-log.json").read_text(encoding="utf-8")
            )
            self.assertEqual(1, log["rewrite_count"])
            self.assertEqual("rewrite-me", log["rewrites"][0]["name"])


if __name__ == "__main__":
    unittest.main()
