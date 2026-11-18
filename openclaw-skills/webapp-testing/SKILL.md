---
name: webapp-testing
description: 'Use when testing local web applications with Playwright, verifying frontend behavior, debugging UI issues, capturing screenshots, inspecting browser logs, or validating user flows.'
zh_description: "用于使用 Playwright 测试本地 Web 应用、验证前端行为、截图和查看浏览器日志。"
version: "1.0.1"
author: "Anthropic contributors; local curators"
source: "https://github.com/anthropics/skills"
source_url: "https://github.com/anthropics/skills/blob/e4bb5d960d87126ff3b3a8af1a104b7db67560ba/skills/webapp-testing/SKILL.md"
license: "Apache-2.0"
tags: ["development", "testing", "webapp"]
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 3
complexity: "intermediate"
---

# Web Application Testing

To test local web applications, write native Python Playwright scripts.

**Helper Scripts Available**:
- `scripts/with_server.py` - Starts multiple servers and attempts cleanup.
  Current implementation uses `shell=True`, unread stdout/stderr pipes and
  termination of the shell Popen only. Verbose logs can block and descendants
  may survive. Use only reviewed commands in authorized environments; prefer
  existing servers or a host runner that consumes logs and manages its process
  group. Confirm owned descendants exit; the helper alone does not prove cleanup.

Usually inspect `--help` for usage. Read source first when side effects,
modification scope or lifecycle handling need review; do not execute an unknown
helper merely to avoid reading it.

## Decision Tree: Choosing Your Approach

```
User task → Is it static HTML?
    ├─ Yes → Read HTML file directly to identify selectors
    │         ├─ Success → Write Playwright script using selectors
    │         └─ Fails/Incomplete → Treat as dynamic (below)
    │
    └─ No (dynamic webapp) → Is the server already running?
        ├─ No → Run: python scripts/with_server.py --help
        │        Then use the helper + write simplified Playwright script
        │
        └─ Yes → Reconnaissance-then-action:
            1. Navigate and wait for the target element/app-ready signal
            2. Take screenshot or inspect DOM
            3. Identify selectors from rendered state
            4. Execute actions with discovered selectors
```

## Example: Using with_server.py

To start a server, run `--help` first, then use the helper:

**Single server:**
```bash
python scripts/with_server.py --server "npm run dev" --port 5173 -- python your_automation.py
```

**Multiple servers (e.g., backend + frontend):**
```bash
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python your_automation.py
```

Keep browser logic in the automation script. The helper starts servers and
attempts cleanup; verify its owned descendants exit as noted above:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True) # Always launch chromium in headless mode
    page = browser.new_page()
    page.goto('http://localhost:5173') # Server already running and ready
    page.get_by_role('button', name='Submit').wait_for(state='visible')
    # Replace with this app's ready marker/expected response and assert its state
    # ... your automation logic
    browser.close()
```

## Reconnaissance-Then-Action Pattern

1. **Inspect rendered DOM**:
   ```python
   page.screenshot(path='/tmp/inspect.png', full_page=True)
   content = page.content()
   page.locator('button').all()
   ```

2. **Identify selectors** from inspection results

3. **Execute actions** using discovered selectors

## Common Pitfall

Wait for the target element, application-ready marker or expected response
before inspecting the relevant state. Use `networkidle` only when appropriate
for that page; polling may prevent it, and network quiet does not prove UI readiness.

## Best Practices

- Inspect bundled helper usage and lifecycle limits before choosing it; review source when needed.
- Use `sync_playwright()` for synchronous scripts
- Always close the browser when done
- Use descriptive selectors: `text=`, `role=`, CSS selectors, or IDs
- Use locator assertions or explicit application readiness; fixed sleeps do not establish readiness

## Reference Files

- **examples/** - Examples showing common patterns:
  - `element_discovery.py` - Discovering buttons, links, and inputs on a page
  - `static_html_automation.py` - Using file:// URLs for local HTML
  - `console_logging.py` - Capturing console logs during automation
