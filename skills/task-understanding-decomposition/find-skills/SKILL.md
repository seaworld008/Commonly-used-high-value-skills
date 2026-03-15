---
name: "find-skills"
description: "让 Agent 自动搜索并安装合适技能，解决不知道该用哪个技能的问题。"
---

# Find Skills

当用户只描述目标、但未指定技能时，优先使用本技能做自动匹配。

## 安装

```bash
npx clawhub@latest install find-skills
```

## 工作方式

1. 根据用户目标生成技能检索词。
2. 在 ClawHub 搜索候选技能并排序。
3. 给出推荐安装顺序与理由。
4. 按确认结果执行安装。
