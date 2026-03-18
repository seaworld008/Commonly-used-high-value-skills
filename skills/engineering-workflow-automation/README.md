# 工程工作流自动化 / Workflow Automation

> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.

聚焦 GitHub、浏览器自动化、CI 排障、Playwright 与工程协作自动化。

当前分类共 **7** 个技能。

## 推荐先看

- [jupyter-notebook](./jupyter-notebook/) - Use when the user asks to create, scaffold, or edit Jupyter notebooks (`.ipynb`) for experiments, explorations, or tutorials; prefer the bundled templates and run the helper script `new_notebook.py` to generate a clean starting notebook.
- [playwright](./playwright/) - Use when the task requires automating a real browser from the terminal (navigation, form filling, snapshots, screenshots, data extraction, UI-flow debugging) via `playwright-cli` or the bundled wrapper script.
- [gh-address-comments](./gh-address-comments/) - Help address review/issue comments on the open GitHub PR for the current branch using gh CLI; verify gh auth first and prompt the user to authenticate if not logged in.
- [gh-fix-ci](./gh-fix-ci/) - Use when a user asks to debug or fix failing GitHub PR checks that run in GitHub Actions; use `gh` to inspect checks and logs, summarize failure context, draft a fix plan, and implement only after explicit approval. Treat external providers (for example Buildkite) as out of scope and report only the details URL.

## 技能总览

| 技能 | 简介 | 目录 | 详情 |
|------|------|------|------|
| `agent-browser` | 为 Agent 提供真实浏览器自动化能力，支持语义定位、表单交互、截图录屏、脚本执行与会话管理。 | [目录](./agent-browser/) | [SKILL.md](./agent-browser/SKILL.md) |
| `gh-address-comments` | Help address review/issue comments on the open GitHub PR for the current branch using gh CLI; verify gh auth first and prompt the user to authenticate if not logged in. | [目录](./gh-address-comments/) | [SKILL.md](./gh-address-comments/SKILL.md) |
| `gh-fix-ci` | Use when a user asks to debug or fix failing GitHub PR checks that run in GitHub Actions; use `gh` to inspect checks and logs, summarize failure context, draft a fix plan, and implement only after explicit approval. Treat external providers (for example Buildkite) as out of scope and report only the details URL. | [目录](./gh-fix-ci/) | [SKILL.md](./gh-fix-ci/SKILL.md) |
| `github` | 通过 GitHub CLI 自动化 Issue、PR、Review 与 CI 检查，适合工程协作闭环。 | [目录](./github/) | [SKILL.md](./github/SKILL.md) |
| `jupyter-notebook` | Use when the user asks to create, scaffold, or edit Jupyter notebooks (`.ipynb`) for experiments, explorations, or tutorials; prefer the bundled templates and run the helper script `new_notebook.py` to generate a clean starting notebook. | [目录](./jupyter-notebook/) | [SKILL.md](./jupyter-notebook/SKILL.md) |
| `playwright` | Use when the task requires automating a real browser from the terminal (navigation, form filling, snapshots, screenshots, data extraction, UI-flow debugging) via `playwright-cli` or the bundled wrapper script. | [目录](./playwright/) | [SKILL.md](./playwright/SKILL.md) |
| `yeet` | Use only when the user explicitly asks to stage, commit, push, and open a GitHub pull request in one flow using the GitHub CLI (`gh`). | [目录](./yeet/) | [SKILL.md](./yeet/SKILL.md) |

## 维护方式

- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。
- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。
- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`
