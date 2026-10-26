# Compatibility and Validation Notes

This local adaptation was reviewed against `shadcn-ui/ui` commit
`8f04138777c1b6996e709993362a7b0a12888ecf` and npm CLI `4.22.1`.
The local version is independent of the upstream package release.

## Known Reference Errata

- The original entry assumes a host that executes a bang-prefixed shell block.
  The active local entry uses explicit project inspection and performs no such
  automatic execution or wildcard Bash preauthorization.
- Upstream examples use `@latest`; use the project's compatible version instead.
- The upstream CLI reference is not an exhaustive list of every released flag.
  Verify the installed command's help instead of treating an absent table row as
  proof that a flag does not exist.
- Some Tailwind v3 examples wrap a full `oklch(...)` CSS variable in another color
  function. If a variable stores the full color, use `color: var(--warning)`.
  If it stores channels only, use the project's appropriate channel function.
  Do not mix the two representations.
- The original showcase-coverage script searches source strings and follows
  filesystem links. A commented-out import can count as "shown", and directory
  links can recurse. Its byte-exact source is retained as reference text only.
  It is not an active coverage or rendering validator in this skill.

## Acceptance Evidence

Check actual local imports/exports, compile the project and test the requested
states. A source-reference count is a heuristic, not proof of rendered UI.
Browser evidence should record the page/viewport, interaction and observed
state. Build success, accessibility checks and visual inspection are separate
signals; do not claim a check that was unavailable or not run.

Registry code is project source code. Check its dependencies, local path aliases,
network behavior and affected files before applying. Use the intended registry
and scope; a preset or showcase recipe does not itself authorize installing all
components, replacing existing work or changing global client configuration.
