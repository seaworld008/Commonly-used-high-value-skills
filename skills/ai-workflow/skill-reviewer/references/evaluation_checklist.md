# Skill Evaluation Checklist

Review skills against the target host's current documentation and the repository's quality contract. Treat this checklist as review criteria, not additional universal approval gates.

## YAML Frontmatter

- [ ] `name` field present and valid
  - Max 64 characters
  - Lowercase letters, numbers, hyphens only
  - Host-specific naming restrictions checked against its current schema
- [ ] `description` field present and valid
  - Non-empty
  - Meets the repository and host description budgets
  - Concrete task and trigger words appear first
  - Includes trigger conditions ("Use when...")

## Description Quality

### Clear Task Description Check

```
✅ "Read transcripts from supplied YouTube URLs..."
❌ "You can use this to..."
❌ "I can help you..."
✅ "Browses YouTube videos..."
✅ "This skill processes..."
```

### Trigger Conditions Check

Description should include:
- What the skill does
- When to use it
- Specific triggers (file types, keywords, scenarios)

```
❌ "Processes PDFs"
✅ "Extracts text and tables from PDF files. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction."
```

## Instruction Quality

- [ ] Imperative/infinitive form used (verb-first)
- [ ] Concise (avoid obvious explanations)
- [ ] Clear workflow steps
- [ ] Checklist pattern for complex tasks

### Imperative Form Check

```
❌ "You should run the script..."
❌ "The user can configure..."
✅ "Run the script..."
✅ "Configure by editing..."
```

## Progressive Disclosure

- [ ] SKILL.md body under 500 lines
- [ ] Detailed content in `references/`
- [ ] Large files include grep patterns
- [ ] No duplication between SKILL.md and references

## Bundled Resources

### Scripts (`scripts/`)
- [ ] Executable with proper shebang
- [ ] Explicit error handling (no bare except)
- [ ] Clear documentation
- [ ] No hardcoded secrets

### References (`references/`)
- [ ] Self-explanatory filenames
- [ ] Loaded as needed, not always
- [ ] No duplication with SKILL.md

### Assets (`assets/`)
- [ ] Used in output, not loaded into context
- [ ] Templates, images, boilerplate

## Privacy and Paths

- [ ] No absolute user paths (`/Users/username/`)
- [ ] No private identities or undeclared personal data; public product and attribution names may be necessary
- [ ] No hardcoded secrets
- [ ] Resources resolve from the installed skill; use runtime-resolved paths when tools require absolute paths

## Workflow Pattern

- [ ] Clear sequential steps
- [ ] Complex workflows have usable checkpoints without requiring boilerplate for simple tasks
- [ ] Validation/verification steps included

## Error Handling

- [ ] Scripts have specific exception types
- [ ] Error messages are helpful
- [ ] Recovery paths documented

## Summary Table

| Category | Status | Notes |
|----------|--------|-------|
| Frontmatter | | |
| Description | | |
| Instructions | | |
| Progressive Disclosure | | |
| Resources | | |
| Privacy | | |
| Workflow | | |
| Error Handling | | |
