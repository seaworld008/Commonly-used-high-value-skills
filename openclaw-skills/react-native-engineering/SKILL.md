---
name: react-native-engineering
description: 'Use when building, reviewing, debugging, testing, upgrading, or shipping React Native and Expo applications, including navigation, native modules, New Architecture compatibility, iOS/Android platform differences, performance, EAS builds, over-the-air updates, and release validation.'
zh_description: "用于构建、审查、调试、测试、升级和发布 React Native 与 Expo 应用，覆盖新架构、原生模块、性能、EAS 和双平台验证。"
version: "1.0.0"
author: seaworld008
source: "in-house"
source_url: ""
tags: '[react-native, expo, mobile, ios, android, testing, performance, eas]'
created_at: "2026-08-10"
updated_at: "2026-08-10"
quality: 5
complexity: advanced
---

# React Native Engineering

Build React Native applications as mobile systems, not browser applications
with different tags. Preserve the shared TypeScript product core while treating
iOS, Android, native dependencies, application binaries, and update channels as
real release boundaries.

## Start With Repository Evidence

Inspect the project before recommending an API or command:

```bash
node -p "require('./package.json').dependencies?.['react-native']"
node -p "require('./package.json').dependencies?.expo"
node -p "require('./package.json').dependencies?.['expo-router']"
test -d ios && echo "ios directory present"
test -d android && echo "android directory present"
test -f app.json && sed -n '1,220p' app.json
test -f app.config.ts && sed -n '1,220p' app.config.ts
test -f eas.json && sed -n '1,220p' eas.json
```

Report the detected execution model:

```text
React Native:
Expo SDK:
Workflow: Expo managed/CNG | prebuild | bare React Native
Navigation:
New Architecture:
Native projects checked in:
Build/update service:
Package manager:
```

Do not paste setup commands until the installed versions and workflow are
known. React Native, Expo SDK, native modules, CocoaPods, Gradle, and Xcode
compatibility move together.

## Choose The Right Workflow

Prefer an Expo framework workflow for new applications unless requirements
prove it unsuitable. It provides version-coordinated native modules,
development builds, routing options, build services, and update tooling.

Choose bare React Native or checked-in native projects when the application
requires one of these:

- custom native build phases or extensive native source ownership;
- a native SDK that cannot be expressed through an Expo config plugin;
- host-app integration where React Native is embedded in existing iOS or
  Android applications;
- organization-specific signing, packaging, or build infrastructure that must
  own every native step.

Do not eject or prebuild merely to edit a generated file. First determine
whether app configuration or a config plugin can express the change.

## New Architecture Baseline

Treat the New Architecture as the current production baseline. React Native
0.76 enabled it by default, and newer React Native and Expo releases have made
legacy opt-out increasingly constrained.

Before adding or upgrading a native dependency:

1. Confirm the package supports the project's React Native and Expo versions.
2. Run the framework's dependency health check.
3. Build both native platforms when the dependency contains native code.
4. Exercise the dependency on a physical device when it touches sensors,
   background work, notifications, media, or platform security.

For Expo projects:

```bash
npx expo-doctor@latest
npx expo install --check
npx expo export
```

For bare React Native projects, use the repository's package manager plus its
documented Android and iOS build commands. Do not assume an Expo command exists.

## TypeScript And Boundaries

Use TypeScript for application code and run the compiler as a type checker.
Metro/Babel handles bundling; `tsc` should normally validate rather than emit.

Keep these boundaries explicit:

```text
screens/routes     navigation entry points and route parameters
features           product behavior grouped by domain
components         reusable presentational UI
services           typed network, storage, analytics, and native adapters
state              cross-screen client state with named ownership
platform           .ios/.android variants and native capability wrappers
```

Do not let screens own transport parsing, persistence, and business rules at
the same time. Isolate platform APIs behind typed adapters so tests can replace
them without mocking the whole runtime.

## UI And Platform Behavior

Design for mobile interaction:

- use safe-area insets for edge-to-edge layouts;
- account for keyboard appearance, focus order, and text scaling;
- expose accessibility roles, labels, state, and hints where the visible text
  is insufficient;
- use `Pressable` or an established component system with explicit disabled,
  pressed, focus, and loading states;
- test compact and large screens, light and dark appearance, and increased font
  size;
- keep platform forks narrow and name them with `.ios.tsx` or `.android.tsx`
  only when behavior actually differs.

Never infer Android behavior from an iOS simulator or the reverse. Permissions,
back navigation, keyboards, notifications, background execution, deep links,
and file access have platform-specific contracts.

## Lists, Images, And Rendering Cost

Measure before optimizing, then fix the dominant frame or memory cost.

For long collections:

- use a virtualized list rather than mapping hundreds of mounted children;
- provide stable keys based on domain identity;
- avoid recreating render callbacks and large derived arrays without need;
- keep row components cheap and measure the effect of memoization;
- paginate or incrementally load data rather than retaining an unbounded feed.

For images:

- request dimensions close to rendered size;
- define layout dimensions to prevent reflow;
- use caching behavior appropriate to privacy and freshness;
- test memory pressure on representative lower-end Android hardware.

