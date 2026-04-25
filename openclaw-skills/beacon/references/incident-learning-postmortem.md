# Incident Learning & Postmortem

> Blameless postmortem culture, incident learning patterns, templates, organizational metrics

## 1. Blameless Postmortem: 5 Principles

| # | Principle | Description | Practice |
|---|-----------|-------------|----------|
| **BL-01** | **Assume good faith** | All participants acted on the best information available and made the best decision they could | Focus on system flaws, not individuals |
| **BL-02** | **Ask What/How, not Why** | Analyze "what happened" and "how it happened" | Avoid "why did you do that?" — it forces defensiveness |
| **BL-03** | **Forward-built timeline** | Construct timeline from before the incident forward | Prevents hindsight bias (don't reason backward from outcome) |
| **BL-04** | **Systems thinking** | Analyze system interactions, not individual mistakes | Examine tools, processes, communication, organizational structure |
| **BL-05** | **Accountability ≠ Punishment** | Assign ownership for fixes, but do not assign fault | "Eliminate blame, establish ownership" |

---

## 2. Cognitive Bias Countermeasures

| Bias | Description | Countermeasure |
|------|-------------|----------------|
| **Fundamental attribution error** | Attributing actions to character rather than circumstances | Focus analysis on situational factors |
| **Confirmation bias** | Attending only to information that supports existing beliefs | Appoint Devil's Advocate, include external team members |
| **Hindsight bias** | Perceiving events as "predictable" after the fact | Forward-built timeline (BL-03) |
| **Negativity bias** | Disproportionate focus on negative events | Explicitly document what went well |

---

## 3. Postmortem Template

```
Required sections:
  1. Incident Metadata
     - Date/time, duration, severity, participants, publication date

  2. Executive Summary
     - Impact (quantitative: QPS drop rate, latency increase, affected users, revenue impact)
     - Root cause (1-2 sentences)
     - Trigger (direct cause)

  3. Detailed Timeline
     - Minute-by-minute chronology (detection → response → recovery)
     - Decision-making context for each action

  4. Root Cause Analysis
     - Focus on system defects (not human error)
     - 5 Whys or fishbone diagram
     - List of contributing factors

  5. Lessons Learned
     - What went well (mandatory)
     - What went poorly
     - Where we got lucky

  6. Action Items
     - Single owner per item (multiple owners prohibited)
     - Priority (P0/P1/P2)
     - Tracking ticket link
     - Type: Prevention / Mitigation / Detection / Repair
     - Measurable success criteria

  7. Glossary (for readers outside the domain)

  8. Appendix (graphs, log excerpts, supporting data)
```

---

## 4. Postmortem Anti-Patterns

| # | Anti-Pattern | Problem | Countermeasure |
|---|-------------|---------|----------------|
| **PA-01** | **Blaming language** | Destroys psychological safety → reporting avoidance | Reviewer checks language before publication |
| **PA-02** | **Vague action items** | "Improve it" / "Be more careful" → unactionable | SMART criteria (specific, measurable, time-bound) |
| **PA-03** | **Multiple owners** | Diffusion of responsibility → nobody acts | Single POC (Point of Contact) per item |
| **PA-04** | **Delayed publication** | Information freshness degrades, learning opportunity lost | Mandate publication within 7 days |
| **PA-05** | **Behavioral fixes only** | "Be more careful next time" → recurrence | Prioritize systemic fixes (automation, guardrails) |
| **PA-06** | **Closed postmortems** | Shared only within team → no organizational learning | Default to company-wide publication, hold reading sessions |
| **PA-07** | **Unclosed action items** | Action items abandoned | Track closure rate, hold FixIt Weeks |

---

## 5. Incident Learning Metrics

```
Postmortem quality indicators:
  - Time to publication (target: < 7 days)
  - Action item specificity score
  - Prevention vs Mitigation action ratio
  - Reader reach (team-only / cross-organization)
  - Data completeness (quantitative impact, timeline detail)

Organizational health metrics:
  - Action item closure rate (target: > 80%)
  - Average time to closure
  - Similar incident recurrence rate
  - MTTD (Mean Time to Detect) trend
  - MTTR (Mean Time to Resolve) trend

Culture indicators:
  - Voluntary participation rate in postmortem reviews
  - Language blamelessness (checked during review)
  - Leadership consistency in blameless behavior
  - On-call team attrition rate
  - Psychological safety survey score

Knowledge sharing practices:
  - Weekly/monthly outage report distribution
  - Postmortem reading sessions (cross-team)
  - "Wheel of Misfortune" (past incident training exercises)
  - "Greatest Hits" annual compilation
  - Presentations by incident responders
```

---

## 6. Beacon Integration

```
Usage in Beacon:
  1. Post-incident monitoring improvement proposals (reduce detection time)
  2. Integration with SLO violation analysis (track budget consumption causes)
  3. Alert effectiveness validation (was it detected? was it timely?)
  4. Dashboard improvement proposals (visibility gaps during incidents)

Quality gates:
  - Postmortem includes quantitative impact data
  - Each action item has a single owner assigned
  - Systemic fixes are prioritized over behavioral fixes
  - Monitoring improvement items are included (Beacon integration point)
  - Published within 7 days
  - Closure rate exceeds 80% (quarterly check)
```

**Source:** [Google SRE: Postmortem Culture](https://sre.google/workbook/postmortem-culture/) · [PagerDuty: The Blameless Postmortem](https://postmortems.pagerduty.com/culture/blameless/) · [Atlassian: Blameless Postmortem](https://www.atlassian.com/incident-management/postmortem/blameless) · [Rootly: 2025 SRE Incident Management Best Practices](https://rootly.com/sre/2025-sre-incident-management-best-practices-checklist)
