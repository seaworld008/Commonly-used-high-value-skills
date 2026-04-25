# Prompt Catalog

Purpose: Select the right NotebookLM prompt family, duration, and style, then produce a concise steering prompt that fits the audience and source.

## Contents

- Core prompt rules
- Format selection matrix
- Canonical prompt skeletons
- Duration calibration
- Source-prep meta prompts

## Core Prompt Rules

- Keep steering prompts at `150 words` or less.
- Keep instructions to `8` or fewer.
- Use the three-layer structure:
  - `Audience`
  - `Focus`
  - `Tone`
- Prefer `2-3` high-value patterns instead of stacking every pattern.
- State what to skip, not only what to include.

### Pattern Library

| Pattern | Use it when... | Default effect |
|---------|----------------|----------------|
| `Audience Anchor` | Audience level or decision context matters most | Improves fit and relevance |
| `Negative Space` | The source is broad or noisy | Reduces repetition and drift |
| `Focus Laser` | The task must go deep on `1-2` topics | Raises depth and clarity |
| `Tone Dial` | Brand voice or audience tone matters | Improves engagement |
| `Duration Target` | Time or slide count must stay tight | Improves pacing |
| `Structural Blueprint` | The format needs explicit sequencing | Improves flow and completeness |

## Format Selection Matrix

| Family | Best for | Default duration / size | Use this when... |
|--------|----------|-------------------------|------------------|
| `Audio Deep Dive` | Deep understanding, technical or strategic learning | `15-30 min` | Audience wants depth and can stay engaged |
| `Audio Brief` | Executive summary, sharing, short updates | `3-10 min` | Time is scarce and actionability matters |
| `Audio Critique` | Research review, product evaluation | `10-20 min` | Sources contain claims, trade-offs, or evidence to assess |
| `Audio Debate` | Multi-perspective comparison | `15-25 min` | Sources intentionally conflict or compare viewpoints |
| `Audio Lecture` | Teaching, tutorials, onboarding | `15-30 min` | Audience needs stepwise learning |
| `Video Explainer` | Concept explanation with visuals | `2-10 min` | Visual reinforcement matters |
| `Video Brief` | Teasers, short shareable summaries | `30-90 sec` to `2-3 min` | Awareness and quick distribution matter |
| `Presenter Slides` | Live presentation | `10-20 slides` | A speaker will talk over the deck |
| `Detailed Deck` | Handout or self-serve reading | `15-30 slides` | The deck must stand alone |
| `Infographic` | Visual summary | 60-second scan target | Data must be understood quickly |
| `Mind Map` | Topic structure and hierarchy | depth depends on topic | The main value is organization, not narrative |
| `Deep Research` | Full investigation | scope-driven | Source quality is strong and the task requires depth |

## Audience-Fit Defaults

| Audience | Preferred audio | Preferred video | Preferred slides |
|----------|-----------------|-----------------|------------------|
| `C-suite` | `Brief: Executive Summary` | `Explainer: Corporate` | `Presenter: Internal` |
| `PM` | `Brief` or `Deep Dive` | `Explainer: Corporate` | `Presenter: Internal` |
| `Senior Engineer` | `Deep Dive: Technical` | `Explainer: Whiteboard` | `Detailed: Handout` |
| `Junior Dev` | `Lecture: Tutorial` | `Explainer: Classroom` | `Detailed: Educational` |
| `Researcher` | `Critique: Research` | `Explainer: Academic` | `Detailed: Handout` |
| `General Public` | `Deep Dive: General` | `Brief: Casual` | `Presenter: TED-style` |
| `Student` | `Lecture: Tutorial` | `Explainer: Classroom` | `Detailed: Educational` |
| `Sales` | `Brief: Social Share` | `Brief: Casual` | `Presenter: Internal` |

## Video Style Matrix

| Style | Best for | Avoid when... |
|-------|----------|---------------|
| `Whiteboard` | Engineering and systems explanation | You need a polished executive feel |
| `Classroom` | Teaching and tutorials | You need a short teaser |
| `Abstract` | High-level conceptual framing | Precision and operational detail matter |
| `Corporate` | Executive or internal business updates | The audience expects casual or playful tone |
| `Casual` | Social or lightweight summaries | Brand voice must stay formal |
| `Cinematic` | Emotional storytelling | Dense technical content dominates |
| `Academic` | Research-heavy explanation | Speed and brevity are the main goal |
| `News` | Timely summaries and updates | The content is evergreen and reflective |

