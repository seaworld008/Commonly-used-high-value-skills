from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_dead_links.py"


class CheckDeadLinksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("check_dead_links", SCRIPT_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.module = module

    def test_should_ignore_template_urls(self) -> None:
        urls = [
            "https://github.com/user/repo",
            "https://figma.com/design/:fileKey/:fileName?node-id=1-2",
            "https://arxiv.org/abs/{id",
            "https://hooks\\.slack\\.com/services/[A-Z0-9",
            "https://staging.myapp.com",
        ]
        for url in urls:
            self.assertTrue(self.module.should_ignore_url(url), url)

    def test_should_keep_real_urls(self) -> None:
        urls = [
            "https://github.com/seaworld008/Commonly-used-high-value-skills",
            "https://github.com/NousResearch/hermes-agent",
            "https://supabase.com/docs/guides/getting-started/ai-skills",
        ]
        for url in urls:
            self.assertFalse(self.module.should_ignore_url(url), url)


if __name__ == "__main__":
    unittest.main()
