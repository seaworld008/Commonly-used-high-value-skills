from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_sync_report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generate_sync_report", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GenerateSyncReportTests(unittest.TestCase):
    def test_source_label_uses_discovery_url_without_blank_github_repo(self) -> None:
        module = load_module()

        label = module.source_label(
            {
                "source": "skills.sh (supabase/agent-skills)",
                "url": "https://skills.sh/supabase/agent-skills/supabase",
            }
        )

        self.assertEqual("[supabase/agent-skills](https://skills.sh/supabase/agent-skills/supabase)", label)

    def test_upstream_skill_name_falls_back_to_video_name(self) -> None:
        module = load_module()

        self.assertEqual(
            "supabase-postgres-best-practices",
            module.upstream_skill_name({"video_name": "supabase-postgres-best-practices"}),
        )

    def test_main_generates_non_empty_skill_and_source_fields(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmp_dir = Path(tmp)
            discovery = tmp_dir / "discovery.json"
            upstream = tmp_dir / "upstream.json"
            output = tmp_dir / "sync-report.md"
            discovery.write_text(
                json.dumps(
                    {
                        "local_skill_count": 1,
                        "discoveries": [
                            {
                                "name": "supabase",
                                "source": "skills.sh (supabase/agent-skills)",
                                "url": "https://skills.sh/supabase/agent-skills/supabase",
                                "repo_stars": 100,
                                "description": "Supabase workflow guidance",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            upstream.write_text(
                json.dumps(
                    {
                        "rows": [
                            {
                                "video_name": "graphify",
                                "needs_update": True,
                                "latest_commit": "1234567890abcdef",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            old_cwd = os.getcwd()
            try:
                os.chdir(REPO_ROOT)
                module = load_module()
                module.main_args = None
                import sys

                old_argv = sys.argv
                sys.argv = [
                    "generate_sync_report.py",
                    "--discovery",
                    str(discovery.relative_to(REPO_ROOT)),
                    "--upstream",
                    str(upstream.relative_to(REPO_ROOT)),
                    "--output",
                    str(output.relative_to(REPO_ROOT)),
                ]
                module.main()
            finally:
                sys.argv = old_argv
                os.chdir(old_cwd)

            report = output.read_text(encoding="utf-8")
            self.assertIn("[supabase/agent-skills](https://skills.sh/supabase/agent-skills/supabase)", report)
            self.assertIn("**graphify**", report)
            self.assertNotIn("https://github.com/)", report)
            self.assertNotIn("****", report)


if __name__ == "__main__":
    unittest.main()
