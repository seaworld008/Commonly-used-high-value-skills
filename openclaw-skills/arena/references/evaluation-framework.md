# Evaluation Framework

Quality metrics, scoring methodology, and comparison report templates for variant evaluation.

**Pipeline position:** This framework covers the REVIEW → EVALUATE stages of the Arena workflow:
- COMPETE Solo: `SPEC → SCOPE LOCK → EXECUTE → **REVIEW → EVALUATE** → ADOPT → VERIFY`
- COMPETE Team: `SPEC → DESIGN → SPAWN → COMPETE → **REVIEW → EVALUATE** → ADOPT → CLEANUP`
- COLLABORATE Solo/Team: `SPEC → DECOMPOSE → SCOPE LOCK → EXECUTE → **REVIEW** → INTEGRATE → VERIFY`

**Note:** In COLLABORATE mode, REVIEW is per-subtask (same checklist) but there is no comparative EVALUATE phase. Instead, all passing subtasks proceed to INTEGRATE. See `collaborate-mode-guide.md` for COLLABORATE-specific review considerations (e.g., EXPECTED_FAIL for cross-subtask dependencies).

---

## Variant Scoring Matrix

| Criterion | Weight | Score (1-5) | Weighted | Description |
|-----------|--------|-------------|----------|-------------|
| Correctness | 40% | | | Meets specification requirements completely |
| Code Quality | 25% | | | Readability, maintainability, idiomatic patterns |
| Performance | 15% | | | Efficiency, resource usage, scalability |
| Safety | 15% | | | Error handling, input validation, security |
| Simplicity | 5% | | | Avoids over-engineering, minimal complexity |
| **Total** | 100% | | | |

### Score Definitions

| Score | Label | Meaning |
|-------|-------|---------|
| 5 | Excellent | Exceeds requirements, best-in-class |
| 4 | Good | Meets all requirements with minor room for improvement |
| 3 | Adequate | Meets core requirements, some gaps |
| 2 | Below Average | Partial implementation, notable issues |
| 1 | Poor | Fails to meet requirements |

### Weight Adjustment Guidelines

Default weights work for most scenarios. Adjust when:

| Scenario | Adjustment |
|----------|------------|
| Security-critical code | Safety: 30%, Code Quality: 20% |
| Performance-sensitive path | Performance: 30%, Simplicity: 0% |
| Prototype / exploration | Simplicity: 15%, Performance: 5% |
| Legacy codebase integration | Code Quality: 35%, Correctness: 30% |

---

## Post-Completion Review Checklist (MANDATORY)

After each variant completes execution, Arena MUST run this review checklist **before** proceeding to comparative evaluation. This is a quality gate — no variant enters EVALUATE without a completed review.

### Review Steps (run on each variant)

| # | Check | Command / Method | Result | Severity |
|---|-------|------------------|--------|----------|
| 1 | **Scope Validation** | `git diff --name-only $BASE_COMMIT..arena/variant-{engine}` | PASS if only allowed files modified | **CRITICAL** — revert unauthorized files |
| 2 | **Build Verification** | Run project build command (e.g., `npm run build`, `go build ./...`) | PASS / FAIL / SKIP (no build configured) | **CRITICAL** — FAIL = disqualify |
| 3 | **Test Execution** | Run project test command (e.g., `npm test`, `pytest`, `go test ./...`) | PASS / FAIL / SKIP (no tests configured) | **HIGH** — FAIL = penalize Correctness |
| 4 | **Automated Code Review** | `codex review --uncommitted` | Summary of findings | **MEDIUM** — feeds Code Quality & Safety |
| 5 | **Acceptance Criteria** | Read implementation, check each criterion from spec | Met / Unmet per criterion | **HIGH** — all unmet = disqualify |

**Execution order matters:** Scope → Build → Test → Review → Acceptance. If Build fails, skip remaining checks (variant is already disqualified).

### Solo Mode Review

Arena leader runs the checklist **after each engine commits**, before moving to the next variant or EVALUATE:

```bash
# After codex variant commits:
git checkout arena/variant-codex

# 1. Scope check
git diff --name-only $BASE_COMMIT..HEAD
# Compare against allowed_files, revert any violations

# 2. Build
npm run build  # or project-specific build command

# 3. Test
npm test  # or project-specific test command

# 4. codex review
codex review --uncommitted
# ...
```

### Team Mode Review

Arena leader runs the checklist **after all subagents complete and report back**. Use the worktree directories or checkout each branch:

```bash
# Review variant-codex (using worktree if still available, or checkout)
cd /tmp/$SESSION_ID/variant-codex  # or: git checkout arena/variant-codex

# Run the same 5-step checklist
# Repeat for variant-gemini
```

