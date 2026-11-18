---
name: lark-openapi-explorer
description: '飞书/Lark 原生 OpenAPI 探索：从官方文档库中挖掘未经 CLI 封装的原生 OpenAPI 接口。当用户的需求无法被现有 lark-* skill 或 lark-cli 已注册命令满足，需要查找并调用原生飞书 OpenAPI 时使用。'
zh_description: "飞书/Lark 原生 OpenAPI 探索：从官方文档库中挖掘未经 CLI 封装的原生 OpenAPI 接口。"
version: "1.0.5"
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/7beffb086d7fa3c5b843d8affa7c089f49cfc65e/skills/lark-openapi-explorer"
license: MIT
tags: [feishu, lark, lark-cli, openapi, api]
created_at: "2026-05-19"
updated_at: "2026-11-17"
quality: 4
complexity: advanced
metadata:
  requires:
    bins: ["lark-cli"]
---

# OpenAPI Explorer

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md) 了解认证、身份切换和安全规则。

当用户的需求**无法被现有 skill 或 CLI 已注册 API 覆盖**时，使用本技能从飞书官方 markdown 文档库中逐层挖掘原生 OpenAPI 接口，然后通过 `lark-cli api` 裸调完成任务。

## 文档库结构

飞书 OpenAPI 文档以 markdown 层级组织：

```
llms.txt                          ← 顶层索引，列出所有模块文档链接
  └─ llms-<module>.txt            ← 模块文档，包含功能概述 + 底层 API 文档链接
       └─ <api-doc>.md            ← 单个 API 的完整说明（方法/路径/参数/响应/错误码）
```

文档入口：

| 品牌 | 入口 URL |
|------|----------|
| 飞书 (Feishu) | `https://open.feishu.cn/llms.txt` |
| Lark | `https://open.larksuite.com/llms.txt` |

> 所有文档以**中文**编写。如果用户使用英文交流，需将文档内容翻译为英文后输出。

## 挖掘流程

严格按以下步骤逐层检索，**不要跳步或猜测 API**：

### Step 1：确认现有能力不足

```bash
# 先检查是否已有对应的 skill 或已注册 API
lark-cli <可能的service> --help
```

如果已有对应命令或 shortcut，直接使用，**不需要继续挖掘**。

### Step 2：从顶层索引定位模块

用 WebFetch 获取顶层索引，找到与需求相关的模块文档链接：

```
WebFetch https://open.feishu.cn/llms.txt
  → 提取问题："列出所有模块文档链接，找出与 <用户需求关键词> 相关的链接"
```

- 飞书品牌使用 `open.feishu.cn`
- Lark 品牌使用 `open.larksuite.com`
- 如不确定用户品牌，默认使用飞书

### Step 3：从模块文档定位具体 API

用 WebFetch 获取模块文档，找到具体 API 的文档链接：

```
WebFetch https://open.feishu.cn/llms-docs/zh-CN/llms-<module>.txt
  → 提取问题："找出与 <用户需求> 相关的 API 说明和文档链接"
```

### Step 4：获取 API 完整规范

用 WebFetch 获取具体 API 文档，提取完整的调用规范：

```
WebFetch https://open.feishu.cn/document/server-docs/.../<api>.md
  → 提取问题："返回完整 API 规范：HTTP 方法、URL 路径、路径参数、查询参数、请求体字段（名称/类型/必填/说明）、响应字段、所需权限、错误码"
```

### Step 5：通过 CLI 调用 API

使用 `lark-cli api` 裸调：

```bash
# GET 请求
lark-cli api GET /open-apis/<path> --params '{"key":"value"}'

# POST 请求
lark-cli api POST /open-apis/<path> --data '{"key":"value"}'

# PUT 请求
lark-cli api PUT /open-apis/<path> --data '{"key":"value"}'

# DELETE 请求
lark-cli api DELETE /open-apis/<path>
```

## 输出规范

向用户呈现挖掘结果时，按以下格式组织：

1. **API 名称与功能**：一句话描述
2. **HTTP 方法与路径**：`METHOD /open-apis/...`
3. **关键参数**：列出必填和常用可选参数
4. **所需权限**：scope 列表
5. **调用示例**：给出 `lark-cli api` 的完整命令
6. **注意事项**：频率限制、特殊约束等

如果用户使用英文交流，将以上所有内容翻译为英文。

## 安全规则

- **按实际副作用判断写入授权**：POST/PUT/PATCH/DELETE 等修改资源的调用须在用户已授权的对象与范围内；不能仅按 HTTP 方法名推定读写。高风险确认沿用 `lark-shared` 协议
- 建议先用 `--dry-run` 预览请求（如支持）
- 不要猜测 API 路径或参数——必须从文档中获取确认
- 涉及敏感操作（删除群、移除成员等）时，向用户说明影响范围

## 使用场景示例

### 场景 1：用户需要拉人进群（优先使用已注册资源）

先按 [`lark-im`](../lark-im/SKILL.md) 的 `chat.members.create` 资源与身份条件执行，不将已收录能力当成未封装 API。只有本机 `lark-cli im --help` / 对应资源帮助确认当前安装版本缺少所需能力时，才进入官方文档发现链，核对方法、参数、scope 和已有写入授权后准备原生请求。

### 场景 2：用户需要设置群公告

```bash
# Step 1: 确认 CLI 没有封装
lark-cli im --help
# 只有当前帮助确认缺少所需能力时，继续发现；已有命令则使用它

# Step 2-4: 挖掘文档
# → PATCH /open-apis/im/v1/chats/:chat_id/announcement

# Step 5: 调用
lark-cli api PATCH /open-apis/im/v1/chats/oc_xxx/announcement \
  --data '{"revision":"0","requests":["<html>公告内容</html>"]}'
```

## 参考

- [lark-shared](../lark-shared/SKILL.md) — 认证和全局参数
- [lark-skill-maker](../lark-skill-maker/SKILL.md) — 如需将挖掘到的 API 固化为新 Skill

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

- Prefer the upstream workflow for Lark Openapi Explorer; this section only adds local quality
  guardrails.
- Do not invent project facts when required files, vaults, services, or tools are
  unavailable.
- Stop and ask for clarification when the next action could overwrite user work,
  expose private data, or change production state.
- Treat skill selection as routing, not ceremony: invoke only the narrowest
  applicable workflow and keep user or repository instructions authoritative.
<!-- LOCAL-QUALITY-SUPPLEMENT:END -->
