# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Real PDF/PNG regressions; LibreOffice is ALWAYS an explicit offline double."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from urllib.parse import unquote, urlsplit
import zipfile

import pytest

fitz = pytest.importorskip("pymupdf")
pytest.importorskip("markdown_it")
Image = pytest.importorskip("PIL.Image")
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/office-white-collar"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def md():
    return load(SCRIPTS / "pdf/scripts/md_to_pdf.py", "original_markdown_pdf")


@pytest.fixture
def render():
    return load(SCRIPTS / "docx/scripts/render_docx.py", "original_docx_renderer")


def make_pdf(path, sizes=((612, 792),), text="Actual PDF content"):
    with fitz.open() as document:
        for number, (width, height) in enumerate(sizes, 1):
            page = document.new_page(width=width, height=height)
            page.insert_text((40, 60), f"{text} page {number}")
        document.save(path)
    return path


def make_docx(path, *, body="", extras=None, external=None):
    parts = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>Document fixture</w:t></w:r></w:p>' + body +
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/></w:sectPr></w:body></w:document>',
    }
    if external:
        parts["word/_rels/document.xml.rels"] = '<Relationships><Relationship Id="r2" TargetMode="External" Target="' + external + '"/></Relationships>'
    parts.update(extras or {})
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
    return path


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_of(path):
    with fitz.open(path) as document:
        return "\n".join(page.get_text() for page in document)


def test_markdown_real_chinese_lists_table_code_and_pagination(md, tmp_path):
    source = tmp_path / "中文 空格.md"
    source.write_text("# 中文标题\n正文 English\n1. 第一项\n2. Second item\n\n"
                      "| 姓名 | Value |\n| --- | --- |\n| 张三 | 42 |\n\n"
                      "```python\nprint(123)\n```\n" + "\n\nMore paragraph content. " * 120, encoding="utf-8")
    before = file_digest(source)
    output = tmp_path / "报告 空格.pdf"
    assert md.markdown_to_pdf(source, output) == output
    with fitz.open(output) as document:
        assert len(document) >= 2
        text = "".join(page.get_text() for page in document)
        for expected in ("中文标题", "正文 English", "1. 第一项", "2. Second item", "张三", "42", "print(123)"):
            assert expected in text
        page = document[0].get_pixmap(dpi=72)
        assert len(set(page.samples)) > 20
    assert file_digest(source) == before
    assert not list(tmp_path.glob(".markdown-pdf-*"))


def test_markdown_nested_list_structure_and_literal_html(md, tmp_path):
    source = tmp_path / "source.md"
    source.write_text('Intro\n- Outer\n  - Inner\n\n<img src="https://invalid.example/x">\n<style>@import "file:///private";</style>')
    output = tmp_path / "out.pdf"
    md.markdown_to_pdf(source, output)
    text = text_of(output)
    assert "Outer" in text and "Inner" in text and "<img" in text and "@import" in text


@pytest.mark.parametrize("content", ["", "![remote](https://invalid.example/pixel.png)", "![local](image.png)"])
def test_markdown_rejected_input_preserves_prior_pdf(md, tmp_path, content):
    source = tmp_path / "source.md"
    source.write_text(content)
    output = make_pdf(tmp_path / "old.pdf")
    before = output.read_bytes()
    with pytest.raises(ValueError):
        md.markdown_to_pdf(source, output)
    assert output.read_bytes() == before
    assert not list(tmp_path.glob(".markdown-pdf-*"))


def test_markdown_layout_failure_preserves_output(md, tmp_path, monkeypatch):
    source = tmp_path / "source.md"
    source.write_text("# New content")
    output = make_pdf(tmp_path / "old.pdf")
    before = output.read_bytes()
    monkeypatch.setattr(fitz.Story, "draw", lambda *a: (_ for _ in ()).throw(RuntimeError("draw failed")))
    with pytest.raises(RuntimeError, match="draw failed"):
        md.markdown_to_pdf(source, output)
    assert output.read_bytes() == before
    assert not list(tmp_path.glob(".markdown-pdf-*"))


@pytest.mark.parametrize("kind", ["same", "hardlink", "symlink", "directory"])
def test_markdown_protects_input_and_nonregular_outputs(md, tmp_path, kind):
    source = tmp_path / "source.md"
    source.write_text("# Must survive")
    output = tmp_path / "out.pdf"
    if kind == "same":
        output = source
    elif kind == "hardlink":
        os.link(source, output)
    elif kind == "symlink":
        output.symlink_to(source)
    else:
        output.mkdir()
    with pytest.raises(ValueError):
        md.markdown_to_pdf(source, output)
    assert source.read_text() == "# Must survive"


