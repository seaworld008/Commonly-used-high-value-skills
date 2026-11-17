"""Regression coverage for landing-page data boundaries and token CLI exports."""

import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "skills/product-design/landing-page-generator/scripts/landing_page_scaffolder.py"
TOKENS = ROOT / "skills/product-design/ui-design-system/scripts/design_token_generator.py"
STRING_LITERAL = r'"(?:[^"\\\r\n]|\\.)*"'
JSX_STRING = re.compile(r'\{(' + STRING_LITERAL + r')\}')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def landing():
    return load_module("landing_generator_boundaries", LANDING)


@pytest.fixture
def page():
    return {
        "brand": "Brand",
        "nav_links": [{"text": "Features", "url": "#features"}],
        "nav_cta": {"text": "Start", "url": "/start"},
        "hero": {
            "headline": "Welcome", "subheadline": "Hello",
            "primary_cta": {"text": "Start", "url": "/start"},
            "secondary_cta": {"text": "Learn", "url": "/learn"},
        },
        "features": {
            "title": "Features", "subtitle": "Details",
            "items": [{"icon": "*", "title": "Fast", "description": "Works"}],
        },
        "testimonials": {
            "title": "Reviews", "items": [
                {"quote": "Great", "name": "A", "title": "Lead", "company": "Co"},
            ],
        },
        "pricing": {
            "title": "Pricing", "plans": [{
                "name": "Pro", "price": 29, "description": "For teams",
                "features": ["Unlimited"], "cta_text": "Buy", "cta_url": "/buy",
            }],
        },
        "cta": {"headline": "Ready?", "subheadline": "Try it", "text": "Go", "url": "/go"},
        "footer_text": "Copyright", "title": "Page", "meta_description": "Description",
    }


TEXT_PATHS = [
    ("brand",), ("footer_text",),
    ("nav_links", 0, "text"), ("nav_cta", "text"),
    ("hero", "headline"), ("hero", "subheadline"),
    ("hero", "primary_cta", "text"), ("hero", "secondary_cta", "text"),
    ("features", "title"), ("features", "subtitle"),
    *[("features", "items", 0, key) for key in ("icon", "title", "description")],
    ("testimonials", "title"),
    *[("testimonials", "items", 0, key) for key in ("quote", "name", "title", "company")],
    ("pricing", "title"),
    *[("pricing", "plans", 0, key) for key in ("name", "price", "description", "cta_text")],
    ("pricing", "plans", 0, "features", 0),
    *[("cta", key) for key in ("headline", "subheadline", "text")],
]
LINK_PATHS = [
    ("nav_links", 0, "url"), ("nav_cta", "url"),
    ("hero", "primary_cta", "url"), ("hero", "secondary_cta", "url"),
    ("pricing", "plans", 0, "cta_url"), ("cta", "url"),
]
PAYLOAD = '合法 {team} < > &copy; " \' \\ \n\r\t\u2028\u2029 </title><script>alert(1)</script>{(() => {throw 1})()}'


def set_value(config, path, value):
    for key in path[:-1]:
        config = config[key]
    config[path[-1]] = value


def test_all_tsx_text_is_a_round_trippable_string_expression(landing, page):
    expected = [f"field-{index}: {PAYLOAD}" for index in range(len(TEXT_PATHS))]
    for path, value in zip(TEXT_PATHS, expected):
        set_value(page, path, value)
    output = landing.generate_tsx(page)
    # The full value must be a single JSON/JS string inside JSX braces. In
    # particular, payload braces and JSX tags must not become source code.
    literals = [json.loads(match[1]) for match in JSX_STRING.finditer(output)]
    for value in expected:
        assert literals.count(value) == 1
    without_literals = JSX_STRING.sub("{STRING}", output)
    assert "field-" not in without_literals
    assert "<script>" not in without_literals
    assert "throw 1" not in without_literals


def test_tsx_metadata_uses_string_literals_and_style_comment_is_bounded(landing, page):
    page.update(title=PAYLOAD, meta_description=PAYLOAD, design_style="custom\nthrow 123;")
    output = landing.generate_tsx(page)
    entries = re.findall(r'^\s*(?:title|description): (' + STRING_LITERAL + r'),$', output, re.M)
    assert [json.loads(entry) for entry in entries] == [PAYLOAD] * 4
    assert "// Design style: clean-minimal\n" in output
    assert "throw 123" not in output


def test_default_footer_brand_is_also_string_data(landing):
    output = landing.generate_tsx({"brand": PAYLOAD})
    literals = [json.loads(match[1]) for match in JSX_STRING.finditer(output)]
    assert PAYLOAD in literals
    assert any(value.endswith(f" {PAYLOAD}. All rights reserved.") for value in literals)


