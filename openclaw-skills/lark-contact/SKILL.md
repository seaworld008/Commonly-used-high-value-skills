---
name: lark-contact
description: '飞书 / Lark 通讯录:按姓名 / 邮箱解析成 open_id,或按 open_id 反查姓名 / 部门 / 邮箱 / 联系方式 / 个人状态 / 签名,以及按关键词搜索当前用户可见的机器人 / 智能体(agent)。当用户提到一个名字要下一步发消息 / 排日程,或拿到 open_id 想查具体信息时使用。不负责部门树遍历、按部门列员工、组织架构图,这类需求走原生 OpenAPI。'
zh_description: "用于按姓名或邮箱解析飞书 open_id，并反查成员姓名、部门、邮箱和个人状态。"
version: "1.0.7"
author: larksuite
source: "github:larksuite/cli"
source_url: "https://github.com/larksuite/cli/tree/7beffb086d7fa3c5b843d8affa7c089f49cfc65e/skills/lark-contact"
license: MIT
tags: [feishu, lark, lark-cli, contacts, identity]
created_at: "2026-05-19"
updated_at: "2026-11-23"
quality: 3
complexity: intermediate
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli contact --help"
---

## 选哪个命令

**user 身份和 bot 身份是两条完全独立的路径**。先确定当前身份,再按下表选命令:

| 想做什么 | user 身份 | bot 身份 |
|---|---|---|
| 按姓名 / 邮箱搜员工拿 open_id | [`+search-user`](references/lark-contact-search-user.md) | 不支持 |
| 按关键词搜索当前用户可见的机器人 / 智能体 | [`+search-bot`](references/lark-contact-search-bot.md) | 不支持 |
| 已知 open_id 取他人资料 | `+search-user --user-ids <id>` | [`+get-user --user-id <id>`](references/lark-contact-get-user.md) |
| 查看自己 | `+get-user` 或 `+search-user --user-ids me` | 不支持 |
| 查同事的个人状态 / 签名 | `user_profiles batch_query` | 不支持 |

已知 open_id 只是想发消息 / 排日程,不必经过 contact —— 直接 [`lark-im`](../lark-im/SKILL.md) / [`lark-calendar`](../lark-calendar/SKILL.md)。

### 名字没说清是人还是机器人 / 智能体

用户给的名字常常不表明类型。例如「和 reviewDuck 约个会」里的 reviewDuck 可能是同事昵称,也可能是机器人。
- 名字含 bot / agent / AI / 助手 / 机器人 / 智能体 / assistant 等明显特征时,反过来先搜机器人更快
- 不确定的话两边都搜一下

## 典型场景

找张三给他发消息:先搜,确认 open_id,再发:

```bash
lark-cli contact +search-user --query "张三" --has-chatted --as user
lark-cli im +messages-send --user-id ou_xxx --text "Hi!"
```

批量查同事的个人状态 / 个性签名(先用 schema 看参数)。

```bash
lark-cli schema contact.user_profiles.batch_query
lark-cli contact user_profiles batch_query \
  --params '{"user_id_type":"open_id"}' \
  --data '{"user_ids":["ou_xxx","ou_yyy"],"query_option":{"include_personal_status":true,"include_description":true}}' \
  --as user
```

搜索命中多条且后续操作有副作用(发消息、邀请会议等),把候选列给用户挑;不要擅自选第一条。

## 搜索机器人 / 智能体

`+search-bot` 使用 user 身份按关键词搜索当前用户可见的机器人,返回 `ou_` 开头的机器人 open_id。参数细节等见 [`lark-contact-search-bot.md`](references/lark-contact-search-bot.md)。

```bash
lark-cli contact +search-bot --query '会议助手' --as user
lark-cli contact +search-bot --queries '会议助手,日报助手,审批助手' --as user
```

## 注意事项

- **41050 / Permission denied** 受当前身份的可见范围限制(三条命令都可能遇到)。细节见 [`lark-shared`](../lark-shared/SKILL.md)。
- **跨租户用户**(`is_cross_tenant=true`)多数业务字段为空字符串,这是飞书可见性规则,下游做空值兜底。
- **ID 类型**:`+get-user` 可通过 `--user-id-type` 使用 `open_id`、`union_id` 或 `user_id`;`+search-user` 使用用户 open_id;`+search-bot` 不支持按 ID 查询,它按关键词搜索并返回机器人 open_id。

## 不在本 skill 范围

- 发消息 / 查聊天记录 → [`lark-im`](../lark-im/SKILL.md)
- 排日程 / 邀请会议 → [`lark-calendar`](../lark-calendar/SKILL.md)
- 部门树 / 按部门列员工 / 组织架构 → [`lark-openapi-explorer`](../lark-openapi-explorer/SKILL.md) 查找原生接口

<!-- LOCAL-CURATION-SUPPLEMENT:START -->
## 端到端消歧与排查示例 / End-to-End Lookup Examples

下面演示从模糊姓名检索到精确 `open_id` 确认、跨租户空值兜底以及交接下游技能（发消息 / 约会）的完整操作流程：

```bash
# Step 1: 先用关键词检索同名候选（默认以 user 身份读取当前可见通讯录）
lark-cli contact +search-user --query '张敏' --as user

# Step 2: 若返回多个同名候选项，向用户展示姓名 + 部门 + open_id 并等待确认后再取详情
# 确认目标 open_id 为 ou_example_target 后再拉取完整联系信息与邮箱：
lark-cli contact +get-user \
  --user-id 'ou_example_target' \
  --user-id-type open_id \
  --as user

# Step 3: 批量校验多个参与者邮箱并映射到 open_id（用于创建日程或拉群）
lark-cli contact +get-user \
  --emails 'alice@example.com,bob@example.com' \
  --as user
```

### 常见边界与错误排查 Checklist

- **41050 / 权限或可见性受限**：优先核对当前 CLI 登录身份是否为 `user`（`bot` 往往受限于应用通讯录授权范围）；若仍无结果，确认目标成员不在当前用户的隔离部门内。
- **跨租户对象 (`is_cross_tenant: true`)**：`department_ids`、`email`、`mobile` 等内部字段会返回空字符串或省略，仅将 `open_id`、`name` 与 `avatar` 传给下游 [`lark-im`](../lark-im/SKILL.md) 或 [`lark-calendar`](../lark-calendar/SKILL.md)。
- **写前不可猜测唯一匹配**：当 `+search-user` 返回 >= 2 条记录且下一步将触发发消息、邀请会议或审批抄送时，必须列出候选项请用户选择。
<!-- LOCAL-CURATION-SUPPLEMENT:END -->
