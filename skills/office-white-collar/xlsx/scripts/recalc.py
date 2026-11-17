"""Recalculate Excel formulas with a private LibreOffice profile.

A successful process exit alone does not verify recalculation. The macro must
confirm its save, and every formula must have a cached result.
"""

import json
import posixpath
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from zipfile import ZipFile

from office.soffice import get_soffice_env
from openpyxl import load_workbook

MACRO_FILENAME = "Module1.xba"
RECALCULATE_MACRO = """<?xml version="1.0" encoding="UTF-8"?>
<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module1" script:language="StarBasic">
    Sub RecalculateAndSave()
      Dim doc As Object
      Dim loadProperties(2) As New com.sun.star.beans.PropertyValue
      Dim receipt As Integer
      On Error GoTo Failed
      loadProperties(0).Name = "Hidden"
      loadProperties(0).Value = True
      loadProperties(1).Name = "MacroExecutionMode"
      loadProperties(1).Value = com.sun.star.document.MacroExecMode.NEVER_EXECUTE
      loadProperties(2).Name = "UpdateDocMode"
      loadProperties(2).Value = com.sun.star.document.UpdateDocMode.NO_UPDATE
      doc = StarDesktop.loadComponentFromURL("{document_uri}", "_blank", 0, loadProperties())
      If IsNull(doc) Or IsEmpty(doc) Then GoTo Failed
      doc.calculateAll()
      doc.store()
      doc.close(True)
      receipt = FreeFile
      Open "{receipt_path}" For Output As #receipt
      Print #receipt, "recalculated"
      Close #receipt
      StarDesktop.terminate()
      Exit Sub
    Failed:
      On Error Resume Next
      If receipt &lt;&gt; 0 Then Close #receipt
      Kill "{receipt_path}"
      doc.close(True)
      StarDesktop.terminate()
    End Sub
</script:module>"""


def setup_libreoffice_macro(profile_dir, completion_file, filename):
    """Install into an initialized, caller-owned temporary profile only."""
    basic_dir = Path(profile_dir) / "user" / "basic"
    macro_dir = basic_dir / "Standard"
    macro_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = escape(str(completion_file).replace('"', '""'))
    document_uri = escape(Path(filename).resolve().as_uri())
    (macro_dir / MACRO_FILENAME).write_text(
        RECALCULATE_MACRO.format(document_uri=document_uri, receipt_path=receipt_path),
        encoding="utf-8"
    )
    (macro_dir / "script.xlb").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<library:library xmlns:library="http://openoffice.org/2000/library" '
        'library:name="Standard" library:readonly="false" library:passwordprotected="false">'
        '<library:element library:name="Module1"/></library:library>', encoding="utf-8"
    )
    (basic_dir / "script.xlc").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<library:libraries xmlns:library="http://openoffice.org/2000/library" '
        'xmlns:xlink="http://www.w3.org/1999/xlink">'
        '<library:library library:name="Standard" library:link="false" '
        f'xlink:href="{escape((macro_dir / "script.xlb").as_uri())}"/>'
        '</library:libraries>', encoding="utf-8"
    )


def _empty_string_formula_caches(filename):
    """Retain XML evidence that openpyxl collapses to None for empty strings.

    Only a formula cell explicitly typed str with a present, empty v qualifies.
    Resolve worksheet parts through workbook relationships, never sheet order.
    """
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rel_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    empty_strings = set()
    with ZipFile(filename) as archive:
        package = ET.fromstring(archive.read("_rels/.rels"))
        workbook_part = next(
            rel.get("Target").lstrip("/") for rel in package
            if rel.get("Type", "").endswith("/officeDocument")
            and rel.get("TargetMode") != "External"
        )
        workbook_dir = posixpath.dirname(workbook_part)
        workbook = ET.fromstring(archive.read(workbook_part))
        rels_part = posixpath.join(workbook_dir, "_rels", posixpath.basename(workbook_part) + ".rels")
        relationships = ET.fromstring(archive.read(rels_part))
        worksheets = {
            rel.get("Id"): rel.get("Target") for rel in relationships
            if rel.get("Type", "").endswith("/worksheet")
            and rel.get("TargetMode") != "External"
        }
        for sheet in workbook.findall(f"{ns}sheets/{ns}sheet"):
            target = worksheets.get(sheet.get(f"{rel_ns}id"))
            if target is None:  # Chartsheets have no formula caches.
                continue
            part = posixpath.normpath(posixpath.join(workbook_dir, target)).lstrip("/")
            xml = ET.fromstring(archive.read(part))
            for cell in xml.iter(f"{ns}c"):
                value = cell.find(f"{ns}v")
                if (cell.get("t") == "str" and cell.find(f"{ns}f") is not None
                        and value is not None and not value.text):
                    empty_strings.add((sheet.get("name"), cell.get("r")))
    return empty_strings


