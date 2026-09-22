# 2026-09-22 技能维护审计

本轮以 main `bea60815831c0463f6592d8220eba2453e6cc9be` 为基线；开始时工作区干净。
全量覆盖 285 个规范入口、3,848 个技能及共享指令文件的静态清点。
人工重点复核质量队列中的 13 个入口、缺失辅助文件、占位实现、计划类指令和候选新增技能。
静态扫描没有代替每个参考文件的逐句语义审查，也没有执行全部技能对应的外部服务操作。

## 已交付的修复

| 项目 | 发现与处理 | 验证方式 |
|---|---|---|
| `senior-devops` | 三个脚本仅返回空成功；三个参考文件为占位模板。淘汰并登记持久策略 | 逐文件检查；替代覆盖由 `cc-devops-skills`、`pipe`、`terraform-engineer`、`release-manager` 提供 |
| 7 个 alirezarezvani 技能 | 入口引用的辅助文件未收录。补回 39 个脚本、参考文档和模板，附 7 份 MIT 许可 | 固定提交 `19392f7a08264ed00486a251f5b2098321771f94`、逐文件 artifact、CLI 帮助与重点功能测试 |
| `arxiv` | 补回实际搜索脚本与许可 | 固定提交 `ee4452991d17534aa561f31ee55596d082aa94e7`；离线 Atom 解析测试 |
| `agent-hub` | 清理工具原来强制移除工作区且用子串匹配会话 | 改用完整分支前缀和普通 Git 移除；回归验证保留脏工作区与其他会话 |
| `linear` | 固定归档提交不存在其宣称的 Python helper | 移除不可用命令，保留 GraphQL 与连接器路径 |
| 计划类 3 项 | 移除强制切换宿主模式、Claude 专用必选子技能和重复审批；补充依赖与证据交接 | 静态指令检查与 diff 复核 |
| `web-scraper` | 请求缺超时、示例变量未定义，缺少分页终止与失败判定 | 重写为带超时、字段验证、游标去重和采集验收的流程 |
| `python-performance`、`performance-profiler` | 使用墙钟计时、示例脚本被误当成随包工具 | 使用 `perf_counter`，说明项目自备脚本与基准比较条件 |
| `hermes-agent` | 新稳定版参考文档更新 | 审查 `v2026.9.21` 的两处差异；检查并更新 composite 依赖锁 |
| 同步工具 | `--source` 会遗漏无法归属的 provenance 错误，产生错误成功 | 保留加载错误，不允许过滤；正反回归测试 |
| 静态审计 | 未识别已知的空成功工具模板 | 增加该精确模式检测，保留真实分析脚本通过 |

恢复的 7 项为 `agent-hub`、`security-pen-testing`、`information-security-manager-iso27001`、
`landing-page-generator`、`saas-metrics-coach`、`senior-architect`、`skill-security-auditor`。
入口版本标识为本地 patch；恢复资源保持原许可与固定来源，Python 辅助文件清理了行尾空白。
`agent-hub` 的工作区清理修复是本地 overlay，不能声称与上游逐字相同。

## 保留与淘汰判断

只淘汰已证明没有有效独有能力的 `senior-devops`。`brainstorming`、`writing-plans`、
`executing-plans` 分别负责设计选择、计划编写、既有计划执行；缩短重复控制规则后保留。
`firebase-security-rules-auditor`、Lark、Obsidian、LLM Wiki 等虽因长度或描述启发式进入队列，
仍有规则安全、服务权限或知识结构方法；不按评分机械删除。
`hermes-open-gsd-workflow` 保留 Core/Pi 状态隔离的独有边界。
全局技能安装不在本轮范围；仓库 retirement policy 可供以后显式安装时清理旧项。

## 上游检查与保留策略

来源检查设置进程总时限，避免上轮 `x-twitter-scraper` 无限等待；本轮该来源检查已返回。
默认分支变化仍按 monitor 策略处理；没有未经审查地执行批量覆盖。
Hermes 稳定版两处参考变化已单独审查并应用。

