# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Offline behavior and adversarial fixtures for the original Office rebuild."""

import importlib.util
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import types
import warnings
import zipfile
from xml.dom import minidom

import pytest

ROOT = Path(__file__).resolve().parents[1]
OFFICE = ROOT / "skills/office-white-collar"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CT = b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
RELS = b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
PARTS = {"docx": "word/document.xml", "pptx": "ppt/presentation.xml", "xlsx": "xl/workbook.xml"}
OWNED = ("pack.py", "unpack.py", "helpers/merge_runs.py", "helpers/simplify_redlines.py")


def load(path):
    spec = importlib.util.spec_from_file_location("_original_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=("docx", "pptx", "xlsx"))
def office(request):
    return OFFICE / request.param / "scripts/office"


def document(body):
    return f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'.encode()


def run(text, properties="", attrs=""):
    return f'<w:r{attrs}>{properties}<w:t xml:space="preserve">{text}</w:t></w:r>'


def revision(text, author="Ada", tag="ins", ident="1", date="2026-01-01T00:00:00Z", extra=""):
    text_tag = "t" if tag == "ins" else "delText"
    author_attr = f' w:author="{author}"' if author is not None else ""
    date_attr = f' w:date="{date}"' if date is not None else ""
    return (f'<w:{tag} w:id="{ident}"{author_attr}{date_attr}{extra}>'
            f'<w:r><w:{text_tag} xml:space="preserve">{text}</w:{text_tag}></w:r></w:{tag}>')


def tree(path, family="docx", xml=None):
    data = {"[Content_Types].xml": CT, "_rels/.rels": RELS,
            PARTS[family]: xml or (document("<w:p/>") if family == "docx" else b"<root/>"),
            "media/data.bin": bytes(range(256))}
    for name, value in data.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)
    return data


def archive(path, family="docx", extra=(), xml=None):
    data = {"[Content_Types].xml": CT, "_rels/.rels": RELS,
            PARTS[family]: xml or (document("<w:p/>") if family == "docx" else b"<root/>")}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as dest:
            for name, value in list(data.items()) + list(extra):
                dest.writestr(name, value)
    return path


def snapshot(path):
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def docfile(tmp_path, body):
    path = tmp_path / "word/document.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(document(body))
    return path


def test_independent_copies_identical():
    for name in OWNED:
        assert len({(OFFICE / family / "scripts/office" / name).read_bytes()
                    for family in PARTS}) == 1


def test_real_zip_roundtrip_preserves_every_part(office, tmp_path):
    family = office.parents[1].name
    source = tmp_path / "source"
    xml = (document('<w:p>' + run("  leading\t\ntrailing  “quoted” ") + "</w:p>")
           if family == "docx" else b'<root xml:space="preserve">  a <t> b </t> c  </root>')
    expected = tree(source, family, xml)
    package = tmp_path / ("result." + family)
    packer, unpacker = load(office / "pack.py"), load(office / "unpack.py")
    assert packer.pack(source, package, validate=False)[0]
    with zipfile.ZipFile(package) as z:
        assert {n: z.read(n) for n in z.namelist()} == expected
    output = tmp_path / "output"
    assert unpacker.unpack(package, output, False, False)[0]
    assert snapshot(output) == expected
    assert snapshot(source) == expected


@pytest.mark.parametrize("name", [
    "../escaped", "/absolute", "C:/drive", "a/../../escape", "a\\escape", "a//b",
    "./alias", "bad./x", "bad /x", "a:b", "control\x01",
])
def test_reject_unsafe_zip_names(office, tmp_path, name):
    source = archive(tmp_path / "bad.docx", extra=[(name, b"payload")])
    output = tmp_path / "output"
    output.mkdir()
    (output / "keep").write_bytes(b"old")
    original = source.read_bytes()
    ok, message = load(office / "unpack.py").unpack(source, output)
    assert not ok and message.startswith("Error")
    assert snapshot(output) == {"keep": b"old"}
    assert source.read_bytes() == original
    assert not (tmp_path / "escaped").exists()