### Review Result Template

Record results for each variant using this structure:

```yaml
review_result:
  variant: "arena/variant-{engine}"
  engine: "{codex | gemini}"
  checks:
    scope:
      status: PASS | FAIL
      unauthorized_files: []  # Files that were reverted
      notes: ""
    build:
      status: PASS | FAIL | SKIP
      error_output: ""  # First 10 lines of error if FAIL
    test:
      status: PASS | FAIL | SKIP
      passed: 0
      failed: 0
# ...
```

### Disqualification Rules

| Condition | Verdict | Action |
|-----------|---------|--------|
| Build fails | **DISQUALIFY** | Variant cannot be adopted; skip remaining checks |
| Scope violation (core logic in forbidden files) | **DISQUALIFY** | Cannot revert without breaking implementation |
| All acceptance criteria unmet | **DISQUALIFY** | Engine did not address the spec |
| Scope violation (reverted successfully) | **WARN** | Note violation, deduct from Code Quality score |
| Some tests fail | **WARN** | Penalize Correctness score; still evaluate |
| codex review finds critical issues | **WARN** | Penalize Safety score; still evaluate |
| No tests exist / cannot run | **PASS with note** | Cannot verify; note in evaluation |

### Integration with Evaluation Scoring

Review results directly feed into the 5-criteria scoring:

| Review Check | Scoring Impact |
|-------------|----------------|
| Scope validation | Code Quality: scope violations = -1 point |
| Build verification | Correctness: build fail = disqualify |
| Test execution | Correctness: all pass = +1, failures = -1 per severity |
| codex review findings | Code Quality: quality findings, Safety: security findings |
| Acceptance criteria | Correctness: directly determines base score |
| Quantitative metrics | Simplicity: code volume, Code Quality: exported symbols (see "Quantitative Metrics Collection" section) |

---

## Automated Review Gate Logic

The REVIEW phase follows a strict sequential gate with early termination. Variants that fail critical gates are immediately disqualified without running subsequent checks.

### Disqualification Fast-Path

```
┌─────────────┐
│ Scope Check  │──FAIL (unrevertable)──→ DISQUALIFY (skip all remaining checks)
└──────┬───────┘
       │ PASS / WARN (reverted)
       ▼
┌─────────────┐
│ Build Check  │──FAIL──→ DISQUALIFY (skip all remaining checks)
└──────┬───────┘
       │ PASS
       ▼
┌─────────────┐
│ Test Check   │──FAIL──→ Correctness penalty applied (continue to next check)
└──────┬───────┘
       │ PASS
       ▼
...
```

### Gate Execution Rules

| Gate | Pass Condition | Fail Action | Continues? |
|------|---------------|-------------|------------|
| **Scope Check** | Only allowed files modified, OR unauthorized files successfully reverted | Unrevertable scope violation (core logic in forbidden files) → DISQUALIFY | Only if PASS/WARN |
| **Build Check** | Project builds successfully (`npm run build`, `go build`, etc.) | Build failure → DISQUALIFY immediately | Only if PASS |
| **Test Check** | All existing tests pass | Test failures → apply Correctness penalty (−1 per critical failure, −0.5 per minor) | Always continues |
| **codex review** | N/A (informational gate) | Findings feed into Code Quality and Safety scores | Always continues |
| **Acceptance Check** | At least 1 acceptance criterion met | ALL criteria unmet → DISQUALIFY | Only if SOME/ALL MET |

### Early Termination Benefits

- **Saves time:** Build failures are caught before running expensive test suites or codex review
- **Clear signal:** Disqualified variants are excluded from EVALUATE — no ambiguity about whether to include them
- **Resource efficiency:** codex review (API cost) is only run on variants that pass Build Check

### Edge Cases

| Scenario | Handling |
|----------|----------|
| No build command configured | Skip Build Check (PASS with note) |
| No test command configured | Skip Test Check (PASS with note) |
| codex review unavailable | Skip codex review (no impact on scoring) |
| Scope violation partially revertable | Revert what's possible → WARN, deduct from Code Quality, continue |
| All variants disqualified | Abort EVALUATE → notify user → suggest spec refinement or re-run |

---

## Evaluation Data Collection

Arena collects evaluation data directly from Git and file reading — no external abstraction layer.

### Variant Comparison via Git

```bash
# Diff between two variant branches
git diff arena/variant-codex..arena/variant-gemini

# Diff a variant against the base commit
git diff $BASE_COMMIT..arena/variant-codex

# See files changed by a variant
git diff --stat $BASE_COMMIT..arena/variant-codex

# Show a specific file in a variant branch
git show arena/variant-codex:path/to/file
```