def test_markdown_explicit_image_root_renders_real_image(md, tmp_path):
    source = tmp_path / "source.md"
    picture = tmp_path / "中文 image.png"
    Image.new("RGB", (70, 40), (255, 0, 0)).save(picture)
    source.write_text("# Local picture\n\n![caption](%E4%B8%AD%E6%96%87%20image.png)")
    output = tmp_path / "out.pdf"
    md.markdown_to_pdf(source, output, resource_root=tmp_path)
    with fitz.open(output) as document:
        assert document[0].get_images()
        assert "Local picture" in document[0].get_text()


@pytest.mark.parametrize("target", ["../outside.png", "%2e%2e/outside.png", "link.png", "https://invalid.example/x.png", "data:image/png;base64,AAAA", "vector.svg"])
def test_authorized_images_still_reject_escape_and_network(md, tmp_path, target):
    root = tmp_path / "allowed"
    root.mkdir()
    Image.new("RGB", (2, 2)).save(tmp_path / "outside.png")
    (root / "link.png").symlink_to(tmp_path / "outside.png")
    (root / "vector.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="file:///private"/></svg>')
    source = root / "source.md"
    source.write_text(f"![image]({target})")
    with pytest.raises((ValueError, OSError)):
        md.markdown_to_pdf(source, root / "out.pdf", resource_root=root)
    assert not (root / "out.pdf").exists()


def cli(script, args):
    return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True,
                          text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=60)


def test_batch_partial_failure_reports_each_result_and_nonzero(tmp_path):
    source = tmp_path / "good.md"
    source.write_text("# Real batch\n中文")
    bad = tmp_path / "missing.md"
    old = make_pdf(tmp_path / "missing.pdf")
    before = old.read_bytes()
    result = cli(SCRIPTS / "pdf/scripts/batch_convert.py", [source, bad])
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert (report["status"], report["succeeded"], report["failed"]) == ("failed", 1, 1)
    assert report["results"][1]["outputs"] == []
    assert "Real batch" in text_of(source.with_suffix(".pdf"))
    assert old.read_bytes() == before


def test_batch_collision_does_not_overwrite_and_empty_batch_fails(tmp_path):
    sources = []
    for folder in ("a", "b"):
        directory = tmp_path / folder
        directory.mkdir()
        source = directory / "same.md"
        source.write_text(folder)
        sources.append(source)
    output = tmp_path / "outputs"
    output.mkdir()
    old = make_pdf(output / "same.pdf")
    before = old.read_bytes()
    script = SCRIPTS / "pdf/scripts/batch_convert.py"
    result = cli(script, [*sources, "-o", output])
    assert result.returncode == 1
    assert json.loads(result.stdout)["succeeded"] == 0
    assert old.read_bytes() == before
    assert cli(script, []).returncode != 0


def test_md_cli_missing_dependency_failure_and_default_output(md, tmp_path, monkeypatch):
    source = tmp_path / "说明.md"
    source.write_text("# Command line")
    result = cli(SCRIPTS / "pdf/scripts/md_to_pdf.py", [source])
    assert result.returncode == 0, result.stderr
    assert "Command line" in text_of(source.with_suffix(".pdf"))
    before = source.with_suffix(".pdf").read_bytes()
    monkeypatch.setattr(md, "_dependencies", lambda: (_ for _ in ()).throw(RuntimeError("dependency unavailable")))
    monkeypatch.setattr(sys, "argv", ["md_to_pdf.py", str(source)])
    assert md.main() == 1
    assert source.with_suffix(".pdf").read_bytes() == before


def test_docx_and_pdf_dpi_use_all_sections_pages_and_rotation(render, tmp_path):
    docx = make_docx(tmp_path / "page.docx", body='<w:p><w:pPr><w:sectPr><w:pgSz w:w="15840" w:h="12240"/></w:sectPr></w:pPr></w:p>')
    assert render.calc_dpi_via_ooxml_docx(docx, 792, 792) == 72
    pdf = make_pdf(tmp_path / "mixed.pdf", ((612, 792), (1008, 612)))
    assert render.calc_dpi_via_pdf(pdf, 1008, 792) == 72
    rotated = tmp_path / "rotated.pdf"
    with fitz.open(pdf) as document:
        document[1].set_rotation(90)
        document.save(rotated)
    assert render.calc_dpi_via_pdf(rotated, 1008, 792) == 56
    with pytest.raises(ValueError):
        render.calc_dpi_via_pdf(pdf, 0, 100)


