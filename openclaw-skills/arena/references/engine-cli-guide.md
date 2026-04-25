# Engine CLI Guide

Direct CLI reference for external AI engines used by Arena. Arena calls `codex exec` and `gemini` directly — no abstraction layer.

---

## Overview

Arena directly invokes external AI engine CLIs to generate implementation variants (COMPETE) or subtask implementations (COLLABORATE). Each engine runs in its own Git branch, producing isolated outputs.

### Key Principles

- **No abstraction layer** — Arena calls `codex exec` and `gemini` directly via Bash
- **Git branch isolation** — Each variant lives in its own `arena/variant-{engine}` branch (COMPETE) or `arena/task-{subtask_id}` branch (COLLABORATE)
- **Engine-agnostic evaluation** — Same scoring criteria regardless of which engine produced the code
- **Dual paradigm** — Same CLI commands for both COMPETE (compare variants) and COLLABORATE (integrate subtasks). See `collaborate-mode-guide.md` for COLLABORATE-specific prompt templates.

---

## Engine Availability Check

Before starting any Arena session, verify available engines:

```bash
# Check codex availability
which codex && echo "codex: available" || echo "codex: not found"

# Check gemini availability
which gemini && echo "gemini: available" || echo "gemini: not found"
```

**Minimum requirement:** At least 1 engine must be available. With 2+ engines, Arena runs cross-engine competition (default). With 1 engine, Arena switches to Self-Competition mode. With 0 engines, Arena aborts with a user notification.

---

## Self-Competition Mode

When only one engine is available, Arena generates variant diversity through different strategies applied to the same engine. This ensures Arena can still provide comparative quality even without multiple engines.

### Strategy 1: Approach Hint Divergence

Inject different design philosophy hints into the same specification prompt.

```bash
BASE_COMMIT=$(git rev-parse HEAD)

# Variant 1: iterative approach
git checkout -b arena/variant-codex-iterative $BASE_COMMIT
codex exec --full-auto "Implement the following specification.
{spec_content}
## Approach Directive
Prefer an ITERATIVE, step-by-step, imperative approach. Use loops, mutable state, and procedural decomposition.
{constraints_and_criteria}"
git add -A && git commit -m "arena: variant-codex-iterative implementation"

# Variant 2: functional approach
git checkout -b arena/variant-codex-functional $BASE_COMMIT
codex exec --full-auto "Implement the following specification.
{spec_content}
# ...
```

**Branch naming:** `arena/variant-{engine}-{approach}`
- `arena/variant-codex-iterative`
- `arena/variant-codex-functional`
- `arena/variant-codex-oop`
- `arena/variant-gemini-modular`

### Strategy 2: Model Variant Divergence

Use different models within the same engine CLI.

```bash
BASE_COMMIT=$(git rev-parse HEAD)

# Variant 1: o4-mini (fast, concise)
git checkout -b arena/variant-codex-o4-mini $BASE_COMMIT
codex exec --full-auto -m o4-mini "{spec_prompt}"
git add -A && git commit -m "arena: variant-codex-o4-mini implementation"

# Variant 2: o3 (powerful, thorough)
git checkout -b arena/variant-codex-o3 $BASE_COMMIT
codex exec --full-auto -m o3 "{spec_prompt}"
git add -A && git commit -m "arena: variant-codex-o3 implementation"
```

**Branch naming:** `arena/variant-{engine}-{model}`
- `arena/variant-codex-o4-mini`
- `arena/variant-codex-o3`

**Note:** Model availability depends on API access. Check engine documentation for supported models.

### Strategy 3: Prompt Verbosity Divergence

Vary the level of detail in the specification prompt.

```bash
BASE_COMMIT=$(git rev-parse HEAD)

# Variant 1: concise prompt (minimal guidance, more engine creativity)
git checkout -b arena/variant-codex-concise $BASE_COMMIT
codex exec --full-auto "Implement: {brief_spec}. Files: {allowed_files}. Tests must pass."
git add -A && git commit -m "arena: variant-codex-concise implementation"

# Variant 2: detailed prompt (comprehensive guidance, less ambiguity)
git checkout -b arena/variant-codex-detailed $BASE_COMMIT
codex exec --full-auto "{full_structured_prompt_with_all_sections}"
git add -A && git commit -m "arena: variant-codex-detailed implementation"
```

