#!/usr/bin/env python3
# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Convert Markdown inputs independently, with explicit per-file outcomes.

Usage: batch_convert.py FILE.md [FILE.md ...] [-o DIRECTORY]
Without -o each PDF is placed next to its source. Output-name collisions are
rejected before conversion. A failed task does not remove its previous PDF;
other independent tasks can finish. Any failure makes the process exit nonzero.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from md_to_pdf import markdown_to_pdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--output-dir", "-o", type=str)
    parser.add_argument("--resource-root", help="Explicit local image authorization, applied to each input")
    args = parser.parse_args()
    sources = [Path(name).absolute() for name in args.files]
    outputs = [(Path(args.output_dir).absolute() / source.with_suffix(".pdf").name)
               if args.output_dir else source.with_suffix(".pdf") for source in sources]
    counts = Counter(str(path.resolve()).casefold() for path in outputs)
    input_paths = {str(path.resolve()).casefold() for path in sources}
    results = []
    for source, output in zip(sources, outputs):
        row = {"input": str(source), "output": str(output), "status": "failed", "outputs": []}
        try:
            key = str(output.resolve()).casefold()
            if counts[key] > 1:
                raise ValueError("Multiple inputs map to the same output")
            if key in input_paths:
                raise ValueError("Output would overwrite a batch input")
            if source.suffix.lower() not in {".md", ".markdown"}:
                raise ValueError("Only .md and .markdown inputs are supported")
            result = markdown_to_pdf(source, output, resource_root=args.resource_root)
            if not result.is_file() or not result.stat().st_size:
                raise RuntimeError("Conversion produced no output")
            row.update(status="success", outputs=[str(result)])
        except Exception as exc:
            row["error"] = str(exc)
        results.append(row)
    succeeded = sum(row["status"] == "success" for row in results)
    print(json.dumps({"status": "success" if succeeded == len(results) and succeeded else "failed",
                      "succeeded": succeeded, "failed": len(results) - succeeded,
                      "results": results}, ensure_ascii=False, indent=2))
    return 0 if succeeded == len(results) and succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
