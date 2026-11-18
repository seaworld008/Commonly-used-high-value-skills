# Releases

[简体中文](./RELEASES.md) · [English](./RELEASES.en.md)

This file summarizes the main changes in each release. Full notes for every release are in [`docs/releases/`](./releases/), itemized changes are in [CHANGELOG.md](../CHANGELOG.md), and release packages with checksums are on [GitHub Releases](https://github.com/seaworld008/Commonly-used-high-value-skills/releases).

## Latest Release

**v6.2.0 Portfolio audit and evolving browser foundations (2026-11-18)**: combines the v6.1.0 audit of 293 skills and provenance/license repairs with agent-browser 0.43.0, DevTools and Playwright guidance. Adds priority foundation checks, ongoing drift tracking and reviewed baseline advancement to full maintenance and the weekly workflow. [Release notes](./releases/v6.2.0.md).

When upgrading from an older version, use `--prune-retired` to clean up retired skills: it deletes only unchanged copies this installer owns and archives everything else.

```bash
npx github:seaworld008/Commonly-used-high-value-skills install --target codex --prune-retired --dry-run
```

## Recent Releases

- [v6.1.0](./releases/v6.1.0.md) (2026-11-17): incorporated into v6.2.0; historical review evidence is retained.

- [v6.0.0](./releases/v6.0.0.md) (2026-11-04): retired three duplicate entrypoints, retained 293 skills, and updated triggers, tool discovery and upstream checks.

- [v5.0.0](./releases/v5.0.0.md) (2026-10-27): completes the full portfolio curation and adds `shadcn`, `security-model`, and `remotion-video`; `self-improving-agent` moves to `reflect-learn`.
- [v4.3.0](./releases/v4.3.0.md) (2026-10-24): updates 4 curated skills and upgrades how behavior changes and wording tweaks are verified.
- [v4.1.0](./releases/v4.1.0.md) (2026-10-16): updates engineering methods, Lark tasks and charts, AKS readiness checks, and Neon search guidance, and fixes offline HTML report updates on macOS.
- [v4.0.0](./releases/v4.0.0.md) (2026-10-12): fixes CodeQL findings, adds a zero-open-Code-Scanning-alerts release gate, and replaces the old executable with a safer offline HTML renderer.
- [v3.3.0](./releases/v3.3.0.md) (2026-10-12): adds Go profiling, benchmarking, and observability, plus architecture deepening, HTML reports, animated topology panels, and Azure diagnostics.
- [v3.2.0](./releases/v3.2.0.md) (2026-10-04): adds the `grill-me` plan stress test and completes a full source-maintenance pass.

Earlier releases are listed in [CHANGELOG.md](../CHANGELOG.md).
