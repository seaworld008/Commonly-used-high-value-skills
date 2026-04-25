# Collaborate Mode Guide

Guide for running Arena in COLLABORATE paradigm — splitting tasks across external engines by strength and integrating all results into a unified implementation.

---

## Core Concept

In COLLABORATE mode, Arena **decomposes** a complex task into independent subtasks, assigns each subtask to the external engine best suited for it, executes all subtasks (sequentially or in parallel), and then **integrates all results** into a single unified implementation.

```
COMPETE:  Same spec → Multiple engines → Pick best → Discard rest
COLLABORATE: Decomposed spec → Engine per subtask → Integrate ALL → Unified result
```

**Key principle:** Every engine's output is valuable and gets merged. COLLABORATE is cooperative, not competitive.

---

## When to Use COLLABORATE

| Condition | COLLABORATE | COMPETE |
|-----------|-------------|---------|
| Task naturally splits into parts | Yes | No |
| Each part matches a different engine's strengths | Yes | Doesn't matter |
| All subtask outputs needed in final result | Yes | No (pick one) |
| Quality comparison needed | No | Yes |
| Approach uncertainty | No | Yes |

**COLLABORATE is best when:**
- A feature has distinct components (e.g., core algorithm + API layer + UI integration)
- codex and gemini each excel at different subtasks
- The goal is a complete implementation, not a quality comparison
- External engines (not Claude Code) are needed for cooperative development

**COLLABORATE is NOT for:**
- Comparing approaches (use COMPETE)
- Tasks that cannot be cleanly split into non-overlapping file scopes
- Single-file changes (use COMPETE Quick Mode or Builder)
- When only Claude Code instances are needed (use Rally)

---

## Arena COLLABORATE vs Rally

| Aspect | Arena COLLABORATE | Rally |
|--------|-------------------|-------|
| **Execution engines** | External (codex, gemini) | Claude Code instances |
| **Task splitting** | By engine strengths | By file/module ownership |
| **Isolation** | Git worktrees + branches | Agent Teams API sessions |
| **Integration** | Git merge in dependency order | Rally's own merge protocol |
| **When to choose** | External engine strengths needed | Claude Code is sufficient |

---

## COLLABORATE Workflow

```
SPEC → DECOMPOSE → SCOPE LOCK → EXECUTE → REVIEW → INTEGRATE → VERIFY
```

### Phase 1: SPEC — Validate Full Specification

Same as COMPETE. Ensure the full feature specification is clear, complete, and testable. See SKILL.md → "Phase 1: SPEC" for details.

### Phase 2: DECOMPOSE — Split into Subtasks

This is the COLLABORATE-specific phase. Arena analyzes the spec and creates a decomposition plan.

#### Decomposition Template

```yaml
decomposition:
  task: "[Full task description]"
  subtask_count: 2  # Typically 2-4
  subtasks:
    - id: "core-logic"
      description: "Implement the core algorithm for X"
      engine: codex
      branch: "arena/task-core-logic"
      allowed_files:
        - "src/core/algorithm.ts"
        - "src/core/algorithm.test.ts"
      forbidden_files:
        - "package.json"
        - "tsconfig.json"
        - ".env*"
# ...
```

#### Decomposition Rules

1. **Non-overlapping file scopes** — Each file belongs to exactly ONE subtask. No file appears in multiple subtasks' `allowed_files`.
2. **Shared read-only files** — Common types, interfaces, configs go in `shared_read`. All engines can read these but MUST NOT modify them.
3. **Dependency-aware ordering** — Subtasks that depend on others' types or interfaces should be ordered later in `integration_order`.
4. **Engine-strength alignment** — Assign subtasks based on engine strengths (see Engine Assignment Strategy below).
5. **Minimum 2 subtasks** — COLLABORATE requires at least 2 subtasks. For single-subtask work, use COMPETE or Builder.
6. **Maximum 4 subtasks recommended** — More than 4 subtasks increases integration complexity and cost. Ask for confirmation if 5+.

#### Engine Assignment Strategy

