# Extended procedures and examples

Use [SKILL.md](SKILL.md) to select the task. Read only the sections it links for the current step.

<a id="section-1"></a>

## Codebase Analysis Commands

Run these before generating docs to gather facts:

```bash
# Project overview
cat package.json | jq '{name, version, scripts, dependencies: (.dependencies | keys), devDependencies: (.devDependencies | keys)}'

# Directory structure (top 2 levels)
find . -maxdepth 2 -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/.next/*' | sort | head -60

# Largest files (often core modules)
find src/ -name "*.ts" -not -path "*/test*" -exec wc -l {} + | sort -rn | head -20

# All routes (Next.js App Router)
find app/ -name "route.ts" -o -name "page.tsx" | sort

# All routes (Express)
grep -rn "router\.\(get\|post\|put\|patch\|delete\)" src/routes/ --include="*.ts"

# Recent major changes
git log --oneline --since="90 days ago" | grep -E "feat|refactor|breaking"

# Top contributors
git shortlog -sn --no-merges | head -10

# Test coverage summary
pnpm test:ci --coverage 2>&1 | tail -20
```

---
