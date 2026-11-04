# Releases

[简体中文](./RELEASES.md) · [English](./RELEASES.en.md)

This file summarizes the main changes in each release. Full notes for every release are in [`docs/releases/`](./releases/), itemized changes are in [CHANGELOG.md](../CHANGELOG.md), and release packages with checksums are on [GitHub Releases](https://github.com/seaworld008/Commonly-used-high-value-skills/releases).

## Latest Release

**v6.0.0 Portfolio Consolidation (2026-11-04)**: retires three duplicate entries (`skill-vetter` → `skill-security-auditor`, `github` → `github-ops`, `neon-postgres-egress-optimizer` → `neon-postgres`), rewrites `find-skills`, `link-checker` (now with a read-only checker script) and `figma` around real tools, and removes default `MEMORY.md`/cron writes. It also gives 46 skills trigger-based descriptions, runs a full upstream sync check, and upgrades Hermes Agent to v0.22.7. 293 skills across 16 categories. [Release notes](./releases/v6.0.0.md).

When upgrading from an older version, use `--prune-retired` to clean up retired skills: it deletes only unchanged copies this installer owns and archives everything else.

```bash
npx github:seaworld008/Commonly-used-high-value-skills install --target codex --prune-retired --dry-run
```

## Recent Releases

- [v5.0.0](./releases/v5.0.0.md) (2026-10-27): completes the full portfolio curation and adds `shadcn`, `security-model`, and `remotion-video`; `self-improving-agent` moves to `reflect-learn`.
- [v4.3.0](./releases/v4.3.0.md) (2026-10-24): updates 4 curated skills and upgrades how behavior changes and wording tweaks are verified.
- [v4.1.0](./releases/v4.1.0.md) (2026-10-16): updates engineering methods, Lark tasks and charts, AKS readiness checks, and Neon search guidance, and fixes offline HTML report updates on macOS.
- [v4.0.0](./releases/v4.0.0.md) (2026-10-12): fixes CodeQL findings, adds a zero-open-Code-Scanning-alerts release gate, and replaces the old executable with a safer offline HTML renderer.
- [v3.3.0](./releases/v3.3.0.md) (2026-10-12): adds Go profiling, benchmarking, and observability, plus architecture deepening, HTML reports, animated topology panels, and Azure diagnostics.
- [v3.2.0](./releases/v3.2.0.md) (2026-10-04): adds the `grill-me` plan stress test and completes a full source-maintenance pass.

Earlier releases are listed in [CHANGELOG.md](../CHANGELOG.md).
