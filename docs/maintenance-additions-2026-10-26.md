# 三项高价值技能增量收录（2026-10-26）

本批接续全量策展，以明确能力缺口为依据，只增加三个入口。没有重新引入永久退役名称或同义包装，也没有把通用提示包装成新技能。

| 技能 | 缺口与资产 | 来源及处理 |
|---|---|---|
| shadcn | 实际组件/注册源/主题契约、差异预览与交互验收 | 官方 shadcn-ui/ui，MIT，固定提交 8f04138777c1b6996e709993362a7b0a12888ecf；保留原始参考及版权，本地入口移除自动 shell、通配授权和默认全量安装 |
| security-model | SECURITY_MODEL.md 根到叶策略解析、可信 base 和陈旧引用检查 | Sentry d12f250460ffd961f549dbebf7eeb0cf4afd4c2e，Apache-2.0；保留 OpenAI 2b74623e0fe2e92b6832e0cea585944ec60495ae 归属；解析器在保留版权基础上进行本地安全硬化 |
| remotion-video | 帧时间线、抽帧与最终媒体元数据验收 | 原创入口、React 示例及只读 Python 校验器；仅使用官方 API 事实，不复制缺少宽松许可的上游技能文本 |

## 筛选证据

shadcn 与 Remotion 在 skills.sh 上有明确使用热度，选取其官方来源而非转存别名：
[shadcn](https://www.skills.sh/shadcn-ui/ui/shadcn)、
[Remotion skills](https://www.skills.sh/remotion-dev/skills)。统计会变化且不同页面口径不一致，因此不以精确安装数作质量承诺。
[security-model](https://github.com/getsentry/skills/tree/d12f250460ffd961f549dbebf7eeb0cf4afd4c2e/skills/security-model) 优先看官方可执行资产与策略契约，没有宣称它拥有同等安装热度。社区热度不能代替实际验收。

新增功能不替代现有 frontend、视频生成或漏洞扫描入口：shadcn 聚焦既定技术栈的组件变更；Remotion 聚焦可复现帧渲染及媒体规格；security-model 聚焦供审查器消费的策略上下文与解析。三者均有明确边界和可检查的交付标准。

## 保留与修复

- 外部原始入口、参考、示例、规范和法律文本保留不可变快照；原始可执行文件以 .txt 后缀归档，只执行本地经审查的 helper。provenance v2 区分 primary、secondary 和 local 所有权。
- shadcn 不把字符串 import 扫描当作页面已展示；原始辅助脚本的误报和目录链接递归限制已在兼容说明中记录。Tailwind 完整颜色变量不嵌套包装。实际验证过 npm CLI 4.22.1 的 help、add/help、info/help，没有向任何项目写入组件。
- security-model 修复空 ref 回退、OID 固定、文件与路径边界、Git 历史模式/体积、已删除文件及警告放大；保留上游测试并增加本地边界回归。新抑制/风险接受不能由被审 diff 自己授权。
- Remotion 校验器只读 ffprobe JSON，检查尺寸、帧率、时长、可用帧数和音轨存在性，限制输入体积和有理数字符串长度；不运行媒体文件、安装 runtime 或发起云任务。

## 许可和验收边界

shadcn 的 MIT 与 Sentry/OpenAI 的 Apache-2.0 均按不可变提交核验。Remotion 上游技能缺少可接受的宽松许可证，阻止的是复制收录，已以原创实现解决能力缺口；Remotion runtime 及第三方资产使用条款仍须按实际项目核对。没有削弱许可检测器或将复制内容改称原创。

完整顺序流水线和统一验证均已通过：814 项 Python 测试、65 项 Node 测试、304 份 Python 文件编译、严格质量 299 PASS/0 WARN/0 FAIL（含嵌套入口）、来源覆盖 296/296，许可 missing/disallowed 为零；安装器语法/help/targets/bundles、npm pack dry-run、资源/视频/库存/README/冲突/空白检查及健康报告均通过。生成器幂等、独立审查以及最新 PR head 和合并提交 CI 的具体结果以本批交付记录为准。没有运行实际视频渲染/音频验收、浏览器组件验收、模型行为评测或安全扫描服务；测试与文档校验不能替代这些结果。
