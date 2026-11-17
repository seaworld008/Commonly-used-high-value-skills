---
name: yeet
description: 'Use only when the user explicitly asks to stage, commit, push, and open a GitHub pull request in one flow using the GitHub CLI (`gh`).'
zh_description: "按用户要求暂存、提交、推送改动并创建 GitHub PR。"
version: "1.0.2"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["automation", "workflow", "yeet"]'
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 2
complexity: "intermediate"
---

# Yeet (The Ultimate Git Flow)

"Yeet" 是一种极致效率的开发哲学：当一项修改已经完成并通过验证，无需反复确认，直接执行“暂存 -> 提交 -> 推送 -> 创建 PR”的一键流水线。本技能通过 `gh` CLI 和原生 `git` 命令，帮助开发者在秒级完成从本地代码到 GitHub 评审页面的流转。

## 安装与前提条件

```bash
# 确保已安装 GitHub CLI
gh --version
# 验证登录状态与权限 (repo, workflow)
gh auth status
```

- 如果 `gh` 缺失，Agent 应主动提示用户安装。
- 如果未登录，报告连接状态；仅在已有配置授权下，使用宿主支持的可信本地登录流程。

## 命名规范 (Naming Conventions)

- **分支 (Branch)**：如果当前在 `main`/`master`，自动创建 `codex/{feature-description}`。
- **提交 (Commit)**：遵循 Conventional Commits（如 `feat: add auth` 或 `fix: resolve race condition`）。
- **PR 标题**：`[codex] {description}`，需简明扼要概括全量 Diff。

## 触发条件 / When to Use

- 用户明确要求将本次指定改动暂存、提交、推送并创建 PR 时使用。
- 修复、文档更新、重构或多包改动本身不构成发布授权；按已有请求确定仓库、文件和目标分支。

## 核心能力 / Core Capabilities

### 1. 智能分支与环境感知 (Environment Sensing)
- **操作步骤**：
  1. 运行 `git status -sb` 检查当前状态是否干净。
  2. 获取默认分支名称（通常为 `main` 或 `master`）。
  3. 若在默认分支，按仓库约定生成简短分支名并切出，例如 `git checkout -b codex/fix-login-typo`；不依赖额外的 `slugify` 工具。
- **最佳实践**：分支名应尽可能短小（Slugified），避免包含空格或特殊字符。

### 2. 自动化变更打包 (Atomic Staging)
- **操作步骤**：
  1. 用 `git diff` 和 `git diff --cached` 检查未暂存与已暂存改动，区分本次范围与其他工作。
  2. 按明确路径暂存，例如 `git add -- src/auth.py`，再检查 `git diff --cached` 及其统计；已有无关暂存不得混入提交。
- **最佳实践**：如果发现敏感文件（如 `.env`），Agent 应自动发出警报并中止 Yeet。

### 3. CI 预检与健壮性保障 (Pre-push Checks)
- **操作步骤**：
  1. 尝试运行本地定义的检查脚本（如 `npm run lint` 或 `go test ./...`）。
  2. 若检查失败，Agent 尝试自动修复（例如运行 `prettier --write`）并重新运行。
- **最佳实践**：若缺少工具链，先报告缺失项；只有现有授权包含安装时才安装，并记录未运行的检查。

### 4. 幂等推送与冲突处理 (Robust Push)
- **操作步骤**：
  1. 执行带有跟踪信息的推送：`git push -u origin $(git branch --show-current)`。
  2. 若远端领先或发生分叉，先核实远端变化与本次授权，再按仓库约定整合并重新验证。
- **最佳实践**：改写远端历史须在明确授权范围内；PR 描述不能代替授权，普通推送失败不自动转为强推。

### 5. 语义化 PR 描述生成 (Rich PR Content)
- **操作步骤**：
  1. 提取全量 Diff 摘要。
  2. 自动生成 Markdown 格式的 PR Body，包含：背景、根本原因、修复方案、测试证明。
  3. 使用 `gh pr create --draft --fill` 创建 PR。
- **最佳实践**：将 PR 设为 `Draft` (草稿) 状态，给用户最后一次人工复核的机会。

## 常用命令/模板 / Common Patterns

### 一键 Yeet 完整流 (Full Flow Template)
```markdown
### 🚀 Yeet 开始执行
1. **[Branch]**: 从 `main` 切换到 `codex/fix-login-typo`。
2. **[Stage]**: 暂存 `src/auth.py` 的改动。
3. **[Commit]**: `fix: correct typo in login error message`。
4. **[Pre-Check]**: 运行 `pytest` ... **PASSED**.
5. **[Push]**: 推送至 `origin/codex/fix-login-typo`。
6. **[PR]**: 创建 PR #456 并生成描述。

### 📄 自动生成的 PR Body 预览
> **Title**: [codex] fix login typo
> **Description**: This PR addresses a UI issue where the error message showed 'Invalid credentails'.
> **Root Cause**: Spelling error in string literal.
> **Fix**: Updated L45 in `auth.py`.
> **Tests**: Ran unit tests and verified manually.
```

### 快速创建 PR 示例 (CLI)
```bash
# 在任务专用临时目录创建唯一文件；填入已核实的描述
pr_body=$(mktemp -p "$TMPDIR" pr-body.XXXXXX)
printf '%s\n' '## Summary' '本次改动及验证结果' > "$pr_body"
gh pr create --title "[codex] feature-x" --body-file "$pr_body" --draft
rm -- "$pr_body"
```

## 进阶应用场景 / Advanced Use Cases

### 1. 无缝集成 CI 修复 (Auto-Fixer)
- 当 `gh-fix-ci` 修复已验证，且本次授权包含发布修复时，衔接 `yeet` 将指定改动推回 PR。

后续定时发布属于独立任务，不能由本次 PR 发布请求推导。

## 边界与限制 / Boundaries

- **认证安全**：Yeet 严重依赖 `gh` 和 `git` 的本地配置。如果环境不安全，严禁在包含明文密钥的项目中使用。
- **合并冲突 (Merge Conflicts)**：在 `rebase` 过程中如果遇到复杂冲突，Yeet 流程必须停止，交给人类解决。
- **Commit History 污染**：Yeet 倾向于“单次大提交”，对于要求原子提交（Atomic Commits）的严苛项目，建议在 PR 评审阶段进行 Squash。
- **权限限制**：用户可能对该仓库没有 `Push` 权限（如 Fork 的原始库），此时应提醒用户进行 Fork 或推送到自己的仓库。
- **构建开销**：如果本地 `pre-push` 检查非常耗时（如编译 C++ 项目），Yeet 会显著变慢。

## 最佳实践总结

1. **预览第一**：在 `git add` 后，Agent 必须打印出变更文件的列表。
2. **Body 为王**：PR 描述质量直接决定了评审速度，必须通过 LLM 生成高质量的 Prose。
3. **追踪日志**：在 Yeet 执行过程中，所有命令输出必须可见，方便排查。
4. **清理临时文件**：Yeet 结束后，仅删除本次创建的唯一临时文件，不清理共享路径或其他任务文件。
5. **状态反馈**：任务完成时，Agent 必须返回 PR 的 Web URL 链接。
6. **范围核对**：文件数量较多时核对任务清单和差异；已有发布授权内可直接完成，只有混入无关工作或需要扩大范围时才澄清。