**Branch naming:** `arena/variant-{engine}-{style}`
- `arena/variant-codex-concise`
- `arena/variant-codex-detailed`

### Choosing a Self-Competition Strategy

| Strategy | Best When | Diversity Level |
|----------|-----------|-----------------|
| **Approach Hint** | Multiple valid design patterns exist | High |
| **Model Variant** | Engine supports multiple models with different strengths | Medium |
| **Prompt Verbosity** | Uncertain how much guidance the engine needs | Medium |
| **Combined** | Maximum diversity needed (e.g., different model + different approach) | Very High |

**Default recommendation:** Start with Approach Hint divergence — it produces the most meaningfully different implementations.

---

## Engine Command Reference

### codex exec

Execute implementation tasks via OpenAI Codex CLI.

```bash
# Basic execution (full-auto mode, no confirmation prompts)
codex exec --full-auto "implement the following: {spec_prompt}"

# With specific model
codex exec --full-auto -m o4-mini "implement the following: {spec_prompt}"
```

**Key flags:**
| Flag | Description |
|------|-------------|
| `--full-auto` | No confirmation prompts — required for Arena automation |
| `-m <model>` | Model selection (default: o4-mini) |

**Notes:**
- `codex exec` operates on the current working directory
- Changes are made directly to the filesystem (not sandboxed)
- Always run on a dedicated branch to isolate changes

### gemini CLI

Execute implementation tasks via Google Gemini CLI.

```bash
# Basic execution (YOLO mode, no confirmation prompts)
gemini -p "implement the following: {spec_prompt}" --yolo

# Sandbox mode (for safer execution)
gemini -p "implement the following: {spec_prompt}" --sandbox
```

**Key flags:**
| Flag | Description |
|------|-------------|
| `-p "<prompt>"` | Non-interactive prompt mode |
| `--yolo` | No confirmation prompts — required for Arena automation |
| `--sandbox` | Run in sandboxed environment (safer but limited) |

**Notes:**
- `gemini` operates on the current working directory
- `--yolo` allows file writes without confirmation
- Always run on a dedicated branch to isolate changes

### codex review (Automated Review)

Use codex as an automated reviewer for variant quality assessment.

```bash
# Review uncommitted changes on current branch
codex review --uncommitted

# Review specific files
codex review --uncommitted -- path/to/file1 path/to/file2
```

**Integration with evaluation:**
- Feed `codex review` output into Code Quality and Safety scores
- Use as supplementary evidence, not sole basis for scoring

---

## Git Branch-Based Variant Management

Arena uses Git branches to isolate each engine's implementation, enabling clean comparison and easy adoption.

### Branch Naming Convention

```
arena/variant-{engine}     # e.g., arena/variant-codex, arena/variant-gemini
arena/variant-{engine}-{n} # For multi-approach: arena/variant-codex-1, arena/variant-codex-2
```

### Solo Mode Lifecycle (Sequential — Single Working Directory)

Solo Mode runs engines **sequentially** in the same working directory. No parallel conflicts occur because only one engine runs at a time.

#### 1. Prepare (Stash & Branch)

```bash
# Save any uncommitted work
git stash push -m "arena: pre-session stash"

# Record the base point
BASE_BRANCH=$(git branch --show-current)
BASE_COMMIT=$(git rev-parse HEAD)
```

#### 2. Create Variant Branches

```bash
# Create codex variant branch from base
git checkout -b arena/variant-codex $BASE_COMMIT

# Create gemini variant branch from base (after codex is done)
git checkout -b arena/variant-gemini $BASE_COMMIT
```

#### 3. Execute Engine on Each Branch (Sequential)

```bash
# --- Codex variant ---
git checkout arena/variant-codex
codex exec --full-auto "{spec_prompt}"
git add -A && git commit -m "arena: variant-codex implementation"

# --- Gemini variant (runs AFTER codex is done) ---
git checkout arena/variant-gemini
gemini -p "{spec_prompt}" --yolo
git add -A && git commit -m "arena: variant-gemini implementation"
```

#### 4. Compare Variants

```bash
# Diff between variants
git diff arena/variant-codex..arena/variant-gemini

# Diff each variant against base
git diff $BASE_COMMIT..arena/variant-codex
git diff $BASE_COMMIT..arena/variant-gemini

# Read specific files for detailed review
# Use Read tool on files of interest in each branch
```

