# Format & Audience Matching Anti-Patterns

Purpose: Choose the right NotebookLM format for the audience, avoid duration mismatches, and design a coherent multi-format funnel.

## Contents

- Format anti-patterns `FA-01..FA-07`
- Multi-format anti-patterns `MF-01..MF-04`
- Audience-fit tables
- Strategy and funnel rules

## Format Anti-Patterns

| ID | Anti-pattern | Symptom | Fix |
|----|--------------|---------|-----|
| `FA-01` | Format Fixation | Audio is used even when visuals are required | Choose from purpose -> audience -> format |
| `FA-02` | Audience-Format Mismatch | The audience says it is too long, too shallow, or too technical | Use the audience-fit matrix |
| `FA-03` | Purpose Blindness | The chosen format does not support the actual decision or delivery need | Define the job-to-be-done first |
| `FA-04` | One-Size-Fits-All Tone | The tone feels off for the audience | Calibrate tone to audience type |
| `FA-05` | Duration Disconnect | Attention span and runtime conflict | Use explicit duration defaults |
| `FA-06` | Multi-Format Incoherence | Different formats say different things | Define the core message first |
| `FA-07` | Accessibility Ignorance | The format does not fit the context of use | Check whether the audience will read, watch, or listen |

## Multi-Format Anti-Patterns

| ID | Anti-pattern | Symptom | Fix |
|----|--------------|---------|-----|
| `MF-01` | Sequential Duplicate | Video becomes a weak copy of audio | Re-optimize per format |
| `MF-02` | Key Message Drift | The message changes across formats | Lock `3` core messages first |
| `MF-03` | Flat Adaptation | Brief is too long and Deep Dive too shallow | Adjust depth per format family |
| `MF-04` | Missing Funnel Design | Formats feel isolated | Design `Teaser -> Brief -> Deep Dive` when appropriate |

## Audience-Fit Tables

### Audio

| Audience | Preferred style | Preferred duration | Avoid by default |
|----------|-----------------|--------------------|------------------|
| `C-suite` | `Brief: Executive Summary` | `5-8 min` | `Deep Dive` |
| `PM` | `Brief` or `Deep Dive` | `8-15 min` | `Lecture Mode` |
| `Senior Engineer` | `Deep Dive: Technical` | `15-20 min` | `Brief` |
| `Junior Dev` | `Lecture: Tutorial` | `20-25 min` | `Critique` |
| `Researcher` | `Critique: Research` | `12-18 min` | `Brief` |
| `General Public` | `Deep Dive: General` | `15-18 min` | `Technical Deep Dive` |
| `Student` | `Lecture: Tutorial` | `20-25 min` | `Executive Brief` |
| `Sales` | `Brief: Social Share` | `3-8 min` | `Academic Lecture` |

### Video

| Audience | Preferred style | Preferred duration | Avoid by default |
|----------|-----------------|--------------------|------------------|
| `Engineers` | `Explainer: Whiteboard` | `3-5 min` | `Cinematic` |
| `Executives` | `Explainer: Corporate` | `2-3 min` | `Academic` |
| `Social followers` | `Brief: Casual` | `30-90 sec` | `Whiteboard` |
| `Students` | `Explainer: Classroom` | `5-10 min` | `Corporate` |

### Slides

| Use case | Preferred format | Slide count |
|----------|------------------|-------------|
| Conference talk | `Presenter: TED-style` | `10-15` |
| Internal presentation | `Presenter: Internal` | `10-20` |
| Handout | `Detailed: Handout` | `15-30` |
| Educational deck | `Detailed: Educational` | `20-30` |

## Strategy Rules

- Start with purpose, not with a favorite format.
- Challenge audio-only defaults when the content is visual, comparative, or data-heavy.
- Challenge a `30 min` Deep Dive for executives unless there is explicit need.
- Use a funnel when multiple formats serve one campaign:
  - `Teaser`
  - `Brief`
  - `Deep Dive`
