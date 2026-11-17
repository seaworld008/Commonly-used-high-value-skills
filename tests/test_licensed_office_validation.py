# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Offline OOXML contracts. All documents are synthetic; Office is never run."""

import importlib
import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import zipfile

from lxml import etree
import pytest

ROOT = Path(__file__).resolve().parents[1] / 'skills/office-white-collar'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
X = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'


def put(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def relationships(*items):
    return f'<Relationships xmlns="{REL}">' + ''.join(
        f'<Relationship Id="{rid}" Type="{R}/{kind}" Target="{target}"/>'
        for rid, kind, target in items) + '</Relationships>'


def fixture(root, family):
    root.mkdir(parents=True, exist_ok=True)
    types = {}
    if family == 'docx':
        main = 'word/document.xml'
        put(root, main, f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p></w:body></w:document>')
        types[main] = 'wordprocessingml.document.main'
    elif family == 'xlsx':
        main = 'xl/workbook.xml'
        put(root, main, f'<workbook xmlns="{X}" xmlns:r="{R}"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
        put(root, 'xl/worksheets/sheet1.xml', f'<worksheet xmlns="{X}"><sheetData><row r="1"><c r="A1"><v>4</v></c></row></sheetData></worksheet>')
        put(root, 'xl/_rels/workbook.xml.rels', relationships(('rId1', 'worksheet', 'worksheets/sheet1.xml')))
        types[main] = 'spreadsheetml.sheet.main'
        types['xl/worksheets/sheet1.xml'] = 'spreadsheetml.worksheet'
    else:
        main = 'ppt/presentation.xml'
        put(root, main, f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst><p:sldSz cx="9144000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>')
        put(root, 'ppt/_rels/presentation.xml.rels', relationships(('rId1', 'slide', 'slides/slide1.xml')))
        put(root, 'ppt/slides/slide1.xml', f'<p:sld xmlns:p="{P}" xmlns:a="{A}"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld></p:sld>')
        types[main] = 'presentationml.presentation.main'
        types['ppt/slides/slide1.xml'] = 'presentationml.slide'
    put(root, '_rels/.rels', relationships(('rId1', 'officeDocument', main)))
    overrides = ''.join(f'<Override PartName="/{part}" ContentType="application/vnd.openxmlformats-officedocument.{kind}+xml"/>' for part, kind in types.items())
    put(root, '[Content_Types].xml', f'<Types xmlns="{CT}"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>{overrides}</Types>')
    return root


def packed(root, family):
    path = root.parent / f'{root.name}.{family}'
    with zipfile.ZipFile(path, 'w') as zf:
        for item in root.rglob('*'):
            if item.is_file():
                zf.write(item, item.relative_to(root).as_posix())
    return path


def cli(skill, script, *args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    return subprocess.run([sys.executable, str(ROOT / skill / 'scripts' / script), *map(str, args)],
                          capture_output=True, text=True, timeout=30, env=env)


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.fixture
def modules(monkeypatch):
    # Load only reconstructed validators/helpers and the preserved soffice module.
    for key in list(sys.modules):
        if key in ('office', 'helpers', 'validators') or key.startswith(('office.', 'helpers.', 'validators.')):
            monkeypatch.delitem(sys.modules, key)
    monkeypatch.syspath_prepend(str(ROOT / 'pptx/scripts'))
    monkeypatch.syspath_prepend(str(ROOT / 'pptx/scripts/office'))
    validators = importlib.import_module('validators')
    helpers = importlib.import_module('helpers')

    def load(skill, filename):
        path = ROOT / skill / 'scripts' / filename
        spec = importlib.util.spec_from_file_location('licensed_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    yield SimpleNamespace(v=validators, h=helpers, load=load)
    for key in list(sys.modules):
        if key in ('office', 'helpers', 'validators') or key.startswith(('office.', 'helpers.', 'validators.')):
            sys.modules.pop(key, None)


@pytest.mark.parametrize('skill', ['docx', 'pptx', 'xlsx'])
@pytest.mark.parametrize('family', ['docx', 'pptx', 'xlsx'])
def test_all_cli_copies_validate_real_small_packages_without_writing(skill, family, tmp_path):
    root = fixture(tmp_path / 'unpacked', family)
    before = snapshot(root)
    result = cli(skill, 'office/validate.py', root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert snapshot(root) == before
    package = packed(root, family)
    content = package.read_bytes()
    result = cli(skill, 'office/validate.py', package)
    assert result.returncode == 0, result.stdout + result.stderr
    assert package.read_bytes() == content


@pytest.mark.parametrize('family', ['docx', 'pptx', 'xlsx'])
@pytest.mark.parametrize('damage', ['xml', 'relationship', 'content_type', 'schema', 'dtd', 'missing_rels', 'wrong_main_type', 'wrong_root_relation'])
def test_rejects_real_package_defects(family, damage, tmp_path):
    root = fixture(tmp_path / 'case', family)
    main = {'docx': 'word/document.xml', 'pptx': 'ppt/presentation.xml', 'xlsx': 'xl/workbook.xml'}[family]
    part = root / main
    if damage == 'xml':
        part.write_text('<broken>')
    elif damage == 'relationship':
        put(root, '_rels/.rels', relationships(('rId1', 'officeDocument', '../outside.xml')))
    elif damage == 'content_type':
        put(root, '[Content_Types].xml', f'<Types xmlns="{CT}"/>')
    elif damage == 'schema':
        part.write_text(part.read_text().replace('>', ' impossible="1">', 1))
    elif damage == 'dtd':
        part.write_text('<!DOCTYPE document [<!ENTITY x SYSTEM "file:///unread-secret">]>' + part.read_text())
    elif damage == 'wrong_main_type':
        ct = root / '[Content_Types].xml'
        ct.write_text(ct.read_text().replace('.main+xml', '.invalid+xml'))
    elif damage == 'wrong_root_relation':
        put(root, '_rels/.rels', relationships(('rId1', 'image', main)))
    else:
        (root / '_rels/.rels').unlink()
    before = snapshot(root)
    result = cli(family, 'office/validate.py', root)
    assert result.returncode != 0, result.stdout
    assert snapshot(root) == before


@pytest.mark.parametrize('name,mode', [('../escape', 0), ('/absolute', 0), ('a\\b', 0),
                                     ('link', stat.S_IFLNK | 0o777), ('fifo', stat.S_IFIFO | 0o600)])
def test_archive_preflight_rejects_before_extracting_any_member(name, mode, modules, tmp_path):
    package = tmp_path / 'bad.zip'
    with zipfile.ZipFile(package, 'w') as zf:
        zf.writestr('first.xml', '<ok/>')
        item = zipfile.ZipInfo(name)
        item.external_attr = mode << 16
        zf.writestr(item, 'payload')
    out = tmp_path / 'out'
    out.mkdir()
    with zipfile.ZipFile(package) as zf, pytest.raises(ValueError):
        modules.h.safe_extract(zf, out)
    assert not list(out.iterdir())


def test_directory_symlink_and_fifo_rejected(modules, tmp_path):
    root = fixture(tmp_path / 'case', 'docx')
    outside = put(tmp_path, 'outside.xml', '<secret/>')
    (root / 'word/link.xml').symlink_to(outside)
    with pytest.raises(ValueError):
        modules.v.DOCXSchemaValidator(root)
    (root / 'word/link.xml').unlink()
    os.mkfifo(root / 'pipe.xml')
    with pytest.raises(ValueError):
        modules.v.DOCXSchemaValidator(root)
    assert outside.read_text() == '<secret/>'


def test_schema_path_and_external_import_are_bounded(modules, tmp_path):
    root = fixture(tmp_path / 'case', 'docx')
    v = modules.v.DOCXSchemaValidator(root)
    schema = put(tmp_path, 'external.xsd', '<schema/>')
    ok, errors = v._validate_single_file_xsd(root / 'word/document.xml', root, schema)
    assert ok is False
    assert any('outside bundled schemas' in e for e in errors)


def test_explicit_repair_persists_and_default_preserves_evidence(tmp_path):
    root = fixture(tmp_path / 'case', 'docx')
    doc = root / 'word/document.xml'
    doc.write_text(doc.read_text().replace('Hello', ' Hello '))
    package = packed(root, 'docx')
    before = package.read_bytes()
    result = cli('docx', 'office/validate.py', package)
    assert result.returncode == 1
    assert package.read_bytes() == before
    result = cli('docx', 'office/validate.py', package, '--auto-repair')
    assert result.returncode == 0, result.stdout + result.stderr
    with zipfile.ZipFile(package) as zf:
        assert b'xml:space="preserve"' in zf.read('word/document.xml')
    assert 'Wrote repaired file' in result.stdout


def test_missing_relationship_file_cannot_hide_rid(modules, tmp_path):
    root = fixture(tmp_path / 'case', 'xlsx')
    (root / 'xl/_rels/workbook.xml.rels').unlink()
    assert modules.v.BaseSchemaValidator(root).validate_all_relationship_ids() is False


def test_comment_legacy_api_and_cli_escaping_reply_and_markers(modules, tmp_path):
    comment = modules.load('docx', 'comment.py')
    root = fixture(tmp_path / 'case', 'docx')
    cid, para, message = comment.add_comment(root, 7, 'a < b & “quoted”', 'A "B"', 'AB')
    assert cid == 7 and para and '7' in message
    result = cli('docx', 'comment.py', root, 8, 'reply', '--parent', 7)
    assert result.returncode == 0, result.stderr
    comments = etree.parse(str(root / 'word/comments.xml'))
    assert comments.find(f'.//{{{W}}}t').text == 'a < b & “quoted”'
    assert comments.find(f'.//{{{W}}}comment').get(f'{{{W}}}author') == 'A "B"'
    assert len(comments.findall(f'.//{{{W}}}comment')) == 2
    v = modules.v.DOCXSchemaValidator(root)
    assert v.validate_file_references()
    assert v.validate_content_types()
    before = snapshot(root)
    with pytest.raises(ValueError, match='already exists'):
        comment.add_comment(root, 7, 'duplicate')
    with pytest.raises(ValueError, match='parent'):
        comment.add_comment(root, 9, 'reply', parent_id=555)
    assert snapshot(root) == before
    document = root / 'word/document.xml'
    document.write_text(document.read_text().replace('<w:p>', '<w:p><w:commentRangeStart w:id="7"/>'))
    assert not modules.v.DOCXSchemaValidator(root).validate_comment_markers()


def test_redlining_detects_untracked_and_accepts_tracked_edits(modules, tmp_path):
    root = fixture(tmp_path / 'case', 'docx')
    original = packed(root, 'docx')
    path = root / 'word/document.xml'
    old = path.read_text()
    path.write_text(old.replace('Hello', 'Changed'))
    assert not modules.v.RedliningValidator(root, original, author='Editor').validate()
    path.write_text(old.replace('<w:r><w:t>Hello</w:t></w:r>', '<w:del w:id="1" w:author="Editor"><w:r><w:delText>Hello</w:delText></w:r></w:del><w:ins w:id="2" w:author="Editor"><w:r><w:t>Changed</w:t></w:r></w:ins>'))
    validator = modules.v.RedliningValidator(root, original, author='Editor')
    assert validator.validate()
    assert '[-' in validator._get_git_word_diff('Hello', 'Changed')
    assert 'FAILED' in validator._generate_detailed_diff('Hello', 'Changed')


def test_add_slide_registers_and_clean_removes_orphans(modules, tmp_path):
    root = fixture(tmp_path / 'case', 'pptx')
    add = modules.load('pptx', 'add_slide.py')
    clean = modules.load('pptx', 'clean.py')
    assert add.duplicate_slide(root, 'slide1.xml') == 'slide2.xml'
    assert modules.v.PPTXSchemaValidator(root).validate()
    before = snapshot(root)
    with pytest.raises(ValueError):
        add.duplicate_slide(root, '../../outside.xml')
    assert snapshot(root) == before
    # Orphan slide has a referenced image; both should disappear in one cleanup.
    put(root, 'ppt/slides/slide9.xml', (root / 'ppt/slides/slide1.xml').read_text())
    put(root, 'ppt/slides/_rels/slide9.xml.rels', relationships(('rId1', 'image', '../media/orphan.png')))
    put(root, 'ppt/media/orphan.png', 'synthetic image')
    ct = root / '[Content_Types].xml'
    ct.write_text(ct.read_text().replace('</Types>', '<Override PartName="/ppt/slides/slide9.xml" ContentType="application/xml"/></Types>'))
    assert Path('ppt/media/orphan.png') in clean.get_slide_referenced_files(root)
    removed = clean.clean_unused_files(root)
    assert {'ppt/slides/slide9.xml', 'ppt/media/orphan.png'} <= set(removed)
    assert 'slide9.xml' not in ct.read_text()
    assert clean.clean_unused_files(root) == []
    assert modules.v.PPTXSchemaValidator(root).validate()


def test_clean_malformed_package_preserves_files(modules, tmp_path):
    root = fixture(tmp_path / 'case', 'pptx')
    put(root, 'ppt/bad.xml', '<broken>')
    clean = modules.load('pptx', 'clean.py')
    before = snapshot(root)
    with pytest.raises(etree.XMLSyntaxError):
        clean.clean_unused_files(root)
    assert snapshot(root) == before


@pytest.mark.parametrize('failure', ['office_nonzero', 'office_missing', 'office_timeout', 'image_nonzero', 'image_empty'])
def test_thumbnail_process_failure_never_reports_success(failure, modules, tmp_path, monkeypatch):
    root = fixture(tmp_path / 'case', 'pptx')
    package = packed(root, 'pptx')
    thumb = modules.load('pptx', 'thumbnail.py')
    temp = tmp_path / 'render'
    temp.mkdir()

    def office(args, **kwargs):
        assert kwargs['timeout'] == 120
        assert args[0].startswith('-env:UserInstallation=file:')
        if failure == 'office_timeout':
            raise subprocess.TimeoutExpired(args, 120)
        if failure != 'office_missing':
            (temp / 'case.pdf').write_bytes(b'synthetic PDF')
        return SimpleNamespace(returncode=1 if failure == 'office_nonzero' else 0, stderr='stand-in', stdout='')

    monkeypatch.setattr(thumb, 'run_soffice', office)
    run = Mock(return_value=SimpleNamespace(returncode=1 if failure == 'image_nonzero' else 0))
    monkeypatch.setattr(thumb.subprocess, 'run', run)
    with pytest.raises((RuntimeError, subprocess.TimeoutExpired)):
        thumb.convert_to_images(package, temp)
    if failure.startswith('office_'):
        run.assert_not_called()


def test_thumbnail_order_hidden_labels_and_render_count(modules, tmp_path):
    root = fixture(tmp_path / 'case', 'pptx')
    thumb = modules.load('pptx', 'thumbnail.py')
    assert thumb.get_slide_info(packed(root, 'pptx')) == [{'name': 'slide1.xml', 'hidden': False}]
    with pytest.raises(ValueError, match='mislabeled'):
        thumb.build_slide_list([{'name': 'slide1.xml', 'hidden': False}], [], tmp_path)
    slides = thumb.build_slide_list([{'name': 'slide2.xml', 'hidden': True}], [], tmp_path)
    assert slides[0][1] == 'slide2.xml (hidden)'
    output = thumb.create_grids(slides, 1, 120, tmp_path / 'grid.jpg')
    assert len(output) == 1 and Path(output[0]).is_file()


@pytest.mark.parametrize('family', ['docx', 'pptx', 'xlsx'])
def test_original_baseline_cli_and_nested_xsd_defects(family, tmp_path):
    root = fixture(tmp_path / 'case', family)
    original = packed(root, family)
    result = cli(family, 'office/validate.py', root, '--original', original)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'baseline' in result.stdout
    if family == 'xlsx':
        part = root / 'xl/worksheets/sheet1.xml'
        part.write_text(part.read_text().replace('<row r="1">', '<row r="invalid">'))
    elif family == 'pptx':
        part = root / 'ppt/slides/slide1.xml'
        part.write_text(part.read_text().replace('<p:cNvPr id="1"', '<p:cNvPr id="invalid"'))
    else:
        part = root / 'word/document.xml'
        part.write_text(part.read_text().replace('<w:p>', '<w:p impossible="1">'))
    result = cli(family, 'office/validate.py', root, '--original', original)
    assert result.returncode == 1, result.stdout + result.stderr


def test_repair_failure_does_not_claim_saved_success(modules, tmp_path, monkeypatch, capsys):
    root = fixture(tmp_path / 'case', 'docx')
    doc = root / 'word/document.xml'
    doc.write_text(doc.read_text().replace('Hello', ' Hello '))
    package = packed(root, 'docx')
    before = package.read_bytes()
    validate = modules.load('docx', 'office/validate.py')
    monkeypatch.setattr(validate, 'rezip', Mock(side_effect=PermissionError('synthetic read-only destination')))
    monkeypatch.setattr(sys, 'argv', ['validate.py', str(package), '--auto-repair'])
    with pytest.raises(SystemExit) as exc:
        validate.main()
    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert 'not rewritten' in output and 'All validations PASSED' not in output
    assert package.read_bytes() == before


def test_para_id_repair_is_explicit_and_keeps_comment_links(modules, tmp_path):
    root = fixture(tmp_path / 'case', 'docx')
    w14 = 'http://schemas.microsoft.com/office/word/2010/wordml'
    doc = root / 'word/document.xml'
    doc.write_text(doc.read_text().replace('<w:p>', f'<w:p xmlns:w14="{w14}" w14:paraId="FFFFFFFF">'))
    validator = modules.v.DOCXSchemaValidator(root)
    assert not validator.validate_id_constraints()
    before = doc.read_bytes()
    assert not validator.validate()
    assert doc.read_bytes() == before
    assert validator.repair() == 1
    assert validator.validate()


def test_comment_complete_package_passes_after_anchoring(modules, tmp_path):
    root = fixture(tmp_path / 'case', 'docx')
    comment = modules.load('docx', 'comment.py')
    comment.add_comment(root, 0, 'Review & clarify')
    doc = root / 'word/document.xml'
    doc.write_text(doc.read_text().replace('<w:p>', '<w:p><w:commentRangeStart w:id="0"/>').replace('</w:p>', '<w:commentRangeEnd w:id="0"/><w:r><w:commentReference w:id="0"/></w:r></w:p>'))
    assert modules.v.DOCXSchemaValidator(root).validate()


def test_create_layout_slide_and_duplicate_do_not_share_notes(modules, tmp_path):
    root = fixture(tmp_path / 'case', 'pptx')
    add = modules.load('pptx', 'add_slide.py')
    layout = (root / 'ppt/slides/slide1.xml').read_text().replace('p:sld', 'p:sldLayout')
    put(root, 'ppt/slideLayouts/slideLayout1.xml', layout)
    ct = root / '[Content_Types].xml'
    ct.write_text(ct.read_text().replace('</Types>', '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/></Types>'))
    assert add.create_slide_from_layout(root, 'slideLayout1.xml') == 'slide2.xml'
    assert modules.v.PPTXSchemaValidator(root).validate()
    rels = root / 'ppt/slides/_rels/slide2.xml.rels'
    rels.write_text(rels.read_text().replace('</Relationships>', f'<Relationship Id="rId2" Type="{R}/notesSlide" Target="../notesSlides/notesSlide1.xml"/></Relationships>'))
    assert add.duplicate_slide(root, 'slide2.xml') == 'slide3.xml'
    assert 'notesSlide' not in (root / 'ppt/slides/_rels/slide3.xml.rels').read_text()


def test_clean_alternate_namespace_prefix_keeps_active_slide(modules, tmp_path):
    root = fixture(tmp_path / 'case', 'pptx')
    pres = root / 'ppt/presentation.xml'
    pres.write_text(pres.read_text().replace('xmlns:p=', 'xmlns:deck=').replace('<p:', '<deck:').replace('</p:', '</deck:'))
    clean = modules.load('pptx', 'clean.py')
    before = snapshot(root)
    assert clean.clean_unused_files(root) == []
    assert snapshot(root) == before


def test_thumbnail_stale_output_and_cli_failure_preserve_grid(modules, tmp_path, monkeypatch, capsys):
    root = fixture(tmp_path / 'case', 'pptx')
    package = packed(root, 'pptx')
    thumb = modules.load('pptx', 'thumbnail.py')
    temp = tmp_path / 'render'
    temp.mkdir()
    (temp / 'case.pdf').write_bytes(b'old pdf')
    run = Mock(side_effect=RuntimeError('synthetic conversion unavailable'))
    monkeypatch.setattr(thumb, 'run_soffice', run)
    with pytest.raises(ValueError, match='stale'):
        thumb.convert_to_images(package, temp)
    run.assert_not_called()
    old = put(tmp_path, 'grid.jpg', 'old grid evidence')
    monkeypatch.setattr(sys, 'argv', ['thumbnail.py', str(package), str(tmp_path / 'grid')])
    with pytest.raises(SystemExit) as exc:
        thumb.main()
    assert exc.value.code == 1
    assert old.read_text() == 'old grid evidence'
    assert 'Created' not in capsys.readouterr().out
