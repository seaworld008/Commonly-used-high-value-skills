"""Offline contracts for the independently authored Figma guide packages.

Only the replacement files are read. No original revisions, login state,
network, desktop application, or Figma connection is needed by these tests.
"""

import json
import re
import struct
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import pytest
import yaml
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "skills" / "ai-agent-platform"
NAMES = ("figma", "figma-implement-design")
COMMON_FILES = {
    "SKILL.md", "LICENSE.txt", "agents/openai.yaml", "assets/icon.svg",
    "assets/figma-small.svg", "assets/figma.png",
}
REFERENCES = {
    "references/figma-mcp-config.md", "references/figma-tools-and-prompts.md",
}
SVG_NS = "http://www.w3.org/2000/svg"


def frontmatter(name):
    content = (BASE / name / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", content, re.S)
    assert match, name
    return yaml.safe_load(match[1]), content[match.end():]


def local_links(path):
    """Resolve Markdown links while preserving their document-relative base."""
    for target in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)\)", path.read_text(encoding="utf-8")):
        parsed = urlsplit(target)
        if parsed.scheme:
            assert parsed.scheme == "https", (path, target)
            assert parsed.hostname == "developers.figma.com", (path, target)
            assert not parsed.username and not parsed.password and not parsed.query
            continue
        assert not parsed.netloc and not parsed.path.startswith("/"), (path, target)
        if parsed.path:
            yield (path.parent / unquote(parsed.path)).resolve()


def code_examples(path):
    return re.findall(r"^```(\w+)\n(.*?)^```", path.read_text(encoding="utf-8"), re.M | re.S)


@pytest.mark.parametrize("name", NAMES)
def test_inventory_and_metadata(name):
    directory = BASE / name
    expected = COMMON_FILES | (REFERENCES if name == "figma" else set())
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
    assert actual == expected
    assert all(not p.is_symlink() for p in directory.rglob("*"))
    fm, body = frontmatter(name)
    required = {
        "name", "description", "zh_description", "version", "author", "source",
        "source_url", "license", "tags", "created_at", "updated_at", "quality", "complexity",
    }
    assert required <= fm.keys()
    assert fm["name"] == name
    assert fm["source"] == "in-house" and fm["author"] == "seaworld008"
    assert fm["license"] == "MIT" and fm["source_url"] == ""
    assert re.fullmatch(r"\d+\.\d+\.\d+", fm["version"])
    minimum = {"figma": (1, 1, 2), "figma-implement-design": (1, 0, 3)}
    assert tuple(map(int, fm["version"].split("."))) >= minimum[name]
    assert type(fm["quality"]) is int and 3 <= fm["quality"] <= 5
    assert len((directory / "SKILL.md").read_text().splitlines()) >= {3: 80, 4: 100, 5: 200}[fm["quality"]]
    assert isinstance(fm["tags"], list) and len(set(fm["tags"])) == len(fm["tags"])
    assert re.search(r"[\u4e00-\u9fff]", fm["zh_description"])
    assert len(fm["description"]) >= 20 and len(body.splitlines()) >= 60


@pytest.mark.parametrize("name", NAMES)
def test_every_attachment_is_reachable_from_entry(name):
    directory = BASE / name
    visited = set()
    pending = [directory / "SKILL.md"]
    permitted = tuple((BASE / n).resolve() for n in NAMES)
    while pending:
        path = pending.pop().resolve()
        if path in visited:
            continue
        assert any(path.is_relative_to(p) for p in permitted), path
        assert path.is_file(), path
        visited.add(path)
        if path.suffix == ".md":
            pending.extend(local_links(path))
        elif path.name == "openai.yaml":
            interface = yaml.safe_load(path.read_text())["interface"]
            pending.extend((path.parent.parent / interface[k]).resolve() for k in ("icon_small", "icon_large"))
    expected = {p.resolve() for p in directory.rglob("*") if p.is_file()}
    assert expected <= visited, expected - visited


@pytest.mark.parametrize("name", NAMES)
def test_license_matches_repository_mit_in_full(name):
    assert (BASE / name / "LICENSE.txt").read_bytes() == (ROOT / "LICENSE").read_bytes()