@pytest.mark.parametrize("entries", [
    [("same", b"1"), ("same", b"2")],
    [("A/x", b"1"), ("a/y", b"2")],
    [("file", b"1"), ("file/child", b"2")],
    [("é", b"1"), ("e\u0301", b"2")],
])
def test_reject_duplicate_and_conflicting_entries(office, tmp_path, entries):
    source = archive(tmp_path / "bad.docx", extra=entries)
    output = tmp_path / "out"
    assert not load(office / "unpack.py").unpack(source, output)[0]
    assert not output.exists()


@pytest.mark.parametrize("kind", [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFSOCK])
def test_reject_zip_special_files(office, tmp_path, kind):
    entry = zipfile.ZipInfo("special")
    entry.create_system = 3
    entry.external_attr = (kind | 0o777) << 16
    source = archive(tmp_path / "bad.docx", extra=[(entry, b"target")])
    assert not load(office / "unpack.py").unpack(source, tmp_path / "out")[0]


@pytest.mark.parametrize("payload", [
    b'<!DOCTYPE root SYSTEM "file:///nonexistent"><root/>',
    b'<!DOCTYPE root [<!ENTITY x SYSTEM "file:///nonexistent">]><root>&x;</root>',
    b'<!DOCTYPE root [<!ENTITY a "bomb"><!ENTITY b "&a;&a;">]><root>&b;</root>',
    '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE root [<!ENTITY x "bad">]><root>&x;</root>'.encode("utf-16"),
    b"<broken>",
])
def test_dangerous_xml_never_replaces_output(office, tmp_path, payload):
    source = tmp_path / "source"
    tree(source, xml=payload)
    target = tmp_path / "existing.docx"
    target.write_bytes(b"old")
    assert not load(office / "pack.py").pack(source, target, validate=False)[0]
    assert target.read_bytes() == b"old"
    package = archive(tmp_path / "bad.docx", xml=payload)
    output = tmp_path / "out"
    output.mkdir()
    (output / "old").write_bytes(b"keep")
    assert not load(office / "unpack.py").unpack(package, output)[0]
    assert snapshot(output) == {"old": b"keep"}


def test_zip_bomb_and_member_count_rejected(office, tmp_path):
    source = archive(tmp_path / "bomb.docx", extra=[("bomb.bin", b"0" * (2 * 1024 * 1024))])
    unpacker = load(office / "unpack.py")
    assert "ratio" in unpacker.unpack(source, tmp_path / "out")[1]
    unpacker._io.MAX_FILES = 2
    assert "count" in unpacker.unpack(source, tmp_path / "out")[1]


def test_expanded_and_xml_limits_reject_before_publication(office, tmp_path, monkeypatch):
    source = archive(tmp_path / "large.docx")
    module = load(office / "unpack.py")
    monkeypatch.setattr(module._io, "MAX_TOTAL_BYTES", 1)
    assert not module.unpack(source, tmp_path / "out")[0]
    monkeypatch.setattr(module._io, "MAX_TOTAL_BYTES", 512 * 1024 * 1024)
    monkeypatch.setattr(module._io, "MAX_XML_BYTES", 3)
    assert not module.unpack(source, tmp_path / "out")[0]
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("special", ["symlink", "fifo"])
def test_pack_rejects_tree_special_files(office, tmp_path, special):
    source = tmp_path / "source"
    tree(source)
    if special == "symlink":
        (source / "bad").symlink_to(source / "[Content_Types].xml")
    else:
        os.mkfifo(source / "bad")
    target = tmp_path / "old.docx"
    target.write_bytes(b"old")
    assert not load(office / "pack.py").pack(source, target, validate=False)[0]
    assert target.read_bytes() == b"old"


