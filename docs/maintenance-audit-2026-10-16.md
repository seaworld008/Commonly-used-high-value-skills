# 2026-10-16 上游策展与兼容性修复

基线为 `a655526c`（v4.0.0）；开始时 `main` 干净。维护分支为 `codex/upstream-curation-20261016`。

## 已交付的修改

- 更新 34 个公开技能和 AKS 嵌套 readiness，公开总数仍为 294；无新增、退休、改名或合并技能，退休 tombstone 保持不变。
- 工程工作流：修复 React 重试示例、错误边界状态、空白字符串校验，以及 24 份已有性能清单中的 shell/JavaScript 围栏混用。补入保留决策证据和限定条件的文档审阅方法；保留本地 TDD 触发边界，没有照搬更宽的上游触发描述和重复的反例表。
- Lark：补入任务分组的归属与分页流程及完整参考；更新 Base 人员提及示例、Docx/Wiki 与妙搭 `/page/` 路由，以及 Slides 图表 XSD。XSD 支持气泡、瀑布、帕累托及 OOXML 属性；验证了新字段边界和废弃 `gap` 字段的拒绝行为。
- AKS：移除虚构的 readiness assessment API 和原地 Standard→Automatic SKU 切换流程；使用实际可发现的元数据读取、离线规则评估与脱敏工作负载投影。保留本地文件修改的已有授权逻辑，区分条件性策略和默认阻塞。完整纳入 `sanitize-readiness-input.jq` 与可选运维能力参考，没有执行云端操作或安装插件。
- Neon：更新 BM25 非匹配过滤、混合检索候选上限与 embedding 维度/编码参考；保留现有连接、ORM 和授权边界，没有引入未安装的 `neon-realtime` 依赖。
- 调试与审阅：诊断示例只报告环境变量是否存在，不输出值；修正 Git SHA 提取示例；ADHD 示例不再无关地安装依赖。
- HTML 渲染器：修复 macOS `/tmp` 和 `/private/tmp` 别名下的受管报告更新；统一父目录真实路径，保留最终文件的 `O_NOFOLLOW`。新增别名成功与文件符号链接拒绝回归。

## 已记录的逐提交审阅

| 来源 | 本轮检查点 | 条目数 | 许可证 |
|---|---|---:|---|
| addyosmani/agent-skills | `aeac41d4d005999432bb7312f7ff06383a91d59d` | 24 | MIT |
| larksuite/cli | `017b19a793ad71794a02887ede04757f3d82e10d` | 23 | MIT |
| obra/superpowers | `bb92a77741419a4ab5f06e711a283343f1ada0c3` | 11 | MIT |
| ayghri/i-have-adhd | `1ecea1993b7fce257ffbd686c070948b5e07eda6` | 1 | MIT |
| microsoft/azure-skills | `d1736f313f7a5259006325d8c9dbce046ed128c0`；诊断快照仍为 `0727d81638d64b6888f796287ee00baecfb08ced` | 2 | MIT |
| neondatabase/agent-skills | `5e693d6d5ddbe11d72c93e3b594ecfe574de44b2` | 2 | Apache-2.0 |

完整比较了 Lark、工程工作流和上述已更新来源的受管文件；没有文本变化的同源条目也记录了审阅检查点。保留全部原有 LOCAL-QUALITY-SUPPLEMENT / LOCAL-CURATION-SUPPLEMENT 块和历史归档 sidecar。新增的 3 份资源已进入 provenance v2 与 OpenClaw 导出，不依赖未跟踪文件。

## 未关闭的上游事项与合并门禁

- 在线检查 `live-panel` 的固定来源 `ythx-101/live-panel-skill@2a5dc1ea9983c193f20c9ff4000c8a11efb3b5e1` 时，许可证提供器返回 `immutable license content produced 0 canonical SPDX matches []`。原文含 MIT 正文及第三方示例设计/表述权利说明；本轮保留原文和现有资产，没有放宽许可识别规则。
- Simota 的完整 tree 比较发现 154 份受管文件变化；部分 diff 获取发生 TLS/EOF，且新内容涉及未打包的共享契约，未推进这些条目的审阅检查点。
- Graphify、Xquik、LinkedIn、Grill Me 和 Hermes 的其他变更仍在审阅队列。部分 GitHub compare 达到 300 文件上限，已用完整 Git tree 补核变化范围；tree 观测不等于正文策展完成。
- Hermes 稳定版虽允许自动同步，相关桌面插件正文的读取未完成，且包含 PM 安装/环境契约变更；没有在不完整审阅下替换正文或组合依赖。
- GitHub API/clone 的 EOF、TLS 错误与本地质量失败分开记录。全量检查及逐源结果见同名 JSON；不能将本轮描述为全部上游已同步。按本次维护授权，PR 保持未合并，直到许可和待审来源问题关闭。

## 验证范围

用户指定顺序的刷新与完整检查通过：690 个测试、严格质量检查（297 PASS / 0 WARN / 0 FAIL，含嵌套入口）、指令检查零发现、退休策略零违规、来源覆盖 294/294、来源/许可证元数据审计、冲突标记、OpenClaw 视频来源、健康阈值、Python 编译、Node 安装器语法/help/targets、npm pack dry-run 和 `git diff --check`。新增 jq 测试验证秘密与未知字段不进入输出、保留 readiness 字段，并正确统计同命名空间的重复 Service selector。

许可证元数据审计通过不代表在线来源许可识别阻塞已经解决；健康 PASS 不代表全部来源新鲜度通过。未执行真实 Lark、Azure、Neon、X 或 Hermes 集成验收，也没有进行模型行为评测。提交后的生成幂等性和 PR 检查结果在交付时单独记录。