#### 5. Adopt Winner

```bash
# Return to base branch
git checkout $BASE_BRANCH

# Merge the winning variant
git merge arena/variant-codex -m "arena: adopt variant-codex"
# or
git merge arena/variant-gemini -m "arena: adopt variant-gemini"
```

#### 6. Cleanup

```bash
# Delete variant branches
git branch -D arena/variant-codex
git branch -D arena/variant-gemini

# Restore stashed work if any
git stash pop
```

---

### Team Mode Lifecycle (Parallel — git worktree Isolation)

Team Mode runs engines **in parallel**. To prevent conflicts, each variant gets its own **isolated working directory** via `git worktree`.

#### Why git worktree is Required for Parallel Execution

Without worktree isolation, parallel subagents sharing the same working directory will encounter:
- **`.git/index.lock` contention** — Multiple `git add`/`git commit` operations fight for the lock file
- **Filesystem write conflicts** — Two engines writing to the same files simultaneously corrupt output
- **Cross-contamination** — `git add -A` picks up another engine's uncommitted changes
- **Branch checkout races** — `git checkout` in a shared directory affects all processes

`git worktree` creates a **separate directory** for each branch, with its own working tree but sharing the same `.git` repository. Each subagent operates in complete filesystem isolation.

```
project/                          # Main working directory (Arena leader stays here)
├── .git/                         # Shared Git repository
├── src/...                       # Base branch files
└── ...

/tmp/arena-{session}/variant-codex/   # Worktree for codex (subagent works here)
├── src/...                           # Independent copy of files
└── ...

/tmp/arena-{session}/variant-gemini/  # Worktree for gemini (subagent works here)
├── src/...                           # Independent copy of files
└── ...
```

#### 1. Prepare (Arena Leader — BEFORE spawning subagents)

```bash
# Save any uncommitted work
git stash push -m "arena: pre-session stash"

# Record the base point
BASE_BRANCH=$(git branch --show-current)
BASE_COMMIT=$(git rev-parse HEAD)
SESSION_ID="arena-$(date +%s)"

# Create worktree base directory
mkdir -p /tmp/$SESSION_ID
```

#### 2. Create Branches and Worktrees (Arena Leader)

```bash
# Create variant branches from base commit
git branch arena/variant-codex $BASE_COMMIT
git branch arena/variant-gemini $BASE_COMMIT

# Create isolated worktrees for each variant
git worktree add /tmp/$SESSION_ID/variant-codex arena/variant-codex
git worktree add /tmp/$SESSION_ID/variant-gemini arena/variant-gemini
```

**IMPORTANT:** Arena leader creates ALL branches and worktrees BEFORE spawning any subagent. Subagents receive the worktree path and work within it — they do NOT create branches or worktrees themselves.

#### 3. Spawn Subagents (Arena Leader)

Each subagent receives its dedicated worktree path:
- variant-codex gets `/tmp/$SESSION_ID/variant-codex`
- variant-gemini gets `/tmp/$SESSION_ID/variant-gemini`

Subagents `cd` into their worktree and execute the engine there. No branch checkout needed — the worktree is already on the correct branch.

#### 4. Parallel Engine Execution (Subagents — fully isolated)

```bash
# --- variant-codex subagent (in /tmp/$SESSION_ID/variant-codex) ---
cd /tmp/$SESSION_ID/variant-codex
codex exec --full-auto "{spec_prompt}"
git add -A && git commit -m "arena: variant-codex implementation"

# --- variant-gemini subagent (in /tmp/$SESSION_ID/variant-gemini) ---
# (runs SIMULTANEOUSLY — no conflicts)
cd /tmp/$SESSION_ID/variant-gemini
gemini -p "{spec_prompt}" --yolo
git add -A && git commit -m "arena: variant-gemini implementation"
```

Each subagent's `git add -A` only sees files in its own worktree directory — no cross-contamination is possible.

#### 5. Compare Variants (Arena Leader — after all subagents complete)

```bash
# Diff between variants (same as Solo Mode — branches work normally)
git diff arena/variant-codex..arena/variant-gemini

# Diff each variant against base
git diff $BASE_COMMIT..arena/variant-codex
git diff $BASE_COMMIT..arena/variant-gemini
```

#### 6. Adopt Winner (Arena Leader)

