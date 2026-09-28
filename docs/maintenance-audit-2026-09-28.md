# 2026-09-28 全仓维护审计

## 范围与基线

基线为 `v3.0.0` / `4d170b083cd41ad5d16fa088bcfe8f73da55df6f`，共 16 类、286 个 canonical skills。扫描覆盖跟踪文件、安装器、维护脚本、技能辅助程序、来源与制品清单、生成物、CI 和发布元数据；对高风险路径及选定上游差异做人工语义审阅。不是对每个第三方工具的生产实测或模型能力评测。

基线全量流水线通过 619 个测试和 231 个子测试，但刷新产生了无内容变更的跨日日期差异。静态初筛检查 408 个 Python 文件、40 个 JavaScript 文件和 20 个 shell 文件。浏览器模块和宿主模板按其真实运行环境解释，不把合法 ESM 资产当成 CommonJS 故障。

[机器可读结果](maintenance-audit-2026-09-28.json)保留全部 152 条上游判定、基线摘要、已吸收变更及来源提交，不把检查失败改成“最新”。

## 已修复与淘汰的行为

| 问题 | 本次处理 | 回归证据 |
|---|---|---|
| 普通安装直接删除同名目标，用户修改可能丢失 | 先复制到临时目录并核验库存；修改过或未托管的旧副本归档；最后替换失败时恢复旧目录 | `test_installer_safety.py`：未托管/已托管修改、复制失败、最终重命名失败 |
| 源目标重叠与目录符号链接别名未在写前拒绝 | 解析真实路径，涵盖分类目录别名；校验所有选定来源和重名后再写入 | 重叠、别名、重名、后续源损坏测试 |
| Windows 上直接 spawn npm/npx 的 `.cmd` 包装器不可靠 | 定位 npm 的 JavaScript 入口，通过 Node 和参数数组调用，不启用 shell 拼接 | `test_npm_command.py` 与 Ubuntu/Windows、Node 22/24 矩阵 |
| 无变化的来源清单隔日重生成会漂移 | 默认保留未变化条目的检查日期；显式 `--record-check` 才记录纯检查刷新；真实内容变更仍更新 | `test_bootstrap_in_house_sources.py` 跨日与内容变更用例 |
| 两个直接 Node 辅助程序受父级 CommonJS 影响 | 在 `writing-skills`、`develop-web-game` 添加私有 ESM 包作用域，保留上游脚本正文 | 两个实际路径的 `node --check` |
| 依赖扫描器内置少量错误/陈旧漏洞映射，却声称全面 CVE 扫描 | 移除硬编码映射，明确定位为离线清单；输出 `not_assessed`，解析失败标记 partial；旧安全门禁退出 2 | serde 错配、JSON 状态、解析失败、失败关闭测试 |
| 升级规划器将模拟版本表当成注册表最新版本 | 淘汰模拟版本、公告和时间估算；保留原 CLI 路径作为明确退出 2 的迁移提示 | 不再把 React 18.2.0 等写死版本当作查询结果 |
| 许可证子串匹配可把复合表达式或其他文字当作 MIT | 精确匹配已知别名；未知表达式保持未知；不将 Unlicense/public domain 改写为 MIT | 复合表达式、伪子串、不同许可四项用例 |

安装保护是逐技能暂存与回滚，不是全部客户端目标的一次性事务，也不承诺抵御所有并发外部写入。备份位于目标目录同级 `.high-value-skills-backups/`；报错后应检查备份和清单再继续。

依赖工具的 `0 vulnerabilities` 历史字段仅为兼容输出，不是安全证明。需要有维护中的生态扫描器、当前公告与真实锁文件支持结论。许可证工具仍是初筛，不是法律意见或完整 SPDX 表达式解析器。

## 上游升级与策展

全量只读检查结果：152 项中，17 项未发现可应用更新、1 项稳定版更新、90 项默认分支待审差异、19 项资源不可用、25 项策略预期跳过。

- **稳定版**：Hermes Agent 升级到 `v2026.9.24` / `f97608f178d1ffeca59860195ab7da295f7c8e5f`。新增 webhook 消息映射回会话的使用与信任边界；使用原同步事务，审阅未变化的 `hermes-open-gsd-workflow` 正文摘要后更新组合依赖证据。
- **明确吸收的策展变更**：Graphify 路径引用安全；Neon 复用已有连接、项目和 ORM；Supabase 最小权限及独立数据库凭据边界；前端 UI 状态/参考审阅；代码审查触发与 merge-base 示例；Firebase 可解析 JSON；飞书邮件链接与会后查询边界；调试和技能辅助脚本使用显式解释器。
- **不盲目覆盖**：默认分支不会替换本地精简路由和已有用户授权逻辑。部分上游扩大了强制停顿、子代理与状态机流程，不能仅因提交更新就认为更适合本仓库。记录差异，但不伪造全部完成的 monitor 检查点。

只读取回 169 个选定文本文件的固定旧/新提交以便比较，其中 83 个有上游差异。这个集合不等于全部目录映射资源；未完整覆盖的目录资源仍保留待审状态。没有把摘要刷新用作“已完整同步”的证明。

### 资源不可用的 19 项

`simota/agent-skills` 的以下技能存在声明资源不可用：
`builder`、`gateway`、`schema`、`nexus`、`rally`、`oracle`、`guardian`、`triage`、`gear`、`ledger`、`growth`、`compete`、`pulse`、`tome`、`voice`、`scaffold`、`lens`、`scout`、`ripple`。

本地已授权副本保留。需要进一步核对上游重命名、迁移和新的完整 artifact 清单；不可用不等于可删除，也不等于已更新。全部来源判定见 JSON 记录。

## 公共技能的保留与淘汰决策

本次不新增、也不删除公共 canonical skill 路径，仍为 286 个技能。已有 v3.0.0 的 `senior-devops` 退役不重复执行。

组合路由、规划入口、Obsidian/LLM Wiki 与飞书场景入口包含客户端、状态或权限边界；静态组合评分偏低不构成删除依据。此次淘汰的是已经证实会给出虚假结果的内部模拟行为，而不是通过删技能制造“优化数量”。

建议客户端按需安装。`--all` 是所有客户端目标，不是低上下文预算的推荐默认值；README 中提供了只安装所需技能的预览命令。

## 验收与交付约束

```bash
python scripts/validate_repository.py --refresh
npm test
python scripts/reconcile_artifact_inventory.py --offline --check-clean --quiet
# 提交后的再次刷新必须没有跟踪文件差异
python scripts/validate_repository.py --refresh
git diff --exit-code
```

安装器额外测试在 Ubuntu/Windows、Node 22/24 上运行。PR 必须在最新 head 上通过检查；发布必须基于已合并 main 的精确 SHA，等待 Repository Validation、provenance 和 CodeQL 成功，不能用分支旧检查替代。

Release 包含源码包、npm 格式包、发布证据与 SHA256SUMS。先创建草稿并下载回验，逐文件核对 canonical 内容、版本、文件模式与摘要后再公开。不会发布 npm registry，也不会修改用户本机全局技能或客户端配置。

## 限制

未执行真实模型行为评测、Playwright 在线游戏会话、Hermes 生产 gateway、飞书真实会议、Neon/Supabase 数据库或全局 bundle 安装。原有 live/snapshot/不可用资源边界如实保留。通过静态检查和离线回归，不等于所有第三方版本、网络服务和生产流程均得到实测认证。
