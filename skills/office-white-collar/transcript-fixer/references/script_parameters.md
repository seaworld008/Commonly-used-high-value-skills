# Script Parameters Reference

本页对应当前随包 CLI；所有命令在技能根目录运行。Python 环境需满足 `requirements.txt`（`httpx>=0.24.0`、`filelock>=3.13.0`）。已获授权的环境安装和字典 setup 可持续复用，不需要每次重做。

## Core CLI: scripts/fix_transcription.py

```bash
python scripts/fix_transcription.py --input meeting.md --stage 2 --output ./corrected --domain general
```

| 参数 | 当前行为 |
|------|----------|
| `--input, -i` | UTF-8 原稿文件；处理时必需 |
| `--output, -o` | 输出目录，默认原稿目录 |
| `--stage, -s` | 累计执行至该阶段，默认 3 |
| `--domain, -d` | 默认 general；核心 CLI 支持自选合法领域名 |
| `--init` | 初始化所选持久数据库，仅用于已授权的字典 setup |
| `--add FROM TO` | 将已确认的可复用词条写入所选字典 |
| `--list` | 按领域列出词条；属于持久库管理入口，会构造 Repository |
| `--validate` | 检查当前 `config.database.path` 的已有结构与完整性，不初始化或迁移 |
| `--review-learned`、`--approve FROM TO` | 占位处理器，打印未实现；不能视为完成审阅或批准 |

### 阶段与产物

| 阶段 | 输入与执行 | 本次成功产物 |
|------|------------|--------------|
| 1 | 原稿 → 词典和上下文规则 | `meeting_stage1.md` |
| 2 | 原稿 → 词典 → AI | `meeting_stage1.md`、`meeting_stage2.md` |
| 3 | 同 2，另打印 diff 生成提示 | 同 2；不自动生成 HTML 或报告 |

Stage 2 直接传原稿，无需预先传 Stage 1 文件。传 `meeting_stage1.md` 会再跑一次词典，产物变为 `meeting_stage1_stage1.md` 和 `meeting_stage1_stage2.md`。

```bash
python scripts/fix_transcription.py --input meeting.md --stage 1
python scripts/fix_transcription.py --input meeting.md --stage 2
python scripts/fix_transcription.py --input meeting.md --stage 3 --output ./corrected
```

AI 失败时不得把旧 `*_stage2.md` 当成本次结果。包装器以本次私有 manifest 的 `outputs` 列表识别交付；自动化调用核心 CLI 时，可设置 `TRANSCRIPT_FIXER_OUTPUT_MANIFEST` 为本次专用 JSON 路径，核对退出状态和清单。该清单是交付记录，不是语义准确性的证明。Stage 1 已完成而 Stage 2 失败属于部分交付。

### 退出码

- `0`：请求的处理完成；`--validate` 结构检查完成且无错误（可有缺 key 等警告）。学习占位命令也可能返回 0，须读提示。
- `1`：文件缺失、AI 凭据缺失、模型失败、持久化失败或验证失败/未验收等运行错误。
- `2`：argparse 参数错误（如未知选项、非法阶段）；不是“缺密钥”的专用退出码。
- 没有“API 失败固定退出 3”的约定；独立 `--health` 命令另有状态语义。

### 配置与只读校验边界

`TRANSCRIPT_FIXER_DB_PATH` 优先指定数据库；否则使用 `TRANSCRIPT_FIXER_CONFIG_DIR/corrections.db`，目录默认 `~/.transcript-fixer`。

`--validate` 不构造 Repository，不写 schema、WAL 或用户侧车。缺库/缺表返回 1。无活动侧车的数据库复制到私有临时目录后用只读 immutable SQLite 检查，复制前后和检查后检测源文件变化。存在 `-wal`、`-shm`、`-journal`时保守返回 1，明确 `not verified`。不要删除侧车来“通过”检查；由已授权维护者提供静止的一致非 WAL 副本。此校验不证明 API 可用、全部列约束匹配或模型准确性。

## Enhanced wrapper: scripts/fix_transcript_enhanced.py

```bash
python scripts/fix_transcript_enhanced.py meeting.md --output ./corrected --stage 2 --domain embodied_ai
```

包装器输入为位置参数；`--output/-o`、`--stage` 如上，领域限 `general`、`embodied_ai`、`finance`、`medical`。内部 `uv run --with ...` 直接采用同一 `requirements.txt`。它只读取传入进程环境的 `GLM_API_KEY`，不查 shell 文件或其他账号凭据。缺 key 在启动核心处理前退出 1。默认不打开浏览器；`--no-auto-open` 显式保持默认，`--auto-open` 只在授权时尝试打开本次 manifest 中的 HTML，包装器本身不生成 HTML。

## Word diff: scripts/generate_word_diff.py

```bash
python scripts/generate_word_diff.py original.md corrected.md output.html
```

三个位置参数分别是原文、修正文、HTML 路径。第三个可省略，默认写原文旁的 `original_对比_词语级.html`。成功返回 0，缺参数、缺输入、读写失败返回 1。仅生成词语级 HTML，不生成 Markdown、unified diff 或其他虚构报告；不会自动开浏览器。先核对本次修正文再运行。

## 学习、凭据与协作

学习及自动批准默认关闭，分别由 `TRANSCRIPT_FIXER_ENABLE_LEARNING` 和 `TRANSCRIPT_FIXER_AUTO_APPROVE` 控制。启用学习会持久化历史和候选，需在已授权字典维护范围内；默认普通处理不创建持久库。所有环境变量由进程读取，包装器不寻找登录文件。

`--import`、`--merge`、`--export`、`--export-json` 不在当前核心 CLI 参数中。团队 JSON 交换是策展方法，不能将这些旧选项当成可执行入口。批量写入可参考并审阅 `scripts/examples/bulk_import.py`，单条批准使用 `--add`。提供商不可用时检查退出状态和 manifest；脚本不保证输出任何宿主专用 fallback 标记。
