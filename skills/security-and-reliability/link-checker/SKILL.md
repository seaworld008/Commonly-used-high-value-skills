---
name: link-checker
description: '检测 URL 可达性与潜在风险，识别失效链接、跳转链路和可疑域名。'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["checker", "link", "security"]'
created_at: "2026-03-15"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Link Checker

当任务包含外部链接清单、邮件/文档 URL 安全检查时使用。Link Checker 是一款全方位、多维度的链接健康度与安全性审计工具。它不仅能发现 404 等失效链接，还能深入探测重定向背后的潜在威胁（如钓鱼攻击、恶意软件下载），确保 Agent 与外部互联网交互时的绝对安全。

## 安装

```bash
npx clawhub@latest install link-checker
```

## 触发场景

- **对外发布前检查**：在发布新的文档（Docs）、博客文章（Blog）或落地页（Landing Page）前，确保其中引用的所有内外部链接均为有效且可达。
- **疑似钓鱼链接检测**：在处理邮件或 Slack 消息中的未知 URL 时，利用 Link Checker 进行“先行探测”。
- **SEO 优化与维护**：定期对现有网站进行全量扫描，修复会导致搜索引擎降权的“断链”。
- **审核运营素材**：在广告投放或邮件营销前，核对跳转链路是否正确，避免预算浪费。
- **代码库依赖核对**：检查 `package.json` 或 `README.md` 中引用的项目主页、许可协议链接是否依然有效。

## 核心检查项

- **HTTP 状态码与超时**：识别 404 (Not Found), 403 (Forbidden), 500 (Server Error) 等基本可达性问题。
- **重定向路径分析 (Redirect Chain)**：追踪 301/302 跳数。如果跳转次数超过 5 次，标记为高风险或潜在的重定向循环。
- **协议安全性 (SSL/TLS)**：强制检查是否支持 HTTPS，是否存在证书过期或不安全的 TLS 版本。
- **域名信誉与可疑特征**：检测同形异义词攻击（Homograph Attack，如 `googIe.com` 使用大写 i 代替小写 l）、异常子域名（如 `login.paypal.com.secure-auth.xyz`）。
- **页面内容一致性**：检查最终跳转页面的标题（Title）是否与原始链接描述相符。

## 结果建议

- **阻断 (Block)**：检测到确凿的恶意链接、病毒库匹配项或无法修复的证书错误。
- **人工复核 (Review)**：链接可达但域名信誉低，或重定向到了意外的第三方平台。
- **通过 (Pass)**：链接有效、安全且符合内容上下文。
- **输出修复方案**：若发现 301 永久重定向，自动生成替代的最新 URL。

## 触发条件 / When to Use

- **邮件/文档摘要任务**：当 Agent 准备从某个外部链接提取内容前。
- **安全加固 (Hardening)**：作为 `security-vetter` 或 `input-guard` 的下游技能，对输入流中的 URL 进行清洗。
- **部署前哨 (Pre-deploy)**：集成在 CI/CD 流水线的最后一步。
- **知识库更新 (RAG Maintenance)**：在更新本地 `MEMORY.md` 引用时。
- **大规模网页抓取 (Scraping)**：在启动 `web_scraper` 之前，先批量验证 URL 列表的活性。

## 核心能力 / Core Capabilities

### 1. 深度网络探测 (Network Probing)
- **操作步骤**：
  1. 使用 `HEAD` 请求而非 `GET` 请求（减少流量消耗，隐藏抓取痕迹）。
  2. 设置合理的 `User-Agent`（模拟 Chrome/Safari）以规避反爬策略。
  3. 捕获完整的 HTTP Response Headers，提取 `X-Powered-By` 或 `Server` 字段进行指纹识别。
- **最佳实践**：对于高敏感域名，使用 `Proxy` 模式进行探测，防止本地 IP 泄露。

