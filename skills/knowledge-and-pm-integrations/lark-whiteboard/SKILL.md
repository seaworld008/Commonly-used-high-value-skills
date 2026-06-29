---
name: lark-whiteboard
description: '飞书画板：查询和编辑飞书云文档中的画板。支持导出画板为预览图片、导出原始节点结构、使用多种格式更新画板内容。 当用户需要查看画板内容、导出画板图片、编辑画板时使用此 skill。不负责：飞书云文档内容编辑（lark-doc）、文档内嵌电子表格/Base（lark-sheets / lark-base）。'
zh_description: "用于查询、导出和编辑飞书云文档中的画板内容和节点结构。"
version: "1.0.4"
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/main/skills/lark-whiteboard"
license: MIT
tags: '[feishu, lark, lark-cli, whiteboard, diagram]'
created_at: "2026-05-19"
updated_at: "2026-06-29"
quality: 3
complexity: advanced
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli whiteboard --help"
---

> [!IMPORTANT]
> - 运行 `lark-cli --version`，确认可用，无需询问用户。
> - 运行 `npx -y @larksuite/whiteboard-cli@^0.2.12 -v`，确认可用，无需询问用户。

**CRITICAL — 开始前 MUST 先用 Read 工具读取 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)，其中包含认证、权限处理**

---

## 快速决策

**身份**：画板操作默认使用 `--as user`。仅当需要以应用身份上传时使用 `--as bot`。

| 用户需求                                    | 行动                                                                                            |
|-----------------------------------------|-----------------------------------------------------------------------------------------------|
| 查看画板内容 / 导出图片 / 导出 SVG 矢量图 | [`+query --output_as image/svg`](references/lark-whiteboard-query.md)                             |
| 获取画板的 Mermaid/PlantUML 代码               | [`+query --output_as code`](references/lark-whiteboard-query.md)                              |
| 检查画板是否由代码绘制                             | [`+query --output_as code`](references/lark-whiteboard-query.md)                              |
| 仅微调节点文字/颜色                         | `+query --output_as raw` → 手动改 JSON → `+update --input_format raw`                            |
| 用户**已提供** Mermaid/PlantUML/SVG 代码，或明确指定用该格式 | 自己生成/使用代码 → [`+update --input_format mermaid/plantuml/svg`](references/lark-whiteboard-update.md) |
| 新建/创作复杂图表（架构/流程/组织等）                    | → **[§ 创作 Workflow](references/lark-whiteboard-workflow.md#创作-workflow)**                     |
| 修改/重绘已有画板                               | → **[§ 修改 Workflow](references/lark-whiteboard-workflow.md#修改-workflow)**                     |

## Shortcuts

| Shortcut | 说明 |
|---|---|
| [`+query`](references/lark-whiteboard-query.md) | 查询画板，导出为预览图片、SVG 矢量图、代码或原始节点结构。 |
| [`+update`](references/lark-whiteboard-update.md) | 更新画板，支持 PlantUML、Mermaid、SVG 或 OpenAPI 原生格式 |

---

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

## Whiteboard Safety Checklist

Before updating a whiteboard:

- Query the current board first unless the user explicitly wants to replace it from scratch.
- Preserve existing node ids when making small edits so comments, references, and layout anchors remain stable.
- Prefer Mermaid or PlantUML for structured architecture and flow diagrams; use raw JSON only when exact node manipulation is required.
- Confirm whether the user wants a visual preview, source code, or both.
- Avoid destructive rewrites when the request is only to rename labels, adjust colors, or add a small branch.
- Keep exported previews with the task output when the user needs review evidence.

## Review Output

For edits, report:

1. What changed in the board.
2. Which input format was used.
3. Whether a preview/export was generated.
4. Any assumptions about layout, node grouping, or diagram semantics.
