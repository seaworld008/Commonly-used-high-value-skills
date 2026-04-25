# Decision Templates

Output formats for variant selection, specification validation, and Arena session reporting.

---

## Selection Rationale Format

Use this format when documenting why a variant was chosen.

```markdown
### Variant Selection: [session_id]

**Mode:** [Solo / Team]
**Selected:** Variant [X] (Engine: [engine], Branch: arena/variant-[engine])
**Rejected:** Variant [Y] (Engine: [engine], Branch: arena/variant-[engine])

**Rationale:**
- Correctness: [Score] - [Comment]
- Code Quality: [Score] - [Comment]
- Performance: [Score] - [Comment]
- Safety: [Score] - [Comment]
- Simplicity: [Score] - [Comment]

**Decisive Factor:** [The single most important reason for selection]

**Trade-offs Accepted:**
- [What was sacrificed and why it's acceptable]

**Preservation Notes:**
- [Ideas from rejected variants worth remembering for future work]
```

---

## Specification Validation Report

Use when validating specification quality before running engines.

```markdown
### Spec Validation: [spec_description]

**Overall Quality:** [Good / Needs Revision / Insufficient]

**Ambiguities Found:**
1. [Ambiguity description] - Severity: [High/Medium/Low]
   - Suggested clarification: [How to resolve]
2. [Ambiguity description] - Severity: [High/Medium/Low]
   - Suggested clarification: [How to resolve]

**Missing Elements:**
- [ ] [Missing element 1]
- [ ] [Missing element 2]

**Recommendation:** [Proceed / Revise before running / Generate spec variants]
```

---

## Session Summary Format (COMPETE)

Use at the end of a COMPETE session to summarize all activity.

```markdown
### Arena Session Summary (COMPETE)

**Task:** [Task description]
**Date:** [YYYY-MM-DD]
**Paradigm:** COMPETE
**Mode:** [Solo / Team / Quick]

**Variants Executed:**
| Session ID | Engine | Branch | Winner | Cost Est. |
|------------|--------|--------|--------|-----------|
| [ID] | [engine] | arena/variant-[engine] | [yes/no] | [estimate] |

**Total Cost Estimate:** [Approximate]

**Final Implementation:**
- Selected: Variant [X] (Engine: [engine])
- Adopted via: `git merge arena/variant-[engine]`
- Files Changed: [count] files
- Test Status: [PASS/FAIL]

**Key Learnings:**
- [Learning 1 - e.g., engine performance observation]
- [Learning 2 - e.g., spec pattern insight]
```

---

## Session Summary Format (COLLABORATE)

Use at the end of a COLLABORATE session.

```markdown
### Arena Session Summary (COLLABORATE)

**Task:** [Task description]
**Date:** [YYYY-MM-DD]
**Paradigm:** COLLABORATE
**Mode:** [Solo / Team]

**Subtasks Executed:**
| Subtask ID | Engine | Branch | Status | Files Changed |
|------------|--------|--------|--------|---------------|
| [subtask_id] | [engine] | arena/task-[subtask_id] | [PASS/FAIL] | [count] |

**Integration Order:** [subtask_id_1] → [subtask_id_2] → ...
**Merge Conflicts:** [None / Resolved (details)]

**Total Cost Estimate:** [Approximate]

**Integration Verification:**
- Build: [PASS/FAIL]
- Tests: [PASS/FAIL] ([N] tests)
- codex review: [Summary]
- Interface check: [PASS/FAIL]

**Files Changed (total):** [count]

**Engine Effectiveness:**
- codex ([subtask_ids]): [Brief assessment]
- gemini ([subtask_ids]): [Brief assessment]

**Key Learnings:**
- [Learning 1 - e.g., decomposition strategy insight]
- [Learning 2 - e.g., integration observation]
```

---

## AUTORUN Compact Report

Abbreviated format for Nexus autonomous mode. Omit verbose explanations.

### COMPETE

```markdown
## Arena COMPETE Result
- Session: [session_id] | Mode: [Solo/Team/Quick] | Engine: [engine(s)] | Variants: [N]
- Winner: Variant [X] (Score: [X.XX/5.00])
- Rationale: [One sentence]
- Files: [list]
- Cost: [estimate]
- Status: [PASS/FAIL/PENDING]
```

### COLLABORATE

```markdown
## Arena COLLABORATE Result
- Session: [session_id] | Mode: [Solo/Team] | Subtasks: [N]
- Engines: codex ([subtask_ids]), gemini ([subtask_ids])
- Integration: [CLEAN / CONFLICTS_RESOLVED]
- Files: [list]
- Build: [PASS/FAIL] | Tests: [PASS/FAIL]
- Cost: [estimate]
- Status: [SUCCESS/PARTIAL/FAILED]
```

---

## Hybrid Variant Documentation

