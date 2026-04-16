#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path


SKILL_FILENAME = "SKILL.md"

CATEGORY_METADATA = {
    "ai-agent-platform": {
        "title": "AI 平台与 Agent 开发 / AI Agent Platform",
        "summary": "围绕 AI 平台能力、Agent 构建、设计到代码以及主动式工作流的技能集合。",
    },
    "deployment-platforms": {
        "title": "部署平台 / Deployment Platforms",
        "summary": "聚焦 Vercel、Netlify、Render、Cloudflare 等部署平台的发布与接入技能。",
    },
    "developer-engineering": {
        "title": "开发工程 / Developer Engineering",
        "summary": "覆盖开发、测试、性能、架构、数据库和工程效率的核心技能集合。",
    },
    "devops-sre": {
        "title": "DevOps / SRE",
        "summary": "面向发布、CI/CD、可观测性、故障响应和环境治理的技能集合。",
    },
    "engineering-workflow-automation": {
        "title": "工程工作流自动化 / Workflow Automation",
        "summary": "聚焦 GitHub、浏览器自动化、CI 排障、Playwright 与工程协作自动化。",
    },
    "finance-investing": {
        "title": "金融投资 / Finance Investing",
        "summary": "覆盖金融数据、估值、风控、回测、投研写作和事件驱动分析的技能集合。",
    },
    "growth-operations-xiaohongshu": {
        "title": "增长运营 / Growth Operations",
        "summary": "聚焦小红书、社媒、内容、归因、竞品和增长分析的技能集合。",
    },
    "knowledge-and-pm-integrations": {
        "title": "项目管理与知识库集成 / Knowledge and PM Integrations",
        "summary": "连接 Notion、Linear 和规格到实施流程的知识与项目管理技能集合。",
    },
    "multimodal-media": {
        "title": "多模态内容 / Multimodal Media",
        "summary": "聚焦图像、音频、视频、截图、摘要与转写的多模态生产力技能集合。",
    },
    "office-white-collar": {
        "title": "办公与文档 / Office and Documents",
        "summary": "覆盖文档、表格、演示、PDF 与会议内容处理的办公生产力技能集合。",
    },
    "openclaw-memory-and-safety": {
        "title": "记忆与安全 / Memory and Safety",
        "summary": "聚焦输入防护、RAG 和标准化操作手册的安全与记忆技能集合。",
    },
    "operations-general": {
        "title": "通用运营 / General Operations",
        "summary": "覆盖品牌、事实核查、内部沟通、主题与常用运营辅助技能。",
    },
    "product-design": {
        "title": "产品与设计 / Product and Design",
        "summary": "聚焦产品分析、设计系统、UX 研究与 SaaS 产品设计能力。",
    },
    "security-and-reliability": {
        "title": "安全治理与稳定性 / Security and Reliability",
        "summary": "覆盖 Sentry、安全最佳实践、威胁建模与安全所有权分析的技能集合。",
    },
    "task-understanding-decomposition": {
        "title": "任务理解与拆解 / Task Understanding",
        "summary": "聚焦 brainstorming、research、计划编写、skills 检索与任务拆解。",
    },
}

