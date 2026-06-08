---
name: vercel-react-view-transitions
description: 'Guide for adding native-feeling page, route, shared-element, and list transitions in React and Next.js with the View Transition API.'
version: "1.0.0"
author: seaworld008
source: github:vercel-labs/agent-skills
source_url: "https://skills.sh/vercel-labs/agent-skills/vercel-react-view-transitions"
license: MIT
tags: '[react, nextjs, animation, transitions, frontend, vercel]'
created_at: "2026-06-08"
updated_at: "2026-06-08"
quality: 4
complexity: intermediate
---

# Vercel React View Transitions

Practical guidance for implementing React View Transitions in production UI work. This skill is intended for code generation, refactoring, and review tasks where the goal is to add motion without introducing a heavyweight animation library.

This repository version is an original in-house rewrite informed by the public Vercel skill and related platform guidance. Keep the implementation grounded in React and Next.js behavior, not generic CSS animation habits.

## When to Use

Use this skill when the task involves any of the following:

- route or page transitions in a React or Next.js app
- list-to-detail shared element motion
- enter and exit animations tied to UI state changes
- reordering cards, rows, or grid items with smooth visual continuity
- replacing ad hoc animation libraries for simple navigation transitions
- reviewing whether a proposed transition respects accessibility and browser support

Do not reach for this skill when the request is mainly about canvas, WebGL, game animation, or highly choreographed motion systems. In those cases, a dedicated animation or rendering approach is more appropriate.

## Availability Rules

- In plain React apps, treat `ViewTransition` support as experimental and version-sensitive.
- In modern Next.js App Router environments, verify the framework behavior before adding polyfills or third-party wrappers.
- Unsupported browsers must still render correctly. Motion is an enhancement, not a dependency.
- Always include a reduced-motion path before polishing the default animation.

## Working Model

Think about view transitions as three separate decisions:

1. What visual region should transition?
2. Which state change should trigger the transition?
3. What motion style should be applied when the browser captures old and new snapshots?

If those three decisions are not clear, do not start coding animation classes yet. Audit the UI first.

## Implementation Workflow

### 1. Audit the interaction

Before editing code, identify:

- the state or navigation event that changes the UI
- the exact element boundaries that should animate
- whether the transition is page-wide, local, or shared-element
- whether loading, suspense, or async updates are involved

Good candidates:

- gallery to detail page
- tabs or segmented views
- sortable lists
- card expansion into a modal or detail panel

Bad candidates:

- unstable layouts that shift significantly between renders
- components that remount unpredictably on each keystroke
- content that must remain fully static for accessibility or performance reasons

### 2. Place transition boundaries deliberately

Wrap the smallest meaningful UI region, not the whole application by default.

```tsx
import { ViewTransition } from "react";

export function ProductCard({ children }: { children: React.ReactNode }) {
  return (
    <ViewTransition>
      <article className="product-card">{children}</article>
    </ViewTransition>
  );
}
```

Prefer narrow boundaries because broad boundaries often create unnecessary cross-fades and make debugging harder.

### 3. Trigger transitions with transition-aware updates

Use transition-aware React flows when the UI update is non-urgent.

```tsx
import { startTransition, useState } from "react";

export function SortableGrid() {
  const [sort, setSort] = useState<"popular" | "latest">("popular");

  function handleSort(next: "popular" | "latest") {
    startTransition(() => {
      setSort(next);
    });
  }

  return (
    <>
      <button onClick={() => handleSort("popular")}>Popular</button>
      <button onClick={() => handleSort("latest")}>Latest</button>
    </>
  );
}
```

If an update must be immediate and interaction-critical, do not force a transition just for visual effect.

### 4. Name shared elements only when identity is stable

Shared-element motion works only when the old and new elements represent the same conceptual object.

```tsx
<ViewTransition name={`product-${product.id}`}>
  <img src={product.image} alt={product.title} />
</ViewTransition>
```

Use stable IDs. Never derive names from array index or transient sort order.

### 5. Add CSS last

Start with a minimal, working transition boundary. Then add motion classes after the render flow is correct.

```css
@media (prefers-reduced-motion: no-preference) {
  ::view-transition-old(.slide-forward) {
    animation: 180ms ease-out both fade-out, 220ms ease-out both slide-left;
  }

  ::view-transition-new(.slide-forward) {
    animation: 220ms ease-out both fade-in, 220ms ease-out both slide-in-right;
  }
}

@keyframes fade-out {
  to { opacity: 0; }
}

@keyframes fade-in {
  from { opacity: 0; }
}

@keyframes slide-left {
  to { transform: translateX(-16px); }
}

@keyframes slide-in-right {
  from { transform: translateX(16px); }
}
```

Keep timing short. Most navigation transitions feel better in the 150ms to 250ms range than in long cinematic motion.

## Common Patterns

### Pattern: route transition in Next.js

- isolate the content area that changes between routes
- keep persistent chrome such as header and nav outside the transition when possible
- prefer directional classes only when navigation intent is known

### Pattern: list reorder

- preserve stable keys
- wrap only the moving items or container region that visually changes
- avoid mixing reorder animation with unrelated loading spinners in the same boundary

### Pattern: shared card to detail morph

- name only the elements that should visually map across states
- ensure both source and destination render in the same user action flow
- keep aspect ratio changes modest unless the design explicitly wants a dramatic transform

### Pattern: suspense reveal

- combine transitions with deferred or async UI only when fallback behavior is already correct
- fix loading jitter first, then add motion

## Review Checklist

When reviewing a PR that uses view transitions, check the following:

- transition boundaries are intentionally scoped
- keys and shared-element names are stable
- the interaction still works with reduced motion
- unsupported browsers still receive usable UI
- no manual DOM snapshot hacks were added
- the team did not add a large animation dependency for a small navigation effect
- CSS does not animate layout in a way that causes avoidable jank

## Anti-Patterns

Avoid these mistakes:

- wrapping the entire app tree by default
- using random IDs or array indexes for shared-element names
- adding transitions before fixing layout instability
- coupling transitions to every `setState` call
- hiding broken data-fetch or suspense behavior behind motion
- shipping motion that has no reduced-motion override

## Boundaries

This skill is not a full animation design system. It does not replace:

- Framer Motion for complex choreography
- canvas/WebGL animation systems
- gesture-heavy mobile interaction frameworks
- brand-motion direction work done by designers

If the user needs cinematic sequences, drag physics, or scroll-linked animation systems, switch to a more specialized approach.

## Output Expectations

When applying this skill, the agent should usually produce:

- a short audit of the target interaction
- the smallest viable transition boundary in React code
- reduced-motion-safe CSS
- a note about browser or framework assumptions
- a brief explanation of why this boundary and trigger were chosen

## Final Principle

Prefer continuity over spectacle. A good view transition makes the state change easier to follow, not harder to understand.