When the best solution combines elements from multiple variants.

```markdown
### Hybrid Selection: [session_id]

**Mode:** [Solo / Team]
**Base:** Variant [X] (Engine: [engine])
**Merged From:** Variant [Y] (Engine: [engine])

**What was taken from each:**
| Element | Source | Reason |
|---------|--------|--------|
| [Component/approach] | Variant [X] | [Why this part is better] |
| [Component/approach] | Variant [Y] | [Why this part is better] |

**Integration Notes:**
- [How the parts were combined]
- [Any conflicts resolved during merge]

**Verification:**
- [ ] Combined implementation passes all tests
- [ ] No conflicts between merged approaches
- [ ] Performance is not degraded by combination
```

---

## Hybrid Adoption Procedure

Step-by-step procedure for combining elements from multiple variants into a single implementation.

### When to Use Hybrid Adoption

- No single variant is best across all criteria
- Variant A excels in some files/modules, Variant B in others
- Combining the best parts produces a clearly superior result
- The combined elements do not have architectural conflicts

### File-Level Selection Method

The primary hybrid approach is **file-level cherry-picking** — selecting specific files from different variants.

#### Step-by-Step Procedure

```bash
# 1. Start from the base variant (the one with the higher overall score)
git checkout $BASE_BRANCH
git merge arena/variant-codex -m "arena: hybrid base from variant-codex"

# 2. Cherry-pick specific files from the other variant
git checkout arena/variant-gemini -- src/module/file-to-take.ts
git checkout arena/variant-gemini -- src/module/file-to-take.test.ts

# 3. Stage the cherry-picked files
git add src/module/file-to-take.ts src/module/file-to-take.test.ts

# 4. Commit the hybrid result
git commit -m "arena: hybrid adoption (base: codex, cherry-picked: gemini files)"
```

#### Alternative: Partial Function-Level Cherry-Pick

When you need specific functions from another variant (not entire files):

```bash
# 1. Merge the base variant
git checkout $BASE_BRANCH
git merge arena/variant-codex -m "arena: hybrid base from variant-codex"

# 2. Show the specific function from the other variant
git show arena/variant-gemini:src/module/file.ts
# Manually identify the function/section to adopt

# 3. Use Edit tool to replace the specific function
# (Arena leader performs the surgical edit using Read + Edit tools)

# 4. Commit the hybrid result
git add -A && git commit -m "arena: hybrid adoption (base: codex, function-level: gemini)"
```

### Post-Hybrid Verification (MANDATORY)

After any hybrid adoption, Arena MUST re-run verification checks. The combination of elements from different variants may introduce integration issues.

```bash
# 1. Scope Check — verify no unexpected files were added
git diff --name-only $BASE_COMMIT..HEAD

# 2. Build Verification — the hybrid MUST build
npm run build  # or project-specific build command

# 3. Test Execution — the hybrid MUST pass all tests
npm test  # or project-specific test command

# 4. Integration Check — verify combined elements work together
# Read the hybrid files and check for:
# - Import/export consistency
# - Type compatibility
# - No duplicated functionality
# - No conflicting patterns (e.g., sync vs async approaches)
```

**If post-hybrid verification fails:**
1. Identify the incompatible element
2. Revert to the base variant: `git reset --hard HEAD~1` (reverts the hybrid commit)
3. Either: fix the incompatibility and re-attempt, OR adopt the base variant as-is
4. Document the hybrid failure in the session report

### Hybrid Decision Documentation

Always document hybrid decisions using the existing "Hybrid Variant Documentation" template (see above), plus:

```markdown
**Post-Hybrid Verification:**
- [ ] Build passes
- [ ] All tests pass
- [ ] No import/type conflicts
- [ ] Combined elements integrate cleanly
- [ ] No performance regression from mixed approaches
```

---

## Escalation Report

When Arena cannot make a clear selection and needs user input.

```markdown
### Escalation: Variant Selection Required

**Session:** [session_id]
**Mode:** [Solo / Team]
**Reason:** [Why automated selection is insufficient]

**Candidates:**

| Aspect | Variant A | Variant B |
|--------|-----------|-----------|
| Engine | [engine] | [engine] |
| Branch | arena/variant-[engine] | arena/variant-[engine] |
| Score | [X.XX] | [X.XX] |
| Approach | [Brief] | [Brief] |
| Strength | [Key advantage] | [Key advantage] |
| Weakness | [Key disadvantage] | [Key disadvantage] |

**Arena's Lean:** Variant [X] (confidence: [Low/Medium])
**Decisive Question:** [What information would resolve this?]

**Options:**
1. Adopt Variant [A] - [one-line rationale]
2. Adopt Variant [B] - [one-line rationale]
3. Hybrid approach - combine best of both
4. Re-run with refined spec
```
