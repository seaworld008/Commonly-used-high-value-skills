import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "discover_new_skills.py"


def load_module():
    spec = importlib.util.spec_from_file_location("discover_new_skills", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DiscoverNewSkillsTests(unittest.TestCase):
    def test_load_retired_skill_names_reads_hard_retirement_denylist(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = Path(tmpdir) / "portfolio-policy.json"
            policy.write_text(
                json.dumps(
                    {
                        "retired_skills": [
                            {"name": "legacy-helper", "replacement": "current-helper"},
                            {"name": "duplicate-helper"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                {"legacy-helper", "duplicate-helper"},
                module.load_retired_skill_names(policy),
            )

    def test_build_report_includes_source_health_and_errors(self):
        module = load_module()

        report = module.build_discovery_report(
            local_skill_count=10,
            all_discoveries=[
                module.make_discovery(
                    source_key="github",
                    name="alpha",
                    source="GitHub",
                    url="https://github.com/example/alpha",
                    repo_stars=1,
                    description="Alpha",
                )
            ],
            unique_discoveries=[
                module.make_discovery(
                    source_key="github",
                    name="alpha",
                    source="GitHub",
                    url="https://github.com/example/alpha",
                    repo_stars=1,
                    description="Alpha",
                )
            ],
            source_health={
                "github": {
                    "status": "degraded",
                    "errors": [{"kind": "unauthorized", "message": "401"}],
                    "queries": 2,
                    "results": 1,
                },
                "skills_sh": {
                    "status": "healthy",
                    "errors": [],
                    "queries": 1,
                    "results": 0,
                },
                "clawhub": {
                    "status": "healthy",
                    "errors": [],
                    "queries": 1,
                    "results": 0,
                },
            },
        )

        self.assertEqual(10, report["local_skill_count"])
        self.assertIn("generated_at", report)
        self.assertTrue(report["generated_at"].endswith("Z"))
        self.assertIn("source_health", report)
        self.assertEqual("degraded", report["source_health"]["github"]["status"])
        self.assertEqual("unauthorized", report["errors"][0]["kind"])
        self.assertEqual(1, report["source_health"]["github"]["emitted"])
        self.assertEqual(1, report["source_health"]["github"]["unique_emitted"])
        self.assertEqual(1, report["raw_discovered"])

    def test_classify_fetch_error_recognizes_http_statuses(self):
        module = load_module()

        unauthorized = module.classify_fetch_error(401, "Unauthorized")
        rate_limited = module.classify_fetch_error(429, "Too Many Requests")
        not_found = module.classify_fetch_error(404, "Not Found")

        self.assertEqual("unauthorized", unauthorized["kind"])
        self.assertEqual("rate_limited", rate_limited["kind"])
        self.assertEqual("not_found", not_found["kind"])


if __name__ == "__main__":
    unittest.main()