def test_output_symlink_and_source_containment_rejected(office, tmp_path):
    source = tmp_path / "source"
    tree(source)
    real = tmp_path / "real.docx"
    real.write_bytes(b"keep")
    alias = tmp_path / "alias.docx"
    alias.symlink_to(real)
    packer = load(office / "pack.py")
    assert not packer.pack(source, alias, validate=False)[0]
    assert not packer.pack(source, source / "nested.docx", validate=False)[0]
    assert real.read_bytes() == b"keep"
    zipped = archive(source / "inside.docx")
    assert not load(office / "unpack.py").unpack(zipped, source)[0]


def test_atomic_pack_failure_keeps_input_and_output(office, tmp_path, monkeypatch):
    source = tmp_path / "source"
    expected = tree(source)
    target = tmp_path / "old.docx"
    target.write_bytes(b"old")
    packer = load(office / "pack.py")
    def fail(*args):
        raise OSError("injected replace failure")
    monkeypatch.setattr(packer.os, "replace", fail)
    assert not packer.pack(source, target, validate=False)[0]
    assert snapshot(source) == expected and target.read_bytes() == b"old"


def test_atomic_unpack_restores_existing_directory(office, tmp_path, monkeypatch):
    source = archive(tmp_path / "source.docx")
    output = tmp_path / "out"
    output.mkdir()
    (output / "keep").write_bytes(b"old")
    unpacker = load(office / "unpack.py")
    replace = os.replace
    def fail_stage(src, dest):
        if Path(src).name == "parts":
            raise OSError("injected publishing failure")
        return replace(src, dest)
    monkeypatch.setattr(unpacker.os, "replace", fail_stage)
    assert not unpacker.unpack(source, output)[0]
    assert snapshot(output) == {"keep": b"old"}


def test_validation_receives_private_copy_and_failure_blocks_publish(office, tmp_path, monkeypatch):
    source = tmp_path / "source"
    expected = tree(source)
    output = tmp_path / "old.docx"
    output.write_bytes(b"old")
    packer = load(office / "pack.py")
    def reject(stage, original, suffix, infer):
        assert Path(stage).is_relative_to(Path(os.environ["TMPDIR"]))
        (Path(stage) / "word/document.xml").write_bytes(b"changed")
        return False
    monkeypatch.setattr(packer, "_run_validation", reject)
    assert not packer.pack(source, output)[0]
    assert snapshot(source) == expected and output.read_bytes() == b"old"


def test_safe_run_merge_keeps_text_properties_and_statistics(office, tmp_path):
    props = "<w:rPr><w:b/></w:rPr>"
    path = docfile(tmp_path, "<w:p>" + run(" a ", props) + run(" b ", props) + "</w:p>")
    count, message = load(office / "helpers/merge_runs.py").merge_runs(tmp_path)
    assert count == 1 and "1" in message
    dom = minidom.parseString(path.read_bytes())
    assert len(dom.getElementsByTagNameNS(W, "r")) == 1
    assert [n.firstChild.data for n in dom.getElementsByTagNameNS(W, "t")] == [" a ", " b "]
    assert len(dom.getElementsByTagNameNS(W, "b")) == 1


@pytest.mark.parametrize("body", [
    "<w:p>" + run("a") + "<w:bookmarkStart w:id='1' w:name='b'/>" + run("b") + "</w:p>",
    "<w:p>" + run("a") + "<w:proofErr w:type='spellStart'/>" + run("b") + "</w:p>",
    "<w:p>" + run("a") + "<!--boundary-->" + run("b") + "</w:p>",
    "<w:p><w:r><w:fldChar w:fldCharType='begin'/></w:r>" + run("a") + run("b") + "</w:p>",
    "<w:p><w:r><w:drawing/></w:r>" + run("a") + "</w:p>",
    "<w:p>" + run("a", attrs=" w:rsidR='1'") + run("b", attrs=" w:rsidR='2'") + "</w:p>",
    "<w:p>" + run("a", "<w:rPr><w:b/></w:rPr>") + run("b") + "</w:p>",
    "<w:p>" + revision("a") + revision("b", ident="2") + "</w:p>",
    "<w:p><w:ins w:author='Ada'>" + run("a") + run("b") + "</w:ins></w:p>",
    "<w:p>" + run("a") + "<w:r><w:t>b</w:t><w:tab/></w:r></w:p>",
    "<w:p><w:r><w:t>a</w:t></w:r><w:r><w:delText>b</w:delText></w:r></w:p>",
    "<w:p>" + run("a") + run("b") + "</w:p><w:p><w:r><w:fldChar w:fldCharType='end'/></w:r></w:p>",
])
def test_run_merge_refuses_semantic_boundaries(office, tmp_path, body):
    path = docfile(tmp_path, body)
    before = path.read_bytes()
    assert load(office / "helpers/merge_runs.py").merge_runs(tmp_path)[0] == 0
    assert path.read_bytes() == before