```bash
# Return to base branch (leader is already here)
git checkout $BASE_BRANCH

# Merge the winning variant
git merge arena/variant-codex -m "arena: adopt variant-codex"
```

#### 7. Cleanup (Arena Leader — AFTER subagent shutdown)

```bash
# Remove worktrees FIRST (must be done before deleting branches)
git worktree remove /tmp/$SESSION_ID/variant-codex
git worktree remove /tmp/$SESSION_ID/variant-gemini

# Clean up temp directory
rm -rf /tmp/$SESSION_ID

# Delete variant branches
git branch -D arena/variant-codex
git branch -D arena/variant-gemini

# Restore stashed work if any
git stash pop
```

**WARNING:** Always remove worktrees before deleting branches. `git branch -D` will fail if a worktree still references the branch.

---

## Engine Selection Heuristics

| Engine | Strengths | Best For |
|--------|-----------|----------|
| **codex** | Fast iteration, code-focused, algorithmic strength | Refactoring, algorithmic tasks, pure code generation |
| **gemini** | Creative approaches, broad context window, novel solutions | New architecture, exploratory tasks, design-heavy work |

### Selection Decision Matrix

| Task Characteristic | Recommended Engine |
|--------------------|--------------------|
| Algorithm / data structure | codex |
| Refactoring / migration | codex |
| New feature with clear spec | codex + gemini (compare) |
| Creative / exploratory solution | gemini |
| Broad codebase understanding needed | gemini |
| Performance-critical optimization | codex |
| Default (when unsure) | codex + gemini (compare both) |

---

## Prompt Construction Protocol

Arena must construct precise, scoped prompts before passing them to any external engine. Vague prompts lead to uncontrolled changes.

### Step 1: Scope Lock (REQUIRED before any engine invocation)

Before running any engine, Arena MUST determine and lock the following:

```yaml
scope:
  # Files the engine is ALLOWED to create or modify
  allowed_files:
    - "src/auth/login.ts"
    - "src/auth/login.test.ts"
    - "src/types/auth.ts"

  # Files the engine MUST NOT touch (auto-include common sensitive files)
  forbidden_files:
    - "package.json"          # dependency changes need separate review
    - "package-lock.json"
    - "*.lock"
    - ".env*"                 # secrets
    - "tsconfig.json"         # build config
    - "*.config.js"           # build/lint config
# ...
```

**How to determine `allowed_files`:**
1. Read the spec and identify which modules/features are affected
2. Use `Glob` and `Grep` to find existing files in those modules
3. Include test files corresponding to each implementation file
4. If new files are needed, specify their exact paths

### Step 2: Build the Engine Prompt

Use the structured prompt templates below. **Every field is required** — do not omit sections.

### codex exec Prompt Template

```
Implement the following specification.

## Specification
{spec_content}

## Allowed Files (ONLY modify or create these files)
{allowed_files_list}

## Forbidden (DO NOT modify these files or patterns)
{forbidden_files_list}

## Constraints
- ONLY modify or create files listed in "Allowed Files" above
- DO NOT modify any file not listed in "Allowed Files"
- DO NOT add, remove, or modify dependencies (package.json, Gemfile, requirements.txt, etc.)
...
```

### gemini Prompt Template

```
Implement the following specification.

## Specification
{spec_content}

## Allowed Files (ONLY modify or create these files)
{allowed_files_list}

## Forbidden (DO NOT modify these files or patterns)
{forbidden_files_list}

## Constraints
- ONLY modify or create files listed in "Allowed Files" above
- DO NOT modify any file not listed in "Allowed Files"
- DO NOT add, remove, or modify dependencies (package.json, Gemfile, requirements.txt, etc.)
...
```

### Step 2b: Inject Approach Hints (for Multi-Variant / Self-Competition)

When generating multiple variants (whether cross-engine or same-engine), append an **Approach Directive** section to the base prompt. This section differentiates each variant's implementation strategy.

**Approach Directive template (append after Constraints, before Success Criteria):**

```
## Approach Directive
{approach_hint}
```

**Common approach hints:**

| Approach | Hint Text |
|----------|-----------|
| Iterative | "Prefer an ITERATIVE, step-by-step, imperative approach. Use loops, mutable state, and procedural decomposition." |
| Functional | "Prefer a FUNCTIONAL, declarative approach. Use immutable data, pure functions, and composition." |
| OOP | "Prefer an OBJECT-ORIENTED approach. Use classes, encapsulation, and polymorphism." |
| Minimal | "Prefer the SIMPLEST possible implementation. Minimize abstraction layers and code volume." |
| Robust | "Prefer a DEFENSIVE implementation. Add comprehensive error handling, input validation, and edge case coverage." |

