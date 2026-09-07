# Codex 与 Claude 技能兼容

核验日期：2026-09-07。规范源为 `skills/<category>/<name>/SKILL.md`；两个客户端共用技能正文与随附资料。

## 官方依据与实现边界

| 依据 | 本仓库采用的行为 |
|---|---|
| [Astra 指导](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra) | 结合已有授权持续完成任务；审查隐藏停顿和重复验证 |
| [Codex Skills](https://learn.chatgpt.com/docs/build-skills) | 用途与触发词前置，正文和引用按需读取 |
| [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | 共享入口只保留项目约定，维护步骤按需加载 |
| [Claude Skills](https://code.claude.com/docs/en/skills) | 区分通用技能格式和 Claude 专属扩展 |
| [Claude 项目指令](https://code.claude.com/docs/en/memory) | `CLAUDE.md` 通过 `@AGENTS.md` 原生导入共享约定 |
| [Claude 最佳实践](https://code.claude.com/docs/en/best-practices) | 删除可从代码推断的重复规则，以真实任务校验指令效果 |

官方指导并不意味着所有客户端版本支持相同能力。当前本机核验基线为 Codex CLI 0.153.4 和 Claude Code 2.1.138；未升级客户端。

## 共享内容与宿主差异

- `name`、`description` 和 Markdown 正文是共享入口；保留仓库完整 frontmatter 与来源元数据。
- Claude 的 `context: fork`、`allowed-tools`、`disable-model-invocation`、`$ARGUMENTS` 和动态命令注入属于宿主能力。通用流程须有可理解的输入和执行步骤，不能把这些字段当作其他 Agent 的权限或工具保证。
- Codex 的 `agents/openai.yaml` 是可选宿主元数据；它不代替正文中的领域方法，也不要求 Claude 解析。
- 专用平台技能可以使用该平台的真实 API 和工具名；仅把通用工作的宿主调用方式改为能力条件，不把平台技能重写成含糊的通用流程。
- 路由目标可能是上游角色而非本地技能。先使用实际可用的等价能力；缺失可选角色时完成独立工作并说明限制，不因名字相似安装工具。
- 已有用户授权在后续步骤继续有效；新的目标、破坏性影响或真实仓库保护要求仍需解决。技能不能要求覆盖更高优先级的指令。

## 发现、安装与引用

Codex 当前官方文档推荐项目或用户级 `.agents/skills`，支持符号链接。安装器现有 `codex` 目标保留 `.codex/skills`，避免悄悄改变已有用户安装位置；项目级默认目标为 `.agents/skills`。本机 Codex 0.153.4 的实际发现测试作为兼容证据，不将旧目录声称为所有未来版本的默认。

Claude 使用 `.claude/skills` 或用户级 `~/.claude/skills`，显式调用形式为 `/skill-name`。Codex 使用 `$skill-name`。仅浏览仓库的分类 `skills/` 目录不等于已经注册到客户端技能列表。

复制或导出必须保留整个技能目录，包括 `references/`、`reference/`、`EXTENDED.md`、scripts、assets 和许可证。跨技能相对引用依赖配套技能；按单技能安装时应清楚标记这些依赖，不能假称缺失引用已随包交付。

官方 Codex 文档说明初始技能列表有上下文预算，描述可能被截短或技能被省略。用途前置可以改善截短后的可识别性；不要为同一套技能同时安装多个副本。仓库的 240 字符描述与 500 行入口上限是维护政策，并非模型限制。

## 审计与评测

`python scripts/audit_skill_instructions.py --json` 输出每个规范技能的随附文件摘要，以及共享入口、维护文档和 CI 文件。`findings` 是已知可确定问题；`review_hints` 是人工语义审阅线索，不单独阻断 CI。自动库存中的 `semantic_review: not_assessed` 明确表示没有代替语义审阅。

真实评测由 `scripts/run_instruction_evals.py` 显式启动；默认只输出计划，不调用模型，不进入定时 CI。场景在 `evals/cross-agent/cases.json`。评测以相同模型、推理档位、场景、权限和工具分别比较基线与候选。

```bash
python scripts/run_instruction_evals.py \
  --source /path/to/frozen-baseline \
  --output /tmp/skill-evals \
  --cohort baseline
# 明确运行模型时追加 --execute；候选使用 --cohort candidate
```

评测通过进程参数禁用无关全局技能，不改用户配置；真实外部写入替换为本地模拟服务。输出记录工具调用、耗时、token 和逐项断言。自动观察不构成语义验收。汇总器默认保持 unreviewed；只有显式传入位于被测 Agent 可写范围之外的受信任复核文件，且证据摘要一致，才应用任务结论。复核者可为受信任的人或独立于被测运行的 AI，必须准确声明身份和盲评边界。

用户已取消本次 Claude 登录与模型运行：Claude 仅进行静态和布局兼容验证，真实对照为 Codex/Astra 12 场景 × 前后 × 2 次，共 48 个场景运行。暂停场景包含实际后续用户回合，应单独记录回合数。不能把 Claude 的静态兼容检查称为模型实测通过。

本轮实测结果见 [Astra 行为对照](sources/reports/astra-behavior-comparison-2026-09-07.md)。维护和评测脚本在源码 checkout 中运行；npm 包用于安装技能，完整工具与报告随源码发布。

`skills/.npmignore` 排除 Python 字节码和解释器缓存。npm 自身还会省略技能中的 5 个 `.gitignore`（Git 元数据）；完整源码压缩包保留这些文件。脚本、引用与其他技能资源仍按清单验证。

使用 `summarize_instruction_evals.py --review-file <可信复核清单>` 汇总已复核记录；复核清单应由操作方检查完整记录后制作，不能从被测模型的成功声明自动生成。该工具不把 shell 字符串识别或最终标记缺失当成未发生副作用的证明。
