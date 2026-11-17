#!/usr/bin/env python3
# Copyright (c) 2026 seaworld008
# SPDX-License-Identifier: MIT
"""Render validated tabular data to deterministic, headless SVG or PNG charts."""

import argparse
import csv
import json
import math
import os
from pathlib import Path
import sys
import tempfile


CHART_TYPES = ("line", "area", "bar", "barh", "scatter", "hist", "waterfall")
COLORS = ("#245A73", "#BE632B", "#67783D", "#88518B", "#397B79", "#9B475B")


def _lazy_imports():
    """Delay optional dependencies so --help also works without them."""
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("chartkit requires matplotlib, numpy and pandas") from exc
    return pd, np, plt


def _read_data(path):
    """Read UTF-8 CSV or a JSON array of row objects; never fill missing cells."""
    pd, _, _ = _lazy_imports()
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as source:
            rows = list(csv.reader(source))
        if not rows or not rows[0] or any(not name.strip() for name in rows[0]):
            raise ValueError("CSV needs nonempty column names")
        if len(set(rows[0])) != len(rows[0]):
            raise ValueError("CSV column names must be unique")
        if any(len(row) != len(rows[0]) for row in rows[1:]):
            raise ValueError("CSV row width differs from header")
        return pd.DataFrame(rows[1:], columns=rows[0])
    if path.suffix.lower() == ".json":
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("JSON object contains a duplicate key")
                result[key] = value
            return result
        with path.open(encoding="utf-8") as source:
            rows = json.load(source, object_pairs_hook=unique_object)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("JSON must be an array of row objects")
        return pd.DataFrame(rows)
    raise ValueError("data extension must be .csv or .json")


