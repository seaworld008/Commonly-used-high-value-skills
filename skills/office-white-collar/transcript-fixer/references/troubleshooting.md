# Troubleshooting Guide

命令在技能根目录运行。先记录退出码、本次输出清单和所选数据库路径，不复制凭据或原稿正文到诊断日志。现有 setup/维护授权持续复用。

## API Authentication Errors

### GLM_API_KEY Not Set

Stage 2/3 需要显式进程环境中的 `GLM_API_KEY`。包装器在启动核心 CLI 前检查；核心 CLI 在 Stage 1 后检查，失败退出 1。安全存在性检查：

```bash
python -c 'import os, sys; sys.exit(0 if os.environ.get("GLM_API_KEY") else 1)'
```

有非空值返回 0，缺失或空值返回 1；不打印原值。shell 即使开启 xtrace，命令参数也不含 key。不要用 echo、printenv、env 全量输出或 shell 变量展开检查密钥。通过已授权的安全方式向进程注入凭据，不去搜索 shell 登录文件、其他账号或密钥目录；不要在追踪 shell 中输入真实密钥赋值。

### Invalid API Key / Provider Failure

401/403：通过提供商授权界面核对权限与配额；避免将请求头或完整异常正文贴进日志。网络/模型失败：记录脱敏状态和本次 manifest，Stage 2 未生成时报告部分交付并返回失败，不把旧文件当新结果。脚本不保证任何宿主专用 fallback 标记。已有授权下可改用 Stage 1 或人工校正，保留原稿与不确定性。

## Dependency Errors

`requirements.txt` 声明 httpx、filelock；包装器从该文件生成相同 uv 依赖参数。普通环境须两者齐备。HTTP/2 为可选能力，不以强制安装 h2 代替支持 HTTP/1.1。在线安装与提供商调用均是独立运行验证，不能从静态依赖检查推断已通过。

## Learning System Issues

学习默认关闭，未启用时没有历史/候选是预期结果。`--review-learned` 和 `--approve` 是未实现的占位命令；返回 0 不能表示已经审阅或批准。收集错误短语、正确短语、领域、来源和反例，人工确认可复用后在已授权字典维护中使用：

```bash
python scripts/fix_transcription.py --add "巨升智能" "具身智能" --domain embodied_ai
```

显式启用学习和自动批准是两个独立开关，不能因用户要求单次校正就自动打开。频率与置信度阈值是候选筛选依据，不能替代语义复核。

## Database Issues

### Database Not Found

`--validate` 报所选 `config.database.path` 缺失并退出 1，不创建它。路径优先来自 `TRANSCRIPT_FIXER_DB_PATH`，否则来自 `TRANSCRIPT_FIXER_CONFIG_DIR/corrections.db`；目录默认 `~/.transcript-fixer`。一次性 Stage 1 可在没有持久库时运行。需要字典且已有 setup 授权时才执行 `python scripts/fix_transcription.py --init`，然后重新验证；不要将初始化后的状态声称为原来健康。

### WAL / Locked Database: not verified

`--validate` 不打开用户 SQLite 连接。存在 `-wal`、`-shm`、`-journal`时保守退出 1 并报告 `not verified`。已完成 checkpoint 且无侧车的 WAL 库可以按静态快照检查，源文件发生变化时仍明确未验收。

- 不删除、截断或忽略 WAL；其中可能有唯一的已提交数据。
- 不为 preflight 自动 checkpoint、VACUUM、迁移或切换 journal_mode。
- 让已授权维护者在停写后提供一致非 WAL 副本，或用 SQLite backup 机制生成独立一致副本供后续处理；必要格式转换只作用于私有副本。
- 若复制前后源文件变化，同样未验收，待库静止后重试。不要为通过测试杀死不属于自己的进程。

### Corrupted Database / Missing Tables

`--validate` 对无活动侧车的静态源创建私有快照，检查文件头、SQLite integrity 和八张必需表。空文件、非 SQLite 文件、缺表均退出 1；不构造会初始化 schema 的 Repository。

缺表并不意味着可以“安全重建”。先保留原始库和有关侧车的一致备份，记录缺失结构；在已有维护范围内审查迁移和恢复计划，用副本验证数据与约束后再决定是否替换。不要先删库、盲目运行初始化或把修复后的结果作为原始健康证据。结构检查也不证明所有业务列、规则含义或模型结果正确。

## Common Pitfalls

### 1. Stage Order Confusion

Stage 2 累计执行词典和 AI，直接传原稿：

```bash
python scripts/fix_transcription.py --input meeting.md --stage 2
```

产物为 `meeting_stage1.md`、`meeting_stage2.md`。Stage 3 也不会自动生成 HTML。反复输入 Stage 1 文件会重复处理、产生双后缀。

### 2. Team Import / Export

当前核心 CLI 没有 `--import`、`--merge`、`--export` 或 `--export-json`；旧示例不能执行。团队 JSON 文件需人工按 `from_text + domain` 审查冲突，在已授权字典中逐条 `--add`，或先审阅 `scripts/examples/bulk_import.py`。不要用未知选项返回的 argparse 2 当作导入成功。

### 3. Old Output Mistaken for Current Success

核心处理错误通常退出 1，可能已写 Stage 1。包装器只认本次私有 manifest，不扫描旧文件。自动化核心调用可设 `TRANSCRIPT_FIXER_OUTPUT_MANIFEST` 为专用路径，检查 JSON `outputs`，不能仅看文件是否存在。

### 4. Testing on Large Files

先用小样本 Stage 1 检查高风险词条、上下文规则与反例；确认后再跑 AI。保留人名、数字、说话人原始归属，避免对单次歧义改写无条件建词条。

### 5. Missing Diff

```bash
python scripts/generate_word_diff.py meeting.md meeting_stage2.md review.html
```

仅生成该 HTML，不开浏览器。缺输入或读写失败返回 1。确认修正文来自本次运行；浏览器检查沿用已有授权。

## Validation Commands

```bash
python scripts/fix_transcription.py --validate
```

只读结构检查成功为 0，缺 key 可有警告但不影响 Stage 1；数据库缺失、损坏、缺表或无法可靠验收为 1。CLI 参数错误是 2；没有“缺 key=2 / API 失败=3”的协议。

诊断报告只保留所选路径、检查范围、退出码、缺表名及未验收原因。SQLite 读查询示例见 `sql_queries.md`，数据库结构见 `database_schema.md`；直接 sqlite3 或 Repository 管理入口不等于本工具的零写入 preflight。