@pytest.mark.parametrize("tag", ["ins", "del"])
def test_revision_merge_preserves_all_text_and_author(office, tmp_path, tag):
    path = docfile(tmp_path, "<w:p>" + revision(" a ", tag=tag) + revision(" b ", tag=tag, ident="2") + "</w:p>")
    module = load(office / "helpers/simplify_redlines.py")
    assert module.simplify_redlines(tmp_path)[0] == 1
    dom = minidom.parseString(path.read_bytes())
    revisions = dom.getElementsByTagNameNS(W, tag)
    assert len(revisions) == 1
    assert revisions[0].getAttributeNS(W, "author") == "Ada"
    text_tag = "t" if tag == "ins" else "delText"
    assert [n.firstChild.data for n in dom.getElementsByTagNameNS(W, text_tag)] == [" a ", " b "]


@pytest.mark.parametrize("other", [
    revision("b", author="Grace"), revision("b", tag="del"),
    revision("b", date="2026-01-02T00:00:00Z"),
    revision("b", date=None), revision("b", extra=' w:displacedByCustomXml="next"'),
])
def test_revision_merge_refuses_incompatible_metadata(office, tmp_path, other):
    path = docfile(tmp_path, "<w:p>" + revision("a") + other + "</w:p>")
    before = path.read_bytes()
    assert load(office / "helpers/simplify_redlines.py").simplify_redlines(tmp_path)[0] == 0
    assert path.read_bytes() == before


def test_unknown_authors_are_never_invented(office, tmp_path):
    path = docfile(tmp_path, "<w:p>" + revision("a", author=None) + revision("b", author=None) + "</w:p>")
    module = load(office / "helpers/simplify_redlines.py")
    assert module.simplify_redlines(tmp_path)[0] == 0
    assert module.get_tracked_change_authors(path) == set()
    assert module.infer_author(tmp_path) is None
    assert module.infer_author(tmp_path, default="explicit fallback") == "explicit fallback"
    path.write_bytes(document("<w:p>" + revision("a") + revision("b", author="Grace") + "</w:p>"))
    assert module.infer_author(tmp_path) is None


def test_author_inference_compares_original_without_extracting(office, tmp_path):
    original = archive(tmp_path / "original.docx", xml=document("<w:p>" + revision("old") + "</w:p>"))
    docfile(tmp_path, "<w:p>" + revision("old") + revision("new", author="Grace") + "</w:p>")
    module = load(office / "helpers/simplify_redlines.py")
    assert module.infer_author(tmp_path, original) == "Grace"


@pytest.mark.parametrize("mode", ["fifo", "duplicate", "bomb"])
def test_author_archive_uses_the_same_safety_policy(office, tmp_path, mode):
    source = tmp_path / "original.docx"
    if mode == "fifo":
        os.mkfifo(source)
    else:
        extra = ([("word/document.xml", document("<w:p/>"))] if mode == "duplicate"
                 else [("bomb.bin", b"0" * (2 * 1024 * 1024))])
        archive(source, extra=extra)
    module = load(office / "helpers/simplify_redlines.py")
    with pytest.raises(ValueError):
        module._get_authors_from_docx(source)


