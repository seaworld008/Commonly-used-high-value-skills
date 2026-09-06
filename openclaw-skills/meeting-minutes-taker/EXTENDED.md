# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

#### Progressive Context Offloading (Use File System)

**Critical: Write each pass output to files, not conversation context.**

**Path Convention:** All intermediate files should be created in a **transcript-specific subdirectory** under `<output_dir>/intermediate/` to avoid conflicts between different transcripts being processed.

**CRITICAL: Use transcript-specific subdirectory structure:**
```
<output_dir>/intermediate/<transcript-name>/version1.md
<output_dir>/intermediate/<transcript-name>/version2.md
<output_dir>/intermediate/<transcript-name>/version3.md
```

Example: If final minutes will be `project-docs/meeting-minutes/2026-01-14-api-design.md`, then:
- Intermediate files: `project-docs/meeting-minutes/intermediate/2026-01-14-api-design/version1.md`
- This prevents conflicts when multiple transcripts are processed in the same session
- The `intermediate/` folder should be added to `.gitignore` (temporary working files)

```
// Create transcript-specific subdirectory first
mkdir: <output_dir>/intermediate/<transcript-name>/

// Launch all 3 subagents IN PARALLEL (must be single message with 3 Task tool calls)
Task 1 → Write to: <output_dir>/intermediate/<transcript-name>/version1.md (complete minutes)
Task 2 → Write to: <output_dir>/intermediate/<transcript-name>/version2.md (complete minutes)
Task 3 → Write to: <output_dir>/intermediate/<transcript-name>/version3.md (complete minutes)

Merge Phase:
  Read: <output_dir>/intermediate/<transcript-name>/version1.md
  Read: <output_dir>/intermediate/<transcript-name>/version2.md
  Read: <output_dir>/intermediate/<transcript-name>/version3.md
  → UNION merge, consolidate duplicates, INCLUDE ALL DIAGRAMS → Write to: draft_minutes.md

Final Review:
  Read: draft_minutes.md
  Read: original_transcript.md
  → Compare & add omissions → Write to: final_minutes.md
```

**Benefits of file-based context offloading:**
- Conversation context stays clean (avoids token overflow)
- Intermediate results persist (can be re-read if needed)
- Each pass starts with fresh context window
- Merge phase reads only what it needs
- **Human can inspect intermediate files for review** - Critical for understanding what each pass captured
- Supports very long transcripts that exceed context limits
- **Enables post-hoc debugging** - If final output is missing something, human can trace which pass missed it

**IMPORTANT: Always preserve intermediate versions in transcript-specific subdirectory:**
- `<output_dir>/intermediate/<transcript-name>/version1.md`, `version2.md`, `version3.md` - Each subagent output
- These files help human reviewers understand the merge process
- Do NOT delete intermediate files after merge
- Human may want to compare intermediate versions to understand coverage gaps
- **Add `intermediate/` to `.gitignore`** - These are temporary working files, not final deliverables
- **Transcript-specific subdirectory** prevents conflicts when processing multiple transcripts

<a id="section-2"></a>

#### Strategy B: Parallel Multi-Agent (Complete Minutes Each Agent) - PREFERRED

**MUST use the Task tool** to spawn multiple subagents with **isolated context**, each generating **complete minutes**:

**Implementation using Task tool:**
```
// Launch ALL 3 subagents in PARALLEL (single message, multiple Task tool calls)
Task(subagent_type="general-purpose", prompt="Generate complete meeting minutes from transcript...", run_in_background=false) → version1.md
Task(subagent_type="general-purpose", prompt="Generate complete meeting minutes from transcript...", run_in_background=false) → version2.md
Task(subagent_type="general-purpose", prompt="Generate complete meeting minutes from transcript...", run_in_background=false) → version3.md

// After all complete:
Main Agent: Read all versions → UNION merge, consolidate duplicates → draft_minutes.md
```

