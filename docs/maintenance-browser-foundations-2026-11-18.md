# 浏览器基础能力适配与持续检查记录

检查日期：2026-11-18。规则入口见[持续维护流程](browser-foundation-maintenance.md)，
在线检查结果见[本次检查数据](maintenance-browser-foundations-2026-11-18.json)。

## 变化与处理

agent-browser 的旧入口同时包含固定快照、发现 stub 和大量重复约束；其来源固定在
旧提交，普通同步即使显示检查成功，也不能发现后续稳定版。现按官方稳定版
0.43.0 更新 core、引用与模板，并保留 Apache-2.0 来源及精确文件证据。

新版入口采用每条命令的任务 session、`skills get core --ref ...` 按需加载、
snapshot/ref 交互与条件等待；模板在同一个 shell 中保留任务 session。
离线参考资料明确对应 0.43.0，实际操作仍加载已安装 CLI 的匹配版本指引。

DevTools 技能补充 1.13.0 的 pageId 默认路由、logpoints、按页面网络 mock、
JavaScript 禁用以及实验性工具组边界。Playwright 技能区分 CLI、MCP 0.0.85
和宿主原生 Browser/Chrome 的生命周期、版本及 refs。

## 持续性

- 新增基础能力 policy，记录稳定版、已审阅提交和相关文件树摘要。
- 检查 npm latest、GitHub 稳定发布以及上游技能、模板、工具接口和配置变化。
- 全仓更新入口先做基础检查；基础项目待审阅或检查失败时停止批量 apply。
- 通用来源扫描优先处理 agent-browser、DevTools、Playwright。
- 现有周一 upstream-sync 在发现新技能前检查基础能力，并把结果纳入同一条周报
  issue；缺报告、旧报告、来源失败不能写成“全部最新”。
- 检查不自动推进审阅基线；适配、验证和基线修改在同一批提交中交付。
- 批量更新后的校验复用 `validate_repository.py --refresh`，避免维护另一套过期检查列表。

## 验证证据

- 五个在线目标均为 current；npm 与 GitHub 稳定版一致。
- Windows：24 项基础检查、报告状态、更新阻断及定时流程回归测试通过。
- Windows agent-browser 0.43.0：动态加载 core 与 commands 引用成功。
- 独立任务会话完成本地 data URL 页面打开、快照发现按钮、点击实际返回的 ref、
  等待结果并再次快照验证；会话关闭成功，没有使用用户登录页面。
- 三个 shell 模板通过 `bash -n`。
- 隔离 Linux 验证副本完成完整流水线：3816 tests passed，5 skipped，397 subtests passed。
  包括指令、质量、许可、来源、artifact inventory、资源引用、README 和完整 pytest。
- 本机 Codex、Claude、共享 `.agents/skills` 已同步 agent-browser、DevTools、Playwright 三项。

完整验证使用 Linux 的文件 mode 与字节语义；Windows 原有检出的 CRLF 和部分
POSIX 来源写入器不作为技能内容漂移。本次新的在线检查命令及相关回归在 Windows
原生环境验证。真实浏览器验收覆盖 CLI 路径，宿主原生 Browser/Chrome 插件按当前
宿主文档维护；没有据此声称全部宿主浏览器后端均完成真实交互测试。

测试使用的 Chrome 为 157.0.8103.79；CLI 提示有更新的 Chrome 158.0.8127.36。
浏览器引擎的升级属于宿主维护项，本次源码适配记录保留该提示。

## 官方依据

- [agent-browser 0.43.0](https://github.com/vercel-labs/agent-browser/releases/tag/v0.43.0)
- [DevTools MCP 1.13.0](https://github.com/ChromeDevTools/chrome-devtools-mcp/releases/tag/chrome-devtools-mcp-v1.13.0)
- [Playwright MCP 0.0.85](https://github.com/microsoft/playwright-mcp/releases/tag/v0.0.85)
- [OpenAI 浏览器使用说明](https://developers.openai.com/training/walkthroughs/using-your-computer-and-browser)
