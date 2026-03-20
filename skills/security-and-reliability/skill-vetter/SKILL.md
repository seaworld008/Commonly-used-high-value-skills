---
name: skill-vetter
description: '在安装前审计技能安全性，识别恶意指令、越权行为与高风险配置。'
---

# Skill Vetter

建议在安装社区技能前优先执行本技能，作为安全前置检查。

## 安装

```bash
npx clawhub@latest install skill-vetter
```

## 核心能力

- 检测潜在恶意/可疑指令
- 识别高风险权限与外部依赖
- 输出风险等级与处置建议
