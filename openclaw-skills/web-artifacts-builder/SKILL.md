---
name: web-artifacts-builder
description: 'Build complex interactive HTML artifacts with React, Tailwind, and shadcn/ui when multiple components, routing, or state are needed.'
zh_description: "用于构建复杂多组件 HTML/React 网页 artifacts，尤其适合需要状态、路由或 shadcn/ui 的场景。"
version: "1.0.4"
author: "Anthropic contributors; local curators"
source: "https://github.com/anthropics/skills"
source_url: "https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/web-artifacts-builder/SKILL.md"
license: "Apache-2.0 AND MIT"
tags: '["artifacts", "builder", "development", "web"]'
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 3
complexity: "intermediate"
---

# Web Artifacts Builder

Build an interactive React artifact and deliver a verified standalone HTML file.
Use this workflow for stateful views, multiple components, or reusable visual tools.
For a small static page, choose the project's simpler existing workflow.

## When to Use

- The deliverable needs React state, several coordinated components, or routing.
- The user needs an HTML artifact that opens without a development server.
- An existing artifact has missing styles, broken interactions, or incomplete bundled assets.

## Requirements and Source

The template uses React 18, TypeScript, Vite 8, Tailwind 3 and the bundled shadcn/ui sources.
Use Node `^20.19.0 || >=22.12.0` and an already available `pnpm` command.
The scripts reject incompatible engines and missing tools before initialization.
They install only project dependencies, with dependency lifecycle scripts disabled.
They do not install a global package manager or change global configuration.

The fixed direct dependencies are a reviewed compatibility set for this archive.
Its calendar uses react-day-picker 9; other components include older compatible APIs.
The initializer copies the reviewed template lockfile and installs with `--frozen-lockfile`.
Keep that lockfile and record Node and pnpm versions for reproduction.
An upgrade needs type checking of all component sources and real interaction tests.
New registry versions alone do not establish compatibility with the bundled components.

The skill adapts Anthropic's Apache-2.0 workflow and includes shadcn's MIT components.
There are 43 UI modules and two support modules in the archive, 45 source files total.
Preserve `LICENSE.txt`, `LICENSE.shadcn.txt` and `THIRD_PARTY_NOTICES.md` in generated projects.
Local original helpers are covered by `LICENSE.local.txt`; they do not relicense third-party code.
The generated project includes an original MIT scrollbar compensation module with its own notice.
A project-local pnpm override supplies the public component/constant interfaces used by this template;
it does not download the unresolved upstream scrollbar implementation.
Publisher notice supplements apply only to their recorded exact package versions.

## Initialize a Project

Resolve the loaded skill directory to an absolute path first:

```bash
ARTIFACT_SKILL_DIR="/absolute/path/to/loaded/web-artifacts-builder"
bash "$ARTIFACT_SKILL_DIR/scripts/init-artifact.sh" "new-artifact"
cd "new-artifact"
pnpm typecheck
pnpm build
```

The destination must be absent or an empty directory; existing content is preserved.
Names are handled as path/title data rather than shell or sed expressions.
A failed installation removes its own staging directory and leaves the old destination intact.
The scaffold includes `@/` aliases, all bundled component sources and the full notices.
Use its JSON PostCSS configuration with both Vite and the standalone bundler.

## Develop and Check the Application

Edit `src/App.tsx`, import only components needed by the artifact, and reuse its theme.
Choose hierarchy, spacing, color, typography and interaction states for the actual audience.
Avoid adding a component library merely to increase visual complexity.
Keep initial state deterministic and ensure the first render communicates a useful result.
For date-only selections, format local calendar fields rather than converting midnight to UTC.
For forms, test invalid input, successful input, disabled controls and status feedback.
For dialogs, test keyboard activation, Escape, focus containment and return of focus.
For calendars, test selection and month changes, including the intended date/timezone.
For carousels and resizable panels, verify both controls and the resulting content/layout.
Check keyboard access, readable labels and contrast at desktop and narrow viewports.

```bash
pnpm typecheck
pnpm build
```

Type checking covers the entire source tree, including components not imported by the entry page.
A successful Vite build establishes compilation; it does not prove standalone HTML behavior.
Use native text and interactive controls where appropriate instead of flattening everything to images.

## Bundle the Standalone HTML

Run from the project root, which must contain `package.json` and `index.html`:

```bash
bash "$ARTIFACT_SKILL_DIR/scripts/bundle-artifact.sh"
```

The script uses project-local Parcel and html-inline at explicit reviewed versions.
Missing bundling dependencies are added locally with lifecycle scripts disabled.
It uses a private temporary Parcel configuration and retains the project's `.parcelrc`.
Build and inline output stay in a staging directory on the same filesystem.
The previous `dist` remains intact; only a complete candidate replaces `bundle.html`.
Invalid, empty or incompletely inlined output is rejected before publication.
Failure preserves the previous HTML and removes the helper's temporary files.
Publication is atomic for a single writer; serialize simultaneous builds of the same artifact.

The final HTML contains inert, encoded source notices rather than executing or displaying them.
Installed runtime dependencies also need their full applicable license and copyright notices.
Preserve the artifact's notices when sharing or embedding its code in another deliverable.
This does not establish rights to user-provided images, fonts, datasets or newly added packages.
Verify those assets separately and include their applicable notices.

## Standalone Acceptance Checklist

1. Open `bundle.html` directly, independently of Vite and the source directory.
2. Verify that styles, icons, fonts and images resolve without local build paths.
3. Disable networking and reload; exercise each core interaction again.
4. Inspect requests and console errors; record any intentional external data dependency.
5. Check both a desktop viewport and a narrow viewport, with no unwanted horizontal overflow.
6. Use the keyboard for forms, dialogs, selection widgets and navigation.
7. Decode the inert notice payload and compare its bytes with the applicable source files.
8. Make a controlled build fail and confirm the previous delivery still opens unchanged.

Dynamic `fetch`, lazy imports and URLs constructed by application code need real browser testing.
The static resource gate cannot prove that every possible application branch works offline.
If a required tool or browser is unavailable, report that specific unperformed check.
Do not report build success as interaction, accessibility or production acceptance.

## Diagnose Failures

| Symptom | Check |
| --- | --- |
| Calendar type errors | Archive API and react-day-picker major must agree |
| Missing alias | Check `tsconfig.json` and Vite alias; preserve the project configuration |
| Missing styles | Verify `.postcssrc.json`, Tailwind content globs and imported CSS |
| Build works, standalone fails | Inspect residual resources, module loading and dynamic requests |
| Native dependency unavailable | Check platform packages and engine compatibility; do not enable arbitrary lifecycle scripts |
| Missing license body | Restore the actual installed package's full notice; metadata alone is insufficient |
| Oversized HTML | Remove unused imports and large embedded media, then rebuild and retest |

## Delivery

Share the final HTML and identify the tested build, viewport and interactions.
State the actual verification boundary and any intentional network requirements.
Keep editable source and lockfile when the user needs to maintain the artifact.
