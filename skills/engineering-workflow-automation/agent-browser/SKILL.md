---
name: agent-browser
description: '为 Agent 提供真实浏览器自动化能力，支持语义定位、表单交互、截图录屏、脚本执行与会话管理。'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["agent", "automation", "browser", "workflow"]'
created_at: "2026-03-15"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Agent Browser

当任务需要 **直接操作网页**（而不是只读 API 数据）时使用本技能。Agent Browser 基于标准的 CDP (Chrome DevTools Protocol) 协议，赋予 Agent 像人类一样浏览网页、填写表单、点击按钮以及处理复杂前端交互（如 React/Vue 渲染页面、弹窗、验证码预览）的能力。

## 安装

```bash
npx clawhub@latest install agent-browser
```

## 适用场景

- **打开网页并执行多步操作**：登录后台管理系统、在多个页签间比对数据、提交复杂的业务表单。
- **用自然语言定位元素**：无需编写复杂的 CSS Selector，直接通过“点击左上角的搜索框”或“找到包含‘加入购物车’字样的按钮”进行操作。
- **导出多媒体产出**：将当前页面保存为高清截图、滚动截长图、PDF 文档，甚至录制一段操作视频。
- **执行页面内 JavaScript**：直接在 Console 中注入自定义脚本，提取原本难以抓取的动态数据或模拟特定用户行为。
- **保存会话状态**：支持 Cookie、LocalStorage 的持久化（`retain` 机制），实现跨会话的免登录访问。

## 使用建议

1. **先说明目标页面与预期结果**：建立清晰的 `Success Criteria`。
2. **分阶段执行**：将复杂操作拆成可验证的原子步骤（导航 → 定位 → 操作 → 校验）。
3. **涉及账号安全**：优先使用隔离的浏览器 Profile，并开启最小权限模式。
4. **视觉优先**：在关键操作前后进行 `screenshot`，既是留存证据，也方便 Agent 自我纠错。

## 触发条件 / When to Use

- **API 缺失场景**：当目标网站不提供公开 API，只能通过网页前端交互获取数据时。
- **图形化报表抓取**：需要从复杂的仪表盘（Dashboard）中截取特定图表并分析。
- **自动化注册/登录流程**：需要模拟用户完成一系列实人认证或偏好设置步骤。
- **SEO 与前端性能测试**：通过 `console` 读取页面报错、性能指标（LCP, FID）并进行诊断。
- **动态内容实时监控**：如监控股市实时行情网页或秒杀活动的库存变动。

## 核心能力 / Core Capabilities

### 1. 语义化快照与定位 (Semantic Snapshot)
- **操作步骤**：
  1. 调用 `snapshot` 获取辅助功能树（Accessibility Tree）。
  2. 结合 `ax*`（可访问性引用）和 `n*`（DOM 引用）理解页面层级。
  3. 通过 `highlight` 技能验证定位是否准确。
- **最佳实践**：在复杂页面中，先进行 `scroll` 滚动到底部，确保懒加载（Lazy Loading）的内容完整呈现。

### 2. 精准动作模拟 (Action Emulation)
- **操作步骤**：
  1. 调用 `act` 接口，执行 `click`, `type`, `hover`, `drag` 等动作。
  2. 设置 `clearFirst: true` 确保输入框内容干净。
  3. 对于关键步骤，开启 `slowly: true` 以模仿人类真实点击频率，降低被反爬引擎识别的风险。
- **最佳实践**：在点击“提交”后，立即配合 `wait` 工具，直到特定 URL 或文字出现，确保操作已生效。

### 3. 会话留存与持久化 (Session Retention)
- **操作步骤**：
  1. 使用 `retain: true` 标记重要的页签（Tab）。
  2. 被标记的页签在 Agent 会话结束后不会被自动关闭，方便后续二次访问。
- **最佳实践**：在需要用户手动扫码登录时，开启 `retain`，等用户扫码完成后 Agent 再接管。

### 4. 异常捕获与诊断 (Errors & Requests)
- **操作步骤**：
  1. 实时读取 `errors` 列表，识别 JS 执行崩溃。
  2. 监控 `requests` 网络请求，拦截并分析特定的 API 数据包（甚至包括 XHR/Fetch 的 Response）。

## 常用命令/模板 / Common Patterns

### 网页信息采集工作流模板 (Scraping Workflow)
```markdown
### 任务目标
[目标描述：从 X 网站抓取前 10 个产品的价格和评论]

### 操作步骤 (Action Sequence)
1. **Navigate**: 访问 `https://example.com/products`。
2. **Wait**: 等待包含 `.product-list` 的元素加载完成。
3. **Scroll**: 滚动至页面底部触发分页。
4. **Snapshot**: 获取所有 `n` 级引用的文本内容。
5. **Console**: 注入脚本 `Array.from(document.querySelectorAll('.price')).map(e => e.innerText)`。
6. **Screenshot**: 截取整个列表区域存入 `output/products.png`。

### 预期结果
- 汇总 JSON 数据。
- 截图证据。
```

### 快速打开与保留页签示例
```javascript
// 示例：打开 GitHub 并保留会话，不被自动销毁
const tab = await mcp_call({
  name: 'browser_open',
  arguments: {
    targetUrl: "https://github.com",
    profile: "chrome"
  }
});
await mcp_call({
  name: 'browser_retain',
  arguments: {
    targetId: tab.targetId,
    retain: true
  }
});
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动化 UI 回归测试
- Agent 定期打开开发环境网页，截取核心功能页面，并与 `MEMORY.md` 中的“基准截图”进行对比，识别 UI 错位或样式丢失。

### 2. 跨平台数据“搬运工”
- 将 A 系统的报表数据读出，自动登录 B 系统并手动填入每一条记录，实现无 API 情况下的系统集成。

## 边界与限制 / Boundaries

- **验证码拦截 (CAPTCHA)**：复杂的图形或拼图验证码仍需人工干预（可配合 `question` 技能将截图发给用户）。
- **资源开销 (Resources)**：启动浏览器（尤其是多开）非常消耗 CPU 和内存。
- **驱动兼容性**：在部分无头环境（Headless）中，某些依赖 GPU 加速的动画或 WebGL 可能渲染异常。
- **防爬检测 (Anti-Bot)**：如果动作过于机械或 IP 归属地异常，目标网站可能触发封禁。建议配合代理（Proxy）使用。
- **超时风险**：在网速极慢或服务器响应缓慢时，需合理设置 `timeoutMs`。

## 最佳实践总结

1. **失败重试策略**：针对导航失败或元素找不到，设计 2-3 次自动重试机制。
2. **环境一致性**：尽量保持分辨率（Viewport Size）一致，防止响应式布局导致元素位置突变。
3. **清理现场**：除非开启了 `retain`，否则在任务结束后及时 `close` 无效页签。
4. **隐身模式**：处理敏感任务时，优先使用 `incognito` 模式。
5. **日志可追溯**：将所有的 `browser console` 错误日志记录下来，它是调试的第一线索。
