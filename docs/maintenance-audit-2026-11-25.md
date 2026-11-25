# 2026-11-25 补丁修复、审查收尾与基础能力升级报告

本次维护在 `v7.0.0`（`3322e606`）基础上于隔离工作分支 `codex/v7.0.1-rls-and-maintenance` 完成 `database-designer` 多租户行级安全（RLS）模板补丁、PR #164 其余 3 项审查意见修复、跨平台 LF 换行规范化、浏览器基础能力升级与活跃上游同步，形成可复现的 `v7.0.1` 补丁发布。

## 核心补丁与 PR #164 审查闭环

1. **`database-designer` 多租户 PostgreSQL RLS 成员校验补丁（PR #164 P1）**：
   - 修复 `skills/developer-engineering/database-designer/references/orm-and-rls-patterns.md` 合并旧指南时遗漏父表 RLS 与组织成员过滤的问题，同步刷新 `openclaw-skills/database-designer/` 镜像并更新主入口 `SKILL.md`（`v1.0.4`）与 `README.md` 目录说明。
   - 补全 `organizations`、`users`、`organization_members`、`projects`、`tasks` 完整可执行 DDL 与复合/部分索引；创建无 `BYPASSRLS` 的非表所有者角色 `app_user` 并执行最小权限授权（排除 `project_id`、`created_by_id` 与 `deleted_at` 的直接 `UPDATE`，禁止修改 `organization_members`）。
   - 同时对 `organization_members`、`projects`、`tasks` 启用 RLS，并在 `org_members_self_read`、`projects_member_read`、`tasks_read`、`tasks_insert`、`tasks_update`、`tasks_delete` 中显式校验 `organization_members` 成员关系及角色权限。
   - 针对 PostgreSQL 对带 `WHERE` 的 `UPDATE` 也会检查 `FOR SELECT` 策略（`deleted_at IS NULL`）的语义特性，补充受控 `SECURITY DEFINER` 函数 `soft_delete_task(p_task_id TEXT)`（固定 `SET search_path = pg_catalog, public`，校验 `app.current_user_id`、组织成员与创建者/管理员权限）并仅向 `app_user` 授予 `EXECUTE`。
   - 新增真实 PostgreSQL 回归测试 `tests/test_database_designer_rls.py`：由非超级用户 `schema_owner` 建表并建策略，切换至非所有者角色 `app_user` 验证双租户正反向隔离、伪造身份/越权篡改拦截、只读 `viewer` 写入拒绝、创建者与管理员删除分层及未设会话用户 fail-closed 行为。
2. **PR #164 其余 3 处 P2 审查项修复**：
   - `skills/knowledge-and-pm-integrations/lark-contact/SKILL.md`（`1.0.8`）：Step 3 批量邮箱解析改用受支持的 `lark-cli contact +search-user --queries 'alice@example.com,bob@example.com' --as user`（替代不支持 `--emails` 的 `+get-user`）。
   - `skills/knowledge-and-pm-integrations/lark-skill-maker/SKILL.md`（`1.0.8`）：Step B 日程预览示例改用 `lark-cli calendar +create` 与 `--attendee-ids`（替代不存在的 `+event-create` / `--attendees`）。
   - `skills/ai-workflow/find-skills/references/catalog-query-recipes.md`（入口 `SKILL.md` `1.1.3`）：将两段内嵌双引号冲突的 `python3 -c "..."` 改写为单引号保护的 `python3 - <<'PY' ... PY` heredoc，并在回归测试中直接通过 `bash` 实测两段配方均以退出码 `0` 正常输出。
3. **跨平台行尾一致性加固（`.gitattributes`）**：
   - 在 `.gitattributes` 顶部新增 `* text=auto eol=lf` 及常见二进制文件 `-text` 规则，保留末尾针对 `playwright/LICENSE.upstream.txt`、`THIRD_PARTY_NOTICES.md`、`canvas-fonts/*.txt` 的既有 `-text whitespace=...cr-at-eol` 特例，避免 Windows 宿主 `core.autocrlf=true` 检出 CRLF 破坏 provenance SHA-256 校验。

