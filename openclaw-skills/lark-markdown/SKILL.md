---
name: lark-markdown
description: '飞书 Markdown：查看、创建、上传和编辑 Markdown 文件。当用户需要创建或编辑 Markdown 文件、读取或修改时使用。'
version: 1.1.0
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/main/skills/lark-markdown"
license: MIT
tags: '[feishu, lark, lark-cli, markdown, docs]'
created_at: "2026-05-19"
updated_at: "2026-05-19"
quality: 3
complexity: intermediate
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli markdown --help"
---

# markdown (v1)

**CRITICAL — 开始前 MUST 先用 Read 工具读取 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)，其中包含认证、权限处理**

## 快速决策

- 用户要**上传、创建一个原生 `.md` 文件**，使用 `lark-cli markdown +create`
- 用户要**读取 Drive 里某个 `.md` 文件内容**，使用 `lark-cli markdown +fetch`
- 用户要对 Markdown 文件做**局部文本替换 / 正则替换**，优先使用 `lark-cli markdown +patch`
- 用户要**覆盖更新 Drive 里某个 `.md` 文件内容**，使用 `lark-cli markdown +overwrite`
- 用户要把本地 Markdown **导入成在线新版文档（docx）**，不要用本 skill，改用 [`lark-drive`](../lark-drive/SKILL.md) 的 `lark-cli drive +import --type docx`
- 用户要对 Markdown 文件做**rename / move / delete / 搜索 / 权限 / 评论**等云空间操作，不要留在本 skill，切到 [`lark-drive`](../lark-drive/SKILL.md)

## 核心边界

- 本 skill 处理的是 **Drive 中作为普通文件存储的 Markdown**，不是 docx 文档
- `--name` 和本地 `--file` 文件名都必须显式带 `.md` 后缀；不满足时 shortcut 会直接报错
- `--content` 支持：
  - 直接传字符串
  - `@file` 从本地文件读取内容
  - `-` 从 stdin 读取内容
- `markdown +patch` 的内部语义是：**先完整下载 Markdown，再本地替换，再整文件覆盖上传**
- `markdown +patch` 不是服务端原子 patch；它是 CLI 侧编排出来的局部更新能力
- `markdown +patch` 当前只支持**单组** `--pattern` / `--content`
- `markdown +patch` 替换后的最终内容**不能为空**；如果替换后整篇 Markdown 变成空字符串，CLI 会直接报错，不会上传空文件
- `--file` 只接受本地 `.md` 文件路径

## Shortcuts（推荐优先使用）

Shortcut 是对常用操作的高级封装（`lark-cli markdown +<verb> [flags]`）。有 Shortcut 的操作优先使用。

| Shortcut | 说明 |
|----------|------|
| [`+create`](references/lark-markdown-create.md) | Create a Markdown file in Drive |
| [`+fetch`](references/lark-markdown-fetch.md) | Fetch a Markdown file from Drive |
| [`+patch`](references/lark-markdown-patch.md) | Patch a Markdown file in Drive via fetch-local-replace-overwrite |
| [`+overwrite`](references/lark-markdown-overwrite.md) | Overwrite an existing Markdown file in Drive |

## 参考

- [lark-shared](../lark-shared/SKILL.md) — 认证和全局参数
- [lark-drive](../lark-drive/SKILL.md) — Drive 文件管理、导入 docx、move/delete/search 等

## Repository Curation Notes

### When to Use

- Use this skill when the user explicitly asks for 飞书 Markdown 文件 work in Feishu/Lark.
- Use it before falling back to raw OpenAPI calls when the requested action matches the supported shortcut or service command.
- Use `lark-shared` first when credentials, identity, scopes, or tenant visibility are unclear.
- Prefer bounded, inspectable commands and show the user candidate records before taking side-effecting actions.

### Core Capabilities

- Discover the relevant `lark-cli markdown` command surface with `--help` before composing requests.
- Keep identity explicit with `--as user` or `--as bot` whenever the result depends on user-visible resources.
- Request the narrowest useful output format; use JSON for automation and table/pretty output only for human inspection.
- Handle permission errors by checking missing scopes and current identity instead of retrying the same command blindly.

### Common Patterns

```bash
# Inspect the official command surface before acting
lark-cli markdown --help

# Verify authentication and granted scopes when a command fails
lark-cli auth status
lark-cli auth check --help

# Preview side-effecting operations when supported
lark-cli markdown --help | sed -n '1,80p'
```

- For read flows, first locate the target resource, then fetch details with an ID-based command.
- For write flows, validate IDs, scopes, and ownership before issuing create/update/delete operations.
- For ambiguous people, chats, documents, tables, or meetings, list candidates and ask the user to choose.
- For automation output, keep stable IDs, URLs, timestamps, and the exact command used in the final summary.

### Boundaries

- Do not invent Feishu tokens, open IDs, chat IDs, document tokens, table IDs, or meeting IDs.
- Do not bypass tenant permission controls; ask the user or administrator to grant the required scope or visibility.
- Do not use raw `lark-cli api` until the skill-specific shortcuts and registered commands have been checked.
- Do not perform destructive changes without a clear user request and, when possible, a dry-run or read-back verification.
