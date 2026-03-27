# 通用运营 / General Operations

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

覆盖品牌、事实核查、内部沟通、主题与常用运营辅助技能。

当前分类共 **11** 个技能。

## 推荐先看

- [interview-system-designer](./interview-system-designer/) - This skill should be used when the user asks to "design interview processes", "create hiring pipelines", "calibrate interview loops", "generate interview questions", "design competency matrices", "analyze interviewer bias", "create scoring rubrics", "build question banks", or "optimize hiring systems". Use for designing role-specific interview loops, competency assessments, and hiring calibration systems.
- [teams-channel-post-writer](./teams-channel-post-writer/) - Creates educational Teams channel posts for internal knowledge sharing about Claude Code features, tools, and best practices. Applies when writing posts, announcements, or documentation to teach colleagues effective Claude Code usage, announce new features, share productivity tips, or document lessons learned. Provides templates, writing guidelines, and structured approaches emphasizing concrete examples, underlying principles, and connections to best practices like context engineering. Activates for content involving Teams posts, channel announcements, feature documentation, or tip sharing.
- [docs-cleaner](./docs-cleaner/) - Consolidates redundant documentation while preserving all valuable content. This skill should be used when users want to clean up documentation bloat, merge redundant docs, reduce documentation sprawl, or consolidate multiple files covering the same topic. Triggers include "clean up docs", "consolidate documentation", "too many doc files", "merge these docs", or when documentation exceeds 500 lines across multiple files covering similar topics.
- [brand-guidelines](./brand-guidelines/) - Applies Anthropic''s official brand colors and typography to any sort of artifact that may benefit from having Anthropic''s look-and-feel. Use it when brand colors or style guidelines, visual formatting, or company design standards apply.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `brand-guidelines` | Applies Anthropic''s official brand colors and typography to any sort of artifact that may benefit from having Anthropic''s look-and-feel. Use it when brand colors or style guidelines, visual formatting, or company design standards apply. | [目录](./brand-guidelines/) | [SKILL.md](./brand-guidelines/SKILL.md) |
| `confidence-check` | 用于结构化自我审查，验证假设、识别不确定性和减少幻觉输出。来源：全网高频推荐的可靠性技能。 | [目录](./confidence-check/) | [SKILL.md](./confidence-check/SKILL.md) |
| `docs-cleaner` | Consolidates redundant documentation while preserving all valuable content. This skill should be used when users want to clean up documentation bloat, merge redundant docs, reduce documentation sprawl, or consolidate multiple files covering the same topic. Triggers include "clean up docs", "consolidate documentation", "too many doc files", "merge these docs", or when documentation exceeds 500 lines across multiple files covering similar topics. | [目录](./docs-cleaner/) | [SKILL.md](./docs-cleaner/SKILL.md) |
| `fact-checker` | Verifies factual claims in documents using web search and official sources, then proposes corrections with user confirmation. Use when the user asks to fact-check, verify information, validate claims, check accuracy, or update outdated information in documents. Supports AI model specs, technical documentation, statistics, and general factual statements. | [目录](./fact-checker/) | [SKILL.md](./fact-checker/SKILL.md) |
| `internal-comms` | A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.). | [目录](./internal-comms/) | [SKILL.md](./internal-comms/SKILL.md) |
| `interview-system-designer` | This skill should be used when the user asks to "design interview processes", "create hiring pipelines", "calibrate interview loops", "generate interview questions", "design competency matrices", "analyze interviewer bias", "create scoring rubrics", "build question banks", or "optimize hiring systems". Use for designing role-specific interview loops, competency assessments, and hiring calibration systems. | [目录](./interview-system-designer/) | [SKILL.md](./interview-system-designer/SKILL.md) |
| `slack-gif-creator` | Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack like "make me a GIF of X doing Y for Slack." | [目录](./slack-gif-creator/) | [SKILL.md](./slack-gif-creator/SKILL.md) |
| `supermemory` | 用于长期记忆管理、偏好捕获、矛盾检测和项目状态跟踪。来源：supermemoryai/supermemory。 | [目录](./supermemory/) | [SKILL.md](./supermemory/SKILL.md) |
| `teams-channel-post-writer` | Creates educational Teams channel posts for internal knowledge sharing about Claude Code features, tools, and best practices. Applies when writing posts, announcements, or documentation to teach colleagues effective Claude Code usage, announce new features, share productivity tips, or document lessons learned. Provides templates, writing guidelines, and structured approaches emphasizing concrete examples, underlying principles, and connections to best practices like context engineering. Activates for content involving Teams posts, channel announcements, feature documentation, or tip sharing. | [目录](./teams-channel-post-writer/) | [SKILL.md](./teams-channel-post-writer/SKILL.md) |
| `theme-factory` | Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with colors/fonts that you can apply to any artifact that has been creating, or can generate a new theme on-the-fly. | [目录](./theme-factory/) | [SKILL.md](./theme-factory/SKILL.md) |
| `weather` | 免 API Key 的天气查询技能，支持多数据源与自然语言请求。 | [目录](./weather/) | [SKILL.md](./weather/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
