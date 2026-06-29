---
name: github
description: 'Use when automating GitHub issues, pull requests, reviews, CI checks, labels, releases, or engineering collaboration loops through the GitHub CLI.'
zh_description: "用于通过 GitHub CLI 自动化 Issue、PR、Review、CI 检查、标签和发布协作。"
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["automation", "github", "workflow"]'
created_at: "2026-03-15"
updated_at: "2026-06-29"
quality: 2
complexity: "intermediate"
---

# GitHub

当任务涉及 GitHub 仓库协作（Issue/PR/CI/Review）时使用。GitHub 技能是连接本地代码环境与远程协作平台的桥梁，它通过封装 `gh` CLI 工具，使 Agent 能够执行从“创建 Issue 跟踪 Bug”到“合并经过评审的 PR”全生命周期的自动化管理。

## 安装

```bash
npx clawhub@latest install github
```

## 触发场景

- **创建、分配、更新 Issue 与 Milestone**：快速将用户提出的功能点转化为可跟踪的条目。
- **批量处理 PR 评论、状态和合并策略**：在多人评审的大型 PR 中，自动汇总反馈并提交合并请求。
- **读取 CI 失败日志并生成修复清单**：当 GitHub Actions 运行失败时，自动拉取日志并利用 `gh-fix-ci` 技能进行修复。
- **汇总仓库活动用于周报或复盘**：从 `gh pr list` 和 `gh issue list` 中提取数据，生成具有洞察力的协作报告。
- **发布管理 (Releases)**：自动生成 Release Note 并发布新的版本包。
- **权限与项目维护**：管理 Repo 的 Labels, Topics 以及 Collaborators。

## 推荐流程

1. **环境准备 (Setup)**：明确目标仓库（Owner/Repo）、当前分支、目标（如修复 CI 或处理 Review）。
2. **状态感知 (Sensing)**：拉取当前 PR / Issue / Workflow Run 的最新元数据。
3. **策略生成 (Planning)**：执行动作前先生成“变更预览”（Preview），描述将要修改的标签、关闭的 Issue 或触发的 Action，避免大规模误操作。
4. **动作执行 (Execution)**：调用 `gh` 指令执行具体动作。
5. **状态同步 (Sync)**：执行后回写结果（如回复评论、添加标签、同步状态到 `MEMORY.md`）。

### 本机 `gh` 认证优先

在任何 GitHub 自动化前，先执行：

```bash
gh auth status
```

如果仓库脚本需要 GitHub API，但环境里没有显式的 `GITHUB_TOKEN` / `GH_TOKEN`，优先复用本机 `gh auth token`，而不是直接走未认证请求。这样可以显著减少：

- `401 Unauthorized`
- 过早触发的 API rate limit
- 因匿名搜索受限导致的“误以为没有更新”

## 触发条件 / When to Use

- **代码提交前夕**：需要创建 PR 以启动团队评审。
- **CI/CD 构建失败**：当 GitHub Actions 报错时，Agent 自动响应。
- **团队协作同步**：需要快速查看当前仓库中有哪些 `Unresolved` 的 Issue。
- **发布周期点**：需要从 Git Commits 中提取变更日志（Changelog）并创建 Release。
- **安全审计**：定期扫描仓库的 Dependabot 警告并尝试自动修复。

## 核心能力 / Core Capabilities

### 1. 深度 Issue 管理 (Issue Lifecycle)
- **操作步骤**：
  1. 使用 `gh issue create` 创建结构化 Issue。
  2. 使用 `gh issue edit` 增加标签（Label）、里程碑（Milestone）和受指派人（Assignee）。
  3. 通过 `gh issue comment` 与协作者进行交互。
- **最佳实践**：为每一类 Issue 设计标准的模板（Bug Report, Feature Request），提高沟通效率。

### 2. PR 全链路自动化 (Pull Request Mastery)
- **操作步骤**：
  1. 创建 PR：`gh pr create --fill --draft`。
  2. 读取 Review 建议：`gh pr view --json reviews`。
  3. 执行合并：`gh pr merge --auto --squash`。
- **最佳实践**：在合并前，先运行 `gh pr checks` 确保所有的 CI 检查项均已通过。

### 3. Workflow 与 CI/CD 故障排查 (Actions/Workflow)
- **操作步骤**：
  1. 列出最近的运行记录：`gh run list --limit 5`。
  2. 如果失败，下载日志：`gh run view <run_id> --log`。
  3. 分析报错日志，定位到具体的 Step 和文件行号。
