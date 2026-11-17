# Team Collaboration Guide

共享经过审阅的纠错知识，以领域和出处为边界，不共享凭据或含原稿历史的整个数据库。沿用已有团队 setup、字典维护及发布授权；工具不额外增加审批循环。

## Current Entry Points

核心 CLI 当前支持 `--add`、`--list`、`--init`、校正和校验。`--import`、`--merge`、`--export`、`--export-json` 尚无参数入口；不能照旧选项运行或把未知参数退出 2 当成功。`--review-learned`、`--approve` 是占位，不会批准条目。

命令在技能根目录运行，数据库优先选 `TRANSCRIPT_FIXER_DB_PATH`，否则用 `TRANSCRIPT_FIXER_CONFIG_DIR/corrections.db`（目录默认 `~/.transcript-fixer`）。学习和自动批准默认关闭；普通校正不隐式启用。

## Knowledge Exchange

团队可以人工维护 JSON 词条，或在已授权环境使用经过审阅的 Service API，格式参考 `file_formats.md`。交换条目应包含：

- 错误短语、正确短语及 domain。
- 源文支持的使用场景与必要的反例。
- 人工审阅状态、来源和版本，不附无关原稿正文。
- 规则优先级和潜在冲突；避免无条件短词替换。

示意记录（是策展格式，不保证为某个导入器的直接输入）：

```json
{
  "domain": "embodied_ai",
  "from_text": "巨升智能",
  "to_text": "具身智能",
  "reviewed": true,
  "counterexample": "人名或引用按原文保留"
}
```

收件人先核对领域、出处与现有词条，再将已确认条目加入所选字典：

```bash
python scripts/fix_transcription.py --add "巨升智能" "具身智能" --domain embodied_ai
python scripts/fix_transcription.py --input small_sample.md --stage 1 --domain embodied_ai
```

批量输入可参考 `scripts/examples/bulk_import.py`，先审查其文件格式、数据库路径及更新行为，不直接运行未审阅队友脚本。脚本示例不是通用自动 merge 的保证。

## Conflict Resolution

以 `from_text + domain` 识别键冲突：

1. 新词条也须检查源语义与反例，再添加。
2. 同键同值可去重，保留出处和审阅证据。
3. 同键异值先比较语境；必要时使用完整短语、上下文规则或不同领域，不能按较高“confidence”自动覆盖。
4. 删除和停用保留理由，防止下次同步复活误词。
5. 在小样本运行 Stage 1，核对预期命中与不应改写的反例。

财务领域“股价”可能完全正确；机器人语境“股价系统”才可能是“框架系统”。按行业/项目分开维护，避免 general 词典污染所有团队。

## Git Workflow

使用单独的共享知识目录保存经过审阅的 JSON 和说明，数据库所在目录不是代码仓库的必选位置。不要假定运行程序会自动生成 corrections.json、domains/ 等文件。

用小批次、明确主题的变更记录或 PR 比较新增条目、删除条目及反例；为 finance、medical、embodied_ai 等领域指定合适审阅者。拉取合并按既有团队流程处理，手动解决同键异值；不能全选 ours/theirs 丢弃他人已审阅条目。

忽略 `*.db`、`*.db-wal`、`*.db-shm`、`*.db-journal`、备份、原稿及凭据文件。只分享必要的审阅知识，不复制 correction_history 或 suggestion_examples 的敏感上下文。自动 cron/CI 推送不是默认行为，需在既有发布范围内专门配置，不能由普通校正顺带创建。

## Selective Domain Sharing

- Finance：核对数值、财务口径与真实“股价”用法；不接收未经审阅的通用同音替换。
- Embodied AI：核对术语、产品和公司名，保留跨领域歧义反例。
- Medical：核对源文术语与说话人，不把推测变为事实。
- 项目领域：使用核心 CLI 支持的合法自选名；包装器仅提供四个内置领域选项。

成员可以合并多个领域的已审阅知识，但每次运行明确选择领域，不宣称简单合并可自动解决语义冲突。

## Backup and Recovery

更改前为所选数据库制作一致备份。活动 WAL 可能包含唯一已提交数据，不能只复制主库而遗漏 WAL。使用维护者控制的 SQLite backup 或停写后的一致副本，恢复先在独立目录检查词条、约束和样本效果；不直接覆盖原库。

`--validate` 是零写入校验，不执行恢复/迁移。存在侧车或复制期间变化时明确未验收并返回 1。需要验证时，提供无活动侧车的静止一致副本；不要删除侧车或为了“健康”重建 schema。Git 中的知识记录只能恢复词条版本，不能代替数据库历史和审计的完整备份。

## Verification and Delivery

运行小样本 Stage 1，语义复核后按授权调用 AI；Stage 2 是累计词典和 AI，产物为 `*_stage1.md`、`*_stage2.md`。Stage 3 只提示 diff；如需 HTML：

```bash
python scripts/generate_word_diff.py original.md corrected.md review.html
```

默认不开浏览器。报告本次退出码与 manifest 的 outputs，失败时明确部分交付，不能沿用旧文件。CI 可以检查 JSON 语法、键唯一性、领域、出处和样本反例，但不能把静态检查称为真实提供商或领域专家评测。
