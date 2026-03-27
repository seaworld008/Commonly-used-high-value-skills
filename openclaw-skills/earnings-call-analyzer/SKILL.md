---
name: earnings-call-analyzer
description: 'Use when summarizing earnings calls, extracting management tone changes, surfacing guidance language, or turning transcript snippets into an actionable investor update.'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["analyzer", "call", "earnings", "finance"]'
created_at: "2026-03-18"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Earnings Call Analyzer (业绩电话会分析师)

将冗长、充满术语的业绩电话会转录文本（Transcripts）转化为极速投资简报，精准捕捉管理层语气变化、指引（Guidance）语言、资本配置逻辑以及潜在风险信号。

## 安装与前提条件

```bash
# 确保已安装文本处理与情感分析库
pip install pandas nltk textblob
# 下载分段脚本
npx clawhub install earnings-call-analyzer
```

## 触发条件 / When to Use

- **财报发布后总结 (Post-earnings Wrap-up)**：在财报发布后的 24 小时内，快速同步核心增量信息。
- **PM 或 IC 投资建议 (Investment Committee Notes)**：为投资经理提供结构化的核心观点摘要。
- **差异化认知核查 (Variant-perception Checks)**：通过对比本季度与上季度的措辞差异，识别管理层对未来预期的微妙变化。
- **管理层信誉跟踪 (Management Credibility)**：记录管理层在过去几个季度中对承诺的执行情况，识别“画大饼”或“过度保守”的信号。
- **Q&A 压力点分析**：识别分析师问询最密集的领域，通常这就是市场目前最大的担忧点。

## 核心能力 / Core Capabilities

### 1. 结构化分段与清洗 (Transcript Segmentation)
- **操作步骤**：
  1. 将转录文本拆分为：**准备好的陈述 (Prepared Remarks)** 和 **问答环节 (Q&A Segments)**。
  2. 提取发言人身份：CEO, CFO, IR 以及 参与提问的卖方分析师。
  3. 过滤掉无意义的寒暄（Phatic communication）。
- **最佳实践**：给 Q&A 环节分配更高的权重，因为这部分最能体现管理层的应变能力和真实底气。

### 2. 多维度情感与信号提取 (Signal Extraction)
- **操作步骤**：
  1. 运行 `scripts/analyze_earnings_call.py`。
  2. 统计关键词频率：如 `Guidance`, `Capex`, `EBITDA`, `Supply chain`, `Margin expansion`.
  3. 识别情感对比：正面（信心十足、强劲）、谨慎（挑战、逆风、不确定性）。
- **最佳实践**：不仅看词频，更要看上下文。例如，“我们面临挑战，但有信心克服”应被记为中性偏好，而非纯负面。

### 3. 指引与前瞻性陈述追踪 (Guidance Tracking)
- **操作步骤**：
  1. 自动提取所有数字化的指引（如：FY25 Revenue Growth expected at 10-12%）。
  2. 对比共识预期（Consensus Estimates），判断是 Beat 还是 Miss。
  3. 标注指引中的前置条件（如：Assuming stable currency rates）。

### 4. 问答环节“回避性”检测 (Evasive Answer Detection)
- **操作步骤**：
  1. 分析管理层在回答特定问题时的长度与直接度。
  2. 标记短语，如：`I’ll let CFO answer`, `We will provide more details later`, `As we previously stated`.
- **最佳实践**：高回避率通常意味着该业务单元存在未披露的问题。

## 常用命令/模板 / Common Patterns

### 业绩电话会摘要模板 (Investor Readout Template)
```markdown
### 📈 [公司名] [Qx] 业绩电话会摘要

**1. 核心定调 (Tone of the Call)**:
- **语气**: [例如：谨慎乐观，重点强调成本控制]
- **情绪得分**: 6.5/10 (较上季 7.2/10 下滑)

**2. 管理层核心论点 (Key Narrative)**:
- [要点 A]: 描述业务进展。
- [要点 B]: 描述战略转型。

**3. 指引更新 (Guidance & Forward Outlook)**:
- **营收**: [FY26 指引上修至 XX%]
- **利润率**: [维持不变，强调受汇率影响]

**4. 关键问答回顾 (Top Q&A Takeaways)**:
- **问题 1 (摩根大通分析师)**: 关于毛利率的压力。
- **回答摘要**: 强调供应链优化将在下半年抵消原材料上涨。

**5. 隐忧与风险点 (Hidden Red Flags)**:
- 管理层三次回避了关于 [竞争对手 X] 入场的影响问题。
```

### 快速分析脚本命令
```bash
# 传入 JSON 格式的 Transcript
python scripts/analyze_earnings_call.py --input assets/jpm_q4_2025.json --compare assets/jpm_q3_2025.json
```

## 进阶应用场景 / Advanced Use Cases

### 1. “管理层黑盒”对比
- 对比同一行业内 5 家公司在同一周业绩会上的关键词，识别全行业共性的“系统性风险”（如：AI 投入的回报期）与单体公司的“独特性优势”。

### 2. 情绪波动图谱
- 将电话会转录文本按时间轴（每 5 分钟一段）计算情绪得分，生成情绪瀑布图，识别是在哪个环节（如 CEO 总结或 CFO 报数）出现了情绪拐点。

## 边界与限制 / Boundaries

- **语义理解限制**：对于讽刺、暗喻或极其含蓄的表达，模型可能存在误判。
- **音频转录质量**：如果输入的 Transcript 本身存在 OCR/ASR 错误，后续分析的可靠性将大打折扣。
- **过度解读风险**：一个词的增减可能只是发言习惯，不应作为投资决策的唯一依据。
- **时效性压力**：在财报季节，需要处理海量文本，单次分析耗时应控制在 60 秒内。
- **法规合规**：本技能仅供研究参考，严禁利用其生成虚假的诱导性投资评论。

## 最佳实践总结

1. **对比胜过描述**：永远问自己“这和上个季度比有什么不同？”。
2. **盯紧 Guidance**：数字化的指引变化是资本市场最敏感的信号。
3. **识别 Q&A 压力点**：分析师反复追问的地方，就是下个季度的雷区或爆发点。
4. **记忆同步**：将管理层的核心承诺存入 `MEMORY.md`，用于下季度的“打脸式”复核。
5. **多源核实**：将 Transcript 分析结果与卖方研究报告（Broker Reports）进行交叉验证。
6. **分段授权**：大任务分段处理，先摘要，再根据用户要求深入特定 Segment。