CATEGORY_USAGE_GUIDES = {
    "ai-agent-platform": """
<a id="hermes-graphify-gsd-global-workflow"></a>
## Hermes + graphify + GSD 全局非侵入式工作流

`hermes-graphify-gsd-nonintrusive-workflow` 适合在还没有进入具体项目之前，先把 Hermes Agent、graphify 和 GSD 组合成一套可复用、可升级、非侵入式的本机工作流。

### 什么时候使用

- 想让 Hermes 负责 orchestration / memory / execution。
- 想让 graphify 负责代码图谱、架构回忆和低成本刷新。
- 想让 GSD 负责 planning cadence、phase management 和执行节奏。
- 想保留 Hermes、graphify、GSD 上游仓库的干净状态，不希望为了本机集成去 patch 上游源码。
- 想把适配层放在 wrappers、项目脚本和文档中，方便未来升级。

### 推荐提示词

```text
请使用 hermes-graphify-gsd-nonintrusive-workflow，帮我检查本机 Hermes 是否已安装，并在不修改上游仓库代码的前提下，配置 graphify 和 GSD 的全局工作流。
```

### 核心执行原则

1. 先检查 `command -v hermes` 和 `hermes --version`。
2. 如果 Hermes 不存在，只提示用户手动安装 Hermes，不自动安装 Hermes。
3. 如果 Hermes 已存在，再安装或升级 graphify 与 GSD。
4. graphify 使用当前 PyPI 包名 `graphifyy`，CLI 入口仍是 `graphify`。
5. GSD 默认使用 Codex runtime：`npx -y get-shit-done-cc@latest --codex --global --sdk`。
6. 优先创建或复用 `~/.local/bin/` wrappers，不直接修改 Hermes、graphify、GSD 上游源码。

### 可复用文件

| 文件 | 用途 |
|------|------|
| `templates/bootstrap-toolchain.sh` | 检查 Hermes，并安装/升级 graphify 与 GSD。 |
| `templates/graphify-wrapper.sh` | 在多个 Python 环境中寻找可 import graphify 的解释器。 |
| `templates/gsd-sdk-wrapper.sh` | 通过稳定路径调用 GSD SDK CLI。 |
| `templates/ai-workflow.sh` | 给项目提供统一的 `doctor` / `context` / `sync` 入口。 |
| `references/first-install.md` | 首次安装策略和推荐命令。 |
| `references/upgrade-contract.md` | 升级时优先修 wrappers 和项目脚本，而不是上游源码。 |

### 常用验证命令

```bash
command -v hermes
hermes --version
command -v graphify
graphify --help
command -v gsd-sdk
gsd-sdk --version
```

<a id="hermes-graphify-gsd-runtime-operator"></a>
## Hermes + graphify + GSD Runtime Operator

`hermes-graphify-gsd-runtime-operator` 适合在仓库已经完成接入之后，专门处理运行态诊断、writer ownership、auto-continue、handoff / blocked / lease / cron 等状态问题。

### 什么时候使用

- 想知道“现在是谁在写”。
- 想确认当前 repo 还是不是推荐 writer surface。
- 想排查 `auto-progress` 一直显示 running 的原因。
- 想清理旧 sandbox / worktree 遗留的 writer lease。
- 想确认 handoff、blocked、planning mirror、lease 状态是否一致。

### 推荐提示词

```text
请使用 hermes-graphify-gsd-runtime-operator，检查当前仓库的 auto-continue / writer lease / blocked / handoff 状态，并告诉我现在是否还是主仓库在负责写入。
```

### 推荐先跑的命令

```bash
./scripts/ai-workflow.sh doctor
./scripts/ai-workflow.sh auto-execution-surface-show
./scripts/ai-workflow.sh auto-runner-show
./scripts/ai-workflow.sh auto-progress
./scripts/ai-workflow.sh auto-workflow-state-show
```

### 和其他技能的关系

- 还没接入工作流时，先用 `hermes-graphify-gsd-nonintrusive-workflow` 或 `hermes-graphify-gsd-project-integration`。
- 已经接入，只是运行态异常时，优先切到 `hermes-graphify-gsd-runtime-operator`。
""",
    "engineering-workflow-automation": """
<a id="hermes-graphify-gsd-project-workflow"></a>
## Hermes + graphify + GSD 项目接入工作流

`hermes-graphify-gsd-project-integration` 适合在一个具体仓库中落地 Hermes + graphify + GSD 工作流。它关注的是项目内脚本、项目文档、图谱刷新、规划上下文和可验证的本地操作入口。

### 什么时候使用

- 想给某个仓库添加 `scripts/graphify-sync.sh`。
- 想给某个仓库添加统一入口 `scripts/ai-workflow.sh`。
- 想在 `AGENTS.md` 中告诉未来 AI 助手：先读什么、怎么刷新图谱、哪些目录是本地工作流产物。
- 想在 `README.md` 中给人类开发者写清楚项目级 AI workflow。
- 想把 `.planning/`、`graphify-out/` 等本地产物放进 `.gitignore`。
- 想在改代码前后用 graphify 保持项目架构图谱新鲜。

### 推荐提示词

```text
请使用 hermes-graphify-gsd-project-integration，把当前仓库接入 Hermes + graphify + GSD 工作流。请添加必要脚本、更新 AGENTS.md / README.md / .gitignore，并运行可用的验证命令。
```

### 推荐接入顺序

1. 先确认 Hermes 是用户已经安装好的前置条件。
2. 如果 Hermes 存在，安装或升级 graphify 与 GSD 全局工具链。
3. 审计当前仓库是否已有 `AGENTS.md`、`README.md`、`scripts/`、`.planning/`、`.codex/`、`graphify-out/`。
4. 复用已有脚本；只有缺失时才新增薄脚本层。
5. 添加或更新 `scripts/graphify-sync.sh`，支持 `status`、`smart`、`force`、`serve`。
6. 视项目需要添加 `scripts/ai-workflow.sh`，支持 `doctor`、`context`、`sync`、`force`、`next`。
7. 更新 `AGENTS.md` 和 `README.md`，让 AI 助手和人类开发者都能理解这套流程。
8. 把 `.planning/` 和 `graphify-out/` 加入 `.gitignore`，除非用户明确想提交这些产物。
9. 跑真实命令验证，避免只写文档不验证。

### 可复用文件

| 文件 | 用途 |
|------|------|
| `templates/graphify-sync.sh` | 项目级 graphify 刷新脚本，优先做低成本代码图谱刷新。 |
| `templates/ai-workflow.sh` | 项目级 AI 工作流统一入口。 |
| `templates/agents-section.md` | 可插入项目 `AGENTS.md` 的工作流说明。 |
| `templates/readme-section.md` | 可插入项目 `README.md` 的用户说明。 |
| `templates/bootstrap-toolchain.sh` | 项目接入前的工具链 bootstrap。 |
| `references/integration-checklist.md` | 仓库接入检查清单。 |
| `references/first-install.md` | repo 级首次安装策略。 |

### 常用验证命令

```bash
command -v hermes
hermes --version
command -v graphify
graphify --help
command -v gsd-sdk
gsd-sdk --version
./scripts/graphify-sync.sh status
./scripts/graphify-sync.sh smart
./scripts/ai-workflow.sh doctor
./scripts/ai-workflow.sh context
```

### 和全局工作流技能的关系

推荐顺序是先全局、再项目：

```text
第一步：使用 hermes-graphify-gsd-nonintrusive-workflow，建立非侵入式全局工具链和升级契约。
第二步：进入目标仓库，使用 hermes-graphify-gsd-project-integration，把脚本、文档和验证流程接进去。
```

如果你只想给一个仓库快速接入，也可以直接使用 `hermes-graphify-gsd-project-integration`。它会先检查全局工具链，再处理项目内文件。

<a id="gsd-graphify-brownfield-bootstrap"></a>
## GSD + graphify Brownfield Bootstrap

`gsd-graphify-brownfield-bootstrap` 适合复杂 brownfield 仓库，特别是当前仓库缺少 `.planning/`、需要手工种下 current-state / roadmap / docs 基线，而且不想依赖交互式 `gsd-sdk init` 的时候。

### 什么时候使用

- 现有仓库想接入 GSD + graphify，但 `.planning/` 还是空的。
- 想统一 one canonical brownfield bootstrap 流程给团队复用。
- 想把 `.codex/`、`graphify-out/`、`.planning/`、README / AGENTS / docs 一次性收敛起来。
- 想在大改造前先沉淀 current state、entrypoints、roadmaps。

### 推荐提示词

```text
请使用 gsd-graphify-brownfield-bootstrap，为当前 brownfield 仓库建立统一的 GSD + graphify 启动流程，并手工种下 .planning 基线，不要依赖交互式 gsd-sdk init。
```

### 典型产物

1. `./.codex/` 本地 runtime 文件
2. `scripts/graphify-sync.sh`
3. `graphify-out/`
4. 手工 seeded 的 `.planning/`
5. `AGENTS.md`、`README.md`、docs 中的 brownfield 指引

### 和项目接入技能的关系

- 普通仓库接入优先用 `hermes-graphify-gsd-project-integration`。
- 发现仓库确实需要补 `.planning/`、补 brownfield current-state baseline 时，再切到 `gsd-graphify-brownfield-bootstrap`。
""",
}


