# 工程工作流自动化 / Workflow Automation

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦 GitHub、浏览器自动化、CI 排障、Playwright 与工程协作自动化。

当前分类共 **9** 个技能。

## 推荐先看

- [jupyter-notebook](./jupyter-notebook/) - Use when the user asks to create, scaffold, or edit Jupyter notebooks (`.ipynb`) for experiments, explorations, or tutorials; prefer the bundled templates and run the helper script `new_notebook.py` to generate a clean starting notebook.
- [playwright](./playwright/) - Use when the task requires automating a real browser from the terminal (navigation, form filling, snapshots, screenshots, data extraction, UI-flow debugging) via `playwright-cli` or the bundled wrapper script.
- [gh-address-comments](./gh-address-comments/) - Help address review/issue comments on the open GitHub PR for the current branch using gh CLI; verify gh auth first and prompt the user to authenticate if not logged in.
- [gh-fix-ci](./gh-fix-ci/) - Use when a user asks to debug or fix failing GitHub PR checks that run in GitHub Actions; use `gh` to inspect checks and logs, summarize failure context, draft a fix plan, and implement only after explicit approval. Treat external providers (for example Buildkite) as out of scope and report only the details URL.

<a id="hermes-graphify-gsd-project-workflow"></a>
## Hermes + graphify + GSD 项目接入工作流

`hermes-graphify-gsd-project-integration` 适合在一个具体仓库中落地 Hermes + graphify + GSD 工作流。它关注的是项目内脚本、项目文档、图谱刷新、规划上下文和可验证的本地操作入口。

### 什么时候使用

- 想给某个仓库添加 `scripts/graphify-sync.sh`。
- 想给某个仓库添加统一入口 `scripts/ai-workflow.sh`。
- 想在 `AGENTS.md` 中告诉未来 AI 助手：先读什么、怎么刷新图谱、哪些目录是本地工作流产物。
- 想在 `README.md` 中给人类开发者写清楚项目级 AI workflow。
- 想把 `.planning/`、`graphify-out/` 等本地产物放进 `.gitignore`。
- 想在改代码前后用 graphify 保持项目架构图谱新鲜。

### 推荐提示词

```text
请使用 hermes-graphify-gsd-project-integration，把当前仓库接入 Hermes + graphify + GSD 工作流。请添加必要脚本、更新 AGENTS.md / README.md / .gitignore，并运行可用的验证命令。
```

### 推荐接入顺序

1. 先确认 Hermes 是用户已经安装好的前置条件。
2. 如果 Hermes 存在，安装或升级 graphify 与 GSD 全局工具链。
3. 审计当前仓库是否已有 `AGENTS.md`、`README.md`、`scripts/`、`.planning/`、`.codex/`、`graphify-out/`。
4. 复用已有脚本；只有缺失时才新增薄脚本层。
5. 添加或更新 `scripts/graphify-sync.sh`，支持 `status`、`smart`、`force`、`serve`。
6. 视项目需要添加 `scripts/ai-workflow.sh`，支持 `doctor`、`context`、`sync`、`force`、`next`。
7. 更新 `AGENTS.md` 和 `README.md`，让 AI 助手和人类开发者都能理解这套流程。
8. 把 `.planning/` 和 `graphify-out/` 加入 `.gitignore`，除非用户明确想提交这些产物。
9. 跑真实命令验证，避免只写文档不验证。

### 可复用文件

| 文件 | 用途 |
|------|------|
| `templates/graphify-sync.sh` | 项目级 graphify 刷新脚本，优先做低成本代码图谱刷新。 |
| `templates/ai-workflow.sh` | 项目级 AI 工作流统一入口。 |
| `templates/agents-section.md` | 可插入项目 `AGENTS.md` 的工作流说明。 |
| `templates/readme-section.md` | 可插入项目 `README.md` 的用户说明。 |
| `templates/bootstrap-toolchain.sh` | 项目接入前的工具链 bootstrap。 |
| `references/integration-checklist.md` | 仓库接入检查清单。 |
| `references/first-install.md` | repo 级首次安装策略。 |

### 常用验证命令

```bash
command -v hermes
hermes --version
command -v graphify
graphify --help
command -v gsd-sdk
gsd-sdk --version
./scripts/graphify-sync.sh status
./scripts/graphify-sync.sh smart
./scripts/ai-workflow.sh doctor
./scripts/ai-workflow.sh context
```

### 和全局工作流技能的关系

推荐顺序是先全局、再项目：

```text
第一步：使用 hermes-graphify-gsd-nonintrusive-workflow，建立非侵入式全局工具链和升级契约。
第二步：进入目标仓库，使用 hermes-graphify-gsd-project-integration，把脚本、文档和验证流程接进去。
```

如果你只想给一个仓库快速接入，也可以直接使用 `hermes-graphify-gsd-project-integration`。它会先检查全局工具链，再处理项目内文件。

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `agent-browser` | 为 Agent 提供真实浏览器自动化能力，支持语义定位、表单交互、截图录屏、脚本执行与会话管理。 | [目录](./agent-browser/) | [SKILL.md](./agent-browser/SKILL.md) |
| `gh-address-comments` | Help address review/issue comments on the open GitHub PR for the current branch using gh CLI; verify gh auth first and prompt the user to authenticate if not logged in. | [目录](./gh-address-comments/) | [SKILL.md](./gh-address-comments/SKILL.md) |
| `gh-fix-ci` | Use when a user asks to debug or fix failing GitHub PR checks that run in GitHub Actions; use `gh` to inspect checks and logs, summarize failure context, draft a fix plan, and implement only after explicit approval. Treat external providers (for example Buildkite) as out of scope and report only the details URL. | [目录](./gh-fix-ci/) | [SKILL.md](./gh-fix-ci/SKILL.md) |
| `github` | 通过 GitHub CLI 自动化 Issue、PR、Review 与 CI 检查，适合工程协作闭环。 | [目录](./github/) | [SKILL.md](./github/SKILL.md) |
| `hermes-graphify-gsd-project-integration` | Use when integrating Hermes Agent, graphify, and GSD into a specific repository, especially for adding project-local graph refresh scripts, AGENTS.md guidance, README workflow docs, gitignore entries, and a brownfield-friendly planning loop without modifying upstream tool repositories. | [目录](./hermes-graphify-gsd-project-integration/) | [SKILL.md](./hermes-graphify-gsd-project-integration/SKILL.md) |
| `jupyter-notebook` | Use when the user asks to create, scaffold, or edit Jupyter notebooks (`.ipynb`) for experiments, explorations, or tutorials; prefer the bundled templates and run the helper script `new_notebook.py` to generate a clean starting notebook. | [目录](./jupyter-notebook/) | [SKILL.md](./jupyter-notebook/SKILL.md) |
| `playwright` | Use when the task requires automating a real browser from the terminal (navigation, form filling, snapshots, screenshots, data extraction, UI-flow debugging) via `playwright-cli` or the bundled wrapper script. | [目录](./playwright/) | [SKILL.md](./playwright/SKILL.md) |
| `web-scraper` | 用于网页数据抓取、结构化提取和反爬策略应对。来源：全网高频推荐。 | [目录](./web-scraper/) | [SKILL.md](./web-scraper/SKILL.md) |
| `yeet` | Use only when the user explicitly asks to stage, commit, push, and open a GitHub pull request in one flow using the GitHub CLI (`gh`). | [目录](./yeet/) | [SKILL.md](./yeet/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
