# PR Template for Skill Contributions

Use the target repository's template. Keep the description proportional to the
change and explain the behavior a reviewer should assess.

## Title

```text
fix: clarify skill authorization and trigger scope
refactor: share instruction validation between local and CI
```

## Body

```markdown
## Summary

[Concrete trigger or problem, and how the skill behaves after this change.]

## Validation

[Checks actually run, relevant evidence, and untested behavior.]
```

For larger changes, add compatibility or source details that affect a decision:

- Which host-specific extensions are involved and what other agents can use.
- Whether source ownership or generated artifacts changed.
- Whether runtime comparison supports a behavior claim or only static checks ran.
- Whether an existing consumer needs to change its workflow.

Do not invent before/after measurements, require a quote from every source,
repeat the complete file list, or add empty sections. Cite official guidance when
it supports a material change. Attribution follows the target repository and
host requirements; this template does not append a tool trailer.

## Reviewer Questions

1. Is the task and trigger boundary clear?
2. Are user authority and required repository checks preserved?
3. Are examples, scripts and links still usable after installation?
4. Does the evidence support the claimed behavior change?
