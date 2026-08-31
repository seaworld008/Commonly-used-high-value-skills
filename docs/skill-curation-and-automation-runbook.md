# Skill Curation and Automation Runbook

这份 runbook 沉淀每周精选技能、上游同步、组合审计和自动化持续更新的实践经验。目标不是“尽可能多收集”，而是长期保持高价值、可追溯、可验证、可自动刷新的技能组合。

## 1. 维护目标

- 全库技能必须值得保留：低质技能要补强、替换或剔除。
- 外部来源必须可追溯：复制外部文本前先确认 permissive license。
- 未授权但高信号的候选只能做原创 in-house rewrite，不能复制 upstream 文本。
- 生成文件只能通过 pipeline 更新，不能手工改。
- 每周自动化必须使用当期可用的强推理 agentic coding 模型，并设置
  `reasoning_effort = high`；不要在治理规则中固定会过期的模型版本。
- 维护输出必须能回答：新增了什么、更新了什么、为什么没有删除、哪些外部源被阻塞、验证是否干净。

## 2. 每周推荐顺序

先更新已有技能，再发现新技能，最后做组合审计。这样可以避免在陈旧基线上重复引入已经被上游改进的能力。

```bash
git fetch origin --prune
gh auth status
git status --short --branch

python scripts/sync_upstream.py --check-only
python scripts/discover_new_skills.py --output docs/sources/reports/discovery.json
python scripts/audit_skill_portfolio.py
```

`--check-only` 默认严格只读。只有确实需要把成功检查时间写回 provenance 时，才显式使用：

```bash
python scripts/sync_upstream.py --check-only --record-check
```

同步通道遵循以下边界：稳定 release 或不可变 fixed ref 可在门禁通过后自动更新；默认分支、canary 和组合依赖只做 monitor，必须按 commit range 人工复核。

周期检查以机器报告为准，不以日志中的“0 updates”作为成功证明：

```bash
python scripts/sync_upstream.py --check-only \
  --report-json /tmp/upstream-report.json
```

`complete`/`degraded`/`failed` 分别使用退出码 `0`/`2`/`1`。`degraded` 必须保留或更新复核 Issue；`failed` 必须使自动化失败，不能关闭既有 Issue。报告的七项计数必须守恒。

如果发现有可应用的上游更新：

```bash
python scripts/sync_upstream.py --apply
```

如果发现新候选，先核验 license 和重复覆盖，再通过 ingestion 流程纳入：

```bash
python scripts/ingest_skill.py --dir skills/<category>/<skill-name> --source "<source_url>"
```

外部接入会先写独立 provenance v2 mapping，再执行 in-house bootstrap，避免外部技能被误登记为自研。GitHub 来源应同时给出精确路径；接入后用 artifact inventory 检查所有 sidecar 的所有权：

```bash
python scripts/ingest_skill.py \
  --dir skills/<category>/<skill-name> \
  --source "github:<owner>/<repo>" \
  --source-url "https://github.com/<owner>/<repo>" \
  --upstream-path "path/to/SKILL.md"
python scripts/reconcile_artifact_inventory.py \
  --output /tmp/artifact-inventory.json
```

任何技能变更后都跑完整 pipeline：

```bash
python scripts/enrich_frontmatter.py && \
python scripts/bootstrap_in_house_sources.py --write-json docs/sources/in-house.skills.json && \
python scripts/refresh_repo_views.py && \
python scripts/generate_tags_index.py && \
python scripts/build_catalog_json.py && \
python scripts/check_readme_sync.py && \
python scripts/lint_skill_quality.py --min-lines 50 && \
python scripts/audit_skill_portfolio.py --check-policy && \
python scripts/validate_skill_sources.py && \
python scripts/reconcile_artifact_inventory.py --offline --check-clean --quiet && \
python scripts/check_source_coverage.py --min-percent 100 && \
python scripts/audit_licenses.py && \
python -m pytest -q tests
```

## 3. 技能组合审计

`lint_skill_quality.py` 回答“能不能提交”，`audit_skill_portfolio.py` 回答“是否值得在高价值组合里保留”。每轮维护都应看组合审计，而不是只看 lint。

```bash
python scripts/audit_skill_portfolio.py
```

审计结果按 action 处理：

| Action | 含义 | 处理方式 |
|---|---|---|
| `keep` | 当前质量足够 | 保留；如有元数据小缺口则顺手修 |
| `review` | 组合价值或触发描述需要人工判断 | 优先补 `description`、`zh_description`、结构、示例、边界 |
| `improve` | 内容深度或可执行性不足 | 在同 PR 中补强；补不强则寻找替代 |
| `replace_or_archive` | 不适合继续作为高价值技能 | 找更优质 permissive 替代；没有替代则归档或删除 |