## 浏览器基础能力与上游技能同步

- **浏览器基础能力全面升级（`check_browser_foundations.py` 复检 `7/7 current`、`Browser foundations: complete`）**：
  - `agent-browser` 升至 **`0.44.0`**（`v0.44.0`，`0a923358ea989d7602f0d06507ad3447c62ffe9b`）：同步 `upstream-core.md` 及 `commands.md` / `session-management.md` / `snapshot-refs.md` / `streaming.md` / `trust-boundaries.md`，更新跨文档 ref `"no longer loaded"` 错误说明、WebMCP `[origin]`/`cross-origin` 标记与内联 JSON 参数、`--allowed-domains` 空列表 fail-closed、`tab keep` 与 `vercel` 技能改名。
  - `browser-testing-with-devtools` 适配 **`chrome-devtools-mcp 1.14.0`**（`chrome-devtools-mcp-v1.14.0`）：补充 `--backgroundNewPages`、`serviceWorkerId`（`sw-N`）网络与控制台查询、`get_css_styles` 计算样式与 CSS 变量内联解析、透明截图、网络 mock 的 abort/allow-origin 支持与工具期页面报错回传。
  - `modern-web-guidance` 升至 **`1.0.2`**（`v1.0.2`，`2b4aa13a72dd47cd135b06ce5abfccd92e19b24f`）及 `modern-web-guidance-src`（`92686ac7d6ebd6c794b575335a7ff4a3e7f66ecb`）：更新版本固定调用、补充 `js` 学科级指南提示与 `context-menu`/`teaser` 新指南说明。
- **活跃上游技能同步与策展**：
  - `hermes-agent`：由 `v0.23.3` 同步至官方稳定版 **`v0.23.4`**（`8fc0374447313e276f6b9a2764bfc750190c966a`，技能正文与 24 个管理文件一致，更新 `tests/test_official_hermes_artifact_set.py` 固定版本基线）。
  - `graphify`：完成 `v0.9.111..v0.9.119`（`ba33a181f88b6ff675699decf4878566af851ab3`）人工差异审阅，Codex 技能与 8 个引用文件未变，推进监控检查点。
  - `accessibility-engineering`：吸收 `addyosmani/agent-skills` 对 `scripts/audit-a11y.sh` 相对于加载技能目录的绝对路径解析说明（`v1.0.1`），保留本仓扁平 `references/` 与 `0755` 权限。
  - `security-and-hardening` 与 `addyosmani/agent-skills` 检查点：吸收 `hardening-patterns.md` 中 SSRF 连接时过滤与保留 `Host`/TLS SNI 证书校验的 TOCTOU 防护说明，并将全部 25 项 `addyosmani/agent-skills` 监控条目推进至 `e997ac5b9a74eab332d5e9793bb38a38c8cfdd74`。
  - `x-twitter-scraper`：吸收 `Xquik-dev/x-twitter-scraper` `references/monitors-webhooks.md` 中 6 组 30 类账号监控事件及 `POST /monitors/posts` 说明（`v1.0.10`），保留本地全部安全与实时估算护栏。

## 验证范围与已知边界

- **本地与 CI 验证边界**：本次验证覆盖原生 Linux 环境下的 `validate_repository.py --refresh`、真实 PostgreSQL 18.6 非所有者 `app_user` 租户隔离测试（`tests/test_database_designer_rls.py`）、`check_browser_foundations.py`、`npm test`、Node 安全单测、仓库健康评分及生成幂等性检查；上述检查不替代在线真实 LLM 模型端到端评测或飞书/Xquik 实盘账号联调。
- **外部来源已知限制**：21 个 `openai/skills` 条目因上游 `LICENSE.txt` 在 Apache-2.0 末尾附加微软版权声明及上游仓库提示迁移至 `openai/plugins`，在自动 SPDX 校验中仍返回 `unavailable`，本版继续保留仓库内既审可用快照。
