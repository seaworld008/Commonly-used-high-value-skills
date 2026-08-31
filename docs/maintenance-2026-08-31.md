# 2026-08-31 精选维护决策

本轮继续 PR #95，不另建重复周更 PR。开始时工作树干净；历史 PR 检索
没有其他开放或已关闭未合并项。最终检查与合并状态以 PR 的精确提交为准。

## 范围与保留原则

- 维持 284 个 canonical skills、36 个永久退休墓碑；不为数量新增技能。
- 不退役完整工作流，不将参考资产误判为没有价值的单文件包装。
- 保留所有既有 LOCAL-CURATION / LOCAL-QUALITY 补充块。
- 外部内容继续记录真实来源和 MIT 等许可；本地改编不改变其版权 lineage。
- 不执行本机客户端技能安装，不安装 Hermes 或 Open GSD 运行时。

## 已接受的修正

- Hermes 稳定版 `v2026.8.27`：22 个受管文件完整保留，加入缓存导致旧页面
  的诊断指导；升级与 `hermes-open-gsd-workflow` 的依赖锁在协调事务内完成。
  Router 不复制运行时协议、不安装软件、隔离 `.planning/` 与 `.gsd/` 的
  契约不变，因此本次兼容性审查允许依赖前移。
- GitHub API：只对只读请求的临时传输错误、429 和指定 5xx 做最多三次尝试；
  401/403/404 不重试，长 Retry-After 留给下一次运行，不误报成无更新。
- Xquik：按官方文档改为 `docs/search/execute`、`spec.paths`、normalized v1
  响应；保留账户操作仅规划、隐私/费用确认、幂等和不确定写入检查。
  删除供应商要求固定法律结论、限制法律引用来源与强制用词的说明。
  上游删除的两个 MCP 安全参考由本仓继续改编维护，并保留旧提交的独立、
  MIT 许可、不可变 archived sidecar 来源，不虚构为原创内容。
- Lark：精选审批加签/转交流程、Base 完整分页与 rev 一致性、邮件重复参数、
  Drive appid 类型及 Slides marginRight schema 修正；保留现有写入边界。
- Cloudflare：修复 AI SDK provider 配置位置与 Chat Completions 选择，
  不再把旧 OpenAI 模型名传给 Workers AI。
- Agent Designer：Anthropic 示例使用显式配置模型，并补必需的 max_tokens。
- AWS：移除全局固定请求单价，要求记录区域、规格、读一致性和查询日期。
- Addy：保留未完成计划，补性能回归监测、查询计划/连接池/缓存正确性要求；
  不因索引未采用就盲目改索引，不在生产默认执行 EXPLAIN ANALYZE。

## Commit-aware monitor 决策

| 来源 | 本轮审阅提交 | 决策 |
| --- | --- | --- |
| larksuite/cli | `6646386e0996b1ff5df640bccff834a20bcb203b` | 对 39 commits、72 个受管变更做人工选择，接受上述兼容性修正 |
| Xquik-dev/x-twitter-scraper | `dc5fa6037d700eb3a7721155e92dabeeb9e56894` | 13 个制品变更；保留安全参考，拒绝营销及预设法律断言，以当前官方 MCP 契约修正 |
| addyosmani/agent-skills | `d2c37ef6225dd8726cdd369a8030307f48592d26` | 吸收计划保护及性能方法；PR 触发词扩写不改变已有覆盖，不新增同意图的 constraint 路由 |
| alirezarezvani/claude-skills | `19392f7a08264ed00486a251f5b2098321771f94` | 受管变化仅 AWS 价格示例和 agent-hub 命令名，均已处理 |
| simota/agent-skills | `0b594f3ff4bf53639f60832a943d90a5109ddf85` | 受管制品树不变；共享措辞/自包含测试 fixture 不构成本仓新能力 |
| wshobson/agents | `38e19c20d2b154510b0e624a2e3e186b19b5c527` | 受管制品树不变，保留本地 curated 版本 |
| NousResearch/hermes-agent | `1f99a4b2f2982fbef06df00ad673ade4e1895668` | 前次审阅后 42 commits、85 文件，不改变六个监测技能的受管路径；运行时代码留给稳定版 |
| xiaolai/nlpm | `92e64eebd178aaf9892dde3c078afdbe3d3140ca` | 后续四个提交仅 auditor 日志与注册表，不复制遥测 |

其他没有受管变化的来源沿用逐提交/完整树审阅证据。`monitor_review` 表示
本地 curated 内容与上游不完全相同，不代表审阅检查点不能前移。只有核对
精确提交、许可和受管路径后才记录复核；不能用网络错误的空结果推进检查点。

## 明确不接入的内容

- Lark 新 chart checker 的行锚点存在 1-based/0-based 偏移，且缺少相应
  上游测试；不引入这个脚本，也不新增空壳替代品。现有坐标规则继续有效。
- 不接受 Sheets 将“必须回读/禁止覆盖”等要求降为可选的变更。
- 不接入未经本仓 CLI fixture 验证的新 chart PATCH、field extension
  批量写回和 media-download fallback 行为；其新增能力不是当前组合缺口。
- 保留 Base 的现有分析示例与校验参考，不因上游收缩文件就删除可用资产。
- Open GSD Core `1.12.0` / Pi `1.17.0` 发布记录已检查，但本轮不升级这两个
  显式安装 bundle。Core 引入新的状态事务、schema/退出码及工具身份契约，
  Pi 更改自动运行与恢复路径；这不是可仅凭技能文本检查放行的升级。
  继续使用已有已校验的 `1.11.0` / `1.16.0` 不可变锁和独立状态根。
  候选包的摘要/attestation subject 初验不是签名验证或运行时验收；不作
  这类完成声明，也不把候选不接入伪装成已更新。

## 组合审计队列

保留 `supabase-postgres-best-practices`、`python-performance`、`web-scraper`
等有领域参考或可执行资产的技能；保留 Lark 的真实外部命令契约。
`executing-plans`、`verification-before-completion` 和 Hermes/GSD 路由属于
连贯工作流及验收边界，不能仅因单步模型原生化拆除。
`llm-wiki` 有维护与可追溯性约束。十个 review 项没有满足高置信退休条件，
因此不新增退休墓碑或别名。

## 验证边界

跨 mapping 事务覆盖未批准依赖、陈旧审批、同文件依赖、用户并发编辑、
映射替换故障和五个强制退出恢复点。来源侧测试保护 archived lineage、
固定提交、第二活动来源拒绝与网络重试上限。
完整 pipeline、生成器幂等、远端 CI 与合并后精确 SHA 检查作为交付门禁。
离线测试和 CI 不代表真实飞书/Xquik 账户请求或运行时安装已验收。
