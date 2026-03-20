---
name: github
description: '通过 GitHub CLI 自动化 Issue、PR、Review 与 CI 检查，适合工程协作闭环。'
---

# GitHub

当任务涉及 GitHub 仓库协作（Issue/PR/CI/Review）时使用。

## 安装

```bash
npx clawhub@latest install github
```

## 触发场景

- 创建、分配、更新 Issue 与 Milestone
- 批量处理 PR 评论、状态和合并策略
- 读取 CI 失败日志并生成修复清单
- 汇总仓库活动用于周报或复盘

## 推荐流程

1. 明确仓库、分支、目标（如修复 CI 或处理 review）。
2. 拉取当前 PR / Issue / workflow run 的最新状态。
3. 执行动作前先生成变更预览，避免误操作。
4. 执行后回写结果（评论、标签、状态同步）。

## 边界与安全

- 默认最小权限 Token，避免授予多仓库写权限。
- 删除分支、强制推送、批量关闭等高风险操作需二次确认。
