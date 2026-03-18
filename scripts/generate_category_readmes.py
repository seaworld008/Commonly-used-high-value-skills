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
