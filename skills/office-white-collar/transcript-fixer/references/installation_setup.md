# Setup Guide

以下命令在技能根目录运行。使用已授权的环境和 setup；不用每次校正重新申请或初始化。一次性 Stage 1 无需持久库或 API key。

## Installation

Python 3.10+（源码使用现代联合类型语法）。在已有虚拟环境中安装：

```bash
python -m pip install -r requirements.txt
```

也可使用 uv 的已授权环境安装同一 requirements；不要假定有可用的 pyproject/uv sync 工程。

必需依赖为 `httpx>=0.24.0`（提供商 HTTP 客户端）与 `filelock>=3.13.0`（学习/持久化锁）。`difflib`、`sqlite3` 来自标准库；不需要 requests 或 anthropic SDK。HTTP/2 为可选，不要求 h2。包装器读取同一 requirements 构造 uv 的 `--with` 参数。可选的 `scripts/ensure_deps.py` 是独立安装助手，不是每次运行的必需入口。

## Database Initialization

只有需要持久字典且 setup 在授权范围内时：

```bash
python scripts/fix_transcription.py --init
```

所选路径为 `TRANSCRIPT_FIXER_DB_PATH`，否则为 `TRANSCRIPT_FIXER_CONFIG_DIR/corrections.db`（目录默认 `~/.transcript-fixer`）。初始化可能写 schema/WAL，已有库先保留一致备份；不要把它当成只读健康检查。表结构以 `scripts/core/schema.sql` 和 `database_schema.md` 为准，不承诺每次初始化均生成备份。

## API Configuration

Stage 2/3 使用显式传入进程环境的 `GLM_API_KEY`。通过用户已授权的安全方式注入；包装器不查 shell profile、登录文件或其他账号凭据。不要在 shell xtrace、命令历史或报告中输入真实 key。仅检查是否非空：

```bash
python -c 'import os, sys; sys.exit(0 if os.environ.get("GLM_API_KEY") else 1)'
```

有值退出 0，缺失/空值退出 1，无原值输出。API 权限、模型配额、网络可用性须单独验收。参见 `glm_api_setup.md`。

## Verify Configuration

```bash
python scripts/fix_transcription.py --validate
```

当前所选库必须已经存在；缺库、缺表、损坏或无法可靠验收退出 1。检查不创建目录、不初始化、不迁移、不写用户库和侧车。无活动侧车的数据库会通过私有只读快照检查完整性和八张必需表；WAL/SHM/journal 侧车存在时明确 `not verified` 并退出 1，不自动修复。由维护者提供无活动侧车的静止一致副本，不要删除活动侧车。缺 API key 是警告，不能据此推断 Stage 2 可运行。

## First Run

```bash
python scripts/fix_transcription.py --input meeting.md --stage 1 --domain general
python scripts/fix_transcript_enhanced.py meeting.md --stage 2 --output ./corrected
```

第二条需已有 uv 和凭据/数据共享授权。Stage 2 累计先跑词典，再 AI；产物为 `*_stage1.md`、`*_stage2.md`，浏览器默认不开。HTML 需显式运行 `scripts/generate_word_diff.py`。学习与自动批准默认关闭，CLI 审阅/批准仍是占位；人工确认可复用词条后用 `--add`，详见 `workflow_guide.md`。
