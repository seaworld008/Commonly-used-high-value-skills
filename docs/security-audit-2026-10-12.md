# 2026-10-12 Code Scanning 安全审计与修复

## 范围与实际发现

目标仓库：seaworld008/Commonly-used-high-value-skills，基线 main = 5fcc2a0d35d746daad91f67d9928f1c780ca830a（v3.3.0）。

通过具备 security-events:read 权限的临时 GitHub Actions 只读任务读取 Code Scanning API，确认 **18 条开放 CodeQL 告警（14 High / 4 Medium）**。工作流证据：https://github.com/seaworld008/Commonly-used-high-value-skills/actions/runs/38222142859 。

| 安全规则 | 告警编号 | 对应风险 |
| --- | --- | --- |
| js/redos | 37, 38 | 第三方 Markdown 解析器中的灾难性回溯 |
| js/path-injection | 39, 40 | 根据用户可控路径执行本地文件操作 |
| js/bad-tag-filter | 41, 42, 43, 44, 45 | 不完整的 HTML/script 标签过滤 |
| js/incomplete-multi-character-sanitization | 46, 47 | 不完整的多字符转义 |
| js/incomplete-sanitization | 48 | 仅替换第一个小于号 |
| js/shell-command-injection-from-environment | 49 | 通过 cmd /c 和环境输入打开文件 |
| js/overly-large-range | 50 | 重叠 Unicode 字符区间 |
| js/client-side-request-forgery | 51 | Live Panel 根据 URL 参数直接发 fetch |
| js/file-system-race | 52, 53 | stat 之后再次按路径打开文件 |
| js/indirect-command-line-injection | 54 | 用户/环境影响系统打开命令 |

来源：17 条在 skills/office-white-collar/answer-me-with-html/scripts/am.mjs，1 条在 skills/multimodal-media/live-panel/assets/template.html。OpenClaw 路由由规范源生成，不手工隐藏同类文件。

## 技术修复及必要取舍

- **HTML CLI**：不再保留无法以合理成本完整审计的约 800 KB 上游第三方捆绑执行文件；改为小型、自包含、无依赖的离线渲染器。不使用子进程、网络模块、动态代码执行或对输入 HTML 的危险正则过滤。
- **防注入**：所有不可信文本经统一 HTML 转义；禁止原样嵌入 raw HTML、SVG、图片和第三方脚本；页面启用 CSP。
- **文件系统**：随机文件名，受管输出目录、O_NOFOLLOW / O_EXCL、受控 patch、fstat(fd)、输入大小约束。拒绝路径穿越、符号链接和跨目录修改。
- **Live Panel**：继续允许本地 Python 脚本内嵌 JSON；删除从 URL query 发起 fetch 的分支，同时设置 connect-src 'none'。
- **发布保护**：将 Code Scanning 开放告警列表作为 GitHub Release 的真实阻断门禁；若任一告警仍 open，不能发布。
- **安全兼容性**：原 HTML CLI 的 serve、clean、update、自动打开、语音、任意代码及本地图片嵌入功能被明确停用；不能再宣称功能完全等价，因此采用 **v4.0.0 主版本**。
- **来源治理**：MIT 许可证及上游历史来源仍保留，更新本地覆盖版文件哈希与权限。此实现不声称是上游发布的逐字镜像。

## 回归与发布验收

新增测试涵盖恶意 HTML/SVG 转义、CSP、flow/table、受管 patch、路径穿越、外部文件拒绝、旧命令禁止、输入上限、符号链接目录以及 Live Panel 的 fetch 禁止。

完整门禁为 validate_repository.py --refresh、生成索引幂等、许可证/来源与 SHA256、Ubuntu/Windows × Node 22/24 安装器、CodeQL security-extended、合并后 main 的实际开放告警数量检查，以及 Release 四附件独立下载与 SHA256 校验。

**边界**：Code Scanning 零开放告警证明当前配置的扫描规则未报告尚未解决的问题，不是对供应链、运行时系统或每种输入都不存在任何漏洞的绝对保证。实际关闭情况必须在合并后的默认分支重新读取 API 确认。