**Important:** The approach hint is added AFTER the standard constraints. It guides style and design philosophy — it does NOT override scope lock or forbidden files rules.

### Step 3: Post-Execution Scope Validation

After each engine run, Arena MUST verify scope compliance:

```bash
# Check which files were actually changed
git diff --name-only

# Verify no forbidden files were touched
# If forbidden files were modified, revert them:
git checkout -- {forbidden_file}
```

If an engine modified files outside the allowed scope:
1. Revert unauthorized changes: `git checkout -- {file}`
2. Keep only authorized changes
3. Note the scope violation in the evaluation (deduct from Code Quality score)

### Prompt Construction Notes

- **codex** works best with focused, directive prompts — keep specs concise, list exact files
- **gemini** benefits from broader context — include tech stack, patterns, and reference files
- **Both** require explicit "DO NOT" constraints — engines will optimize broadly without them
- **Acceptance criteria** prevent engines from doing "too much" or "too little"
- **Allowed files list** is the single most important constraint for parallel safety

---

## Prompt Builder Checklist

Use this checklist to verify every engine prompt before invocation. Missing fields are the #1 cause of scope violations and poor variant quality.

### Required Fields

| # | Field | Status | Notes |
|---|-------|--------|-------|
| 1 | **Specification** | ☐ | Functional requirements from spec |
| 2 | **Allowed Files** | ☐ | Explicit list of files engine may create/modify |
| 3 | **Forbidden Files** | ☐ | Files engine MUST NOT touch |
| 4 | **Constraints** | ☐ | Standard constraint block (no dependency changes, follow conventions, etc.) |
| 5 | **Success Criteria** | ☐ | Acceptance criteria from spec |

### Optional Fields

| # | Field | When Required | Status |
|---|-------|---------------|--------|
| 6 | **Approach Directive** | Multi-variant / Self-Competition | ☐ |
| 7 | **Codebase Context** | gemini prompts | ☐ |
| 8 | **Scope Boundary** | COLLABORATE subtasks | ☐ |

### Pre-Flight Validation Rules

| Rule | Check | Fail Action |
|------|-------|-------------|
| Allowed files list is non-empty | `allowed_files.length > 0` | BLOCK — prompt has no target |
| Forbidden files includes defaults | `package.json`, `.env*`, `*.config.*` present | WARN — add defaults if missing |
| Spec is non-trivial | Specification section > 20 characters | BLOCK — spec too vague |
| Success criteria exist | At least 1 criterion listed | BLOCK — no way to verify output |
| No overlap with other variants | `allowed_files` does not overlap other prompts (COLLABORATE) | BLOCK — scope collision |

### Common Mistakes

| Mistake | Consequence | Prevention |
|---------|-------------|------------|
| Omitting `Forbidden Files` | Engine modifies package.json, config, or unrelated code | Always include default forbidden list |
| Vague specification | Engine guesses intent, produces unrelated code | Require specific functional requirements |
| Missing `Allowed Files` | Engine creates files in unexpected locations | Always derive allowed files from spec + Glob/Grep |
| Copy-pasting without updating | Wrong file paths or stale spec from previous session | Re-derive scope for each new session |
| Forgetting Approach Directive | Self-Competition variants are too similar | Add distinct approach hints for each variant |

---

## Cost Tracking

Arena tracks costs via provider dashboards. In-session tracking is approximate:

### Estimation Approach

| Engine | Cost Factor | Tracking Method |
|--------|------------|-----------------|
| codex | Per-token via OpenAI API | Check OpenAI dashboard or API usage page |
| gemini | Per-token via Google AI | Check Google AI Studio usage |

### Pre-Execution Cost Estimate

Before executing, Arena should display a cost summary to the user:

```
Arena Cost Estimate
───────────────────
Mode:       {Solo / Team / Quick}
Variants:   {N}
Engines:    {engine list}
Est. Scale: {small / medium / large}
            - small: 2 variants, short prompts, simple task
            - medium: 2-3 variants, moderate prompts
            - large: 4+ variants or Team Mode

Confirmation required: {Yes (≥3 variants or Team Mode) / No}
```