| Subtask Characteristic | Recommended Engine | Rationale |
|------------------------|--------------------|-----------|
| Algorithm / data structure | codex | Fast, focused, code-centric |
| Refactoring / migration | codex | Strong at systematic code transformation |
| Performance optimization | codex | Precise, benchmarkable changes |
| API design / endpoint | gemini | Broader context understanding |
| Architecture / integration | gemini | Creative design, wide context window |
| New module from scratch | gemini | Handles broad specification well |
| Test generation | Either | Both capable; codex for unit, gemini for integration |

**When only 1 engine is available:**
COLLABORATE still works with a single engine — assign different subtasks to the same engine. The value comes from task decomposition and scope isolation, not engine diversity. Branch naming uses `arena/task-{subtask_id}` (not engine names).

---

### Phase 3: SCOPE LOCK — Per-Subtask Scope

Build a separate engine prompt for each subtask using the standard Prompt Construction Protocol from `engine-cli-guide.md`.

Each subtask prompt includes:
- The subtask-specific specification (NOT the full task spec)
- `allowed_files` for that subtask only
- `forbidden_files` (including other subtasks' files)
- `shared_read` files listed as read-only context
- Standard constraints from the prompt template
- Acceptance criteria specific to the subtask

**COLLABORATE-specific constraint addition:**

Add this to each subtask prompt:
```
## Scope Boundary (COLLABORATE mode)
This is ONE subtask of a larger feature. Other subtasks handle other parts.
- You are responsible ONLY for the files listed in "Allowed Files"
- Other parts of the feature will be implemented by other engines
- Do NOT attempt to implement the full feature — only your assigned portion
- Shared types in {shared_read_paths} are READ-ONLY reference — do NOT modify them
- If you need a type or interface that doesn't exist yet, define it in your allowed files and note it for integration
```

### Phase 4: EXECUTE — Run Engines

#### Solo Mode (Sequential)

```bash
BASE_COMMIT=$(git rev-parse HEAD)
git stash push -m "arena: pre-session stash"

# Subtask 1: core-logic (codex)
git checkout -b arena/task-core-logic $BASE_COMMIT
codex exec --full-auto "{subtask_1_prompt}"
git diff --name-only                      # Validate scope
git checkout -- {any_forbidden_files}     # Revert unauthorized changes
git add -A && git commit -m "arena: task-core-logic implementation"

# Subtask 2: api-integration (gemini)
git checkout -b arena/task-api-integration $BASE_COMMIT
gemini -p "{subtask_2_prompt}" --yolo
git diff --name-only                      # Validate scope
git checkout -- {any_forbidden_files}     # Revert unauthorized changes
# ...
```

#### Team Mode (Parallel)

Uses the same git worktree isolation as COMPETE Team Mode. See `team-mode-guide.md` for worktree lifecycle.

```bash
# 1. Prepare worktrees (Arena leader)
BASE_COMMIT=$(git rev-parse HEAD)
SESSION_ID="arena-$(date +%s)"
mkdir -p /tmp/$SESSION_ID

git branch arena/task-core-logic $BASE_COMMIT
git branch arena/task-api-integration $BASE_COMMIT
git worktree add /tmp/$SESSION_ID/task-core-logic arena/task-core-logic
git worktree add /tmp/$SESSION_ID/task-api-integration arena/task-api-integration

# 2. Spawn subagents (see Teammate Prompt Templates below)
# Each subagent gets its own worktree path and subtask-specific prompt
```

### Phase 5: REVIEW — Per-Subtask Quality Gate

Run the same 5-step review checklist as COMPETE (see `evaluation-framework.md` → "Post-Completion Review Checklist") on each subtask branch independently:

1. **Scope Check** — Verify only the subtask's allowed files were modified
2. **Build Check** — Run project build (may fail if subtask depends on another — expected)
3. **Test Check** — Run subtask's own tests
4. **codex review** — `codex review --uncommitted` on the subtask branch
5. **Acceptance Criteria** — Verify subtask-specific criteria

**COLLABORATE-specific review notes:**
- Build failures are EXPECTED if a subtask depends on another subtask's output (e.g., imports types that don't exist yet on the base branch). These are noted but NOT disqualifying.
- Test failures that are clearly due to missing dependencies from other subtasks are similarly noted but not disqualifying.
- Only failures within the subtask's own scope are disqualifying.

