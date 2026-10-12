"""Regression coverage for the offline HTML renderer and the Live Panel request boundary."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills/office-white-collar/answer-me-with-html/scripts/am.mjs"
PANEL = ROOT / "skills/multimodal-media/live-panel/assets/template.html"


@unittest.skipUnless(__import__("shutil").which("node"), "Node is not installed")
class HardenedRendererTests(unittest.TestCase):
    def command(self, directory: Path, *args: str, text: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            ["node", str(CLI), *args],
            cwd=directory, input=text,
            text=True, capture_output=True, timeout=15, check=False,
        )

    def test_xss_payload_escaped_and_csp_disallows_script_and_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = (
                "---\ntitle: <script>bad</script>\nlang: en\n---\n"
                "## Demo\n<script>alert(1)</script>\n"
                "<SVG onload=alert(2)>\n"
                "| Name | Value |\n| --- | --- |\n| <img src=x onerror=alert(3)> | data |\n"
            )
            process = self.command(root, "render", "-", "--no-open", text=payload)
            self.assertEqual(0, process.returncode, process.stderr)
            files = list((root / ".am-pages").glob("*.html"))
            self.assertEqual(1, len(files))
            html = files[0].read_text(encoding="utf-8")
            self.assertIn("Content-Security-Policy", html)
            self.assertIn("default-src &#39;none&#39;", html)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
            self.assertIn("&lt;SVG onload=alert(2)&gt;", html)
            self.assertIn("&lt;img src=x onerror=alert(3)&gt;", html)
            self.assertNotIn("<script>alert(1)</script>", html)
            self.assertNotIn("<img src=x onerror=alert(3)>", html)
            self.assertRegex(files[0].name, r"^am-[a-f0-9]{24}\.html$")

    def test_render_supports_tables_code_and_basic_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fenced = chr(96) * 3
            payload = "\n".join([
                "## Components", "| Service | Status |", "| --- | --- |",
                "| Gateway | ok |", fenced + "flow",
                "Client -> API -> Database", fenced, "",
            ])
            result = self.command(root, "render", "-", text=payload)
            self.assertEqual(0, result.returncode, result.stderr)
            html = next((root / ".am-pages").glob("*.html")).read_text()
            self.assertIn("<table>", html)
            self.assertIn("Gateway", html)
            self.assertIn('class="flow"', html)
            self.assertIn("Database", html)

    def test_patch_updates_exact_managed_panel_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self.command(root, "render", "-", text="## Findings\nOriginal\n## Other\nKeep\n")
            self.assertEqual(0, first.returncode, first.stderr)
            target = next((root / ".am-pages").glob("*.html"))
            updated = self.command(root, "patch", str(target), "--panel", "Findings", text="Replacement <script>\n")
            self.assertEqual(0, updated.returncode, updated.stderr)
            output = target.read_text()
            self.assertIn("Replacement &lt;script&gt;", output)
            self.assertIn("Keep", output)
            self.assertNotIn("<script>", output)
            missing = self.command(root, "patch", str(target), "--panel", "Not Found", text="anything")
            self.assertNotEqual(0, missing.returncode)
            self.assertEqual(output, target.read_text())

    def test_rejects_external_paths_and_legacy_exec_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "outside.html"
            outside.write_text("Keep unchanged")
            result = self.command(root, "patch", str(outside), "--panel", "Demo", text="overwrite")
            self.assertNotEqual(0, result.returncode)
            self.assertEqual("Keep unchanged", outside.read_text())
            for args in [("serve",), ("update",), ("clean",), ("render", "https://example.com"),
                         ("render", "-", "--replace", str(outside))]:
                with self.subTest(args=args):
                    result = self.command(root, *args, text="## A\nhello\n")
                    self.assertNotEqual(0, result.returncode)

    def test_input_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.command(root, "render", "-", text="A" * (256 * 1024 + 200))
            self.assertNotEqual(0, result.returncode)
            self.assertEqual([], list((root / ".am-pages").glob("*.html")) if (root / ".am-pages").exists() else [])

    @unittest.skipIf(os.name == "nt", "symlink fixture requires Unix permissions")
    def test_rejects_symlinked_output_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external = root / "destination"
            external.mkdir()
            (root / ".am-pages").symlink_to(external, target_is_directory=True)
            result = self.command(root, "render", "-", text="## A\nsafe\n")
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(any(external.iterdir()))

    def test_runtime_contains_no_shell_or_fetch_implementation(self):
        cli = CLI.read_text(encoding="utf-8")
        self.assertNotIn("child_process", cli.replace("No child processes", ""))
        self.assertNotIn("spawn(", cli)
        self.assertNotIn("eval(", cli)
        self.assertNotIn("fetch(", cli)
        self.assertNotIn("http.request(", cli)


class LivePanelNetworkSecurityTests(unittest.TestCase):
    def test_query_parameter_cannot_trigger_fetch(self):
        template = PANEL.read_text(encoding="utf-8")
        self.assertIn('connect-src \'none\'', template)
        self.assertIn('missing embedded configuration', template)
        self.assertNotRegex(template, r"\bfetch\s*\(")
        self.assertNotIn("decodeURIComponent(m[1])", template)


if __name__ == "__main__":
    unittest.main()