### Direct File Reading

For detailed review, checkout each branch and read files directly:

```bash
git checkout arena/variant-codex
# Use Read tool to inspect implementation files

git checkout arena/variant-gemini
# Use Read tool to inspect implementation files
```

### Automated Review Integration

Use `codex review` as supplementary quality signal:

```bash
# Review uncommitted changes (checkout variant branch first)
git checkout arena/variant-codex
codex review --uncommitted
```

**How to integrate review results:**
- Feed `codex review` findings into **Code Quality** score (patterns, readability, maintainability)
- Feed security-related findings into **Safety** score (vulnerabilities, input validation)
- Review output is supplementary evidence — Arena's own analysis takes precedence

### Test Result Integration

Run tests on each variant branch and reflect results in Correctness score:

```bash
git checkout arena/variant-codex
# Run project-specific test command (npm test, pytest, etc.)
```

**Scoring impact:**
| Test Result | Correctness Impact |
|------------|-------------------|
| All tests pass + new tests added | Score 4-5 |
| All existing tests pass, no new tests | Score 3-4 |
| Some test failures | Score 2-3 (depending on severity) |
| Major test failures | Score 1-2 |
| Tests cannot run | Score 1 (investigate) |

---

## Enhanced Comparison Tooling

Beyond basic `git diff`, use these techniques for deeper variant comparison.

### Statistical Comparison

```bash
# File-level change statistics per variant
git diff --stat $BASE_COMMIT..arena/variant-codex
git diff --stat $BASE_COMMIT..arena/variant-gemini

# Compact summary (insertions/deletions only)
git diff --shortstat $BASE_COMMIT..arena/variant-codex
git diff --shortstat $BASE_COMMIT..arena/variant-gemini

# Side-by-side file change comparison
echo "=== Variant A (codex) ===" && git diff --stat $BASE_COMMIT..arena/variant-codex
echo "=== Variant B (gemini) ===" && git diff --stat $BASE_COMMIT..arena/variant-gemini
```

### Function/Symbol-Level Diff Detection

Identify what logical units changed (not just lines):

```bash
# Show function-level changes (for supported languages)
git diff --diff-filter=M -p $BASE_COMMIT..arena/variant-codex | grep -E '^\+.*function |^\+.*class |^\+.*def |^\+.*const .* = '

# Compare function signatures between variants
git show arena/variant-codex:src/module.ts | grep -E 'export (function|class|const|interface)' > /tmp/codex-exports.txt
git show arena/variant-gemini:src/module.ts | grep -E 'export (function|class|const|interface)' > /tmp/gemini-exports.txt
diff /tmp/codex-exports.txt /tmp/gemini-exports.txt
```

### Parallel Test Result Comparison

Run tests on both variants and compare results side-by-side:

```bash
# Collect test results for each variant
git checkout arena/variant-codex
npm test 2>&1 | tee /tmp/test-result-codex.txt
TEST_EXIT_CODEX=$?

git checkout arena/variant-gemini
npm test 2>&1 | tee /tmp/test-result-gemini.txt
TEST_EXIT_GEMINI=$?

# Quick comparison
echo "=== Test Results Comparison ==="
echo "Codex: exit=$TEST_EXIT_CODEX"
echo "Gemini: exit=$TEST_EXIT_GEMINI"
diff /tmp/test-result-codex.txt /tmp/test-result-gemini.txt || true
```

### Complexity Metrics

Approximate code complexity comparison:

```bash
# Line count comparison
echo "=== Lines of Code ==="
git diff --stat $BASE_COMMIT..arena/variant-codex | tail -1
git diff --stat $BASE_COMMIT..arena/variant-gemini | tail -1

# File count comparison
echo "=== Files Changed ==="
git diff --name-only $BASE_COMMIT..arena/variant-codex | wc -l
git diff --name-only $BASE_COMMIT..arena/variant-gemini | wc -l

# New vs modified files
echo "=== New Files (codex) ===" && git diff --diff-filter=A --name-only $BASE_COMMIT..arena/variant-codex
echo "=== New Files (gemini) ===" && git diff --diff-filter=A --name-only $BASE_COMMIT..arena/variant-gemini
```

### Comparison Summary Template

After collecting comparison data, summarize:

```markdown
| Metric | Variant A ({engine}) | Variant B ({engine}) |
|--------|---------------------|---------------------|
| Files changed | {N} | {N} |
| Lines added | {N} | {N} |
| Lines removed | {N} | {N} |
| New files | {N} | {N} |
| Test result | PASS/FAIL | PASS/FAIL |
| Tests passing | {N}/{total} | {N}/{total} |
| Build result | PASS/FAIL | PASS/FAIL |
| Exported symbols | {N} | {N} |
```