#### Review Result Template (COLLABORATE)

```yaml
review_result:
  subtask_id: "core-logic"
  branch: "arena/task-core-logic"
  engine: "codex"
  checks:
    scope:
      status: PASS | FAIL
      unauthorized_files: []
    build:
      status: PASS | FAIL | EXPECTED_FAIL
      notes: "Build fails due to missing API types from api-integration subtask — expected"
    test:
      status: PASS | FAIL | PARTIAL
      passed: 5
      failed: 0
# ...
```

### Phase 6: INTEGRATE — Merge All Results

Unlike COMPETE (pick one winner), INTEGRATE merges ALL passing subtask results in dependency order.

```bash
git checkout $BASE_BRANCH

# Merge in dependency order (integration_order from decomposition)
git merge arena/task-core-logic -m "arena: integrate task-core-logic"
# Verify no conflicts
git merge arena/task-api-integration -m "arena: integrate task-api-integration"
# Verify no conflicts
```

#### Conflict Resolution

With properly non-overlapping file scopes, merge conflicts should NOT occur. If they do:

| Conflict Type | Cause | Resolution |
|---------------|-------|------------|
| File in shared_read modified | Engine violated scope lock | Revert the unauthorized change, re-run subtask |
| Same file in two subtasks | Decomposition error — overlapping scopes | Fix decomposition, re-run affected subtask |
| Generated files (lock files, build output) | Side effect of engine execution | Take the version from the later subtask |
| Type/interface mismatch | Subtasks defined incompatible types | Arena leader manually resolves (Edit tool) |

**If merge conflicts occur in a shared type file:**
1. Read both versions
2. Manually merge the type definitions using the Edit tool
3. Ensure both subtasks' code works with the merged types
4. This is one of the few cases where Arena leader directly modifies code

### Phase 7: VERIFY — Integration Verification

After all subtasks are merged, run comprehensive verification:

```bash
# 1. Build — Full project build must pass
npm run build  # or project-specific build command

# 2. Tests — ALL tests must pass (including cross-subtask integration tests)
npm test  # or project-specific test command

# 3. codex review — Review the integrated result
codex review --uncommitted

# 4. Interface check — Verify imports/exports between subtask boundaries
# Read files at subtask boundaries and verify:
# - Import paths are correct
# - Exported types/functions match imported usage
# - No circular dependencies introduced
# - Shared types are used consistently
```

**If integration verification fails:**
1. Identify which subtask's output causes the failure
2. If it's an interface mismatch: Arena leader resolves with Edit tool
3. If it's a fundamental incompatibility: re-run the failing subtask with updated context
4. Document the issue in the session report

---

## Quick Collaborate Mode

Quick Collaborate is a lightweight variant of COLLABORATE for small-scope tasks. Arena executes both subtasks sequentially in Solo mode without spawning teammates, then integrates the results directly.

### Eligibility Criteria

| Criterion | Threshold |
|-----------|-----------|
| Total subtasks | Exactly 2 |
| Total files affected | ≤ 4 files |
| Estimated total change | ≤ 80 lines |
| Subtask interdependency | Low (minimal shared interfaces) |
| Engine availability | At least 1 engine available |

All criteria must be met. If any criterion is exceeded, escalate to standard Solo or Team COLLABORATE.

### Workflow Comparison

| Step | Standard COLLABORATE (Solo) | Quick Collaborate |
|------|----------------------------|-------------------|
| Worktree setup | 1 worktree per subtask | 1 worktree per subtask (same) |
| Subtask execution | Sequential `codex exec` / `gemini` | Sequential `codex exec` / `gemini` (same) |
| Integration | Full merge + verification script | Simplified merge + inline verification |
| Evaluation | Per-subtask + integrated scoring | Integrated scoring only (skip per-subtask) |
| REFINE eligibility | Yes | No — escalate to standard if score < 3.0 |
| Team spawning | No (Solo) | No |

