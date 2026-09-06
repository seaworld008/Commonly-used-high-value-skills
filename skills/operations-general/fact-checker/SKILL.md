---
name: fact-checker
description: 'Verify factual claims against current authoritative sources and apply requested corrections with citations; use for accuracy checks or outdated documentation.'
zh_description: "核实事实与时效性，并按请求修正文档及补充来源。"
version: "1.1.1"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["checker", "fact", "productivity"]'
created_at: "2026-03-04"
updated_at: "2026-09-06"
quality: 5
complexity: "intermediate"
---

# Fact Checker

Verify factual claims in documents and propose corrections backed by authoritative sources.

## When to use

Trigger when users request:
- "Fact-check this document"
- "Verify these AI model specifications"
- "Check if this information is still accurate"
- "Update outdated data in this file"
- "Validate the claims in this section"

## Workflow

Copy this checklist to track progress:

```
Fact-checking Progress:
- [ ] Step 1: Identify factual claims
- [ ] Step 2: Search authoritative sources
- [ ] Step 3: Compare claims against sources
- [ ] Step 4: Generate correction report
- [ ] Step 5: Apply corrections with user approval
```

### Step 1: Identify factual claims

Scan the document for verifiable statements:

**Target claim types:**
- Technical specifications (context windows, pricing, features)
- Version numbers and release dates
- Statistical data and metrics
- API capabilities and limitations
- Benchmark scores and performance data

**Skip subjective content:**
- Opinions and recommendations
- Explanatory prose
- Tutorial instructions
- Architectural discussions

### Step 2: Search authoritative sources

For each claim, search official sources:

**AI models:**
- Official announcement pages (anthropic.com/news, openai.com/index, blog.google)
- API documentation (platform.claude.com/docs, platform.openai.com/docs)
- Developer guides and release notes

**Technical libraries:**
- Official documentation sites
- GitHub repositories (releases, README)
- Package registries (npm, PyPI, crates.io)

**General claims:**
- Academic papers and research
- Government statistics
- Industry standards bodies

**Search strategy:**
- Use the exact claim subject + specification + provider
- Include current year for recent information
- Verify from multiple sources when possible

### Step 3: Compare claims against sources

Create a comparison table:

| Claim in Document | Source Information | Status | Authoritative Source |
|-------------------|-------------------|--------|---------------------|
| Product supports feature X in all plans | Current plan matrix limits X to enterprise | ❌ Incorrect scope | Official pricing/docs |
| Library Y 2.4 is the current stable release | Registry and release page list a newer stable version | ⚠️ Outdated | Official registry/release |

**Status codes:**
- ✅ Accurate - claim matches sources
- ❌ Incorrect - claim contradicts sources
- ⚠️ Outdated - claim was true but superseded
- ❓ Unverifiable - no authoritative source found

### Step 4: Generate correction report

Present findings in structured format:

```markdown
## Fact-Check Report

### Summary
- Total claims checked: X
- Accurate: Y
- Issues found: Z

### Issues Requiring Correction

#### Issue 1: Outdated Product Specification
**Location:** Line 77-80 in docs/file.md
**Current claim:** "<exact text from the document>"
**Correction:** "<claim supported by the current official source>"
**Source:** <direct official documentation URL>
**Rationale:** <what changed, including effective or release date>

#### Issue 2: Incorrect Scope or Unit
**Location:** Line 79 in docs/file.md
**Current claim:** "<exact text>"
**Correction:** "<correct value with unit and scope>"
**Source:** <direct primary-source URL>
**Rationale:** <explain whether the error was version, unit, geography, plan, or date>
```

### Step 5: Apply Requested Corrections

If the user requested corrections, apply supported edits and report their sources.
If the task is review-only, present the report without changing the document.
Ask about unresolved meaning or consequential scope changes, not routine edits
already authorized by the request.

**When applying corrections:**

```text
Apply an exact, anchored replacement only after re-reading the current file.
Preserve surrounding formatting and attach the source near the corrected claim.
```

**After corrections:**

1. Verify all edits were applied successfully
2. Note the correction summary (e.g., "Updated 4 claims in section 2.1")
3. Remind user to commit changes

## Search best practices

### Query construction

**Good queries** (specific, current):
- "<provider> <product> official plan limits <current year>"
- "<library> official release notes stable version"
- "<standards body> <metric> definition <effective year>"

**Poor queries** (vague, generic):
- "Claude context"
- "AI models"
- "Latest version"

### Source evaluation

**Prefer official sources:**
1. Product official pages (highest authority)
2. API documentation
3. Official blog announcements
4. GitHub releases (for open source)

**Use with caution:**
- Third-party aggregators (llm-stats.com, etc.) - verify against official sources
- Blog posts and articles - cross-reference claims
- Social media - only for announcements, verify elsewhere

**Avoid:**
- Outdated documentation
- Unofficial wikis without citations
- Speculation and rumors

### Handling ambiguity

When sources conflict:

1. Prioritize most recent official documentation
2. Note the discrepancy in the report
3. Present both sources to the user
4. Recommend contacting vendor if critical

When no source found:

1. Mark as ❓ Unverifiable
2. Suggest alternative phrasing: "According to [Source] as of [Date]..."
3. Recommend adding qualification: "approximately", "reported as"

## Special considerations

### Time-sensitive information

Always include temporal context:

**Good corrections:**
- "截至 2026 年 1 月" (As of January 2026)
- "Claude Sonnet 4.5 (released September 2025)"

**Poor corrections:**
- "Latest version" (becomes outdated)
- "Current model" (ambiguous timeframe)

### Numerical precision

Match precision to source:

**Source says:** "approximately 1 million tokens"
**Write:** "1M tokens (approximately)"

**Source says:** "200,000 token context window"
**Write:** "200K tokens" (exact)

### Citation format

Include citations in corrections:

```markdown
> **注**：产品规格和版本信息以链接的官方文档为准；核验日期：YYYY-MM-DD。
```

Link to sources when possible.

## Examples

### Example 1: Technical specification update

**User request:** "Fact-check the AI model context windows in section 2.1"

**Process:**
1. Extract each model name, limit, unit, plan, and date as a separate claim
2. Search each provider's current official model catalog and documentation
3. Record the exact source page and verification date
4. Generate report showing discrepancies
5. Apply corrections within the requested scope; keep review-only tasks read-only

### Example 2: Statistical data verification

**User request:** "Verify the benchmark scores in chapter 5"

**Process:**
1. Extract numerical claims
2. Search for official benchmark publications
3. Compare reported vs. source values
4. Flag any discrepancies with source links
5. Update with verified figures

### Example 3: Version number validation

**User request:** "Check if these library versions are still current"

**Process:**
1. List all version numbers mentioned
2. Check package registries (npm, PyPI, etc.)
3. Identify outdated versions
4. Suggest updates with changelog references
5. Update after user confirms

## Quality checklist

Before completing fact-check:

- [ ] All factual claims identified and categorized
- [ ] Each claim verified against official sources
- [ ] Sources are authoritative and current
- [ ] Correction report is clear and actionable
- [ ] Temporal context included where relevant
- [ ] User approval obtained before changes
- [ ] All edits verified successful
- [ ] Summary provided to user

## Limitations

**This skill cannot:**
- Verify subjective opinions or judgments
- Access paywalled or restricted sources
- Determine "truth" in disputed claims
- Predict future specifications or features

**For such cases:**
- Note the limitation in the report
- Suggest qualification language
- Recommend user research or expert consultation
