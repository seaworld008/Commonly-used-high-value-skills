---
name: lark-whiteboard
description: '飞书画板：查询和编辑飞书云文档中的画板。支持导出画板为预览图片、导出原始节点结构、使用多种格式更新画板内容。 当用户需要查看画板内容、导出画板图片、编辑画板时使用此 skill。不负责：飞书云文档内容编辑（lark-doc）、文档内嵌电子表格/Base（lark-sheets / lark-base）。'
zh_description: "用于查询、导出和编辑飞书云文档中的画板内容和节点结构。"
version: "1.0.7"
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/main/skills/lark-whiteboard"
license: MIT
tags: '[feishu, lark, lark-cli, whiteboard, diagram]'
created_at: "2026-05-19"
updated_at: "2026-08-10"
quality: 3
complexity: advanced
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli whiteboard --help"
---

> [!IMPORTANT]
> - 运行 `lark-cli --version`，确认可用，无需询问用户。
> - 运行 `npx -y @larksuite/whiteboard-cli@^0.2.13 -v`，确认可用，无需询问用户。

**CRITICAL — 开始前 MUST 先用 Read 工具读取 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)，其中包含认证、权限处理**

---

## 快速决策

**身份**：画板操作默认使用 `--as user`。仅当需要以应用身份上传时使用 `--as bot`。

> 先判断「只读还是写入」，再在对应表内按上到下匹配，**命中即停**。

### A. 只读 · 查看 / 导出（不改画板）

| 用户需求 | 行动 |
|---|---|
| 查看画板内容 / 导出图片 | [`+export --output-type preview`](references/lark-whiteboard-export.md)                       |
| 导出 SVG 矢量图 | [`+export --output-type svg`](references/lark-whiteboard-export.md)                       |
| 提取画板的 Mermaid/PlantUML 源码 | [`+export --output-type source`](references/lark-whiteboard-export.md) |

### B. 写入 · 创作 / 编辑（会改画板，命中即停）

| 场景 | 行动 | 写入方式 | 对原内容 |
|---|---|---|---|
| 用户**已提供** Mermaid/PlantUML/SVG 代码，或明确指定用该格式 | 使用该代码 → [`+update`](references/lark-whiteboard-update.md)，`--input_format` 取单值 `mermaid` / `plantuml` / `svg`；写入非空已有画板并需要 overwrite 时，先确认会整板重建；若 SVG 用于修改已有画板，先走 [`routes/svg-edit.md`](routes/svg-edit.md) 有损确认 | overwrite / append | 按用户要求 |
| 从零新建复杂图表（架构/流程/组织等） | → **[§ 创作 Workflow](references/lark-whiteboard-workflow.md#创作-workflow)** | 首次写入 | — |
| 修改 / 增补已有画板 | → **[§ 编辑 Workflow](references/lark-whiteboard-workflow.md#编辑-workflow)** | 见该表 | 见该表 |

## Shortcuts

| Shortcut                                          | 说明 |
|---------------------------------------------------|---|
| [`+export`](references/lark-whiteboard-export.md) | 导出画板为预览图片、SVG 矢量图、代码或原始节点结构。 |
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
