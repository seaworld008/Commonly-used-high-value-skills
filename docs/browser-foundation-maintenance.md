# 浏览器基础能力的持续维护

浏览器软件版本、仓库技能版本、上游文档和正在运行的工具接口分别记录。
更新一个技能的日期，不能证明 CLI、MCP 或宿主插件已更新。

## 每次全仓更新的入口

```bash
python scripts/check_browser_foundations.py
python scripts/sync_all_upstream_skills.py
```

全仓入口已经内置第一步；独立命令适合只检查基础能力。定时 upstream-sync
也在发现新技能和全量检查之前运行它，并将结果写入同一周报和持续跟踪 issue。
不另外创建定时任务。网络失败保持失败，不得用上一次报告声称本次检查成功。

`docs/sources/browser-foundations.json` 是优先级和审阅基线：

- agent-browser、Chrome DevTools MCP、Playwright MCP：同时查询 npm latest、
  GitHub 最新稳定发布以及默认分支中相关命令/技能文件的树摘要。
- DevTools 与 Playwright 的仓库技能来源：检查相关目录，而非只看整个仓库 HEAD。
- 通用同步器先检查 agent-browser、DevTools、Playwright，其他技能保持原顺序。
- 官方 Browser/Chrome/computer-use/node_repl 由宿主分发，仓库不复制内部源码；
  手动维护时读取当前宿主工具文档并检查应用更新渠道、实际加载的构建和接口。

树摘要包含路径、blob SHA 和文件 mode，能发现引用/模板/接口新增、修改及删除。
无关目录变化不会触发适配。路径消失、树被截断或 API/注册表失败均不能算“最新”。
已有 provenance 固定快照继续保留许可证及不可变来源；它不再掩盖后续稳定版发布。

## 状态与闭环

| 状态 | 含义 | 后续动作 |
| --- | --- | --- |
| current | 本次在线比较与已审阅的接口及稳定版一致 | 保留当前基线 |
| review_required | 新稳定版、包版本或接口摘要变化 | 审阅差异，适配技能和辅助文件 |
| unavailable | 任一必要来源未完成检查 | 记录失败来源，恢复后重试 |

报告整体对应 complete、degraded、failed。检查不会安装本机软件、替换技能，
也不会推进 `reviewed_*`。批量 apply 对后两种状态停止；只读全仓检查可继续
收集其他来源结果，但最终退出状态保留基础检查失败或待审阅事实。

适配步骤：

1. 从记录的 `reviewed_commit` 到报告的当前提交查看相关目录差异，核对发布说明、
   npm engines、实际安装包和 MCP tool schema。默认分支新增能力可能尚未发布，
   不把未发布参数写成稳定版已支持。
2. 更新触发描述、具体命令、session/ref 生命周期和引用/模板；保留本地兼容适配。
   按已安装版本动态加载指引，离线引用标注审阅版本，避免常用入口复制整套手册。
3. 更新 provenance v2 的精确引用、许可证检查点、artifact inventory 和摘要。
   不用刷新摘要冒充内容审阅，也不把本地改写声称为上游原文。
4. 运行相关回归测试和 `python scripts/validate_repository.py --refresh`。
   CLI help、MCP initialize/tools/list 和真实页面交互分别记录，不能互相替代。
5. 审查后手工更新 policy 的 `reviewed_commit`、`reviewed_tree_digest`、
   `reviewed_version`、`reviewed_release` 和 `reviewed_at`，提交技能与基线的同一批变更。
   重新在线检查，只有全部目标完成才是 complete。

持续演进并非无条件追随默认分支或自动覆盖全部文本；它要求新变化可靠地进入
待审阅队列、适配有验证、基线有证据。新增基础后端时，将它的来源和验收契约
加入同一 policy 与测试，避免分散维护多个互不关联的版本清单。

## 本次审阅（2026-11-18）

- agent-browser 稳定版 0.43.0：更新 core/reference/template 快照；入口采用任务
  session、按 `--ref` 加载资料、snapshot 优先和条件等待；Node 最低 22。
- Chrome DevTools MCP 1.13.0：pageId 默认路由、logpoints、按页面网络 mock、
  JavaScript 禁用与实验性工具组边界；以当前服务端 schema 为准。
- Playwright MCP 0.0.85：区分 MCP、CLI 与宿主原生 browser 的版本及 refs。
- 发布后的默认分支命令变化仅作为后续监控基线；稳定版指引仍按上述发布范围。
- 宿主 browser 更新后重新读取其实际 API；仓库没有一个应替代宿主指令的
  同名通用 browser 快照，不新增职责重复的 wrapper。
