# Source Preparation Guide

Purpose: Prepare NotebookLM sources so format choice and steering prompts are grounded in reliable, focused material.

## Contents

- Core source-quality rule
- Source type matrix
- Notebook composition patterns
- Source count and tier guidance
- Free vs Plus considerations
- Universal pre-upload checklist

## Core Rule

Source quality determines roughly `70%` of output quality. A strong steering prompt cannot rescue weak, noisy, inaccessible, or contradictory sources.

## Source Type Matrix

| Source type | Best use | Strengths | Watch-outs |
|-------------|----------|-----------|------------|
| `PDF` | Reports, papers, structured documentation | Stable structure, page references, charts | OCR issues, scanned PDFs, noisy headers/footers |
| `Google Docs` | Living docs and structured notes | Native heading structure, editable, clear hierarchy | `100+ pages` slows handling, comments/suggestions add noise |
| `Web URL` | Public articles and current explanations | Easy sharing, current information | Login/paywall, JS-heavy pages, navigation noise |
| `YouTube` | Talks, explainers, interviews | Audio + transcript signal | Best at `5-30 min`; long or noisy videos degrade extraction |
| `Audio files` | Interviews, podcasts, meeting recordings | Natural voice material | Noise, weak speaker separation, unclear transcript |
| `Pasted text` | Small curated excerpts, notes, outline-first sources | Maximum control over scope | Easy to lose structure if dumped as flat text |

## Source-Specific Rules

### PDF

- Prefer selectable text over image-only scans.
- OCR scanned PDFs before upload.
- Keep the table of contents if it helps structure.
- Remove irrelevant headers, footers, and repeated boilerplate when possible.

### Google Docs

- Use proper `H1/H2/H3` heading styles.
- Resolve or remove comments and suggestion-mode artifacts.
- Confirm view access before relying on the document.
- Split or trim docs that exceed `100+ pages`.

### Web URL

- Use public, static-content URLs whenever possible.
- Prefer article pages over home pages or landing pages.
- Replace paywalled or login-gated links.
- Assume SPA-heavy pages may be incomplete.

### YouTube

- Prefer videos with captions.
- Prefer clear speech and low background noise.
- Individual video URLs are better than playlist URLs.
- Avoid extremely long videos unless deep coverage is required.

### Audio Files

- Prefer clear speech, strong channel separation, and minimal noise.
- Add metadata or a short context note when the source lacks structure.
- Avoid relying on audio-only sources for visual-heavy outputs.

### Pasted Text

- Preserve headings and bullets.
- Put the most important summary near the top.
- Separate sections clearly.
- Avoid flat text dumps with no hierarchy.

## Notebook Composition Patterns

| Pattern | Best for | When to use |
|---------|----------|-------------|
| `Single Deep` | Deep Dive, Lecture, Deep Research | One topic needs depth, not breadth |
| `Multi-Perspective` | Debate, Critique | Contrasting views or tension is the point |
| `Hierarchical` | Lecture, Detailed Deck | The audience needs concept-by-concept buildup |
| `Comparative` | Infographic, Critique | Options, alternatives, or benchmarks must be contrasted |
| `Chronological` | Deep Dive, Presenter Slides | Sequence and narrative arc matter |

## Source Count Guidance

| Situation | Recommended count | Notes |
|-----------|-------------------|-------|
| Deep analysis | `1-3` | Best for focus and fidelity |
| High-quality focused notebook | `2-5` | Often the strongest default |
| Standard notebook | `5-15` | Good range for most cases |
| Overload warning | `20+` | Trim before proceeding |
| Notebook hard limit | `50` | System maximum |

## Format-Driven Preparation

| Output family | Source preparation emphasis |
|---------------|----------------------------|
| `Audio Overview` | Use focused, discussion-friendly sources; avoid overly broad sets |
| `Video Overview` | Prefer sources with visualizable concepts, data, and structure |
| `Presenter Slides` | Preserve headings, bullets, and the central storyline |
| `Detailed Deck` | Include enough context, evidence, and self-contained detail |
| `Infographic` | Favor numeric data, rankings, comparisons, and concise takeaways |
| `Mind Map` | Favor sources with clean hierarchy and named subtopics |
| `Deep Research` | Favor high-trust, high-depth sources and clear scope boundaries |

## Free vs Plus Guidance

Capabilities change frequently. Check current official NotebookLM documentation before making hard claims.

| Capability | Free | Plus | Guidance |
|------------|------|------|----------|
| Notebook count | Limited | More generous / advanced support | Ask before recommending Plus as a solution |
| Audio Overview | More limited | More feature-complete | Use Plus recommendations only when justified |
| Video Overview | More limited | More style and capability depth | Do not assume availability |
| Deep Research | More limited | More complete | Confirm user tier before leaning on it |
| Interactive / advanced generation features | More limited | More available | Frame as optional, not assumed |

## Universal Pre-Upload Checklist

- `Accessibility`: every source is accessible without login or paywall issues
- `Readability`: OCR, transcript, or structure quality is acceptable
- `Focus`: the set is not overloaded or redundant
- `Freshness`: time-sensitive topics use fresh enough sources
- `Language`: languages are unified, or multilingual intent is explicit
- `Role assignment`: each source has a reason to be in the notebook

## Quick Failure Diagnosis

| Symptom | Likely cause | First fix |
|---------|--------------|-----------|
| Output is shallow | Too many sources or weak sources | Trim to `2-5` strong sources |
| Output hallucinates facts | Sources are incomplete or prompt scope is too broad | Improve source quality and constrain scope |
| Output drifts off-topic | Flat or noisy source structure | Re-structure the source and add summary headings |
| Output misses important visuals or data | Information is trapped in images | Add text tables, captions, or extracted notes |
| Output mixes languages unexpectedly | Mixed-language source set | Unify source language or make multilingual output explicit |