def test_helpers_reject_dtd_without_modifying_document(office, tmp_path):
    path = docfile(tmp_path, "<w:p/>")
    evil = b'<!DOCTYPE x [<!ENTITY a "bad">]><x>&a;</x>'
    path.write_bytes(evil)
    for name in ("merge_runs", "simplify_redlines"):
        count, message = getattr(load(office / f"helpers/{name}.py"), name)(tmp_path)
        assert count == 0 and message.startswith("Error")
        assert path.read_bytes() == evil


def test_missing_required_parts_rejected(office, tmp_path):
    source = tmp_path / "empty"
    source.mkdir()
    output = tmp_path / "out.docx"
    assert not load(office / "pack.py").pack(source, output, validate=False)[0]
    package = tmp_path / "empty.docx"
    with zipfile.ZipFile(package, "w") as z:
        z.writestr("only.txt", "text")
    assert not load(office / "unpack.py").unpack(package, tmp_path / "out")[0]


def test_cli_works_in_standalone_install_without_other_skills(office, tmp_path):
    standalone = tmp_path / "standalone"
    for name in OWNED:
        target = standalone / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(office / name, target)
    source = tmp_path / "source"
    tree(source, xml=document("<w:p>" + run("a") + run("b") + "</w:p>"))
    output = tmp_path / "result.docx"
    cmd = [sys.executable, str(standalone / "pack.py"), str(source), str(output), "--validate", "false"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    assert proc.returncode == 0, proc.stderr
    cmd = [sys.executable, str(standalone / "unpack.py"), str(output), str(tmp_path / "out"),
           "--merge-runs", "true", "--simplify-redlines", "true"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    assert proc.returncode == 0 and "Merged 1 runs" in proc.stdout, proc.stderr


def test_public_validator_contract_with_synthetic_substitute(office, tmp_path, monkeypatch):
    # No import or execution of the baseline validator implementation.
    calls = []
    class Validator:
        def __init__(self, directory, original_file=None, author=None):
            calls.append(("init", Path(directory), original_file, author))
        def validate(self):
            calls.append("validate")
            return True
        def __getattr__(self, name):
            if name.startswith("validate_"):
                return lambda: calls.append(name) or True
            raise AttributeError(name)
    stub = types.ModuleType("validators")
    for name in ("DOCXSchemaValidator", "PPTXSchemaValidator", "BaseSchemaValidator", "RedliningValidator"):
        setattr(stub, name, Validator)
    monkeypatch.setitem(sys.modules, "validators", stub)
    packer = load(office / "pack.py")
    for suffix in (".docx", ".pptx", ".xlsx"):
        assert packer._run_validation(tmp_path, None, suffix)
    assert calls.count("validate") == 3
    assert "validate_content_types" not in calls  # All families use their full public validate contract.


def test_compressible_local_data_roundtrips_without_triggering_own_bomb_policy(office, tmp_path):
    source = tmp_path / "source"
    tree(source)
    data = b"0" * (2 * 1024 * 1024)
    (source / "media/zeros.bin").write_bytes(data)
    package = tmp_path / "large.docx"
    assert load(office / "pack.py").pack(source, package, validate=False)[0]
    with zipfile.ZipFile(package) as z:
        assert z.getinfo("media/zeros.bin").compress_type == zipfile.ZIP_STORED
    output = tmp_path / "out"
    assert load(office / "unpack.py").unpack(package, output, False, False)[0]
    assert (output / "media/zeros.bin").read_bytes() == data


@pytest.mark.parametrize("xml", [b"<x>" * 150 + b"</x>" * 150,
                                  b"<x>" + b"<y/>" * 100001 + b"</x>"])
def test_xml_structure_bombs_are_rejected_before_dom(office, tmp_path, xml):
    source = archive(tmp_path / "deep.docx", xml=xml)
    assert not load(office / "unpack.py").unpack(source, tmp_path / "out")[0]
    assert not (tmp_path / "out").exists()


def test_cross_filesystem_publication_fails_before_moving_existing_output(office, tmp_path, monkeypatch):
    source = archive(tmp_path / "source.docx")
    output = tmp_path / "out"
    output.mkdir()
    (output / "keep").write_bytes(b"old")
    unpacker = load(office / "unpack.py")
    original = Path.stat
    def different_device(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path.name == "parts":
            return types.SimpleNamespace(st_dev=result.st_dev + 1, st_mode=result.st_mode)
        return result
    monkeypatch.setattr(Path, "stat", different_device)
    ok, message = unpacker.unpack(source, output, False, False)
    assert not ok and "filesystem" in message
    assert snapshot(output) == {"keep": b"old"}


@pytest.mark.parametrize("name", ["merge_runs", "simplify_redlines"])
def test_helper_atomic_failure_keeps_original_xml(office, tmp_path, monkeypatch, name):
    body = (run("a") + run("b") if name == "merge_runs"
            else revision("a") + revision("b", ident="2"))
    path = docfile(tmp_path, "<w:p>" + body + "</w:p>")
    expected = path.read_bytes()
    module = load(office / f"helpers/{name}.py")
    def fail(*args):
        raise OSError("injected XML publish failure")
    monkeypatch.setattr(module._io.os, "replace", fail)
    count, message = getattr(module, name)(tmp_path)
    assert count == 0 and message.startswith("Error")
    assert path.read_bytes() == expected


@pytest.mark.parametrize("separator", ["<w:bookmarkStart w:id='9' w:name='x'/>",
                                       "<!--keep-->", "<w:r><w:drawing/></w:r>"])
def test_revision_boundaries_are_preserved(office, tmp_path, separator):
    path = docfile(tmp_path, "<w:p>" + revision("a") + separator + revision("b", ident="2") + "</w:p>")
    before = path.read_bytes()
    assert load(office / "helpers/simplify_redlines.py").simplify_redlines(tmp_path)[0] == 0
    assert path.read_bytes() == before


def test_multiple_merge_statistics_are_actual_removed_nodes(office, tmp_path):
    path = docfile(tmp_path, "<w:p>" + "".join(run(str(i)) for i in range(100)) + "</w:p>")
    assert load(office / "helpers/merge_runs.py").merge_runs(tmp_path)[0] == 99
    assert len(minidom.parseString(path.read_bytes()).getElementsByTagNameNS(W, "t")) == 100
    path.write_bytes(document("<w:p>" + "".join(revision(str(i), ident=str(i)) for i in range(100)) + "</w:p>"))
    assert load(office / "helpers/simplify_redlines.py").simplify_redlines(tmp_path)[0] == 99
    assert len(minidom.parseString(path.read_bytes()).getElementsByTagNameNS(W, "t")) == 100


@pytest.mark.parametrize("family", ["docx", "xlsx"])
def test_real_library_document_roundtrip(office, tmp_path, family):
    # These are real file-format libraries; no Office renderer or account is used.
    source = tmp_path / ("library." + family)
    if family == "docx":
        library = pytest.importorskip("docx")
        doc = library.Document()
        doc.add_paragraph("  中文 with  spaces  ").add_run("bold").bold = True
        doc.save(source)
    else:
        library = pytest.importorskip("openpyxl")
        book = library.Workbook()
        book.active["A1"] = "  中文 with  spaces  "
        book.active["B1"] = "=1+1"
        book.save(source)
        book.close()
    output = tmp_path / "parts"
    assert load(office / "unpack.py").unpack(source, output, False, False)[0]
    rebuilt = tmp_path / ("rebuilt." + family)
    assert load(office / "pack.py").pack(output, rebuilt, validate=False)[0]
    with zipfile.ZipFile(source) as a, zipfile.ZipFile(rebuilt) as b:
        assert {n: a.read(n) for n in a.namelist()} == {n: b.read(n) for n in b.namelist()}
    if family == "docx":
        assert library.Document(rebuilt).paragraphs[0].text == "  中文 with  spaces  bold"
    else:
        book = library.load_workbook(rebuilt)
        assert book.active["A1"].value == "  中文 with  spaces  "
        assert book.active["B1"].value == "=1+1"
        book.close()
