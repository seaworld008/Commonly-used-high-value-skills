# 2026-09-07 技能组合维护与收尾检查

## 组合与来源

- 保持 284 个规范技能、36 个永久退休墓碑；无新增、退役或合并技能，辅助制品保留。更新 Supabase/Postgres 数据库专用验收指导与 Supabase 文档入口。
- 初始全量来源扫描 149 项：116 equal、8 monitor review、25 个政策保留快照、0 unavailable、0 rollback。8 项已人工复核并记录至精确提交；三组定向复扫均无剩余 monitor review。
- Graphify `v0.9.47..v0.9.55`：156 个提交，Codex 入口和 8 个 reference blob 完全一致。
- Hermes `77915e34..693641aa`：159 个提交，6 个监控技能入口 blob 不变；稳定发布仍为 `v2026.8.31`。
- NLPM `dffbb03c..eb6b088f`：10 个提交只改变报告、追踪与仪表盘，受管 README 不变。
- Issue #93 的 Lark/Hermes 历史提交已被现有复核检查点覆盖，附比较证据关闭；候选按能力缺口筛选，没有数量型扩充。

## 修复与审查

- PR #102 优化 Postgres supplement 与 monitor 检查点；合并命令未 fail-fast，导致两条新审查意见未处理即合并。随后 PR #103 修复更新日期和 review 记录选择，原线程全部回复并解决。后续合并独立检查成功状态、未解决线程、当前 head，并使用 `--match-head-commit`。
- PR #104 修复 checkout 与 create-pull-request 的重复 Authorization header，固定 MIT 许可的 create-pull-request v8.1.1；Changelog 重跑 `34074618417` 成功。
- PR #99 刷新后仅新增 15 行，既有历史保留；6 项 CI 和该 head 的 Codex Review 完成后合并。
- 收尾检查发现 catalog/tag 解析把嵌套 metadata 提升为顶层字段，覆盖本地版本、作者、触发描述和标签。两个生成器现在忽略缩进行，与仓库现有顶层解析约定一致，新增回归用例。
- 健康评估器支持仓库外输出路径，回归测试改用仓库外临时目录。
- 修复 Supabase `monitoring-and-debugging.md` 的真实 404，官方现行入口为 `observability.md`，直接请求返回 200。

## 验证范围

- 完整本地管线：563 pytest 通过；287 strict PASS、0 WARN/FAIL；284 个入口指令审计无发现。
- 组合 271 keep / 13 review；墓碑违规 0。155 个外部许可条目合规，缺失/禁止许可 0；来源覆盖 284/284，2,286 个受管文件无摘要、模式或归属欠账。
- 全量外链复扫 390 个地址，按现有探测政策不可达 0。Semantic Scholar 存在 429 限流，首轮一个请求超时后重试恢复；429 表示服务可达但访问受限，不是 API 功能成功。
- Issue #100 的原始地址已复查；新增 Supabase 404 已修复。未通过忽略域名或放宽状态码掩盖错误。
- 工作流 actionlint、Python 编译、Node 语法/help/targets、npm pack dry-run、OpenClaw 视频映射、健康评估、生成器幂等及 diff 空白检查通过。
- 两次孤儿 index.lock 经确认无进程/句柄持有后精确移除；失效 worktree 记录未清理，客户端与运行时未安装。
- 这些是仓库、来源和静态验证证据；不表示数据库生产性能、在线迁移或模型任务成功率已经实测。
