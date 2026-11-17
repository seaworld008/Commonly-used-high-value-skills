"""Full primary-source license variants without widening artifact scope."""
from pathlib import Path
import pytest
from scripts.audit_licenses import _has_notice_body

ROOT = Path(__file__).resolve().parents[1]
APACHE = (ROOT / "skills/developer-engineering/frontend-design/LICENSE.txt").read_bytes()
OFL = (ROOT / "skills/product-design/canvas-design/canvas-fonts/InstrumentSerif-OFL.txt").read_bytes()


def test_complete_apache_without_optional_howto_appendix(tmp_path):
    path = tmp_path / "LICENSE.txt"
    assert b"END OF TERMS AND CONDITIONS" in APACHE
    path.write_bytes(APACHE)
    assert _has_notice_body(path, "Apache-2.0")
    path.write_bytes(APACHE.replace(b"perpetual", b"temporary", 1))
    assert not _has_notice_body(path, "Apache-2.0")
    path.write_bytes(APACHE + b"\nRedistribution is prohibited.\n")
    assert not _has_notice_body(path, "Apache-2.0")


def test_original_publisher_https_ofl_notice_and_alterations(tmp_path):
    path = tmp_path / "OFL.txt"
    assert b"https://scripts.sil.org/OFL" in OFL
    path.write_bytes(OFL)
    assert _has_notice_body(path, "OFL-1.1")
    for raw in (OFL.replace(b"https://scripts.sil.org/OFL", b"ftp://scripts.sil.org/OFL"),
                b"import os; os.system('untrusted')\n" + OFL,
                OFL.replace(b"PERMISSION", b"NO PERMISSION", 1)):
        path.write_bytes(raw)
        assert not _has_notice_body(path, "OFL-1.1")