### Execution Example

```
Arena (Quick Collaborate)
├── DECOMPOSE: Split task into 2 subtasks
├── Worktree: git worktree add arena/task-1
├── Bash: codex exec "subtask 1 prompt" (in arena/task-1)
├── Worktree: git worktree add arena/task-2
├── Bash: gemini -p "subtask 2 prompt" (in arena/task-2)
├── Integrate: git merge arena/task-1 + arena/task-2 into working branch
├── Verify: build + lint + type-check (inline, no separate script)
└── EVALUATE → ADOPT (no per-subtask scoring)
```

### Escalation Conditions

Quick Collaborate escalates to standard COLLABORATE when:

| Condition | Action |
|-----------|--------|
| Integration merge conflicts | Escalate to Solo COLLABORATE (full verification) |
| Integrated score < 3.0 | Escalate to Solo COLLABORATE with REFINE |
| Build/lint/type-check failure | Retry once; if still failing, escalate |
| Subtask produces > 40 lines | Continue but flag for post-session review |

---

## Teammate Prompt Templates (COLLABORATE)

### task-{subtask_id} (codex)

```
You are task-{subtask_id} on the arena-{task_id} team.

## Your Role
You are a PROXY for the codex CLI tool. You do NOT implement code yourself.
Your sole job is to invoke `codex exec` via the Bash tool in your assigned worktree directory.

## Context
This is a COLLABORATE session. You are implementing ONE SUBTASK of a larger feature.
Other subtasks are being handled by other engines in parallel.

## ABSOLUTE PROHIBITIONS
- NEVER write, edit, or generate implementation code yourself
- NEVER use Edit, Write, or NotebookEdit tools
- NEVER attempt to fix, improve, or adjust engine output
- NEVER modify files outside your allowed list
...
```bash
cd {worktree_path}
git branch --show-current
# Expected: arena/task-{subtask_id}
```

### 2. Run codex with the EXACT prompt below
```bash
codex exec --full-auto "{subtask_engine_prompt}"
```

### 3. Validate scope
```bash
git diff --name-only
```
Revert any files NOT in the allowed list:
```bash
git checkout -- {unauthorized_file}
```

### 4. Commit
```bash
git add -A && git commit -m "arena: task-{subtask_id} implementation"
```

### 5. Report to team leader
Include: files changed, scope violations, errors, completeness assessment.

### 6. Mark task complete

## Allowed Files
{allowed_files_list}

## Forbidden Files
{forbidden_files_list}

## Subtask Engine Prompt
{subtask_engine_prompt}
```

### task-{subtask_id} (gemini)

Same structure as the codex template above, with these differences:
- Engine command: `gemini -p "{subtask_engine_prompt}" --yolo`
- Branch: `arena/task-{subtask_id}`
- Worktree path: `{worktree_path}`

---

## Integration Report Template

After COLLABORATE completes, produce this report:

```markdown
### COLLABORATE Integration Report

**Task:** [Full task description]
**Date:** [YYYY-MM-DD]
**Mode:** [Solo / Team]

**Decomposition:**
| Subtask ID | Engine | Branch | Status | Files Changed |
|------------|--------|--------|--------|---------------|
| core-logic | codex | arena/task-core-logic | PASS | 2 |
| api-integration | gemini | arena/task-api-integration | PASS | 3 |

**Integration Order:** core-logic → api-integration
**Merge Conflicts:** None (clean merge)

...
```

---

## AUTORUN Compact Report (COLLABORATE)

For Nexus autonomous mode:

```markdown
## Arena COLLABORATE Result
- Session: [session_id] | Mode: [Solo/Team] | Subtasks: [N]
- Engines: codex ([subtask_ids]), gemini ([subtask_ids])
- Integration: [CLEAN / CONFLICTS_RESOLVED]
- Files: [list]
- Build: PASS | Tests: PASS
- Cost: [estimate]
- Status: [SUCCESS/PARTIAL/FAILED]
```

---

## Error Handling & Partial Failure

### Single Subtask Failure

If one subtask fails but others succeed:

