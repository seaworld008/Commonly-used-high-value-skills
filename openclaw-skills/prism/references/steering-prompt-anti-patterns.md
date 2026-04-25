# Steering Prompt Anti-Patterns

Purpose: Detect steering prompt failures quickly, prevent NotebookLM field misuse, and keep iteration disciplined.

## Contents

- Steering anti-patterns `SP-01..SP-07`
- NotebookLM-specific anti-patterns `NB-01..NB-05`
- Quality gates
- Iteration rules

## Steering Anti-Patterns

| ID | Anti-pattern | Symptom | Fix |
|----|--------------|---------|-----|
| `SP-01` | Vague Steering | Generic, unfocused output | Specify audience, focus, tone, and duration |
| `SP-02` | Prompt Bloat | Reasoning degrades near `3,000` tokens | Keep prompt to `150 words` and `8` instructions or fewer |
| `SP-03` | Multi-Task Overload | The output is mediocre at everything | Keep `1 prompt = 1 purpose` |
| `SP-04` | Audience Omission | Wrong difficulty or tone | Use `Audience Anchor` at the start |
| `SP-05` | Positive-Only Framing | Output includes filler and drift | Add explicit `Skip:` instructions |
| `SP-06` | Contradictory Instructions | Unstable or partially ignored instructions | Remove conflicts and set priorities clearly |
| `SP-07` | Customization Box Confusion | Steering has little or no effect | Put Audio/Video steering in NotebookLM's Customize field, not the chat box |

## NotebookLM-Specific Anti-Patterns

| ID | Anti-pattern | Symptom | Fix |
|----|--------------|---------|-----|
| `NB-01` | Generic Summarization | Output only paraphrases the source | Ask for analysis, contrast, critique, or synthesis |
| `NB-02` | Citation Neglect | Unsupported claims slip in | Ask for source-grounded claims and explicit attribution |
| `NB-03` | Passive Extraction | Conflicts between sources are ignored | Ask for contradictions and gaps explicitly |
| `NB-04` | Monolingual Assumption | Output language drifts unexpectedly | Explicitly state output language if multilingual sources exist |
| `NB-05` | Feature Misuse | Wrong expectation for Audio, Video, or chat | Match the task to the correct NotebookLM feature |

## Quality Gates

| Gate | Action |
|------|--------|
| Prompt `> 150 words` | Trim aggressively |
| Instructions `> 8` | Reduce to essentials |
| More than one purpose | Split the task |
| Tone is not explicit | Add a concrete tone description |
| No `Skip:` list | Add negative space |
| `3` failed rounds | Review source quality, not only the prompt |

## Iteration Discipline

- Change one variable per round.
- Save the previous version before regenerating.
- Stop at `>= 4.0` or after `3 rounds`.
- If the source is weak, improve the source before writing a fourth prompt.
