---
name: link-checker
description: '检测 URL 可达性与潜在风险，识别失效链接、跳转链路和可疑域名。'
---

# Link Checker

当任务包含外部链接清单、邮件/文档 URL 安全检查时使用。

## 安装

```bash
npx clawhub@latest install link-checker
```

## 触发场景

- 对外发布前检查文档/落地页链接有效性
- 检测疑似钓鱼或异常跳转链接
- 审核邮件、运营素材中的 URL 风险

## 核心检查项

- HTTP 状态码与超时
- 重定向次数与最终落地域名
- 协议安全性（HTTP/HTTPS）
- 域名可疑特征（拼写欺骗、异常子域）

## 结果建议

- 按风险分级：阻断 / 人工复核 / 通过
- 输出替代链接或修复建议
