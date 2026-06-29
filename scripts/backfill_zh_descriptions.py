#!/usr/bin/env python3
"""Backfill concise zh_description fields for existing skills.

The repository requires zh_description in public Chinese surfaces. This helper
adds one-line Chinese summaries without changing existing zh_description values.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CATEGORY_CN = {
    "ai-agent-platform": "AI Agent 平台",
    "ai-workflow": "AI 工作流",
    "deployment-platforms": "部署平台",
    "developer-engineering": "开发工程",
    "devops-sre": "DevOps/SRE",
    "engineering-workflow-automation": "工程自动化",
    "finance-investing": "金融投资",
    "growth-operations-xiaohongshu": "增长运营",
    "knowledge-and-pm-integrations": "知识库与项目协作",
    "multimodal-media": "多模态内容",
    "office-white-collar": "办公文档",
    "openclaw-memory-and-safety": "记忆与安全",
    "operations-general": "通用运营",
    "product-design": "产品设计",
    "security-and-reliability": "安全可靠性",
    "task-understanding-decomposition": "任务理解与拆解",
}

SPECIAL_DESCRIPTIONS = {
    "agent-hub": "用于管理 Agent 能力中心、技能发现、路由和协作工作流。",
    "arena": "用于构建和运行 Agent 竞技场、评测对战和能力比较流程。",
    "chatgpt-apps": "用于设计、构建和调试 ChatGPT Apps 与相关集成能力。",
    "develop-web-game": "用于开发网页游戏原型、玩法循环、交互逻辑和前端实现。",
    "figma": "用于处理 Figma 设计读取、解析、交付和实现协作。",
    "figma-implement-design": "用于将 Figma 设计转化为可实现的前端界面和组件。",
    "native-mcp": "用于构建和调试原生 MCP 集成、服务器和工具调用流程。",
    "openai-docs": "用于查阅和应用 OpenAI 官方文档、API 行为和集成指南。",
    "andrej-karpathy-skills": "用于应用 Andrej Karpathy 风格的 AI 学习、构建和研究实践。",
    "browser-testing-with-devtools": "用于通过浏览器 DevTools 测试、调试和验证前端行为。",
    "context-engineering": "用于设计上下文工程策略、提示输入结构和长任务信息流。",
    "deep-research": "用于执行深度研究、资料收集、来源核验和综合分析。",
    "dispatching-parallel-agents": "用于拆分任务并调度多个 Agent 并行协作。",
    "using-agent-skills": "用于选择、加载和正确使用 Agent Skills 完成任务。",
    "using-git-worktrees": "用于使用 Git worktree 隔离并行开发和审查工作。",
    "using-superpowers": "用于使用 Superpowers 工作流提升计划、执行和验证质量。",
    "cloudflare-deploy": "用于将应用部署到 Cloudflare 并处理相关发布流程。",
    "netlify-deploy": "用于将网站或应用部署到 Netlify 并获取预览或生产链接。",
    "render-deploy": "用于将服务或应用部署到 Render 并处理运行配置。",
    "nextjs-app-router": "用于 Next.js App Router 项目开发、路由设计和服务端渲染实践。",
    "neon-postgres": "用于 Neon Postgres 数据库连接、分支、迁移和运行维护。",
    "vercel-react-best-practices": "用于 Vercel/React 项目的架构、性能和部署最佳实践。",
    "vercel-react-view-transitions": "用于在 React/Vercel 项目中实现和优化 View Transitions。",
    "azure-kubernetes": "用于 Azure Kubernetes 集群管理、部署、排障和运维。",
    "github-ops": "用于 GitHub 运维、仓库管理、PR/Issue 流程和自动化协作。",
    "playwright": "用于使用 Playwright 编写、运行和调试端到端测试。",
    "playwright-pro": "用于高级 Playwright 测试、诊断、稳定性和浏览器自动化。",
    "financial-data-collector": "用于收集股票、财报、宏观和市场数据并生成分析输入。",
    "portfolio-risk-manager": "用于投资组合风险分析、仓位约束和风险报告生成。",
    "x-twitter-scraper": "用于抓取和分析 X/Twitter 公开内容、线程和增长信号。",
    "lark-base": "用于操作飞书 Base 数据表、记录、字段和自动化数据流程。",
    "lark-calendar": "用于查询、创建和管理飞书日历事件与日程安排。",
    "lark-doc": "用于读取、编辑和生成飞书云文档内容。",
    "lark-drive": "用于搜索、读取和管理飞书云空间文件与权限。",
    "lark-im": "用于发送、读取和处理飞书即时消息与群聊交互。",
    "lark-sheets": "用于读取、编辑和分析飞书电子表格数据。",
    "lark-task": "用于创建、查询和更新飞书任务及待办事项。",
    "linear": "用于管理 Linear issue、项目、状态流转和工程协作。",
    "notion-spec-to-implementation": "用于将 Notion 规格文档转化为可执行实现计划。",
    "imagegen": "用于生成、编辑和迭代图像内容与视觉素材。",
    "screenshot": "用于截图、屏幕捕获、视觉核查和界面证据收集。",
    "sora": "用于构思、生成和评审 Sora 视频或视频提示词。",
    "docx": "用于创建、编辑和检查 Word `.docx` 文档。",
    "excel-automation": "用于自动化 Excel 工作簿、公式、图表和数据处理。",
    "pptx": "用于创建、编辑和美化 PowerPoint 演示文稿。",
    "spreadsheet": "用于处理电子表格数据、公式、清洗和分析。",
    "honcho": "用于管理 Agent 记忆、运行状态、协作上下文和安全边界。",
    "input-guard": "用于输入安全检查、提示注入防护和高风险请求拦截。",
    "rag-architect": "用于设计 RAG 架构、检索策略、索引和评估流程。",
}

TOKEN_CN = {
    "agent": "Agent",
    "agents": "Agent",
    "ai": "AI",
    "api": "API",
    "app": "应用",
    "apps": "应用",
    "analytics": "分析",
    "analyzer": "分析",
    "analyst": "分析",
    "architect": "架构",
    "architecture": "架构",
    "audit": "审计",
    "auditor": "审计",
    "automation": "自动化",
    "aws": "AWS",
    "backtester": "回测",
    "bootstrap": "启动",
    "browser": "浏览器",
    "builder": "构建",
    "calendar": "日历",
    "campaign": "活动",
    "canvas": "画布",
    "capture": "捕获",
    "ci": "CI",
    "cd": "CD",
    "cli": "CLI",
    "cloudflare": "Cloudflare",
    "code": "代码",
    "codebase": "代码库",
    "collector": "采集",
    "coach": "教练",
    "comms": "沟通",
    "comps": "可比公司",
    "competitive": "竞品",
    "competitors": "竞品",
    "content": "内容",
    "contributor": "贡献",
    "creator": "创建",
    "data": "数据",
    "database": "数据库",
    "debugging": "调试",
    "debt": "技术债",
    "demo": "演示",
    "demand": "需求",
    "deploy": "部署",
    "deployment": "部署",
    "design": "设计",
    "designer": "设计",
    "devops": "DevOps",
    "doc": "文档",
    "docs": "文档",
    "drive": "云盘",
    "driven": "驱动",
    "engineering": "工程",
    "engineer": "工程",
    "error": "错误",
    "evaluation": "评估",
    "evaluator": "评估",
    "excel": "Excel",
    "fact": "事实",
    "filing": "申报文件",
    "finance": "金融",
    "financial": "金融",
    "fix": "修复",
    "frontend": "前端",
    "game": "游戏",
    "generator": "生成",
    "github": "GitHub",
    "git": "Git",
    "graphify": "Graphify",
    "growth": "增长",
    "guard": "防护",
    "hardening": "加固",
    "image": "图像",
    "inspection": "检查",
    "integration": "集成",
    "implementation": "实现",
    "investing": "投资",
    "investment": "投资",
    "issue": "Issue",
    "jupyter": "Jupyter",
    "knowledge": "知识",
    "kubernetes": "Kubernetes",
    "landing": "落地页",
    "link": "链接",
    "markdown": "Markdown",
    "marketing": "营销",
    "manager": "管理",
    "mcp": "MCP",
    "meeting": "会议",
    "media": "媒体",
    "memory": "记忆",
    "minutes": "纪要",
    "model": "模型",
    "monorepo": "Monorepo",
    "navigator": "导航",
    "notion": "Notion",
    "notebook": "Notebook",
    "observability": "可观测性",
    "office": "办公",
    "optimization": "优化",
    "owner": "负责人",
    "parallel": "并行",
    "performance": "性能",
    "pm": "项目管理",
    "pmm": "PMM",
    "pipeline": "流水线",
    "postgres": "Postgres",
    "ppt": "PPT",
    "pr": "PR",
    "product": "产品",
    "profiler": "性能分析",
    "prompt": "提示词",
    "qa": "质量保障",
    "quality": "质量",
    "rag": "RAG",
    "react": "React",
    "release": "发布",
    "research": "研究",
    "researcher": "研究",
    "review": "评审",
    "reviewer": "评审",
    "risk": "风险",
    "scanner": "扫描",
    "schema": "Schema",
    "search": "搜索",
    "security": "安全",
    "senior": "高级",
    "server": "服务器",
    "skill": "技能",
    "skills": "技能",
    "slack": "Slack",
    "social": "社交",
    "source": "来源",
    "speech": "语音",
    "sre": "SRE",
    "strategy": "策略",
    "strategies": "策略",
    "supabase": "Supabase",
    "suite": "套件",
    "system": "系统",
    "task": "任务",
    "test": "测试",
    "testing": "测试",
    "threat": "威胁",
    "toolkit": "工具包",
    "tracker": "跟踪",
    "troubleshooting": "排障",
    "transcript": "转录稿",
    "ui": "UI",
    "ux": "UX",
    "valuation": "估值",
    "vercel": "Vercel",
    "vulnerability": "漏洞",
    "workflow": "工作流",
    "workflows": "工作流",
    "xlsx": "XLSX",
}

STOPWORDS = {"a", "an", "and", "the", "of", "for", "to", "with"}
GENERATED_PREFIX_RE = re.compile(r'^zh_description: "用于.*场景下的.*相关任务。"$')


def parse_frontmatter(text: str) -> tuple[list[str], str] | None:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.DOTALL)
    if not match:
        return None
    return match.group(1).splitlines(), match.group(2)


def field_value(lines: list[str], key: str) -> str:
    prefix = key + ":"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix):].strip().strip("'").strip('"')
    return ""


def has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def concise_chinese_from_description(description: str) -> str | None:
    if not has_cjk(description):
        return None
    cleaned = re.sub(r"\s+", " ", description).strip()
    cleaned = re.split(r"[。.!?；;]", cleaned)[0].strip()
    if not cleaned:
        return None
    if len(cleaned) > 58:
        cleaned = cleaned[:58].rstrip("，、, ") + "。"
    elif not cleaned.endswith("。"):
        cleaned += "。"
    return cleaned


def translate_name(name: str) -> str:
    parts = [p for p in re.split(r"[-_]+", name.lower()) if p and p not in STOPWORDS]
    translated = [TOKEN_CN.get(part, part) for part in parts]
    # Collapse adjacent duplicate words while preserving order.
    out: list[str] = []
    for item in translated:
        if not out or out[-1] != item:
            out.append(item)
    return "、".join(out)


def category_template(category: str, translated_name: str) -> str:
    phrase = translated_name or "专业能力"
    templates = {
        "ai-agent-platform": f"用于{phrase}，支持 Agent 平台编排、集成和运行管理。",
        "ai-workflow": f"用于{phrase}，支持任务规划、执行、评审和验证。",
        "deployment-platforms": f"用于{phrase}，支持部署发布、配置、预览和故障处理。",
        "developer-engineering": f"用于{phrase}，支持开发、调试、评审和交付。",
        "devops-sre": f"用于{phrase}，支持部署、监控、排障和发布管理。",
        "engineering-workflow-automation": f"用于{phrase}，支持工程协作、自动化验证和交付闭环。",
        "finance-investing": f"用于{phrase}，支持投资研究、风险评估和报告生成。",
        "growth-operations-xiaohongshu": f"用于{phrase}，支持内容、营销、渠道和数据分析。",
        "knowledge-and-pm-integrations": f"用于{phrase}，支持知识管理、项目同步和平台集成。",
        "multimodal-media": f"用于{phrase}，支持内容生成、编辑、分析和交付。",
        "office-white-collar": f"用于{phrase}，支持文档、表格、演示和资料整理。",
        "openclaw-memory-and-safety": f"用于{phrase}，支持记忆管理、安全防护和运行治理。",
        "operations-general": f"用于{phrase}，支持信息整理、沟通和执行管理。",
        "product-design": f"用于{phrase}，支持产品研究、策略、界面和交付协作。",
        "security-and-reliability": f"用于{phrase}，支持安全扫描、审计、加固和风险治理。",
        "task-understanding-decomposition": f"用于{phrase}，支持检索、拆解、反思和决策。",
    }
    return templates.get(category, f"用于{phrase}，支持专业流程规划、执行和验证。")


def generated_description(name: str, category: str, description: str) -> str:
    if name in SPECIAL_DESCRIPTIONS:
        return SPECIAL_DESCRIPTIONS[name]
    from_chinese = concise_chinese_from_description(description)
    if from_chinese:
        return from_chinese

    translated_name = translate_name(name)
    return category_template(category, translated_name)


def add_zh_description(skill_file: Path, dry_run: bool) -> bool:
    text = skill_file.read_text(encoding="utf-8")
    parsed = parse_frontmatter(text)
    if parsed is None:
        return False
    lines, body = parsed
    if any(line.startswith("zh_description:") for line in lines):
        return False

    name = field_value(lines, "name") or skill_file.parent.name
    description = field_value(lines, "description")
    category = skill_file.parent.parent.name
    zh = generated_description(name, category, description)
    insert_at = 0
    for idx, line in enumerate(lines):
        if line.startswith("description:"):
            insert_at = idx + 1
            break
    lines.insert(insert_at, f'zh_description: "{zh}"')
    new_text = "---\n" + "\n".join(lines) + "\n---\n" + body
    if not dry_run:
        skill_file.write_text(new_text, encoding="utf-8")
    return True


def refresh_generated_zh_description(skill_file: Path, dry_run: bool) -> bool:
    text = skill_file.read_text(encoding="utf-8")
    parsed = parse_frontmatter(text)
    if parsed is None:
        return False
    lines, body = parsed
    name = field_value(lines, "name") or skill_file.parent.name
    description = field_value(lines, "description")
    category = skill_file.parent.parent.name
    zh = generated_description(name, category, description)

    changed = False
    new_lines: list[str] = []
    for line in lines:
        if GENERATED_PREFIX_RE.match(line):
            new_lines.append(f'zh_description: "{zh}"')
            changed = True
        else:
            new_lines.append(line)
    if changed and not dry_run:
        skill_file.write_text("---\n" + "\n".join(new_lines) + "\n---\n" + body, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill missing zh_description fields.")
    parser.add_argument("--skills-dir", type=Path, default=REPO_ROOT / "skills")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--refresh-generated",
        action="store_true",
        help="Refresh older generated zh_description template values.",
    )
    args = parser.parse_args()

    changed: list[Path] = []
    for skill_file in sorted(args.skills_dir.glob("*/*/SKILL.md")):
        if args.refresh_generated:
            updated = refresh_generated_zh_description(skill_file, args.dry_run)
        else:
            updated = add_zh_description(skill_file, args.dry_run)
        if updated:
            changed.append(skill_file)

    action = "Would update" if args.dry_run else "Updated"
    print(f"{action} {len(changed)} skills")
    for path in changed:
        print(path.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
