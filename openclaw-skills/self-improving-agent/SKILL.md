---
name: self-improving-agent
description: '带记忆与自我优化机制的 Agent 技能，能在迭代中持续改进行为。'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["agent", "ai", "improving", "self"]'
created_at: "2026-03-15"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Self Improving Agent

用于需要长期运行、持续学习和策略改进的 Agent 工作流。Self Improving Agent 核心逻辑在于“闭环进化”：它不仅执行任务，还会观察执行结果、收集反馈，并据此修改自身的 Prompts、工具调用链或决策权重，从而在下一次类似任务中表现得更好。

## 安装

```bash
npx clawhub@latest install self-improving-agent
```

## 使用场景

- **长周期自动化任务**：如持续了一年的行业研报分析，Agent 能在月度总结中识别出之前的漏项并自动修正抓取逻辑。
- **重复任务中的策略优化**：在频繁的 PR 审查或 Bug 修复中，Agent 会根据开发者的修正意见（Review Comments）动态调整自身的代码规范检测强度。
- **基于历史反馈的行为修正**：如果用户多次指出 Agent 说话太啰嗦，它会自我更新 `System Prompt` 为更简洁的风格。
- **动态知识库维护**：当现有的 `MEMORY.md` 知识过时或发生冲突时，Agent 主动发起“知识清洗”任务。
- **环境自适应部署**：当从本地部署环境迁移到云端容器环境时，Agent 自动学习新的 API 端点和资源限制策略。

## 触发条件 / When to Use

- **任务失败后的复盘阶段**：当一个复杂任务（如 CI/CD 流水线构建）连续失败 3 次，Agent 自动唤起 `self-improving-agent` 进行根因分析。
- **显式用户批评/点赞**：当用户输入包含强烈的负面情绪或明确的指正（“别再用这个库了”）时。
- **性能/效率瓶颈期**：检测到单次任务 Token 消耗过大或耗时异常增长时，主动寻找优化路径。
- **定期维护计划 (Scheduled Optimization)**：通过 `cron` 技能每周执行一次自我诊断（Self-Diagnostics）。

## 核心能力 / Core Capabilities

### 1. 执行与观测 (Execution & Observation)
- **操作步骤**：
  1. 启动目标任务（Target Task）。
  2. 启动后台日志收集器，记录所有的中间决策点、API 返回值和潜在错误（Error Logs）。
  3. 捕获最终产出物的“质量得分”（可以是用户的点赞，也可以是 Linter 的通过率）。
- **最佳实践**：使用 `process` 技能运行长任务时，实时重定向 `stderr` 到审计文件。

### 2. 反射与归因 (Reflection & Attribution)
- **操作步骤**：
  1. 调用 `memory_search` 查找过去 10 次同类任务的成败记录。
  2. 利用 LLM 深度对比：成功案例与失败案例在 Prompt 结构上有何区别？哪些工具调用是冗余的？
  3. 生成“改进策略草案”（Candidate Policy）。
- **最佳实践**：采用 A/B Testing 思想，在下一轮任务中仅改变 1 个变量。

### 3. Prompt/代码 动态修改 (Dynamic Modification)
- **操作步骤**：
  1. 基于改进策略，使用 `edit` 工具修改自身的 `SKILL.md` 正文或 `System Prompt` 模板。
  2. 更新 `MEMORY.md` 中的“禁忌法则”和“成功套路”。
  3. 执行一次“模拟运行”以确认修改没有破坏基本功能。
- **最佳实践**：修改前备份原始配置文件，并在 `MEMORY.md` 记录 `diff` 变更记录。

### 4. 知识固化与分发 (Knowledge Consolidation)
- **操作步骤**：
  1. 将学到的新技能点（如某个冷门的 API 参数用法）沉淀为结构化的 JSON/Markdown 片段。
  2. 通过 `mcp_call` 将这些知识同步到共享知识库。

## 常用命令/模板 / Common Patterns

### 自我优化日志模板 (Self-Improvement Log)
```markdown
### 原始任务执行记录 (Execution Log)
- **任务**: [生成 React 登录页面]
- **结果**: [失败 - 样式丢失]
- **反馈**: [用户反馈称样式未正确引入 Tailwind]

### 根因分析 (Root Cause)
- **诊断**: 原始 Prompt 中未显式包含 `tailwind.config.js` 的引用建议。
- **关联记忆**: 3 天前在项目 B 中也遇到了同样的问题。

### 优化决策 (Improvement Decision)
- **行动**: 更新 `frontend-design` 技能的 `Core Capabilities` 模板。
- **变更点**: 强制要求在所有 React 渲染任务中包含 `style_framework_check` 步骤。

### 下一步验证 (Verification)
- [ ] 运行 `test-tailwind-render` 命令。
- [ ] 等待用户下一次 React 相关指令。
```

### 动态 Prompt 注入示例
```javascript
// 示例：基于用户反馈动态调整说话风格
if (userFeedback.includes("concise")) {
  await mcp_call({
    name: 'update_system_prompt',
    arguments: {
      modifier: "Always provide answers in bullet points, max 3 items."
    }
  });
}
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动重构循环
- Agent 持续监测代码库的重复率。一旦发现重复代码超过阈值，它会利用 `self-improving-agent` 逻辑生成重构方案，并在 PR 中提出“这是我根据之前的代码模式总结出的通用组件”。

### 2. 销售话术/客服策略进化
- 在与客户的对话流中，Agent 会记录导致对话中断的节点，并自动调整后续的话术风格，直到找到最高转化率的路径。

## 边界与限制 / Boundaries

- **进化漂移 (Evolutionary Drift)**：长期的过度自我优化可能导致 Agent 行为偏离最初的设计初衷。建议设定“核心价值守卫者” (Guardrails) 防止过度修改。
- **资源浪费风险**：自我复盘是一个高 Token 消耗的过程，应避免在琐碎的小任务上频繁触发优化逻辑。
- **配置覆盖风险**：动态修改 `SKILL.md` 可能覆盖用户的手工配置，需保留 `undo` 机制。
- **收敛速度**：对于高度动态、不可预测的任务，Self-Improving 逻辑可能难以收敛，甚至产生错误的结论。
- **负反馈陷阱**：如果不加辨别地吸收所有用户反馈，恶意或错误的反馈可能污染 Agent 的改进方向。

## 最佳实践总结

1. **小步快跑**：每次优化只改动一个最小逻辑单元。
2. **保留追溯性**：所有的进化过程必须在 `MEMORY.md` 中有迹可循。
3. **设置审计阈值**：关键策略的变更必须由人类（Human-in-the-loop）最终审批通过。
4. **多样性评估**：不仅要看当前任务是否成功，还要看修改后是否导致其他原本成功的任务失败（防止 Regression）。
5. **记忆清理**：过期的优化策略应定期“遗忘”，防止过时的经验干扰当前的决策。
6. **分环境进化**：开发环境大胆进化，生产环境稳健保守。
