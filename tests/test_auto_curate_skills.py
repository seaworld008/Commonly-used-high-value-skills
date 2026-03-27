import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


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

        ranked = module.rank_discoveries(
            report,
            existing_names={"test-driven-development"},
            limit=10,
        )

        self.assertEqual("infra-automation", ranked[0]["name"])
        self.assertEqual("random-helper", ranked[1]["name"])
        self.assertNotIn("test-driven-development", [item["name"] for item in ranked])
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
        )

        rendered = [" ".join(step["cmd"]) for step in plan]
        self.assertIn("python scripts/sync_upstream.py --apply", rendered[0])
        self.assertIn("python scripts/discover_new_skills.py --output docs/sources/reports/discovery.json", rendered[1])
        self.assertTrue(
            any("python scripts/enrich_frontmatter.py" in command for command in rendered),
            rendered,
        )
        self.assertIn("python -m unittest discover tests -v", rendered[-1])

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
                            }
                        ]
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
            )

            self.assertEqual(1, report["selected_count"])
            self.assertEqual("platform-best-practices", report["selected"][0]["name"])

    def test_build_branch_name_uses_codex_prefix(self):
        module = load_module()
        branch = module.build_branch_name("skills-curation")
        self.assertTrue(branch.startswith("codex/"))
        self.assertIn("skills-curation", branch)

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
                },
                sync_mode="apply",
                branch_name="codex/skills-curation-20260327-120000",
                base_branch="main",
            )

            body = output.read_text(encoding="utf-8")
            self.assertIn("Skills curation automation", body)
            self.assertIn("alpha-skill", body)
            self.assertIn("upstream_markdown_not_found", body)
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


if __name__ == "__main__":
    unittest.main()
