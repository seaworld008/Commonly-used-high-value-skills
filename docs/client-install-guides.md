# Client Install Guides

这份文档提供按客户端划分的安装示例，帮助你把本仓库的技能接入不同 AI 工具。

## 总原则

- `skills/` 是分类源码目录，适用于：
  - 直接浏览仓库源码的 `Codex`
  - 直接浏览仓库源码的 `Claude Code`
  - `Hermes Agent`
  - 其他按源码浏览技能目录的 AI coding assistants
- `~/.codex/skills`、`~/.claude/skills` 和项目内 `.claude/skills` 是本机安装目录，适合让客户端自动发现技能。
- `openclaw-skills/` 是扁平导出目录，适用于：
  - `OpenClaw`

如果你不确定，默认先看目标工具是否支持多级目录：

- 支持多级目录：优先 `skills/`
- 只支持一层平铺目录：优先同步到对应客户端的本机 skills 目录；`OpenClaw` 使用 `openclaw-skills/`

---

## 1. npx 一键安装

本仓库提供 npm package 入口，可以通过 GitHub 源直接运行，不需要先手动 clone：

```bash
npx github:seaworld008/Commonly-used-high-value-skills install
```

默认目标是当前项目的 `.agents/skills`，适合需要项目级安装、又希望多种 Agent 工具都能读取的场景。

常用目标：

```bash
# 安装到 Codex 用户级目录
npx github:seaworld008/Commonly-used-high-value-skills install --target codex

# 安装到 Claude Code 用户级目录
npx github:seaworld008/Commonly-used-high-value-skills install --target claude

# 安装到 Claude Code 项目级目录
npx github:seaworld008/Commonly-used-high-value-skills install --target claude-project

# 安装到 OpenClaw 默认目录；本地仓库优先使用 openclaw-skills/，npx 包会从 skills/ 平铺
npx github:seaworld008/Commonly-used-high-value-skills install --target openclaw

# 一次安装到多个默认目标
npx github:seaworld008/Commonly-used-high-value-skills install --target agents-project,codex,claude

# 自定义目录，适配其他客户端
npx github:seaworld008/Commonly-used-high-value-skills install --target custom --dir ./vendor/agent-skills
```

查看所有目标：

```bash
npx github:seaworld008/Commonly-used-high-value-skills list-targets
```

如果你已经使用 `skills.sh`，也可以用它的通用入口安装：

```bash
npx skills add seaworld008/Commonly-used-high-value-skills --all -a codex -a claude-code --copy
```

仓库自带的安装器更明确地处理本仓库的双目录结构：本地 clone 里 `openclaw` 目标会优先使用 `openclaw-skills/`；通过 npx 安装时，为避免重复打包生成文件，会从 `skills/` 平铺安装。

---

## 2. Codex

### 推荐目录

- 使用：`skills/`

### 本地同步推荐

如果你已经有一个本地 Codex 技能目录，推荐直接同步：

```bash
python3 scripts/sync_codex_skills.py \
  --source-root ./skills \
  --codex-root ~/.codex/skills
```

### 安装后检查

如果本地 Codex 技能目录有历史遗留格式问题，可以再执行：

```bash
python3 scripts/normalize_codex_skills.py ~/.codex/skills
```

### 建议先试的技能

- `skills/ai-agent-platform/hermes-agent`
- `skills/developer-engineering/codebase-onboarding`
- `skills/security-and-reliability/skill-vetter`
- `skills/ai-workflow/nlpm-audit`（审计 `SKILL.md`、`AGENTS.md`、`CLAUDE.md`、插件 manifests、hooks、commands；用法见 [`nlpm-audit Usage Guide`](./nlpm-audit-usage.md)）

---

## 3. Claude Code

### 推荐目录

- 使用：`skills/`

### 常见接入方式

如果你想让 Claude Code 自动发现这些技能，推荐同步到个人或项目级 skills 目录：

```bash
# 个人级，所有项目可用
python3 scripts/sync_codex_skills.py \
  --source-root ./skills \
  --codex-root ~/.claude/skills

# 项目级，只在当前项目可用
python3 scripts/sync_codex_skills.py \
  --source-root ./skills \
  --codex-root ./.claude/skills
```