删除或替换前必须人工复核，不要只按分数机械删除。高质量但 upstream
消失的外部技能可以保留为 licensed `snapshot`，并在 v2 entry 与 origin
中标记 `sync_mode: archived` 或 `local-only`。不能把已复制的外部内容
简单改写成 `source: in-house` 来丢弃许可证 lineage；只有真正独立创作、
不再复制上游表达的重写版才可转为 in-house。

退役必须记录 decision ledger：替代项、独有资产、外部契约、许可证和安装端清理动作。只有替代技能完全覆盖意图，并且原技能没有独有脚本、高风险 guardrail、外部契约或验收标准时，才允许删除活动副本。

## 4. 精选新技能准入标准

新技能必须同时满足：

- 明确触发场景：frontmatter `description` 能让 Agent 判断何时使用。
- 内容可执行：不少于 50 行，优先不少于 100 行，有步骤、命令、模板或代码块。
- 覆盖不重复：不是现有技能的薄包装或同义复制。
- 作用域清楚：解决一个明确任务，不是泛泛的“提升效率”。
- 来源可追溯：`source`、`source_url`、license、provenance JSON 均完整。
- 中文公开面完整：必须有短且准确的 `zh_description`。

外部候选 license 决策：

| 上游状态 | 可做动作 |
|---|---|
| MIT / Apache-2.0 / BSD / ISC 等 permissive license | 可复制或同步，保留 license 与来源 |
| 无 license / license unknown | 不复制文本；只可原创 in-house rewrite |
| copyleft / commercial / unclear terms | 默认不纳入，除非仓库策略明确允许 |
| repo archived 但内容仍高价值 | 可保留本地快照，标记 archived，不再自动同步 |

## 5. 中文 frontmatter 完整性

`zh_description` 是中文 README、分类 README 和用户扫描体验的基础字段。新增或更新技能时不要只写英文描述。

检查缺失：

```bash
python - <<'PY'
from pathlib import Path
missing = []
for p in sorted(Path("skills").glob("*/*/SKILL.md")):
    parts = p.read_text(encoding="utf-8", errors="replace").split("---", 2)
    if len(parts) < 3 or "\nzh_description:" not in "\n" + parts[1]:
        missing.append(str(p))
print("missing_zh_description", len(missing))
if missing:
    print("\n".join(missing[:50]))
PY
```

批量补齐历史缺口时使用脚本，不要手写生成物：

```bash
python scripts/backfill_zh_descriptions.py --dry-run
python scripts/backfill_zh_descriptions.py
```

如果早期机器生成描述过于泛化，可刷新脚本识别到的生成描述：

```bash
python scripts/backfill_zh_descriptions.py --refresh-generated
```

补齐后必须跑完整 pipeline，让分类 README、OpenClaw export、catalog 和 tags index 保持一致。

## 6. 外部阻塞源处理规则

每周自动化会遇到网络和上游状态噪声。不要把外部噪声误判成仓库回归，也不要把真实元数据问题当成噪声忽略。

| 信号 | 分类 | 处理 |
|---|---|---|
| ClawHub 偶发 SSL EOF | 外部临时噪声 | 重试；若 discovery 仍部分失败，在总结中记录 source health |
| GitHub raw 旧路径 `404` | 可能是 provenance 陈旧 | 先尝试用 GitHub API / source_url 精确路径修复；确认消失后标记 archived 或 local-only |
| `IncompleteRead` / TLS handshake 超时 | 外部临时噪声 | 脚本应短重试，不应中断整轮维护 |
| GitHub API `403` rate limit | 外部限流 | 优先使用 `gh auth status` 和本地 gh token；记录 partial check |
| license missing / unknown | 仓库治理问题 | 必须修复或改 in-house，不能只记录 |
| generated diff drift | 仓库生成链路问题 | 重新跑 pipeline 并提交生成结果 |

同步脚本应优先使用 provenance 中的精确 upstream path。对已归档或本地维护
的来源，要同时更新 v2 entry、origin 和兼容层 `upstream`，不能只改 legacy
字段。例如：

下面两个片段只展示状态迁移时必须同步修改的字段；未展示的 provenance
v2 必填字段仍须保留并通过 schema 与 repository validator。

```json
{
  "kind": "snapshot",
  "sync_mode": "archived",
  "upstream": {
    "sync_mode": "archived",
    "archived_at": "2026-06-29"
  },
  "origins": [{
    "repo": "owner/repo",
    "sync_mode": "archived",
    "tracking": {
      "channel": "fixed_ref",
      "ref": "<immutable-commit>",
      "resolved_commit": "<immutable-commit>"
    }
  }]
}
```

或：

```json
{
  "kind": "snapshot",
  "sync_mode": "local-only",
  "upstream": {
    "sync_mode": "local-only"
  },
  "origins": [{
    "repo": "owner/repo",
    "sync_mode": "local-only",
    "tracking": {
      "channel": "fixed_ref",
      "ref": "<immutable-commit>",
      "resolved_commit": "<immutable-commit>"
    }
  }]
}
```