def split_frontmatter(text: str) -> tuple[str | None, str]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.DOTALL)
    if not match:
        return None, text
    return match.group(1), text[match.end() :]


def extract_description(frontmatter: str | None) -> str | None:
    if not frontmatter:
        return None
    match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return re.sub(r"\s+", " ", value).strip()


def derive_description_from_body(body: str) -> str:
    overview_match = re.search(
        r"^##\s+(Overview|概述)\s*$([\s\S]+?)(?=^##\s+|\Z)",
        body,
        re.MULTILINE,
    )
    if overview_match:
        overview_block = overview_match.group(2)
        description = derive_description_from_body(overview_block)
        if description != "Skill available in this category.":
            return description

    in_code = False
    collected = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line:
            if collected:
                break
            continue
        if line.startswith("#"):
            continue
        if line in {"---", "***"}:
            continue
        if line.startswith(("**Tier:**", "**Category:**", "**Domain:**", "**Purpose:**", "**Tags:**", "**Maintainer:**")):
            continue
        if line.startswith(">"):
            continue
        if line.startswith("**") and line.endswith("**"):
            continue
        if line.startswith(("- ", "* ", "|")):
            if collected:
                break
            continue
        collected.append(re.sub(r"\s+", " ", line))
        if len(" ".join(collected)) > 220:
            break
    if collected:
        return " ".join(collected)
    return "Skill available in this category."


