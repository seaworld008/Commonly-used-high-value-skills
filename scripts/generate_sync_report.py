#!/usr/bin/env python3
"""Generate a human-readable sync report from discovery and upstream check results."""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_SOURCES = ("github", "skills_sh", "clawhub")
DISCOVERY_STATUSES = {"healthy", "degraded", "unavailable"}
UPSTREAM_BUCKETS = (
    "equal",
    "changed",
    "monitor_review",
    "unavailable",
    "rollback",
    "expected_skipped",
)
UPSTREAM_CHANGE_TYPES = {
    "none",
    "body_changed",
    "artifact_changed",
    "monitor_review",
    "upstream_rollback",
    "expected_skipped",
    "offline",
    "unavailable",
}


def escape_table_cell(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def source_label(discovery: dict) -> str:
    source = discovery.get("source") or discovery.get("source_repo") or "source"
    url = discovery.get("url") or ""
    repo = discovery.get("source_repo") or ""
    if not repo:
        match = re.search(r"\(([^)]+/[^)]+)\)", str(source))
        if match:
            repo = match.group(1)
    label = repo or source
    if url:
        return f"[{escape_table_cell(label)}]({url})"
    if repo:
        return f"[{escape_table_cell(repo)}](https://github.com/{repo})"
    return escape_table_cell(label)


def upstream_skill_name(row: dict) -> str:
    return (
        row.get("skill_name")
        or row.get("video_name")
        or row.get("slug")
        or Path(row.get("repo_skill", "")).parent.name
        or "unknown-skill"
    )


def upstream_update_reason(row: dict) -> str:
    if row.get("update_reason"):
        return row["update_reason"]
    latest = row.get("latest_commit")
    if latest:
        return f"new upstream commit `{latest[:12]}` available"
    return "new commits available"


def _is_count(value: object) -> bool:
    return type(value) is int and value >= 0


def validate_discovery(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("discovery report must be an object")
    source_health = payload.get("source_health")
    if (
        not isinstance(source_health, dict)
        or set(source_health) != set(DISCOVERY_SOURCES)
    ):
        raise ValueError(
            "discovery source_health must contain exactly "
            "github, skills_sh, and clawhub"
        )
    flattened_errors: list[dict[str, Any]] = []
    statuses: set[str] = set()
    for source in DISCOVERY_SOURCES:
        health = source_health[source]
        if not isinstance(health, dict):
            raise ValueError(f"discovery source {source} health must be an object")
        status = health.get("status")
        queries = health.get("queries")
        results = health.get("results")
        raw_results = health.get("raw_results")
        emitted = health.get("emitted")
        unique_emitted = health.get("unique_emitted")
        errors = health.get("errors")
        if status not in DISCOVERY_STATUSES:
            raise ValueError(f"discovery source {source} has invalid status")
        if any(
            not _is_count(value)
            for value in (
                queries,
                results,
                raw_results,
                emitted,
                unique_emitted,
            )
        ):
            raise ValueError(
                f"discovery source {source} counts must be non-negative integers"
            )
        if (
            results != raw_results
            or raw_results < emitted
            or emitted < unique_emitted
        ):
            raise ValueError(
                f"discovery source {source} raw/emitted counts are inconsistent"
            )
        if queries == 0:
            raise ValueError(f"discovery source {source} performed zero queries")
        if not isinstance(errors, list) or any(
            not isinstance(error, dict) for error in errors
        ):
            raise ValueError(f"discovery source {source} errors must be objects")
        for error in errors:
            if (
                not isinstance(error.get("kind"), str)
                or not error["kind"].strip()
                or not isinstance(error.get("message"), str)
            ):
                raise ValueError(
                    f"discovery source {source} error fields are invalid"
                )
            status_code = error.get("status_code")
            if status_code is not None and not _is_count(status_code):
                raise ValueError(
                    f"discovery source {source} error status_code is invalid"
                )
        sorted_errors = sorted(
            errors,
            key=lambda item: (
                str(item.get("kind", "")),
                str(item.get("status_code", "")),
                str(item.get("message", "")),
            ),
        )
        if errors != sorted_errors:
            raise ValueError(
                f"discovery source {source} errors are not stably sorted"
            )
        expected_status = (
            "healthy"
            if not errors
            else ("degraded" if results > 0 else "unavailable")
        )
        if status != expected_status:
            raise ValueError(
                f"discovery source {source} status {status!r} disagrees with "
                f"queries/results/errors; expected {expected_status!r}"
            )
        statuses.add(status)
        for error in errors:
            flattened_errors.append({**error, "source": source})

    discoveries = payload.get("discoveries")
    if not isinstance(discoveries, list) or any(
        not isinstance(item, dict) for item in discoveries
    ):
        raise ValueError("discovery discoveries must be a list of objects")
    seen_names: set[str] = set()
    for index, item in enumerate(discoveries):
        source_key = item.get("source_key")
        name = item.get("name")
        source = item.get("source")
        url = item.get("url")
        description = item.get("description")
        stars = item.get("repo_stars")
        if source_key not in DISCOVERY_SOURCES:
            raise ValueError(f"discovery row {index} has invalid source_key")
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (name, source, url)
        ):
            raise ValueError(
                f"discovery row {index} requires name/source/url strings"
            )
        if not url.startswith("https://"):
            raise ValueError(f"discovery row {index} url must use HTTPS")
        if not isinstance(description, str):
            raise ValueError(
                f"discovery row {index} description must be a string"
            )
        if not _is_count(stars):
            raise ValueError(
                f"discovery row {index} repo_stars must be non-negative"
            )
        normalized_name = name.strip().casefold()
        if normalized_name in seen_names:
            raise ValueError("discovery rows must have unique names")
        seen_names.add(normalized_name)
    for field in (
        "local_skill_count",
        "raw_discovered",
        "total_discovered",
        "unique_discovered",
    ):
        if not _is_count(payload.get(field)):
            raise ValueError(f"discovery {field} must be a non-negative integer")
    if payload["unique_discovered"] != len(discoveries):
        raise ValueError("discovery unique_discovered disagrees with discoveries")
    if payload["total_discovered"] < payload["unique_discovered"]:
        raise ValueError("discovery total_discovered is smaller than unique count")
    if payload["raw_discovered"] != sum(
        source_health[source]["raw_results"] for source in DISCOVERY_SOURCES
    ):
        raise ValueError("discovery raw_discovered violates source conservation")
    if payload["total_discovered"] != sum(
        source_health[source]["emitted"] for source in DISCOVERY_SOURCES
    ):
        raise ValueError("discovery total_discovered violates source conservation")
    if payload["unique_discovered"] != sum(
        source_health[source]["unique_emitted"]
        for source in DISCOVERY_SOURCES
    ):
        raise ValueError("discovery unique count violates source conservation")
    if payload.get("errors") != flattened_errors:
        raise ValueError("discovery top-level errors disagree with source errors")
    if "unavailable" in statuses:
        return "failed"
    if "degraded" in statuses:
        return "degraded"
    return "complete"


def discovery_state(payload: dict, *, exists: bool) -> str:
    if not exists:
        return "failed"
    try:
        return validate_discovery(payload)
    except ValueError:
        return "failed"


def upstream_row_bucket(row: object) -> str:
    if not isinstance(row, dict):
        raise ValueError("upstream rows must contain objects")
    change_type = row.get("change_type")
    if change_type not in UPSTREAM_CHANGE_TYPES:
        raise ValueError(f"upstream row has invalid change_type {change_type!r}")
    check_error = row.get("check_error")
    if check_error is not None and not isinstance(check_error, str):
        raise ValueError("upstream row check_error must be a string or null")
    if type(row.get("needs_update")) is not bool:
        raise ValueError("upstream row needs_update must be boolean")
    if type(row.get("needs_review")) is not bool:
        raise ValueError("upstream row needs_review must be boolean")
    expected_update = change_type in {"body_changed", "artifact_changed"}
    expected_review = change_type in {"monitor_review", "upstream_rollback"}
    if row["needs_update"] != expected_update:
        raise ValueError("upstream row needs_update disagrees with change_type")
    if row["needs_review"] != expected_review:
        raise ValueError("upstream row needs_review disagrees with change_type")
    if check_error or change_type == "unavailable":
        return "unavailable"
    return {
        "none": "equal",
        "body_changed": "changed",
        "artifact_changed": "changed",
        "monitor_review": "monitor_review",
        "upstream_rollback": "rollback",
        "expected_skipped": "expected_skipped",
        "offline": "expected_skipped",
    }[change_type]


def validate_upstream(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("upstream report must be an object")
    summary = payload.get("summary")
    rows = payload.get("rows")
    if not isinstance(summary, dict) or not isinstance(rows, list):
        raise ValueError("upstream summary and rows are required")
    mode = payload.get("mode")
    if mode not in {"online", "offline"}:
        raise ValueError("upstream mode must be online or offline")
    recomputed = {key: 0 for key in UPSTREAM_BUCKETS}
    for row in rows:
        recomputed[upstream_row_bucket(row)] += 1
    expected_summary = {"total": len(rows), **recomputed}
    if set(summary) != set(expected_summary):
        raise ValueError("upstream summary has missing or unexpected buckets")
    for key, expected in expected_summary.items():
        value = summary.get(key)
        if not _is_count(value) or value != expected:
            raise ValueError(
                f"upstream summary {key} disagrees with rows: "
                f"{value!r} != {expected}"
            )
    if not rows or recomputed["unavailable"] or payload.get("inventory_error"):
        expected_state = "failed"
    elif (
        mode == "offline"
        or recomputed["monitor_review"]
        or recomputed["rollback"]
    ):
        expected_state = "degraded"
    else:
        expected_state = "complete"
    if payload.get("state") != expected_state:
        raise ValueError(
            f"upstream declared state {payload.get('state')!r} disagrees "
            f"with recomputed state {expected_state!r}"
        )
    derived_counts = {
        "total_checked": len(rows),
        "needs_update_count": sum(
            1 for row in rows if row.get("needs_update")
        ),
        "needs_review_count": sum(
            1 for row in rows if row.get("needs_review")
        ),
        "check_error_count": sum(
            1 for row in rows if row.get("check_error")
        ),
    }
    for key, expected in derived_counts.items():
        value = payload.get(key)
        if not _is_count(value) or value != expected:
            raise ValueError(
                f"upstream {key} disagrees with rows: {value!r} != {expected}"
            )
    return expected_state


def upstream_report_state(payload: dict, *, exists: bool) -> str:
    if not exists:
        return "failed"
    try:
        return validate_upstream(payload)
    except ValueError:
        return "failed"


def combine_state(*states: str) -> str:
    rank = {"complete": 0, "degraded": 1, "failed": 2}
    return max(states, key=lambda value: rank.get(value, 2))


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, f"{label} report is missing: {path}"
    except (OSError, json.JSONDecodeError) as exc:
        return {}, f"{label} report cannot be read: {exc}"
    if not isinstance(payload, dict):
        return {}, f"{label} report must be a JSON object"
    return payload, None


def _write_outputs(state: str, has_updates: bool, needs_attention: bool) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return
    with open(github_output, "a", encoding="utf-8") as handle:
        handle.write(f"has_updates={'true' if has_updates else 'false'}\n")
        handle.write(
            f"needs_attention={'true' if needs_attention else 'false'}\n"
        )
        handle.write(f"sync_state={state}\n")


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate sync report.")
    parser.add_argument("--discovery", default="docs/sources/reports/discovery.json")
    parser.add_argument("--upstream", default="docs/sources/reports/upstream-check.json")
    parser.add_argument("--output", default="docs/sources/reports/sync-report.md")
    parser.add_argument("--foundation", help="Required browser foundation check report when provided")
    args = parser.parse_args(argv)
    
    discovery_path = _resolve_path(args.discovery)
    upstream_path = _resolve_path(args.upstream)
    output_path = _resolve_path(args.output)
    
    discovery, discovery_read_error = _read_json(discovery_path, "discovery")
    upstream, upstream_read_error = _read_json(upstream_path, "upstream")
    validation_errors = [
        error
        for error in (discovery_read_error, upstream_read_error)
        if error
    ]
    discovery_status = "failed"
    upstream_status = "failed"
    discovery_valid = False
    upstream_valid = False
    if not discovery_read_error:
        try:
            discovery_status = validate_discovery(discovery)
            discovery_valid = True
        except ValueError as exc:
            validation_errors.append(f"invalid discovery report: {exc}")
    if not upstream_read_error:
        try:
            upstream_status = validate_upstream(upstream)
            upstream_valid = True
        except ValueError as exc:
            validation_errors.append(f"invalid upstream report: {exc}")
    
    new_skills = (
        discovery.get("discoveries", [])
        if discovery_valid
        else []
    )
    upstream_rows = (
        upstream.get("rows", [])
        if upstream_valid
        else []
    )
    upstream_updates = [r for r in upstream_rows if r.get("needs_update")]
    upstream_reviews = [
        row
        for row in upstream_rows
        if row.get("needs_review")
        or row.get("check_error")
        or row.get("change_type") == "unavailable"
    ]
    foundation = None
    foundation_status = "complete"
    if args.foundation:
        foundation, error = _read_json(_resolve_path(args.foundation), "browser foundations")
        try:
            if error:
                raise ValueError(error)
            from check_browser_foundations import validate_report
            foundation_status = validate_report(foundation)
        except ValueError as exc:
            validation_errors.append(str(exc))
            foundation_status = "failed"
            foundation = None
    state = combine_state(
        discovery_status,
        upstream_status,
        foundation_status,
    )
    
    has_updates = bool(new_skills or upstream_updates)
    needs_attention = bool(has_updates or upstream_reviews or state != "complete")
    
    # Generate report
    lines = [
        "# Weekly Skill Sync Report",
        "",
        f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Automation state**: `{state}`",
        f"**Local skills**: {discovery.get('local_skill_count', 'N/A')}",
        "",
    ]
    if validation_errors:
        lines.append("## Report Validation Failures")
        lines.append("")
        for error in validation_errors:
            lines.append(f"- {escape_table_cell(error)}")
        lines.append("")
    if args.foundation:
        lines.extend(["## Browser foundations (priority check)", "",
                      f"State: `{foundation_status}`", "",
                      "Host-managed Browser/Chrome/computer-use plugins require a separate runtime check; CI does not update or verify those application builds.", ""])
        for row in (foundation or {}).get("rows", []):
            lines.append(f"- **{escape_table_cell(row['id'])}** (`{row['state']}`): "
                         + escape_table_cell("; ".join(row["reasons"]) or "checked current"))
        lines.append("")
    discovery_errors = (
        discovery.get("errors", []) if discovery_valid else []
    )
    if discovery_errors:
        lines.append(
            f"## Discovery Source Errors ({len(discovery_errors)})"
        )
        lines.append("")
        for error in discovery_errors:
            source = escape_table_cell(error.get("source") or "unknown")
            kind = escape_table_cell(error.get("kind") or "request_failed")
            message = escape_table_cell(error.get("message") or "")
            status_code = error.get("status_code")
            status = (
                f" HTTP {status_code}"
                if type(status_code) is int
                else ""
            )
            lines.append(
                f"- **{source}** (`{kind}`{status}): {message}"
            )
        lines.append("")
    
    if new_skills:
        lines.append(f"## New Skills Discovered ({len(new_skills)})")
        lines.append("")
        lines.append("| Skill | Source | Stars/Installs | Description |")
        lines.append("|-------|-----------|-------|-------------|")
        for s in new_skills[:30]:  # Cap at 30
            name = escape_table_cell(s.get("name", ""))
            source = source_label(s)
            stars = s.get("repo_stars", 0)
            desc = escape_table_cell(s.get("description") or s.get("repo_description") or "")[:120]
            lines.append(f"| `{name}` | {source} | {stars} | {desc} |")
        lines.append("")
    
    if upstream_updates:
        lines.append(f"## Upstream Updates ({len(upstream_updates)})")
        lines.append("")
        for u in upstream_updates:
            lines.append(f"- **{upstream_skill_name(u)}**: {upstream_update_reason(u)}")
        lines.append("")

    if upstream_reviews:
        lines.append(f"## Upstream Review / Failures ({len(upstream_reviews)})")
        lines.append("")
        for row in upstream_reviews:
            change_type = row.get("change_type") or "unavailable"
            detail = row.get("check_error") or upstream_update_reason(row)
            lines.append(
                f"- **{upstream_skill_name(row)}** (`{change_type}`): "
                f"{escape_table_cell(detail)}"
            )
        lines.append("")
    
    if not needs_attention:
        lines.append(
            "No new discoveries or upstream updates this week. Checked sources match reviewed baselines."
            if args.foundation else
            "No new discoveries or upstream updates this week. All skills are up to date."
        )
        lines.append("")
    elif state == "failed" and not (new_skills or upstream_updates or upstream_reviews):
        lines.append(
            "The scan did not complete. No up-to-date conclusion can be drawn "
            "until the failed source is checked again."
        )
        lines.append("")
    
    lines.append("---")
    lines.append("*This report was auto-generated by the [upstream-sync workflow](.github/workflows/upstream-sync.yml).*")
    
    report = "\n".join(lines)
    _atomic_write_text(output_path, report)
    # Outputs are a trust signal for the workflow. Publish them only after the
    # report itself has been durably replaced.
    _write_outputs(state, has_updates, needs_attention)
    print(f"Wrote sync report: {output_path}")
    if needs_attention:
        print(f"Updates found: {len(new_skills)} new skills, {len(upstream_updates)} upstream updates")
    else:
        print("No updates found.")
    return 1 if validation_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
