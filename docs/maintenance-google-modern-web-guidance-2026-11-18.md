# Google Modern Web Guidance 精选与持续维护

本次新增 `skills/developer-engineering/modern-web-guidance`，采用本地原创适配入口，
明确引用 Google 的检索方法、兼容性规则和官方 CLI。没有将改写后的正文声称为
官方原文镜像。技能保留上游 Web 范围内“必须先检索”和首次执行前主动核对网络审批的规则，
按 Codex、Claude 的宿主权限及当前会话已有授权执行。

## 来源与许可

- 分发库：<https://github.com/GoogleChrome/modern-web-guidance>。
- 实际源码库：<https://github.com/GoogleChrome/modern-web-guidance-src>。
- 已审阅分发提交：`64a6d708f5a43f2cd3fde5d4d7db3905ba1bdf65`。
- 官方 npm 版本与分发库稳定版均为 1.0.1；Node 要求 >=22。
- 根软件/技能许可为 Apache-2.0；README 对 `guides/` 指南正文另行声明 CC-BY-4.0。
  本次保留 Apache 许可文本和来源说明，指南语料按需通过官方 CLI 获取，未复制进仓库。

登记器要求改写的入口走 in-house 原创适配登记；Google 来源、不可变观察提交和
授权范围在维护引用中保留。后续若要收录指南正文，须单独记录其 CC-BY 归属与修改说明，
不能根据根目录或 GitHub API 的 Apache 标签推断所有子文件都是同一种许可。

## 精选后的行为

所有 HTML/CSS 与客户端 JavaScript 实现或修改任务必须先检索，包括框架中的原生
Web 能力；不能因简单或熟悉而跳过。纯后端、基础设施、工具配置、测试与文案任务
沿用上游排除范围。先按具体能力短查询，读取实际返回的 guide ID，再按需 retrieve。
保留浏览器目标、Baseline 状态、特性检测、回退、SSR 边界和无障碍验收方法。
广域 legacy-scan 仅用于用户要求的现代化审计；保留合法回退，不为零告警改坏代码。

首次执行前核对宿主沙箱、网络权限与既有授权；受审批控制且缺少授权时，先请求
仅针对已审阅 modern-web-guidance 命令的联网审批，不申请通用 npx/pnpx 白名单。
已有授权直接复用；无需审批的宿主不额外询问；禁止审批的宿主不得绕过其限制。
保留上游 pnpx 优先、Windows npx.cmd、可写临时缓存与离线缓存尝试的适配方法。

入口不会因加载而改写本机技能、开启 Origin Trials 或改变产品浏览器策略。
交付格式遵从宿主和用户要求，查询中避免私有源码与秘密。检索命令使用已审阅的
1.0.1，运行时指南内容与仓库入口版本分开记录。

## 持续进化

加入现有 browser-foundations 优先清单，同时检查：

1. 分发库技能目录（包括指南）、发布版本、package 与许可说明。
2. 源码库 skills-src、guides、features、CLI 源码、package 与许可说明。
3. npm latest 与已审阅版本是否一致。

现有全仓更新及周一定时检查会优先发现差异，并在同一条周报 issue 跟踪。
来源不可用、许可变化、指南或 CLI 变化均需要审阅；适配并验证后再推进基线。
新增指南或 CLI 实现变化即使没有改动入口正文，也不会被旧固定快照掩盖。

## 验证记录

- 官方 1.0.1 `--help` 正常，实际命令覆盖 search、retrieve 和 legacy-scan。
- 在设置 `DISABLE_TELEMETRY=1` 的维护探测中，查询 `light dismiss dialog` 成功，
  使用实际返回的 `light-dismiss-a-dialog` ID 取回指南，退出码均为 0。
- 七个基础能力目标在线检查均为 current，包括两个 Google 来源。
- 增加双来源、许可路径和语料变化的回归检查；相关 15 项测试通过。
- 全量收录与 canonical 验证使用隔离 Linux 副本，保留 Git 文件模式与原始字节语义。
  真实运行验证覆盖指南检索，不将其当作指南涉及的所有浏览器 API 都已实测。

收录登记成功；完整 `validate_repository.py --refresh` 通过：3818 tests passed、5 skipped、397 subtests passed。指令、质量、许可、来源、资源引用、README 与生成视图检查全部通过。