def load_skill_summary(skill_dir: Path) -> dict:
    raw_text = (skill_dir / SKILL_FILENAME).read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(raw_text)
    description = extract_description(frontmatter) or derive_description_from_body(body)
    richness = sum(1 for name in ("scripts", "references", "assets") if (skill_dir / name).exists())
    return {"name": skill_dir.name, "description": description, "richness": richness}


def title_case_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def render_category_readme(category_name: str, skills: list[dict]) -> str:
    metadata = CATEGORY_METADATA.get(
        category_name,
        {
            "title": title_case_slug(category_name),
            "summary": "该分类下聚合了一组相关的高价值技能。",
        },
    )
    sorted_skills = sorted(skills, key=lambda item: item["name"])
    featured = sorted(skills, key=lambda item: (-item["richness"], item["name"]))[:4]

    lines = [
        f"# {metadata['title']}",
        "",
        "> This file is generated from the skill tree. Update source skills and rerun `python3 scripts/generate_category_readmes.py`.",
        "",
        metadata["summary"],
        "",
        f"当前分类共 **{len(sorted_skills)}** 个技能。",
        "",
        "## 推荐先看",
        "",
    ]

    for item in featured:
        lines.append(f"- [{item['name']}](./{item['name']}/) - {item['description']}")

    usage_guide = CATEGORY_USAGE_GUIDES.get(category_name)
    if usage_guide:
        lines.extend(["", usage_guide.strip()])

    lines.extend(
        [
            "",
            "## 技能总览",
            "",
            "| 技能 | 简介 | 目录 | 详情 |",
            "|------|------|------|------|",
        ]
    )

    for item in sorted_skills:
        lines.append(
            f"| `{item['name']}` | {item['description']} | [目录](./{item['name']}/) | [SKILL.md](./{item['name']}/SKILL.md) |"
        )

    lines.extend(
        [
            "",
            "## 维护方式",
            "",
            "- 新增技能时保持 `skills/<category>/<skill-name>/SKILL.md` 结构。",
            "- 若技能有 `scripts/`、`references/`、`assets/`，优先复用并保持说明同步。",
            "- 修改分类内容后可重新运行：`python3 scripts/generate_category_readmes.py`",
            "",
        ]
    )

    return "\n".join(lines)


def discover_category_skills(category_dir: Path) -> list[dict]:
    skills = []
    for child in sorted(category_dir.iterdir()):
        if not child.is_dir():
            continue
        if (child / SKILL_FILENAME).exists():
            skills.append(load_skill_summary(child))
    return skills


def generate_category_readmes(skills_root: Path | str) -> list[Path]:
    skills_root = Path(skills_root)
    generated = []
    for category_dir in sorted(skills_root.iterdir()):
        if not category_dir.is_dir():
            continue
        skills = discover_category_skills(category_dir)
        if not skills:
            continue
        output_path = category_dir / "README.md"
        output_path.write_text(render_category_readme(category_dir.name, skills), encoding="utf-8")
        generated.append(output_path)
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate README.md files for each skill category.")
    parser.add_argument(
        "--skills-root",
        default=str(Path(__file__).resolve().parents[1] / "skills"),
        help="Skills root directory (default: ./skills)",
    )
    args = parser.parse_args()
    generated = generate_category_readmes(args.skills_root)
    print(f"Generated {len(generated)} category README files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
