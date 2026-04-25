# Output Templates

**Purpose:** Detailed templates and guidelines for each output format.
**Read when:** Deciding document structure or format during COMPOSE phase.

---

## Learning Document Template (Standard)

```markdown
# [Change Title] — Learning Document

## Meta
| Field | Value |
|-------|-------|
| Target | [commit hash / PR #number / branch name] |
| Date | YYYY-MM-DD |
| Audience | [beginner / intermediate / advanced] |
| Related files | [primary file list] |
| Change volume | [+XX / -YY lines, ZZ files] |

---

## Overview
[1-3 sentences describing the full picture: what changed, why, and how]

---

## Glossary
| Term | Definition | Context in this change |
|------|-----------|----------------------|
| [Term 1] | [General definition] | [Specific meaning/usage in this change] |

---

## Background (Why)

### Problem Solved
[Problem/issue that existed before the change]

### Motivation / Trigger
[What prompted this change — bug report, performance issue, new requirement, etc.]

### Constraints
[Technical or business constraints that influenced the change]

---

## Change Details (What & How)

### Change Point 1: [Title]

**Before:**
```[language]
// Pre-change code (necessary and sufficient scope)
```
[Explanation of pre-change behavior/problems]

**After:**
```[language]
// Post-change code (highlight diff with comments)
```
[Explanation of post-change behavior/improvements]

**Learning Point:**
> [General principle or pattern learnable from this change]

---

## Design Decisions (Why This Way)

### Adopted Approach
[Description of chosen design/pattern]

**Reasons for selection:**
1. [Reason 1]
2. [Reason 2]

### Alternatives Considered
| Alternative | Summary | Rejection Reason |
|-------------|---------|-----------------|
| [Option A] | [Summary] | [Why not adopted] |
| [Option B] | [Summary] | [Why not adopted] |

---

## Anti-patterns (Why Not)

### ❌ [Pattern to Avoid 1]
```[language]
// Code example of what NOT to do
```
**Why to avoid:** [Technical reason, potential problems]
**Instead:** [Reference to the correct approach]

---

## Flow Diagram
```mermaid
[Diagram showing how the change affects system flow]
[Mark changed portions]
```

---

## Summary & Lessons

### General Takeaways
1. [Lesson 1: principle applicable beyond this project]
2. [Lesson 2]

### Project-specific Notes
- [Note 1]

### References
- [Link 1]
```

---

## Glossary Template

Lightweight format focused on terminology:

```markdown
# [Target] — Glossary

| Term | Category | Definition | Usage in Code | Related Terms |
|------|----------|-----------|--------------|---------------|
| [Term] | [pattern/library/concept/api] | [Definition] | `[code usage]` | [Related] |
```

---

## Decision Record Template

ADR (Architecture Decision Record) style:

```markdown
# ADR-[number]: [Decision Title]

## Status
[Proposed / Accepted / Deprecated / Superseded]

## Context
[Background and situation requiring the decision]

## Options Considered

### Option 1: [Name]
- **Pros:** [Advantages]
- **Cons:** [Disadvantages]

### Option 2: [Name]
- **Pros:** [Advantages]
- **Cons:** [Disadvantages]

## Decision
[Chosen option and rationale]

## Consequences
[Impact and trade-offs of this decision]

## Related Commits
- [commit hash]: [description]
```

---

## Tutorial Template

Step-by-step reproducible walkthrough:

```markdown
# [Title] — Tutorial

## Prerequisites
- [Required knowledge 1]
- [Required tools/environment]

## Goal
[What the reader will be able to do after completing this tutorial]

## Steps

### Step 1: [Title]
[Explanation]
```[language]
// Code to execute
```
**Verify:** [Expected result]

### Step 2: [Title]
[Repeat same structure]

## Common Mistakes
| Mistake | Symptom | Correct Approach |
|---------|---------|-----------------|
| [Mistake 1] | [Error message etc.] | [How to do it right] |

## Extension Exercises
- [Challenge 1]
- [Challenge 2]
```

---

## Learning Series Template (Batch Mode)

Serialized episodes across multiple PRs/commits:

```markdown
# [Series Title] — Learning Series

## Series Overview
| Field | Value |
|-------|-------|
| Scope | [PR #1, #2, #3 / branch / sprint] |
| Episodes | [count] |
| Date range | YYYY-MM-DD — YYYY-MM-DD |
| Audience | [beginner / intermediate / advanced] |
| Theme | [What ties these changes together] |

## Series Map
| Episode | Target | Title | Key Concept |
|---------|--------|-------|-------------|
| 1 | PR #XX | [Title] | [Core concept] |
| 2 | PR #YY | [Title] | [Core concept] |

---

## Episode 1: [Title]
**Target:** [commit/PR ref]
**Prerequisite episodes:** None

[Standard learning document sections: Overview, Glossary, etc.]

### Connection to Series
- **Builds on:** [previous episode concepts, if any]
- **Leads to:** [what the next episode will cover]

---

## Episode 2: [Title]
[Repeat structure]

---

## Series Summary
### Concept Progression
[How understanding builds across episodes]

### Knowledge Graph
[Concept relationships across all episodes — hand off to Canvas for visualization]
```

---

## Incremental Update Template

Delta-only document comparing against a previous learning document:

```markdown
# [Component/Feature] — Incremental Update

## Meta
| Field | Value |
|-------|-------|
| Previous doc | [path/ref to previous learning doc] |
| Previous target | [original commit/PR] |
| Current target | [new commit/PR] |
| Date | YYYY-MM-DD |
| Audience | [level] |

---

## What Changed Since Last Document

### Added Knowledge
[New concepts, patterns, or decisions not present in previous doc]

### Changed Decisions
| Decision | Previous | Current | Reason for Change |
|----------|----------|---------|-------------------|
| [Decision] | [Old approach] | [New approach] | [Why it changed] |

### Deprecated Patterns
[Patterns from previous doc that are no longer valid]

### Unchanged (Reference)
[Brief pointer to previous doc sections that remain valid]

---

## Updated Glossary
[Only new or changed terms — reference previous doc for unchanged terms]

## Quality Scorecard
[Standard scorecard]
```

---

## Quality Scorecard Template

Attach at the end of every deliverable:

```markdown
## Quality Scorecard

| Axis | Score | Evidence |
|------|-------|----------|
| Fact/Inference Ratio | [A/B/C] | [X inferences labeled out of Y total claims] |
| Term Coverage | [A/B/C] | [X/Y first-occurrence terms defined] |
| Before/After Pairs | [A/B/C] | [N code comparison pairs included] |
| Why Not Depth | [A/B/C] | [N alternatives with rejection reasons] |
| Audience Fit | [A/B/C] | [Audience: level, detection: method, confidence: H/M/L] |

**Overall:** [PASS if no C scores / REVISION NEEDED if any C]
```

---

## Depth Adjustment Guidelines

### Beginner additions
- Add "Background: [Concept]" sections explaining framework/language basics
- Link to official documentation
- Include comprehension checks: "Can you explain this concept in one sentence?"

### Advanced compression
- Omit term definitions for standard industry vocabulary
- Focus on trade-off analysis, architecture impact, and alternative approaches
- Use concise technical prose without step-by-step elaboration