---

## Quantitative Metrics Collection

Supplement subjective scoring with automated, measurable metrics. These provide objective data points for variant comparison.

### Automated Metrics

| Metric | Command | Unit | Higher = Better? |
|--------|---------|------|-----------------|
| Lines added | `git diff --shortstat $BASE_COMMIT..arena/variant-{engine}` | count | Depends on context |
| Lines removed | `git diff --shortstat $BASE_COMMIT..arena/variant-{engine}` | count | Depends on context |
| Files changed | `git diff --name-only $BASE_COMMIT..arena/variant-{engine} \| wc -l` | count | Lower is simpler |
| New files created | `git diff --diff-filter=A --name-only $BASE_COMMIT..arena/variant-{engine} \| wc -l` | count | Lower is simpler |
| Test count (pass) | Project test runner output | count | Higher is better |
| Test count (fail) | Project test runner output | count | 0 is required |
| Build time | `time {build_command}` | seconds | Lower is better |
| Exported symbols | `grep -E 'export (function\|class\|const\|interface)' {files}` | count | Fewer = simpler API |

### Collection Template

After running the review checklist, collect quantitative metrics for each variant:

```yaml
quantitative_metrics:
  variant: "arena/variant-{engine}"
  code_volume:
    lines_added: 0
    lines_removed: 0
    files_changed: 0
    new_files: 0
    net_lines: 0  # added - removed
  test_results:
    total: 0
    passed: 0
    failed: 0
    skipped: 0
    coverage_delta: "+0%"  # If coverage tool available
  build:
# ...
```

### Integration with Scoring

Quantitative metrics inform but do not replace the 5-criteria scoring:

| Metric | Scoring Impact |
|--------|---------------|
| Code volume (net lines) | Simplicity: fewer lines for same functionality = higher score |
| Test pass rate | Correctness: 100% pass = baseline, failures penalize |
| New test count | Correctness: more tests covering new behavior = bonus |
| Build success | Correctness: build fail = disqualify |
| Exported symbols | Code Quality: smaller API surface = higher score |
| Coverage delta | Correctness: positive delta = bonus, negative = penalty |

---

## Comparison Report Template

```markdown
## Arena Comparison Report

### Session Information
- Session ID: [session_id]
- Spec: [Spec description]
- Mode: [Solo / Team]
- Engines: [List of engines used]
- Variants Generated: [N]
- Date: [YYYY-MM-DD]

### Variant Summaries

#### Variant A (Engine: [engine], Branch: arena/variant-[engine])
- Approach: [Brief description of implementation strategy]
- Strengths: [Key advantages]
...
```

---

## Quick Evaluation (for AUTORUN mode)

When time is constrained, use this abbreviated format:

```markdown
## Quick Eval: [session_id]
| Variant | Engine | Correct | Quality | Perf | Safety | Simple | Total |
|---------|--------|---------|---------|------|--------|--------|-------|
| A | [engine] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [X.XX] |
| B | [engine] | [1-5] | [1-5] | [1-5] | [1-5] | [1-5] | [X.XX] |

**Winner:** Variant [X] ([one-line rationale])
**Mode:** [Solo/Team]
**Cost:** [estimate]
```

---

## Evaluation Anti-Patterns

Avoid these common evaluation mistakes:

| Anti-Pattern | Problem | Correction |
|--------------|---------|------------|
| **Recency bias** | Favoring the last variant reviewed | Score each criterion independently, then compare |
| **Halo effect** | One strong criterion overshadowing weaknesses | Apply weighted scoring strictly |
| **Complexity worship** | Preferring "clever" over "clear" | Simplicity criterion exists for a reason |
| **Sunk cost** | Favoring variant from expensive engine | Judge output, not input cost |
| **Feature creep** | Rewarding variants that add unrequested features | Score against spec, not beyond it |

---

## Tie-Breaking Rules

When variants score within 0.2 points of each other:

1. **Correctness wins** - If one is more correct, it wins regardless of total
2. **Simplicity wins** - Among equally correct variants, prefer simpler
3. **Safety wins** - If security is relevant, prefer safer
4. **Cost wins** - If all else equal, prefer cheaper engine
5. **Escalate** - If truly indistinguishable, present both to user with trade-offs

---

## Learning Metrics

Track session outcomes to improve future Arena decisions. Record metrics in the Arena journal (`.agents/arena.md`) after each session.

### Session Metrics Schema