Do not claim a performance improvement from code review alone. Capture a
before/after trace, interaction time, frame metric, memory profile, or bundle
measurement in a release-like build.

## Data, Offline, And Failure States

Define ownership for server state, local durable state, and transient UI state.
Avoid placing every category into one global store.

Every network-backed screen needs deliberate states:

```text
initial loading
refreshing with existing data
empty success
partial or stale cached data
recoverable error with retry
authentication expiry
offline behavior
```

Cancel or ignore stale requests when navigation or parameters change. Make
mutations idempotent where mobile retries can duplicate submissions. Never log
tokens, sensitive payloads, notification contents, or device identifiers.

## Testing Pyramid

Use the cheapest test that can observe the failure:

1. Static checks for types, lint, configuration, and dependency compatibility.
2. Unit tests for domain logic and platform-independent adapters.
3. Component tests through visible text, accessibility semantics, and user
   actions.
4. Integration tests for navigation, persistence, and service boundaries.
5. Device end-to-end tests for critical journeys and native behavior.

For Expo projects, prefer `jest-expo` with React Native Testing Library. Do not
introduce `react-test-renderer` into a modern React 19 stack; current Expo
guidance uses `@testing-library/react-native`.

```bash
npx expo install jest-expo jest @types/jest --dev
npx expo install @testing-library/react-native --dev
npm test -- --runInBand
```

Component tests should assert user-observable behavior instead of internal
component state or implementation-only props. E2E coverage should prioritize
authentication, payments, onboarding, deep links, offline recovery, and other
journeys where native integration changes the outcome.

## Build And Release Gates

Separate JavaScript validation from native binary validation:

```bash
npm run lint
npx tsc --noEmit
npm test -- --runInBand
npx expo-doctor@latest
npx expo export
```

Then run the repository's actual iOS and Android build path. For an EAS
project, representative commands may be:

```bash
eas build --platform android --profile preview
eas build --platform ios --profile preview
```

Use `eas build --local` when reproducing a cloud build failure or when policy
requires local infrastructure. A successful JavaScript bundle does not prove
Gradle, CocoaPods, signing, entitlements, native resources, or store packaging.

## Over-The-Air Update Boundary

An over-the-air update may change JavaScript, styling, and bundled assets only
when the installed binary is compatible. Changes to native code, native
dependencies, permissions, the Expo SDK, or other binary configuration require
a new build.

Before publishing an update:

1. Confirm the runtime version and target channel.
2. Produce and inspect the exported bundle.
3. Test the update on the same binary users will run.
4. Use staged rollout or a preview channel when impact is broad.
5. Keep a documented rollback or republish path.

Never use an update channel to bypass application-store policy or deliver code
that requires a different native runtime.

## Upgrade Workflow

Upgrade one compatibility boundary at a time:

1. Read the current React Native or Expo upgrade guidance.
2. Update the framework and version-coupled packages.
3. Run dependency diagnostics.
4. Regenerate native projects only when the repository's workflow expects it.
5. Review native diffs instead of accepting them blindly.
6. Run static, component, Android, and iOS validation.
7. Test critical native capabilities on devices.

Do not mix a framework upgrade with unrelated navigation, state, and UI
refactors. Smaller diffs make native regressions diagnosable.

## Debugging Sequence

When a failure appears:

1. Classify it as JavaScript, Metro, native compile, native runtime, signing,
   device-only, or release-only.
2. Capture the first causal error, not the final cascade.
3. Reproduce on the smallest relevant platform and build configuration.
4. Check version compatibility before clearing caches.
5. Clear only the cache implicated by evidence.
6. Rebuild and record the exact command and environment.

Avoid ritual deletion of `node_modules`, Pods, Gradle caches, and derived data.
It destroys evidence and can hide dependency drift without fixing it.

## Review Output

For reviews or upgrade plans, return:

```markdown
## React Native Baseline
- Versions and workflow:
- New Architecture status:
- Native dependencies:

## Findings
| Priority | Platform | Evidence | Impact | Fix |

## Validation Matrix
| Gate | iOS | Android | Evidence |

## Release Decision
PASS | PASS WITH FIXES | BLOCKED
```

Block release for reproducible crashes, incompatible native dependencies,
broken signing, untested permission changes, missing critical-journey device
coverage, or an update/binary runtime mismatch.

## Official Sources

- React Native introduction and current guides:
  `https://reactnative.dev/docs/getting-started`
- React Native TypeScript guidance:
  `https://reactnative.dev/docs/typescript`
- React Native New Architecture:
  `https://reactnative.dev/architecture/landing-page`
- React Native testing overview:
  `https://reactnative.dev/docs/testing-overview`
- Expo New Architecture guidance:
  `https://docs.expo.dev/guides/new-architecture/`
- Expo unit testing:
  `https://docs.expo.dev/develop/unit-testing/`
- EAS local builds:
  `https://docs.expo.dev/build-reference/local-builds/`
- EAS Update:
  `https://docs.expo.dev/eas-update/introduction/`

Re-check these sources when framework versions change. The candidate that
motivated this skill had no detectable upstream license, so this implementation
is original and does not reproduce its text.
