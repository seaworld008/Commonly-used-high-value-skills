# Team Mode Guide

Guide for running Arena in Team Mode using the Agent Teams API for true parallel execution of external AI engines.

---

## Core Concept

In Team Mode, Arena acts as the **team leader** and spawns subagents (Claude Code `general-purpose` agents) that serve as **proxies** for external AI engines. Each subagent's sole job is to invoke an external CLI (`codex exec` or `gemini`) via the Bash tool — the subagent does NOT implement code itself.

```
Arena (Team Leader)
├── variant-codex (subagent) → Bash: codex exec ...
├── variant-gemini (subagent) → Bash: gemini -p ...
└── [optional: variant-codex-2, variant-gemini-2, ...]
```

**Key principle:** Subagents are remote hands, not brains. They delegate all implementation work to external engines.

---

## Arena Paradigms and Rally: Competition vs Cooperation

| Aspect | Arena COMPETE (Team Mode) | Arena COLLABORATE (Team Mode) | Rally |
|--------|--------------------------|-------------------------------|-------|
| **Purpose** | Competition — same spec, different engines | Cooperation — different subtasks, external engines | Cooperation — different tasks, Claude Code only |
| **Subagent tasks** | All do the SAME task differently | Each does a DIFFERENT subtask | Each does a DIFFERENT task |
| **External engines** | codex, gemini | codex, gemini | None (Claude Code only) |
| **Result handling** | Compare → select best → discard rest | Merge ALL in dependency order | Collect all → integrate all |
| **Branch naming** | `arena/variant-{engine}` | `arena/task-{subtask_id}` | N/A (Rally's own protocol) |
| **Typical use** | "Which engine produces better auth code?" | "codex handles algorithm, gemini handles API" | "Build frontend + backend + tests in parallel" |
| **Evaluation** | 5-criteria scoring, winner selection | Per-subtask review, integration verification | Completeness check, integration validation |

**This guide covers COMPETE Team Mode.** For COLLABORATE Team Mode (parallel subtask execution with worktrees), see `collaborate-mode-guide.md` — the same worktree isolation mechanism is reused.

---

## When to Use Team Mode vs Solo Mode

| Condition | Solo Mode | Team Mode |
|-----------|-----------|-----------|
| Variant count | 2 | 3+ |
| Parallelism | Sequential | True parallel |
| Cost | Low (single session) | Higher (N sessions) |
| Complexity | Low-Medium | High |
| Best for | codex vs gemini 2-way comparison | Multi-approach, engine mixing |

**Default to Solo Mode.** Use Team Mode when:
- 3+ variants are needed
- Time is a bottleneck and parallel execution matters
- Multiple approach hints need to be tested with the same engine

---

## Team Design Patterns

### Pattern 1: Engine Competition

Two subagents, each using a different engine to implement the same spec.

```
Arena Leader
├── variant-codex  → codex exec "{spec}"
└── variant-gemini → gemini -p "{spec}"
```

### Pattern 2: Multi-Approach

Multiple subagents using the same or different engines with different approach hints.

```
Arena Leader
├── variant-codex-iterative → codex exec "{spec} Use an iterative approach"
├── variant-codex-recursive → codex exec "{spec} Use a recursive approach"
└── variant-gemini-novel    → gemini -p "{spec} Propose a novel approach"
```

### Pattern 3: Engine + Review

Combine implementation and automated review in parallel.

```
Arena Leader
├── variant-codex  → codex exec "{spec}" → git commit
├── variant-gemini → gemini -p "{spec}" → git commit
└── reviewer       → (waits for completion) → codex review on both branches
```

### Pattern 4: Same-Engine Multi-Variant (Self-Competition)

Multiple subagents using the same engine with different approach hints for Self-Competition.

```
Arena Leader
├── variant-codex-iterative  → codex exec "{spec} Prefer iterative approach"
├── variant-codex-functional → codex exec "{spec} Prefer functional approach"
└── variant-codex-minimal    → codex exec "{spec} Prefer minimal implementation"
```

**Worktree setup for same-engine variants:**

```bash
SESSION_ID="arena-$(date +%s)"
BASE_COMMIT=$(git rev-parse HEAD)
mkdir -p /tmp/$SESSION_ID

# Create branches for each approach variant
git branch arena/variant-codex-iterative $BASE_COMMIT
git branch arena/variant-codex-functional $BASE_COMMIT
git branch arena/variant-codex-minimal $BASE_COMMIT

# Create isolated worktrees
git worktree add /tmp/$SESSION_ID/variant-codex-iterative arena/variant-codex-iterative
git worktree add /tmp/$SESSION_ID/variant-codex-functional arena/variant-codex-functional
git worktree add /tmp/$SESSION_ID/variant-codex-minimal arena/variant-codex-minimal
```

### Pattern 5: Mixed Competition (Cross-Engine + Self-Competition)

Combine cross-engine and same-engine variants for maximum diversity.

```
Arena Leader
├── variant-codex-imperative → codex exec "{spec} Prefer imperative style"
├── variant-codex-functional → codex exec "{spec} Prefer functional style"
├── variant-gemini-standard  → gemini -p "{spec}" --yolo
└── variant-gemini-sandbox   → gemini -p "{spec}" --sandbox
```

---

## Lifecycle

```
SPEC → DESIGN → SPAWN → COMPETE → REVIEW → EVALUATE → ADOPT → CLEANUP
```

### Phase 1: SPEC

Arena leader validates or creates the specification (same as Solo Mode).

### Phase 2: DESIGN

Arena leader decides:
- How many variants
- Which engines
- Which approach hints
- Branch naming

### Phase 3: SPAWN (with git worktree isolation)

Arena leader creates **isolated working directories** via `git worktree` BEFORE spawning subagents. This prevents all parallel execution conflicts (`.git/index.lock` contention, filesystem write conflicts, cross-contamination).

```python
# 1. Prepare worktrees (Arena leader via Bash)
# git stash push -m "arena: pre-session stash"
# BASE_COMMIT=$(git rev-parse HEAD)
# SESSION_ID="arena-$(date +%s)"
# mkdir -p /tmp/$SESSION_ID

# 2. Create branches and worktrees
# git branch arena/variant-codex $BASE_COMMIT
# git branch arena/variant-gemini $BASE_COMMIT
# git worktree add /tmp/$SESSION_ID/variant-codex arena/variant-codex
# git worktree add /tmp/$SESSION_ID/variant-gemini arena/variant-gemini

# 3. Create team
TeamCreate(team_name="arena-{task_id}")

# ...
```

**CRITICAL:** The Arena leader MUST create all branches and worktrees BEFORE spawning subagents. Subagents receive the worktree path and operate within it — they do NOT create branches, checkout, or switch directories outside their assigned worktree.

### Phase 4: COMPETE (parallel-safe)

Subagents work in **true parallel** with full filesystem isolation:
- Each `cd`s into its pre-created worktree directory
- Each invokes its assigned engine CLI within its isolated directory
- Each `git add -A && git commit` only affects files in its own worktree
- No `.git/index.lock` contention — worktrees share the repo but have independent index files
- Each commits results and marks task complete

Arena leader monitors via TaskList and waits for all tasks to complete.

### Phase 5: REVIEW (Mandatory Quality Gate)

After all subagents complete, the Arena leader runs a **mandatory review** on each variant. This is a quality gate — no variant proceeds to EVALUATE without passing review.

For each variant branch, the Arena leader:

1. **Scope Check** — `git diff --name-only $BASE_COMMIT..arena/variant-{engine}` and verify only allowed files were modified
2. **Test Execution** — Checkout or use worktree to run the project's test command (`npm test`, `pytest`, etc.)
3. **Build Verification** — Run the project's build command to confirm the variant compiles/builds
4. **Automated Code Review** — `codex review --uncommitted` for code quality and security signals
5. **Acceptance Criteria Check** — Read implementation files and verify each acceptance criterion from the spec is met

**Review result per variant:**

```yaml
review_result:
  variant: "arena/variant-{engine}"
  scope_check: PASS | FAIL   # Were only allowed files modified?
  test_result: PASS | FAIL | SKIP  # Did tests pass?
  build_result: PASS | FAIL | SKIP  # Did build succeed?
  codex_review_summary: "[Key findings]"
  acceptance_criteria:
    - criterion: "[Criterion 1]"
      met: true | false
    - criterion: "[Criterion 2]"
      met: true | false
  overall: PASS | FAIL | WARN
  notes: "[Any issues or observations]"
```

**Disqualification rules:**
- **Scope FAIL** → Attempt to revert unauthorized files and re-check; if core logic is in forbidden files, disqualify
- **Test FAIL** → Variant is penalized in Correctness score but NOT automatically disqualified (may still be the best option)
- **Build FAIL** → Variant is disqualified (cannot be adopted)
- **All criteria unmet** → Variant is disqualified

### Phase 6: EVALUATE

Arena leader uses **review results as primary input** for scoring:
1. Reads implementation files
2. Runs `git diff` between variants
3. Applies 5-criteria scoring (see `evaluation-framework.md`) informed by review results
4. Selects winner from variants that passed review

### Phase 7: ADOPT

Arena leader merges winning branch into base branch.

### Phase 7: CLEANUP

**IMPORTANT:** Remove worktrees BEFORE deleting branches. `git branch -D` will fail if a worktree still references the branch.

```python
# 1. Shutdown subagents
SendMessage(type="shutdown_request", recipient="variant-codex", ...)
SendMessage(type="shutdown_request", recipient="variant-gemini", ...)

# 2. Delete team
TeamDelete()

# 3. Remove worktrees (MUST be done before branch deletion)
# git worktree remove /tmp/$SESSION_ID/variant-codex
# git worktree remove /tmp/$SESSION_ID/variant-gemini
# rm -rf /tmp/$SESSION_ID

# 4. Clean up branches
# git branch -D arena/variant-codex arena/variant-gemini

# ...
```

---

## Teammate Prompt Templates

**CRITICAL**: Arena leader MUST construct the full engine prompt (with scope lock, constraints, and acceptance criteria) BEFORE spawning subagents. The `{engine_prompt}` below is the complete prompt built via `references/engine-cli-guide.md` "Prompt Construction Protocol".

### variant-codex

```
You are variant-codex on the arena-{task_id} team.

## Your Role
You are a PROXY for the codex CLI tool. You do NOT implement code yourself.
Your sole job is to invoke `codex exec` via the Bash tool in your assigned worktree directory.

## ABSOLUTE PROHIBITIONS
- NEVER write, edit, or generate implementation code yourself
- NEVER use Edit, Write, or NotebookEdit tools
- NEVER attempt to fix, improve, or adjust engine output
- NEVER modify files that the engine did not touch
- NEVER install, add, or remove dependencies
- NEVER modify config files (tsconfig, eslint, webpack, docker, CI/CD, etc.)
- NEVER create or checkout branches — your worktree is already on the correct branch
- NEVER operate outside your assigned worktree directory
...
```bash
cd {worktree_path}
```
Verify you are on the correct branch:
```bash
git branch --show-current
# Expected output: arena/variant-codex
```

### 2. Run codex with the EXACT prompt below (do not modify it)
```bash
codex exec --full-auto "{engine_prompt}"
```

### 3. Validate scope — check which files were changed
```bash
git diff --name-only
```
Compare against the allowed files list below.
If ANY file outside the allowed list was modified, revert it:
```bash
git checkout -- {unauthorized_file}
```

### 4. Commit only authorized changes
```bash
git add -A && git commit -m "arena: variant-codex implementation"
```

### 5. Report to team leader
Send a message with:
- Files changed: `git diff --stat HEAD~1`
- Scope violations: list any files that were reverted
- Engine errors/warnings: any output issues from codex
- Completeness assessment: does the diff cover the spec?

### 6. Mark task as completed via TaskUpdate

## Allowed Files (engine may ONLY touch these)
{allowed_files_list}

## Forbidden Files (revert if engine touches these)
{forbidden_files_list}
...
```

### variant-gemini

```
You are variant-gemini on the arena-{task_id} team.

## Your Role
You are a PROXY for the gemini CLI tool. You do NOT implement code yourself.
Your sole job is to invoke `gemini` via the Bash tool in your assigned worktree directory.

## ABSOLUTE PROHIBITIONS
- NEVER write, edit, or generate implementation code yourself
- NEVER use Edit, Write, or NotebookEdit tools
- NEVER attempt to fix, improve, or adjust engine output
- NEVER modify files that the engine did not touch
- NEVER install, add, or remove dependencies
- NEVER modify config files (tsconfig, eslint, webpack, docker, CI/CD, etc.)
- NEVER create or checkout branches — your worktree is already on the correct branch
- NEVER operate outside your assigned worktree directory
...
```bash
cd {worktree_path}
```
Verify you are on the correct branch:
```bash
git branch --show-current
# Expected output: arena/variant-gemini
```

### 2. Run gemini with the EXACT prompt below (do not modify it)
```bash
gemini -p "{engine_prompt}" --yolo
```

### 3. Validate scope — check which files were changed
```bash
git diff --name-only
```
Compare against the allowed files list below.
If ANY file outside the allowed list was modified, revert it:
```bash
git checkout -- {unauthorized_file}
```

### 4. Commit only authorized changes
```bash
git add -A && git commit -m "arena: variant-gemini implementation"
```

### 5. Report to team leader
Send a message with:
- Files changed: `git diff --stat HEAD~1`
- Scope violations: list any files that were reverted
- Engine errors/warnings: any output issues from gemini
- Completeness assessment: does the diff cover the spec?

### 6. Mark task as completed via TaskUpdate

## Allowed Files (engine may ONLY touch these)
{allowed_files_list}

## Forbidden Files (revert if engine touches these)
{forbidden_files_list}
...
```

### variant-{engine}-{approach} (Self-Competition)

For same-engine variants with approach hints. Adapt the base engine template by adding the approach directive.

```
You are variant-{engine}-{approach} on the arena-{task_id} team.

## Your Role
You are a PROXY for the {engine} CLI tool. You do NOT implement code yourself.
Your sole job is to invoke `{engine_command}` via the Bash tool in your assigned worktree directory.

## ABSOLUTE PROHIBITIONS
[Same as standard engine template — see variant-codex/variant-gemini templates above]

## ALLOWED ACTIONS (exhaustive list)
[Same as standard engine template]

## Your Worktree
Your assigned working directory is: {worktree_path}
This directory is an isolated copy of the repository on branch `arena/variant-{engine}-{approach}`.
...
```bash
cd {worktree_path}
```
Verify you are on the correct branch:
```bash
git branch --show-current
# Expected output: arena/variant-{engine}-{approach}
```

### 2. Run {engine} with the EXACT prompt below (do not modify it)
```bash
{engine_invocation_command}
```
NOTE: The prompt includes an Approach Directive that differentiates this variant from others using the same engine. Do NOT remove or modify the Approach Directive.

### 3-6. [Same as standard engine template — scope validation, commit, report, mark complete]

## Allowed Files
{allowed_files_list}

## Forbidden Files
{forbidden_files_list}

## Engine Prompt (pass to {engine} exactly as-is — includes Approach Directive)
{engine_prompt_with_approach_hint}
```

---

## Monitoring & Error Handling

### Progress Monitoring

Arena leader checks progress via:

```python
# Check task status
TaskList()  # Shows all tasks with status

# Send message to check on slow subagent
SendMessage(type="message", recipient="variant-codex", content="Status update?")
```

### Error Recovery

| Situation | Action |
|-----------|--------|
| Subagent engine fails | Subagent reports error → Leader decides: retry, skip, or replace |
| Subagent times out | Leader sends status check → If unresponsive, shutdown and re-spawn |
| Branch conflict | Leader resolves by resetting branch from base commit |
| All variants fail | Leader falls back to Solo Mode with different prompts |

### Re-spawn Strategy

If a subagent fails:

```python
# 1. Shutdown failed subagent
SendMessage(type="shutdown_request", recipient="variant-codex", ...)

# 2. Clean up its worktree and branch
# git worktree remove /tmp/$SESSION_ID/variant-codex
# git branch -D arena/variant-codex

# 3. Recreate branch and worktree
# git branch arena/variant-codex $BASE_COMMIT
# git worktree add /tmp/$SESSION_ID/variant-codex arena/variant-codex

# 4. Create new task and spawn replacement
TaskCreate(subject="Re-implement spec via codex exec (retry)", ...)
Task(
  subagent_type="general-purpose",
# ...
```

---

## Cleanup Guarantee Protocol

Cleanup MUST succeed even if individual steps fail. Use `|| true` to ensure all cleanup steps are attempted, and `--force` flags where available.

### Guaranteed Cleanup Sequence

```bash
# Step 1: Remove worktrees (force removal — tolerates dirty state)
git worktree remove --force /tmp/$SESSION_ID/variant-codex 2>/dev/null || true
git worktree remove --force /tmp/$SESSION_ID/variant-gemini 2>/dev/null || true
# Repeat for all variant worktrees...

# Step 2: Prune stale worktree references
git worktree prune || true

# Step 3: Remove temp directory
rm -rf /tmp/$SESSION_ID || true

# Step 4: Delete variant branches
git branch -D arena/variant-codex 2>/dev/null || true
git branch -D arena/variant-gemini 2>/dev/null || true
# Repeat for all variant branches...
# ...
```

**Key principles:**
- Every cleanup command uses `|| true` to prevent cascading failures
- `git worktree remove --force` handles dirty worktrees (uncommitted changes)
- `git worktree prune` cleans up references to manually-deleted worktree directories
- `2>/dev/null` suppresses error output for already-cleaned resources
- Worktrees MUST be removed before their branches are deleted

### When to Run Cleanup

| Scenario | Trigger |
|----------|---------|
| Normal completion | After ADOPT phase, before session ends |
| Partial failure | If any subagent fails and session continues with remaining variants |
| Total failure | All variants fail or are disqualified |
| User cancellation | User requests to stop the Arena session |
| Error in EVALUATE/ADOPT | Cleanup is mandatory regardless of where the error occurs |

**IMPORTANT:** Even if the Arena session fails at any point, the Cleanup Guarantee Protocol MUST run. Arena leader should wrap the main workflow in a try-finally pattern (conceptually) to ensure cleanup always executes.

---

## Subagent Failure Scenarios

Detailed detection and recovery procedures for each failure type.

| # | Failure Scenario | Detection Method | Recovery Action | Max Retries |
|---|-----------------|-----------------|-----------------|-------------|
| 1 | **Engine CLI failure** (non-zero exit, error output) | Subagent reports error via SendMessage; task status remains in_progress | Reset branch to BASE_COMMIT, re-spawn subagent with same prompt | 1 |
| 2 | **Subagent no response** (>5 min silence) | TaskList shows task in_progress for >5 min; no SendMessage received | Send status check → if still no response after 1 min, send shutdown_request → re-spawn | 1 |
| 3 | **Git operation failure** (commit fails, merge conflict) | Subagent reports git error via SendMessage | Leader manually resolves: `git worktree remove --force` → recreate worktree → re-spawn | 1 |
| 4 | **Worktree creation failure** (path exists, branch in use) | `git worktree add` returns non-zero exit | Clean stale references: `git worktree prune` → retry creation; if still fails, use different temp path | 2 |
| 5 | **All variants fail** (every subagent reports failure or all disqualified) | All tasks completed with failure reports or all variants disqualified in REVIEW | Run Cleanup Guarantee Protocol → fall back to Solo Mode with refined prompts; if Solo also fails, ABORT and notify user | 0 (escalation) |

### Failure Recovery Flowchart

```
Subagent reports error or timeout detected
    │
    ├── Single variant failure?
    │   ├── Retries remaining? → Reset branch + Re-spawn
    │   └── No retries left? → Mark variant as FAILED, continue with remaining variants
    │
    └── All variants failed?
        ├── Attempt Solo Mode fallback with refined prompts
        └── Solo also fails? → ABORT + notify user + run Cleanup Guarantee
```

### Partial Success Handling

When some variants succeed and others fail:
- **Minimum viable evaluation:** Arena can evaluate with as few as 1 successful variant
- **Single variant scenario:** If only 1 variant succeeds, adopt it without comparative scoring (but still run REVIEW gate)
- **Report failures:** Include failed variants in the session summary with failure reasons

---

## Timeout Settings

Default timeout values for Team Mode operations. Adjust based on task complexity.

| Operation | Default Timeout | Adjustment |
|-----------|----------------|------------|
| Engine CLI execution (per invocation) | 5 minutes | Increase to 10 min for large codebases or complex specs |
| Subagent total completion | 10 minutes | Includes engine execution + scope validation + commit |
| Full Arena session (Team Mode) | 30 minutes | Covers SPAWN through CLEANUP |
| Status check response | 1 minute | Time to wait after sending status check before escalating |

### Timeout Enforcement

```bash
# Arena leader monitors elapsed time per subagent
# If subagent exceeds timeout:

# 1. Send status check
SendMessage(type="message", recipient="variant-codex", content="Status check: have you completed execution?")

# 2. Wait 1 minute for response

# 3. If no response, initiate recovery
SendMessage(type="shutdown_request", recipient="variant-codex", content="Timeout exceeded, shutting down")

# 4. Run Cleanup Guarantee for this variant's resources
git worktree remove --force /tmp/$SESSION_ID/variant-codex 2>/dev/null || true
git branch -D arena/variant-codex 2>/dev/null || true

# ...
```

**Note:** Timeouts are soft limits enforced by the Arena leader through periodic TaskList checks. There is no hard process kill — the leader uses shutdown_request and then cleans up resources.

---

## Complete Team Mode Example

```python
# === PREPARE (Arena leader via Bash) ===
# git stash push -m "arena: pre-session stash"
# BASE_BRANCH=$(git branch --show-current)
# BASE_COMMIT=$(git rev-parse HEAD)
# SESSION_ID="arena-$(date +%s)"
# mkdir -p /tmp/$SESSION_ID

# === CREATE BRANCHES & WORKTREES (Arena leader via Bash) ===
# git branch arena/variant-codex $BASE_COMMIT
# git branch arena/variant-gemini $BASE_COMMIT
# git worktree add /tmp/$SESSION_ID/variant-codex arena/variant-codex
# git worktree add /tmp/$SESSION_ID/variant-gemini arena/variant-gemini

# === SETUP TEAM ===
TeamCreate(team_name="arena-auth-refactor")
# ...
```
