# 通用运营 / General Operations

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

覆盖品牌、事实核查、内部沟通、主题与常用运营辅助技能。

当前分类共 **14** 个技能。

## 推荐先看

- [interview-system-designer](./interview-system-designer/) - This skill should be used when the user asks to "design interview processes", "create hiring pipelines", "calibrate interview loops", "generate interview questions", "design competency matrices", "analyze interviewer bias", "create scoring rubrics", "build question banks", or "optimize hiring systems". Use for designing role-specific interview loops, competency assessments, and hiring calibration systems.
- [teams-channel-post-writer](./teams-channel-post-writer/) - Creates educational Teams channel posts for internal knowledge sharing about Claude Code features, tools, and best practices. Applies when writing posts, announcements, or documentation to teach colleagues effective Claude Code usage, announce new features, share productivity tips, or document lessons learned. Provides templates, writing guidelines, and structured approaches emphasizing concrete examples, underlying principles, and connections to best practices like context engineering. Activates for content involving Teams posts, channel announcements, feature documentation, or tip sharing.
- [crest](./crest/) - Building engineer self-branding by transforming technical contributions into a professional brand. Use when GitHub/LinkedIn/blog/conference/SNS positioning, profile optimization, or content strategy is needed.
- [docs-cleaner](./docs-cleaner/) - 用于合并冗余文档、减少文档膨胀，并在保留有效内容的前提下整理知识库。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `brand-guidelines` | 用于在文档、页面或视觉产物中应用 Anthropic 风格的品牌色、字体和视觉规范。 | [目录](./brand-guidelines/) | [SKILL.md](./brand-guidelines/SKILL.md) |
| `confidence-check` | 用于结构化自检答案、验证假设、识别不确定性并降低幻觉风险。 | [目录](./confidence-check/) | [SKILL.md](./confidence-check/SKILL.md) |
| `crest` | Building engineer self-branding by transforming technical contributions into a professional brand. Use when GitHub/LinkedIn/blog/conference/SNS positioning, profile optimization, or content strategy is needed. | [目录](./crest/) | [SKILL.md](./crest/SKILL.md) |
| `dawn` | Proposes exactly one personal side-project idea per invocation, sized to a 1-3 day MVP. Targets CLI, automation, LLM, DX, productivity, and data-viz angles; avoids clichés like TODO apps, weather apps, and pomodoro timers. Output is an 8-section brief including a ready-to-paste coding-agent prompt. Use for morning/daily idea rituals and weekend-hack ideation. Don''t use for existing-product feature proposals (Spark), dialogue brainstorming (Riff), or prototype implementation (Forge). | [目录](./dawn/) | [SKILL.md](./dawn/SKILL.md) |
| `docs-cleaner` | 用于合并冗余文档、减少文档膨胀，并在保留有效内容的前提下整理知识库。 | [目录](./docs-cleaner/) | [SKILL.md](./docs-cleaner/SKILL.md) |
| `fact-checker` | Verifies factual claims in documents using web search and official sources, then proposes corrections with user confirmation. Use when the user asks to fact-check, verify information, validate claims, check accuracy, or update outdated information in documents. Supports AI model specs, technical documentation, statistics, and general factual statements. | [目录](./fact-checker/) | [SKILL.md](./fact-checker/SKILL.md) |
| `hearth` | Generating, optimizing, and auditing personal development environment config files (zsh/tmux/neovim/ghostty). Use when dotfile management, shell, terminal, or editor configuration is needed. | [目录](./hearth/) | [SKILL.md](./hearth/SKILL.md) |
| `internal-comms` | 用于撰写状态报告、领导层更新、FAQ、事故通报和项目进展等内部沟通材料。 | [目录](./internal-comms/) | [SKILL.md](./internal-comms/SKILL.md) |
| `interview-system-designer` | This skill should be used when the user asks to "design interview processes", "create hiring pipelines", "calibrate interview loops", "generate interview questions", "design competency matrices", "analyze interviewer bias", "create scoring rubrics", "build question banks", or "optimize hiring systems". Use for designing role-specific interview loops, competency assessments, and hiring calibration systems. | [目录](./interview-system-designer/) | [SKILL.md](./interview-system-designer/SKILL.md) |
| `slack-gif-creator` | Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack like "make me a GIF of X doing Y for Slack." | [目录](./slack-gif-creator/) | [SKILL.md](./slack-gif-creator/SKILL.md) |
| `supermemory` | 用于长期记忆管理、偏好捕获、矛盾检测和项目状态跟踪。 | [目录](./supermemory/) | [SKILL.md](./supermemory/SKILL.md) |
| `teams-channel-post-writer` | Creates educational Teams channel posts for internal knowledge sharing about Claude Code features, tools, and best practices. Applies when writing posts, announcements, or documentation to teach colleagues effective Claude Code usage, announce new features, share productivity tips, or document lessons learned. Provides templates, writing guidelines, and structured approaches emphasizing concrete examples, underlying principles, and connections to best practices like context engineering. Activates for content involving Teams posts, channel announcements, feature documentation, or tip sharing. | [目录](./teams-channel-post-writer/) | [SKILL.md](./teams-channel-post-writer/SKILL.md) |
| `theme-factory` | 用于为幻灯片、文档、报告和网页应用预设主题或生成新的颜色字体系统。 | [目录](./theme-factory/) | [SKILL.md](./theme-factory/SKILL.md) |
| `weather` | 用于免 API Key 查询当前天气、预报、恶劣天气和旅行天气信息。 | [目录](./weather/) | [SKILL.md](./weather/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
