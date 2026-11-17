"""Exercise theme boundaries through real HTML generation and CLI file writes."""

import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys

import pytest


LANDING = Path(__file__).resolve().parents[1] / (
    "skills/product-design/landing-page-generator/scripts/landing_page_scaffolder.py"
)
COLOR_FIELDS = ("primary_color", "secondary_color", "background", "text_color")
THEME_FIELDS = (*COLOR_FIELDS, "font")
BREAKOUTS = (
    "</style><script>/* harmless fixture */</script><style>",
    "</StYlE ><img src=fixture onerror='/* harmless fixture */'><style>",
)
UNSAFE_VALUES = (
    *BREAKOUTS,
    "#fff; color: red",
    "red !important",
    "red} body {display:none} /*",
    'Inter; src: url("https://fixture.invalid/font")',
    '@import "https://fixture.invalid/style"',
    "url(https://fixture.invalid/image)",
    "URL(javascript:fixture)",
    "expression(fixture)",
    "javascript:fixture",
    "var(--untrusted)",
    "attr(data-theme)",
    r"u\72l(https://fixture.invalid/image)",
    r"\3c /style\3e",
    "red/**/",
    "&lt;/style&gt;",
    "",
    "   ",
    None, False, 123, [], {},
)


@pytest.fixture(scope="module")
def landing():
    spec = importlib.util.spec_from_file_location("html_theme_boundaries", LANDING)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ParsedHTML(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.style_text = []
        self.in_style = False
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, attrs))
        self.in_style = tag == "style"

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.style_text.append(data)


@pytest.mark.parametrize("field", THEME_FIELDS)
@pytest.mark.parametrize("value", UNSAFE_VALUES)
def test_every_theme_field_rejects_unsafe_values(landing, field, value):
    with pytest.raises(ValueError, match=f"theme\\.{field}"):
        landing.generate_html({"theme": {field: value}})


@pytest.mark.parametrize("field", THEME_FIELDS)
@pytest.mark.parametrize("code", [*range(32), *range(127, 160), 0x200B, 0x2028, 0x2029, 0x202E, 0xFEFF])
def test_every_theme_field_rejects_controls_even_at_edges(landing, field, code):
    for value in (f"{chr(code)}red", f"red{chr(code)}", f"re{chr(code)}d"):
        with pytest.raises(ValueError, match=f"theme\\.{field}"):
            landing.generate_html({"theme": {field: value}})


@pytest.mark.parametrize("theme", [None, [], "red", 1, True])
def test_theme_must_be_an_object(landing, theme):
    with pytest.raises(ValueError, match="theme"):
        landing.generate_html({"theme": theme})


@pytest.mark.parametrize("field", COLOR_FIELDS)
@pytest.mark.parametrize("value", [
    "#abc", "#ABCD", "#123456", "#12345678", "blue", "RebeccaPurple",
    "transparent", "currentColor", " rgb(12, 34, 56) ", "rgba(12, 34, 56, 0.5)",
    "rgb(10%, 20%, 30%)", "rgba(10%, 20%, 30%, 50%)",
    "rgb(12 34 56 / 50%)", "RGB(12 34 56)", "rgba(12 34 56 / .5)",
    "hsl(240, 100%, 50%)", "hsla(240, 100%, 50%, .5)",
    "hsl(240deg 100% 50% / 50%)", "hsl(.5turn 50% 40%)",
    "hsl(-1.5rad 50% 40%)", "hsl(100grad 50% 40%)",
])
def test_normal_colors_preserve_html_structure(landing, field, value):
    baseline = ParsedHTML(landing.generate_html({}))
    parsed = ParsedHTML(landing.generate_html({"theme": {field: value}}))
    assert parsed.elements == baseline.elements
    assert all(tag != "script" for tag, _ in parsed.elements)
    if field != "secondary_color":  # Accepted reserved field is currently unused.
        assert value.strip() in "".join(parsed.style_text)


@pytest.mark.parametrize("value", [
    "Inter, system-ui, -apple-system, sans-serif", "Arial, sans-serif",
    '"Open Sans", sans-serif', "'Times New Roman', serif", "Roboto Mono, monospace",
    '"Noto Sans SC", "微软雅黑", sans-serif', "system-ui", "ui-sans-serif, sans-serif",
])
def test_normal_font_stacks_preserve_html_structure(landing, value):
    baseline = ParsedHTML(landing.generate_html({}))
    parsed = ParsedHTML(landing.generate_html({"theme": {"font": value}}))
    assert parsed.elements == baseline.elements
    assert all(tag != "script" for tag, _ in parsed.elements)
    assert f"font-family: {value};" in "".join(parsed.style_text)


@pytest.mark.parametrize("field", COLOR_FIELDS)
@pytest.mark.parametrize("value", [
    "#12", "#12345", "#ggg", "not-a-color", "rgb(1,2)", "rgb(1,2,3,4,5)",
    "hsl(1,2,3)", "linear-gradient(red, blue)", "red blue", "inherit",
])
def test_unsupported_color_syntax_is_rejected(landing, field, value):
    with pytest.raises(ValueError, match=f"theme\\.{field}"):
        landing.generate_html({"theme": {field: value}})


@pytest.mark.parametrize("value", [
    '"Unclosed', "Inter,,serif", "Inter,", "123Font", "'Inter' serif",
    "Inter:serif", "Inter/serif", "Inter!important",
])
def test_unsupported_font_syntax_is_rejected(landing, value):
    with pytest.raises(ValueError, match=r"theme\.font"):
        landing.generate_html({"theme": {"font": value}})


@pytest.mark.parametrize("field", THEME_FIELDS)
@pytest.mark.parametrize("payload", BREAKOUTS)
@pytest.mark.parametrize("existing_output", [False, True])
def test_real_cli_rejects_breakout_before_writing(landing, tmp_path, field, payload, existing_output):
    config = tmp_path / "config.json"
    output = tmp_path / "page.html"
    original = landing.generate_html({"brand": "Existing page"})
    config.write_text(json.dumps({"theme": {field: payload}}), encoding="utf-8")
    if existing_output:
        output.write_text(original, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(LANDING), str(config), "--format", "html", "--output", str(output)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert f"theme.{field}" in result.stderr
    assert not result.stdout
    if existing_output:
        actual = output.read_text(encoding="utf-8")
        assert actual == original
        parsed = ParsedHTML(actual)
        assert parsed.elements == ParsedHTML(original).elements
        assert all(tag != "script" for tag, _ in parsed.elements)
    else:
        assert not output.exists()


def test_real_cli_accepts_normal_theme(tmp_path):
    config = tmp_path / "config.json"
    output = tmp_path / "page.html"
    config.write_text(json.dumps({"theme": {
        "primary_color": "#2563eb", "secondary_color": "#1e40af",
        "background": "#ffffff", "text_color": "#1f2937",
        "font": "Inter, system-ui, -apple-system, sans-serif",
    }}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(LANDING), str(config), "--format", "html", "--output", str(output)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    parsed = ParsedHTML(output.read_text(encoding="utf-8"))
    assert sum(tag == "style" for tag, _ in parsed.elements) == 1
    assert all(tag != "script" for tag, _ in parsed.elements)
