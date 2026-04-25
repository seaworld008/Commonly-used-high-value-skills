# Session Analysis Methods

Methods and best practices for session replay analysis.

---

## Analysis Types

### 1. Flow Analysis

Analyze a specific user flow (e.g., checkout).

```yaml
FLOW_ANALYSIS:
  scope: "Specific user journey"
  questions:
    - Where do users drop off?
    - What paths do users actually take?
    - How does expected flow differ from actual?

  metrics:
    - completion_rate: "% who finish the flow"
    - drop_off_points: "Where users leave"
    - path_diversity: "How many unique paths exist"
    - time_to_complete: "Duration statistics"
```

### 2. Segment Comparison

Compare behavior across different user segments.

```yaml
SEGMENT_COMPARISON:
  scope: "Compare behavior across groups"
  dimensions:
    - device: [mobile, desktop, tablet]
    - user_type: [new, returning, power_user]
    - persona: [Researcher-defined personas]
    - source: [organic, paid, direct, referral]

  metrics:
    - behavior_patterns: "How groups differ"
    - success_rates: "Completion by segment"
    - friction_points: "Segment-specific problems"
```

### 3. Problem Investigation

Deep-dive analysis into known problem areas.

```yaml
PROBLEM_INVESTIGATION:
  scope: "Deep-dive into known issues"
  triggers:
    - metric_drop: "Conversion decreased"
    - user_complaint: "Feedback about specific area"
    - echo_prediction: "Simulated friction point"

  approach:
    1. Isolate affected sessions
    2. Identify common patterns
    3. Find root cause
    4. Quantify impact
```

### 4. Anomaly Detection

Detect unusual behavior patterns.

```yaml
ANOMALY_DETECTION:
  scope: "Identify unusual behavior"
  types:
    - positive: "Unexpectedly successful sessions"
    - negative: "Unusually high frustration"
    - neutral: "New behavior patterns emerging"

  methods:
    - statistical: "Deviation from baseline"
    - pattern: "Unusual sequence detection"
    - temporal: "Time-based anomalies"
```

---

## Analysis Workflow

```
1. SCOPE DEFINITION
   ├── What flow/area?
   ├── What time period?
   ├── Which user segments?
   └── What questions to answer?

2. DATA COLLECTION
   ├── Pull relevant sessions
   ├── Apply filters
   ├── Check data quality
   └── Note limitations

3. PATTERN EXTRACTION
   ├── Identify common paths
   ├── Calculate frustration signals
   ├── Find drop-off points
   └── Detect anomalies

4. EVIDENCE GATHERING
   ├── Find representative sessions
   ├── Document specific examples
   ├── Quantify findings
   └── Cross-validate

5. SYNTHESIS
   ├── Formulate hypotheses
   ├── Prioritize issues
   ├── Recommend actions
   └── Prepare handoffs
```

---

## Data Sources

### Session Replay Platforms

| Platform | Strengths | Considerations |
|----------|-----------|----------------|
| **Hotjar** | Heatmaps, recordings, surveys | Free tier limited |
| **FullStory** | Advanced search, DX integration | Enterprise pricing |
| **LogRocket** | Redux integration, error tracking | Developer-focused |
| **Smartlook** | Mobile app support | Good for apps |
| **Mouseflow** | Form analytics | Form-focused |

### Data Points to Collect

```yaml
SESSION_DATA:
  identification:
    - session_id: "Anonymized unique ID"
    - user_segment: "Persona/cohort assignment"
    - device_info: "Type, OS, browser"

  behavior:
    - page_views: "Sequence of pages visited"
    - clicks: "Element, timestamp, position"
    - scrolls: "Depth, velocity, direction"
    - forms: "Field interactions, errors"
    - timing: "Time on page, between actions"

  context:
    - entry_point: "Where they came from"
    - exit_point: "Where they left"
    - errors: "JavaScript errors, API failures"
```

---

## Statistical Considerations

### Sample Size Guidelines

| Analysis Type | Minimum Sessions | Recommended |
|---------------|------------------|-------------|
| Flow completion | 100 | 500+ |
| Segment comparison | 50 per segment | 200+ per segment |
| Anomaly detection | 1000 baseline | 5000+ |
| Problem investigation | 30 affected | 100+ |

### Confidence Levels

```yaml
CONFIDENCE_THRESHOLDS:
  high_confidence:
    sample_size: ">500 sessions"
    pattern_frequency: ">30% of sessions"
    statistical_significance: "p < 0.05"

  medium_confidence:
    sample_size: "100-500 sessions"
    pattern_frequency: "15-30% of sessions"
    note: "Directionally useful, verify with more data"

  low_confidence:
    sample_size: "<100 sessions"
    pattern_frequency: "<15% of sessions"
    note: "Hypothesis only, needs validation"
```

---

## Privacy Best Practices

### Must Do

- Anonymize all session identifiers
- Mask PII in replays (emails, names, addresses)
- Respect user consent preferences
- Apply data retention limits
- Aggregate before sharing

### Never Do

- Store raw PII in analysis outputs
- Share individual session recordings externally
- Analyze without proper consent
- Keep data longer than policy allows
- Identify specific individuals

### Anonymization Template

```yaml
SESSION_REFERENCE:
  # Instead of user ID
  reference: "Session #A7B3C (Mobile, New User, US)"

  # Instead of exact timestamps
  timing: "Morning session, 12 minutes total"

  # Instead of specific location
  context: "Entered from product page, exited at payment"
```

---

## Common Analysis Patterns

### Pattern 1: Funnel Drop-off

```yaml
FUNNEL_ANALYSIS:
  flow: [Landing → Product → Cart → Checkout → Payment → Confirmation]

  findings:
    step: "Cart → Checkout"
    drop_rate: "45%"
    frustration_signals:
      - rage_clicks_on_checkout_button: "12%"
      - back_to_cart: "28%"

  hypothesis: "Checkout button visibility issue"
  evidence: "67% of rage clicks on mobile devices"
```

### Pattern 2: Loop Detection

```yaml
LOOP_ANALYSIS:
  definition: "User returns to same page 2+ times within 60s"

  findings:
    location: "Search results page"
    loop_rate: "23% of sessions"
    common_sequence: "Results → Product → Results → Product → Exit"

  hypothesis: "Search results don't match expectations"
  evidence: "Users view average 4.2 products before leaving"
```

### Pattern 3: Dead End Detection

```yaml
DEAD_END_ANALYSIS:
  definition: "High exit rate from non-terminal page"

  findings:
    location: "FAQ page"
    exit_rate: "78%"
    preceding_action: "Help link click"

  hypothesis: "FAQ doesn't answer user questions"
  evidence: "82% scroll to bottom, 45% use search on FAQ page"
```
