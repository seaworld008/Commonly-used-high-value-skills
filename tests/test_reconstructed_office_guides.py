"""Check guide links and new examples offline; never start Office or a server.

Copyright (c) 2026 seaworld008
SPDX-License-Identifier: MIT
"""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

from openpyxl import load_workbook
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
OFFICE = ROOT / "skills/office-white-collar"
COMMIT = "e4bb5d960d87126ff3b3a8af1a104b7db67560ba"
GUIDES = (
    "docx/SKILL.md", "docx/EXTENDED.md", "pptx/SKILL.md",
    "pptx/editing.md", "pptx/pptxgenjs.md", "xlsx/SKILL.md",
)


def blocks(path, language):
    return re.findall(rf"^```{language}\n(.*?)^```", path.read_text(), re.M | re.S)


def heading_ids(text):
    # Local headings use plain text; GitHub strips punctuation, keeping Unicode.
    return {
        re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        for title in re.findall(r"^#{1,6} (.+)$", text, re.M)
    }


@pytest.mark.parametrize("relative", GUIDES)
def test_local_links_and_script_routes_resolve(relative):
    path = OFFICE / relative
    text = path.read_text()
    for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if re.match(r"https?://", link):
            continue
        filename, _, fragment = link.partition("#")
        target = (path.parent / filename).resolve() if filename else path
        assert target.is_relative_to(OFFICE)
        assert target.is_file(), (relative, link)
        if fragment:
            assert fragment in heading_ids(target.read_text()), (relative, link)
    # Check all displayed helper names without reading their implementations.
    for script in re.findall(r"(?<![\w/])(scripts/[\w/]+\.py)\b", text):
        assert (path.parent / script).is_file(), (relative, script)


@pytest.mark.parametrize("skill", ["docx", "pptx", "xlsx"])
def test_entry_metadata_and_fixed_licensed_source(skill):
    path = OFFICE / skill / "SKILL.md"
    text = path.read_text()
    header = yaml.safe_load(text.split("---", 2)[1])
    assert header["name"] == skill
    assert header["tags"] == [skill]
    assert header["quality"] == 5
    assert header["version"] == "1.1.3"
    assert header["source"] == "https://github.com/anthropics/skills"
    assert header["license"] == "Apache-2.0"
    assert header["author"] == "Anthropic contributors; local curators"
    assert header["source_url"] == (
        f"https://github.com/anthropics/skills/blob/{COMMIT}/skills/{skill}/SKILL.md"
    )
    assert {"description", "zh_description", "created_at", "updated_at", "complexity"} <= header.keys()
    assert len(text.splitlines()) >= 50


@pytest.mark.parametrize("relative", GUIDES)
def test_adaptation_has_attribution_and_local_change_notice(relative):
    text = (OFFICE / relative).read_text()
    assert COMMIT in text
    assert "Complete terms in LICENSE.txt" in text
    assert "本地修改" in text
    assert "SPDX-License-Identifier: Apache-2.0" in text


@pytest.mark.parametrize("relative", ["docx/EXTENDED.md", "pptx/pptxgenjs.md"])
def test_original_javascript_parses_without_installing_dependencies(relative, tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is absent; JS syntax has not been checked")
    examples = blocks(OFFICE / relative, "javascript")
    assert len(examples) == 1
    example = tmp_path / "example.cjs"
    example.write_text(examples[0])
    completed = subprocess.run(
        [node, "--check", str(example)], cwd=tmp_path,
        text=True, capture_output=True, timeout=15,
    )
    assert completed.returncode == 0, completed.stderr


def test_xlsx_example_creates_real_formulas_styles_and_uncalculated_caches(tmp_path):
    examples = [code for code in blocks(OFFICE / "xlsx/SKILL.md", "python") if "book = Workbook()" in code]
    assert len(examples) == 1
    compile(examples[0], "xlsx guide example", "exec")
    script = tmp_path / "make-workbook.py"
    script.write_text(examples[0])
    destination = tmp_path / "example.xlsx"
    completed = subprocess.run(
        [sys.executable, str(script), str(destination)], cwd=tmp_path,
        env={**os.environ, "TMPDIR": str(tmp_path)},
        text=True, capture_output=True, timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    book = load_workbook(destination, data_only=False)
    sheet = book["Delivery"]
    assert (sheet["B2"].value, sheet["C2"].value) == (20, 18)
    assert {cell.coordinate: cell.value for row in sheet for cell in row if cell.data_type == "f"} == {
        "D2": "=C2/B2", "B3": "=SUM(B2:B2)",
        "C3": "=SUM(C2:C2)", "D3": "=C3/B3",
    }
    assert sheet["D2"].number_format == "0.0%"
    assert sheet["B2"].fill.fgColor.rgb.endswith("FFF1B8")
    assert "合成示例" in sheet["B2"].comment.text
    assert book["Sources"]["A2"].value == "Delivery!B2:C2"
    book.close()
    cached = load_workbook(destination, data_only=True)
    assert cached["Delivery"]["D2"].value is None
    cached.close()
    with zipfile.ZipFile(destination) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    cells = [cell for cell in root.findall(".//s:c", ns) if cell.find("s:f", ns) is not None]
    assert len(cells) == 4
    assert all(cell.find("s:v", ns) is None or cell.find("s:v", ns).text is None for cell in cells)


def test_redline_and_comment_xml_examples_have_consistent_semantics():
    examples = blocks(OFFICE / "docx/EXTENDED.md", "xml")
    assert len(examples) == 2
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraph = ET.fromstring(examples[0])
    for excluded, expected in (("del", "交付日期为 周三。"), ("ins", "交付日期为 周二。")):
        pieces = []
        for child in paragraph:
            if child.tag != ns + excluded:
                pieces.extend(node.text or "" for node in child.iter()
                              if node.tag in (ns + "t", ns + "delText"))
        assert "".join(pieces) == expected
    comment = ET.fromstring(examples[1])
    markers = [node for node in comment.iter() if node.tag in {
        ns + "commentRangeStart", ns + "commentRangeEnd", ns + "commentReference",
    }]
    assert len(markers) == 3
    assert {node.attrib[ns + "id"] for node in markers} == {"12"}
