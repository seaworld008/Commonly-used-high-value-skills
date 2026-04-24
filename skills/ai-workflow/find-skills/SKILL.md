---
name: find-skills
description: '让 Agent 自动搜索并安装合适技能，解决不知道该用哪个技能的问题。'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["find", "planning", "skills", "workflow"]'
created_at: "2026-03-15"
updated_at: "2026-03-20"
quality: 4
complexity: "intermediate"
---

# Find Skills

当用户只描述目标、但未指定具体工具或技能时，优先使用本技能做自动匹配。Find Skills 是 Agent 的“大脑插件中心”，它能理解用户意图，并从浩如烟海的 ClawHub 仓库中精准定位、安装并配置合适的技能。

## 安装

```bash
npx clawhub@latest install find-skills
```

## 工作方式

1. **语义理解 (Semantic Extraction)**：根据用户复杂、模糊的目标，生成 3-5 个核心技能检索词（如 “SQL optimization”, “React chart libraries”）。
2. **多源检索 (Multi-Source Search)**：在 ClawHub 官方仓库、本地已安装列表及相关开源索引中搜索候选技能。
3. **优先级排序 (Prioritization)**：根据技能的评分、下载量、更新频率以及与当前任务的匹配度进行综合排序。
4. **决策与理由 (Reasoning)**：为前 3 名技能给出详细的推荐安装理由。
5. **按需执行 (On-Demand Execution)**：按用户确认结果或自主决策执行 `clawhub install`。

## 触发条件 / When to Use

- **冷启动场景**：新项目开始，用户提出了一个 Agent 之前没处理过的任务类型（如“帮我写一个 Chrome 插件”）。
- **工具链补强**：Agent 发现现有技能集无法完成任务，提示缺失必要的工具（如缺失 `image-edit` 时）。
- **优化替代方案**：现有技能效率低下或报错，需要寻找功能类似的“增强版”技能。
- **批量环境部署**：需要为一套复杂的工程方案（如云原生架构）一键安装全套开发、运维技能。
- **自动升级检测**：当用户询问最新功能时，Agent 自动搜索是否有对应的 Beta 版技能可用。

## 核心能力 / Core Capabilities

### 1. 精准意图映射 (Intent Mapping)
- **操作步骤**：
  1. 接收到原始 Prompt。
  2. 调用内部 LLM 对 Prompt 进行“原子任务”拆解。
  3. 将拆解后的原子任务（如“PDF parsing”, “OCR”, “Summarization”）映射为标准技能标签。
- **最佳实践**：生成检索词时，应包含“动词 + 名词”结构，如 `parse-xlsx` 而非仅仅是 `xlsx`。

### 2. 候选技能对比评估 (Skill Benchmarking)
- **操作步骤**：
  1. 调用 `list_agent` 或搜索接口。
  2. 提取每个候选技能的 `description` 和 `metadata`。
  3. 建立评分矩阵（功能覆盖度、稳定性、易用性）。
- **最佳实践**：优先推荐那些有 `verified` 标签或在大厂生产环境验证过的技能。

### 3. 一键环境就绪 (Zero-Config Readiness)
- **操作步骤**：
  1. 确认目标技能后，自动执行 `clawhub install <skill-name>`。
  2. 检查安装后的 `README.md`，识别是否需要环境变量（ENV）或 OAuth 授权。
  3. 如果需要，主动提示用户配置或通过 `composio_connect_app` 完成连接。
- **最佳实践**：安装完成后，自动运行一个 `hello world` 级别的测试指令，确保技能真实可用。

### 4. 依赖项解析与递归安装
- **操作步骤**：
  1. 分析目标技能的依赖链。
  2. 自动补充安装底层依赖（如 `puppeteer`, `ffmpeg` 等底层二进制工具）。

## 常用命令/模板 / Common Patterns

### 智能技能匹配模板 (Matching Template)
```markdown
### 用户目标
[描述：实现一个能够自动分析 XHS 数据并生成周报的机器人]

### 识别出的关键词 (Generated Keywords)
- `xiaohongshu-crawler`
- `data-analysis-pandas`
- `markdown-report-generator`
- `chart-visualizer`

### 推荐技能组合 (Recommended Stack)
1. **xhs-analyzer** (评分 4.8): 包含成熟的爬虫逻辑和反爬策略。
2. **super-report** (评分 4.5): 支持将 JSON 直接转化为美观的 Markdown。
3. **quick-chart** (评分 4.9): 能够生成静态图片图表并插入报告。

### 是否立即安装前两项？ (Confirm Installation?)
> [Yes] / [No] / [Tell me more]
```

### 检索接口模拟示例
```javascript
// 示例：查询具备“代码审查”能力的技能
const candidateSkills = await mcp_call({
  name: 'search_available_skills',
  arguments: {
    keyword: 'code-review',
    limit: 5,
    sort_by: 'downloads'
  }
});
```

## 进阶应用场景 / Advanced Use Cases

### 1. 跨平台能力迁移
- 用户原本在本地使用 `python-scripts`，现在想迁移到云端。Find Skills 会主动寻找 `vercel-deploy` 和 `supabase-connector` 等技能来适配。

### 2. 紧急漏洞补救
- 当系统提示 `dependency vulnerability` 时，Find Skills 会搜索具备“安全扫描与自动补救”能力的技能（如 `security-vetter`）。

## 边界与限制 / Boundaries

- **安装权限限制**：在受限容器或无 root 权限的环境下，安装可能失败。
- **冲突检测**：防止安装功能高度重合或命令名称冲突（Name Collision）的多个技能。
- **Token 消耗**：频繁的大规模搜索和 `description` 解析会消耗较多 Token。
- **未经验证风险**：对于非官方认证（Community）的技能，Agent 应给予明确的安全警告。
- **版本不兼容**：由于 ClawHub 版本迭代快，部分老旧技能可能在当前环境无法运行。

## 最佳实践总结

1. **先搜后装**：不要盲目安装，先利用 `find-skills` 进行横向对比。
2. **最小安装原则**：只安装完成当前任务最核心的 1-2 个技能，保持系统简洁。
3. **理由先行**：Agent 在推荐安装时，必须说明“为什么这个技能适合你的任务”。
4. **安装后自检**：安装成功后，立即读取 `SKILL.md` 获取该技能的 `Common Patterns`。
5. **定期清理**：对于一次性任务使用的技能，在任务结束后提示用户可以卸载（Unload）。
