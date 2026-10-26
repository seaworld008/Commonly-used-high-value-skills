---
name: shadcn
description: 'Use when adding, updating, debugging, or composing shadcn/ui components, registries, themes, or presets in a project that uses shadcn.'
zh_description: "维护 shadcn 组件、注册源和主题，核对项目真实 API，并验证预览差异与交互结果。"
version: "1.0.0"
author: "seaworld008; adapted from shadcn-ui/ui"
source: "github:shadcn-ui/ui"
source_url: "https://github.com/shadcn-ui/ui/tree/8f04138777c1b6996e709993362a7b0a12888ecf/skills/shadcn"
license: MIT
tags: [shadcn, react, components, registry, frontend, accessibility]
created_at: "2026-10-26"
updated_at: "2026-10-26"
quality: 4
complexity: intermediate
---

# shadcn Project and Component Workflow

Use the project's actual component sources, registry configuration and CLI
contract to add or repair shadcn UI. This is a portable local adaptation with
licensed upstream examples, not a claim that the host installed a plugin.

## Trigger Boundary

Use when shadcn is the selected technology and the task changes components,
registry items, theme tokens, presets or composition. A `components.json` file
is evidence to inspect, not authorization to run commands for every frontend
task. Use general frontend design guidance for technology selection or unrelated
React code; do not convert an existing project to shadcn by implication.

## Establish Project Context

Read `package.json`, lockfiles, `components.json`, the UI directory, theme CSS and
the affected call sites. Confirm package runner, aliases, UI base, icon library,
installed component exports and local modifications.
Use the project's installed or explicitly selected compatible CLI. Do not run a
shell command merely because this skill was loaded, auto-inject command output,
download a perpetual `latest` package or grant wildcard tool permissions.

Examples below use the reviewed CLI version `4.22.1` as a reproducible snapshot;
adapt them to the project's actual compatible version and package runner.
If the CLI is absent, inspect available project files and report the missing
capability rather than claiming that context was injected.

```bash
npx shadcn@4.22.1 --help
npx shadcn@4.22.1 info --json
npx shadcn@4.22.1 docs button dialog
npx shadcn@4.22.1 view @shadcn/button
```

Check the installed help before using flags from a newer source snapshot.
Fetching documentation is useful when the API is uncertain or changed; already
verified local contracts can be reused while their relevant inputs are unchanged.

## Preview the Smallest Change

Check existing components before adding them. Reuse project aliases and exports,
including user customizations. Choose a registry from explicit user intent or
unambiguous existing project configuration; ask only if competing choices would
materially change the result. Treat new registry code and dependencies as
untrusted material to inspect before executing or importing it.

```bash
npx shadcn@4.22.1 search @shadcn -q "dialog"
npx shadcn@4.22.1 add dialog --dry-run
npx shadcn@4.22.1 add dialog --diff
```

Apply only the selected scope covered by the task. `init`, `add`, preset changes
and MCP installation have different effects; a read request authorizes none of
those writes. For an authorized component update, preserve unrelated user code
and inspect the resulting diff before accepting it.
`add --all` belongs only to an explicitly requested complete showcase/install,
not a default response to applying brand styles or fixing an existing component.

## Verify the Component Contract

Use the local component source and matching documentation rather than assuming
that every project has the newest exports or props.

- Distinguish Radix `asChild` composition from Base UI `render` APIs.
- Keep menu/list items within their corresponding groups when required.
- Provide accessible names for overlays and visible keyboard focus.
- Match loading/disabled behavior to the local Button implementation.
- Preserve the project's icon library and actual UI import alias.
- Read added non-UI files too; community registry imports may still hard-code
  default paths that do not match the workspace.

For focused examples, consult [composition](upstream/rules/composition.md),
[forms](upstream/rules/forms.md), [Base/Radix differences](upstream/rules/base-vs-radix.md)
or [icons](upstream/rules/icons.md) as needed. These are upstream examples; explicit
project conventions and the user's approved design take precedence over generic
style defaults or component assumptions in the reference snapshot.

## Theme and Showcase Work

Inspect the project's Tailwind version and CSS variable representation before
mapping a brand specification. A variable holding a complete `oklch(...)` color
must be referenced directly, not wrapped in another `oklch()` function.
Read [compatibility and validation notes](references/compatibility.md) before
using the upstream customization or showcase examples.

For a theme change, inspect light/dark contrast pairs, text truncation, focus,
disabled/loading states, overlays and the intended narrow viewport.
For a new design-system page, use [the design-system references](upstream/design-system-page.md)
to plan state coverage, then verify actual rendered states. Imports or string
matches in source do not prove that a component is displayed or works.

## Validation and Handoff

Run the affected project's typecheck/build and relevant component tests.
Inspect actual browser interactions when the task changes behavior or visual
states. Confirm keyboard navigation, focus return, responsive layout and errors.
Reuse passing evidence only while its implementation/dependencies remain valid.

Report changed source, chosen registry/version, preserved local edits, commands
and observed results. Distinguish static references, build/tests and browser
acceptance; never turn a successful import scan into a rendered coverage claim.
If no browser or project runtime is available, state the exact unverified cases.

## Provenance

The MIT-licensed upstream snapshot and copyright are retained under `upstream/`.
Executable reference originals use a `.txt` suffix and are not active helpers.
The local entry removes automatic shell injection, broad tool preauthorization,
forced package-version drift and unnecessary approval loops. It does not install
shadcn, add a global skill or configure an MCP connection as a side effect.