def _ensure_outdir(p):
    path = Path(p)
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_chart(df, chart_type, x, y_cols, title, out_path):
    """Render a DataFrame and return its output Path after atomic publication.

    Missing/nonfinite values are errors. Area charts stack nonnegative series;
    waterfall rows are signed changes from zero. Histograms use y observations.
    SVG keeps text as text; PNG is exactly 1200 by 675 pixels.
    """
    pd, np, plt = _lazy_imports()
    if chart_type not in CHART_TYPES:
        raise ValueError("unsupported chart type")
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("data must be a nonempty pandas DataFrame")
    if isinstance(y_cols, str):
        y_cols = [part.strip() for part in y_cols.split(",")]
    else:
        y_cols = list(y_cols)
    if not y_cols or len(set(y_cols)) != len(y_cols) or any(not name for name in y_cols):
        raise ValueError("y columns must be nonempty and unique")
    if not df.columns.is_unique or any(name not in df for name in [x, *y_cols]):
        raise ValueError("selected columns must exist and column names must be unique")
    if chart_type == "waterfall" and len(y_cols) != 1:
        raise ValueError("waterfall requires exactly one y column")
    output = Path(out_path)
    fmt = output.suffix.lower().lstrip(".")
    if fmt not in ("svg", "png"):
        raise ValueError("output extension must be .svg or .png")
    labels = df[x]
    if labels.isna().any() or any(not str(value).strip() for value in labels):
        raise ValueError("x contains missing labels")
    for value in labels:
        if isinstance(value, (complex, np.complexfloating)):
            raise ValueError("x must not contain complex values")
        if isinstance(value, (int, float, np.number)) and not math.isfinite(float(value)):
            raise ValueError("x contains nonfinite values")
    if chart_type not in ("scatter", "hist") and labels.astype(str).duplicated().any():
        raise ValueError("x labels must be unique; aggregate explicitly before charting")
    values = []
    for name in y_cols:
        series = df[name]
        if series.map(lambda value: isinstance(value, (bool, np.bool_))).any():
            raise ValueError("boolean observations are not numeric measurements")
        if series.map(lambda value: isinstance(value, (complex, np.complexfloating))).any():
            raise ValueError("complex observations are not real measurements")
        try:
            numeric = pd.to_numeric(series, errors="raise").to_numpy(dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"column {name!r} must contain numbers") from exc
        if not np.isfinite(numeric).all():
            raise ValueError(f"column {name!r} contains missing or nonfinite values")
        values.append(numeric)
    if chart_type == "area" and any((series < 0).any() for series in values):
        raise ValueError("stacked area requires nonnegative values")
    if chart_type == "area":
        with np.errstate(over="ignore", invalid="ignore"):
            totals = np.sum(values, axis=0)
        if not np.isfinite(totals).all():
            raise ValueError("stacked area totals exceed numeric range")
    positions = np.arange(len(df))
    if chart_type == "scatter":
        if labels.map(lambda value: isinstance(value, (bool, np.bool_))).any():
            raise ValueError("scatter x must be numeric, not boolean")
        try:
            positions = pd.to_numeric(labels, errors="raise").to_numpy(dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError("scatter x must be numeric") from exc
        if not np.isfinite(positions).all():
            raise ValueError("scatter x must be finite")
    # Context isolates settings from callers and fixes SVG element IDs across runs.
    with plt.rc_context({"svg.fonttype": "none", "svg.hashsalt": "chartkit-original-v1",
                         "font.family": "DejaVu Sans", "font.size": 12,
                         "axes.spines.top": False, "axes.spines.right": False}):
        fig, ax = plt.subplots(figsize=(12, 6.75), dpi=100)
        temporary = None
        try:
            ax.set_title(title or "", loc="left", pad=18)
            ax.set_xlabel(x)
            ax.set_ylabel(", ".join(y_cols))
            for index, (name, series) in enumerate(zip(y_cols, values)):
                color = COLORS[index % len(COLORS)]
                if chart_type == "line":
                    ax.plot(positions, series, label=name, color=color, marker="o")
                elif chart_type in ("bar", "barh"):
                    width = 0.8 / len(y_cols)
                    centers = positions - 0.4 + width * (index + 0.5)
                    if chart_type == "bar":
                        ax.bar(centers, series, width=width, label=name, color=color)
                    else:
                        ax.barh(centers, series, height=width, label=name, color=color)
                elif chart_type == "scatter":
                    ax.scatter(positions, series, label=name, color=color, marker=("o", "s", "^")[index % 3])
                elif chart_type == "hist":
                    # Shared edges permit comparisons across multiple distributions.
                    edges = np.histogram_bin_edges(np.concatenate(values), bins="auto")
                    ax.hist(series, bins=edges, label=name, color=color, alpha=0.65, edgecolor="white")
            if chart_type == "area":
                ax.stackplot(positions, *values, labels=y_cols, colors=COLORS)
            elif chart_type == "waterfall":
                changes = values[0]
                with np.errstate(over="ignore", invalid="ignore"):
                    totals = np.cumsum(changes)
                if not np.isfinite(totals).all():
                    raise ValueError("waterfall cumulative values exceed numeric range")
                starts = np.concatenate(([0.0], totals[:-1]))
                ax.bar(positions, changes, bottom=starts,
                       color=[COLORS[0] if value >= 0 else COLORS[1] for value in changes])
                for index in range(len(changes) - 1):
                    ax.plot([index + 0.4, index + 0.6], [totals[index]] * 2,
                            color="#59636A", linewidth=1)
                ax.set_ylabel(f"Cumulative {y_cols[0]} (signed changes)")
            if chart_type not in ("scatter", "hist"):
                if chart_type == "barh":
                    ax.set_yticks(positions, labels.astype(str).tolist())
                    ax.set_xlabel(", ".join(y_cols))
                    ax.set_ylabel(x)
                else:
                    ax.set_xticks(positions, labels.astype(str).tolist())
            if chart_type == "hist":
                ax.set_xlabel(", ".join(y_cols))
                ax.set_ylabel("Observation count")
            if len(y_cols) > 1:
                ax.legend(frameon=False)
            ax.set_axisbelow(True)
            ax.grid(axis="x" if chart_type == "barh" else "y", alpha=0.2)
            if chart_type in ("bar", "barh", "area", "waterfall"):
                if chart_type == "barh":
                    ax.axvline(0, color="#59636A", linewidth=0.8)
                else:
                    ax.axhline(0, color="#59636A", linewidth=0.8)
            fig.tight_layout(pad=1.8)
            _ensure_outdir(output.parent)
            with tempfile.NamedTemporaryFile(prefix=".chartkit-", suffix="." + fmt,
                                             dir=output.parent, delete=False) as staging:
                temporary = Path(staging.name)
            metadata = {"Date": None, "Creator": "chartkit"} if fmt == "svg" else {"Software": "chartkit"}
            fig.savefig(temporary, format=fmt, dpi=100, metadata=metadata)
            os.replace(temporary, output)
            return output
        finally:
            plt.close(fig)
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="UTF-8 .csv or JSON array of row objects")
    parser.add_argument("--type", required=True, choices=CHART_TYPES)
    parser.add_argument("--x", required=True, help="x column (numeric for scatter)")
    parser.add_argument("--y", required=True, help="comma-separated numeric columns")
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--filename", required=True, help="basename ending in .svg or .png")
    parser.add_argument("--title", default="", help="chart title, including units when useful")
    args = parser.parse_args()
    if Path(args.filename).name != args.filename or "\\" in args.filename:
        parser.error("--filename must be a basename, not a path")
    target = Path(args.out) / args.filename
    if Path(args.data).resolve() == target.resolve():
        parser.error("output must differ from input")
    try:
        result = render_chart(_read_data(args.data), args.type, args.x,
                              args.y, args.title, target)
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        print(f"chartkit: {exc}", file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