```yaml
session_metrics:
  date: "YYYY-MM-DD"
  task_type: "feature | bugfix | refactor | optimization | migration"
  paradigm: "COMPETE | COLLABORATE"
  mode: "Quick | Solo | Team"
  engines_used:
    - engine: "codex"
      model: "o4-mini"  # if specified
    - engine: "gemini"
  variant_count: 2
  self_competition: false  # true if same engine used for multiple variants
  self_competition_strategy: "approach_hint | model_variant | prompt_verbosity | null"
  winner:
    variant: "arena/variant-codex"
    engine: "codex"
# ...
```

### Metrics Accumulation

Over time, accumulated metrics inform:

| Metric Pattern | Insight | Action |
|----------------|---------|--------|
| Engine X wins >70% for task_type Y | Engine X is dominant for this task type | Update Engine Selection Heuristics default |
| Self-Competition score gaps consistently <0.5 | Same engine produces similar variants | Prefer cross-engine competition or combined strategies |
| Model A consistently beats Model B | Model performance hierarchy for this codebase | Default to winning model |
| Quick Mode escalation rate >30% | Eligibility criteria too permissive | Tighten Quick Mode criteria (e.g., ≤ 2 files instead of ≤ 3) |
| Average Team Mode score gap > Solo Mode | Parallelism and diversity improve quality | Recommend Team Mode more aggressively |

### Compact Journal Entry Format

For quick metric logging after each session:

```markdown
## YYYY-MM-DD - [Task Summary]
**Metrics:** {mode} | {engines} | {variant_count}v | Winner: {engine} ({score}) | Gap: {score_gap}
**Discovery:** [What was learned]
**Impact:** [How this changes future usage]
```

---

## REFINE Phase Framework

The REFINE phase is an optional iterative improvement cycle that can be inserted into the COMPETE workflow between EVALUATE and ADOPT. When the best variant is good but not great, REFINE attempts to improve it through targeted re-execution.

### When to Trigger REFINE

REFINE is triggered when ALL of the following conditions are met:

| Condition | Threshold |
|-----------|-----------|
| Best variant passes REVIEW (not disqualified) | Required |
| Best variant total score | 2.5 ≤ score < 4.0 |
| At least one criterion scored ≤ 3 | Required |
| Remaining time/budget allows re-execution | Required |
| Task is not Quick Mode | Required |

**Do NOT trigger REFINE when:**
- Best variant scores ≥ 4.0 (already good enough)
- Best variant scores < 2.5 (too poor — re-spec instead)
- All variants were disqualified (re-spec, not refine)
- Quick Mode (REFINE adds too much overhead for small tasks)

### REFINE Workflow

```
EVALUATE → [score < 4.0?] → REFINE → RE-EVALUATE → [improved?] → ADOPT
                                 ↑                        |
                                 └── [iteration < max] ───┘
```

**Updated COMPETE workflow with REFINE:**
```
SPEC → SCOPE LOCK → EXECUTE → REVIEW → EVALUATE → [REFINE] → ADOPT → VERIFY
```

### Refinement Prompt Template

The REFINE prompt builds on the original spec by adding specific improvement directives based on evaluation results:

```
Re-implement the following specification with targeted improvements.

## Original Specification
{original_spec_content}

## Previous Attempt Analysis
The previous implementation scored {total_score}/5.0. Specific weaknesses:
{weakness_list}

## Improvement Directives
Focus on improving these specific areas:
{improvement_directives}

## What Worked Well (preserve these aspects)
{strengths_to_preserve}
...
```

### Iteration Limits

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Max iterations | 2 | Diminishing returns after 2 refinement attempts |
| Min score improvement | 0.3 | Below this, further refinement is unlikely to help |
| Timeout per iteration | Same as original execution | Prevent runaway cost |

### Exit Conditions

REFINE exits and proceeds to ADOPT when ANY of these conditions is true:

| Condition | Action |
|-----------|--------|
| Score ≥ 4.0 | ADOPT refined variant |
| Max iterations reached (2) | ADOPT best variant so far |
| Score improvement < 0.3 between iterations | ADOPT current variant (diminishing returns) |
| Refined variant scores worse than original | ADOPT original variant |
| Build/test failure in refined variant | ADOPT original variant |

### Score Comparison Template

```yaml
refine_result:
  original:
    variant: "arena/variant-{engine}"
    score: {original_total}
    breakdown:
      correctness: {score}
      code_quality: {score}
      performance: {score}
      safety: {score}
      simplicity: {score}
  refined_iteration_1:
    variant: "arena/variant-{engine}-refined-1"
    score: {refined_total}
    breakdown:
      correctness: {score}
# ...
```