@pytest.fixture
def office_double(render, monkeypatch):
    """No real Office or socket is launched; outputs are real PDFs, labeled synthetic."""
    calls = []
    state = {"mode": "ok"}
    monkeypatch.setattr(render, "_office_binary", lambda: "synthetic-soffice")
    monkeypatch.setattr(render, "_soffice_env", lambda: {"SAL_USE_VCLPLUGIN": "svp", "SYNTHETIC": "1"})

    def run(command, **kwargs):
        assert command[0] == "synthetic-soffice"
        assert kwargs["env"]["SYNTHETIC"] == "1"
        assert kwargs["timeout"] == 120 and kwargs["capture_output"] and kwargs["text"]
        profile = Path(unquote(urlsplit(command[1].split("=", 1)[1]).path))
        assert profile.stat().st_mode & 0o777 == 0o700
        config = (profile / "user/registrymodifications.xcu").read_text()
        assert "DisableMacrosExecution" in config and "<value>true</value>" in config
        assert "MacroSecurityLevel" in config and "<value>3</value>" in config
        assert "--headless" in command and "--norestore" in command
        assert not any("no-sandbox" in value for value in command)
        source = Path(command[-1])
        assert not source.stat().st_mode & 0o222
        assert source.name == "input.docx"
        calls.append((command, profile, source))
        target = Path(command[command.index("--outdir") + 1]) / "input.pdf"
        if state["mode"] == "timeout":
            raise subprocess.TimeoutExpired(command, 120)
        if state["mode"] == "invalid":
            target.write_bytes(b"%PDF- fake truncated output")
        elif state["mode"] != "missing":
            make_pdf(target, ((612, 792), (792, 612)), text="SYNTHETIC Office conversion")
        return subprocess.CompletedProcess(command, 7 if state["mode"] == "nonzero" else 0, "", "synthetic failure")

    monkeypatch.setattr(render.subprocess, "run", run)
    return SimpleNamespace(calls=calls, state=state)


def test_docx_safe_argv_private_profile_real_pdf_png_validation(render, office_double, tmp_path):
    source = make_docx(tmp_path / '中文 document & "quote".docx')
    before = file_digest(source)
    output = tmp_path / "输出 空格"
    result = render._render(source, output, width=792, height=792)
    assert result["status"] == "success" and result["pages"] == 2 and result["dpi"] == 72
    assert result["dimensions"] == [[612, 792], [792, 612]]
    assert len(result["outputs"]) == 3
    for name in result["outputs"][1:]:
        with Image.open(name) as picture:
            picture.load()
            assert picture.format == "PNG"
            assert picture.convert("L").getextrema()[0] < 100
            assert picture.info["dpi"][0] == pytest.approx(72, abs=0.1)
    assert "SYNTHETIC Office conversion" in text_of(Path(result["outputs"][0]))
    assert file_digest(source) == before
    assert all(not profile.exists() and not copy.exists() for _, profile, copy in office_double.calls)
    assert not list(output.glob(".docx-render-*"))


@pytest.mark.parametrize("mode", ["nonzero", "timeout", "missing", "invalid"])
def test_office_failure_never_publishes_or_uses_old_pdf(render, office_double, tmp_path, mode):
    source = make_docx(tmp_path / "doc.docx")
    output = tmp_path / "out"
    output.mkdir()
    old = make_pdf(output / "doc.pdf")
    (output / "page-1.png").write_bytes(b"old page must survive")
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    office_double.state["mode"] = mode
    with pytest.raises(Exception):
        render.rasterize(source, output, 72)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    assert office_double.calls and all(not p.exists() for _, p, _ in office_double.calls)
    assert old.is_file()