## 7. 替换和剔除策略

只有同时满足以下条件时才剔除技能：

- 组合审计为 `replace_or_archive` 或人工确认低价值。
- 内容无法通过合理补强达到本仓库标准。
- 没有独特触发场景，或与现有技能高度重复。
- 删除不会破坏一个重要类别的能力覆盖。
- provenance、README、OpenClaw export 和 catalog 可通过 pipeline 收敛。

优先替换而不是直接删除。替换候选必须比原技能在至少两个维度上更好：更清晰触发、更深内容、更好示例、更可信来源、更活跃维护、更明确 license。

如果没有更优替代，但本地版本仍有价值，应保留为带原许可证 lineage 的
`snapshot`；只有完全原创重写的内容才改为 `in_house`。不能为了“清空
warning”删除仍有独有价值的能力。

## 8. PR 和分支策略

### 组合依赖的稳定版升级

当 `sync_upstream.py --apply` 报告需要 dependent review 时，先阅读组合
技能及新依赖的变更，确认状态根、权限、安装与验收边界仍兼容。然后将
当前组合 SKILL.md 的 SHA-256 作为显式审批传入：

```bash
python3 scripts/sync_upstream.py --apply --source github:OWNER/REPO \
  --reviewed-dependent COMPOSITE-SLUG=REVIEWED_CANONICAL_SHA256
```

占位值必须替换为本次审查的真实 slug 与摘要。脚本按全局事务锁、排序后的
mapping 锁、技能锁顺序操作；先恢复 mapping journal，再判断 artifact
authority。所有依赖锁与来源映射一起提交，失败恢复旧状态。不要手工预先
改锁、伪造摘要或关闭完整来源校验。

上游删除的有用许可资产可以保留为非 canonical 的 archived sidecar，
但必须记录真实外部来源、许可和与 resolved_commit 相同的不可变 fixed_ref；
不能变成第二个活动同步来源。后续 digest 刷新不得复活该 archived origin。

### 分支与合并

每周维护尽量拆成可审查 PR：

- 上游同步 PR：只包含 upstream sync 和必要质量修复。
- 新增技能 PR：只包含少量精选新增技能。
- 审计/治理 PR：脚本、frontmatter、文档、生成视图收敛。

分支命名使用 `codex/` 前缀。PR 标签优先加 `codex`；自动化发起的 PR 还应加 `codex-automation`。

合并前必须满足：

- `git diff --exit-code` 干净。
- 完整 pipeline 通过。
- `python scripts/audit_skill_portfolio.py` 没有 `improve` 或 `replace_or_archive`；如果仍有 `review`，PR 摘要必须解释原因和后续计划。
- license audit 中 `MISSING = 0`，`UNKNOWN = 0`，除非有明确的暂存说明且不涉及复制外部文本。
- 如果改动影响安装体验，必须验证 `node --check bin/install-skills.js`、`node bin/install-skills.js --help` 和 `npm pack --dry-run`。

## 9. 自动化配置要求

每周技能维护任务需要高推理预算，避免低模型把外部噪声误判为“无变化”或错误复制无 license 内容。

推荐配置：

```toml
model = "gpt-5.6-sol"
reasoning_effort = "high"
```

模型标识会随运行平台演进；每次调整自动化时都应核对当前可用的高能力
agentic coding 模型，不要从旧周报或历史配置中照抄已过时的 ID。

自动化运行结束必须更新 memory，至少记录：

- 运行时间。
- 已合并 PR 和 merge commit。
- 新增、更新、删除或保留的技能。
- 组合审计 action mix。
- 完整 pipeline 和测试结果。
- 外部阻塞源：ClawHub、GitHub rate limit、旧 raw path 404、DNS/TLS 问题。
- 是否有下一轮待办，尤其是 `review` 队列、license 缺口或 missing `zh_description`。

## 10. 最终健康目标

每周维护结束时，理想状态是：

- `missing_zh_description 0`
- `audit_skill_portfolio.py`: 全部 `keep`，或剩余 `review` 有明确解释
- `lint_skill_quality.py --min-lines 50`: 0 FAIL / 0 WARN
- `audit_licenses.py`: missing 0 / unknown 0
- `check_readme_sync.py`: OK
- `node bin/install-skills.js --help`: OK
- `npm pack --dry-run`: OK
- `python scripts/validate_skill_sources.py`: OK
- `python scripts/check_source_coverage.py --min-percent 100`: OK
- `python -m pytest -q tests`: OK
- `git status --short --branch`: 干净并同步 `origin/main`

这组指标比单独的“发现了多少新技能”更重要。仓库的核心价值来自长期精选和可维护性，而不是数量增长。
