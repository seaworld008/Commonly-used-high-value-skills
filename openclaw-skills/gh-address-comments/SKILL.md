---
name: gh-address-comments
description: 'Use when addressing GitHub PR review comments or issue comments on the current branch with gh CLI, including auth checks, comment triage, edits, verification, and replies.'
zh_description: "用于通过 gh CLI 处理当前分支的 GitHub PR Review 评论或 Issue 评论。"
version: "1.0.2"
author: "OpenAI contributors; local curators"
source: "https://github.com/openai/skills"
source_url: "https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.curated/gh-address-comments/SKILL.md"
license: "Apache-2.0"
tags: '["address", "automation", "comments", "workflow"]'
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 2
complexity: "intermediate"
metadata:
short-description: Address comments in a GitHub PR review
---

# PR Comment Handler (GitHub CLI)

用于快速定位当前分支对应的 GitHub Pull Request 并自动处理其中的 Review 意见或 Issue 评论。该技能通过 `gh` CLI 工具与 GitHub API 交互，能够读取评论、理解意图、提出修复建议并自动执行代码修改，从而显著加快代码评审的闭环速度。

## 安装与配置

优先复用宿主已有连接或已安装且已授权的 `gh`，按当前任务检查权限。
只有确需缺失依赖、且已有安装/登录授权时才配置；不要因加载技能就安装或扩大 token scope。

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
  3. 从明确 PR URL/base repository 确定归属，读取 reviews 与 reviewThreads；`gh pr view --json reviews` 只提供 reviews，不是全部线程。
  4. `scripts/fetch_comments.py` 当前按 head repository 定位，fork PR 可能取错仓库；顶层分页可能重取已结束 connection，嵌套评论仅 first:100。它的输出不能作为完整评论集。改用独立分页查询：各顶层 connection 分别完成，线程评论也分页；按 ID 去重并核对 pageInfo 与真实终止条件。
- **最佳实践**：优先区分 `General Comment` (全局评论) 和 `Inline Comment` (代码行内评论)，以便精准定位代码行。

### 2. 按授权确定范围 (Clarification)
- **操作步骤**：
  1. 对所有评论进行编号。
  2. 针对每一条评论，评估修复难度和可能的变更方案。
  3. 输出清晰的列表：`[编号] 评论内容 -> 拟修复逻辑`。
  4. 复用用户已指定的评论范围（例如“全部处理”）；只有实质歧义才用宿主实际提供的交互工具澄清，不强制重新选择。
- **最佳实践**：对于不确定的评论，主动询问其语境，避免误改。

### 3. 自动代码修复 (Action)
- **操作步骤**：
  1. 根据 `path` 和 `line` 信息，用宿主可用的读文件能力定位本地源文件。
  2. 利用 LLM 生成修复后的代码块。
  3. 使用 `edit` 或 `apply_patch` 进行局部替换。
- **最佳实践**：在修改后立即运行本地单元测试 `npm test` 或 `pytest` 以验证正确性。

### 4. 状态闭环 (Response)
- **操作步骤**：
  1. 根据已有提交授权决定是否提交；未授权时保留可审查 diff 与验证记录。
  2. 根据已有 push 授权决定是否推送，核对目标分支和最新 head。
  3. 回复与 resolve 是独立远端写操作，各自依已有明确授权执行。普通 PR comment/review comment 不会关闭线程；resolve 需真实 thread ID 和显式 `resolveReviewThread` mutation。
  4. 写入后读取返回值并复查实际评论/`isResolved` 状态；未执行或未证实就报告待处理。
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

### 已授权范围（有实质歧义时才询问）
- [ ] 全部处理
- [ ] 仅处理编号: [ ]
- [ ] 仅生成修复草案，不要执行提交
```

### GitHub CLI 常用操作示例
```bash
# 列出指定 PR 的未解决 review threads；替换 OWNER、REPO 和编号
gh api graphql --paginate -F owner=OWNER -F name=REPO -F number=123 \
  -f query='query($owner: String!, $name: String!, $number: Int!, $endCursor: String) {
    repository(owner: $owner, name: $name) {
      pullRequest(number: $number) {
        reviewThreads(first: 100, after: $endCursor) {
          nodes { id isResolved path line }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  }' --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)'

# 仅在已明确授权外发时发送普通 PR 评论；它不回复某个 inline thread，也不 resolve
gh pr comment 123 --body "Addressing feedback in commit e5f2a1..."
```

`reviews` 与 `reviewThreads` 是不同的数据结构，不能从 review 状态推断
thread 是否已解决。上例只列出 thread 定位信息；读取其评论时继续遵守
对应 connection 的分页。只有用户明确要求发送回复时才运行评论写入命令。

## 进阶应用场景 / Advanced Use Cases

### 1. 自动重构评审
- 评审人提出“这段代码太复杂了，请尝试重构”。先定位具体评审意见，在授权范围内做最小重构并验证；需要总结可复用的经验时，使用 `reflect-learn` 比较改动与回归证据，只有获得对应授权才持久化规则。

### 2. 多 PR 同步更新
- 在 Monorepo 环境中，一个变更可能涉及多个关联 PR。本技能可以跨仓库检索同名分支下的所有评审意见并一并处理。

## 边界与限制 / Boundaries

- **认证权限 (Auth Scopes)**：读取仅需对应读权限；写入仅在授权覆盖时使用所需最小权限。`Forbidden` 先检查目标/权限，不能据此自行登录或扩大授权。
- **行号偏移 (Line Drift)**：如果本地代码在评论发出后已经发生了大幅改动，原始行号可能失效。此时需结合关键词模糊搜索定位。
- **逻辑冲突**：Agent 可能无法完全理解评审人的真实意图（如过于抽象的架构建议），严禁执行任何“猜测性”的大规模重构。
- **网络访问限制**：部分公司内网环境可能屏蔽 GitHub API。
- **并发冲突**：在推送代码前，必须执行 `git pull --rebase` 以防止与他人的并行提交冲突。

## 最佳实践总结

1. **备份第一**：在执行自动化修复前，确保本地 `git status` 干净，方便一键回滚。
2. **渐进式提交**：不要把所有修复塞进一个大 Commit。每一条（或每一组）评论对应一个清晰的 Commit。
3. **人类审核 (Audit)**：推送前，Agent 必须通过 `diff` 展示变更内容。
4. **回复内容**：已有明确外发授权时，以修复证据和 Commit Hash 回复；否则提供待发送草稿。
5. **CI/CD 联动**：在推送后主动提醒用户关注 CI 构建状态，如果失败则自动通过 `gh-fix-ci` 进行修复。
