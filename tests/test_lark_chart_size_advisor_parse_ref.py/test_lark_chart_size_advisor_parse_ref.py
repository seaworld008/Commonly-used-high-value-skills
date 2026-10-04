import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "knowledge-and-pm-integrations" / "lark-sheets" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lark_chart_size_advisor import _parse_ref


class ParseRefTests(unittest.TestCase):
    def test_accepts_single_cell_reference(self):
        self.assertEqual(_parse_ref("A1"), (None, "A1"))
        self.assertEqual(_parse_ref("'Summary'!$B$2"), ("Summary", "B2"))

    def test_preserves_multi_cell_range_reference(self):
        self.assertEqual(_parse_ref("Sheet1!A1:C3"), ("Sheet1", "A1:C3"))

    def test_rejects_invalid_a1_references(self):
        for value in ("", "A1:", "A1:B", "not-a-range"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _parse_ref(value)


if __name__ == "__main__":
    unittest.main()
