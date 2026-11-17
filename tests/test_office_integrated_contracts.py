# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Pack/unpack contracts against real, licensed validators and synthetic OOXML.

OFFICE_CONTRACT_CANONICAL optionally supplies current read-only dependencies in
an isolated repair checkout. Only the six pack/unpack files come from this tree.
"""

import gc
import importlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
RELATIVE = Path("skills/office-white-collar")
FAMILIES = ("docx", "pptx", "xlsx")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
X = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def rels(*entries):
    return f'<Relationships xmlns="{REL}">' + "".join(
        f'<Relationship Id="{ident}" Type="{R}/{kind}" Target="{target}"/>'
        for ident, kind, target in entries) + "</Relationships>"


def run(text):
    return f'<w:r><w:t>{text}</w:t></w:r>'


def revision(text, author="Ada", ident=1, tag="ins"):
    text_tag = "delText" if tag == "del" else "t"
    return (f'<w:{tag} w:id="{ident}" w:author="{author}" w:date="2026-01-01T00:00:00Z">'
            f'<w:r><w:{text_tag}>{text}</w:{text_tag}></w:r></w:{tag}>')


def document(body):
    return f'<w:document xmlns:w="{W}"><w:body><w:p>{body}</w:p></w:body></w:document>'


def parts(root, family):
    if family == "docx":
        main = "word/document.xml"
        put(root, main, document(run("Hello")))
        content_types = {main: "wordprocessingml.document.main"}
    elif family == "xlsx":
        main = "xl/workbook.xml"
        put(root, main, f'<workbook xmlns="{X}" xmlns:r="{R}"><sheets><sheet name="One" sheetId="1" r:id="rId1"/></sheets></workbook>')
        put(root, "xl/worksheets/sheet1.xml", f'<worksheet xmlns="{X}"><sheetData><row r="1"><c r="A1"><v>4</v></c></row></sheetData></worksheet>')
        put(root, "xl/_rels/workbook.xml.rels", rels(("rId1", "worksheet", "worksheets/sheet1.xml")))
        content_types = {main: "spreadsheetml.sheet.main", "xl/worksheets/sheet1.xml": "spreadsheetml.worksheet"}
    else:
        main = "ppt/presentation.xml"
        put(root, main, f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst><p:sldSz cx="9144000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>')
        put(root, "ppt/_rels/presentation.xml.rels", rels(("rId1", "slide", "slides/slide1.xml")))
        put(root, "ppt/slides/slide1.xml", f'<p:sld xmlns:p="{P}"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld></p:sld>')
        content_types = {main: "presentationml.presentation.main", "ppt/slides/slide1.xml": "presentationml.slide"}
    put(root, "_rels/.rels", rels(("rId1", "officeDocument", main)))
    overrides = "".join(f'<Override PartName="/{name}" ContentType="application/vnd.openxmlformats-officedocument.{kind}+xml"/>' for name, kind in content_types.items())
    put(root, "[Content_Types].xml", f'<Types xmlns="{CT}"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>{overrides}</Types>')
    return root


def archive(root, target):
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as dest:
        for item in root.rglob("*"):
            if item.is_file():
                dest.write(item, item.relative_to(root).as_posix())
    return target


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


@pytest.fixture(scope="session")
def runtime(tmp_path_factory):
    dependencies = Path(os.environ.get("OFFICE_CONTRACT_CANONICAL", ROOT))
    target = tmp_path_factory.mktemp("office-contract-runtime")
    for family in FAMILIES:
        directory = Path(family) / "scripts/office"
        shutil.copytree(dependencies / RELATIVE / directory, target / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("pack.py", "unpack.py"):
            shutil.copyfile(ROOT / RELATIVE / directory / name, target / directory / name)
    return target


@pytest.fixture(params=FAMILIES)
def office(request, runtime, monkeypatch, tmp_path):
    temp = tmp_path / "temporary"
    temp.mkdir()
    monkeypatch.setenv("TMPDIR", str(temp))
    directory = runtime / request.param / "scripts/office"
    namespace = "_integrated_office_" + request.param
    package = types.ModuleType(namespace)
    package.__path__ = [str(directory)]
    monkeypatch.setitem(sys.modules, namespace, package)
    packer = importlib.import_module(namespace + ".pack")
    spec = importlib.util.spec_from_file_location(namespace + ".unpack", directory / "unpack.py")
    unpacker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unpacker)
    yield types.SimpleNamespace(pack=packer, unpack=unpacker, directory=directory, temp=temp)
    for name in list(sys.modules):
        if name.startswith(namespace + "."):
            sys.modules.pop(name, None)


def cli(office, script, *args):
    return subprocess.run([sys.executable, str(office.directory / script), *map(str, args)],
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                          capture_output=True, text=True, timeout=30)


@pytest.mark.parametrize("family", FAMILIES)
def test_good_packages_pass_real_validation_and_roundtrip(office, tmp_path, family):
    source = parts(tmp_path / "source", family)
    before = snapshot(source)
    target = tmp_path / ("packed." + family)
    result = cli(office, "pack.py", source, target)
    assert result.returncode == 0, result.stdout + result.stderr
    result = cli(office, "validate.py", target)
    assert result.returncode == 0, result.stdout + result.stderr
    output = tmp_path / "output"
    assert office.unpack.unpack(target, output, False, False)[0]
    assert snapshot(output) == before == snapshot(source)
    assert not list(office.temp.iterdir())


@pytest.mark.parametrize("blank", [False, True])
def test_ordinary_docx_original_succeeds_without_revision_author(office, tmp_path, blank):
    source = parts(tmp_path / "source", "docx")
    if blank:
        put(source, "word/document.xml", document(""))
    original = archive(source, tmp_path / "original.docx")
    before = original.read_bytes(), snapshot(source)
    result = cli(office, "pack.py", source, tmp_path / "out.docx", "--original", original)
    assert result.returncode == 0, result.stdout + result.stderr
    assert before == (original.read_bytes(), snapshot(source))
    assert not list(office.temp.iterdir())


@pytest.mark.parametrize("case,accepted", [
    ("tracked", True), ("multiple_authors", True), ("untracked", False),
    ("ambiguous_untracked", False), ("missing_author", False),
    ("changed_prior_author", False), ("changed_prior_text", False),
    ("changed_prior_date", False), ("deleted_prior_revision", False),
])
def test_docx_original_checks_real_revisions_and_attribution(office, tmp_path, case, accepted):
    source = parts(tmp_path / "source", "docx")
    prior = revision("Prior", "Previous") if "prior" in case else ""
    put(source, "word/document.xml", document(run("Hello") + prior))
    original = archive(source, tmp_path / "original.docx")
    body = revision("Hello", tag="del") + revision("Changed", ident=2)
    if case == "multiple_authors":
        body += revision("More", "Grace", ident=3)
    elif case == "untracked":
        body = run("Changed")
    elif case == "ambiguous_untracked":
        body = run("Untracked") + revision("A") + revision("B", "Grace", ident=2)
    elif case == "missing_author":
        body = body.replace(' w:author="Ada"', "")
    elif case == "changed_prior_author":
        body = run("Hello") + prior.replace("Previous", "Imposter")
    elif case == "changed_prior_text":
        body = run("Hello") + prior.replace(">Prior<", ">Tampered<")
    elif case == "changed_prior_date":
        body = run("Hello") + prior.replace("2026-01-01", "2026-01-02")
    elif case == "deleted_prior_revision":
        body = run("Hello")
    put(source, "word/document.xml", document(body))
    before = original.read_bytes(), snapshot(source)
    output = tmp_path / "out.docx"
    output.write_bytes(b"previous package")
    ok, message = office.pack.pack(source, output, original)
    assert ok is accepted, message
    if accepted:
        with zipfile.ZipFile(output) as result:
            assert result.read("word/document.xml") == (source / "word/document.xml").read_bytes()
    else:
        assert output.read_bytes() == b"previous package"
    assert before == (original.read_bytes(), snapshot(source))
    assert not list(office.temp.iterdir())


@pytest.mark.parametrize("damage", ["cell_attribute", "duplicate_sheet_id"])
def test_xlsx_rejects_real_xsd_and_unique_id_errors(office, tmp_path, damage):
    source = parts(tmp_path / "source", "xlsx")
    if damage == "cell_attribute":
        part = source / "xl/worksheets/sheet1.xml"
        part.write_text(part.read_text().replace("<v>", '<v impossible="1">'))
    else:
        part = source / "xl/workbook.xml"
        part.write_text(part.read_text().replace("</sheets>", '<sheet name="Two" sheetId="1" r:id="rId1"/></sheets>'))
    before = snapshot(source)
    output = tmp_path / "out.xlsx"
    output.write_bytes(b"previous package")
    direct = cli(office, "validate.py", source)
    packed = cli(office, "pack.py", source, output)
    assert direct.returncode == packed.returncode == 1, direct.stdout + packed.stdout
    diagnostic = "impossible" if damage == "cell_attribute" else "Duplicate"
    assert diagnostic.lower() in direct.stdout.lower()
    assert diagnostic.lower() in packed.stdout.lower()
    assert output.read_bytes() == b"previous package"
    assert snapshot(source) == before
    assert not list(office.temp.iterdir())


@pytest.mark.parametrize("family", FAMILIES)
def test_real_validation_then_failed_zip_publish_is_atomic(office, tmp_path, monkeypatch, family):
    source = parts(tmp_path / "source", family)
    before = snapshot(source)
    output = tmp_path / ("out." + family)
    output.write_bytes(b"previous package")

    def fail(src, dst):
        assert Path(src).name == "package.zip" and Path(dst) == output
        raise PermissionError("publish-denied")

    monkeypatch.setattr(office.pack.os, "replace", fail)
    ok, message = office.pack.pack(source, output)
    assert not ok and "publish-denied" in message
    assert output.read_bytes() == b"previous package"
    assert snapshot(source) == before
    assert not list(office.temp.iterdir())


@pytest.mark.parametrize("failure", ["persistent", "once", "occupied", "symlink"])
def test_failed_rollback_preserves_recoverable_old_bytes(office, tmp_path, monkeypatch, failure):
    source = archive(parts(tmp_path / "source", "docx"), tmp_path / "input.docx")
    output = tmp_path / "output"
    put(output, "nested/keep", "old edits")
    (output / "bytes").write_bytes(bytes(range(256)))
    expected = snapshot(output)
    unrelated = put(tmp_path, "previous-output/keep", "unrelated")
    external = put(tmp_path, "external/keep", "external")
    replace = os.replace
    attempts = []

    def fail(src, dst):
        src, dst = Path(src), Path(dst)
        if src.name == "parts":
            if failure == "occupied":
                put(output, "new", "new owner")
            elif failure == "symlink":
                output.symlink_to(external.parent, target_is_directory=True)
            raise PermissionError("publish-denied")
        if src.name == "previous-output" and dst == output:
            attempts.append(src)
            if failure == "persistent" or (failure == "once" and len(attempts) == 1):
                raise PermissionError("restore-denied")
        return replace(src, dst)

    monkeypatch.setattr(office.unpack.os, "replace", fail)
    ok, message = office.unpack.unpack(source, output, False, False)
    assert not ok and "publish-denied" in message and "rollback failed" in message
    backup = Path(message.split("previous output preserved at ", 1)[1])
    gc.collect()  # The recovery copy must survive context exit and finalizers.
    assert backup.is_relative_to(office.temp.resolve())
    assert snapshot(backup) == expected
    assert unrelated.read_text() == "unrelated" and external.read_text() == "external"
    if failure in ("persistent", "once"):
        assert "restore-denied" in message and len(attempts) == 1
        assert not output.exists()
        if failure == "once":
            fail(backup, output)
        else:
            replace(backup, output)
        assert snapshot(output) == expected
    elif failure == "occupied":
        assert snapshot(output) == {"new": b"new owner"}
    else:
        assert output.is_symlink()
    assert len(list(office.temp.iterdir())) == 1


@pytest.mark.parametrize("case", ["success", "publish_failure", "no_previous", "backup_failure", "invalid_xml"])
def test_unpack_cleanup_and_normal_recovery(office, tmp_path, monkeypatch, case):
    source_tree = parts(tmp_path / "source", "docx")
    if case == "invalid_xml":
        put(source_tree, "word/document.xml", "<broken>")
    source = archive(source_tree, tmp_path / "input.docx")
    output = tmp_path / "output"
    if case != "no_previous":
        put(output, "keep", "previous")
    unrelated = put(office.temp, "user-owned/keep", "leave alone")
    replace = os.replace

    def fail(src, dst):
        if case in ("publish_failure", "no_previous") and Path(src).name == "parts":
            raise PermissionError("publish-denied")
        if case == "backup_failure" and Path(src) == output:
            raise PermissionError("backup-denied")
        return replace(src, dst)

    monkeypatch.setattr(office.unpack.os, "replace", fail)
    ok, message = office.unpack.unpack(source, output, False, False)
    assert ok is (case == "success"), message
    if case == "success":
        assert snapshot(output) == snapshot(source_tree)
    elif case == "no_previous":
        assert not output.exists()
    else:
        assert snapshot(output) == {"keep": b"previous"}
    assert unrelated.read_text() == "leave alone"
    assert list(office.temp.iterdir()) == [unrelated.parent]


def test_private_temp_alias_does_not_allow_external_symlinks(office, tmp_path, monkeypatch):
    # Model /var -> /private/var only for the internally created staging root.
    alias = tmp_path / "temp-alias"
    alias.symlink_to(office.temp, target_is_directory=True)
    monkeypatch.setenv("TMPDIR", str(alias))
    source = parts(tmp_path / "source", "docx")
    original = archive(source, tmp_path / "original.docx")
    output = tmp_path / "out.docx"
    ok, message = office.pack.pack(source, output, original)
    assert ok, message
    assert office.unpack.unpack(output, tmp_path / "unpacked", False, False)[0]
    external = tmp_path / "source-alias"
    external.symlink_to(source, target_is_directory=True)
    before = output.read_bytes()
    assert not office.pack.pack(external, output, original)[0]
    assert output.read_bytes() == before
    assert not list(office.temp.iterdir())
