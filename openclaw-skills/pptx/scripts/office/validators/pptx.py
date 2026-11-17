# Adapted from anthropics/skills: skills/pptx/scripts/office/validators/pptx.py
# Source commit: e4bb5d960d87126ff3b3a8af1a104b7db67560ba (Apache-2.0).
# SPDX-License-Identifier: Apache-2.0
# Local modifications Copyright (c) 2026 seaworld008.
# Local changes: closed dependencies, API compatibility, safe offline validation.
"""
Validator for PowerPoint presentation XML files against XSD schemas.
"""

import re
from pathlib import Path

try:
    from ..helpers import opc_target, rels_source_part, safe_extract
except ImportError:
    from helpers import opc_target, rels_source_part, safe_extract

from .base import BaseSchemaValidator, safe_parse



# Adapted from anthropics/skills: skills/pptx/scripts/office/helpers/pptx_theme.py
# Source commit: e4bb5d960d87126ff3b3a8af1a104b7db67560ba (Apache-2.0).
# SPDX-License-Identifier: Apache-2.0
# Local modifications Copyright (c) 2026 seaworld008.
# Local changes: closed dependencies, API compatibility, safe offline validation.
"""Find masters sharing a theme part in the way PowerPoint refuses to open.

Reports only; the fix is to move <p:notesMasterIdLst> back to directly after
<p:sldIdLst> in ppt/presentation.xml.
"""




import posixpath
import re
from typing import Mapping

try:
    from ..helpers import part_text
except ImportError:
    from helpers import part_text

THEME_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"

_MASTER_RE = re.compile(
    r"^ppt/(?P<group>slideMasters|notesMasters|handoutMasters)/"
    r"(?:slide|notes|handout)Master(?P<num>\d+)\.xml$"
)
_GROUP_ORDER = {"slideMasters": 0, "notesMasters": 1, "handoutMasters": 2}

_RELATIONSHIP_RE = re.compile(
    r"<Relationship\b[^>]*?(?:/>|>.*?</Relationship\s*>)", re.DOTALL
)


def _sort_key(name: str) -> tuple[int, int]:
    m = _MASTER_RE.match(name)
    assert m is not None
    return (_GROUP_ORDER[m.group("group")], int(m.group("num")))


def _rels_path(part: str) -> str:
    directory, base = posixpath.split(part)
    return f"{directory}/_rels/{base}.rels"