@pytest.mark.parametrize("body,extras,external", [
    ("", {}, "https://invalid.example/image.png"),
    ("", {}, "file:///private/document"),
    ("", {"word/vbaProject.bin": b"macro"}, None),
    ('<w:altChunk/>', {}, None),
    ('<w:fldSimple w:instr="DDEAUTO unsafe"/>', {}, None),
    ('<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText>INCLUDE</w:instrText></w:r><w:r><w:instrText>TEXT file:///private</w:instrText></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>', {}, None),
    ("", {"word/media/image.svg": '<svg/>'}, None),
    ("", {"../escape.xml": '<x/>'}, None),
    ("", {"word/_rels/document.xml.rels": '<Relationships><Relationship Target="../../private"/></Relationships>'}, None),
    ("", {"word/evil.xml": '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///private">]><x>&e;</x>'}, None),
])
def test_unsafe_docx_rejected_before_office(render, office_double, tmp_path, body, extras, external):
    source = make_docx(tmp_path / "unsafe.docx", body=body, extras=extras, external=external)
    with pytest.raises(Exception):
        render.rasterize(source, tmp_path / "out", 72)
    assert not office_double.calls
    assert list((tmp_path / "out").iterdir()) == []


def test_safe_page_fields_and_split_instructions_are_accepted(render, tmp_path):
    docx = make_docx(tmp_path / "fields.docx", body='<w:fldSimple w:instr="NUMPAGES"/>'
                     '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText>PA</w:instrText></w:r>'
                     '<w:r><w:instrText>GE</w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>'
                     '<w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>')
    assert render.calc_dpi_via_ooxml_docx(docx, 612, 792) == 72


def test_existing_profile_and_socket_block_are_not_bypassed(render, tmp_path, monkeypatch):
    source = make_docx(tmp_path / "doc.docx")
    stage = tmp_path / "stage"
    stage.mkdir()
    profile = stage / "profile"
    profile.mkdir()
    canary = profile / "user-macro"
    canary.write_text("untouched")
    with pytest.raises(ValueError, match="new private profile"):
        render.convert_to_pdf(source, profile, stage, "doc")
    assert canary.read_text() == "untouched"
    def blocked():
        raise RuntimeError("local sockets unavailable")
    monkeypatch.setattr(render, "_soffice_env", blocked)
    monkeypatch.setattr(render.subprocess, "run", lambda *a, **k: pytest.fail("Office must not launch"))
    with pytest.raises(RuntimeError, match="local sockets"):
        render.run_cmd_no_check(["synthetic-soffice"])


