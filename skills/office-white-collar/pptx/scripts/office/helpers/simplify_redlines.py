# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Coalesce compatible adjacent revisions without accepting or deleting them."""

import importlib.util
from pathlib import Path
import zipfile

_spec = importlib.util.spec_from_file_location(
    "_office_redline_io", Path(__file__).resolve().parents[1] / "pack.py")
_io = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_io)

WORDML_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def traverse(node):
    yield node
    for child in node.childNodes:
        yield from traverse(child)


def _is_element(node, tag):
    return (node.nodeType == node.ELEMENT_NODE
            and node.namespaceURI == WORDML_NS
            and node.localName == tag.split(":")[-1])


def _find_elements(root, tag):
    return [node for node in traverse(root) if _is_element(node, tag)]


def _get_author(elem):
    value = elem.getAttributeNS(WORDML_NS, "author")
    return value if value.strip() else None


def _revision_attrs(elem):
    # IDs identify individual revisions; all other metadata must agree.
    return {(attr.namespaceURI, attr.localName or attr.name): attr.value
            for attr in elem.attributes.values()
            if (attr.namespaceURI, attr.localName) != (WORDML_NS, "id")}


def _plain_revision(elem):
    for node in elem.childNodes:
        if node.nodeType == node.TEXT_NODE:
            if node.data.strip(" \t\r\n"):
                return False
        elif not _is_element(node, "r"):
            return False
    allowed = {"r", "rPr", "t" if elem.localName == "ins" else "delText"}
    for node in traverse(elem):
        if node is elem or node.nodeType in (node.TEXT_NODE, node.CDATA_SECTION_NODE):
            continue
        if node.nodeType != node.ELEMENT_NODE or node.namespaceURI != WORDML_NS:
            return False
        # Ordinary run formatting is allowed, revision-bearing properties are not.
        in_properties = node.parentNode
        while in_properties is not elem and not _is_element(in_properties, "rPr"):
            in_properties = in_properties.parentNode
        if in_properties is not elem:
            if node.localName.endswith("Change") or node.localName in ("ins", "del", "moveFrom", "moveTo"):
                return False
        elif node.localName not in allowed:
            return False
    return any(_is_element(n, "r") for n in elem.childNodes)


def _can_merge_tracked(elem1, elem2):
    if not any(_is_element(elem1, tag) and _is_element(elem2, tag)
               for tag in ("ins", "del")):
        return False
    if elem1.parentNode is not elem2.parentNode or not _is_element(elem1.parentNode, "p"):
        return False
    if _get_author(elem1) is None or _get_author(elem1) != _get_author(elem2):
        return False
    if _revision_attrs(elem1) != _revision_attrs(elem2):
        return False
    sibling = elem1.nextSibling
    while sibling is not elem2:
        if sibling is None or sibling.nodeType != sibling.TEXT_NODE or sibling.data.strip(" \t\r\n"):
            return False
        sibling = sibling.nextSibling
    ancestor = elem1.parentNode
    while ancestor is not None:
        if ancestor.nodeType == ancestor.ELEMENT_NODE and ancestor.namespaceURI == WORDML_NS:
            if ancestor.localName in ("ins", "del", "moveFrom", "moveTo", "fldSimple"):
                return False
        ancestor = ancestor.parentNode
    root = elem1.ownerDocument.documentElement
    has_fields = getattr(elem1.ownerDocument, "_office_has_fields", None)
    if has_fields is None:
        has_fields = any(n.nodeType == n.ELEMENT_NODE and n.namespaceURI == WORDML_NS
                         and n.localName in ("fldChar", "instrText", "fldSimple") for n in traverse(root))
        elem1.ownerDocument._office_has_fields = has_fields
    return not has_fields and _plain_revision(elem1) and _plain_revision(elem2)


def _merge_tracked_content(target, source):
    # Preserve every run, text node and property under the retained revision.
    for child in list(source.childNodes):
        target.appendChild(child)


def _merge_tracked_changes_in(container, tag):
    groups = []
    group = []
    for node in container.childNodes:
        if node.nodeType == node.TEXT_NODE and not node.data.strip(" \t\r\n"):
            continue
        if _is_element(node, tag):
            if group and _can_merge_tracked(group[-1], node):
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
            _merge_tracked_content(group[0], source)
            container.removeChild(source)
            count += 1
    return count


def simplify_redlines(input_dir):
    try:
        directory = _io._safe_directory(input_dir)
        path = _io._safe_directory(directory / "word/document.xml")
        dom = _io._parse_xml(_io._read_regular(path, _io.MAX_XML_BYTES))
        try:
            count = 0
            for paragraph in _find_elements(dom.documentElement, "p"):
                for tag in ("ins", "del"):
                    count += _merge_tracked_changes_in(paragraph, tag)
            if count:
                _io._write_document(path, dom)
            return count, f"Merged {count} tracked changes"
        finally:
            dom.unlink()
    except Exception as exc:
        return 0, f"Error: {exc}"


def _authors(data):
    dom = _io._parse_xml(data)
    try:
        return {author for node in traverse(dom.documentElement)
                if node.nodeType == node.ELEMENT_NODE and node.namespaceURI == WORDML_NS
                and (node.localName in ("ins", "del", "moveFrom", "moveTo")
                     or node.localName.endswith("Change"))
                if (author := _get_author(node)) is not None}
    finally:
        dom.unlink()


def get_tracked_change_authors(doc_xml_path):
    path = _io._safe_directory(doc_xml_path)
    return _authors(_io._read_regular(path, _io.MAX_XML_BYTES))


def _get_authors_from_docx(docx_path):
    path = _io._safe_directory(docx_path)
    if not path.is_file() or path.stat().st_size > _io.MAX_TOTAL_BYTES:
        raise ValueError("original DOCX must be a bounded regular file")
    unpacker = _io._load_local(Path(__file__).resolve().parents[1] / "unpack.py",
                               "_office_author_unpack")
    with zipfile.ZipFile(path) as archive:
        members = unpacker._members(archive)
        document = next((m for m in members if m.filename == "word/document.xml"), None)
        if document is None:
            raise ValueError("missing word/document.xml")
        with archive.open(document) as stream:
            data = stream.read(_io.MAX_XML_BYTES + 1)
        return _authors(data)


def infer_author(modified_dir, original_docx=None, default=None):
    """Infer a sole new author; ambiguity yields the explicitly supplied fallback."""
    modified = get_tracked_change_authors(Path(modified_dir) / "word/document.xml")
    original = _get_authors_from_docx(original_docx) if original_docx else set()
    added = modified - original
    if len(added) == 1:
        return next(iter(added))
    if not added and len(modified) == 1:
        return next(iter(modified))
    return default
