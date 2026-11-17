# SPDX-License-Identifier: Apache-2.0
# Adapted from anthropics/skills, skills/docx/scripts/merge_runs.py
# Commit: e4bb5d960d87126ff3b3a8af1a104b7db67560ba
# The upstream file contains no copyright header; its skill LICENSE.txt is Apache-2.0.
# Local modifications Copyright (c) 2026 seaworld008:
# retain revision/proofing metadata, require text-only runs and identical attributes,
# stop at fields/revisions/unknown nodes, retain text-node whitespace, atomic writes.
"""Conservatively merge directly adjacent, identically formatted Word runs."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "_office_merge_io", Path(__file__).resolve().parents[1] / "pack.py")
_io = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_io)

WORDML_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_SPACE = " \t\r\n"


def _is_element(node, tag):
    return (node.nodeType == node.ELEMENT_NODE
            and node.namespaceURI == WORDML_NS
            and node.localName == tag.split(":")[-1])


def _find_elements(root, tag):
    return [node for node in traverse(root) if _is_element(node, tag)]


def traverse(node):
    yield node
    for child in node.childNodes:
        yield from traverse(child)


def _get_child(parent, tag):
    return next(iter(_get_children(parent, tag)), None)


def _get_children(parent, tag):
    return [child for child in parent.childNodes if _is_element(child, tag)]


def _is_adjacent(elem1, elem2):
    node = elem1.nextSibling
    while node is not None:
        if node is elem2:
            return True
        if node.nodeType != node.TEXT_NODE or node.data.strip(XML_SPACE):
            return False
        node = node.nextSibling
    return False


def _remove_elements(root, tag):
    """Explicit utility only; the merge workflow never removes metadata."""
    for elem in _find_elements(root, tag):
        if elem.parentNode:
            elem.parentNode.removeChild(elem)


def _strip_run_rsid_attrs(root):
    """Explicit metadata cleanup utility; never invoked by merge_runs."""
    count = 0
    for run in _find_elements(root, "r"):
        for attr in list(run.attributes.values()):
            if attr.namespaceURI == WORDML_NS and attr.localName.startswith("rsid"):
                run.removeAttributeNode(attr)
                count += 1
    return count


def _first_child_run(container):
    return next((child for child in container.childNodes if _is_run(child)), None)


def _next_element_sibling(node):
    sibling = node.nextSibling
    while sibling is not None:
        if sibling.nodeType == sibling.ELEMENT_NODE:
            return sibling
        if sibling.nodeType != sibling.TEXT_NODE or sibling.data.strip(XML_SPACE):
            return None
        sibling = sibling.nextSibling
    return None


def _next_sibling_run(node):
    sibling = node.nextSibling
    while sibling is not None:
        if _is_run(sibling):
            return sibling
        sibling = sibling.nextSibling
    return None


def _is_run(node):
    return _is_element(node, "r")


def _attributes(node):
    return {(a.namespaceURI, a.localName or a.name): a.value
            for a in node.attributes.values()}


def _text_only(run):
    elements = [n for n in run.childNodes if n.nodeType == n.ELEMENT_NODE]
    if not _get_children(run, "t") or len(_get_children(run, "rPr")) > 1:
        return False
    for node in run.childNodes:
        if node.nodeType == node.TEXT_NODE:
            if node.data.strip(XML_SPACE):
                return False
        elif not (_is_element(node, "rPr") or _is_element(node, "t")):
            return False
    for text in _get_children(run, "t"):
        if any(n.nodeType not in (n.TEXT_NODE, n.CDATA_SECTION_NODE) for n in text.childNodes):
            return False
    properties = _get_child(run, "rPr")
    if properties and any(n.namespaceURI != WORDML_NS or n.localName.endswith("Change")
                          for n in traverse(properties) if n.nodeType == n.ELEMENT_NODE):
        return False
    return bool(elements)


def _safe_context(run):
    # Restrict to paragraph children: wrappers carry independent semantics.
    parent = run.parentNode
    if not parent or not _is_element(parent, "p"):
        return False
    ancestor = parent
    while ancestor is not None:
        if ancestor.nodeType == ancestor.ELEMENT_NODE and ancestor.namespaceURI == WORDML_NS:
            if ancestor.localName in ("ins", "del", "moveFrom", "moveTo", "fldSimple"):
                return False
        ancestor = ancestor.parentNode
    # Complex fields can span paragraphs; the public workflow additionally
    # refuses a document containing a field. This also protects direct calls.
    root = run.ownerDocument.documentElement
    has_fields = getattr(run.ownerDocument, "_office_has_fields", None)
    if has_fields is None:
        has_fields = any(n.nodeType == n.ELEMENT_NODE and n.namespaceURI == WORDML_NS
                         and n.localName in ("fldChar", "instrText", "fldSimple")
                         for n in traverse(root))
        run.ownerDocument._office_has_fields = has_fields
    return not has_fields


def _can_merge(run1, run2):
    if not (_is_run(run1) and _is_run(run2) and run1.parentNode is run2.parentNode):
        return False
    if not _is_adjacent(run1, run2) or not _safe_context(run1):
        return False
    if not (_text_only(run1) and _text_only(run2)):
        return False
    if _attributes(run1) != _attributes(run2):
        return False
    rpr1 = _get_child(run1, "rPr")
    rpr2 = _get_child(run2, "rPr")
    if (rpr1 is None) != (rpr2 is None):
        return False
    return rpr1 is None or rpr1.toxml() == rpr2.toxml()


def _merge_run_content(target, source):
    for child in list(source.childNodes):
        if not _is_element(child, "rPr"):
            target.appendChild(child)


def _consolidate_text(run):
    """Explicit lossless consolidation; main workflow retains individual nodes."""
    count = 0
    previous = None
    for node in list(run.childNodes):
        if not _is_element(node, "t"):
            previous = None
            continue
        text_nodes = (node.TEXT_NODE, node.CDATA_SECTION_NODE)
        if any(child.nodeType not in text_nodes for child in node.childNodes):
            previous = None
            continue
        if previous is not None and _attributes(previous) == _attributes(node):
            left = "".join(child.data for child in previous.childNodes)
            right = "".join(child.data for child in node.childNodes)
            ancestor = node
            space = "default"
            while ancestor is not None:
                if ancestor.nodeType == ancestor.ELEMENT_NODE and ancestor.hasAttribute("xml:space"):
                    space = ancestor.getAttribute("xml:space")
                    break
                ancestor = ancestor.parentNode
            if space == "preserve" or (left == left.strip(XML_SPACE) and right == right.strip(XML_SPACE)):
                for child in list(node.childNodes):
                    previous.appendChild(child)
                run.removeChild(node)
                count += 1
                continue
        previous = node
    return count


def _merge_runs_in(container):
    # Compare before editing: rescanning an ever-growing target is quadratic.
    groups = []
    group = []
    for node in container.childNodes:
        if node.nodeType == node.TEXT_NODE and not node.data.strip(XML_SPACE):
            continue
        if _is_run(node):
            if group and _can_merge(group[-1], node):
                group.append(node)
                continue
            if group:
                groups.append(group)
            group = [node]
        else:
            if group:
                groups.append(group)
            group = []
    if group:
        groups.append(group)
    count = 0
    for group in groups:
        for source in group[1:]:
            _merge_run_content(group[0], source)
            container.removeChild(source)
            count += 1
    return count


def merge_runs(input_dir):
    try:
        directory = _io._safe_directory(input_dir)
        path = _io._safe_directory(directory / "word/document.xml")
        dom = _io._parse_xml(_io._read_regular(path, _io.MAX_XML_BYTES))
        try:
            root = dom.documentElement
            count = sum(_merge_runs_in(p) for p in _find_elements(root, "p"))
            if count:
                _io._write_document(path, dom)
            return count, f"Merged {count} runs"
        finally:
            dom.unlink()
    except Exception as exc:
        return 0, f"Error: {exc}"
