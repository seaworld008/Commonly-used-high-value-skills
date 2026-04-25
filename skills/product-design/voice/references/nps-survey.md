# Voice NPS Survey Design

Purpose: Use this file when the task is loyalty measurement, NPS implementation, follow-up design, or NPS interpretation.

Contents:
- Core NPS question and score bands
- Follow-up prompts by respondent type
- Formula and benchmark ranges
- Minimal implementation contract
- Analysis checklist

## Core Survey

```markdown
## NPS Survey

### Core Question
"How likely are you to recommend [product name] to a friend or colleague?"

| Score | Segment |
|-------|---------|
| 0-6 | Detractors |
| 7-8 | Passives |
| 9-10 | Promoters |
```

## Follow-up Prompts

| Segment | Prompt |
|---------|--------|
| `Promoters (9-10)` | "What do you value most?" |
| `Passives (7-8)` | "What would make this a 10?" |
| `Detractors (0-6)` | "What did not meet your expectations?" |

## Formula and Benchmarks

```text
NPS = % Promoters - % Detractors
```

| NPS Range | Interpretation |
|-----------|----------------|
| `70+` | World-class |
| `50-69` | Excellent |
| `30-49` | Good |
| `0-29` | Needs improvement |
| `Below 0` | Critical |

## Implementation Rules

- Ask only after the user has experienced meaningful value.
- Keep the score mandatory and the open-text follow-up optional but visible.
- Store `score`, `feedback`, `userId`, `segment`, `touchpoint`, and `timestamp`.
- Track the derived category: `promoter`, `passive`, or `detractor`.
- Separate product outreach consent from the survey response if follow-up is planned.

## Minimal Data Contract

```typescript
interface NPSResponse {
  score: number;
  feedback?: string;
  userId: string;
  segment?: string;
  touchpoint?: string;
  timestamp: string;
}

trackEvent('nps_submitted', {
  score,
  category: score >= 9 ? 'promoter' : score >= 7 ? 'passive' : 'detractor',
  has_feedback: Boolean(feedback)
});
```

## Analysis Checklist

- Report overall NPS and response volume.
- Break down NPS by plan, segment, tenure, and touchpoint.
- Extract promoter strengths, passive upgrade opportunities, and detractor pain points.
- Flag statistically weak samples before recommending broad product changes.
- Route recurrent feature requests to `Spark`, churn-risk themes to `Retain`, and metric instrumentation gaps to `Pulse`.
