# Skill Template Reference

Guidelines for creating new skills from reflection learnings.

## When to Create a Skill

Create a new skill instead of updating an agent when the learning:

| Criteria | Explanation |
|----------|-------------|
| **Non-obvious debugging** | Solution required significant investigation (>10 min) |
| **Misleading error** | Error message pointed to wrong direction |
| **Workaround discovery** | Found workaround through experimentation |
| **Configuration insight** | Setup differs from documented approach |
| **Reusable pattern** | Would help in similar future situations |
| **Trial-and-error success** | Multiple approaches tried before solution |

## Quality Gates

Before creating a skill, verify ALL gates pass:

### 1. Reusable
- [ ] Will help with future tasks (not just this one instance)
- [ ] Applies to similar situations across projects
- [ ] Not overly specific to one codebase

### 2. Non-trivial
- [ ] Requires discovery, not just documentation lookup
- [ ] Took meaningful effort to figure out
- [ ] Not immediately obvious from error message

### 3. Specific
- [ ] Can describe exact trigger conditions
- [ ] Clear symptoms to match against
- [ ] Defined scope (technology, version, context)

### 4. Verified
- [ ] Solution actually worked
- [ ] Tested in the current context
- [ ] Not theoretical or untested

### 5. No Duplication
- [ ] Checked existing skills in `~/.claude/skills/`
- [ ] Checked existing skills in `.claude/skills/`
- [ ] Not covered by existing documentation

## Skill File Structure

Create at `.claude/skills/{skill-name}/SKILL.md`:

```markdown
---
name: {kebab-case-name}
description: |
  {CRITICAL: Include exact error messages, symptoms, technologies}
  Use when: (1) {trigger condition 1}, (2) {trigger condition 2}
  Solves: {problem summary}
author: Claude Code (auto-generated via /reflect)
version: 1.0.0
date: {YYYY-MM-DD}
source_session: {session_id if available}
confidence: {HIGH/MEDIUM}
---

# {Skill Name}

## Problem

{Clear description of the problem this skill solves}

## Context / Trigger Conditions

Use this skill when you encounter:
- {Exact error message if applicable}
- {Symptom 1}
- {Symptom 2}
- {Technology/framework involved}

## Solution

{Step-by-step solution}

1. {Step 1}
2. {Step 2}
3. {Step 3}

## Verification

How to verify the solution worked:
- {Verification step 1}
- {Verification step 2}

## Example

{Concrete example from the session where this was discovered}

## Notes

- {Caveats or edge cases}
- {When this might NOT apply}
- {Related issues}

## References

- {Link to relevant documentation if any}
- {GitHub issue if applicable}
- {Stack Overflow thread if helpful}
```

## Naming Convention

Generate skill names from the problem/solution:

```
{problem-domain}-{specific-issue}
```

### Examples

| Problem | Skill Name |
|---------|------------|
| Prisma connection pool exhaustion | `prisma-connection-pool-exhaustion` |
| Next.js hydration mismatch | `nextjs-hydration-mismatch-fix` |
| Docker compose DNS issues | `docker-compose-network-dns-resolution` |
| TypeScript circular dependency | `typescript-circular-dependency-workaround` |
| React useEffect infinite loop | `react-useeffect-infinite-loop-fix` |
| PostgreSQL connection timeout | `postgres-connection-timeout-configuration` |

### Naming Rules

1. Use kebab-case (lowercase with hyphens)
2. Start with technology/framework name
3. End with problem type (fix, workaround, configuration, etc.)
4. Keep under 50 characters
5. Be specific enough to distinguish from similar issues

## Description Requirements

The description field is **critical** for semantic matching. Include:

### Required Elements

1. **Exact error messages** (for matching)
2. **Technology and version** (for context)
3. **Symptoms** (what user observes)
4. **Trigger conditions** (when it happens)

### Example Description

```yaml
description: |
  React hydration mismatch error: "Text content does not match server-rendered HTML"
  Occurs with Next.js 13+ when server and client render different content.
  Use when: (1) seeing hydration warnings in console, (2) dynamic content
  differs between server and client, (3) using client-only libraries on server.
  Solves: Hydration mismatch causing React to re-render entire component tree.
```

