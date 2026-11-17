# Workflow Guide

在技能根目录运行以下命令。保留原稿、说话人归属、数字和专有名词；上下文不足的改写标为候选。已有 setup 授权持续有效，复用所选配置与已授权环境。

## Pre-Flight Checklist

### Initial Setup（仅需持久字典时）

一次性校正无需初始化全局库。已有字典通过当前配置选择；`TRANSCRIPT_FIXER_DB_PATH` 优先，否则为 `TRANSCRIPT_FIXER_CONFIG_DIR/corrections.db`（目录默认 `~/.transcript-fixer`）。持久 setup 已获授权时：

```bash
python scripts/fix_transcription.py --init
python scripts/fix_transcription.py --add "巨升智能" "具身智能" --domain embodied_ai
```

使用满足 `requirements.txt` 的 Python 环境，或包装器内的 uv 依赖入口。不要修改已有授权之外的账号配置、shell 登录文件。AI 需要用户安全提供进程环境中的 key；不回显、不复制到报告。

### 文件与参数

- 原稿为可读的 UTF-8 文本；先在小样本上确认领域和词典规则。
- 输出写所选目录，原稿保留；核对磁盘空间和本次输出清单。
- Stage 1 无需联网和 key；Stage 2/3 会把文本发往所配置提供商，遵守已有数据共享授权。

**Quick validation**:

```bash
uv run scripts/fix_transcription.py --validate &&
python -c 'import os, sys; sys.exit(0 if os.environ.get("GLM_API_KEY") else 1)'
```

后半句仅返回存在性退出状态（有值 0、缺失/空值 1），不打印 key；即使 shell 开启 xtrace，也不会把环境值展开进命令参数。`--validate` 仅验当前已有库，不做 setup。缺库、缺表、损坏返回 1；WAL/SHM/journal 侧车存在时返回 1 并报告未验收。正常只读校验采用私有静态快照，不写用户库或侧车。无持久库的一次性校正可以直接 Stage 1；校验失败不表示它必须创建默认库。

## 1. First-Time Correction

```bash
python scripts/fix_transcription.py --input meeting.md --stage 1 --domain embodied_ai
python scripts/fix_transcription.py --input meeting.md --stage 2 --domain embodied_ai
```

Stage 2 是累计阶段：先词典，再 AI，直接传原稿。成功得到 `meeting_stage1.md` 和 `meeting_stage2.md`。Stage 3 同样执行这两步，再打印 diff 提示；不自动生成 HTML。使用包装器可选输出目录：

```bash
python scripts/fix_transcript_enhanced.py meeting.md --output ./corrected --stage 2 --domain embodied_ai
```

包装器不搜 shell 凭据、不默认打开浏览器，内部 uv 按 requirements 安装两项依赖。普通直接 Python 环境也须同时有 httpx、filelock；不要求安装可选 h2。

## 2. Iterative Improvement

1. 将同一领域原稿逐次校正，人工核对 AI 的改写与源音频/上下文。
2. 收集“错误短语 → 正确短语”、领域、出处和不确定性。高频并不等于正确，先检查人名、数字和多义词。
3. 对已获授权且确认可复用的词条执行 `--add`，然后用小样本 Stage 1 确认下次能命中。
4. 再跑后续同领域原稿，比对剩余错误，保留误改的反例。

```bash
python scripts/fix_transcription.py --add "巨升方向" "具身方向" --domain embodied_ai
python scripts/fix_transcription.py --input next_meeting.md --stage 1 --domain embodied_ai
```

学习默认关闭。显式启用学习可持久化历史/候选，自动批准还有独立开关；`--review-learned` 与 `--approve` 当前仅打印未实现，不能把它们当成审阅工具或成功批准。默认返回人工待审候选，批准写库使用 `--add`。领域流程详见 `iteration_workflow.md`。

## 3. Domain-Specific Corrections

| Domain | 使用场景 |
|--------|----------|
| general | 通用术语与已核实专名 |
| embodied_ai | 具身智能、机器人、技术交流 |
| finance | 财务、投资，重点核对金额与口径 |
| medical | 医疗术语，保留源语义和不确定性 |

核心 CLI 可用合法自定义领域名；包装器限定上述四种。避免将 `股价 → 框架` 这样的歧义替换无条件加入 general，优先保存已核实的完整短语。