### 2. 启发式安全扫描 (Heuristic Scanning)
- **操作步骤**：
  1. 拆解 URL 组成部分：Protocol, Subdomain, Domain, TLD, Path, Query Params.
  2. 匹配已知的恶意 TLD 黑名单（如部分免费的 `.tk`, `.ml` 域名）。
  3. 扫描 Query 参数中是否包含疑似 Base64 加密的敏感信息。
- **最佳实践**：对比 `whois` 信息中的域名创建时间，对于刚注册不到 30 天的域名保持警惕。

### 3. 内容一致性对比 (Visual/Textual Validation)
- **操作步骤**：
  1. 调用 `web_fetch` 或 `screenshot` 获取最终页面的快照。
  2. 提取页面关键词，与原始锚点文本（Anchor Text）进行语义匹配。
  3. 如果链接描述是“下载发票”，但最终页面包含“博彩游戏”，立即触发报警。
- **最佳实践**：使用 `image_edit` 技能进行 OCR，识别页面内嵌入的恶意图片文字。

### 4. 自动化报告生成 (Auditing Report)
- **操作步骤**：
  1. 将所有检测结果汇总为 Markdown 表格。
  2. 自动生成修复建议（如：将 `http` 升级为 `https`）。

## 常用命令/模板 / Common Patterns

### 链接审计报告模板 (Link Audit Template)
```markdown
### 🔗 链接审计摘要 (2026-03-27)
- **扫描链接总数**: [25]
- **健康链接**: [20]
- **失效链接**: [2]
- **高风险链接**: [3]

### 🚨 风险项详情
| 原始链接 | 最终跳转 | 风险点 | 建议 |
| :--- | :--- | :--- | :--- |
| `http://old.com/doc` | `https://new.com/doc` | 协议不安全 | 升级为 HTTPS |
| `https://bit.ly/3xyz` | `https://suspect.xyz/login` | 隐藏跳转/钓鱼风险 | **严禁访问** |
| `https://broken.link` | - | 404 Not Found | 移除或替换 |

### 🛠️ 自动生成的修复建议
1. 在 `README.md` 第 45 行，替换 `old-url` 为 `new-url`。
2. 移除 `sidebar.md` 中的所有失效导航链接。
```

### 快速扫描示例
```javascript
// 示例：检查给定文本中的所有链接
mcp_call({
  name: 'audit_links_in_text',
  arguments: {
    text: "Please check this doc: https://example.com and the tool: http://unsafe.net",
    deep_scan: true
  }
});
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动化防钓鱼网关
- Agent 监听 Slack 频道。每当有外来人员发布包含 URL 的消息时，Link Checker 自动进行隐形探测，并以 Thread 回复的形式告知全组人员该链接是否安全。

### 2. 内容资产自愈 (Self-healing Content)
- 每月自动扫描 Notion 知识库。发现失效链接后，Agent 自动通过 `tavily-search` 寻找该资源的新位置并自动更新页面。

## 边界与限制 / Boundaries

- **反爬墙拦截**：部分网站（如 LinkedIn, Facebook）对 HEAD 请求极其敏感，可能直接返回 403 导致误报。
- **JavaScript 渲染依赖**：部分链接需要执行 JS 才能完成跳转（如部分短链服务），单纯的 HTTP 请求无法探测。需配合 `agent-browser` 使用。
- **地理位置差异**：部分链接在不同国家的可达性不同（如全球分发的 CDN 或特定地区的墙）。
- **动态链接 (Dynamic URLs)**：带有时效性 Token 或仅限特定 Session 访问的链接，Link Checker 无法进行有效探测。
- **隐私边界**：不得对需要登录凭证的私密链接进行扫描，除非已获得明确授权。

## 最佳实践总结

1. ** HEAD 优先**：永远先尝试 HEAD 请求以节省带宽。
2. **记录重定向流**：不要只看终点，要看路上的每一个站点。
3. **设置合理的 Timeout**：针对不同地区的域名设置差异化的超时阈值（通常 5-15 秒）。
4. **多源验证**：集成 `VirusTotal` 或 `Google Safe Browsing` API 以增强安全性判定。
5. **记忆持久化**：将已验证安全的白名单域名存入 `MEMORY.md`。
