"""Recalculate Excel formulas with a private LibreOffice profile.

A successful process exit alone does not verify recalculation. The macro must
confirm its save, and every formula must have a cached result.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from office.soffice import get_soffice_env
from openpyxl import load_workbook

MACRO_FILENAME = "Module1.xba"
RECALCULATE_MACRO = """<?xml version="1.0" encoding="UTF-8"?>
<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module1" script:language="StarBasic">
    Sub RecalculateAndSave()
      ThisComponent.calculateAll()
      ThisComponent.store()
      ThisComponent.close(True)
      Dim receipt As Integer
      receipt = FreeFile
      Open "__RECEIPT__" For Output As #receipt
      Print #receipt, "recalculated"
      Close #receipt
      StarDesktop.terminate()
    End Sub
</script:module>"""


def setup_libreoffice_macro(profile_dir, completion_file):
    """Install the macro only inside a caller-owned temporary profile."""
    basic_dir = Path(profile_dir) / "user" / "basic"
    macro_dir = basic_dir / "Standard"
    macro_dir.mkdir(parents=True)
    receipt_path = escape(str(completion_file).replace('"', '""'))
    (macro_dir / MACRO_FILENAME).write_text(
        RECALCULATE_MACRO.replace("__RECEIPT__", receipt_path), encoding="utf-8"
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


def _inspect_caches(filename):
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
                            if cached.value is None:
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
        env = get_soffice_env()
        with tempfile.TemporaryDirectory(prefix="xlsx-recalc-") as task_dir:
            task_path = Path(task_dir)
            profile = task_path / "profile"
            completion_file = task_path / "recalculated.ok"
            setup_libreoffice_macro(profile, completion_file)
            cmd = [
                "soffice",
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless",
                "--norestore",
                str(Path(filename).resolve()),
                "vnd.sun.star.script:Standard.Module1.RecalculateAndSave?language=Basic&location=application",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, env=env, timeout=timeout
            )
            if result.returncode != 0:
                return {
                    "status": "recalculation_failed",
                    "error": result.stderr or "LibreOffice recalculation failed",
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