## Content Guidelines

### Problem Section

- Describe what goes wrong
- Include exact error messages
- Explain impact (why it matters)

### Context Section

- List all trigger conditions
- Include technology versions
- Describe environment (local, CI, production)

### Solution Section

- Step-by-step instructions
- Include actual commands/code
- Explain why each step works
- Note any prerequisites

### Verification Section

- How to confirm the fix worked
- What to look for
- Expected behavior after fix

### Notes Section

- Edge cases where fix doesn't apply
- Related issues
- Alternative approaches
- Known limitations

## Skill Location

### Project-Level (Default)

Create in `.claude/skills/{name}/SKILL.md`:
- Can be reviewed before committing
- Versioned with the project
- Can be moved to global if broadly applicable

### Global-Level

If the skill applies across projects, move to `~/.claude/skills/{name}/SKILL.md`:
- Available in all projects
- User-level persistence
- Not project-versioned

## Example Complete Skill

```markdown
---
name: nextjs-hydration-mismatch-fix
description: |
  React hydration mismatch error: "Text content does not match server-rendered HTML"
  Occurs with Next.js 13+ App Router when server and client render different content.
  Use when: (1) hydration warnings in browser console, (2) dynamic content like
  dates/times differ, (3) browser-only APIs used during SSR.
  Solves: Hydration mismatch causing full client re-render.
author: Claude Code (auto-generated via /reflect)
version: 1.0.0
date: 2026-01-18
confidence: HIGH
---

# Next.js Hydration Mismatch Fix

## Problem

React throws "Text content does not match server-rendered HTML" or similar
hydration errors when the server-rendered HTML doesn't match what React
expects on the client. This causes React to discard the server HTML and
re-render the entire component tree client-side, defeating SSR benefits.

## Context / Trigger Conditions

Use this skill when you encounter:
- Console warning: "Text content does not match server-rendered HTML"
- Console warning: "Hydration failed because the initial UI does not match"
- Using `Date.now()`, `Math.random()`, or similar in render
- Accessing `window`, `localStorage`, or `navigator` during SSR
- Different timezone between server and client

## Solution

1. **Identify dynamic content**: Find code that produces different values on server vs client

2. **Use client-only rendering for dynamic content**:
   ```tsx
   'use client'
   import { useState, useEffect } from 'react'

   function DynamicContent() {
     const [mounted, setMounted] = useState(false)

     useEffect(() => {
       setMounted(true)
     }, [])

     if (!mounted) return null  // or a placeholder

     return <div>{new Date().toLocaleString()}</div>
   }
   ```

3. **Use Next.js dynamic imports with ssr: false**:
   ```tsx
   import dynamic from 'next/dynamic'

   const ClientOnlyComponent = dynamic(
     () => import('./ClientOnlyComponent'),
     { ssr: false }
   )
   ```

4. **Use suppressHydrationWarning for intentional mismatches**:
   ```tsx
   <time suppressHydrationWarning>{new Date().toISOString()}</time>
   ```

## Verification

- No hydration warnings in browser console
- Page loads without flicker
- Server HTML matches client HTML (check source vs DOM)

## Example

In the debugging session, the issue was a `<time>` element showing current
date which differed between server build time and client render time. Fixed
by wrapping in a mounted check to only render the date client-side.

## Notes

- `suppressHydrationWarning` only suppresses the warning, doesn't fix the mismatch
- Prefer mounted check or dynamic import over suppressing warnings
- For timestamps, consider using relative time (e.g., "2 hours ago") calculated client-side
- Server components in Next.js 13+ don't have this issue for static content

## References

- https://nextjs.org/docs/messages/react-hydration-error
- https://react.dev/reference/react-dom/client/hydrateRoot#handling-different-client-and-server-content
```

## Skill Creation Checklist

Before finalizing a skill:

- [ ] Name follows kebab-case convention
- [ ] Description includes error messages for matching
- [ ] All quality gates passed
- [ ] Problem clearly described
- [ ] Trigger conditions specific
- [ ] Solution is step-by-step with code
- [ ] Verification steps included
- [ ] Notes cover edge cases
- [ ] Created in `.claude/skills/` for review
