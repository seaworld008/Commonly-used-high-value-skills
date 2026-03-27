---
name: gh-address-comments
description: 'Help address review/issue comments on the open GitHub PR for the current branch using gh CLI; verify gh auth first and prompt the user to authenticate if not logged in.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["address", "automation", "comments", "workflow"]'
created_at: "2026-03-04"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
metadata: 
short-description: Address comments in a GitHub PR review
---

# PR Comment Handler (GitHub CLI)

用于快速定位当前分支对应的 GitHub Pull Request 并自动处理其中的 Review 意见或 Issue 评论。该技能通过 `gh` CLI 工具与 GitHub API 交互，能够读取评论、理解意图、提出修复建议并自动执行代码修改，从而显著加快代码评审的闭环速度。

## 安装与配置

```bash
# 确保已安装 GitHub CLI
brew install gh
# 登录并授权相关权限 (repo, read:org, workflow)
gh auth login
```

## 触发条件 / When to Use

- **PR 进入反馈阶段**：在 CI/CD 完成后，评审人提出了若干修改建议。
- **批量处理琐碎反馈**：如拼写错误、变量重命名、代码风格调整等无需深度逻辑讨论的评论。
- **远程协作同步**：当多个团队成员在同一个 PR 下进行异步讨论，需要快速汇总并执行共识。
- **遗留 PR 清理**：针对已经开启多日但未合入的 PR，自动检索所有未解决（Unresolved）的对话。
- **自动化测试失败复盘**：如果评审人指出了测试用例的覆盖不足，Agent 自动根据评论补充测试代码。

## 核心能力 / Core Capabilities

### 1. 评论提取与语义分类 (Observation)
- **操作步骤**：
  1. 验证当前分支：`git branch --show-current`。
  2. 获取 PR 编号：`gh pr view --json number,url`。
  3. 读取所有 Review 线程：`gh pr view --json reviews` 或运行自定义脚本 `fetch_comments.py`。
- **最佳实践**：优先区分 `General Comment` (全局评论) 和 `Inline Comment` (代码行内评论)，以便精准定位代码行。

### 2. 交互式任务确认 (Clarification)
- **操作步骤**：
  1. 对所有评论进行编号。
  2. 针对每一条评论，评估修复难度和可能的变更方案。
  3. 输出清晰的列表：`[编号] 评论内容 -> 拟修复逻辑`。
  4. 使用 `question` 工具等待用户确认：“请问需要处理哪些编号的评论？”
- **最佳实践**：对于不确定的评论，主动询问其语境，避免误改。

### 3. 自动代码修复 (Action)
- **操作步骤**：
  1. 根据 `path` 和 `line` 信息，使用 `read` 工具定位本地源文件。
  2. 利用 LLM 生成修复后的代码块。
  3. 使用 `edit` 或 `apply_patch` 进行局部替换。
- **最佳实践**：在修改后立即运行本地单元测试 `npm test` 或 `pytest` 以验证正确性。

### 4. 状态闭环 (Response)
- **操作步骤**：
  1. 提交修复代码：`git commit -m "docs/refactor: address PR review comments"`。
  2. 推送代码：`git push origin HEAD`。
  3. 自动回复评论并标记为 `Resolved`：`gh pr review --comment "Fixed as per review" <pr_id>`。
- **最佳实践**：在回复中引用具体的 Commit Hash，方便评审人追溯。

## 常用命令/模板 / Common Patterns

### PR 反馈处理清单模板 (Feedback Checklist)
```markdown
### PR 概览
- **PR 链接**: [https://github.com/org/repo/pull/123]
- **当前状态**: `Changes Requested`

### 待处理评论汇总 (Pending Comments)
1. **[L154, auth.py]**: "Consider using a more secure hashing algorithm."
   - **拟修复**: 切换 `md5` 为 `sha256`。
2. **[L20, styles.css]**: "Hardcoded hex color should be a theme variable."
   - **拟修复**: 替换 `#FFF` 为 `var(--bg-primary)`。

### 您的选择
- [ ] 全部处理
- [ ] 仅处理编号: [ ]
- [ ] 仅生成修复草案，不要执行提交
```

### GitHub CLI 常用操作示例
```bash
# 获取当前 PR 的所有未解决对话 (需配合 jq)
gh pr view --json reviews | jq '.reviews[].comments[] | select(.state != "RESOLVED")'

# 对特定 PR 提交修复后的 Review 回复
gh pr comment 123 --body "Addressing feedback in commit e5f2a1..."
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动重构评审
- 评审人提出“这段代码太复杂了，请尝试重构”。Agent 利用 `gh-address-comments` 结合 `self-improving-agent` 逻辑，自动提取复杂函数并尝试多种解构方案。

### 2. 多 PR 同步更新
- 在 Monorepo 环境中，一个变更可能涉及多个关联 PR。本技能可以跨仓库检索同名分支下的所有评审意见并一并处理。

## 边界与限制 / Boundaries

- **认证权限 (Auth Scopes)**：必须确保 `gh` 具备 `write` 权限。如果遇到 `Forbidden` 错误，需重新运行 `gh auth login`。
- **行号偏移 (Line Drift)**：如果本地代码在评论发出后已经发生了大幅改动，原始行号可能失效。此时需结合关键词模糊搜索定位。
- **逻辑冲突**：Agent 可能无法完全理解评审人的真实意图（如过于抽象的架构建议），严禁执行任何“猜测性”的大规模重构。
- **网络访问限制**：部分公司内网环境可能屏蔽 GitHub API。
- **并发冲突**：在推送代码前，必须执行 `git pull --rebase` 以防止与他人的并行提交冲突。

## 最佳实践总结

1. **备份第一**：在执行自动化修复前，确保本地 `git status` 干净，方便一键回滚。
2. **渐进式提交**：不要把所有修复塞进一个大 Commit。每一条（或每一组）评论对应一个清晰的 Commit。
3. **人类审核 (Audit)**：推送前，Agent 必须通过 `diff` 展示变更内容。
4. **礼貌回复**：处理完评论后，自动感谢评审人的建议，保持良好的开源协作文化。
5. **CI/CD 联动**：在推送后主动提醒用户关注 CI 构建状态，如果失败则自动通过 `gh-fix-ci` 进行修复。
