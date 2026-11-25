# Releases

[简体中文](./RELEASES.md) · [English](./RELEASES.en.md)

This file summarizes the main changes in each release. Full notes for every release are in [`docs/releases/`](./releases/), itemized changes are in [CHANGELOG.md](../CHANGELOG.md), and release packages with checksums are on [GitHub Releases](https://github.com/seaworld008/Commonly-used-high-value-skills/releases).

## Latest Release

**v7.0.1 Tenant isolation patch, review fixes, and browser foundation upgrades (2026-11-25)**: restores `database-designer` PostgreSQL parent/child RLS membership checks, least-privilege non-owner grants, and controlled `soft_delete_task` RPC with live PostgreSQL regression coverage; fixes the remaining PR #164 review items and enforces LF checkout normalization in `.gitattributes`; upgrades `agent-browser 0.44.0`, `chrome-devtools-mcp 1.14.0`, `modern-web-guidance 1.0.2`, `hermes-agent v0.23.4`, and `graphify v0.9.119`. [Release notes](./releases/v7.0.1.md).

When upgrading from an older version, use `--prune-retired` to clean up retired skills: it deletes only unchanged copies this installer owns and archives everything else.

```bash
npx github:seaworld008/Commonly-used-high-value-skills install --target codex --prune-retired --dry-run
```

## Recent Releases

- [v7.0.0](./releases/v7.0.0.md) (2026-11-23): merged and retired 4 overlapping skills, added 5 curated high-value skills, and upgraded 295 canonical skills.

- [v6.2.0](./releases/v6.2.0.md) (2026-11-18): combined the v6.1.0 audit and updated `agent-browser` 0.43.0, DevTools, and Playwright guidance with priority browser-foundation tracking.

- [v6.1.0](./releases/v6.1.0.md) (2026-11-17): incorporated into v6.2.0; historical review evidence is retained.

- [v6.0.0](./releases/v6.0.0.md) (2026-11-04): retired three duplicate entrypoints, retained 293 skills, and updated triggers, tool discovery and upstream checks.

- [v5.0.0](./releases/v5.0.0.md) (2026-10-27): completes the full portfolio curation and adds `shadcn`, `security-model`, and `remotion-video`; `self-improving-agent` moves to `reflect-learn`.
- [v4.3.0](./releases/v4.3.0.md) (2026-10-24): updates 4 curated skills and upgrades how behavior changes and wording tweaks are verified.
- [v4.1.0](./releases/v4.1.0.md) (2026-10-16): updates engineering methods, Lark tasks and charts, AKS readiness checks, and Neon search guidance, and fixes offline HTML report updates on macOS.
- [v4.0.0](./releases/v4.0.0.md) (2026-10-12): fixes CodeQL findings, adds a zero-open-Code-Scanning-alerts release gate, and replaces the old executable with a safer offline HTML renderer.
- [v3.3.0](./releases/v3.3.0.md) (2026-10-12): adds Go profiling, benchmarking, and observability, plus architecture deepening, HTML reports, animated topology panels, and Azure diagnostics.
- [v3.2.0](./releases/v3.2.0.md) (2026-10-04): adds the `grill-me` plan stress test and completes a full source-maintenance pass.

Earlier releases are listed in [CHANGELOG.md](../CHANGELOG.md).