def _resolve(rels_path: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    part_dir = posixpath.dirname(posixpath.dirname(rels_path))
    return posixpath.normpath(posixpath.join(part_dir, target))


def _theme_rel(files: Mapping[str, bytes], master: str):
    rels_path = _rels_path(master)
    rels = files.get(rels_path)
    if rels is None:
        return None
    for element in _RELATIONSHIP_RE.findall(part_text(rels)):
        if f'Type="{THEME_REL_TYPE}"' not in element:
            continue
        target = re.search(r'\bTarget="([^"]+)"', element)
        if target is None:
            continue
        return rels_path, element, _resolve(rels_path, target.group(1))
    return None


def _masters(files: Mapping[str, bytes]) -> list[str]:
    return sorted((n for n in files if _MASTER_RE.match(n)), key=_sort_key)


_PRESENTATION = "ppt/presentation.xml"
_NOTES_MASTERS = "ppt/notesMasters/"
_IGNORABLE_RE = re.compile(r"<!--.*?-->|<\?.*?\?>", re.DOTALL)
_AFTER_SLDIDLST_RE = re.compile(
    r"<p:sldIdLst\b(?:[^>]*/>|[^>]*>.*?</p:sldIdLst\s*>)\s*(<[^>\s/]+)", re.DOTALL
)


def _notes_master_share_is_inert(files: Mapping[str, bytes]) -> bool:
    data = files.get(_PRESENTATION)
    if data is None:
        return False
    match = _AFTER_SLDIDLST_RE.search(_IGNORABLE_RE.sub("", part_text(data)))
    return match is not None and match.group(1) == "<p:notesMasterIdLst"


def _shares(files: Mapping[str, bytes]):
    owner: dict[str, str] = {}
    for master in _masters(files):
        found = _theme_rel(files, master)
        if found is None:
            continue
        rels_path, element, theme = found
        if theme not in files:
            continue
        if theme in owner:
            yield master, rels_path, element, theme, owner[theme]
        else:
            owner[theme] = master


def _is_inert(master: str, inert_notes: bool) -> bool:
    return inert_notes and master.startswith(_NOTES_MASTERS)


def find_shared_master_themes(files: Mapping[str, bytes]) -> list[str]:
    return [
        f"{master} shares {theme} with {first}"
        for master, _, _, theme, first in _shares(files)
    ]


def live_shared_master_themes(files: Mapping[str, bytes]) -> list[str]:
    inert_notes = _notes_master_share_is_inert(files)
    return [
        f"{master} shares {theme} with {first}"
        for master, _, _, theme, first in _shares(files)
        if not _is_inert(master, inert_notes)
    ]


# Adapted from anthropics/skills: skills/pptx/scripts/office/helpers/pptx_chart.py
# Source commit: e4bb5d960d87126ff3b3a8af1a104b7db67560ba (Apache-2.0).
# SPDX-License-Identifier: Apache-2.0
# Local modifications Copyright (c) 2026 seaworld008.
# Local changes: closed dependencies, API compatibility, safe offline validation.
"""Find chart XML that PowerPoint refuses or repairs.

Detection only: more than one repair is usually valid, and only the author knows
which was meant.
"""




import html
import re
from collections import Counter
from typing import Mapping

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

try:
    from ..helpers import part_text
except ImportError:
    from helpers import part_text


_CHART_PART_RE = re.compile(r"ppt/charts/chart\d+\.xml")

_GROUPING_RE = re.compile(r"""<c:grouping\b[^>]*?\bval=["'](\w+)["']""")
_DLBL_POS_RE = re.compile(r"""<c:dLblPos\b[^>]*?\bval=["'](\w+)["']""")

def _strip_ext_lst(text: str) -> str:
    return _strip_outermost(text, "c:extLst")


def _strip_outermost(text: str, name: str) -> str:
    out, cursor = [], 0
    for lo, hi in _outermost_spans(text, name):
        out.append(text[cursor:lo])
        cursor = hi
    out.append(text[cursor:])
    return "".join(out)

_BAR_GROUP_RE = re.compile(r"<c:(bar3DChart|barChart)\b[^>]*(?<!/)>.*?</c:\1\s*>", re.DOTALL)

STACKED_GROUPINGS = frozenset({"stacked", "percentStacked"})
ILLEGAL_ON_STACKED = frozenset({"outEnd"})
LEGAL_ON_STACKED = ("ctr", "inEnd", "inBase")


def _check_stacked_label_positions(part: str, xml: str) -> list[str]:
    problems: list[str] = []
    for match in _BAR_GROUP_RE.finditer(xml):
        block = _strip_ext_lst(match.group(0))
        group = match.group(1)

        grouping = _GROUPING_RE.search(block)
        if grouping is None or grouping.group(1) not in STACKED_GROUPINGS:
            continue

        bad = [p for p in _DLBL_POS_RE.findall(block) if p in ILLEGAL_ON_STACKED]
        for pos in sorted(set(bad)):
            problems.append(
                f'{part}: {bad.count(pos)} data label(s) use dLblPos="{pos}" on a '
                f"{grouping.group(1)} {group}; PowerPoint allows only "
                f"{', '.join(LEGAL_ON_STACKED)} there"
            )
    return problems



_ANY_CHART_GROUP_RE = re.compile(r"<c:(\w+Chart)\b[^>]*(?<!/)>.*?</c:\1\s*>", re.DOTALL)

_AXID_RE = re.compile(
    r"""\s*<c:axId\b[^>]*?\bval=["'](-?\d+)["']\s*(?:/>|>\s*</c:axId\s*>)"""
)

_AXIS_DECL_RE = re.compile(
    r"""<c:(catAx|valAx|serAx|dateAx)\b[^>]*(?<!/)>\s*<c:axId\b[^>]*?\bval=["'](-?\d+)["']"""
)

AXID_LIMIT = {
    "barChart": 2, "lineChart": 2, "areaChart": 2, "scatterChart": 2,
    "bubbleChart": 2, "radarChart": 2, "stockChart": 2,
    "bar3DChart": 3, "line3DChart": 3, "area3DChart": 3,
    "surfaceChart": 3, "surface3DChart": 3,
}

AXID_MINIMUM = {
    "barChart": 2, "lineChart": 2, "areaChart": 2, "scatterChart": 2,
    "bubbleChart": 2, "radarChart": 2, "stockChart": 2,
    "bar3DChart": 2, "area3DChart": 2, "surfaceChart": 2,
    "line3DChart": 3, "surface3DChart": 3,
}


def _declared_axes(xml: str) -> dict[str, list[str]]:
    axes: dict[str, list[str]] = {}
    for kind, axid in _AXIS_DECL_RE.findall(xml):
        axes.setdefault(kind, []).append(axid)
    return axes


def _canonical_ids(axes: dict[str, list[str]], limit: int) -> list[str] | None:
    category = axes.get("catAx", []) + axes.get("dateAx", [])
    value = axes.get("valAx", [])
    series = axes.get("serAx", [])
    if len(category) != 1 or len(value) != 1 or len(series) > 1:
        return None
    ids = [category[0], value[0]]
    if limit >= 3 and series:
        ids.append(series[0])
    return ids


def _undeclared_axes(kind: str, block: str, axes: dict[str, list[str]]) -> list[str] | None:
    if kind not in AXID_LIMIT:
        return None
    ids = _AXID_RE.findall(block)
    declared = {i for group in axes.values() for i in group}
    if len([i for i in ids if i in declared]) >= 2:
        return None
    return ids


def _check_chart_axis_references(part: str, xml: str) -> list[str]:
    axes = _declared_axes(xml)
    problems: list[str] = []
    declared = {i for group in axes.values() for i in group}
    for match in _ANY_CHART_GROUP_RE.finditer(xml):
        kind, block = match.group(1), match.group(0)
        ids = _undeclared_axes(kind, block, axes)
        if ids is None:
            continue
        if not ids:
            problems.append(
                f"{part}: <c:{kind}> declares no <c:axId> this part can resolve; a chart "
                f"group needs {AXID_MINIMUM[kind]}, and PowerPoint discards one with fewer"
            )
            continue
        dead = [i for i in ids if i not in declared]
        canonical = _canonical_ids(axes, AXID_LIMIT[kind])
        if canonical is not None and len(canonical) >= AXID_MINIMUM[kind]:
            hint = f"Fix: point them at the axes this part declares ({', '.join(canonical)})"
        else:
            hint = ("Fix: the part declares several axes of a kind -- declare the "
                    "secondary axes the series expects, or drop them")
        detail = (f"of which {', '.join(dead)} name no declared axis"
                  if dead else f"only {len(ids)} of which this part declares")
        problems.append(
            f"{part}: <c:{kind}> references axId {', '.join(ids)}, {detail}, "
            f"leaving fewer than two live axes; PowerPoint discards the chart. {hint}"
        )
    return problems


def _shown(value: str) -> str:
    return '"' + repr(value[:20])[1:-1] + '"'


DECIMAL_SETTINGS = (
    "crossesAt", "max", "min", "majorUnit", "minorUnit", "logBase",
    "forward", "backward", "intercept", "x", "y", "w", "h",
    "splitPos", "custUnit", "pictureStackUnit",
)
_DECIMAL_SETTING_RE = re.compile(
    rf"""<c:({"|".join(DECIMAL_SETTINGS)})\b[^<>]*?\bval=["']([^"'<>]*)["']"""
)
_DECIMAL_RE = re.compile(
    r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?"
    r"|[+-]?(inf|infinity|nan(\(\w*\))?|\u221e|1\.#(inf|qnan|snan|ind)\d*)",
    re.IGNORECASE,
)


def _check_decimal_settings(part: str, xml: str) -> list[str]:
    problems = []
    for name, raw in sorted(set(_DECIMAL_SETTING_RE.findall(_strip_ext_lst(xml)))):
        value = html.unescape(raw)
        if _DECIMAL_RE.fullmatch(value.strip()):
            continue
        fix = "Fix: write a plain number, or remove the element"
        if name == "crossesAt" and value.strip() == "autoZero":
            fix = ("Fix: leave valAxisCrossesAt: 0 out of the pptxgenjs options, the axis "
                   "crosses at zero anyway. In the XML, write "
                   '<c:crosses val="autoZero"/> or a number')
        problems.append(
            f"{part}: <c:{name} val={_shown(value)}> is not a number, and PowerPoint "
            f"will offer to repair the deck. {fix}"
        )
    return problems


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _drawn_series(root) -> list:
    found, to_visit = [], [root]
    while to_visit:
        for child in to_visit.pop():
            name = _local(child.tag)
            if name == "ser":
                found.append(child)
            elif name == "AlternateContent":
                to_visit.extend(child[:1])
            elif name != "extLst":
                to_visit.append(child)
    return found


def _check_series_order(part: str, xml: str) -> list[str]:
    try:
        root = ElementTree.fromstring(xml.encode("utf-8", "surrogateescape"))
    except (ElementTree.ParseError, DefusedXmlException, LookupError, ValueError):
        return []
    orders = Counter()
    for series in _drawn_series(root):
        own = [c.get("val", "") for c in series if _local(c.tag) == "order"]
        if own and own[0].isascii() and own[0].isdigit():
            orders[own[0]] += 1
    repeated = sorted((o for o, n in orders.items() if n > 1), key=lambda o: (len(o), o))
    if not repeated:
        return []
    return [
        f"{part}: two or more series share the <c:order> value {', '.join(o[:12] for o in repeated)}, "
        f"and PowerPoint will offer to repair the deck. Fix: number <c:order> "
        f"(and <c:idx>) 0, 1, 2... across every series in the chart, a combo "
        f"chart's line series carrying on from its bars"
    ]


PRESET_DASHES = frozenset({
    "solid", "dot", "dash", "lgDash", "dashDot", "lgDashDot", "lgDashDotDot",
    "sysDash", "sysDot", "sysDashDot", "sysDashDotDot",
})
_PRESET_DASH_RE = re.compile(r"""<a:prstDash\b[^<>]*?\bval=["']([^"'<>]*)["']""")


def _check_preset_dashes(part: str, xml: str) -> list[str]:
    values = {html.unescape(v) for v in _PRESET_DASH_RE.findall(_strip_ext_lst(xml))}
    return [
        f"{part}: <a:prstDash val={_shown(value)}> is not a dash style, and PowerPoint "
        f"will offer to repair the deck. Use one of {', '.join(sorted(PRESET_DASHES))}. "
        f"In pptxgenjs, lineDash takes one such word for the whole chart, not an array"
        for value in sorted(values)
        if value.strip() not in PRESET_DASHES
    ]


def _outermost_spans(text: str, name: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    depth = 0
    start = 0
    for match in re.finditer(rf"<(/?){name}\b[^<>]*?(/?)>", text):
        closing, self_closing = match.group(1), match.group(2)
        if self_closing:
            continue
        if closing:
            if depth:
                depth -= 1
                if depth == 0:
                    spans.append((start, match.end()))
        else:
            if depth == 0:
                start = match.start()
            depth += 1
    return spans


CHART_CHECKS = (
    _check_stacked_label_positions,
    _check_chart_axis_references,
    _check_decimal_settings,
    _check_series_order,
    _check_preset_dashes,
)


_COMMENT_OR_PI_RE = re.compile(r"<!--.*?(?:-->|\Z)|<\?(?!xml\s).*?(?:\?>|\Z)", re.DOTALL)


def find_chart_problems(files: Mapping[str, bytes]) -> list[str]:
    problems: list[str] = []
    for part in sorted(n for n in files if _CHART_PART_RE.fullmatch(n)):
        xml = _strip_outermost(_COMMENT_OR_PI_RE.sub("", part_text(files[part])), "mc:Fallback")
        for check in CHART_CHECKS:
            problems.extend(check(part, xml))
    return problems


# Adapted from anthropics/skills: skills/pptx/scripts/office/helpers/pptx_slide.py
# Source commit: e4bb5d960d87126ff3b3a8af1a104b7db67560ba (Apache-2.0).
# SPDX-License-Identifier: Apache-2.0
# Local modifications Copyright (c) 2026 seaworld008.
# Local changes: closed dependencies, API compatibility, safe offline validation.
"""Find the slide-XML defects known or predicted to make PowerPoint refuse or repair the file.

Schema errors are picked by a denylist over lxml's messages, so an unrecognised
error class is a miss rather than a false alarm. Animations that name a shape
the slide no longer has are found by reading the part.
"""




import re

SLIDE_PART_RE = re.compile(
    r"ppt/(slides|slideLayouts|slideMasters|notesSlides|notesMasters|handoutMasters)"
    r"/[^/]+\.xml"
)

FATAL_SLIDE_ERRORS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\}tableStyleId': This element is not expected"),
        "two <a:tableStyleId> in one <a:tblPr> (the schema allows one)",
    ),
    (
        re.compile(r"\}srgbClr', attribute 'val'"),
        "a colour that is not six hex digits",
    ),
    (
        re.compile(r"\}txBody': Missing child element"),
        "a <p:txBody> with no children",
    ),
    (
        re.compile(r"\}miter', attribute 'lim'"),
        'a line join with lim="NaN"',
    ),
    (
        re.compile(r"\}uLnTx': This element is not expected"),
        "<a:uLnTx> in a position the schema forbids",
    ),
    (
        re.compile(r"\}overrideClrMapping': This element is not expected"),
        "<p:overrideClrMapping> in a position the schema forbids",
    ),
    (
        re.compile(r"\}nvGrpSpPr': Missing child element"),
        "a <p:nvGrpSpPr> with no children",
    ),
    (
        re.compile(r"\}(?:off|ext|chOff|chExt)', attribute '\w+': '-?(?:Infinity|NaN)'"),
        "a position or size that is not a number (check the x, y, w, h you worked out)",
    ),
    (
        re.compile(r"\}prstDash', attribute 'val'"),
        "an unknown line dash style (for line.dashType try dash, sysDash or solid)",
    ),
)


