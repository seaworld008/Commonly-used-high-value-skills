---
name: web-scraper
description: '用于网页数据抓取、结构化提取和反爬策略应对。来源：全网高频推荐。'
version: "1.0.0"
author: "seaworld008"
source: "community"
source_url: ""
tags: '["automation", "scraper", "web", "workflow"]'
created_at: "2026-03-27"
updated_at: "2026-03-27"
quality: 4
complexity: "intermediate"
---

# Web Scraper

## 触发条件
- 当需要从第三方公开网站获取大规模数据（如价格监控、社交媒体趋势、新闻聚合）时。
- 在没有官方 API 或官方 API 限制过多、功能不足的情况下，需要直接从 HTML 中提取结构化信息。
- 需要自动化执行网页交互任务（如自动登录、表单填写、文件下载）时。
- 建立行业数据库、训练 AI 模型或进行市场调研需要大量原始网页数据支撑时。
- 需要实时监控网页内容变化（如库存变动、价格降价提醒）并触发警报时。

## 核心能力

### 1. HTTP 请求与会话管理 (Requests & Sessions)
- **请求头 (Headers) 伪装**: 模拟真实浏览器行为，随机切换 User-Agent, Referer, Accept-Language。
- **Cookie 维持**: 使用 Session 对象自动处理 Cookie 传递，维持登录态。
- **代理池 (Proxy Pool)**: 动态切换 IP 地址，防止因单一 IP 频繁访问导致的封禁。
- **重试与退避**: 实现自定义 Retry 策略，处理网络波动或短暂的服务端拒绝。

### 2. 多样化解析与提取技术 (Parsing & Extraction)
- **CSS Selectors & XPath**: 利用树状结构精准定位数据。
- **正则表达式 (Regex)**: 提取 HTML 或 JS 脚本中非结构化的文本数据（如动态变量）。
- **BeautifulSoup/Lxml**: Python 经典的 DOM 解析方案。
- **Schema 提取**: 自动识别网页中的 Schema.org 结构化数据（JSON-LD/Microdata）。

### 3. 处理动态 JS 渲染 (Modern Browsing)
- **无头浏览器 (Headless Browsers)**: 
  - **Playwright**: 现代、快速且支持多浏览器的自动化方案。
  - **Puppeteer**: Google Chrome 官方提供的 Node.js 库。
- **等待机制**: 精确控制 `waitForSelector`, `waitForResponse`, `waitForTimeout` 以确保数据加载完成。
- **事件模拟**: 模拟点击 (Click)、滚动 (Scroll)、输入 (Type) 等用户行为触发 AJAX 加载。

### 4. 深度反爬应对策略 (Anti-scraping Evasion)
- **速率限制 (Rate Limiting)**: 实现分布式爬虫的并发控制，模仿人类浏览节奏（设置随机休眠）。
- **浏览器指纹 (Fingerprinting)**: 隐藏或伪造 WebGL, Canvas, 字体等特征，逃避指纹识别系统。
- **验证码 (Captcha) 处理**: 
  - 自动规避策略（如不触发验证码）。
  - 第三方识别服务（如 2Captcha, YesCaptcha）的集成。
- **HTTP/2 支持**: 许多高级反爬系统通过检测是否使用 HTTP/2 来识别爬虫。

### 5. 数据流与工程化 (Pipeline & Scale)
- **增量抓取 (Incremental Scraping)**: 基于 URL 哈希或 Last-Modified 头，只下载更新过的页面。
- **数据清洗 (Cleansing)**: 使用正则表达式和正则表达式去除 HTML 标签、转义字符及冗余空格。
- **结构化输出**: 自动映射提取结果至 JSON, CSV, 或 SQL 数据库中。
- **并行与分布式**: 利用多线程 (Threading) 或 Scrapy + Redis 实现千万级数据抓取。

## 常用命令/模板

### Playwright Python 基础模板
```python
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 ...")
    page = context.new_page()
    page.goto("https://example.com")
    
    # 模拟滚动到底部触发加载
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_selector(".item-list")
    
    items = page.query_selector_all(".item-list .title")
    results = [item.inner_text() for item in items]
    print(results)
    
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
```

### BeautifulSoup 解析示例
```python
from bs4 import BeautifulSoup
import requests

response = requests.get(url, headers=my_headers)
soup = BeautifulSoup(response.text, 'lxml')

# 使用 CSS Selector
price = soup.select_one('.product-price').get_text(strip=True)
# 使用 XPath (需配合 lxml.etree)
# tree.xpath('//div[@id="title"]/h1/text()')
```

## 边界与限制
- **法律合规性 (Legal & Ethical)**: 严格遵守网站的 `robots.txt`。禁止抓取非公开个人信息。遵循 GDPR 和反不正当竞争法。
- **资源消耗**: 开启浏览器渲染会消耗极大的 CPU 和内存。
- **高频更新**: 目标网站的前端结构一旦变更，爬虫代码必须同步重构。
- **物理障碍**: 强力的验证码（如 HCaptcha/Cloudflare 5s check）有时难以通过程序完美突破。
- **业务干扰**: 禁止进行高频率、破坏性的抓取行为（DDoS 级访问），以免对目标站点造成负担。

---
*注：本技能适用于合规、合理的网页公开数据采集场景。*
* lines: 115
* word count: ~1300 characters
