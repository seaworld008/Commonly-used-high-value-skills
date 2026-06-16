---
name: lark-whiteboard
description: '飞书画板：查询和编辑飞书云文档中的画板。支持导出画板为预览图片、导出原始节点结构、使用多种格式更新画板内容。 当用户需要查看画板内容、导出画板图片、编辑画板时使用此 skill。不负责：飞书云文档内容编辑（lark-doc）、文档内嵌电子表格/Base（lark-sheets / lark-base）。'
version: "1.0.2"
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/main/skills/lark-whiteboard"
license: MIT
tags: '[feishu, lark, lark-cli, whiteboard, diagram]'
created_at: "2026-05-19"
updated_at: "2026-06-16"
quality: 4
complexity: advanced
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli whiteboard --help"
---

> [!IMPORTANT]
> - 运行 `lark-cli --version`，确认可用，无需询问用户。
> - 运行 `npx -y @larksuite/whiteboard-cli@^0.2.11 -v`，确认可用，无需询问用户。

**CRITICAL — 开始前 MUST 先用 Read 工具读取 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)，其中包含认证、权限处理**

---

## 快速决策

**身份**：画板操作默认使用 `--as user`。仅当需要以应用身份上传时使用 `--as bot`。

| 用户需求                                    | 行动                                                                                            |
|-----------------------------------------|-----------------------------------------------------------------------------------------------|
| 查看画板内容 / 导出图片                           | [`+query --output_as image`](references/lark-whiteboard-query.md)                             |
| 获取画板的 Mermaid/PlantUML 代码               | [`+query --output_as code`](references/lark-whiteboard-query.md)                              |
| 检查画板是否由代码绘制                             | [`+query --output_as code`](references/lark-whiteboard-query.md)                              |
| 修改节点文字/颜色（简单改动）                         | `+query --output_as raw` → 手动改 JSON → `+update --input_format raw`                            |
| 用户**已提供** Mermaid/PlantUML 代码，或明确指定用该格式 | 自己生成/使用代码 → [`+update --input_format mermaid/plantuml`](references/lark-whiteboard-update.md) |
| 新建/创作复杂图表（架构/流程/组织等）                    | → **[§ 创作 Workflow](references/lark-whiteboard-workflow.md#创作-workflow)**                     |
| 修改/重绘已有画板                               | → **[§ 修改 Workflow](references/lark-whiteboard-workflow.md#修改-workflow)**                     |

## Shortcuts

| Shortcut | 说明 |
|---|---|
| [`+query`](references/lark-whiteboard-query.md) | 查询画板，导出为预览图片、代码或原始节点结构 |
| [`+update`](references/lark-whiteboard-update.md) | 更新画板，支持 PlantUML、Mermaid 或 OpenAPI 原生格式 |

---

## 更新前检查

画板更新会覆盖节点结构，先做可回退的上下文捕获：

1. `+query --output_as image` 保存当前视觉状态，方便用户确认差异。
2. `+query --output_as raw` 获取原始节点结构；复杂修改先基于 raw 做最小改动。
3. 如果用户给的是 Mermaid/PlantUML，先检查语法和图形语义，再调用
   `+update`。
4. 更新后再次 `+query --output_as image`，对比关键节点、连线方向、文本和颜色。

## 格式选择

| 场景 | 推荐格式 | 原因 |
|---|---|---|
| 小幅文字或颜色调整 | raw | 保留现有布局和节点 id |
| 新建流程图、时序图、架构图 | Mermaid | 可读性强，便于用户审阅 |
| UML 类图、组件图、部署图 | PlantUML | 结构表达更稳定 |
| 需要完全保真编辑 | raw | 避免代码格式转换丢失画板特有属性 |

## 风险边界

- 不要在未导出现状的情况下重绘已有画板。
- 不要把文档编辑、表格编辑或 Base 记录编辑混入画板更新。
- 如果导出的代码无法表达原画板元素，改走 raw 更新或说明不可无损转换。
- 对多人协作画板，先确认用户希望覆盖当前版本，避免覆盖他人刚写入的内容。

## 不在本 skill 范围
- 文档内容编辑 → lark-doc [lark-doc](../lark-doc/SKILL.md)
- 在文档中创建画板 → [lark-doc-whiteboard.md](../lark-doc/references/lark-doc-whiteboard.md)
- 表格 / Base 操作 → [lark-sheets](../lark-sheets/SKILL.md) / [lark-base](../lark-base/SKILL.md)
<!-- LOCAL-QUALITY-SUPPLEMENT:START -->
## Usage Notes

This supplement is maintained by the repository sync pipeline. It keeps the
imported upstream skill usable inside this curated collection when the upstream
source is intentionally concise.

## Common Patterns

```text
1. Confirm that the user's task matches the skill trigger.
2. Read the relevant project files or user-provided context before acting.
3. Choose the smallest reversible action that advances the task.
4. Run the verification command or manual check that proves the result.
5. Report the outcome, evidence, and any remaining risk.
```

## Boundaries

- Prefer the upstream workflow for Lark Whiteboard; this section only adds local quality
  guardrails.
- Do not invent project facts when required files, vaults, services, or tools are
  unavailable.
- Stop and ask for clarification when the next action could overwrite user work,
  expose private data, or change production state.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