def is_schema_verdict(error: str) -> bool:
    return error.startswith("Element ")


_PML = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"

_NAMES_A_SHAPE = frozenset({f"{_PML}spTgt", f"{_PML}bldP", f"{_PML}bldGraphic"})


def _shape_id(value: str | None) -> int | str | None:
    text = (value or "").strip()
    if text.isascii() and text.isdigit() and len(text) <= 18:
        return int(text)
    return text or None


def stranded_animation_targets(root) -> list[str]:
    timing = root.find(f"{_PML}timing")
    if timing is None:
        timing = root.find(f"{_MC}AlternateContent/{_MC}Choice/{_PML}timing")
    if timing is None:
        return []

    on_slide = {_shape_id(e.get("id")) for e in root.iter("{*}cNvPr")}
    named = {_shape_id(e.get("spid")) for e in timing.iter(*_NAMES_A_SHAPE)} - {None}
    stranded = named - on_slide
    return [
        f"<p:timing> animates shape id {spid if isinstance(spid, int) else repr(spid[:16])}, which is gone, so PowerPoint will "
        f"offer to repair the deck. Fix: delete the slide's whole <p:timing> element "
        f"(the slide loses its animations), or put the shape back"
        for spid in sorted(stranded, key=str)
    ]


def fatal_slide_errors(errors: set[str]) -> list[str]:
    out = []
    for error in sorted(errors):
        for pattern, meaning in FATAL_SLIDE_ERRORS:
            if pattern.search(error):
                out.append(f"{meaning}: {error}")
                break
    return out


