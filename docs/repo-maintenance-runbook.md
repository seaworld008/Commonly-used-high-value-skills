# Repo Maintenance Runbook

这份 runbook 说明如何维护本仓库的治理链路，让来源、许可证、死链和整体健康度持续保持稳定。

## 1. 日常维护目标

- `skills/` 仍然是唯一事实来源
- 外源技能必须带可解释的 `source` / `source_url` / `license`
- 生成物不手改，统一通过脚本刷新
- 仓库健康度以 `repo-health` 报告为总览入口

## 2. 关键报告与它们回答的问题

### Repo Health

- 文件：
  - `docs/sources/reports/repo-health.json`
  - `docs/sources/reports/repo-health.md`
  - `docs/sources/reports/repo-health-eval.md`
- 用途：
  - 一眼看全局健康状态
  - 用阈值规则判断当前是 PASS 还是 FAIL
  - 重点关注：
    - source coverage
    - license audit
    - dead links
    - refresh queue
    - source slug conflicts

### License Audit

- 文件：
  - `docs/sources/reports/license-audit.json`
  - `docs/sources/reports/license-audit.md`
- 用途：
  - 检查外源技能是否缺失许可证元数据
  - 原则：
    - `MISSING` 必须清零
    - `UNKNOWN` 只在无法严肃确认上游许可证时短暂存在

### Dead Links

- 文件：
  - `docs/sources/reports/dead-links.json`
- 用途：
  - 检查仓库 Markdown 中真实外链是否失效
  - 注意：
    - 模板 URL、占位 URL、内部示例 URL 已由扫描器忽略
    - 如果报告重新出现大面积坏链，优先检查最近新增的技能示例

### Refresh Queue

- 文件：
  - `docs/sources/reports/refresh-queue.json`
- 用途：
  - 判断哪些来源映射已经变陈旧，需要下一轮巡检

## 3. 本地推荐维护流程

### 快速检查

```bash
python3 scripts/audit_licenses.py \
  --output-json docs/sources/reports/license-audit.json \
  --output-md docs/sources/reports/license-audit.md

python3 scripts/check_dead_links.py \
  --output docs/sources/reports/dead-links.json

python3 scripts/generate_repo_health_report.py
python3 scripts/evaluate_repo_health.py
```

### 完整刷新

```bash
python3 scripts/refresh_repo_views.py
python3 scripts/build_catalog_json.py
python3 scripts/generate_tags_index.py
python3 scripts/validate_skill_sources.py
python3 scripts/check_source_coverage.py
python3 scripts/generate_repo_health_report.py
```

### 推荐测试

```bash
python3 -m unittest \
  tests.test_evaluate_repo_health \
  tests.test_check_dead_links \
  tests.test_generate_repo_health_report \
  tests.test_audit_licenses \
  tests.test_repo_validation_workflow \
  -v
```

## 4. 发现问题时怎么处理

### 情况 A：license audit 出现 `MISSING`

处理顺序：

1. 先补 `license:` 字段
2. 如果能确认具体上游，再补 `source_url`
3. 如果该技能已经明显是仓库整理版，而不是单一转载件，评估是否应改为 `source: in-house`

### 情况 B：dead links 增加

处理顺序：

1. 先判断是不是模板链接 / 占位链接 / 示例假链接
2. 如果是模板例子，改成更明确的占位形式
3. 如果是真链接，优先替换为稳定文档地址
4. 重新生成 `dead-links.json` 与 `repo-health`

### 情况 C：source coverage 下降

处理顺序：

1. 先看新增技能是否没进来源映射
2. 优先更新 `docs/sources/*.skills.json`
3. 再跑 `bootstrap_in_house_sources.py` / `validate_skill_sources.py`

## 5. CI 中当前已经自动做的事

`repo-validation.yml` 现在会自动执行：

- 质量 lint
- license audit
- 生成 repo health 报告
- 评估 repo health 阈值
- 关键测试
- generated files diff 校验
- 上传 `repo-health` artifact

`dead-links.yml` 会定期执行：

- 死链扫描
- 生成 dead-links 报告
- 如有问题则自动开 issue

## 6. 维护判断原则

- 能严肃确认来源和许可证，就精确回填
- 证据不足时，不要为了“看起来干净”乱填元数据
- 如果技能已经经过明显的中文化、扩写和结构重写，且无法唯一对应上游，应考虑改为 `in-house`
- 统一健康报告优先于零散脚本输出，先看总览，再钻细节

## 7. 目标状态

理想状态下，`repo-health` 应接近：

- source coverage = `100%`
- license missing = `0`
- license unknown = `0`
- dead links = `0`
- refresh queue = `0`
- source slug conflicts = `0`

如果这些指标全部满足，就说明仓库治理面处于稳定状态。