@pytest.mark.parametrize("name", NAMES)
def test_host_display_yaml_has_valid_interface_and_real_asset_paths(name):
    document = yaml.safe_load((BASE / name / "agents/openai.yaml").read_text())
    assert set(document) == {"interface"}  # No implicit host connection/config mutation.
    interface = document["interface"]
    required = {"display_name", "short_description", "icon_small", "icon_large", "brand_color", "default_prompt"}
    assert set(interface) == required
    assert all(isinstance(v, str) and v.strip() for v in interface.values())
    assert 25 <= len(interface["short_description"]) <= 64
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", interface["brand_color"])
    assert "$" + name in interface["default_prompt"]
    for key, suffix in (("icon_small", ".svg"), ("icon_large", ".png")):
        path = (BASE / name / interface[key]).resolve()
        assert path.is_relative_to((BASE / name / "assets").resolve())
        assert path.is_file() and path.suffix == suffix


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("filename", ("icon.svg", "figma-small.svg"))
def test_svg_is_accessible_generic_rectangle_line_geometry(name, filename):
    path = BASE / name / "assets" / filename
    data = path.read_text()
    assert "<!DOCTYPE" not in data and "<!ENTITY" not in data
    root = ET.fromstring(data)
    assert root.tag == f"{{{SVG_NS}}}svg"
    assert root.attrib["viewBox"] == "0 0 64 64"
    assert root.attrib["role"] == "img"
    ids = {e.attrib.get("id"): e for e in root}
    for ref in root.attrib["aria-labelledby"].split():
        assert ids[ref].text
    allowed = {"svg", "title", "desc", "rect", "line"}
    primitives = []
    for element in root.iter():
        tag = element.tag.removeprefix(f"{{{SVG_NS}}}")
        assert tag in allowed  # Reject paths/circles composing brand marks, scripts and embedded images.
        for key, value in element.attrib.items():
            assert not key.lower().startswith("on") and "href" not in key.lower()
            assert "url(" not in value.lower()
            if key in {"fill", "stroke"}:
                assert value in {"#183452", "#3568B0", "#FFFFFF"}
        if tag == "rect":
            x, y, w, h = [float(element.attrib[k]) for k in ("x", "y", "width", "height")]
            assert 0 < x < x + w < 64 and 0 < y < y + h < 64
            assert w > 10 and h > 10
            primitives.append(tag)
        elif tag == "line":
            assert all(0 < float(element.attrib[k]) < 64 for k in ("x1", "y1", "x2", "y2"))
            primitives.append(tag)
    assert 1 <= primitives.count("rect") <= 3 and primitives.count("line") >= 4
    assert "figma" not in " ".join(root.itertext()).lower()  # Generic labels, no brand artwork.