- **最佳实践**：结合 `tavily-search` 技能，搜索该报错日志在 StackOverflow 上的典型解决方案。

### 4. 仓库级数据汇总 (Activity Analytics)
- **操作步骤**：
  1. 使用 `gh api` 调用更底层的 GraphQL 或 REST API 获取历史统计数据。
  2. 统计 PR 合并周期（Lead Time）、Issue 关闭率等指标。

### 5. 周期性仓库维护 (Recurring Maintenance)

- 先 `git fetch origin --prune`，再做 discovery / upstream sync。
- 如果同时存在“小而确定的修复”和“大批量同步”，拆成两个 `codex/` 分支与两个 PR。
- 先合并聚焦 PR，再合并批量同步 PR，避免回滚时把不相关内容绑在一起。
- 对 warning 做分类：仓库质量回归要当场修，外部 API `403` / 上游路径 `404` 要单独记录并在 PR 里说明。

## 常用命令/模板 / Common Patterns

### 自动 Issue 转换模板 (Issue from Discussion)
```markdown
### 🚀 识别到的任务
- **标题**: [Feature] 支持 OAuth2 登录
- **标签**: `enhancement`, `high-priority`
- **里程碑**: `v2.0-Alpha`
- **描述**: 根据本轮 Slack 讨论，我们需要引入 Google 和 GitHub 的第三方授权登录。

### 执行的 CLI 命令
`gh issue create --title "[Feature] 支持 OAuth2 登录" --label enhancement --milestone v2.0-Alpha --body "..."`
```

### CI 修复辅助示例 (CLI)
```bash
# 查看最近一次失败的 workflow 详情并输出日志到 temp 文件
RUN_ID=$(gh run list --status failure --limit 1 --json databaseId -q '.[0].databaseId')
gh run view $RUN_ID --log > /tmp/ci-failure.log
```

## 进阶应用场景 / Advanced Use Cases

### 1. “无人值守”依赖升级
- Agent 定期运行 `gh-address-comments` 和 `github` 技能。当发现有 Dependabot 的 PR 时，自动运行测试，若通过则自动执行 `gh pr merge --squash`。

### 2. 跨仓库权限同步
- 在一个企业组织下，Agent 自动将所有符合特定 Topic 的仓库权限配置为统一的“开发小组可见”。

## 边界与限制 / Boundaries

- **认证安全 (Auth Scopes)**：默认使用最小权限 Token。严禁在非受信任环境中显式导出 `GITHUB_TOKEN` 环境变量。
- **破坏性操作红线**：删除分支、强制推送 (`--force`)、删除 Release 或批量关闭 Issue 必须经过人类二次确认。
- **API 速率限制 (Rate Limiting)**：短时间内大规模调用 `gh api` 或 `gh search` 可能触发 GitHub 的 Secondary Rate Limit。
- **告警解释**：不要把匿名 API 的 `401`、上游 fallback 探测时的中间 `404`、或短时网络故障误报成“仓库本身异常”；这类告警要和真实仓库回归分开汇报。
- **合并冲突 (Conflicts)**：GitHub CLI 无法直接处理复杂的代码行冲突，此时必须回退到本地 `git` 环境进行人工 rebase。
- **Workflow 自定义权限**：部分 Repo 限制了通过 CLI 触发 Actions 的权限。

## 最佳实践总结

1. **预览第一**：所有的 `gh` 变更动作必须先生成 Preview，告知用户“我将要在 GitHub 上执行什么”。
2. **两阶段提交**：特别是 `merge` 和 `delete` 动作，必须分两步确认。
3. **记忆化协作**：重要的 Issue ID 或 PR 链接同步到 `MEMORY.md` 以便后续引用。
4. **自动化与人工的边界**：代码审查（Review）建议主要由 LLM 提供参考，但最终的 `Approve` 动作应由人类执行。
5. **日志可追溯**：记录每一次 `gh` 操作的输出，方便事后审计。
6. **模板化管理**：充分利用 GitHub 仓库自带的 `.github/ISSUE_TEMPLATE` 提高规范度。
7. **分阶段合并**：周期性维护优先拆成“聚焦修复 PR”和“批量同步 PR”，降低审查与回滚成本。