## Canonical Prompt Skeletons

Use these as baseline templates. Replace bracketed values and keep the final prompt concise.

### Audio Deep Dive

```text
Target audience: [audience and knowledge level].
Focus heavily on: [1-2 topics].
Tone: [tone].
Duration: aim for [duration].
Discuss: [required themes].
Skip: [what not to cover].
Use concrete comparisons or examples where helpful.
```

### Audio Brief

```text
Target audience: [busy audience].
Open with the single most important insight.
Cover the top [3-5] points only.
Tone: [tone], concise and direct.
Duration: [duration].
Skip: background, caveats, or implementation detail unless critical.
End with: what this means and what to do next.
```

### Audio Critique

```text
Target audience: [audience].
Analyze the source critically.
Evaluate strengths, weaknesses, assumptions, and missing evidence.
Tone: [tone], evidence-first.
Duration: [duration].
Skip: generic praise or unsupported claims.
End with a verdict and next questions.
```

### Audio Debate

```text
Target audience: [audience].
Present the strongest arguments on each side of [question].
Keep both sides balanced before reaching a synthesis.
Tone: [tone].
Duration: [duration].
Skip: false certainty.
End with the conditions under which each side is more persuasive.
```

### Audio Lecture

```text
Target audience: [beginners / learners].
Assume: [knowledge level].
Teach the topic in a step-by-step way.
Tone: patient, encouraging, and clear.
Duration: [duration].
Use concrete examples and simple analogies.
Skip: unexplained jargon.
```

### Video Explainer

```text
Target audience: [audience].
Format: Video Explainer in [visual style].
Focus on: [core topic].
Tone: [tone].
Duration: [duration].
Use visuals to reinforce the key concepts, not decorate them.
Keep on-screen text minimal and readable.
Skip: points that cannot be shown or explained clearly on screen.
```

### Video Brief

```text
Target audience: [audience].
Format: Video Brief in [visual style].
Hook the viewer immediately with the strongest insight.
Tone: [tone].
Duration: [duration].
Cover only the most shareable or decision-relevant points.
End with a clear takeaway or CTA.
```

### Presenter Slides

```text
Target audience: [audience].
Create Presenter Slides for a live talk.
Keep each slide to one message.
Use [style] tone and pacing.
Target length: [slide count].
Minimize slide text and maximize clarity.
Skip detail that belongs in speaker notes, not on the slide.
```

### Detailed Deck

```text
Target audience: [audience].
Create a Detailed Deck that can be read without a presenter.
Include: context, evidence, structure, and conclusions.
Tone: [tone].
Target length: [slide count].
Use clear sections and self-contained explanations.
Skip decorative slides that add no understanding.
```

### Deep Research

```text
Target audience: [audience].
Produce a Deep Research output on [topic].
Prioritize: evidence quality, synthesis, trade-offs, and open questions.
Tone: [tone].
Scope: [specific scope].
Skip: unsupported extrapolation and off-topic context.
End with actionable recommendations and unresolved questions.
```

## Duration Calibration

| Goal | Audio | Video | Slides |
|------|-------|-------|--------|
| Overview / teaser | `3-5 min` | `30-90 sec` | `5-8` |
| Standard summary | `8-12 min` | `2-3 min` | `10-15` |
| Deep exploration | `15-25 min` | `5-10 min` | `20-30` |
| Comprehensive | `25-30 min` | `10-15 min` | `30+` |

## Source-Prep Meta Prompts

Use these when the user is not ready for a final steering prompt.

### Source Quality Check

```text
Review the source set for quality, focus, and gaps.
Identify weak or redundant sources, note if the set is too broad, and recommend the best notebook composition pattern.
```

### Format Selection Check

```text
Recommend the best NotebookLM output format for this audience, purpose, and source set.
Compare the top two options and explain what would be lost with the weaker choice.
```

### Iteration Setup

```text
Assess the current steering prompt.
Keep what is working, change only one variable, and suggest the next A/B test.
```
