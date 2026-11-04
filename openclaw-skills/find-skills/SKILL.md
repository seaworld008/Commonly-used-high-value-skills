---
name: find-skills
description: 'Use when users do not know which skill fits a task, need to search installed skills or public skill catalogs, compare candidates, or decide whether to install one.'
zh_description: "在已安装技能和公开技能目录中检索、比较候选，帮助判断用哪个技能或是否安装。"
version: "1.1.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["find", "planning", "skills", "workflow"]'
created_at: "2026-03-15"
updated_at: "2026-11-04"
quality: 4
complexity: "intermediate"
---

# Find Skills

用户只描述目标、没有指定技能时，先在已有能力中找匹配项；只有确实缺少能力时才检索公开目录。
本技能负责检索、比较和给出可复查的推荐。安装属于单独动作：用户请求安装或当前任务已授权时才执行，
并且先完成来源与安全审查。

## 触发条件 / When to Use

- 用户问“有没有技能能做 X”“该用哪个技能”，或任务类型在本会话中首次出现。
- 当前加载的技能无法覆盖任务，需要确认缺口是否已有现成能力。
- 多个技能职责相近，需要说明各自边界并选出一个入口。
- 用户要求安装、替换或升级某个技能，需要先给出候选对比。

不适用：任务已有明确对应的已加载技能；用户只想要答案而不是工具；创建新技能（用 `skill-creator`）。

## 检索顺序 / Search Order

1. **宿主已提供的技能**：先看当前会话的技能列表或宿主的技能搜索工具。已有能力优先，不为同一意图再装一个。
2. **本仓库目录**：在仓库或已安装副本中按功能检索，而不是只按名称。

   ```bash
   # 在仓库根目录执行；catalog.json 由生成器维护
   python3 -c "import json;[print(s['path'],'|',s['description']) for s in json.load(open('docs/catalog.json'))['skills'] if 'pdf' in (s['name']+s['description']).lower()]"
   rg -n -i --glob 'SKILL.md' '^description:.*(pdf|form)' skills/
   ```

3. **公开目录**：只有前两步没有覆盖时才查询，例如 skills.sh 或 ClawHub。先运行 `--help`
   确认当前 CLI 的子命令和参数，命令名可能随版本变化：

   ```bash
   npx skills --help        # skills.sh CLI；常见为 find / add
   npx clawhub@latest --help   # ClawHub CLI；常见为 search / install
   ```

   网络受限、CLI 不可用或返回空结果时，如实记录“未检索到/未能检索”，不要编造候选、评分或下载量。

## 检索词 / Query Design

- 把目标拆成原子任务，每个用“动词 + 对象”表达：`fill pdf form`、`review terraform plan`。
- 同时用中文和英文、领域术语和工具名各查一次：`xlsx`、`spreadsheet`、`Excel 公式`。
- 记录用过的检索词，便于用户复查或扩展。

## 候选比较 / Comparison

每个候选至少核对以下证据，缺失项写“未核验”：

| 维度 | 需要的证据 |
|---|---|
| 功能匹配 | `description` 与正文是否覆盖当前任务，而非只是名字相似 |
| 可执行资产 | 是否带真实脚本、引用或模板，还是只有通用说明 |
| 来源与许可 | 仓库、提交或版本、许可证文件 |
| 维护状态 | 最近提交或发布时间、是否已被替代或退役 |
| 权限面 | 需要的网络、凭据、写入范围、宿主扩展 |
| 重叠 | 与已安装技能的职责冲突或命名冲突 |

本仓库的退役名称和替代入口记录在 `docs/sources/portfolio-policy.json`；推荐前确认候选不是已退役别名。

## 输出模板 / Recommendation

```markdown
目标：<一句话复述任务>
检索词：<列表>
已检索范围：宿主技能 / 本仓库 / skills.sh / ClawHub（注明哪些未能检索及原因）

推荐：<技能名>（来源、版本或提交）
理由：<覆盖了哪些原子任务；依据哪段 description 或文件>
备选：<1-2 个，并说明为何次选>
缺口：<没有技能覆盖的部分，建议直接完成或创建新技能>
安装：<已安装无需操作 / 需要安装，等待用户确认 / 已按用户要求安装并验证>
```

## 安装与采纳 / Install Only When Asked

1. 用户明确要求安装，或当前任务已授权安装时才执行；仅检索不代表授权。
2. 安装第三方技能前，用 `skill-security-auditor` 扫描并完成人工审查，记录来源提交和许可。
3. 按宿主文档安装到正确目录（本仓库见 `docs/client-install-guides.md`），不改写用户全局配置之外的范围。
4. 安装后读取新技能的 `SKILL.md`，用一个与当前任务相关的小输入验证它能被发现和加载。
5. 技能依赖的二进制、API key 或 OAuth 授权由用户提供；列出需要的项目，不自行获取或伪造。

## 边界与限制 / Boundaries

- 公开目录的排名、下载量和标签不等于质量或安全证明；以文件内容和来源为准。
- 不递归安装依赖链，不为“以后可能用到”批量安装技能。
- 受限容器、无写权限目录或离线环境可能无法安装；报告具体错误。
- 同一意图只推荐一个主入口，避免多个路由技能互相转交。
- 检索不到合适技能时，直接说明，并给出不依赖技能的完成方式。
