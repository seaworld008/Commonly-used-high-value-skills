#!/usr/bin/env python3
"""Import curated skills from simota/agent-skills with upstream tracking."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPO = "simota/agent-skills"
SOURCE_URL = f"https://github.com/{SOURCE_REPO}"
SOURCE_FILE = REPO_ROOT / "docs" / "sources" / "simota-agent-skills-2026-04.skills.json"


SELECTED_SKILLS: dict[str, list[tuple[str, str]]] = {
    "developer-engineering": [
        ("builder", "生产级业务逻辑、接口集成和类型安全实现。"),
        ("gateway", "接口设计、规范生成、版本策略和破坏性变更检查。"),
        ("schema", "数据库模式设计、迁移规划、索引策略和关系建模。"),
    ],
    "ai-workflow": [
        ("nexus", "多智能体任务分解、链路编排、执行协调和结果整合。"),
        ("sherpa", "把复杂任务拆成短步骤，控制漂移并推进交付。"),
        ("rally", "多会话并行执行编排，协调多个智能体共同完成任务。"),
    ],
    "ai-agent-platform": [
        ("oracle", "人工智能应用设计、评估、检索增强和安全护栏规划。"),
        ("arena", "多引擎方案竞赛与协作，比较结果并择优采用。"),
        ("sigil", "根据项目代码自动生成贴合仓库约定的技能。"),
    ],
    "engineering-workflow-automation": [
        ("guardian", "提交、分支、合并请求策略和变更粒度把关。"),
        ("harvest", "采集合并请求信息并生成工作报告和发布材料。"),
        ("latch", "配置和维护生命周期钩子、质量门禁和自动化守卫。"),
    ],
    "devops-sre": [
        ("beacon", "可观测性、服务目标、告警、容量和可靠性设计。"),
        ("triage", "事故首响、影响范围识别、恢复步骤和复盘整理。"),
        ("gear", "依赖、构建、容器、监控和开发环境运维优化。"),
    ],
    "finance-investing": [
        ("ledger", "云成本、预算告警、资源规格和人工智能工作负载成本优化。"),
        ("helm", "商业战略场景模拟、市场分析、指标预测和路线图规划。"),
        ("levy", "日本个税申报、收入分类、扣除优化和税额测算。"),
    ],
    "growth-operations-xiaohongshu": [
        ("growth", "搜索、社交、转化和人工智能引用优化的一体化增长。"),
        ("compete", "竞品研究、差异化定位、矩阵对比和竞争战卡。"),
        ("pulse", "关键指标、埋点、漏斗、留存和仪表盘规格设计。"),
    ],
    "office-white-collar": [
        ("morph", "文档格式转换、分发版生成和可复用转换脚本。"),
        ("stage", "演示文稿生成、叙事节奏设计和会议演讲优化。"),
        ("prism", "资料准备和提示设计，优化知识型工具的多格式输出。"),
    ],
    "knowledge-and-pm-integrations": [
        ("lore", "跨智能体知识沉淀、模式提炼和最佳实践传播。"),
        ("tome", "把仓库变更转化为学习文档、术语说明和设计记录。"),
        ("grove", "仓库结构、文档布局、测试脚本组织和迁移规划。"),
    ],
    "operations-general": [
        ("crest", "技术个人品牌、主页资料、文章和公开形象策略。"),
        ("hearth", "终端、编辑器和本地开发环境配置生成与审计。"),
        ("dawn", "提出适合短周期实现的个人项目创意和最小可行方案。"),
    ],
    "product-design": [
        ("voice", "用户反馈收集、满意度调研、评论分析和洞察提炼。"),
        ("trace", "会话回放分析、行为模式提取和体验问题叙事。"),
        ("researcher", "用户访谈、可用性测试、画像和旅程地图研究。"),
    ],
    "security-and-reliability": [
        ("breach", "红队场景、攻击路径、威胁建模和对抗演练设计。"),
        ("cloak", "隐私工程、敏感信息流、同意管理和数据治理。"),
        ("comply", "合规控制映射、审计轨迹和政策即代码实现。"),
    ],
    "multimodal-media": [
        ("sketch", "图像生成代码、提示优化、批量生成和成本估算。"),
        ("clay", "三维模型生成、网格处理、材质和游戏资产流水线。"),
        ("tone", "游戏音效、背景音乐、语音和音频管线生成。"),
    ],
    "deployment-platforms": [
        ("scaffold", "云基础设施、环境配置和本地开发部署脚手架。"),
        ("pipe", "持续集成工作流、触发策略、安全加固和复用设计。"),
        ("shard", "多租户架构、租户隔离、路由和规模化设计。"),
    ],
    "openclaw-memory-and-safety": [
        ("cast", "用户画像生成、角色注册、生命周期和跨智能体同步。"),
        ("omen", "预演失败模式，识别计划风险并给出优先级。"),
        ("warden", "发布前质量标准评估、评分卡和通过失败判定。"),
    ],
    "task-understanding-decomposition": [
        ("lens", "代码库理解、功能发现、数据流追踪和上下文调查。"),
        ("scout", "缺陷调查、复现步骤、根因分析和影响评估。"),
        ("ripple", "变更前影响分析，评估依赖链和一致性风险。"),
    ],
}


QUALITY_SUPPLEMENTS: dict[str, str] = {
    "levy": """
## Local Quality Supplement

Use this intake outline when a user asks for a tax walkthrough. Keep the result as general educational guidance, cite the relevant rule or official source when available, and ask the user to confirm facts before using any numeric estimate.

