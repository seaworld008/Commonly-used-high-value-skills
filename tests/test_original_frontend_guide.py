"""Exercise the new guide's embedded assets without a browser or network.

Copyright (c) 2026 seaworld008
SPDX-License-Identifier: MIT
"""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pytest
import yaml

from scripts.lint_skill_quality import lint_skill


SKILL = (Path(__file__).resolve().parents[1]
         / "skills/developer-engineering/frontend-design/SKILL.md")


@pytest.fixture(scope="module")
def guide():
    return SKILL.read_text(encoding="utf-8")


def block(guide, language):
    blocks = re.findall(rf"^```{language}\n(.*?)^```$", guide, re.M | re.S)
    assert len(blocks) == 1, f"Expected one complete {language} asset"
    return blocks[0]


@pytest.fixture(scope="module")
def css_rules(guide):
    css = pytest.importorskip("tinycss2", reason="CSS syntax not verified without tinycss2")
    rules = css.parse_stylesheet(block(guide, "css"), skip_comments=True,
                                 skip_whitespace=True)
    assert rules
    assert all(rule.type != "error" for rule in rules)
    return css, rules


def declarations(css, rule):
    result = css.parse_declaration_list(rule.content, skip_comments=True,
                                        skip_whitespace=True)
    assert result
    assert all(item.type == "declaration" for item in result)
    return result


def test_metadata_and_existing_quality_contract(guide):
    metadata = yaml.safe_load(guide.split("---", 2)[1])
    for field in ("name", "description", "zh_description", "version", "tags",
                  "quality", "source", "author", "license"):
        assert metadata[field]
    assert metadata["name"] == "frontend-design"
    assert metadata["source"] == "https://github.com/anthropics/skills"
    assert metadata["license"] == "Apache-2.0"
    assert "Anthropic" in metadata["author"]
    assert lint_skill(SKILL, min_lines=100)["status"] == "PASS"


def test_svg_noise_is_complete_and_references_a_real_filter(guide):
    root = ET.fromstring(block(guide, "svg"))
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.attrib["aria-hidden"] == "true"
    assert root.attrib["focusable"] == "false"
    filters = {item.attrib["id"]: item for item in root.findall("s:defs/s:filter", ns)}
    rect = root.find("s:rect", ns)
    filter_id = re.fullmatch(r"url\(#([\w-]+)\)", rect.attrib["filter"]).group(1)
    noise = filters[filter_id].find("s:feTurbulence", ns)
    assert noise.attrib["type"] == "fractalNoise"
    assert 0 < float(noise.attrib["baseFrequency"]) <= 1
    assert 1 <= int(noise.attrib["numOctaves"]) <= 4
    matrix = filters[filter_id].find("s:feColorMatrix", ns)
    values = [float(value) for value in matrix.attrib["values"].split()]
    assert len(values) == 20
    # Output RGB is zero; output alpha is nonzero but deliberately subtle.
    assert values[:15] == [0] * 15
    assert values[15:18] == [0] * 3
    assert 0 < values[18] < 0.15 and values[19] == 0
    assert all("href" not in key for node in root.iter() for key in node.attrib)


def test_css_declarations_and_reduced_motion_override(css_rules):
    css, rules = css_rules
    normal = {}
    reduced = {}
    for rule in rules:
        if rule.type == "qualified-rule":
            selector = css.serialize(rule.prelude).strip()
            normal[selector] = declarations(css, rule)
        else:
            assert rule.type == "at-rule" and rule.at_keyword == "media"
            assert css.serialize(rule.prelude).strip() == "(prefers-reduced-motion: reduce)"
            for nested in css.parse_rule_list(rule.content, skip_comments=True,
                                              skip_whitespace=True):
                assert nested.type == "qualified-rule"
                selector = css.serialize(nested.prelude).strip()
                reduced[selector] = {
                    d.name: css.serialize(d.value).strip()
                    for d in declarations(css, nested)
                }
    assert reduced[".guide-action"] == {"transition": "none", "transform": "none"}
    focus = {d.name: css.serialize(d.value).strip()
             for d in normal[".guide-action:focus-visible"]}
    assert focus["outline"].startswith("3px solid")
    # All custom property uses resolve to tokens declared by the example.
    tokens = {d.name for d in normal[":root"]}
    for rule in normal.values():
        for d in rule:
            assert set(re.findall(r"var\((--[\w-]+)\)", css.serialize(d.value))) <= tokens


@pytest.mark.parametrize("viewport,root_size", [(360, 16), (768, 16), (1440, 16), (360, 32)])
def test_title_clamp_bounds_and_fallback(css_rules, viewport, root_size):
    css, rules = css_rules
    title = next(rule for rule in rules if rule.type == "qualified-rule"
                 and css.serialize(rule.prelude).strip() == ".guide-title")
    sizes = [d.value for d in declarations(css, title) if d.name == "font-size"]
    assert css.serialize(sizes[0]).strip() == "2rem"
    function = next(t for t in sizes[1] if t.type != "whitespace")
    assert function.type == "function" and function.name == "clamp"
    args = [t for t in function.arguments if t.type != "whitespace"]
    assert [t.type for t in args] == ["dimension", "literal", "dimension",
                                     "literal", "dimension", "literal", "dimension"]
    assert [t.value for t in args if t.type == "literal"] == [",", "+", ","]
    assert [args[i].unit for i in (0, 2, 4, 6)] == ["rem", "rem", "vw", "rem"]
    low, base, fluid, high = (args[i].value for i in (0, 2, 4, 6))
    value = max(low * root_size, min(base * root_size + fluid * viewport / 100,
                                    high * root_size))
    assert low * root_size <= value <= high * root_size
    assert value == pytest.approx({(360, 16): 32, (768, 16): 43.04,
                                   (1440, 16): 56, (360, 32): 64}[viewport, root_size])


def test_example_text_and_button_color_pairs_meet_contrast(css_rules):
    css, rules = css_rules
    root = next(rule for rule in rules if rule.type == "qualified-rule"
                and css.serialize(rule.prelude).strip() == ":root")
    palette = {d.name: css.serialize(d.value).strip() for d in declarations(css, root)}

    def luminance(color):
        assert re.fullmatch(r"#[0-9a-f]{6}", color)
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                  for v in channels]
        return sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722)))

    surface = luminance(palette["--guide-surface"])
    for token in ("--guide-ink", "--guide-muted", "--guide-action"):
        other = luminance(palette[token])
        ratio = (max(surface, other) + 0.05) / (min(surface, other) + 0.05)
        assert ratio >= 4.5, (token, ratio)
