---
name: playwright-pro
description: 'Production-grade Playwright testing skill for E2E suites, flaky test diagnosis, browser automation, migration from Cypress/Selenium, CI integration, visual checks, and regression validation.'
zh_description: "用于高级 Playwright 测试、诊断、稳定性和浏览器自动化。"
version: "1.0.0"
author: seaworld008
source: in-house
source_url: "https://github.com/alirezarezvani/claude-skills/tree/main/engineering-team/playwright-pro"
license: MIT
tags: '[playwright, e2e-testing, regression-testing, browser-automation, ci, flaky-tests, visual-regression, qa]'
created_at: "2026-06-03"
updated_at: "2026-06-03"
quality: 4
complexity: advanced
---

# Playwright Pro

Use this skill to design, generate, review, debug, and stabilize production-grade Playwright test suites. It is the higher-discipline complement to a basic browser automation skill: focus on reliable assertions, maintainable fixtures, CI behavior, coverage strategy, and regression confidence.

## When to Use

- Creating a new Playwright suite for a web app.
- Generating E2E tests from user stories, acceptance criteria, URLs, or existing manual QA steps.
- Fixing flaky Playwright tests in local runs or CI.
- Migrating Cypress, Selenium, Puppeteer, or manual smoke tests to Playwright.
- Adding regression tests for a bug fix.
- Reviewing test quality before merge.
- Testing authentication, checkout, forms, dashboards, uploads, permissions, onboarding, search, settings, or real-time flows.
- Adding visual, accessibility, API-assisted, or cross-browser checks.
- Integrating Playwright into GitHub Actions, CircleCI, Buildkite, Azure Pipelines, or other CI systems.

## Skip When

- The task only needs quick page inspection or a one-off screenshot.
- Unit tests or integration tests would verify the behavior more cheaply and reliably.
- There is no runnable app or stable target environment and the user does not want setup work.
- The user explicitly asks to avoid browser automation.

## Core Capabilities

1. Bootstrap a maintainable Playwright configuration.
2. Generate tests with resilient locators and web-first assertions.
3. Design fixtures for auth, test data, API setup, and cleanup.
4. Diagnose flakiness by timing, isolation, network, data, and selector stability.
5. Review tests for anti-patterns and weak assertions.
6. Migrate legacy suites while preserving behavior coverage.
7. Integrate reports, traces, screenshots, and videos into CI.
8. Build regression strategy around user-critical flows.

## Recommended Workflow

```text
1. Init: inspect framework, routes, auth, package manager, and test conventions.
2. Generate: write the smallest high-value tests for critical user paths.
3. Review: check locators, assertions, isolation, data setup, and failure diagnostics.
4. Run: execute locally in headless mode first, then headed for debugging if needed.
5. Stabilize: remove sleeps, isolate state, and add deterministic waits.
6. CI: shard, report, upload traces, and set retry policy.
7. Maintain: add regression tests for every escaped bug.
```

## Project Setup Checklist

- Install `@playwright/test` with the repo's package manager.
- Keep Playwright config in the established test directory style.
- Use one base URL per environment.
- Store credentials and test secrets in environment variables.
- Use `webServer` for local app startup when appropriate.
- Enable traces on first retry.
- Capture screenshots and videos only on failure unless visual review needs more.
- Add HTML or blob report artifacts in CI.
- Define projects for Chromium, Firefox, WebKit, mobile, or branded browsers only when they provide real coverage.
- Keep timeouts explicit and conservative.

## Example Config

```ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['blob'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
  },
});
```

## Test Generation Pattern

Write tests from user intent, not DOM structure.

```ts
import { test, expect } from '@playwright/test';

test('user can sign in and reach the dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('demo@example.com');
  await page.getByLabel('Password').fill(process.env.E2E_DEMO_PASSWORD!);
  await page.getByRole('button', { name: 'Sign in' }).click();

  await expect(page).toHaveURL(/dashboard/);
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
});
```

Prefer `getByRole`, `getByLabel`, `getByText`, and `getByTestId` over brittle CSS selectors. Add test IDs only where accessible locators are not stable or meaningful.