@pytest.mark.parametrize("name", NAMES)
def test_png_crc_payload_palette_and_svg_geometry_agree(name):
    path = BASE / name / "assets/figma.png"
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    offset = 8
    chunks = []
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        assert len(payload) == length
        crc = struct.unpack(">I", data[offset + 8 + length:offset + 12 + length])[0]
        assert crc == zlib.crc32(kind + payload) & 0xffffffff
        chunks.append((kind, payload))
        offset += length + 12
    assert offset == len(data) and chunks[0][0] == b"IHDR" and chunks[-1][0] == b"IEND"
    assert {kind for kind, _ in chunks} <= {b"IHDR", b"IDAT", b"IEND"}
    width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    assert (width, height, depth, color, compression, filtering, interlace) == (256, 256, 8, 6, 0, 0, 0)
    raw = zlib.decompress(b"".join(p for k, p in chunks if k == b"IDAT"))
    assert len(raw) == 256 * (256 * 4 + 1)
    with Image.open(path) as image:
        image.load()
        assert image.mode == "RGBA" and image.size == (256, 256)
        # A restricted neutral/blue palette excludes the multicolor Figma logo.
        allowed = {(0, 0, 0, 0), (24, 52, 82, 255), (53, 104, 176, 255), (255, 255, 255, 255)}
        assert {image.getpixel((x, y)) for y in range(image.height) for x in range(image.width)} == allowed
        assert image.getpixel((0, 0))[3] == 0 and image.getbbox() is not None
        svg = ET.parse(BASE / name / "assets/icon.svg").getroot()
        for element in svg:
            a = element.attrib
            if element.tag.endswith("}rect"):
                x, y, w, h = [int(a[k]) for k in ("x", "y", "width", "height")]
                assert image.getpixel(((x + w // 2) * 4, (y + h // 2) * 4)) == (255, 255, 255, 255)
                assert image.getpixel((x * 4, y * 4)) == (53, 104, 176, 255)
            elif element.tag.endswith("}line"):
                x = (int(a["x1"]) + int(a["x2"])) * 2
                y = (int(a["y1"]) + int(a["y2"])) * 2
                assert image.getpixel((x, y)) == (24, 52, 82, 255)


def test_entry_routes_have_distinct_tasks_and_concrete_outputs():
    reader, read_body = frontmatter("figma")
    implementer, impl_body = frontmatter("figma-implement-design")
    assert reader["description"].lower().startswith("read ")
    assert implementer["description"].lower().startswith("implement ")
    assert {"variables", "assets"} <= set(re.findall(r"\w+", reader["description"].lower()))
    assert {"project", "keyboard", "visual"} <= set(re.findall(r"\w+", implementer["description"].lower()))
    assert (BASE / "figma-implement-design/SKILL.md").resolve() in set(local_links(BASE / "figma/SKILL.md"))
    assert (BASE / "figma/SKILL.md").resolve() in set(local_links(BASE / "figma-implement-design/SKILL.md"))
    # Read evidence is tabulated; implementation has executable measurement data.
    assert len(re.findall(r"^\|[^\n]+\|$", read_body, re.M)) >= 5
    assert any(lang == "yaml" and "acceptance" in yaml.safe_load(text)
               for lang, text in code_examples(BASE / "figma-implement-design/SKILL.md"))


def test_acceptance_example_has_measurable_visual_accessibility_and_state_budgets():
    examples = [yaml.safe_load(text) for lang, text in code_examples(BASE / "figma-implement-design/SKILL.md") if lang == "yaml"]
    assert len(examples) == 1
    plan = examples[0]["acceptance"]
    assert set(plan) == {"viewports", "visual", "accessibility", "states"}
    widths = []
    for viewport in plan["viewports"]:
        assert set(viewport) == {"name", "width", "height"}
        assert all(type(viewport[k]) is int and 240 <= viewport[k] <= 4096 for k in ("width", "height"))
        widths.append(viewport["width"])
    assert min(widths) <= 480 and max(widths) >= 1024
    visual = plan["visual"]
    assert 0 < visual["layout_px"] <= 4
    assert 0 < visual["changed_pixel_ratio"] <= 0.05
    assert type(visual["channel_delta"]) is int and 0 < visual["channel_delta"] < 256
    a11y = plan["accessibility"]
    assert a11y["text_contrast"] >= 4.5
    assert a11y["large_text_contrast"] >= 3 and a11y["control_contrast"] >= 3
    assert {"Tab", "Shift+Tab", "Enter", "Space", "Escape"} <= set(a11y["keyboard"])
    assert {"default", "loading", "empty", "error", "success", "disabled", "focus"} <= set(plan["states"])


def test_url_location_example_has_consistent_file_and_node_identity():
    examples = [json.loads(text) for language, text in code_examples(BASE / "figma/SKILL.md") if language == "json"]
    located = [example for example in examples if "url" in example]
    assert located
    for example in located:
        parsed = urlsplit(example["url"])
        assert parsed.scheme == "https" and parsed.hostname in {"figma.com", "www.figma.com"}
        assert parsed.username is None and parsed.password is None and parsed.port in {None, 443}
        assert parsed.path.split("/")[1:3] == ["design", example["fileKey"]]
        node = parse_qs(parsed.query)["node-id"]
        assert len(node) == 1 and re.fullmatch(r"\d+-\d+", node[0])
        assert node[0].replace("-", ":") == example["nodeId"]
        assert example["objectType"] == "Design"


@pytest.mark.parametrize("name", NAMES)
def test_examples_parse_and_no_secret_output_or_forced_host_flags(name):
    dangerous = re.compile(
        r"(?:echo|printenv|printf)\s+[^\n]*(?:TOKEN|SECRET|AUTHORIZATION|COOKIE)|"
        r"--(?:dangerously-skip-permissions|dangerously-bypass-approvals-and-sandbox|yolo|full-auto)|"
        r"approval_policy\s*[:=]\s*['\"]?never|sandbox_mode\s*[:=]\s*['\"]?danger-full-access|"
        r"(?:npm|pip)\s+install\s+(?:-g|--global)|curl[^\n]*\|\s*(?:sh|bash)", re.I,
    )
    for path in (BASE / name).rglob("*"):
        if path.suffix not in {".md", ".yaml"}:
            continue
        content = path.read_text(encoding="utf-8")
        assert not dangerous.search(content), path
        assert not re.search(r"\b(?:figd_|ghp_|sk-)[A-Za-z0-9]{16,}", content), path
        assert not re.search(r"mcp__figma__\w+", content), path  # No invented fully qualified host calls.
        if path.suffix == ".md":
            for language, text in code_examples(path):
                assert language in {"json", "yaml"}, path
                parsed = json.loads(text) if language == "json" else yaml.safe_load(text)
                assert isinstance(parsed, dict)
                assert not re.search(r'"(?:token|authorization|cookie|password)"\s*:', text, re.I)