这里的 `--codex-root` 是同步脚本沿用的目标目录参数名，也可以指向 Claude Code 的 skills 目录。
如果你只是让 Claude Code 浏览当前仓库源码，也可以直接阅读 `skills/` 分类目录。

### 建议先试的技能

- `skills/task-understanding-decomposition/brainstorming`
- `skills/developer-engineering/test-driven-development`
- `skills/engineering-workflow-automation/gh-fix-ci`
- `skills/ai-workflow/nlpm-audit`（可显式用 `/nlpm-audit` 请求审计 AI-facing markdown、skills、commands、hooks 与插件发布面；用法见 [`nlpm-audit Usage Guide`](./nlpm-audit-usage.md)）

---

## 4. Hermes Agent

### 推荐目录

- 使用：`skills/`

### 适配说明

本仓库已经把 `Hermes Agent` 作为正式支持对象来维护。  
也就是说，Hermes 不只是“能读这些技能”，而是仓库里已经有面向 Hermes 生态的专用技能：

- `skills/ai-agent-platform/hermes-agent`
- `skills/ai-agent-platform/native-mcp`
- `skills/ai-agent-platform/hermes-graphify-gsd-nonintrusive-workflow`
- `skills/ai-agent-platform/hermes-graphify-gsd-runtime-operator`
- `skills/engineering-workflow-automation/hermes-graphify-gsd-project-integration`

### 推荐起步方式

如果你已经装好了 Hermes，本地可按下面思路开始：

1. 先确保 Hermes 可读取 `skills/`
2. 先读：
   - `skills/ai-agent-platform/hermes-agent`
   - `skills/ai-agent-platform/native-mcp`
3. 如果你想把 Hermes 接进自动开发工作流，再看：
   - `skills/ai-agent-platform/README.md`
   - `skills/engineering-workflow-automation/README.md`

### 建议先试的技能

- `skills/ai-agent-platform/hermes-agent`
- `skills/ai-agent-platform/native-mcp`
- `skills/ai-agent-platform/hermes-graphify-gsd-nonintrusive-workflow`

---

## 5. OpenClaw

### 推荐目录

- 使用：`openclaw-skills/`

### 导出步骤

如果你修改了源码技能，先刷新 OpenClaw 扁平导出：

```bash
python3 scripts/export_openclaw_skills.py
```

### 推荐接入方式

把仓库中的 `openclaw-skills/` 加入 OpenClaw 的技能加载目录，例如：

```bash
openclaw skills list
openclaw skills check
```

如果工具配置支持额外目录，目标应指向：

```text
<repo>/openclaw-skills
```

不要把 OpenClaw 直接指向：

- 仓库根目录
- `skills/`

### 建议先试的技能

- `openclaw-skills/codebase-onboarding`
- `openclaw-skills/skill-vetter`
- `openclaw-skills/hermes-graphify-gsd-runtime-operator`
- `openclaw-skills/nlpm-audit`

---

## 6. 给 AI 工具的最短安装提示词

如果你希望让 AI 工具自己完成安装，可以先发这一段：

```text
你现在是我的本地安装助手，请把这个仓库 https://github.com/seaworld008/Commonly-used-high-value-skills 里的 Skills 安装到当前 AI 工具中。
```

如果它没有自动识别，再补一句：

```text
当前工具是 <Codex / Claude Code / Hermes Agent / Cursor / OpenClaw>，本地仓库路径是 <你的本地仓库路径>。
```

---

## 7. 维护时推荐顺序

如果你对仓库做了修改，建议按这个顺序刷新：

```bash
python3 scripts/refresh_repo_views.py
python3 scripts/build_catalog_json.py
python3 scripts/generate_repo_health_report.py
python3 scripts/evaluate_repo_health.py
```

如果还涉及 OpenClaw 导出，再补：

```bash
python3 scripts/export_openclaw_skills.py
```

---

## 8. 什么时候该看哪份文档

- 想快速开始：看根目录 `README.md` / `README.en.md`
- 想按客户端接入：看本文件
- 想看治理与维护：看 `docs/repo-maintenance-runbook.md`
- 想看 Hermes 自动开发工作流：看
  - `skills/ai-agent-platform/README.md`
  - `skills/engineering-workflow-automation/README.md`