## Locator Rules

- Use user-facing locators first.
- Prefer role plus accessible name for controls.
- Avoid long CSS chains and nth-child selectors.
- Avoid text locators for dynamic copy unless copy is the behavior under test.
- Use `data-testid` for non-semantic UI, repeated rows, charts, or canvas-adjacent controls.
- Keep locators close to assertions so failures are readable.
- Do not locate hidden elements unless testing hidden state explicitly.

## Assertion Rules

- Use web-first assertions: `toBeVisible`, `toHaveText`, `toHaveURL`, `toBeEnabled`, `toHaveCount`.
- Assert the user-visible outcome, not just that a button was clicked.
- For API effects, assert through UI or a controlled API check.
- Avoid arbitrary sleeps.
- Avoid snapshots for highly dynamic content unless normalized.
- Make negative assertions bounded and intentional.
- Test one user behavior per test where practical.

## Flaky Test Diagnosis

Classify the failure before fixing:

- Timing: missing web-first assertion, racing navigation, animation, delayed API.
- Selector: unstable text, generated class, wrong element, hidden duplicate.
- Data: shared account state, order dependence, dirty database, clock dependency.
- Network: third-party dependency, slow API, mock mismatch, environment outage.
- Browser: viewport, locale, permissions, storage state, cross-browser behavior.
- CI: CPU starvation, missing fonts, sandbox, port conflict, parallel collision.

Use evidence:

```bash
npx playwright test tests/e2e/login.spec.ts --trace on
npx playwright show-trace test-results/**/trace.zip
npx playwright test --headed --debug
```

## Fixing Flakiness

- Replace `waitForTimeout` with an assertion on the awaited state.
- Wait for URL, response, element state, or app-specific ready marker.
- Isolate auth with `storageState` fixtures.
- Create unique test data per test run.
- Clean up data through API or database helpers.
- Disable or control animations when they are not under test.
- Mock unstable third-party services.
- Use retries only as a signal capture tool, not as the fix.

## Migration from Cypress or Selenium

- Map each legacy test to a user behavior and expected outcome.
- Drop tests that assert implementation details with no product value.
- Replace implicit waits with Playwright web-first assertions.
- Convert page objects only if they reduce duplication and stay readable.
- Preserve critical coverage first: auth, payments, destructive actions, permissions, and core workflows.
- Run old and new suites in parallel until parity is clear.

## CI Integration

```yaml
- name: Install Playwright browsers
  run: npx playwright install --with-deps

- name: Run E2E tests
  run: npx playwright test

- name: Upload Playwright report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: playwright-report
    path: playwright-report/
```

In larger suites, shard by CI node and keep trace artifacts for failures.

## Review Checklist

- Tests map to real user requirements.
- Locators are accessible and resilient.
- No arbitrary sleeps.
- Each test has deterministic setup and cleanup.
- Auth state is safe and isolated.
- Assertions verify visible outcomes or durable side effects.
- CI artifacts make failures diagnosable.
- Retries are not hiding persistent bugs.
- The suite can run locally without undocumented steps.
- Visual tests have stable baselines and masking for dynamic regions.

## Anti-Patterns

- Testing implementation classes instead of user behavior.
- Sharing one mutable test account across the whole suite.
- Using `page.locator('button').nth(3)`.
- Waiting for network idle as a universal solution in apps with polling.
- Overusing end-to-end tests for logic better covered by unit tests.
- Ignoring failed trace artifacts.
- Making the suite serial because data isolation is missing.
- Testing third-party services live in every CI run.

## Output Format

```markdown
## Test Plan
- Critical flows:
- Fixtures/data:
- Browser matrix:
- CI artifacts:

## Generated or Changed Tests
- ...

## Flake Risks
- ...

## Commands Run
- ...
```

## Boundaries

Do not store real credentials in tests. Do not hit production systems unless the user explicitly confirms the target and safety controls. Prefer local, staging, or mocked services for repeatable automation.