def test_raster_failure_and_publish_failure_restore_old_set(render, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "input.pdf", ((612, 792), (792, 612)))
    output = tmp_path / "out"
    output.mkdir()
    make_pdf(output / "input.pdf", text="Previous PDF")
    for name in ("page-1.png", "page-2.png", "page-3.png", "unrelated.txt"):
        (output / name).write_bytes(name.encode())
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    real_get = fitz.Page.get_pixmap
    def fail_second(page, *args, **kwargs):
        if page.number == 1:
            raise RuntimeError("second page failure")
        return real_get(page, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(fitz.Page, "get_pixmap", fail_second)
        with pytest.raises(RuntimeError):
            render.rasterize(source, output, 72)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    replace = os.replace
    def fail_publish(src, dst):
        if Path(src).name == "page-2.png" and Path(src).parent.name.startswith(".docx-render-"):
            raise OSError("synthetic publication failure")
        return replace(src, dst)
    with monkeypatch.context() as patch:
        patch.setattr(render.os, "replace", fail_publish)
        with pytest.raises(OSError):
            render.rasterize(source, output, 72)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    pages = render.rasterize(source, output, 72)
    assert [p.name for p in pages] == ["page-1.png", "page-2.png"]
    assert not (output / "page-3.png").exists()
    assert (output / "unrelated.txt").read_bytes() == b"unrelated.txt"


@pytest.mark.parametrize("kind", ["directory", "symlink", "hardlink"])
def test_raster_publication_conflicts_preserve_input(render, tmp_path, kind):
    source = make_pdf(tmp_path / "input.pdf")
    before = source.read_bytes()
    output = tmp_path / "out"
    output.mkdir()
    target = output / "page-1.png"
    if kind == "directory":
        target.mkdir()
    elif kind == "symlink":
        target.symlink_to(source)
    else:
        os.link(source, target)
    with pytest.raises(ValueError):
        render.rasterize(source, output, 72)
    assert source.read_bytes() == before
    assert not (output / "input.pdf").exists()


def test_render_cli_real_pdf_bounds_and_failure_status(tmp_path):
    source = make_pdf(tmp_path / "real input.pdf", ((612, 792), (792, 612)))
    script = SCRIPTS / "docx/scripts/render_docx.py"
    output = tmp_path / "pages"
    result = cli(script, [source, "--output_dir", output, "--width", "400", "--height", "400"])
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["pages"] == 2 and report["dpi"] == 36
    assert report["dimensions"] == [[306, 396], [396, 306]]
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    failed = cli(script, [source, "--output_dir", output, "--dpi", "0"])
    assert failed.returncode == 1
    assert json.loads(failed.stdout)["outputs"] == []
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


def test_batch_complete_success_has_existing_valid_output_manifest(tmp_path):
    sources = [tmp_path / "one.md", tmp_path / "two 中文.markdown"]
    for index, source in enumerate(sources):
        source.write_text(f"# Batch document {index}\n中文正文")
    result = cli(SCRIPTS / "pdf/scripts/batch_convert.py", [*sources, "-o", tmp_path / "pdfs"])
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "success" and report["succeeded"] == 2 and report["failed"] == 0
    for index, row in enumerate(report["results"]):
        assert row["outputs"] == [row["output"]]
        assert f"Batch document {index}" in text_of(Path(row["output"]))


def test_invalid_dpi_does_not_launch_office(render, office_double, tmp_path):
    source = make_docx(tmp_path / "doc.docx")
    with pytest.raises(ValueError):
        render.rasterize(source, tmp_path / "out", 0)
    assert not office_double.calls
    assert not (tmp_path / "out").exists()


def test_failed_rollback_preserves_recovery_files_and_attempts_other_restores(render, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "input.pdf", ((612, 792), (792, 612)))
    output = tmp_path / "out"
    output.mkdir()
    previous = make_pdf(output / "input.pdf", text="Retain this PDF").read_bytes()
    (output / "page-1.png").write_bytes(b"first old page")
    (output / "page-2.png").write_bytes(b"second old page")
    replace = os.replace
    def fail(src, dst):
        src = Path(src)
        if src.name == "page-2.png" and src.parent.name.startswith(".docx-render-"):
            raise OSError("publish failure")
        if src.name == "page-1.png" and src.parent.name == "previous":
            raise OSError("restore failure")
        return replace(src, dst)
    monkeypatch.setattr(render.os, "replace", fail)
    with pytest.raises(render.PublicationError, match="recovery needs attention") as failure:
        render.rasterize(source, output, 72)
    assert failure.value.outputs == []
    assert Path(failure.value.recovery_dir).is_dir()
    assert (output / "input.pdf").read_bytes() == previous
    assert (output / "page-2.png").read_bytes() == b"second old page"
    retained = list(output.glob(".docx-render-*/previous/page-1.png"))
    assert len(retained) == 1 and retained[0].read_bytes() == b"first old page"


def test_encrypted_pdf_rejected_without_replacing_outputs(render, tmp_path):
    source = tmp_path / "encrypted.pdf"
    with fitz.open() as document:
        document.new_page().insert_text((40, 60), "Private fixture")
        document.save(source, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="test-only", owner_pw="test-owner")
    output = tmp_path / "out"
    output.mkdir()
    previous = make_pdf(output / "encrypted.pdf").read_bytes()
    with pytest.raises(ValueError, match="unencrypted"):
        render.rasterize(source, output, 72)
    assert (output / "encrypted.pdf").read_bytes() == previous
    assert list(output.iterdir()) == [output / "encrypted.pdf"]


def test_web_link_annotation_is_preserved_without_fetching(md, tmp_path):
    source = tmp_path / "links.md"
    source.write_text("# Links\n[Documentation](https://example.invalid/docs)\n")
    output = md.markdown_to_pdf(source, tmp_path / "links.pdf")
    with fitz.open(output) as document:
        links = document[0].get_links()
        assert links and all(link["uri"] == "https://example.invalid/docs" for link in links)
    source.write_text("[Local escape](../private.txt)")
    previous = output.read_bytes()
    with pytest.raises(ValueError, match="links"):
        md.markdown_to_pdf(source, output)
    assert output.read_bytes() == previous


def test_inert_docx_hyperlinks_are_preserved_without_fetch(render, tmp_path):
    source = make_docx(tmp_path / 'linked.docx')
    with zipfile.ZipFile(source) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    rel = ('<Relationships><Relationship Id="safe-link" '
           'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
           'TargetMode="External" Target="https://example.invalid/reference"/></Relationships>')
    parts['word/_rels/document.xml.rels'] = rel.encode()
    with zipfile.ZipFile(source, 'w') as archive:
        for name, raw in parts.items():
            archive.writestr(name, raw)
    before = source.read_bytes()
    assert render._inspect_docx(source)
    assert source.read_bytes() == before