class PPTXSchemaValidator(BaseSchemaValidator):

    PRESENTATIONML_NAMESPACE = (
        "http://schemas.openxmlformats.org/presentationml/2006/main"
    )

    ELEMENT_RELATIONSHIP_TYPES = {
        "sldid": "slide",
        "sldmasterid": "slidemaster",
        "notesmasterid": "notesmaster",
        "sldlayoutid": "slidelayout",
        "themeid": "theme",
        "tablestyleid": "tablestyles",
    }

    def validate(self):
        if not self.validate_xml():
            return False

        all_valid = True
        if not self.validate_namespaces():
            all_valid = False

        if not self.validate_unique_ids():
            all_valid = False

        if not self.validate_uuid_ids():
            all_valid = False

        if not self.validate_file_references():
            all_valid = False

        if not self.validate_slide_layout_ids():
            all_valid = False

        if not self.validate_content_types():
            all_valid = False

        if not self.validate_against_xsd():
            all_valid = False

        if not self.validate_notes_slide_references():
            all_valid = False

        if not self.validate_all_relationship_ids():
            all_valid = False

        if not self.validate_no_duplicate_slide_layouts():
            all_valid = False

        if not self.validate_master_theme_uniqueness():
            all_valid = False

        if not self.validate_tags():
            all_valid = False

        if not self.validate_charts():
            all_valid = False

        if not self.validate_slides():
            all_valid = False

        return all_valid

    def _package_map(self) -> dict:
        wanted = []
        wanted += list(self.unpacked_dir.glob("[[]Content_Types[]].xml"))
        wanted += list(self.unpacked_dir.glob("ppt/presentation.xml"))
        wanted += list(self.unpacked_dir.glob("ppt/theme/*.xml"))
        wanted += list(self.unpacked_dir.glob("ppt/theme/_rels/*.rels"))
        wanted += list(self.unpacked_dir.glob("ppt/charts/chart*.xml"))
        for group in ("slideMasters", "notesMasters", "handoutMasters"):
            wanted += list(self.unpacked_dir.glob(f"ppt/{group}/*.xml"))
            wanted += list(self.unpacked_dir.glob(f"ppt/{group}/_rels/*.rels"))
        return {
            p.relative_to(self.unpacked_dir).as_posix(): p.read_bytes()
            for p in wanted
            if p.is_file()
        }

    @staticmethod
    def _print_line(text: str, limit: int) -> None:
        try:
            from ..helpers import one_line
        except ImportError:
            from helpers import one_line

        print(one_line(text, limit))

    def _listed_slides(self) -> set[str] | None:
        import lxml.etree

        try:
            from ..helpers import SLIDE_REL_TYPE
        except ImportError:
            from helpers import SLIDE_REL_TYPE

        r_id = f"{{{self.OFFICE_RELATIONSHIPS_NAMESPACE}}}id"
        try:
            pres = safe_parse(str(self.unpacked_dir / "ppt" / "presentation.xml"))
            rels = safe_parse(str(self.unpacked_dir / "ppt" / "_rels" / "presentation.xml.rels"))
            listed = {e.get(r_id) for e in pres.iter(f"{{{self.PRESENTATIONML_NAMESPACE}}}sldId")}
            return {
                opc_target(rel.get("Target", ""), "ppt/presentation.xml", rel.get("TargetMode", ""))
                for rel in rels.getroot()
                if rel.get("Id") in listed and rel.get("Type") == SLIDE_REL_TYPE
            }
        except (OSError, ValueError, lxml.etree.XMLSyntaxError):
            return None

    def validate_master_theme_uniqueness(self):

        shared = live_shared_master_themes(self._package_map())
        if shared:
            print(f"FAILED - Found {len(shared)} master(s) sharing a theme part:")
            for message in shared:
                self._print_line(f"  {message}", 300)
            if any(m.startswith(_NOTES_MASTERS) for m in shared):
                print("  Fix: in ppt/presentation.xml, move <p:notesMasterIdLst> back to "
                      "directly after <p:sldIdLst>. PowerPoint reads that happily.")
            else:
                print("  Fix: give each master its own theme part.")
            return False

        if self.verbose:
            print("PASSED - No master shares a theme part in a way PowerPoint refuses")
        return True

    def validate_tags(self):
        from collections import Counter

        import lxml.etree

        ns = {"p": self.PRESENTATIONML_NAMESPACE, "mc": self.MC_NAMESPACE}
        r_id = f"{{{self.OFFICE_RELATIONSHIPS_NAMESPACE}}}id"
        errors = []
        owners: dict[str, list[str]] = {}
        listed = self._listed_slides()

        for slide in sorted(self.unpacked_dir.glob("ppt/slides/*.xml")):
            relative = slide.relative_to(self.unpacked_dir).as_posix()
            if listed is not None and relative not in listed:
                continue
            try:
                root = safe_parse(str(slide)).getroot()
                named = [t.get(r_id) for t in root.xpath(
                    ".//p:tags[not(ancestor::mc:Fallback) and not(ancestor::mc:Choice[preceding-sibling::mc:Choice])]",
                    namespaces=ns)]
                rels_file = slide.parent / "_rels" / f"{slide.name}.rels"
                targets = {
                    rel.get("Id"): opc_target(rel.get("Target", ""), relative, rel.get("TargetMode", ""))
                    for rel in safe_parse(str(rels_file)).getroot()
                    if rel.get("Type", "").endswith("/relationships/tags")
                } if rels_file.is_file() else {}
            except (lxml.etree.XMLSyntaxError, ValueError):
                continue
            for rid, count in sorted(Counter(r for r in named if r).items()):
                if count > 1:
                    errors.append(
                        f"  {relative[:80]}: {count} <p:tags> elements name the tags relationship "
                        f"{rid!r:.20}. Fix: a copied shape kept its <p:custDataLst>; delete that "
                        f"from the copy, or give it a tags part and relationship of its own"
                    )
                if targets.get(rid):
                    owners.setdefault(targets[rid], []).append(relative)

        for part, slides in sorted(owners.items()):
            if len(slides) > 1:
                named_from = sorted(set(slides))
                more = f" and {len(named_from) - 3} more" if len(named_from) > 3 else ""
                errors.append(
                    f"  {part[:80]}: {len(slides)} tags relationships name it, from "
                    f"{', '.join(s[:60] for s in named_from[:3])}{more}. Fix: copy the part under a new name, add "
                    f"its Override to [Content_Types].xml and point every relationship but one at a copy of its own "
                    f"(add_slide.py does this when it duplicates a slide)"
                )

        if errors:
            print(f"FAILED - Found {len(errors)} tags part(s) with more than one owner; PowerPoint offers to repair the deck:")
            for error in errors:
                self._print_line(error, 700)
            return False
        if self.verbose:
            print("PASSED - Every tags part has one owner")
        return True

    def validate_charts(self):

        problems = find_chart_problems(self._package_map())
        if problems:
            print(f"FAILED - Found {len(problems)} chart problem(s) PowerPoint rejects:")
            for message in problems:
                self._print_line(f"  {message}", 600)
            return False

        if self.verbose:
            print("PASSED - Charts satisfy the constraints PowerPoint enforces")
        return True

    def _original_slide_defects(self, schema) -> set[str]:
        import tempfile
        import zipfile


        if self.original_file is None:
            return set()

        found: set[str] = set()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            try:
                with zipfile.ZipFile(self.original_file, "r") as zf:
                    safe_extract(zf, temp_path)
            except (zipfile.BadZipFile, ValueError, OSError):
                return set()

            for part in sorted(temp_path.rglob("*.xml")):
                relative = part.relative_to(temp_path).as_posix()
                if not SLIDE_PART_RE.fullmatch(relative):
                    continue
                ok, errors = self._validate_single_file_xsd(
                    part.resolve(), temp_path.resolve(), schema_path=schema
                )
                if ok is None or ok or not errors:
                    continue
                found |= set(fatal_slide_errors(set(errors)))
        return found

    def validate_slides(self):
        import lxml.etree


        schema = self.schemas_dir / self.SCHEMA_MAPPINGS["ppt"]
        inherited = self._original_slide_defects(schema)
        listed = self._listed_slides()
        problems: list[str] = []
        broken: list[str] = []

        for xml_file in self.xml_files:
            relative = xml_file.relative_to(self.unpacked_dir).as_posix()
            if not SLIDE_PART_RE.fullmatch(relative):
                continue
            unlisted = relative.startswith("ppt/slides/") and listed is not None and relative not in listed
            try:
                root = safe_parse(str(xml_file)).getroot()
                stranded = [] if unlisted else stranded_animation_targets(root)
            except lxml.etree.XMLSyntaxError:
                stranded = []
            problems.extend(f"{relative}: {m}" for m in stranded)

            ok, errors = self._validate_single_file_xsd(
                xml_file.resolve(), self.unpacked_dir.resolve(), schema_path=schema
            )
            if ok is None or not errors:
                continue

            unreadable = [f"{relative}: {e}" for e in errors if not is_schema_verdict(e)]
            if unreadable:
                broken.extend(unreadable)
                continue
            if ok:
                continue

            for message in fatal_slide_errors(set(errors)):
                if message in inherited:
                    continue
                problems.append(f"{relative}: {message}")

        if broken:
            print(f"FAILED - Could not check {len(broken)} slide part(s):")
            for message in sorted(broken):
                self._print_line(f"  {message}", 240)

        if problems:
            print(f"FAILED - Found {len(problems)} slide problem(s) PowerPoint rejects:")
            for message in sorted(problems):
                self._print_line(f"  {message}", 240)

        if broken or problems:
            return False

        if self.verbose:
            print("PASSED - Slide XML has none of the defects PowerPoint refuses")
        return True

    def _get_schema_path(self, xml_file):
        if xml_file.parent.name == "charts" and xml_file.name.startswith("chart"):
            return None
        if xml_file.parent.name == "ppt" and xml_file.suffix == ".xml":
            import lxml.etree

            try:
                root = safe_parse(str(xml_file)).getroot()
            except (lxml.etree.XMLSyntaxError, OSError):
                root = None
            if root is not None and (lxml.etree.QName(root).namespace or "").startswith(
                "http://schemas.microsoft.com/office/"
            ):
                return None
        return super()._get_schema_path(xml_file)

    def _preprocess_for_schema(self, xml_doc, relative_path):
        if relative_path.as_posix() != "ppt/presentation.xml":
            return xml_doc

        root = xml_doc.getroot()
        ns = f"{{{self.PRESENTATIONML_NAMESPACE}}}"
        notes = root.find(f"{ns}notesMasterIdLst")
        slides = root.find(f"{ns}sldIdLst")
        if notes is None or slides is None:
            return xml_doc

        children = list(root)
        if children.index(notes) < children.index(slides):
            return xml_doc

        root.remove(notes)
        root.insert(list(root).index(slides), notes)
        return xml_doc

    def validate_uuid_ids(self):
        import lxml.etree

        errors = []
        uuid_pattern = re.compile(
            r"^[\{\(]?[0-9A-Fa-f]{8}-?[0-9A-Fa-f]{4}-?[0-9A-Fa-f]{4}-?[0-9A-Fa-f]{4}-?[0-9A-Fa-f]{12}[\}\)]?$"
        )

        for xml_file in self.xml_files:
            try:
                root = safe_parse(str(xml_file)).getroot()

                for elem in root.iter():
                    for attr, value in elem.attrib.items():
                        attr_name = attr.split("}")[-1].lower()
                        if attr_name == "id" or attr_name.endswith("id"):
                            if self._looks_like_uuid(value):
                                if not uuid_pattern.match(value):
                                    errors.append(
                                        f"  {xml_file.relative_to(self.unpacked_dir)}: "
                                        f"Line {elem.sourceline}: ID '{value}' appears to be a UUID but contains invalid hex characters"
                                    )

            except (lxml.etree.XMLSyntaxError, Exception) as e:
                errors.append(
                    f"  {xml_file.relative_to(self.unpacked_dir)}: Error: {e}"
                )

        if errors:
            print(f"FAILED - Found {len(errors)} UUID ID validation errors:")
            for error in errors:
                self._print_line(error, 300)
            return False
        else:
            if self.verbose:
                print("PASSED - All UUID-like IDs contain valid hex values")
            return True

    def _looks_like_uuid(self, value):
        clean_value = value.strip("{}()").replace("-", "")
        return len(clean_value) == 32 and all(c.isalnum() for c in clean_value)

    def validate_slide_layout_ids(self):
        import lxml.etree

        errors = []

        slide_masters = list(self.unpacked_dir.glob("ppt/slideMasters/*.xml"))

        if not slide_masters:
            if self.verbose:
                print("PASSED - No slide masters found")
            return True

        for slide_master in slide_masters:
            try:
                root = safe_parse(str(slide_master)).getroot()

                rels_file = slide_master.parent / "_rels" / f"{slide_master.name}.rels"

                if not rels_file.exists():
                    errors.append(
                        f"  {slide_master.relative_to(self.unpacked_dir)}: "
                        f"Missing relationships file: {rels_file.relative_to(self.unpacked_dir)}"
                    )
                    continue

                rels_root = safe_parse(str(rels_file)).getroot()

                valid_layout_rids = set()
                for rel in rels_root.findall(
                    f".//{{{self.PACKAGE_RELATIONSHIPS_NAMESPACE}}}Relationship"
                ):
                    rel_type = rel.get("Type", "")
                    if "slideLayout" in rel_type:
                        valid_layout_rids.add(rel.get("Id"))

                for sld_layout_id in root.findall(
                    f".//{{{self.PRESENTATIONML_NAMESPACE}}}sldLayoutId"
                ):
                    r_id = sld_layout_id.get(
                        f"{{{self.OFFICE_RELATIONSHIPS_NAMESPACE}}}id"
                    )
                    layout_id = sld_layout_id.get("id")

                    if r_id and r_id not in valid_layout_rids:
                        errors.append(
                            f"  {slide_master.relative_to(self.unpacked_dir)}: "
                            f"Line {sld_layout_id.sourceline}: sldLayoutId with id='{layout_id}' "
                            f"references r:id='{r_id}' which is not found in slide layout relationships"
                        )

            except (lxml.etree.XMLSyntaxError, Exception) as e:
                errors.append(
                    f"  {slide_master.relative_to(self.unpacked_dir)}: Error: {e}"
                )

        if errors:
            print(f"FAILED - Found {len(errors)} slide layout ID validation errors:")
            for error in errors:
                self._print_line(error, 300)
            print(
                "Remove invalid references or add missing slide layouts to the relationships file."
            )
            return False
        else:
            if self.verbose:
                print("PASSED - All slide layout IDs reference valid slide layouts")
            return True

    def validate_no_duplicate_slide_layouts(self):
        import lxml.etree

        errors = []
        slide_rels_files = list(self.unpacked_dir.glob("ppt/slides/_rels/*.xml.rels"))

        for rels_file in slide_rels_files:
            try:
                root = safe_parse(str(rels_file)).getroot()

                layout_rels = [
                    rel
                    for rel in root.findall(
                        f".//{{{self.PACKAGE_RELATIONSHIPS_NAMESPACE}}}Relationship"
                    )
                    if "slideLayout" in rel.get("Type", "")
                ]

                if len(layout_rels) > 1:
                    errors.append(
                        f"  {rels_file.relative_to(self.unpacked_dir)}: has {len(layout_rels)} slideLayout references"
                    )

            except Exception as e:
                errors.append(
                    f"  {rels_file.relative_to(self.unpacked_dir)}: Error: {e}"
                )

        if errors:
            print("FAILED - Found slides with duplicate slideLayout references:")
            for error in errors:
                self._print_line(error, 300)
            return False
        else:
            if self.verbose:
                print("PASSED - All slides have exactly one slideLayout reference")
            return True

    def validate_notes_slide_references(self):
        import lxml.etree

        errors = []
        notes_slide_references = {}

        slide_rels_files = list(self.unpacked_dir.glob("ppt/slides/_rels/*.xml.rels"))

        if not slide_rels_files:
            if self.verbose:
                print("PASSED - No slide relationship files found")
            return True

        for rels_file in slide_rels_files:
            try:
                root = safe_parse(str(rels_file)).getroot()

                for rel in root.findall(
                    f".//{{{self.PACKAGE_RELATIONSHIPS_NAMESPACE}}}Relationship"
                ):
                    rel_type = rel.get("Type", "")
                    if "notesSlide" in rel_type:
                        part = opc_target(
                            rel.get("Target", ""),
                            rels_source_part(rels_file, self.unpacked_dir),
                            rel.get("TargetMode", ""),
                        )
                        if part:
                            slide_name = rels_file.stem.replace(
                                ".xml", ""
                            )

                            notes_slide_references.setdefault(part, []).append(
                                (slide_name, rels_file)
                            )

            except (lxml.etree.XMLSyntaxError, Exception) as e:
                errors.append(
                    f"  {rels_file.relative_to(self.unpacked_dir)}: Error: {e}"
                )

        for target, references in notes_slide_references.items():
            if len(references) > 1:
                slide_names = [ref[0] for ref in references]
                errors.append(
                    f"  Notes slide '{target}' is referenced by multiple slides: {', '.join(slide_names)}"
                )
                for slide_name, rels_file in references:
                    errors.append(f"    - {rels_file.relative_to(self.unpacked_dir)}")

        if errors:
            print(
                f"FAILED - Found {len([e for e in errors if not e.startswith('    ')])} notes slide reference validation errors:"
            )
            for error in errors:
                self._print_line(error, 300)
            print("Each slide may optionally have its own slide file.")
            return False
        else:
            if self.verbose:
                print("PASSED - All notes slide references are unique")
            return True


if __name__ == "__main__":
    raise RuntimeError("This module should not be run directly.")