def _inspect_caches(filename):
    empty_strings = _empty_string_formula_caches(filename)
    wb = load_workbook(filename, data_only=True)
    try:
        wb_formulas = load_workbook(filename, data_only=False)
        try:
            error_details = {}
            formula_count = 0
            missing = []

            for sheet in wb_formulas:
                cached_sheet = wb[sheet.title]
                for row in sheet.iter_rows():
                    for cell in row:
                        cached = cached_sheet[cell.coordinate]
                        location = f"{sheet.title}!{cell.coordinate}"
                        if cell.data_type == "f":
                            formula_count += 1
                            if cached.value is None and (sheet.title, cell.coordinate) not in empty_strings:
                                missing.append(location)
                        # OOXML error cells carry type e. Text may mention an
                        # error literally; new Excel error values are open-ended.
                        if cached.data_type == "e":
                            error_details.setdefault(cached.value, []).append(location)

            total_errors = sum(len(items) for items in error_details.values())
            return {
                "status": "unverified" if missing else (
                    "errors_found" if total_errors else "success"
                ),
                "total_errors": total_errors,
                "total_formulas": formula_count,
                "missing_cached_values": len(missing),
                "missing_cache_locations": missing[:20],
                "error_summary": {
                    err: {"count": len(locations), "locations": locations[:20]}
                    for err, locations in error_details.items() if locations
                },
            }
        finally:
            wb_formulas.close()
    finally:
        wb.close()


def recalc(filename, timeout=30):
    if not Path(filename).is_file():
        return {"status": "recalculation_failed", "error": f"File {filename} does not exist"}
    if timeout <= 0:
        return {"status": "recalculation_failed", "error": "Timeout must be positive"}

    try:
        deadline = time.monotonic() + timeout
        env = get_soffice_env()
        with tempfile.TemporaryDirectory(prefix="xlsx-recalc-") as task_dir:
            task_path = Path(task_dir)
            profile = task_path / "profile"
            completion_file = task_path / "recalculated.ok"
            base_cmd = [
                "soffice",
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless",
                "--norestore",
            ]
            # LibreOffice seeds Standard/Module1.xba on first launch. Wait for
            # that initialization to finish before installing our own module.
            for phase, cmd in (
                ("profile initialization", base_cmd + ["--terminate_after_init"]),
                ("recalculation", base_cmd + ["macro:///Standard.Module1.RecalculateAndSave()"]),
            ):
                if phase == "recalculation":
                    setup_libreoffice_macro(profile, completion_file, filename)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(cmd, timeout)
                result = subprocess.run(
                    cmd, capture_output=True, text=True, env=env, timeout=remaining
                )
                if result.returncode != 0:
                    return {
                        "status": "recalculation_failed",
                        "error": result.stderr or f"LibreOffice {phase} failed",
                        "returncode": result.returncode,
                    }
            if (not completion_file.is_file()
                    or completion_file.read_text(encoding="utf-8").strip() != "recalculated"):
                return {
                    "status": "unverified",
                    "error": "LibreOffice did not confirm recalculation and save",
                }
            return _inspect_caches(filename)
    except subprocess.TimeoutExpired:
        return {
            "status": "recalculation_failed",
            "error": f"LibreOffice recalculation timed out after {timeout} seconds; not verified",
        }
    except Exception as exc:
        return {"status": "recalculation_failed", "error": str(exc)}


def main():
    if len(sys.argv) < 2:
        print("Usage: python recalc.py <excel_file> [timeout_seconds]")
        print("Returns JSON: status, total_errors, total_formulas, error_summary,")
        print("missing_cached_values, missing_cache_locations (when inspection ran).")
        print("Status: success, errors_found, unverified, or recalculation_failed.")
        sys.exit(1)

    filename = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    result = recalc(filename, timeout)
    print(json.dumps(result, indent=2))
    if result["status"] != "success":
        sys.exit(1)


if __name__ == "__main__":
    main()
