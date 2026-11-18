---
name: link-checker
description: 'Use when checking URL availability, dead links, redirect chains, suspicious domains, documentation link health, or link-risk evidence before publishing.'
zh_description: "检测 URL 可达性、失效链接、跳转链路、可疑域名和文档链接健康度。"
version: "1.1.1"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: ["checker", "link", "security"]
created_at: "2026-03-15"
updated_at: "2026-11-17"
quality: 3
complexity: "intermediate"
---

# Link Checker

检查文档、网页、邮件或代码仓库中的链接是否可达、跳向何处、是否可疑，并输出可复查的证据。
本技能使用真实的 HTTP 工具（`curl`、已安装时的 `lychee`）和人工判断；不提供独立的
链接信誉数据库，也不能证明某个链接“绝对安全”。

## 触发条件 / When to Use

- 发布文档、博客、落地页或 README 前，检查内外部链接是否失效。
- 处理邮件、聊天或工单中的陌生 URL，需要在打开或抓取前评估风险。
- 迁移站点或改版后，确认旧链接的重定向是否正确。
- 抓取或 RAG 入库前，批量验证 URL 列表的活性。

不适用：渗透测试或扫描非授权目标；需要登录态的私有页面（除非用户提供授权的测试账号）。

## 工作流程 / Workflow

### 1. 提取链接

```bash
# Markdown / HTML / 源码中的绝对 URL，去重后保存
rg -o --no-filename 'https?://[^\s)"'"'"'<>\]]+' docs/ README.md | sort -u > urls.txt
wc -l urls.txt
```

相对链接和锚点（`./guide.md#install`）按仓库文件结构检查：目标文件存在、锚点对应的标题存在。

### 2. 检查可达性与跳转链

脚本 `scripts/check_links.py` 提取绝对 URL，可输出逐跳状态、最终地址和风险提示。同主机重定向会逐跳校验，跨主机时停止并标记复核；HEAD 返回 403、405 或 501 时可回退 GET。每个实际请求（含跳转和回退）都按目标主机限速。
先用 `--list-only` 列清单。无法确认网络授权时只交付清单。需要限定目标时，对每次请求先核对协议、主机和路径，并按实际目标主机限速。
脚本可标记 `plain-http`、`shortener`、`punycode`、`cross-domain-redirect`、`permanent-redirect`、`long-redirect-chain` 和 `executable-download`。JSON 包含各跳状态，默认 TSV 汇总首尾地址与提示。
```bash
python3 scripts/check_links.py --list-only README.md docs/*.md   # 只列出 URL，不发请求
# 在已授权的网络范围内检查；跨主机跳转由结果列出待复核：
python3 scripts/check_links.py --json --timeout 10 --delay 1 README.md
```

对范围受限的检查，一次只取已核准 URL 的响应头：

```bash
curl -q --proto '=http,https' --head --silent --show-error --max-time 15 \
  "https://example.com/doc"
```

- 遇到 3xx，把 Location 相对当前地址解析成完整 URL，先验证协议、目标和授权范围，再决定是否请求下一跳。目标超出范围时记录 Location 并停止。
- HEAD 被拒且允许回退时，对同一已核准 URL 延时后单次 GET，丢弃正文。每跳沿用相同核验和限速规则。
- 使用工具默认或明确标识自身的 User-Agent；不要伪装浏览器绕过站点的访问控制或反爬策略。
- 遵守站点速率限制，对同一域名保持低并发；收到 429 时退避重试一次，仍失败则记为“受限”。

### 3. 识别可疑特征

| 信号 | 检查方法 |
|---|---|
| 非 HTTPS 或证书错误 | `curl -v` 中的 TLS 错误；`http://` 链接是否有 HTTPS 版本 |
| 跳转到其他主机 | 比较链上相邻主机。脚本仅比较首尾域名末两段，可能漏掉 `co.uk` 下的不同站点。缺少公共后缀数据时将主机变化列为需复核。 |
| 短链与多层跳转 | 跳数 > 3，或经过多个短链服务 |
| 仿冒域名 | 混合字符集或 punycode（`xn--`）、相似字符（`rn`/`m`、`I`/`l`）、品牌词出现在子域而非注册域 |
| 链接文本与目标不符 | 锚文本写“下载发票”，目标却是登录页或可执行文件 |
| 可执行文件下载 | 最终 `Content-Type` 或扩展名为 `.exe`、`.apk`、`.dmg`、`.scr` 等 |

疑似钓鱼或恶意的链接只做上述被动检查，不在本机打开最终页面、下载文件或提交表单。
需要信誉查询（如 Safe Browsing、VirusTotal）时，使用用户已有的账号或 API key，并说明会把 URL 发给第三方。

### 4. 分级与输出

- **失效**：确认的 HTTP 错误（排除 401、403、429）、DNS 失败或超时。脚本对 `broken` 返回退出码 1。
- **需复核**：401/403、429、主机变化、证书问题或可疑特征。脚本把证书错误也归入 `broken`；据错误详情在人工报告中标为需复核。
- **通过**：2xx，跳转链合理且与链接上下文一致。

```markdown
### 链接检查摘要（<日期>，<检查范围>）
- 检查总数：<n>；通过：<n>；失效：<n>；需复核：<n>；未能检查：<n>

| 文件:行 | 原始链接 | 结果 | 最终地址 | 说明 | 建议 |
|---|---|---|---|---|---|
| README.md:45 | http://old.example.com/doc | 301 → 200 | https://new.example.com/doc | 永久跳转 | 替换为最终地址 |
| docs/faq.md:12 | https://broken.example.com | DNS 失败 | - | 域名不可解析 | 移除或寻找替代 |
```

301/308 永久跳转可以建议替换为最终地址；302/307 临时跳转保持原链接并注明。
修改文件只在用户请求修复时进行，并在输出中列出改动的文件和行。

## 边界与限制 / Boundaries

- 只检查用户提供或授权范围内的 URL；不扫描端口、目录或主机。
- 需要执行 JavaScript 才完成的跳转无法用 `curl` 判断，可交给 `agent-browser` 或 `playwright` 在隔离环境验证。
- 可达性受地区、网络出口和时间影响；结果注明检查时间和执行环境。
- 带时效 token 或会话的链接可能对检查者失效，不能据此判定为死链。
- 静态特征只能提示风险，不能确认恶意或安全；结论写明依据和未核验部分。
