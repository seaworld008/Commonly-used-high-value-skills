# 纠错词典配置指南

## 词典结构

当前词典位于所选 SQLite 数据库，路径优先由 `TRANSCRIPT_FIXER_DB_PATH` 指定，否则为 `TRANSCRIPT_FIXER_CONFIG_DIR/corrections.db`（目录默认 `~/.transcript-fixer`）。不通过编辑入口脚本维护常量。下面的 Python 数据仅说明领域规则形状；实际持久化应使用已授权的 CLI/SQL 入口，沿用已有 setup 授权。

### 1. 上下文规则 (context_rules 表)

用于需要结合上下文判断的替换:

```python
CONTEXT_RULES = [
    {
        "pattern": r"正则表达式",
        "replacement": "替换文本",
        "description": "规则说明"
    }
]
```

**示例:**
```python
{
    "pattern": r"近距离的去看",
    "replacement": "近距离地去看",
    "description": "修正'的'为'地'"
}
```

### 2. 领域词典 (corrections 表)

用于直接字符串替换:

```python
CORRECTIONS_DICT = {
    "错误词汇": "正确词汇",
}
```

**示例:**
```python
{
    "巨升智能": "具身智能",
    "奇迹创坛": "奇绩创坛",
    "矩阵公司": "初创公司",
}
```

## 添加自定义规则

### 步骤1: 识别错误模式

从原稿与本次修正文的差异中识别重复错误，核对源语义、说话人及反例。Stage 3 不自动生成报告；需要时显式运行 `scripts/generate_word_diff.py original.md corrected.md output.html`。

### 步骤2: 选择规则类型

- **简单替换** → 使用 CORRECTIONS_DICT
- **需要上下文** → 使用 CONTEXT_RULES

### 步骤3: 添加到词典

在技能根目录，将已经确认可复用的词条写入已授权字典：

```bash
python scripts/fix_transcription.py --add "你的错误" "正确词汇" --domain general
```

### 步骤4: 测试

运行 `python scripts/fix_transcription.py --input sample.md --stage 1 --domain general`，比对 `sample_stage1.md` 和反例。Stage 2 是累计词典与 AI，直接传原稿，成功另有 `sample_stage2.md`。学习、自动批准与浏览器打开默认关闭；CLI 审阅/批准是占位，不能替代人工确认。

## 常见错误类型

### 同音字错误
```python
"股价": "框架",
"三观": "三关",
```

### 专业术语
```python
"巨升智能": "具身智能",
"近距离": "具身",  # 某些上下文中
```

### 公司名称
```python
"奇迹创坛": "奇绩创坛",
```

## 优先级

1. 先应用 CONTEXT_RULES (精确匹配)
2. 再应用 CORRECTIONS_DICT (全局替换)

上述同音词示例依赖上下文，不可无条件将“股价”或“近距离”替换成技术术语。先确认领域与完整短语，避免重复误改。结构验证用 `--validate`，不会初始化用户库；WAL/侧车或不一致快照明确未验收，不能把结构通过当作规则准确。
