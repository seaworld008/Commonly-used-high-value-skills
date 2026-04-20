# Changelog

All notable changes to this repository are documented here.

## [2026-04-18]

### Changed
- add client-specific install guides
- document Hermes Agent support in root readmes
- surface repo health threshold status
- add repo health threshold evaluation
- publish maintenance summaries in CI
- wire repo health into CI and docs
- eliminate dead link report noise
- add unified repo health report
- finalize unresolved community skill provenance
- narrow remaining unknown skill licenses
- add license audit reporting
- backfill confirmed upstream licenses
- enforce license audit in repo validation
- add repo license audit and dead link checks

## [2026-04-16]

### Added
- `hermes-graphify-gsd-runtime-operator` (ai-agent-platform) — hermes-graphify-gsd-runtime-operator
- `gsd-graphify-brownfield-bootstrap` (engineering-workflow-automation) — gsd-graphify-brownfield-bootstrap

## [2026-04-15]

### Added
- `hermes-graphify-gsd-nonintrusive-workflow` (ai-agent-platform) — hermes-graphify-gsd-nonintrusive-workflow
- `hermes-graphify-gsd-project-integration` (engineering-workflow-automation) — hermes-graphify-gsd-project-integration

## [2026-04-13]

### Added
- `hermes-agent` (ai-agent-platform) — hermes-agent
- `mcporter` (ai-agent-platform) — mcporter
- `native-mcp` (ai-agent-platform) — native-mcp
- `code-review-excellence` (developer-engineering) — code-review-excellence
- `codebase-inspection` (developer-engineering) — codebase-inspection
- `debugging-strategies` (developer-engineering) — debugging-strategies
- `graphify` (developer-engineering) — graphify
- `parallel-debugging` (developer-engineering) — parallel-debugging
- `arxiv` (knowledge-and-pm-integrations) — arxiv
- `llm-wiki` (knowledge-and-pm-integrations) — llm-wiki
- `obsidian` (knowledge-and-pm-integrations) — obsidian
- `honcho` (openclaw-memory-and-safety) — honcho
- `dispatching-parallel-agents` (task-understanding-decomposition) — dispatching-parallel-agents
- `executing-plans` (task-understanding-decomposition) — executing-plans
- `finishing-a-development-branch` (task-understanding-decomposition) — finishing-a-development-branch
- `receiving-code-review` (task-understanding-decomposition) — receiving-code-review
- `requesting-code-review` (task-understanding-decomposition) — requesting-code-review
- `using-git-worktrees` (task-understanding-decomposition) — using-git-worktrees
- `using-superpowers` (task-understanding-decomposition) — using-superpowers
- `verification-before-completion` (task-understanding-decomposition) — verification-before-completion
- `writing-skills` (task-understanding-decomposition) — writing-skills

### Changed
- clear remaining skill quality warnings (#17)

## [2026-03-27]

### Added
- `agent-hub` (ai-agent-platform) — agent-hub
- `aws-solution-architect` (developer-engineering) — aws-solution-architect
- `context-engineering` (developer-engineering) — context-engineering
- `docker-expert` (developer-engineering) — docker-expert
- `graphql-expert` (developer-engineering) — graphql-expert
- `kubernetes-specialist` (developer-engineering) — kubernetes-specialist
- `nextjs-app-router` (developer-engineering) — nextjs-app-router
- `python-performance` (developer-engineering) — python-performance
- `rust-engineer` (developer-engineering) — rust-engineer
- `supabase-postgres` (developer-engineering) — supabase-postgres
- `systematic-debugging` (developer-engineering) — systematic-debugging
- `tailwind-design-system` (developer-engineering) — tailwind-design-system
- `terraform-engineer` (developer-engineering) — terraform-engineer
- `test-driven-development` (developer-engineering) — test-driven-development
- `typescript-best-practices` (developer-engineering) — typescript-best-practices
- `senior-architect` (devops-sre) — senior-architect
- `web-scraper` (engineering-workflow-automation) — web-scraper
- `saas-metrics-coach` (finance-investing) — saas-metrics-coach
- `seo-audit` (growth-operations-xiaohongshu) — seo-audit
- `confidence-check` (operations-general) — confidence-check
- `supermemory` (operations-general) — supermemory
- `landing-page-generator` (product-design) — landing-page-generator
- `skill-security-auditor` (security-and-reliability) — skill-security-auditor
- `subagent-driven-development` (task-understanding-decomposition) — subagent-driven-development

### Changed
- simplify AI installation prompt (#12)
- clarify AI-first installation flow
- sync Codex skills and strengthen README trust signals
- tighten curated skill selection policy
- harden skill discovery and curation policy
- automate skill curation and upstream sync
- comprehensive repository optimization (P0-P3)
- add optimization roadmap for world-class skills repository
- add 24 high-value skills from top GitHub repos and skills.sh

### Fixed
- use date-only timestamp in catalog.json to avoid CI drift
- run refresh_repo_views, fix test expectations, normalize YAML frontmatter

## [2026-03-22]

### Fixed
- auto-refresh additional README skill counters

## [2026-03-21]

### Fixed
- normalize string metadata for codex skills
