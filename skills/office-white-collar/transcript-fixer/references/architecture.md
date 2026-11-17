# Architecture Reference

本页描述随包实现及边界，不宣称已进行线上模型评测。CLI 参数以 `scripts/cli/argument_parser.py` 为准，数据结构以 `scripts/core/schema.sql` 为准。

## Entrypoints and Modules

```text
scripts/
├── fix_transcription.py          # 参数分派
├── fix_transcript_enhanced.py    # uv 包装、本次交付清单、可选开浏览器
├── generate_word_diff.py         # 独立词语级 HTML
├── cli/
│   ├── argument_parser.py
│   └── commands.py              # 阶段编排
├── core/
│   ├── dictionary_processor.py
│   ├── ai_processor.py
│   ├── ai_processor_async.py
│   ├── learning_engine.py
│   ├── correction_service.py
│   ├── correction_repository.py
│   └── schema.sql
└── utils/
    ├── config.py
    ├── validation.py
    ├── connection_pool.py
    └── diff_generator.py         # 库级报告工具，不是顶层 CLI
```

领域处理、提供商传输、持久化和校验分别维护。不能因为库级函数存在就承诺 CLI 已连接该功能。入口不自动递归加载所有参考页。

## Correction Data Flow

1. CLI 选择原稿、输出目录、领域和累计阶段。
2. `get_config()` 提供所选数据库和功能开关。普通处理默认不启用学习；已有字典读入私有快照，缺库时可使用空词典，避免初始化全局库。
3. Stage 1 执行 `DictionaryProcessor.process()`：先上下文正则，再词典替换，记录变化；写 `{stem}_stage1.md`。
4. Stage 2 在 Stage 1 文本上调用 AI：分块、主模型/备用模型、重试与结果检查；成功后写 `{stem}_stage2.md`。直接传原稿，不预先串联 Stage 1 文件。
5. 只有显式启用学习才保存历史并分析候选；持久化失败应明确失败/部分交付。
6. Stage 3 仅打印 diff 提示，不生成报告；需要时显式运行词语级 HTML 脚本。

### Output Receipts

核心 CLI 可通过 `TRANSCRIPT_FIXER_OUTPUT_MANIFEST` 写本次专用 JSON：

```json
{"outputs": ["/selected/output/meeting_stage1.md", "/selected/output/meeting_stage2.md"]}
```

包装器自动设置私有路径，核对清单中的允许路径和必需文本产物，避免把旧输出归入本次。Stage 2 失败时，清单可能仅有 Stage 1；报告必须区分部分交付与完整成功。文件存在或 provider 返回状态不证明内容准确。

### Exit Behavior

运行错误（缺文件、缺 key、AI 双模型失败、持久化失败等）为 1。argparse 错误可为 2；没有缺 key=2 / API 失败=3 的固定协议。学习占位命令打印未实现，不以退出 0 作为批准依据。`--health` 是独立管理命令，不能替代零写入 `--validate`。

## Dictionary Processing

优先级高的上下文规则先应用，然后进行词典替换。规则记录错误片段、替代文本、领域和出处；针对同音词、多义词及人名保留反例：

```text
巨升智能 → 具身智能     # 机器人语境，需源文支持
股价系统 → 框架系统     # 比全局“股价→框架”更具体
近距离的去看 → 近距离地去看
近距离搏杀             # 反例，保持不变
```

词典成本低、可复用，但误加条目会在未来原稿中重复误改。先用小样本 Stage 1 比对，不对数字、专名、说话人身份做无依据推断。领域隔离减少跨行业冲突。

处理器以 `process(text) -> (corrected_text, changes)` 返回文本和变更；变更保留行号、原片段、替代片段与规则类型，`get_summary(changes)` 汇总词典/上下文命中。上下文规则适合“的/地”等依位置变化的形式，词典适合稳定的完整术语。先精确例外，再通用规则，保留不应命中的反例。

## AI Provider

随包 GLM 配置使用 Anthropic 兼容消息接口、显式进程环境的 `GLM_API_KEY`；主/备模型以 `ai_processor_async.py` 为准。使用 httpx 的共享异步客户端、超时、重试和并发控制。requirements 的最低支持环境不包含 h2；核心客户端必须支持 HTTP/1.1，将 HTTP/2 作为可选优化。依赖声明不等于已验收：若核心仍写死 `http2=True`，缺 h2 时的构造失败应报告为未完成，不应强迫安装额外依赖来掩盖该问题。