class ParsedHTML(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


def test_html_text_and_metadata_remain_data_after_parsing(landing, page):
    for path in [*TEXT_PATHS, ("title",), ("meta_description",)]:
        set_value(page, path, PAYLOAD)
    parsed = ParsedHTML(landing.generate_html(page))
    assert not any(tag == "script" for tag, _ in parsed.tags)
    assert "".join(parsed.text).count(PAYLOAD) == len(TEXT_PATHS) + 1
    assert {"name": "description", "content": PAYLOAD} in [attrs for _, attrs in parsed.tags]


@pytest.mark.parametrize("url", [
    "https://example.com/search?q={team}&next=\"<tag>\"&literal=&copy;",
    "http://example.com", "HTTPS://example.com/path", "//example.com/path",
    "/docs/{team}", "./docs", "../pricing", "docs/page", "?q={team}",
    "#section-{team}", "", "mailto:hello@example.com", "tel:+123456", "ftp://example.com/file",
])
def test_accepted_links_round_trip_in_every_link_slot(landing, page, url):
    for path in LINK_PATHS:
        set_value(page, path, url)
    tsx = landing.generate_tsx(page)
    hrefs = re.findall(r'href=\{(' + STRING_LITERAL + r')\}', tsx)
    assert [json.loads(value) for value in hrefs] == [url] * len(LINK_PATHS)
    parsed = ParsedHTML(landing.generate_html(page))
    anchors = [attrs for tag, attrs in parsed.tags if tag == "a"]
    assert anchors[0]["href"] == "#"  # Static brand link.
    assert [attrs["href"] for attrs in anchors[1:]] == [url] * len(LINK_PATHS)
    assert all(set(attrs) <= {"href", "class"} for attrs in anchors)


@pytest.mark.parametrize("format", ["tsx", "html"])
@pytest.mark.parametrize("path", LINK_PATHS)
@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "  JaVaScRiPt:alert(1) ",
    "data:text/html,<script>alert(1)</script>", "DATA:image/svg+xml,<svg/>",
    "vbscript:msgbox(1)", "file:///etc/passwd", "java\tscript:alert(1)",
    "https://example.com/\npath", "/path\x00tail", "#anchor\x7f", "/path\x85",
])
def test_unsafe_links_are_rejected_in_every_output_slot(landing, page, format, path, url):
    set_value(page, path, url)
    with pytest.raises(ValueError, match="control characters|URL scheme"):
        getattr(landing, f"generate_{format}")(page)


@pytest.mark.parametrize("code", [*range(32), *range(127, 160)])
def test_every_control_character_is_rejected(landing, code):
    with pytest.raises(ValueError, match="control characters"):
        landing.validate_href(f"https://example.com/{chr(code)}path")


@pytest.mark.parametrize("format", ["tsx", "html"])
@pytest.mark.parametrize("existing_output", [False, True])
def test_cli_rejects_unsafe_link_before_creating_or_overwriting_output(tmp_path, format, existing_output):
    config = tmp_path / "config.json"
    output = tmp_path / f"page.{format}"
    config.write_text(json.dumps({"nav_cta": {"url": "javascript:alert(1)"}}), encoding="utf-8")
    if existing_output:
        output.write_text("keep existing page", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(LANDING), str(config), "--format", format, "--output", str(output)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "Unsupported link URL scheme" in result.stderr
    assert not result.stdout
    if existing_output:
        assert output.read_text(encoding="utf-8") == "keep existing page"
    else:
        assert not output.exists()


@pytest.mark.parametrize("style", ["modern", "classic", "playful"])
def test_real_cli_scss_exports_nested_tokens(style):
    result = subprocess.run(
        [sys.executable, str(TOKENS), "#123456", style, "scss"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    declarations = dict(re.findall(r'^\$([\w-]+): (.*);$', result.stdout, re.M))
    assert declarations
    assert len(declarations) == len(result.stdout.splitlines())
    assert declarations["meta-version"] == '"1.0.0"'
    assert declarations["meta-style"] == json.dumps(style)
    assert declarations["colors-primary-DEFAULT"] == "#123456"
    assert declarations["typography-fontWeight-bold"] == "700"
    assert declarations["spacing-2"] == "8px"
    assert declarations["breakpoints-md"] == "768px"
    assert declarations["z-index-hide"] == "-1"
    assert declarations["animation-keyframes-fadeIn-from-opacity"] == "0"
    assert declarations["animation-keyframes-slideUp-from-transform"] == "translateY(10px)"
    assert declarations["borders-radius-lg"] == {"modern": "16px", "classic": "8px", "playful": "24px"}[style]
