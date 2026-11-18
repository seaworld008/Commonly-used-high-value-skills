# Maintenance and licensing

This skill adapts Google's retrieval and browser-support workflow, including its
mandatory search-first trigger for all HTML/CSS and client-side JavaScript work
and proactive pre-execution network approval in approval-gated environments.
Existing session authorization is reused; the current user and host govern
execution. These are retained skill rules, not changes to global host settings.

Reviewed distribution commit: `64a6d708f5a43f2cd3fde5d4d7db3905ba1bdf65`.
The original upstream entry is `skills/modern-web-guidance/SKILL.md`.

## Sources to check together

- Distribution: https://github.com/GoogleChrome/modern-web-guidance
- Authoring and CLI source: https://github.com/GoogleChrome/modern-web-guidance-src
- npm package: `modern-web-guidance`, reviewed at 1.0.1 (Node >=22).

The distribution repository's skill includes a generated `--skill-version` marker.
That flag is documented as internal. Do not blindly freeze that marker in local
commands or equate it with the npm version, our skill version or browser support.

The repository's browser-foundation policy monitors both repositories, guide and
feature directories, CLI source, package version, release tag and license files.
It runs before bulk maintenance and within the existing weekly workflow. A
missing source or new release requires attention, not an automatic "current" result.

## Review a change

1. Compare the observed commits with the recorded policy/provenance checkpoints.
2. Separate guide-content changes, CLI/API changes, packaging changes and license
   changes. A documentation-only update may need a new review checkpoint without
   changing this entry's instruction text.
   Preserve the upstream web-scope mandatory trigger and proactive approval rule;
   check their host-specific adaptation rather than silently removing them.
3. Recheck scoped licenses in README and LICENSE before copying new assets.
4. For a new CLI version, check its help, one search and retrieval of a returned ID.
   Set `DISABLE_TELEMETRY=1` for those maintenance probes and use a generic query.
5. Adapt material behavior changes, regenerate views, validate the repository,
   then advance the reviewed baselines with evidence in the same change.

## Attribution and content boundary

The distribution's root LICENSE is Apache-2.0 and applies to the skill/software
unless a more specific notice applies. Its README separately places guide content
under `guides/` under CC-BY-4.0 and identifies MDN/specification-derived material.
See the upstream README license section for the full statement.

The entry is an original local adaptation; it is not a verbatim upstream mirror.
The upstream Apache license is included for attribution. The guide
corpus and CLI implementation are retrieved through the official runner; no
guide files are redistributed with this skill. Do not label a future copied
guide corpus Apache-2.0 merely because the repository-level API reports Apache.
Retain CC-BY attribution, source links and change notices when redistributing guides.

## Backend boundary

This is a recommendation/retrieval tool. Browser/Chrome native plugins,
agent-browser, DevTools MCP and Playwright perform runtime validation. Keep their
versions, sessions and element references independent of this tool's guide IDs.