另外以实际 Git checkout 检查大来源的完整 artifact 集：

| 来源 | 当前观察与决策 |
|---|---|
| Simota | 当前 `f425adcb2111ca8c0be88b325888ff61b64dec49`：513 个源文件与本地相同，127 个不同，122 个旧路径在上游消失。保留已许可的本地领域资料；暂不接受包含大量运行时路由与引用重组的整批替换 |
| Lark | 23 项的既有 artifact 中，276 个相同、186 个不同、8 个旧文件路径消失，另观察到 9 个新增文件。保留现有许可快照与会议权限边界；不能把路径消失解释为技能失效 |
| Addy Osmani | 24 个入口有本地策展差异，4 个辅助文件相同。保留跨宿主改写；本轮进一步修复计划类控制规则 |
| Superpowers | 19 个文件相同、14 个不同、2 个新增文件。保留本地工作流边界与可用工具回退，不整包引入宿主控制规则 |

这些不同包含本地 overlay，不全部等同于新增上游功能。当前默认分支没有被宣布全量同步。
未采用的监控更新保留原固定提交，避免用更新检查点掩盖未接受的替换。
原有自动发现 issue #120 仍记录未采用的监控差异；本轮不将它误关为全部同步完成。

## 新技能候选决策

三路实时发现共 2,742 个去重候选，其中 2,070 个为目录未收录候选；GitHub、skills.sh、ClawHub 均返回健康。
候选不会自动安装，以下新增作为独立 PR 交付：

| 候选 | 决策与理由 |
|---|---|
| Prisma Client API | 接受；补足 Prisma 查询、事务和原生 SQL 专项能力，MIT，官方仓库 |
| Prisma 7 Upgrade | 接受；补足版本迁移、适配器、模块与配置专项能力，MIT，官方仓库 |
| Prisma Database Setup | 本轮不增；与上述两项及现有数据库技能交叠，避免一次引入整套 Prisma 入口 |
| Claude API | 本轮不增；当前入口包含泛 LLM 触发与默认模型绑定，需要独立策展才能符合跨宿主范围 |
| Microsoft Playwright CLI | 本轮不增；已有 Playwright 与浏览器技能覆盖，先避免重复入口 |
| 通用 code-review、模板和图片生成包装 | 本轮不增；已有相应规范入口，热度不能替代差异价值 |

Prisma 固定来源：`1123817e60d15ca0f3af91878923241dee7e3b09`，仓库观察到 58 stars、最近推送 2026-09-08。
skills.sh 的安装量是平台计数，不是本仓库的效果评测：Client API 实时发现为 304,606，
迁移技能网页约 218.1K（网页索引有缓存）。
来源：[Prisma repository](https://github.com/prisma/skills)、
[Client API](https://skills.sh/prisma/skills/prisma-client-api)、
[Prisma 7 Upgrade](https://skills.sh/prisma/skills/prisma-upgrade-v7)。

## 验证边界

完整 `validate_repository.py --refresh` 覆盖质量、指令、来源、许可、生成物、资源清单和测试。
新增回归覆盖恢复脚本可调用、SaaS 计算、arXiv 离线 XML 解析、脏工作区保护、来源过滤失败和空成功模板。
首次全量测试发现新增管理文件未进入 Git index，暂存后重新检查；没有降低门槛。
PR 和合并后验证以相应精确提交的 CI 为准。发布阶段另行验证 tag、包内容和公开下载 SHA-256。
不声称已完成真实外部服务、模型行为、生产环境或新 Prisma 项目的运行验收。

维护 PR 本地最终门槛：287 项严格质量 PASS，0 WARN/FAIL；616 tests 与 227 subtests 通过；
来源覆盖 284/284、外部许可缺失与禁止均为 0；npm 打包检查与 15 项决策账本通过。
