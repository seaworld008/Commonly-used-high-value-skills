# Commonly Used High-Value Skills

![Repository Banner](./.github/assets/repo-banner.svg)

[![简体中文](https://img.shields.io/badge/README-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-1677ff)](./README.md)
[![English](https://img.shields.io/badge/README-English-111111)](./README.en.md)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-00b894)](./openclaw-skills/README.md)
[![Skills](https://img.shields.io/badge/Skills-296-7c3aed)](./skills/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

A high-value skills repository for AI developers, organized by real work scenarios such as developer engineering, DevOps, automation, finance, design, knowledge workflows, and reliability.

This repository currently contains **16 categories / 296 skills**.

## Who This Is For

- AI developers using `Codex`, `Claude Code`, `Hermes Agent`, or similar coding assistants
- Teams building reusable skill libraries for common workflows
- OpenClaw users who need a flat exported skill directory
- Builders who want a practical, extensible agent workflow repository instead of a loose prompt collection

## Why It Is Useful

- Skills are organized by scenario, not dumped into a single list
- Many skills include `scripts/`, `references/`, and `assets/`
- The repository supports both categorized source usage and flat OpenClaw export
- It is suitable both for daily usage and long-term team knowledge accumulation
- The repo now supports automated discovery, upstream sync, candidate ranking, quality checks, and generated view refreshes, so it can be maintained as a living skill system rather than a static dump
- Curation is policy-driven: trusted sources can be preferred, noisy sources can be denied, and minimum quality thresholds can be enforced in one place
- `scripts/sync_codex_skills.py` lets you sync the latest repository skills into a local Codex skill directory without manual copying
- The repository also emphasizes trust and safety through provenance tracking, curated source controls, and built-in security-review skills such as `skill-vetter`, `skill-security-auditor`, `input-guard`, and `link-checker`
- The repository now also includes license auditing and scheduled dead-link checks: `repo-validation` blocks external skills that are missing license metadata, while the monthly `dead-links` workflow produces a link health report instead of silently drifting.
- `Hermes Agent` is also treated as a first-class supported client: it uses the same categorized `skills/` tree and already has dedicated Hermes runtime, MCP, and Hermes + graphify + GSD workflow skills in the repository.

## Which Directory Should You Use

| Client | Directory |
|--------|-----------|
| `Codex` / `Claude Code` / `Hermes Agent` / source-browsing AI coding assistants | `skills/` |
| `OpenClaw` | `openclaw-skills/` |

## Quick Start

### Option 1: Give This Prompt to Your AI Tool (Recommended)

If you want your AI tool to install the skills for you, start with this short prompt:

```text
You are my local installation assistant. Please install the skills from this repository into the current AI tool: https://github.com/seaworld008/Commonly-used-high-value-skills
```

If the AI tool cannot infer enough context, add one more line:

```text
The current tool is `<Codex / Claude Code / Hermes Agent / Cursor / OpenClaw>`, and the local repository path is `<your local repo path>`.
```

This works because the repository already includes AI-readable installation rules and directory conventions, so users usually do not need to spell out the full install workflow in the prompt.

### Option 2: Manual Setup

1. Clone the repository.
2. Choose the correct directory for your client:
   - `Codex` / `Claude Code` / `Hermes Agent` / `Cursor` / other source-browsing assistants: use `skills/`
   - `OpenClaw`: use `openclaw-skills/`
3. If you use OpenClaw, generate the flat export first:

```bash
python3 scripts/export_openclaw_skills.py
```

4. Point your AI tool to the correct directory.
5. Verify by opening a few known skills, for example:
   - `skills/developer-engineering/codebase-onboarding`
   - `skills/security-and-reliability/skill-vetter`
   - `openclaw-skills/codebase-onboarding`

If you want client-specific examples instead of the generic setup above, continue with:

- [Client Install Guides](./docs/client-install-guides.md)

### Common Maintenance Commands

If you change source skills in the repository, refresh generated views with:

```bash
python3 scripts/refresh_repo_views.py
```

If you also want to validate external skill license metadata and outbound link health locally, run:

```bash
python3 scripts/audit_licenses.py
python3 scripts/check_dead_links.py --output docs/sources/reports/dead-links.json
```

If Codex shows local skill warnings such as `invalid SKILL.md`, `missing YAML frontmatter`, or broken `metadata`, you can normalize a local Codex skill tree with:

```bash
python3 scripts/normalize_codex_skills.py ~/.codex/skills
```

If you want to sync the latest repository skills into a local Codex skills directory, run:

```bash
python3 scripts/sync_codex_skills.py --source-root ./skills --codex-root ~/.codex/skills
```

## Quick Category Jump Table

| Category | What It Covers | Jump | Folder |
|----------|----------------|------|--------|
| Developer Engineering | Testing, review, performance, architecture, databases | [Jump](#cat-developer-engineering) | [Folder](./skills/developer-engineering/) |
| AI Workflow | Agent skill usage, planning, implementation, review, verification, and shipping loops | [Jump](#cat-ai-workflow) | [Folder](./skills/ai-workflow/) |
| AI Platform and Agents | ChatGPT Apps, Hermes, MCP, Figma, OpenAI docs, proactive agents | [Jump](#cat-ai-agent-platform) | [Folder](./skills/ai-agent-platform/) |
| Workflow Automation | Browser automation, GitHub, notebooks, Playwright, graphify/GSD | [Jump](#cat-workflow-automation) | [Folder](./skills/engineering-workflow-automation/) |
| DevOps / SRE | Releases, observability, incidents, CI/CD, secrets | [Jump](#cat-devops-sre) | [Folder](./skills/devops-sre/) |
| Finance Investing | Financial data, valuation, risk, backtesting, research writing | [Jump](#cat-finance-investing) | [Folder](./skills/finance-investing/) |
| Growth Operations | Xiaohongshu, social media, content, attribution, competitor work | [Jump](#cat-growth-operations) | [Folder](./skills/growth-operations-xiaohongshu/) |
| Office and Documents | Word, Excel, PPT, PDF, meeting output | [Jump](#cat-office-white-collar) | [Folder](./skills/office-white-collar/) |
| Knowledge and PM Integrations | Notion, Linear, Obsidian, Lark/Feishu, spec-to-implementation | [Jump](#cat-knowledge-pm) | [Folder](./skills/knowledge-and-pm-integrations/) |
| General Operations | Brand, fact-checking, internal comms, themes, weather | [Jump](#cat-operations-general) | [Folder](./skills/operations-general/) |
| Product and Design | Product analysis, design systems, UX, SaaS scaffolding | [Jump](#cat-product-design) | [Folder](./skills/product-design/) |
| Security and Reliability | Sentry, best practices, threat modeling, vulnerability scanning | [Jump](#cat-security-reliability) | [Folder](./skills/security-and-reliability/) |
| Multimodal Media | Images, speech, video, screenshots, summaries, transcription | [Jump](#cat-multimodal-media) | [Folder](./skills/multimodal-media/) |
| Deployment Platforms | Cloudflare, Netlify, Render, Vercel | [Jump](#cat-deployment-platforms) | [Folder](./skills/deployment-platforms/) |
| Memory and Safety | Memory, input guard, RAG, runbooks | [Jump](#cat-memory-safety) | [Folder](./skills/openclaw-memory-and-safety/) |
| Task Understanding | Live search, reflection, and task-understanding support | [Jump](#cat-task-understanding) | [Folder](./skills/task-understanding-decomposition/) |

## Recommended Starting Categories

- `developer-engineering`
- `ai-workflow`
- `ai-agent-platform`
- `engineering-workflow-automation`
- `finance-investing`
- `knowledge-and-pm-integrations`
- `multimodal-media`
- `security-and-reliability`

## Hermes Agent Support

This repository does not just happen to include a few Hermes-related skills. It explicitly supports `Hermes Agent` as one of the maintained consumption targets:

- installation layout matches `Codex` / `Claude Code`, using the categorized `skills/` tree
- it includes the dedicated [`hermes-agent`](./skills/ai-agent-platform/hermes-agent/) skill covering CLI usage, gateway setup, profiles, memory, skills, MCP, and contributor guidance
- it includes [`native-mcp`](./skills/ai-agent-platform/native-mcp/) for Hermes MCP usage
- it includes the `hermes-graphify-gsd-*` workflow skills for graph-aware and autonomous development loops

Recommended starting points for Hermes users:

- [`skills/ai-agent-platform/hermes-agent`](./skills/ai-agent-platform/hermes-agent/)
- [`skills/ai-agent-platform/native-mcp`](./skills/ai-agent-platform/native-mcp/)
- [`skills/ai-agent-platform/README.md`](./skills/ai-agent-platform/README.md)
- [Client Install Guides](./docs/client-install-guides.md)

## Repository Positioning

Use this repository when you want:

- reusable AI Skill templates
- agent workflows grounded in real work
- a multi-client skill layout that works across AI coding assistants
- a skills infrastructure that can keep growing as a public, high-value repository

## Repository Goals

- Preserve highly reusable and composable skill modules.
- Reduce discovery and usage cost through consistent directories and documentation.
- Match common work requests to executable methods, templates, scripts, and validation steps.

## Multi-Client Compatible Installation

This repository exposes two consumption surfaces for different AI clients:

| Client | Directory | Why |
|--------|-----------|-----|
| `Codex` / `Claude Code` / `Hermes Agent` / source-browsing coding assistants | `skills/` | Keeps category structure for browsing, maintenance, and editing |
| `OpenClaw` | `openclaw-skills/` | OpenClaw expects a flat one-level skill directory |

### AI-Readable Rules

The repository-level [AGENTS.md](./AGENTS.md) defines these rules for future agents:

- `OpenClaw` installations must use `openclaw-skills/`.
- `Codex`, `Claude Code`, `Hermes Agent`, and similar clients should use `skills/`.
- Do not point OpenClaw at the repository root or the categorized `skills/` tree.
- Do not manually edit `openclaw-skills/`; regenerate it from source scripts.
- When updating `README.md`, update `README.en.md` in the same change.

### Recommended OpenClaw Setup

1. Clone this repository.
2. Generate or refresh the OpenClaw-compatible export:

```bash
python3 scripts/export_openclaw_skills.py
```

3. Add the cloned repository's `openclaw-skills/` directory to `skills.load.extraDirs`.
4. Verify recognition:

```bash
openclaw skills list
openclaw skills check
```

## Directory Structure

```text
skills/
  developer-engineering/                # Developer engineering
  ai-workflow/                          # AI workflows, context engineering, planning, review
  ai-agent-platform/                    # AI platforms and agent development
  engineering-workflow-automation/      # GitHub, CI, browser testing, workflow automation
  devops-sre/                           # DevOps / SRE
  finance-investing/                    # Finance and investment research
  growth-operations-xiaohongshu/        # Growth operations and social media
  office-white-collar/                  # Office documents and white-collar workflows
  knowledge-and-pm-integrations/        # Linear, Notion, Obsidian, Lark/Feishu, knowledge workflows
  operations-general/                   # General operations
  product-design/                       # Product and design
  security-and-reliability/             # Security governance and reliability
  multimodal-media/                     # Images, speech, video, screenshots, transcription
  deployment-platforms/                 # Vercel, Netlify, Render, Cloudflare
  openclaw-memory-and-safety/           # Memory and safety
  task-understanding-decomposition/     # Task understanding and decomposition
openclaw-skills/                        # Generated flat export for OpenClaw
```

## Usage

1. Open the target category directory, for example `skills/developer-engineering/`.
2. Open the relevant `SKILL.md` and read its triggers, workflow, boundaries, and scripts.
3. If a skill includes `scripts/`, `references/`, or `assets/`, reuse those files before recreating similar content.

## Skill Overview (by category, 16 categories / 258 skills)

<a id="cat-developer-engineering"></a>
### 1. Developer Engineering (developer-engineering, 49)

- [`agent-designer`](./skills/developer-engineering/agent-designer/)
- [`api-design-reviewer`](./skills/developer-engineering/api-design-reviewer/)
- [`api-test-suite-builder`](./skills/developer-engineering/api-test-suite-builder/)
- [`aws-solution-architect`](./skills/developer-engineering/aws-solution-architect/)
- [`builder`](./skills/developer-engineering/builder/)
- [`cli-demo-generator`](./skills/developer-engineering/cli-demo-generator/)
- [`code-review-excellence`](./skills/developer-engineering/code-review-excellence/)
- [`codebase-inspection`](./skills/developer-engineering/codebase-inspection/)
- [`codebase-onboarding`](./skills/developer-engineering/codebase-onboarding/)
- [`database-designer`](./skills/developer-engineering/database-designer/)
- [`database-schema-designer`](./skills/developer-engineering/database-schema-designer/)
- [`debugging-strategies`](./skills/developer-engineering/debugging-strategies/)
- [`dependency-auditor`](./skills/developer-engineering/dependency-auditor/)
- [`docker-expert`](./skills/developer-engineering/docker-expert/)
- [`frontend-design`](./skills/developer-engineering/frontend-design/)
- [`gateway`](./skills/developer-engineering/gateway/)
- [`git-worktree-manager`](./skills/developer-engineering/git-worktree-manager/)
- [`github-contributor`](./skills/developer-engineering/github-contributor/)
- [`graphify`](./skills/developer-engineering/graphify/)
- [`graphql-expert`](./skills/developer-engineering/graphql-expert/)
- [`i18n-expert`](./skills/developer-engineering/i18n-expert/)
- [`kubernetes-specialist`](./skills/developer-engineering/kubernetes-specialist/)
- [`mcp-builder`](./skills/developer-engineering/mcp-builder/)
- [`mcp-server-builder`](./skills/developer-engineering/mcp-server-builder/)
- [`migration-architect`](./skills/developer-engineering/migration-architect/)
- [`monorepo-navigator`](./skills/developer-engineering/monorepo-navigator/)
- [`neon-postgres`](./skills/developer-engineering/neon-postgres/)
- [`nextjs-app-router`](./skills/developer-engineering/nextjs-app-router/)
- [`parallel-debugging`](./skills/developer-engineering/parallel-debugging/)
- [`performance-profiler`](./skills/developer-engineering/performance-profiler/)
- [`pr-review-expert`](./skills/developer-engineering/pr-review-expert/)
- [`promptfoo-evaluation`](./skills/developer-engineering/promptfoo-evaluation/)
- [`python-performance`](./skills/developer-engineering/python-performance/)
- [`qa-expert`](./skills/developer-engineering/qa-expert/)
- [`repomix-safe-mixer`](./skills/developer-engineering/repomix-safe-mixer/)
- [`rust-engineer`](./skills/developer-engineering/rust-engineer/)
- [`schema`](./skills/developer-engineering/schema/)
- [`skill-tester`](./skills/developer-engineering/skill-tester/)
- [`supabase`](./skills/developer-engineering/supabase/)
- [`supabase-postgres`](./skills/developer-engineering/supabase-postgres/)
- [`supabase-postgres-best-practices`](./skills/developer-engineering/supabase-postgres-best-practices/)
- [`systematic-debugging`](./skills/developer-engineering/systematic-debugging/)
- [`tailwind-design-system`](./skills/developer-engineering/tailwind-design-system/)
- [`tech-debt-tracker`](./skills/developer-engineering/tech-debt-tracker/)
- [`terraform-engineer`](./skills/developer-engineering/terraform-engineer/)
- [`typescript-best-practices`](./skills/developer-engineering/typescript-best-practices/)
- [`vercel-react-best-practices`](./skills/developer-engineering/vercel-react-best-practices/)
- [`web-artifacts-builder`](./skills/developer-engineering/web-artifacts-builder/)
- [`webapp-testing`](./skills/developer-engineering/webapp-testing/)

<a id="cat-ai-workflow"></a>
### 2. AI Workflow (ai-workflow, 43)

- [`agent-workflow-designer`](./skills/ai-workflow/agent-workflow-designer/)
- [`api-and-interface-design`](./skills/ai-workflow/api-and-interface-design/)
- [`brainstorming`](./skills/ai-workflow/brainstorming/)
- [`browser-testing-with-devtools`](./skills/ai-workflow/browser-testing-with-devtools/)
- [`ci-cd-and-automation`](./skills/ai-workflow/ci-cd-and-automation/)
- [`code-review-and-quality`](./skills/ai-workflow/code-review-and-quality/)
- [`code-simplification`](./skills/ai-workflow/code-simplification/)
- [`context-engineering`](./skills/ai-workflow/context-engineering/)
- [`debugging-and-error-recovery`](./skills/ai-workflow/debugging-and-error-recovery/)
- [`deep-research`](./skills/ai-workflow/deep-research/)
- [`deprecation-and-migration`](./skills/ai-workflow/deprecation-and-migration/)
- [`dispatching-parallel-agents`](./skills/ai-workflow/dispatching-parallel-agents/)
- [`documentation-and-adrs`](./skills/ai-workflow/documentation-and-adrs/)
- [`executing-plans`](./skills/ai-workflow/executing-plans/)
- [`find-skills`](./skills/ai-workflow/find-skills/)
- [`finishing-a-development-branch`](./skills/ai-workflow/finishing-a-development-branch/)
- [`frontend-ui-engineering`](./skills/ai-workflow/frontend-ui-engineering/)
- [`git-workflow-and-versioning`](./skills/ai-workflow/git-workflow-and-versioning/)
- [`idea-refine`](./skills/ai-workflow/idea-refine/)
- [`incremental-implementation`](./skills/ai-workflow/incremental-implementation/)
- [`nexus`](./skills/ai-workflow/nexus/)
- [`performance-optimization`](./skills/ai-workflow/performance-optimization/)
- [`planning-and-task-breakdown`](./skills/ai-workflow/planning-and-task-breakdown/)
- [`prompt-optimizer`](./skills/ai-workflow/prompt-optimizer/)
- [`rally`](./skills/ai-workflow/rally/)
- [`receiving-code-review`](./skills/ai-workflow/receiving-code-review/)
- [`requesting-code-review`](./skills/ai-workflow/requesting-code-review/)
- [`security-and-hardening`](./skills/ai-workflow/security-and-hardening/)
- [`sherpa`](./skills/ai-workflow/sherpa/)
- [`shipping-and-launch`](./skills/ai-workflow/shipping-and-launch/)
- [`skill-creator`](./skills/ai-workflow/skill-creator/)
- [`skill-reviewer`](./skills/ai-workflow/skill-reviewer/)
- [`skills-search`](./skills/ai-workflow/skills-search/)
- [`source-driven-development`](./skills/ai-workflow/source-driven-development/)
- [`spec-driven-development`](./skills/ai-workflow/spec-driven-development/)
- [`subagent-driven-development`](./skills/ai-workflow/subagent-driven-development/)
- [`test-driven-development`](./skills/ai-workflow/test-driven-development/)
- [`using-agent-skills`](./skills/ai-workflow/using-agent-skills/)
- [`using-git-worktrees`](./skills/ai-workflow/using-git-worktrees/)
- [`using-superpowers`](./skills/ai-workflow/using-superpowers/)
- [`verification-before-completion`](./skills/ai-workflow/verification-before-completion/)
- [`writing-plans`](./skills/ai-workflow/writing-plans/)
- [`writing-skills`](./skills/ai-workflow/writing-skills/)

<a id="cat-ai-agent-platform"></a>
### 3. AI Platform and Agent Development (ai-agent-platform, 16)

- [`agent-hub`](./skills/ai-agent-platform/agent-hub/)
- [`arena`](./skills/ai-agent-platform/arena/)
- [`chatgpt-apps`](./skills/ai-agent-platform/chatgpt-apps/)
- [`develop-web-game`](./skills/ai-agent-platform/develop-web-game/)
- [`figma`](./skills/ai-agent-platform/figma/)
- [`figma-implement-design`](./skills/ai-agent-platform/figma-implement-design/)
- [`hermes-agent`](./skills/ai-agent-platform/hermes-agent/)
- [`hermes-graphify-gsd-nonintrusive-workflow`](./skills/ai-agent-platform/hermes-graphify-gsd-nonintrusive-workflow/)
- [`hermes-graphify-gsd-runtime-operator`](./skills/ai-agent-platform/hermes-graphify-gsd-runtime-operator/)
- [`mcporter`](./skills/ai-agent-platform/mcporter/)
- [`native-mcp`](./skills/ai-agent-platform/native-mcp/)
- [`openai-docs`](./skills/ai-agent-platform/openai-docs/)
- [`oracle`](./skills/ai-agent-platform/oracle/)
- [`proactive-agent`](./skills/ai-agent-platform/proactive-agent/)
- [`self-improving-agent`](./skills/ai-agent-platform/self-improving-agent/)
- [`sigil`](./skills/ai-agent-platform/sigil/)

<a id="cat-workflow-automation"></a>
### 4. Engineering Workflow Automation (engineering-workflow-automation, 15)

- [`agent-browser`](./skills/engineering-workflow-automation/agent-browser/)
- [`billing-automation`](./skills/engineering-workflow-automation/billing-automation/)
- [`changelog-automation`](./skills/engineering-workflow-automation/changelog-automation/)
- [`gh-address-comments`](./skills/engineering-workflow-automation/gh-address-comments/)
- [`gh-fix-ci`](./skills/engineering-workflow-automation/gh-fix-ci/)
- [`github`](./skills/engineering-workflow-automation/github/)
- [`gsd-graphify-brownfield-bootstrap`](./skills/engineering-workflow-automation/gsd-graphify-brownfield-bootstrap/)
- [`guardian`](./skills/engineering-workflow-automation/guardian/)
- [`harvest`](./skills/engineering-workflow-automation/harvest/)
- [`hermes-graphify-gsd-project-integration`](./skills/engineering-workflow-automation/hermes-graphify-gsd-project-integration/)
- [`jupyter-notebook`](./skills/engineering-workflow-automation/jupyter-notebook/)
- [`latch`](./skills/engineering-workflow-automation/latch/)
- [`playwright`](./skills/engineering-workflow-automation/playwright/)
- [`web-scraper`](./skills/engineering-workflow-automation/web-scraper/)
- [`yeet`](./skills/engineering-workflow-automation/yeet/)

<a id="cat-devops-sre"></a>
### 5. DevOps / SRE (devops-sre, 14)

- [`azure-kubernetes`](./skills/devops-sre/azure-kubernetes/)
- [`beacon`](./skills/devops-sre/beacon/)
- [`changelog-generator`](./skills/devops-sre/changelog-generator/)
- [`ci-cd-pipeline-builder`](./skills/devops-sre/ci-cd-pipeline-builder/)
- [`cloudflare-troubleshooting`](./skills/devops-sre/cloudflare-troubleshooting/)
- [`env-secrets-manager`](./skills/devops-sre/env-secrets-manager/)
- [`gear`](./skills/devops-sre/gear/)
- [`github-ops`](./skills/devops-sre/github-ops/)
- [`incident-commander`](./skills/devops-sre/incident-commander/)
- [`observability-designer`](./skills/devops-sre/observability-designer/)
- [`release-manager`](./skills/devops-sre/release-manager/)
- [`senior-architect`](./skills/devops-sre/senior-architect/)
- [`senior-devops`](./skills/devops-sre/senior-devops/)
- [`triage`](./skills/devops-sre/triage/)

<a id="cat-finance-investing"></a>
### 6. Finance and Investing (finance-investing, 16)

- [`comps-valuation-analyst`](./skills/finance-investing/comps-valuation-analyst/)
- [`earnings-call-analyzer`](./skills/finance-investing/earnings-call-analyzer/)
- [`event-driven-tracker`](./skills/finance-investing/event-driven-tracker/)
- [`factor-backtester`](./skills/finance-investing/factor-backtester/)
- [`financial-analyst`](./skills/finance-investing/financial-analyst/)
- [`financial-data-collector`](./skills/finance-investing/financial-data-collector/)
- [`helm`](./skills/finance-investing/helm/)
- [`investment-memo-writer`](./skills/finance-investing/investment-memo-writer/)
- [`ledger`](./skills/finance-investing/ledger/)
- [`levy`](./skills/finance-investing/levy/)
- [`macro-regime-monitor`](./skills/finance-investing/macro-regime-monitor/)
- [`options-strategy-evaluator`](./skills/finance-investing/options-strategy-evaluator/)
- [`portfolio-risk-manager`](./skills/finance-investing/portfolio-risk-manager/)
- [`saas-metrics-coach`](./skills/finance-investing/saas-metrics-coach/)
- [`sec-filing-reviewer`](./skills/finance-investing/sec-filing-reviewer/)
- [`stock-screener-builder`](./skills/finance-investing/stock-screener-builder/)

<a id="cat-growth-operations"></a>
### 7. Growth Operations (growth-operations-xiaohongshu, 14)

- [`algorithmic-art`](./skills/growth-operations-xiaohongshu/algorithmic-art/)
- [`app-store-optimization`](./skills/growth-operations-xiaohongshu/app-store-optimization/)
- [`campaign-analytics`](./skills/growth-operations-xiaohongshu/campaign-analytics/)
- [`compete`](./skills/growth-operations-xiaohongshu/compete/)
- [`competitors-analysis`](./skills/growth-operations-xiaohongshu/competitors-analysis/)
- [`content-creator`](./skills/growth-operations-xiaohongshu/content-creator/)
- [`growth`](./skills/growth-operations-xiaohongshu/growth/)
- [`marketing-demand-acquisition`](./skills/growth-operations-xiaohongshu/marketing-demand-acquisition/)
- [`marketing-strategy-pmm`](./skills/growth-operations-xiaohongshu/marketing-strategy-pmm/)
- [`prompt-engineer-toolkit`](./skills/growth-operations-xiaohongshu/prompt-engineer-toolkit/)
- [`pulse`](./skills/growth-operations-xiaohongshu/pulse/)
- [`seo-audit`](./skills/growth-operations-xiaohongshu/seo-audit/)
- [`social-media-analyzer`](./skills/growth-operations-xiaohongshu/social-media-analyzer/)
- [`twitter-reader`](./skills/growth-operations-xiaohongshu/twitter-reader/)

<a id="cat-office-white-collar"></a>
### 8. Office and Documents (office-white-collar, 20)

- [`capture-screen`](./skills/office-white-collar/capture-screen/)
- [`doc`](./skills/office-white-collar/doc/)
- [`doc-coauthoring`](./skills/office-white-collar/doc-coauthoring/)
- [`docx`](./skills/office-white-collar/docx/)
- [`excel-automation`](./skills/office-white-collar/excel-automation/)
- [`gog`](./skills/office-white-collar/gog/)
- [`guizang-ppt-skill`](./skills/office-white-collar/guizang-ppt-skill/)
- [`markdown-tools`](./skills/office-white-collar/markdown-tools/)
- [`meeting-minutes-taker`](./skills/office-white-collar/meeting-minutes-taker/)
- [`mermaid-tools`](./skills/office-white-collar/mermaid-tools/)
- [`morph`](./skills/office-white-collar/morph/)
- [`pdf`](./skills/office-white-collar/pdf/)
- [`pdf-creator`](./skills/office-white-collar/pdf-creator/)
- [`ppt-creator`](./skills/office-white-collar/ppt-creator/)
- [`pptx`](./skills/office-white-collar/pptx/)
- [`prism`](./skills/office-white-collar/prism/)
- [`spreadsheet`](./skills/office-white-collar/spreadsheet/)
- [`stage`](./skills/office-white-collar/stage/)
- [`transcript-fixer`](./skills/office-white-collar/transcript-fixer/)
- [`xlsx`](./skills/office-white-collar/xlsx/)

<a id="cat-knowledge-pm"></a>
### 9. Knowledge and PM Integrations (knowledge-and-pm-integrations, 36)

- [`arxiv`](./skills/knowledge-and-pm-integrations/arxiv/)
- [`grove`](./skills/knowledge-and-pm-integrations/grove/)
- [`lark-approval`](./skills/knowledge-and-pm-integrations/lark-approval/)
- [`lark-attendance`](./skills/knowledge-and-pm-integrations/lark-attendance/)
- [`lark-base`](./skills/knowledge-and-pm-integrations/lark-base/)
- [`lark-calendar`](./skills/knowledge-and-pm-integrations/lark-calendar/)
- [`lark-contact`](./skills/knowledge-and-pm-integrations/lark-contact/)
- [`lark-doc`](./skills/knowledge-and-pm-integrations/lark-doc/)
- [`lark-drive`](./skills/knowledge-and-pm-integrations/lark-drive/)
- [`lark-event`](./skills/knowledge-and-pm-integrations/lark-event/)
- [`lark-im`](./skills/knowledge-and-pm-integrations/lark-im/)
- [`lark-mail`](./skills/knowledge-and-pm-integrations/lark-mail/)
- [`lark-markdown`](./skills/knowledge-and-pm-integrations/lark-markdown/)
- [`lark-minutes`](./skills/knowledge-and-pm-integrations/lark-minutes/)
- [`lark-okr`](./skills/knowledge-and-pm-integrations/lark-okr/)
- [`lark-openapi-explorer`](./skills/knowledge-and-pm-integrations/lark-openapi-explorer/)
- [`lark-shared`](./skills/knowledge-and-pm-integrations/lark-shared/)
- [`lark-sheets`](./skills/knowledge-and-pm-integrations/lark-sheets/)
- [`lark-skill-maker`](./skills/knowledge-and-pm-integrations/lark-skill-maker/)
- [`lark-slides`](./skills/knowledge-and-pm-integrations/lark-slides/)
- [`lark-task`](./skills/knowledge-and-pm-integrations/lark-task/)
- [`lark-vc`](./skills/knowledge-and-pm-integrations/lark-vc/)
- [`lark-vc-agent`](./skills/knowledge-and-pm-integrations/lark-vc-agent/)
- [`lark-whiteboard`](./skills/knowledge-and-pm-integrations/lark-whiteboard/)
- [`lark-wiki`](./skills/knowledge-and-pm-integrations/lark-wiki/)
- [`lark-workflow-meeting-summary`](./skills/knowledge-and-pm-integrations/lark-workflow-meeting-summary/)
- [`lark-workflow-standup-report`](./skills/knowledge-and-pm-integrations/lark-workflow-standup-report/)
- [`linear`](./skills/knowledge-and-pm-integrations/linear/)
- [`llm-wiki`](./skills/knowledge-and-pm-integrations/llm-wiki/)
- [`lore`](./skills/knowledge-and-pm-integrations/lore/)
- [`notion-knowledge-capture`](./skills/knowledge-and-pm-integrations/notion-knowledge-capture/)
- [`notion-meeting-intelligence`](./skills/knowledge-and-pm-integrations/notion-meeting-intelligence/)
- [`notion-research-documentation`](./skills/knowledge-and-pm-integrations/notion-research-documentation/)
- [`notion-spec-to-implementation`](./skills/knowledge-and-pm-integrations/notion-spec-to-implementation/)
- [`obsidian`](./skills/knowledge-and-pm-integrations/obsidian/)
- [`tome`](./skills/knowledge-and-pm-integrations/tome/)

<a id="cat-operations-general"></a>
### 10. General Operations (operations-general, 14)

- [`brand-guidelines`](./skills/operations-general/brand-guidelines/)
- [`confidence-check`](./skills/operations-general/confidence-check/)
- [`crest`](./skills/operations-general/crest/)
- [`dawn`](./skills/operations-general/dawn/)
- [`docs-cleaner`](./skills/operations-general/docs-cleaner/)
- [`fact-checker`](./skills/operations-general/fact-checker/)
- [`hearth`](./skills/operations-general/hearth/)
- [`internal-comms`](./skills/operations-general/internal-comms/)
- [`interview-system-designer`](./skills/operations-general/interview-system-designer/)
- [`slack-gif-creator`](./skills/operations-general/slack-gif-creator/)
- [`supermemory`](./skills/operations-general/supermemory/)
- [`teams-channel-post-writer`](./skills/operations-general/teams-channel-post-writer/)
- [`theme-factory`](./skills/operations-general/theme-factory/)
- [`weather`](./skills/operations-general/weather/)

<a id="cat-product-design"></a>
### 11. Product and Design (product-design, 13)

- [`agile-product-owner`](./skills/product-design/agile-product-owner/)
- [`canvas-design`](./skills/product-design/canvas-design/)
- [`competitive-teardown`](./skills/product-design/competitive-teardown/)
- [`landing-page-generator`](./skills/product-design/landing-page-generator/)
- [`product-analysis`](./skills/product-design/product-analysis/)
- [`product-manager-toolkit`](./skills/product-design/product-manager-toolkit/)
- [`product-strategist`](./skills/product-design/product-strategist/)
- [`researcher`](./skills/product-design/researcher/)
- [`saas-scaffolder`](./skills/product-design/saas-scaffolder/)
- [`trace`](./skills/product-design/trace/)
- [`ui-design-system`](./skills/product-design/ui-design-system/)
- [`ux-researcher-designer`](./skills/product-design/ux-researcher-designer/)
- [`voice`](./skills/product-design/voice/)

<a id="cat-security-reliability"></a>
### 12. Security and Reliability (security-and-reliability, 18)

- [`breach`](./skills/security-and-reliability/breach/)
- [`cloak`](./skills/security-and-reliability/cloak/)
- [`codeql-security-scanner`](./skills/security-and-reliability/codeql-security-scanner/)
- [`comply`](./skills/security-and-reliability/comply/)
- [`grype-syft-sbom-scanner`](./skills/security-and-reliability/grype-syft-sbom-scanner/)
- [`information-security-manager-iso27001`](./skills/security-and-reliability/information-security-manager-iso27001/)
- [`link-checker`](./skills/security-and-reliability/link-checker/)
- [`osv-scanner`](./skills/security-and-reliability/osv-scanner/)
- [`security-best-practices`](./skills/security-and-reliability/security-best-practices/)
- [`security-ownership-map`](./skills/security-and-reliability/security-ownership-map/)
- [`security-pen-testing`](./skills/security-and-reliability/security-pen-testing/)
- [`security-threat-model`](./skills/security-and-reliability/security-threat-model/)
- [`semgrep-appsec-scanner`](./skills/security-and-reliability/semgrep-appsec-scanner/)
- [`sentry`](./skills/security-and-reliability/sentry/)
- [`skill-security-auditor`](./skills/security-and-reliability/skill-security-auditor/)
- [`skill-vetter`](./skills/security-and-reliability/skill-vetter/)
- [`trivy-vulnerability-scanner`](./skills/security-and-reliability/trivy-vulnerability-scanner/)
- [`vuls-linux-cve-scanner`](./skills/security-and-reliability/vuls-linux-cve-scanner/)

<a id="cat-multimodal-media"></a>
### 13. Multimodal Media (multimodal-media, 9)

- [`clay`](./skills/multimodal-media/clay/)
- [`imagegen`](./skills/multimodal-media/imagegen/)
- [`screenshot`](./skills/multimodal-media/screenshot/)
- [`sketch`](./skills/multimodal-media/sketch/)
- [`sora`](./skills/multimodal-media/sora/)
- [`speech`](./skills/multimodal-media/speech/)
- [`summarize`](./skills/multimodal-media/summarize/)
- [`tone`](./skills/multimodal-media/tone/)
- [`transcribe`](./skills/multimodal-media/transcribe/)

<a id="cat-deployment-platforms"></a>
### 14. Deployment Platforms (deployment-platforms, 7)

- [`cloudflare-deploy`](./skills/deployment-platforms/cloudflare-deploy/)
- [`netlify-deploy`](./skills/deployment-platforms/netlify-deploy/)
- [`pipe`](./skills/deployment-platforms/pipe/)
- [`render-deploy`](./skills/deployment-platforms/render-deploy/)
- [`scaffold`](./skills/deployment-platforms/scaffold/)
- [`shard`](./skills/deployment-platforms/shard/)
- [`vercel-deploy`](./skills/deployment-platforms/vercel-deploy/)

<a id="cat-memory-safety"></a>
### 15. Memory and Safety (openclaw-memory-and-safety, 7)

- [`cast`](./skills/openclaw-memory-and-safety/cast/)
- [`honcho`](./skills/openclaw-memory-and-safety/honcho/)
- [`input-guard`](./skills/openclaw-memory-and-safety/input-guard/)
- [`omen`](./skills/openclaw-memory-and-safety/omen/)
- [`rag-architect`](./skills/openclaw-memory-and-safety/rag-architect/)
- [`runbook-generator`](./skills/openclaw-memory-and-safety/runbook-generator/)
- [`warden`](./skills/openclaw-memory-and-safety/warden/)

<a id="cat-task-understanding"></a>
### 16. Task Understanding and Decomposition (task-understanding-decomposition, 5)

- [`lens`](./skills/task-understanding-decomposition/lens/)
- [`reflect-learn`](./skills/task-understanding-decomposition/reflect-learn/)
- [`ripple`](./skills/task-understanding-decomposition/ripple/)
- [`scout`](./skills/task-understanding-decomposition/scout/)
- [`tavily-search`](./skills/task-understanding-decomposition/tavily-search/)

## Next Curation Directions

These areas are good candidates for future expansion and replacement decisions:

- Evaluate industry, data, and science-oriented skills from high-quality public skill repositories.
- Curate command-development, repository-governance, and cross-client compatibility skills.
- Turn official platform documentation into more granular deployment, security, office automation, and multimodal skills.
- Before replacing overlapping skills, compare usage frequency, quality score, and last synced time.

Detailed curation context: [Skill Curation and Upgrade Report](./docs/sources/reports/skill-curation-2026-04-25.md).

## Quick Search Commands

```bash
# List all skill definition files
rg --files skills | rg "SKILL.md$"

# Search by keyword
rg -n "prompt|security|pdf|deploy" skills/**/SKILL.md
```

## Maintenance Notes

- Keep new skills under `skills/<category>/<skill-name>/SKILL.md`.
- Generate the OpenClaw-compatible export with `python3 scripts/export_openclaw_skills.py`; do not manually edit `openclaw-skills/`.
- When landing candidate skills, update formal category lists, provenance mappings, and skill counts.
- Every skill should include clear triggers, steps, boundaries, and validation guidance.
- Prefer reusing existing `scripts/`, `references/`, and `assets/`.
- When updating `README.md`, update `README.en.md` in the same commit and run `python3 scripts/check_readme_sync.py`.

For freshness checks, prefer an offline snapshot plus local comparison instead of probing every skill one by one:

```bash
# 1) Generate a minimal snapshot template
python3 scripts/skill_snapshot_template.py generate --output /tmp/clawhub_skills_snapshot.json

# 2) Generate a snapshot from this repository's current skills
python3 scripts/skill_snapshot_template.py generate --output /tmp/clawhub_skills_snapshot.json --from-local

# 3) Validate snapshot structure
python3 scripts/skill_snapshot_template.py validate --snapshot /tmp/clawhub_skills_snapshot.json

# 4) Compare freshness offline
python3 scripts/audit_skill_freshness.py --snapshot /tmp/clawhub_skills_snapshot.json
```

## Contributing

If you want to help grow this repository:

- read [CONTRIBUTING.md](./CONTRIBUTING.md)
- add or improve skills under `skills/`
- refresh generated views with `python3 scripts/refresh_repo_views.py`
- include verification steps in your PR

## License

This repository is released under the [MIT License](./LICENSE). Externally imported skills retain their upstream license metadata. New external skills must pass `scripts/audit_licenses.py`; high-quality candidates without a clear license are auto-merged only as original `in-house` MIT rewrites, without copying upstream text.

## If This Repo Helps You

- give it a Star
- share it with AI developers and agent workflow builders
- contribute skills that are truly reusable

## Documentation

This repository maintains both Chinese and English README files for global collaboration:

- [Chinese README](./README.md)
- [English README](./README.en.md)

When updating documentation, keep skill counts, directory references, installation guidance, and validation commands consistent across both files.
