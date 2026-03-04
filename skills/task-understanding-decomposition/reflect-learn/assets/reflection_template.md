# Reflection Analysis

## Session Context
- **Date**: {{TIMESTAMP}}
- **Messages Analyzed**: {{MESSAGE_COUNT}}
- **Focus**: {{FOCUS}}
- **Trigger**: {{TRIGGER}}

## Signals Detected

| # | Signal | Confidence | Source Quote | Category |
|---|--------|------------|--------------|----------|
{{SIGNALS_TABLE}}

## Proposed Agent Updates

{{#each AGENT_UPDATES}}
### Change {{index}}: Update {{agent_name}}

**Target**: `{{file_path}}`
**Section**: {{section}}
**Confidence**: {{confidence}}
**Rationale**: {{rationale}}

```diff
{{diff}}
```

{{/each}}

## Proposed New Skills

{{#each NEW_SKILLS}}
### Skill {{index}}: {{skill_name}}

**Quality Gate Check**:
- [{{reusable_check}}] Reusable: {{reusable_reason}}
- [{{nontrivial_check}}] Non-trivial: {{nontrivial_reason}}
- [{{specific_check}}] Specific: {{specific_reason}}
- [{{verified_check}}] Verified: {{verified_reason}}
- [{{nodupe_check}}] No duplication: {{nodupe_reason}}

**Will create**: `.claude/skills/{{skill_name}}/SKILL.md`

**Preview**:
```yaml
---
name: {{skill_name}}
description: |
  {{skill_description}}
---
```

**Full content**: {{skill_summary}}

{{/each}}

## Conflict Check

{{#if HAS_CONFLICTS}}
- [ ] Warning - potential conflict with:
{{#each CONFLICTS}}
  - {{file}}:{{line}} - "{{existing_rule}}"
{{/each}}
{{else}}
- [x] No conflicts with existing rules detected
{{/if}}

## Commit Message

```
reflect: {{COMMIT_TITLE}}

{{#if AGENT_UPDATES}}
Agent updates:
{{#each AGENT_UPDATES}}
- {{summary}}
{{/each}}
{{/if}}

{{#if NEW_SKILLS}}
New skills:
{{#each NEW_SKILLS}}
- {{skill_name}}: {{brief_description}}
{{/each}}
{{/if}}

Extracted: {{TOTAL_SIGNALS}} signals ({{HIGH_COUNT}} high, {{MEDIUM_COUNT}} medium, {{LOW_COUNT}} low confidence)
```

## Review Prompt

Apply these changes?
- `Y` - Apply all changes and commit
- `N` - Discard all changes
- `modify` - Let me adjust specific changes
- `1,3` - Apply only agent changes 1 and 3
- `s1,s2` - Apply only skills 1 and 2
- `all-skills` - Apply all skills, skip agent updates
