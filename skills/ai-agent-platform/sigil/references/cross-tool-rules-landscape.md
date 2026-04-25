# Cross-Tool Rules Landscape

Purpose: load this during `SCAN` when the project uses multiple AI rule systems and Sigil must avoid generating skills that conflict with them.

## Contents

1. Tool comparison
2. Shared rule shapes
3. Interoperability strategies
4. Path-based scoping
5. Sigil implications

## Tool Comparison

| Capability | `CLAUDE.md` | `.cursorrules` / `.cursor/rules/` | `.windsurfrules` | `AGENTS.md` | `.github/copilot-instructions.md` |
|------------|-------------|------------------------------------|------------------|-------------|-----------------------------------|
| Primary tool | Claude Code | Cursor | Windsurf | Cline / Roo | GitHub Copilot |
| Scoped by directory | Yes | partial / file-pattern based | No | Yes | No |
| `@import` support | Yes | No | No | No | No |
| Dynamic context | Yes (`!`command``) | No | No | No | No |
| Hook integration | Yes | No | No | No | No |
| Skill system | Yes | No | No | No | No |

## Shared Rule Shapes

These rule shapes translate well across tools:

| Pattern | Example |
|---------|---------|
| prohibition list | do not leave `console.log` in production code |
| preferred pattern | use `Result` types for domain errors |
| file placement rule | components live in `components/` |
| testing policy | add an integration test for each API endpoint |
| documentation rule | public functions require JSDoc |

Keep tool-specific instructions separate when they depend on:
- tool APIs
- MCP or hook configuration
- editor behavior

## Interoperability Strategies

### Strategy A: Shared Core + Tool-Specific Wrappers

Best when the project intentionally supports multiple AI tools.

```text
project/
├── .ai-rules/
├── CLAUDE.md
├── .cursorrules
├── .windsurfrules
└── .github/copilot-instructions.md
```

### Strategy B: `rulesync`-Style Build Step

Use when one source of truth should feed multiple rule formats.

```bash
npm run sync-rules
```

### Strategy C: `CLAUDE.md` as Master

Use when Claude Code is primary and the team can derive flatter rule files for other tools.

## Path-Based Scoping

| Tool | Scope model |
|------|-------------|
| `CLAUDE.md` | directory-local files |
| `.cursor/rules/` | file-pattern matching |
| `AGENTS.md` | directory-local files |
| `.windsurfrules` | global only |
| Copilot instructions | global only |

For monorepos, prefer directory-scoped rule systems for per-package conventions.

## Sigil Implications

During `SCAN`:

1. Detect every active rule file.
2. Extract shared rules first.
3. Preserve Claude Code-specific strengths only where they will not conflict with broader project rules.
4. Check that generated skills do not contradict other tool-specific guidance.

Sigil may suggest `CLAUDE.md` generation or repair when:
- the project has strong rules elsewhere but no Claude-facing version
- the current `CLAUDE.md` is clearly behind other rule files
- the repository needs a scoped monorepo rule layout