```bash
python scripts/fix_transcription.py --add "股价系统" "框架系统" --domain embodied_ai
python scripts/fix_transcription.py --input lecture.md --stage 1 --domain embodied_ai
```

## 4. Team Collaboration

用经过审阅的词条 JSON、出处与反例交换知识，按 `from_text + domain` 检查冲突。不要共享含原稿历史的数据库或凭据。当前 CLI 不实现 `--export/--import/--merge`；共享文件格式和人工合并见 `team_collaboration.md`、`file_formats.md`。用已确认词条调用 `--add`；批量示例位于 `scripts/examples/bulk_import.py`，先审查其输入与写入范围。远端发布沿用既有授权。

## 5. Stage-by-Stage Execution

| `--stage` | 执行到 | 输出 |
|-------------|--------|------|
| 1 | 词典及上下文规则 | `file_stage1.md` |
| 2 | 词典 → AI | `file_stage1.md`、`file_stage2.md` |
| 3（默认） | 同 2，另有 diff 提示 | 同 2 |

始终传本次原稿 `file.md`。预先传 `file_stage1.md` 会重复词典处理并生成双重后缀；不需要这样串联。

处理成功 0；缺文件、缺 key、AI 失败或存储错误为 1。非法参数通常为 argparse 的 2；不存在“缺 key=2、API 失败=3”的约定。核心 AI 失败时可能已交付 Stage 1；包装器在缺 key 时提前退出。不能根据旧文件的存在判断本次成功。自动化可给核心 CLI 设置本次私有 `TRANSCRIPT_FIXER_OUTPUT_MANIFEST`，读取 JSON 的 `outputs` 并核对退出码；包装器自动使用私有清单。

## 6. Context-Aware Rules

上下文规则按高优先级先执行。先读 `database_schema.md`，备份所选数据库并确认写入在既有维护范围内。此示例用于人工 SQL 会话，路径应替换为当前选中的字典：

```sql
INSERT INTO context_rules (pattern, replacement, description, priority)
VALUES ('近距离的去看', '近距离地去看', '的→地 before verb', 10);
```

先保留“近距离搏杀”等不应改写的反例，在小样本 Stage 1 上比对结果。不要以验证命令代替语义评审；`--validate` 只验已有结构与 SQLite 完整性。

## 7. Diff Report Generation

```bash
python scripts/generate_word_diff.py meeting.md meeting_stage2.md review.html
```

唯一此处交付是 `review.html`。省略第三参数时默认 `meeting_对比_词语级.html`，不生成 Markdown、unified diff 等额外报告。先确认 Stage 2 属于本次成功运行。浏览器默认不开，已有授权要求可视检查时手工打开 HTML；`--auto-open` 仅尝试打开包装器本次清单中的 HTML，不负责创建它。

## Batch Processing

保持每个原稿的独立退出状态和输出目录；先确认单文件小样本，再在授权配额范围内批处理：

```bash
for file in transcripts/*.md; do
  if python scripts/fix_transcription.py --input "$file" --stage 2 --domain embodied_ai; then
    printf '%s\n' "completed: $file"
  else
    printf '%s\n' "failed or partial: $file" >&2
  fi
done
```

避免将 `*_stage1.md`、`*_stage2.md` 再当原稿输入。并发运行需评估提供商限额和持久化锁；失败时记录部分交付，不复用旧报告。

## Maintenance Workflows

- 每周：人工审阅候选、出处和反例；只把已确认可复用词条加入已授权字典。
- 每月：为所选库制作一致备份，WAL 使用 SQLite backup 机制或停写后的完整一致副本；不能只复制主文件而遗漏活动 WAL。
- 清理、迁移、VACUUM 等会写数据，仅在已授权维护中执行，先审查保留策略并验证备份；不要作为普通只读 preflight。
- `--validate` 遇 WAL 明确未验收。维护者可提供无活动侧车的静止一致副本供核验，不能删除侧车或宣称已全部通过。

模型不可用时检查退出状态与本次清单，返回已完成的 Stage 1 和未完成的 Stage 2。脚本不保证任何 fallback 标记。若当前宿主在已有授权内继续人工校正，应另存结果、标注不确定性，按源文复核；沿用已授权 setup，无须添加新的批准循环。