**CRITICAL: Subagent Prompt Must Include:**
1. Full path to transcript file
2. Full path to output file (version1.md, version2.md, version3.md in transcript-specific subdirectory)
3. Context files to load (project-specific context if provided, meeting_minutes_template.md)
4. Reference images/documents if provided by user
5. Output language requirement (match user's language preference, preserve technical terms in English)
6. Quote formatting requirement (see Quote Formatting Requirements section below)

**Why multiple complete passes work:**
- Each pass independently analyzes the SAME content
- Different context states catch different details (no single pass catches everything)
- Pass 1 might catch decision X but miss action item Y
- Pass 2 might catch action item Y but miss decision X
- UNION merge captures both X and Y

**Why isolated context matters:**
- Each pass/agent starts fresh without prior assumptions
- No cross-contamination between passes
- Different "perspectives" emerge naturally from context isolation

<a id="section-3"></a>

### Step 1.7: Transcript Quality Assessment (Optional)

Evaluate transcript quality to determine processing depth:

**Scoring Criteria (1-10 scale):**

| Factor | Score Impact |
|--------|-------------|
| **Content volume** | >10k chars: +2, 5-10k: +1, <2k: cap at 3 |
| **Filler word ratio** | <5%: +2, 5-10%: +1, >10%: -1 |
| **Speaker clarity** | Main speaker >80%: +1 (clear presenter) |
| **Technical depth** | High technical content: +1 |

**Quality Tiers:**

| Score | Tier | Processing Approach |
|-------|------|---------------------|
| ≥8 | **High** | Full structured minutes with all sections, diagrams, quotes |
| 5-7 | **Medium** | Standard minutes, focus on key decisions and action items |
| <5 | **Low** | Summary only - brief highlights, skip detailed transcription |

**Example assessment:**
```
📊 Transcript Quality Assessment:
- Content: 41,837 chars (+2)
- Filler ratio: 3.6% (+2)
- Main speaker: 99% (+1)
- Technical depth: High (+1)
→ Quality Score: 10/10 (High)
→ Recommended: Full structured minutes with diagrams
```

**User decision point**: If quality is Low (<5), ask user:
> "Transcript quality is low (碎片对话/噪音较多). Generate full minutes or summary only?"

<a id="section-4"></a>

## Core Workflow

Copy this checklist and track progress:

```
Meeting Minutes Progress:
- [ ] Step 0 (Optional): Pre-process transcript with transcript-fixer
- [ ] Step 1: Read and analyze transcript
- [ ] Step 1.5: Speaker identification (if transcript has "Speaker 1/2/3")
  - [ ] Analyze speaker features (word count, style, topic focus)
  - [ ] Match against context.md team directory (if provided)
  - [ ] Present speaker mapping to user for confirmation
- [ ] Step 1.6: Generate intelligent filename, confirm with user
- [ ] Step 1.7: Quality assessment (optional, affects processing depth)
- [ ] Step 2: Multi-turn generation (PARALLEL subagents with Task tool)
  - [ ] Create transcript-specific dir: <output_dir>/intermediate/<transcript-name>/
  - [ ] Launch 3 Task subagents IN PARALLEL (single message, 3 Task tool calls)
    - [ ] Subagent 1 → <output_dir>/intermediate/<transcript-name>/version1.md
    - [ ] Subagent 2 → <output_dir>/intermediate/<transcript-name>/version2.md
    - [ ] Subagent 3 → <output_dir>/intermediate/<transcript-name>/version3.md
  - [ ] Merge: UNION all versions, AGGRESSIVELY include ALL diagrams → draft_minutes.md
  - [ ] Final: Compare draft against transcript, add omissions
- [ ] Step 3: Self-review for completeness
- [ ] Step 4: Present draft to user for human review
- [ ] Step 5: Cross-AI comparison (if human provides external AI output)
- [ ] Step 6: Iterate on human feedback (expect multiple rounds)
- [ ] Step 7: Human approves final version

Note: <output_dir> = directory where final meeting minutes will be saved (e.g., project-docs/meeting-minutes/)
Note: <transcript-name> = name derived from transcript file (e.g., 2026-01-15-product-api-design)
```

<a id="section-5"></a>

#### Phase A: Feature Analysis (Pattern Recognition)

For each speaker, analyze:

| Feature | What to Look For |
|---------|-----------------|
| **Word count** | Total words spoken (high = senior/lead, low = observer) |
| **Segment count** | Number of times they speak (frequent = active participant) |
| **Avg segment length** | Average words per turn (long = presenter, short = responder) |
| **Filler ratio** | % of filler words (对/嗯/啊/就是/然后) - low = prepared speaker |
| **Speaking style** | Formal/informal, technical depth, decision authority |
| **Topic focus** | Areas they discuss most (backend, frontend, product, etc.) |
| **Interaction pattern** | Do others ask them questions? Do they assign tasks? |

**Example analysis output:**
```
Speaker Analysis:
┌──────────┬────────┬──────────┬─────────────┬─────────────┬────────────────────────┐
│ Speaker  │ Words  │ Segments │ Avg Length  │ Filler %    │ Role Guess             │
├──────────┼────────┼──────────┼─────────────┼─────────────┼────────────────────────┤
│ 发言人1  │ 41,736 │ 93       │ 449 chars   │ 3.6%        │ 主讲人 (99% of content)│
│ 发言人2  │ 101    │ 8        │ 13 chars    │ 4.0%        │ 对话者 (short responses)│
└──────────┴────────┴──────────┴─────────────┴─────────────┴────────────────────────┘

Inference rules:
- 占比 > 70% + 平均长度 > 100字 → 主讲人
- 平均长度 < 50字 → 对话者/响应者
- 语气词占比 < 5% → 正式/准备充分
- 语气词占比 > 10% → 非正式/即兴发言
```