主备失败不意味着可以交付未校正文本作为 Stage 2 成功。宿主可在既有授权内继续人工校正，保留原稿与不确定性；不保证任何宿主专用 fallback 标记。不得记录完整密钥、Authorization、包含原稿的异常响应或全量环境。

## Learning and Approval

学习默认关闭：`TRANSCRIPT_FIXER_ENABLE_LEARNING` 控制历史/候选持久化，`TRANSCRIPT_FIXER_AUTO_APPROVE` 为独立自动批准开关，默认关闭。已有 setup 授权可持续复用；单次校正不自动扩展为全局学习。

领域方法是按 `from_text + to_text + domain` 收集重复改写、上下文、频率、一致性与最近使用证据。频率和置信度是筛选线索，不是正确性的证明。高频歧义词同样可能是系统性误改。

现有启发式置信度由频率、一致性和最近性加权（0.5、0.3、0.2），属于候选排序分数，并非校准概率。频率分数在约十次出现时饱和；分组已经保证替换一致，最近性是简化启发式。候选应保留若干上下文示例、首次/末次出现和人工拒绝记录，防止重复推荐已拒绝模式。阈值与存储形状应以学习引擎当前实现为准，不能用分数绕过人工源文复核。

`--review-learned` 和 `--approve` 尚未实现真实审阅/批准。实际人工流程：整理出处与反例 → 确认语义与可复用性 → 在授权维护范围内 `--add` → 小样本 Stage 1 复核。不把占位提示当成成功操作。

## Persistent Data Access

`CorrectionService` 管理领域规则、校验和业务操作；`CorrectionRepository` 使用 SQLite 连接池、事务和 schema 初始化。构造 Repository 可能创建结构并启用 WAL，因此只能用于持久管理路径，不能用来证明旧库原本健康。

当前所选 `config.database.path` 优先由 `TRANSCRIPT_FIXER_DB_PATH` 指定，否则为 `TRANSCRIPT_FIXER_CONFIG_DIR/corrections.db`，默认目录 `~/.transcript-fixer`。

核心表包括 corrections、context_rules、correction_history、correction_changes、learned_suggestions、suggestion_examples、system_config、audit_log；schema 还可能包含其他辅助表。软删除用 `is_active` 保留审计痕迹，恢复或清理必须审查保留策略。

历史和候选可能含原稿片段，备份、共享和清理应遵守原有数据范围。JSON 交换可由 Service API 或人工策展实现，但核心 CLI 尚未实现 import/export 参数，不能从 API 推断 CLI 功能。

## Read-only Validation

`utils/validation.py` 使用同一 `get_config()` 选择已有数据库，绝不构造 Repository：

1. 缺库或路径非普通文件：明确错误，退出 1。
2. 发现 WAL/SHM/journal 侧车：明确 `not verified`，退出 1，不打开用户 SQLite 连接。
3. 无侧车时复制主文件到私有临时目录，检查源文件 inode、大小、mtime、ctime 等是否变化。
4. 检查文件头；拒绝活动 journal 侧车；已 checkpoint 且无侧车的 WAL 库可用一致快照检查，避免忽略已提交 WAL。
5. 对非 WAL 快照使用 `mode=ro&immutable=1`，运行 integrity_check、必需表清点及词条计数，之后再次检测源变化。
6. 清理私有快照，保留用户库和侧车原状。

此检查仅证明所见快照的结构和 SQLite 完整性，不证明全部业务列/约束、语义或提供商可用。活动库需由已授权维护者提供无活动侧车的静止一致副本；不能删除侧车、自动 checkpoint 或把恢复后结构说成原始健康。

## Diff and Browser

```bash
python scripts/generate_word_diff.py original.md corrected.md output.html
```

此独立 CLI 生成词语级 HTML；第三参数缺省时为 `original_对比_词语级.html`。不自动开浏览器，不承诺 Markdown/unified/inline 报告。包装器默认 `auto_open=False`，显式 `--auto-open` 仅尝试打开本次清单中的 HTML，本身不负责生成。

## Dependencies and Verification

`requirements.txt` 同时供普通 Python 环境和包装器 uv 参数使用：httpx、filelock。安装助手是可选入口，不能把安装完成当作真实模型验证。离线测试应使用临时真实 SQLite/文件、合成提供商和外部程序替身，区分静态检查、CLI 集成、线上模型与真实浏览器验收。