1. **Assess impact:** Can the feature work without the failed subtask?
2. **If yes:** Integrate passing subtasks, report partial success, document what's missing
3. **If no:** Re-run the failed subtask with refined prompt (max 1 retry)
4. **If retry fails:** Report PARTIAL status, recommend manual completion or alternative approach

### All Subtasks Fail

1. Run Cleanup Guarantee Protocol (see `team-mode-guide.md`)
2. Analyze failure patterns:
   - If all engines failed on scope: decomposition was incorrect
   - If all engines failed on implementation: spec may be insufficient
3. Consider falling back to COMPETE paradigm (maybe the task doesn't split well)
4. Report FAILED status with analysis

### Integration Failure

If individual subtasks pass review but integration fails:

1. Identify the incompatible interface
2. Check if the issue is in shared types or at subtask boundaries
3. Arena leader resolves with minimal Edit tool changes
4. Re-run integration verification
5. If unresolvable: report PARTIAL, document the integration issue

---

## Complete COLLABORATE Example

### Scenario: Add User Authentication Feature

**Full spec:** Add JWT authentication with login endpoint, token verification middleware, and user session management.

**Decomposition:**

```yaml
decomposition:
  task: "Add JWT authentication feature"
  subtask_count: 2
  subtasks:
    - id: "auth-core"
      description: "Implement JWT token generation, verification, and refresh logic"
      engine: codex
      branch: "arena/task-auth-core"
      allowed_files:
        - "src/auth/jwt.ts"
        - "src/auth/jwt.test.ts"
        - "src/auth/types.ts"
      rationale: "codex excels at focused algorithmic/security work"
      dependencies: []

# ...
```

**Solo Mode execution:**

```bash
BASE_COMMIT=$(git rev-parse HEAD)
BASE_BRANCH=$(git branch --show-current)
git stash push -m "arena: pre-session stash"

# --- Subtask 1: auth-core (codex) ---
git checkout -b arena/task-auth-core $BASE_COMMIT
codex exec --full-auto "Implement JWT token logic.
## Specification
Create JWT token generation, verification, and refresh functions.
- generateToken(user: User): string — creates signed JWT with 1h expiry
- verifyToken(token: string): UserPayload — validates and decodes
- refreshToken(token: string): string — issues new token if valid
Use jsonwebtoken library (already installed).
## Scope Boundary (COLLABORATE mode)
This is ONE subtask. API endpoints and middleware are handled separately.
# ...
```

---

## Cleanup Protocol (COLLABORATE)

Same as COMPETE cleanup with subtask-specific branch/worktree names.

### Solo Mode Cleanup

```bash
git branch -D arena/task-core-logic arena/task-api-integration
git stash pop
```

### Team Mode Cleanup

```bash
# 1. Shutdown subagents
# SendMessage(type="shutdown_request", ...) for each subagent

# 2. Delete team
# TeamDelete()

# 3. Remove worktrees (MUST be before branch deletion)
git worktree remove --force /tmp/$SESSION_ID/task-core-logic 2>/dev/null || true
git worktree remove --force /tmp/$SESSION_ID/task-api-integration 2>/dev/null || true
git worktree prune || true
rm -rf /tmp/$SESSION_ID || true

# 4. Delete branches
git branch -D arena/task-core-logic 2>/dev/null || true
git branch -D arena/task-api-integration 2>/dev/null || true
# ...
```

---

## Journal Triggers (COLLABORATE-specific)

Arena SHOULD create a journal entry when:

| Trigger | Condition | What to Record |
|---------|-----------|----------------|
| **Integration Conflict** | Merge conflicts occurred despite non-overlapping scopes | Root cause, resolution, decomposition improvement |
| **Engine-Subtask Mismatch** | Engine performed poorly on assigned subtask | Update engine assignment heuristics |
| **Clean Integration** | All subtasks merged without issues | Validate that decomposition strategy works for this task type |
| **Partial Failure** | Some subtasks failed while others succeeded | Which engine/subtask failed, recovery steps taken |
| **Decomposition Revision** | Had to revise decomposition mid-session | What was wrong with initial decomposition |