```text
Tax year:
Residence status and municipality:
Income categories:
  - salary:
  - business:
  - miscellaneous:
  - capital gains / crypto:
Major deductions:
  - basic / spouse / dependent:
  - social insurance:
  - medical:
  - donations:
Filing route:
  - refund filing:
  - required final return:
  - e-Tax:
Open questions:
  -
```
""".strip()
}


def split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.DOTALL)
    if not match:
        return "", text
    return match.group(1), text[match.end() :]


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def tags_for(category: str, name: str) -> list[str]:
    parts = [part for part in name.split("-") if part]
    base = {
        "developer-engineering": ["development"],
        "ai-workflow": ["ai", "workflow"],
        "ai-agent-platform": ["ai", "agent"],
        "engineering-workflow-automation": ["automation", "workflow"],
        "devops-sre": ["devops", "sre"],
        "finance-investing": ["finance"],
        "growth-operations-xiaohongshu": ["growth", "marketing"],
        "office-white-collar": ["office"],
        "knowledge-and-pm-integrations": ["knowledge"],
        "operations-general": ["productivity"],
        "product-design": ["product", "design"],
        "security-and-reliability": ["security"],
        "multimodal-media": ["media"],
        "deployment-platforms": ["deployment"],
        "openclaw-memory-and-safety": ["memory", "safety"],
        "task-understanding-decomposition": ["analysis", "planning"],
    }[category]
    return sorted(set(base + parts[:3]))


def render_frontmatter(category: str, name: str, description: str, today: str) -> str:
    tags = ", ".join(yaml_quote(tag) for tag in tags_for(category, name))
    lines = [
        "---",
        f"name: {name}",
        f"description: {yaml_quote(description)}",
        'version: "1.0.0"',
        'author: "seaworld008"',
        f'source: "github:{SOURCE_REPO}"',
        f"source_url: {yaml_quote(f'{SOURCE_URL}/tree/main/{name}')}",
        "license: MIT",
        f"tags: [{tags}]",
        f'created_at: "{today}"',
        f'updated_at: "{today}"',
        "quality: 5",
        'complexity: "advanced"',
        "---",
        "",
    ]
    return "\n".join(lines)


def resolve_source_dir(args_source_dir: str | None) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if args_source_dir:
        return Path(args_source_dir).resolve(), None
    tempdir = tempfile.TemporaryDirectory(prefix="simota-agent-skills-")
    target = Path(tempdir.name) / "repo"
    subprocess.run(["git", "clone", "--depth", "1", SOURCE_URL, str(target)], check=True)
    return target, tempdir


def source_commit(source_dir: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=source_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def strip_trailing_whitespace(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()) + ("\n" if text.endswith("\n") else "")


def normalize_text_tree(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        normalized = strip_trailing_whitespace(text)
        if normalized != text:
            path.write_text(normalized, encoding="utf-8")


def import_selected(source_dir: Path, repo_root: Path, apply: bool) -> list[dict]:
    today = date.today().isoformat()
    commit = source_commit(source_dir)
    imported: list[dict] = []

    for category, skills in SELECTED_SKILLS.items():
        for name, description in skills:
            source_skill_dir = source_dir / name
            source_skill_md = source_skill_dir / "SKILL.md"
            if not source_skill_md.exists():
                raise FileNotFoundError(f"Missing upstream skill: {source_skill_md}")

            destination = repo_root / "skills" / category / name
            raw = source_skill_md.read_text(encoding="utf-8", errors="replace")
            _, body = split_frontmatter(raw)
            skill_text = render_frontmatter(category, name, description, today) + body.lstrip()
            supplement = QUALITY_SUPPLEMENTS.get(name)
            if supplement:
                skill_text = skill_text.rstrip() + "\n\n" + supplement + "\n"
            skill_text = strip_trailing_whitespace(skill_text)

            if apply:
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(source_skill_dir, destination)
                normalize_text_tree(destination)
                (destination / "SKILL.md").write_text(skill_text.rstrip() + "\n", encoding="utf-8")

            imported.append(
                {
                    "video_name": name,
                    "normalized_slug": name,
                    "status": "verified_in_repo",
                    "repo_skill": f"skills/{category}/{name}/SKILL.md",
                    "source": f"{SOURCE_URL}/blob/main/{name}/SKILL.md",
                    "notes": "Curated from simota/agent-skills; selected to fill category capability gaps with upstream tracking.",
                    "upstream": {
                        "repo": SOURCE_REPO,
                        "path": f"{name}/SKILL.md",
                        "ref": "main",
                        "last_checked_at": today,
                        "last_synced_at": today if apply else None,
                        "last_synced_commit": commit,
                    },
                }
            )

    return imported


def write_source_mapping(entries: list[dict], repo_root: Path) -> None:
    today = date.today().isoformat()
    payload = {
        "video": {
            "url": SOURCE_URL,
            "checked_at": today,
            "note": "Curated per-category import from simota/agent-skills; refresh with scripts/sync_simota_agent_skills.py.",
        },
        "official_references": [
            {
                "name": "simota/agent-skills repository",
                "url": SOURCE_URL,
                "purpose": "Canonical upstream repository for the imported per-category specialist skills.",
            }
        ],
        "skills": entries,
    }
    SOURCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync curated simota/agent-skills into this repository.")
    parser.add_argument("--apply", action="store_true", help="Write imported skills and source mapping.")
    parser.add_argument("--source-dir", help="Use an already cloned simota/agent-skills directory.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    source_dir, tempdir = resolve_source_dir(args.source_dir)
    try:
        entries = import_selected(source_dir, repo_root, args.apply)
        if args.apply:
            write_source_mapping(entries, repo_root)
        print(
            f"{'Imported' if args.apply else 'Would import'} "
            f"{len(entries)} simota skills across {len(SELECTED_SKILLS)} categories."
        )
        if args.apply:
            print(f"Mapping: {SOURCE_FILE}")
    finally:
        if tempdir is not None:
            tempdir.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
