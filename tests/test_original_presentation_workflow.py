# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Behavioral regressions for the original presentation workflow and chart renderer."""

import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/office-white-collar/pptx/scripts/chartkit.py"
DOCS = ROOT / "skills/office-white-collar/pptx/references/creator-workflow"


class OriginalPresentationWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        cls.root = Path(cls.workspace.name)
        cls.environment = patch.dict(os.environ, {
            "MPLCONFIGDIR": str(cls.root / "mpl"),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        cls.environment.start()
        spec = importlib.util.spec_from_file_location("original_chartkit", SCRIPT)
        cls.chart = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.chart)
        cls.pd, cls.np, cls.plt = cls.chart._lazy_imports()

    @classmethod
    def tearDownClass(cls):
        cls.plt.close("all")
        cls.environment.stop()
        cls.workspace.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(self.work.cleanup)
        self.directory = Path(self.work.name)
        self.frame = self.pd.DataFrame({"team": ["Training", "Support", "Planning"],
                                      "requests": [14, 9, 6], "completed": [11, 7, 4]})

    def run_cli(self, *arguments, no_site=False):
        command = [sys.executable]
        if no_site:
            command.append("-S")
        return subprocess.run([*command, str(SCRIPT), *arguments], cwd=ROOT,
                              text=True, capture_output=True, timeout=60)

    def render_and_observe(self, frame, kind, x, ys, output):
        real_subplots = self.plt.subplots
        axes = []

        def capture(*args, **kwargs):
            figure, ax = real_subplots(*args, **kwargs)
            axes.append(ax)
            return figure, ax

        with patch.object(self.plt, "subplots", side_effect=capture):
            result = self.chart.render_chart(frame, kind, x, ys, "Synthetic fixture", output)
        self.assertEqual(result, output)
        self.assertEqual(self.plt.get_fignums(), [])
        return axes[0]

    def test_bar_svg_contains_real_series_and_accessible_text(self):
        output = self.directory / "bars.svg"
        ax = self.render_and_observe(self.frame, "bar", "team", ["requests", "completed"], output)
        self.assertEqual([bar.get_height() for bar in ax.patches], [14, 9, 6, 11, 7, 4])
        svg = ET.parse(output).getroot()
        self.assertEqual(svg.attrib["viewBox"], "0 0 864 486")
        texts = " ".join(svg.itertext())
        for required in ["Synthetic fixture", "Training", "Support", "Planning", "requests", "completed"]:
            self.assertIn(required, texts)
        self.assertGreater(len(svg.findall(".//{http://www.w3.org/2000/svg}path")), 6)

    def test_png_dimensions_and_nonblank_pixels(self):
        from PIL import Image
        output = self.directory / "bars.png"
        ax = self.render_and_observe(self.frame, "barh", "team", ["requests"], output)
        self.assertEqual([bar.get_width() for bar in ax.patches], [14, 9, 6])
        with Image.open(output) as picture:
            self.assertEqual(picture.size, (1200, 675))
            self.assertEqual(picture.format, "PNG")
            rgb = picture.convert("RGB")
            self.assertGreater(len(rgb.getcolors(maxcolors=1000000)), 20)
            self.assertIn((36, 90, 115), {color for _, color in rgb.getcolors(maxcolors=1000000)})

    def test_line_preserves_observation_order(self):
        ax = self.render_and_observe(self.frame, "line", "team", ["requests"], self.directory / "line.svg")
        self.assertEqual(ax.lines[0].get_ydata().tolist(), [14, 9, 6])
        self.assertEqual([tick.get_text() for tick in ax.get_xticklabels()], self.frame.team.tolist())

    def test_area_stacks_real_values(self):
        ax = self.render_and_observe(self.frame, "area", "team", ["requests", "completed"], self.directory / "area.svg")
        self.assertEqual(len(ax.collections), 2)
        vertices = ax.collections[1].get_paths()[0].vertices
        for position, total in [(0, 25), (1, 16), (2, 10)]:
            self.assertIn(total, vertices[vertices[:, 0] == position, 1].tolist())

    def test_scatter_uses_numeric_x(self):
        frame = self.pd.DataFrame({"time": [1, 4, 10], "count": [8, 3, 6]})
        ax = self.render_and_observe(frame, "scatter", "time", ["count"], self.directory / "scatter.svg")
        self.assertEqual(ax.collections[0].get_offsets().tolist(), [[1, 8], [4, 3], [10, 6]])

    def test_histogram_counts_observations_not_row_labels(self):
        frame = self.pd.DataFrame({"id": ["a", "a", "b", "c"], "value": [1, 1, 2, 4]})
        ax = self.render_and_observe(frame, "hist", "id", ["value"], self.directory / "hist.svg")
        self.assertEqual(sum(bar.get_height() for bar in ax.patches), 4)
        self.assertEqual(ax.get_ylabel(), "Observation count")

    def test_waterfall_signed_deltas_end_at_correct_balance(self):
        frame = self.pd.DataFrame({"step": ["Opening", "Added", "Removed"], "change": [20, 5, -3]})
        ax = self.render_and_observe(frame, "waterfall", "step", ["change"], self.directory / "waterfall.svg")
        self.assertEqual([bar.get_y() for bar in ax.patches], [0, 20, 25])
        self.assertEqual([bar.get_height() for bar in ax.patches], [20, 5, -3])
        self.assertEqual(ax.patches[-1].get_y() + ax.patches[-1].get_height(), 22)

    def test_reproducible_svg_and_png_bytes(self):
        for extension in ("svg", "png"):
            with self.subTest(extension=extension):
                paths = [self.directory / f"repro-{index}.{extension}" for index in range(2)]
                for path in paths:
                    self.chart.render_chart(self.frame, "bar", "team", ["requests"], "Synthetic", path)
                self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())

    def test_invalid_values_never_overwrite_existing_chart(self):
        output = self.directory / "preserved.svg"
        self.chart.render_chart(self.frame, "bar", "team", ["requests"], "Original synthetic", output)
        before = output.read_bytes()
        for value in (None, float("nan"), float("inf"), -float("inf"), "", "unknown", True, 1 + 2j):
            with self.subTest(value=value):
                frame = self.frame.astype(object)
                frame.loc[1, "requests"] = value
                with self.assertRaises(ValueError):
                    self.chart.render_chart(frame, "bar", "team", ["requests"], "Invalid", output)
                self.assertEqual(output.read_bytes(), before)

    def test_invalid_structure_and_semantics(self):
        cases = [
            (self.frame.iloc[:0], "bar", "team", ["requests"]),
            (self.frame, "pie", "team", ["requests"]),
            (self.frame, "bar", "missing", ["requests"]),
            (self.frame, "bar", "team", []),
            (self.frame, "bar", "team", ["requests", "requests"]),
            (self.frame, "waterfall", "team", ["requests", "completed"]),
            (self.frame, "scatter", "team", ["requests"]),
            (self.frame.assign(team=[1 + 2j, 2 + 3j, 3 + 4j]), "scatter", "team", ["requests"]),
            (self.frame.assign(team=["A", "A", "B"]), "line", "team", ["requests"]),
            (self.frame.assign(team=["A", None, "B"]), "bar", "team", ["requests"]),
            (self.frame.assign(requests=[1, -2, 3]), "area", "team", ["requests"]),
            (self.frame.assign(requests=[1e308] * 3, completed=[1e308] * 3), "area", "team", ["requests", "completed"]),
            (self.frame.assign(requests=[1e308] * 3), "waterfall", "team", ["requests"]),
        ]
        for frame, kind, x, ys in cases:
            with self.subTest(kind=kind, x=x, ys=ys):
                with self.assertRaises(ValueError):
                    self.chart.render_chart(frame, kind, x, ys, "Invalid", self.directory / "invalid.svg")
                self.assertFalse((self.directory / "invalid.svg").exists())
                self.assertEqual(self.plt.get_fignums(), [])

    def test_rendering_or_publish_failure_preserves_destination_and_cleans_staging(self):
        from matplotlib.figure import Figure
        output = self.directory / "stable.png"
        self.chart.render_chart(self.frame, "bar", "team", ["requests"], "Synthetic", output)
        before = output.read_bytes()
        for target in (patch.object(Figure, "savefig", side_effect=OSError("disk failure")),
                       patch.object(self.chart.os, "replace", side_effect=OSError("publish failure"))):
            with target, self.assertRaises(OSError):
                self.chart.render_chart(self.frame, "bar", "team", ["requests"], "Synthetic", output)
            self.assertEqual(output.read_bytes(), before)
            self.assertEqual(list(self.directory.glob(".chartkit-*")), [])
            self.assertEqual(self.plt.get_fignums(), [])

    def test_csv_json_parsing_and_rejection(self):
        csv_file = self.directory / "valid.csv"
        csv_file.write_text("team,value\nNA,2\nB,0\n", encoding="utf-8")
        self.assertEqual(self.chart._read_data(csv_file).team.tolist(), ["NA", "B"])
        json_file = self.directory / "valid.json"
        json_file.write_text('[{"team":"A","value":2},{"team":"B","value":0}]')
        self.assertEqual(self.chart._read_data(json_file).value.tolist(), [2, 0])
        for name, body in [("duplicate.csv", "a,a\n1,2\n"), ("width.csv", "a,b\n1\n"),
                           ("empty.csv", ""), ("object.json", '{"a":1}'),
                           ("duplicate.json", '[{"a":1,"a":2}]')]:
            path = self.directory / name
            path.write_text(body)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.chart._read_data(path)

    def test_cli_help_and_missing_dependencies(self):
        help_result = self.run_cli("--help", no_site=True)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        for flag in ("--data", "--type", "--x", "--y", "--out", "--filename", "--title"):
            self.assertIn(flag, help_result.stdout)
        result = self.run_cli("--data", "missing.csv", "--type", "bar", "--x", "x",
                              "--y", "y", "--out", str(self.directory), "--filename", "missing.svg", no_site=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires matplotlib", result.stderr)
        self.assertFalse((self.directory / "missing.svg").exists())

    def test_cli_failure_exit_and_explicit_output(self):
        source = self.directory / "data.json"
        source.write_text('[{"team":"A","value":null}]')
        output = self.directory / "keep.svg"
        output.write_text("existing chart sentinel")
        arguments = ["--data", str(source), "--type", "bar", "--x", "team", "--y", "value",
                     "--out", str(self.directory), "--filename"]
        result = self.run_cli(*arguments, "keep.svg")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_text(), "existing chart sentinel")
        result = self.run_cli(*arguments, "../escape.svg")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("basename", result.stderr)
        source.write_text('[{"team":"A","value":0},{"team":"B","value":4}]')
        result = self.run_cli(*arguments, "keep.svg")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(output))
        self.assertEqual(ET.parse(output).getroot().tag, "{http://www.w3.org/2000/svg}svg")

    def test_documented_shell_example_runs_and_matches_outputs(self):
        source = (DOCS / "EXAMPLES.md").read_text(encoding="utf-8")
        shell_example = re.findall(r"```sh\n(.*?)```", source, flags=re.S)[0]
        environment = dict(os.environ, TMPDIR=str(self.directory))
        result = subprocess.run(["/bin/sh", "-eu", "-c", shell_example], cwd=ROOT, env=environment,
                                text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        svg = ET.parse(self.directory / "synthetic-requests.svg").getroot()
        self.assertIn("Synthetic pilot", " ".join(svg.itertext()))
        self.assertEqual(svg.attrib["viewBox"], "0 0 864 486")
        from PIL import Image
        with Image.open(self.directory / "synthetic-requests.png") as image:
            self.assertEqual(image.size, (1200, 675))

    def test_documented_python_api_example_runs(self):
        source = (DOCS / "EXAMPLES.md").read_text(encoding="utf-8")
        example = re.findall(r"```python\n(.*?)```", source, flags=re.S)[0]
        result = subprocess.run([sys.executable, "-c", example], cwd=ROOT,
                                env=dict(os.environ, TMPDIR=str(self.directory)),
                                text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        svg = ET.parse(self.directory / "synthetic-waterfall.svg").getroot()
        self.assertIn("Synthetic balance changes", " ".join(svg.itertext()))


if __name__ == "__main__":
    unittest.main()
