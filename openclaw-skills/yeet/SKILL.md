---
name: yeet
description: 'Use only when the user explicitly asks to stage, commit, push, and open a GitHub pull request in one flow using the GitHub CLI (`gh`).'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["automation", "workflow", "yeet"]'
created_at: "2026-03-04"
updated_at: "2026-03-20"
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
- 如果未登录，执行 `gh auth login`。

## 命名规范 (Naming Conventions)

- **分支 (Branch)**：如果当前在 `main`/`master`，自动创建 `codex/{feature-description}`。
- **提交 (Commit)**：遵循 Conventional Commits（如 `feat: add auth` 或 `fix: resolve race condition`）。
- **PR 标题**：`[codex] {description}`，需简明扼要概括全量 Diff。

## 触发条件 / When to Use

- **功能开发闭环**：当用户说“帮我提交这些改动并开个 PR”时。
- **紧急修复 (Hotfix)**：需要以最快速度将补丁推送到上游分支进行 CI 验证。
- **文档零碎更新**：修改了 README 或注释，不需要复杂的评审流程。
- **多仓库协同**：在一个 Monorepo 的多个子包中同步执行 Yeet。
- **代码重构后**：当重构规模大但逻辑变动小时，使用 Yeet 快速建立基准。

## 核心能力 / Core Capabilities

### 1. 智能分支与环境感知 (Environment Sensing)
- **操作步骤**：
  1. 运行 `git status -sb` 检查当前状态是否干净。
  2. 获取默认分支名称（通常为 `main` 或 `master`）。
  3. 若在默认分支，基于 `description` 生成合规的分支名并切出：`git checkout -b "codex/$(echo $DESC | slugify)"`。
- **最佳实践**：分支名应尽可能短小（Slugified），避免包含空格或特殊字符。

### 2. 自动化变更打包 (Atomic Staging)
- **操作步骤**：
  1. 运行 `git add -A` 或针对特定目录 `git add src/`。
  2. 结合 `git diff --cached --stat` 预览待提交的内容，防止误传大文件。
- **最佳实践**：如果发现敏感文件（如 `.env`），Agent 应自动发出警报并中止 Yeet。

### 3. CI 预检与健壮性保障 (Pre-push Checks)
- **操作步骤**：
  1. 尝试运行本地定义的检查脚本（如 `npm run lint` 或 `go test ./...`）。
  2. 若检查失败，Agent 尝试自动修复（例如运行 `prettier --write`）并重新运行。
- **最佳实践**：如果本地环境缺失工具链，Agent 应尝试一次性安装依赖。

### 4. 幂等推送与冲突处理 (Robust Push)
- **操作步骤**：
  1. 执行带有跟踪信息的推送：`git push -u origin $(git branch --show-current)`。
  2. 若因上游领先导致推送失败，执行 `git pull --rebase` 并重新推送。
- **最佳实践**：在极少数情况下使用 `--force-with-lease`，但必须在 PR 描述中注明。

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
# 生成临时 Body 文件并创建 PR
echo "## Summary\n$(git log -1 --pretty=%B)" > /tmp/pr-body.md
gh pr create --title "[codex] feature-x" --body-file /tmp/pr-body.md --draft
```

## 进阶应用场景 / Advanced Use Cases

### 1. 无缝集成 CI 修复 (Auto-Fixer)
- 当 `gh-fix-ci` 技能发现错误并修复后，自动衔接 `yeet` 技能，将修复代码推回 PR。

### 2. 定期代码同步 (Sync Upstream)
- 使用 `cron` 技能，每周五下午自动将本地所有的 WIP (Work In Progress) 分支执行一次 Yeet 到远程备份。

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
4. **清理临时文件**：Yeet 结束后，自动删除生成的 `/tmp/pr-body.md` 等中间文件。
5. **状态反馈**：任务完成时，Agent 必须返回 PR 的 Web URL 链接。
6. **防误操作**：如果检测到改动超过 100 个文件，必须强制进行二次确认。
