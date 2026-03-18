# 任务理解与拆解 / Task Understanding

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦 brainstorming、research、计划编写、skills 检索与任务拆解。

当前分类共 **11** 个技能。

## 推荐先看

- [reflect-learn](./reflect-learn/) - |
- [skill-creator](./skill-creator/) - Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, update or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
- [deep-research](./deep-research/) - |
- [prompt-optimizer](./prompt-optimizer/) - Transform vague prompts into precise, well-structured specifications using EARS (Easy Approach to Requirements Syntax) methodology. This skill should be used when users provide loose requirements, ambiguous feature descriptions, or need to enhance prompts for AI-generated code, products, or documents. Triggers include requests to "optimize my prompt", "improve this requirement", "make this more specific", or when raw requirements lack detail and structure.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `agent-workflow-designer` | Design production-grade multi-agent orchestration systems. Covers five core patterns (sequential pipeline, parallel fan-out/fan-in, hierarchical delegation, event-driven, consensus), platform-specific implementations, handoff protocols, state management, error recovery, context window budgeting, and cost optimization. | [目录](./agent-workflow-designer/) | [SKILL.md](./agent-workflow-designer/SKILL.md) |
| `brainstorming` | You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation. | [目录](./brainstorming/) | [SKILL.md](./brainstorming/SKILL.md) |
| `deep-research` | | | [目录](./deep-research/) | [SKILL.md](./deep-research/SKILL.md) |
| `find-skills` | 让 Agent 自动搜索并安装合适技能，解决不知道该用哪个技能的问题。 | [目录](./find-skills/) | [SKILL.md](./find-skills/SKILL.md) |
| `prompt-optimizer` | Transform vague prompts into precise, well-structured specifications using EARS (Easy Approach to Requirements Syntax) methodology. This skill should be used when users provide loose requirements, ambiguous feature descriptions, or need to enhance prompts for AI-generated code, products, or documents. Triggers include requests to "optimize my prompt", "improve this requirement", "make this more specific", or when raw requirements lack detail and structure. | [目录](./prompt-optimizer/) | [SKILL.md](./prompt-optimizer/SKILL.md) |
| `reflect-learn` | | | [目录](./reflect-learn/) | [SKILL.md](./reflect-learn/SKILL.md) |
| `skill-creator` | Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, update or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy. | [目录](./skill-creator/) | [SKILL.md](./skill-creator/SKILL.md) |
| `skill-reviewer` | Reviews and improves Claude Code skills against official best practices. Supports three modes - self-review (validate your own skills), external review (evaluate others' skills), and auto-PR (fork, improve, submit). Use when checking skill quality, reviewing skill repositories, or contributing improvements to open-source skills. | [目录](./skill-reviewer/) | [SKILL.md](./skill-reviewer/SKILL.md) |
| `skills-search` | This skill should be used when users want to search, discover, install, or manage Claude Code skills from the CCPM registry. Triggers include requests like "find skills for PDF", "search for code review skills", "install cloudflare-troubleshooting", "list my installed skills", "what does skill-creator do", or any mention of finding/installing/managing Claude Code skills or plugins. | [目录](./skills-search/) | [SKILL.md](./skills-search/SKILL.md) |
| `tavily-search` | 提供实时联网检索能力，帮助 Agent 获取最新资讯、数据与来源证据。 | [目录](./tavily-search/) | [SKILL.md](./tavily-search/SKILL.md) |
| `writing-plans` | Use when you have a spec or requirements for a multi-step task, before touching code | [目录](./writing-plans/) | [SKILL.md](./writing-plans/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
