# Full Routing Matrix

**Purpose:** Canonical full task-type to chain mapping.
**Read when:** The quick-start matrix is insufficient and you need the full mapping.

Complete task type → agent chain mapping. The SKILL.md contains the top 5 most common patterns; this file contains the full matrix.

---

| Task Type | Primary Chain | Recipe Hints | Additions |
|-----------|---------------|-------------|-----------|
| BUG | Scout → **Sherpa** → Builder → Radar | Scout[bug], Sherpa[epic], Builder[fix], Radar[regression] | +Sentinel (security). Skip Sherpa only when single-file atomic fix |
| INCIDENT | Triage → Scout → Builder | Triage[respond], Scout[bug], Builder[fix] | +Mend (known pattern), +Radar, +Triage (postmortem), +Flux (deep postmortem), +Matrix[combine] (failure scenarios) |
| FEATURE | **Sherpa** → Forge → Builder → Radar | Sherpa[epic], Forge[ui], Builder[api], Radar[edge] | +Muse (UI), +Artisan (frontend), +Matrix (variant exploration), +Flux[reframe] (lateral thinking), +Riff[expand] (idea exploration). Skip Sherpa only when single-file atomic change |
| INVESTIGATE | Lens | Lens[map] | +Scout (bug-related), +Canvas (viz), +Rewind[bisect] (git) |
| BRAINSTORM | Riff | Riff[expand] | +Flux (reframe first), +Spark (spec after), +Magi (decide after), +Void (prune after) |
| DECISION | Magi | Magi[decide] | +Accord[vision] (biz-tech), +Flux (reframe), +Riff (explore before deciding) |
| SECURITY | Sentinel → Builder → Radar | Sentinel[scan], Builder[fix], Radar[edge], Breach[scenario], Vigil[sigma], Specter[race] | +Probe[zap] (dynamic), +Specter (concurrency), +Breach (red-team), +Vigil (detection) |
| REFACTOR | Zen → Radar | Zen[refactor], Radar[coverage] | +Atlas[analyze] (architectural), +Grove[audit] (structure), +Nest[audit] (folder structure) |
| OPTIMIZE | Bolt/Tuner → Radar | Bolt[frontend], Tuner[explain], Radar[edge] | +Schema (DB), +Flux (first-principles), +Matrix (target combos) |
| ANALYSIS | Ripple → Builder → Radar | Ripple[impact], Builder[fix], Radar[edge], Canon[owasp], Sweep[dead] | +Canon (standards), +Sweep (cleanup) |
| API | Gateway → Builder → Radar | Gateway[design], Builder[api], Radar[edge] | +Quill[docstring], +Schema[design] |
| DEPLOY | Guardian → Launch | Guardian[pr], Launch[plan] | +Harvest[weekly] (reporting) |
| MODERNIZE | Horizon → Builder → Radar | Horizon[detect], Builder[crud], Radar[coverage] | +Polyglot (i18n), +Grove (structure), +Flux (first-principles), +Matrix (migration paths) |
| DOCS | Quill | Quill[docstring] | +Canvas[flow], +Morph[md] (convert), +Scribe (specs) |
| STRATEGY | Spark → Builder → Radar | Spark[propose], Builder[ddd], Radar[edge], Growth[seo], Pulse[kpi], Experiment[ab], Compete[matrix], Compete[swot], Retain[reengagement], Voice[nps] | +Growth/Compete/Voice/Pulse/Retain/Experiment, +Helm (simulation) |
| STRATEGY_SIM | Helm | Helm[scenario], Compete[matrix], Compete[swot], Compete[battle-card] | +Compete (intel), +Pulse (KPI), +Magi (decision), +Scribe (docs), +Canvas (viz), +Sherpa (execution) |
| INFRA | Scaffold → Gear → Radar | Scaffold[terraform], Gear[deps], Radar[edge] | +Anvil[cli] (CLI tools), +Pipe (GHA workflows) |
| GHA_WORKFLOW | Pipe | Pipe[workflow], Sentinel[scan] | +Gear (maintenance), +Launch (release), +Sentinel (security) |
| PARALLEL | Rally | Rally[parallel], Sherpa[epic] | +Sherpa (decomposition), see Rally escalation |
| PROJECT | Titan | Titan[deliver] | Full product lifecycle — Titan orchestrates 9 phases, issues chains to Nexus |
| MESSAGING | Relay → Builder → Radar | Relay[webhook], Builder[api], Radar[edge] | +Sentinel (security), +Scaffold (infra) |
| BOT | Relay → Builder → Radar | Relay[bot], Builder[api], Radar[edge] | +Sentinel (security) |
| REALTIME | Relay → Scaffold → Builder | Relay[websocket], Builder[api] | +Radar (tests) |
| WEBHOOK | Gateway → Relay → Builder | Relay[webhook], Builder[api] | +Radar (tests), +Sentinel (security) |
| HOOKS | Latch | Latch[configure] | +Gear (Git hooks), +Sentinel (security) |
| SKILL_GEN | Sigil | Sigil[generate], Architect[create] | +Lens (codebase analysis), +Grove (structure) |
| EVOLUTION | Darwin | Darwin[health], Architect[evolve], Lore[curate] | +Architect (improvement), +Void (sunset), +Lore (knowledge), +Canvas (viz) |
| KNOWLEDGE_SYNC | Lore | Lore[curate] | +Darwin (evolution input), +Architect (design insights), +Nexus (routing feedback) |
| QUALITY | Judge → Canvas | Judge[pr], Radar[coverage] | +Zen[naming] (smells), +Radar (coverage), +Sentinel (security), +Atlas[analyze] (arch), +Sweep (dead code), +Matrix (combinatorial) |
| COMPARE | Arena | Arena[compete], Scout[bug] | +Scout (bug-fix), +Sentinel (security), +Guardian (quality gate), +Matrix (dimension analysis), +Flux (reframe) |
| UX_RESEARCH | Researcher → Echo → Palette | Researcher[interview], Echo[walkthrough], Palette[usability], Trace[replay], Trace[persona] | +Cast[generate] (persona), +Trace (session data) |
| E2E | Voyager → Lens | Voyager[playwright], Radar[edge] | +Gear (CI), +Echo (persona-based), +Matrix (test matrix) |
| BROWSER | Navigator → Builder | Navigator[collect], Scout[bug], Builder[fix] | +Scout (bug repro), +Bolt[frontend] (perf), +Lens (evidence), +Native[reactnative] (mobile webview) |
| DB_DESIGN | Schema → Builder → Radar | Schema[design], Builder[ddd], Radar[edge] | +Tuner[explain] (optimize), +Atlas[analyze] (arch review) |
| OBSERVABILITY | Beacon → Gear → Builder | Beacon[slo], Builder[fix] | +Triage (incident link), +Scaffold (capacity) |
| AI_FEATURE | Oracle → Builder → Radar | Oracle[prompt], Builder[api], Radar[edge] | +Gateway (API), +Stream (pipeline), +Sentinel (safety) |
| PRERELEASE | Warden → Guardian → Launch | Warden[gate], Guardian[strategy], Launch[plan] | +Sentinel (security gate), +Radar (test gate) |
| REQUIREMENTS | Accord → Scribe → Sherpa | Accord[vision], Scribe[prd], Sherpa[epic], Plea[request], Plea[need], Saga[story], Saga[scenario] | +Canvas (diagram), +Magi[decide] (decision), +Saga (narrative), +Cast[generate] (persona) |
| DESIGN_SYSTEM | Vision → Muse → Showcase → Quill | Vision[system], Muse[tokens], Showcase[story] | +Palette[usability] (a11y), +Artisan[component] (impl) |
| DESIGN_SYSTEM_DOCS | Muse → Showcase + Canvas → Quill | — | +Vision (direction), +Artisan (live examples) |
| CONTENT | Prose → Echo → Artisan | Prose[microcopy], Prose[errors], Prose[onboarding], Voice[nps], Voice[review], Voice[sentiment] | +Polyglot (i18n), +Researcher (insights) |
| DEV_EXPERIENCE | Hearth → Gear → Latch | Hearth[zsh], Gear[deps], Latch[configure] | +Anvil (CLI), +Sigil (project skills), +Hone[audit] (CLI audit) |
| LOAD_TEST | Siege → Bolt → Builder | Siege[load], Siege[contract], Siege[chaos], Siege[mutation], Bolt[frontend], Builder[fix], Radar[edge] | +Beacon[slo] (SLO), +Triage (resilience), +Matrix (scenario combos) |
| DEMO | Director/Reel → Quill | Director[demo], Reel[vhs], Director[record], Reel[readme] | +Director[scenario] (scenario), +Director[onboard] (onboarding), +Reel[asciinema] (web embed), +Reel[terminalizer] (interactive), +Cue[script] (scripting), +Showcase (catalog), +Growth (marketing) |
| SPRINT_RETRO | Harvest → Canvas | Harvest[weekly], Canvas[flow] | +Quill[docstring] (publish), +Triage (incident link) |
| KNOWLEDGE | Scribe → Prism | Scribe[prd], Prism[audio], Prism[slide], Prism[video] | +Quill (polish), +Morph (format convert) |
| AITUBER | Cast → Aether → Builder | Cast[generate], Aether[stream], Builder[api] | +Artisan (avatar UI), +Scaffold (infra), +Beacon (monitoring) |
| REVIEW | Judge → Builder | Judge[pr], Builder[fix] | +Zen (refactor), +Sentinel (security), +Matrix (impact dimensions), +Flux (blind-spot) |
| YAGNI | Void → Sweep/Zen | Void[prune] | +Magi (approval), +Pulse (usage data) |
| REMEDIATE | Mend → Radar | Mend[runbook], Radar[regression] | +Beacon[slo] (SLO check), +Gear (infra config), +Triage (escalation) |
| SPEC_VERIFY | Attest | Attest[verify], Attest[bdd], Attest[trace], Radar[coverage] | +Scribe (spec gaps), +Radar (BDD→tests), +Builder (violation fixes), +Warden (release gate) |
| LOOP_OPS | Orbit | Orbit[generate] | +Builder (script changes), +Guardian (commit policy), +Radar (verification closure) |
| GAME | Quest → Forge → Builder → Radar | Quest[gdd], Forge[fullstack], Builder[api], Radar[edge], Tone[sfx], Dot[svg], Clay[text], Lyric[compose] | +Tone[bgm] (BGM), +Tone[voice] (VO), +Dot[canvas] (canvas art), +Clay[game] (game-ready 3D), +Lyric[style] (style transfer), +Saga (narrative), +Matrix (balance) |
| DESIGN | Frame → Artisan → Radar | Frame[extract], Artisan[component], Radar[edge], Loom[guidelines], Pixel[reproduce] | +Muse[tokens] (tokens), +Loom[guidelines] (Make guidelines), +Loom[analyze] (token audit), +Vision (direction), +Forge (prototype) |
| DESIGN_WORKFLOW | Atelier (orchestrator) | Atelier[pipeline], Forge[ui], Forge[fullstack] | Full design→code loop: Vision → Muse/Frame → Forge → Artisan → Showcase → Canvas. Persists design system to `.agents/design-system/`. Use when the task spans design direction + tokens + prototype + implementation + catalog in a single pipeline |
| ARCHITECTURE | Stratum → Canvas | Stratum[model], Canvas[flow] | +Lens[discover] (analysis), +Atlas[analyze] (review), +Scribe[hld] (docs), +Ripple[impact] (impact) |
| CREATIVE | Vision → Sketch → Artisan | Sketch[generate], Ink[icon], Dot[svg], Clay[text] | +Sketch[edit] (image edit), +Sketch[prompt] (prompt opt), +Ink[illustration] (illust), +Dot[canvas] (canvas), +Clay[image] (image-to-3D), +Growth (marketing) |
| MOCKUP | Pixel → Radar | Pixel[reproduce], Radar[coverage], Flow[hover] | +Frame (Figma source), +Muse (tokens), +Flow[loading] (loading states), +Flow[transition] (transitions), +Warden (fidelity gate) |
| DESIGN_AUDIT | Pixel[gap-report] → Canon/Judge | Pixel[gap], Pixel[verify], Pixel[audit] | +Artisan (remediation), +Muse (token regression), +Voyager (VRT baseline). Trigger: "gap analysis", "fidelity audit", "design review". Produces 8-dim × 5-severity × 9-RC Markdown+JSON report with visual artifacts |
| BRANDING | Crest → Quill | Crest[github], Crest[linkedin], Crest[blog], Crest[conference], Crest[sns] | +Growth (SEO/SMO), +Canvas (viz), +Prose (content), +Harvest (portfolio) |
| BUSINESS | Levy → Scribe | Levy[classify], Builder[ddd] | +Schema (data), +Builder (calc), +Canvas (flow) |
| ECOSYSTEM | Darwin → Gauge → Canvas | Darwin[health], Gauge[audit], Realm[phaser] | +Architect (design), +Realm (viz), +Void (prune), +Lore (knowledge) |
| PRIVACY | Cloak → Builder → Radar | Cloak[pii], Builder[fix], Radar[edge] | +Comply (regulatory), +Sentinel (static scan), +Canon (standards) |
| COMPLIANCE | Comply → Builder → Radar | Comply[soc2], Builder[fix], Radar[coverage] | +Cloak (privacy), +Canon (standards), +Scribe (policy docs) |
| CRYPTO | Crypt → Builder → Radar | Crypt[algorithm], Builder[fix], Radar[edge] | +Sentinel (security review), +Probe (TLS validation) |
| VIDEO_SCRIPT | Cue → Director/Reel | Cue[script], Cue[storyboard], Director[demo], Reel[vhs] | +Cue[narration] (narration), +Cue[explainer] (explainer), +Director[scenario] (scenario design), +Director[record] (Playwright recording), +Reel[readme] (README GIF), +Prose (copy), +Growth (marketing) |
| LEGACY | Fossil → Shift → Builder | Fossil[extract], Builder[harden], Radar[coverage] | +Shift[plan] (migration), +Rewind[history] (git history), +Lens[discover] (exploration), +Tome (documentation) |
| LANDING_PAGE | Funnel → Artisan → Radar | Funnel[build], Funnel[cta], Forge[landing], Radar[edge], Sketch[generate], Flow[hover] | +Growth (SEO/CRO), +Prose (copy), +Pixel[reproduce] (mockup), +Ink[icon] (icons), +Flow[transition] (transitions), +Echo (persona test) |
| FINOPS | Ledger → Scaffold → Gear | Ledger[estimate], Ledger[rightsizing], Ledger[ri-sp], Ledger[anomaly], Ledger[ai-gpu] | +Pulse (metrics), +Beacon (monitoring), +Canvas (dashboard spec) |
| TEST_DATA | Mint → Radar | Mint[factory], Mint[boundary], Radar[coverage] | +Schema (DB fixtures), +Siege (load data), +Builder (factory impl) |
| SEARCH | Seek → Builder → Radar | Seek[fulltext], Seek[vector], Seek[hybrid], Seek[index], Seek[rag], Builder[api], Radar[edge] | +Oracle[rag] (RAG/embeddings), +Schema (indexes), +Tuner[explain] (query perf), +Spider[topology] (crawl source) |
| MULTI_TENANT | Shard → Schema → Builder | Shard[isolation], Shard[rls], Shard[routing], Shard[scale], Builder[ddd], Radar[edge] | +Sentinel (security), +Scaffold (infra), +Radar (isolation tests) |
| MIGRATION | Shift → Builder → Radar | Shift[plan], Builder[harden], Radar[regression] | +Fossil (legacy analysis), +Horizon (modernize), +Rewind (history) |
| PRESENTATION | Stage → Canvas | Stage[marp], Stage[conference], Stage[timing] | +Stage[reveal] (reveal.js), +Stage[slidev] (Slidev/Vue), +Cue[script] (narrative), +Quill (content), +Morph (export) |
| LEARNING | Tome → Quill | Tome[learn] | +Canvas (diagrams), +Rewind (change context), +Prism (audio) |
| WORKFLOW | Weave → Builder → Radar | Weave[design], Builder[api], Radar[edge] | +Canvas (diagram), +Schema (persistence), +Attest (spec verify) |
| ARTICLE | Zine → Growth | Zine[note], Zine[zenn], Zine[qiita], Zine[devto], Zine[series] | +Prose (microcopy polish), +Stage (slide version), +Saga (narrative reshape), +Canvas (article diagrams), +Morph (PDF/Word export), +Tome (diff → learning source). Trigger: "tech blog", "note/Zenn/Qiita/dev.to", "連載", "記事" |
| SCHEDULE | Tempo → Builder → Gear | Tempo[cron], Tempo[timezone], Tempo[retry], Tempo[backfill], Tempo[calendar], Builder[api], Radar[edge] | +Weave (retry state machine), +Beacon[alerts] (schedule SLO/alerts), +Pipe (GHA cron), +Voyager[playwright] (temporal test scenarios), +Judge (correctness review), +Triage (incident → replay plan). Trigger: "cron", "timezone", "DST", "retry/backoff", "backfill", "business calendar" |
| GRAMMAR | Grok → Builder → Radar | Grok[regex], Builder[crud], Sentinel[injection], Radar[edge] | +Sentinel (regex security audit), +Canon (grammar → standards compliance), +Atlas (parser module boundary), +Shift (codemod migration), +Judge (grammar review). Trigger: "regex", "parser", "grammar", "DSL design", "AST transform", "ReDoS" |
| DAILY_IDEA | Dawn | Dawn[propose], Forge[ui], Forge[fullstack] | +Forge (prototype), +Builder (production), +Zine (article). Trigger: "今日のアイデア", "毎朝のアイデア", "週末ハック", "副業プロジェクト案", "コーディングエージェントに渡せる題材". Don't confuse with Spark (existing-product feature proposals) |