**Auto-confirmation triggers:**
- 3+ variants → show estimate and require confirmation
- Team Mode → show estimate and require confirmation
- Quick Mode or 2-variant Solo Mode → show estimate, no confirmation needed

### In-Session Tracking

Track cost qualitatively in the session summary:
- Number of engine invocations per variant
- Approximate prompt size (small / medium / large)
- Refer users to provider dashboards for exact costs

---

## Engine-Specific Prompt Strategies

While both engines use the same structured prompt template, their strengths differ. Optimize prompts based on engine characteristics.

### codex Optimization

codex excels with focused, directive prompts:

| Principle | Guidance |
|-----------|----------|
| **Be concise** | Keep specification tight — codex performs well with clear, short instructions |
| **Lead with constraints** | Place "Allowed Files" and "Forbidden" sections early in the prompt |
| **Specify file paths explicitly** | codex is most accurate when exact file paths are given |
| **Prefer imperative language** | "Create function X that does Y" over "Consider implementing..." |
| **Minimize background context** | Skip business rationale — focus on technical requirements |

**codex prompt structure priority:**
1. Constraints and scope (most important — place first)
2. Specification (functional requirements)
3. Success criteria
4. Minimal context (only if needed)

### gemini Optimization

gemini benefits from richer context and exploratory prompts:

| Principle | Guidance |
|-----------|----------|
| **Provide business context** | Explain WHY the feature exists — gemini uses context for better design decisions |
| **Include related files** | List reference files (read-only) so gemini understands the broader architecture |
| **Describe patterns** | Explain existing code patterns — gemini adapts well to established conventions |
| **Encourage alternatives** | "Consider multiple approaches before implementing" can yield creative solutions |
| **Use the Codebase Context section** | Fill in tech_stack, patterns_summary, and reference_files thoroughly |

**gemini prompt structure priority:**
1. Business context and rationale (why this change)
2. Specification (functional requirements)
3. Codebase context (tech stack, patterns, related files)
4. Constraints and scope
5. Success criteria

### Cross-Engine Prompt Adjustment Example

For the same specification, adapt the prompt:

**codex version (compact, directive):**
```
Implement JWT authentication.
## Allowed Files: src/auth/jwt.ts, src/auth/jwt.test.ts
## Forbidden: package.json, tsconfig.json, .env*
## Constraints: [standard constraints]
## Spec: Create verifyToken(token: string): Promise<UserPayload>. Use jsonwebtoken library (already installed). Throw AuthError on invalid/expired tokens. Add unit tests.
## Success Criteria: Tests pass. Function handles expired, malformed, and valid tokens.
```

**gemini version (contextual, exploratory):**
```
Implement JWT authentication for our Express API.
## Codebase Context
- Stack: Express + TypeScript + jsonwebtoken
- Auth pattern: Middleware-based, see src/middleware/auth.ts for current session approach
- Error handling: Custom AppError class in src/errors/
## Spec: Create verifyToken(token: string): Promise<UserPayload>. Should integrate with existing error handling patterns. Consider both sync and async verification approaches.
## Allowed Files: src/auth/jwt.ts, src/auth/jwt.test.ts
## Forbidden: package.json, tsconfig.json, .env*
## Constraints: [standard constraints]
## Success Criteria: Tests pass. Function handles expired, malformed, and valid tokens.
```

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `codex: command not found` | Install: `npm install -g @openai/codex` |
| `gemini: command not found` | Install: `npm install -g @google/gemini-cli` or check Google AI docs |
| Engine hangs / no output | Check API key validity; try with smaller prompt |
| Branch conflict on checkout | `git stash` first, or commit current changes |
| Variant branch already exists | `git branch -D arena/variant-{engine}` then recreate |
| Engine produces no changes | Review prompt specificity; ensure target files are mentioned |
| `.git/index.lock` contention (Team Mode) | Use `git worktree` — each subagent needs its own worktree directory |
| `git worktree add` fails | Ensure the branch already exists: `git branch arena/variant-{engine} $BASE_COMMIT` first |
| `git branch -D` fails (branch in use) | Remove the worktree first: `git worktree remove /tmp/$SESSION_ID/variant-{engine}` |
| Worktree directory not found | Verify `/tmp/$SESSION_ID` exists; Arena leader must create worktrees before spawning subagents |
