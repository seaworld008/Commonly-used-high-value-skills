# Client Install Guides

这份文档提供按客户端划分的安装示例，帮助你把本仓库的技能接入不同 AI 工具。

## 总原则

- `skills/` 是分类源码目录，适用于：
  - `Codex`
  - `Claude Code`
  - `Hermes Agent`
  - 其他按源码浏览技能目录的 AI coding assistants
- `openclaw-skills/` 是扁平导出目录，适用于：
  - `OpenClaw`

如果你不确定，默认先看目标工具是否支持多级目录：

- 支持多级目录：优先 `skills/`
- 只支持一层平铺目录：优先 `openclaw-skills/`

---

## 1. Codex

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

---

## 2. Claude Code

### 推荐目录

- 使用：`skills/`

### 常见接入方式

把本仓库中的 `skills/` 目录纳入 Claude Code 可发现的技能路径即可。  
如果你是通过项目级技能目录管理，可以把所需技能复制或链接到项目技能目录；如果你使用全局技能目录，也可以直接同步过去。

### 建议先试的技能

- `skills/task-understanding-decomposition/brainstorming`
- `skills/developer-engineering/test-driven-development`
- `skills/engineering-workflow-automation/gh-fix-ci`

---

## 3. Hermes Agent

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

## 4. OpenClaw

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

---

## 5. 给 AI 工具的最短安装提示词

如果你希望让 AI 工具自己完成安装，可以先发这一段：

```text
你现在是我的本地安装助手，请把这个仓库 https://github.com/seaworld008/Commonly-used-high-value-skills 里的 Skills 安装到当前 AI 工具中。
```

如果它没有自动识别，再补一句：

```text
当前工具是 <Codex / Claude Code / Hermes Agent / Cursor / OpenClaw>，本地仓库路径是 <你的本地仓库路径>。
```

---

## 6. 维护时推荐顺序

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

## 7. 什么时候该看哪份文档

- 想快速开始：看根目录 `README.md` / `README.en.md`
- 想按客户端接入：看本文件
- 想看治理与维护：看 `docs/repo-maintenance-runbook.md`
- 想看 Hermes 自动开发工作流：看
  - `skills/ai-agent-platform/README.md`
  - `skills/engineering-workflow-automation/README.md`
