#!/usr/bin/env python3
"""Complete v3.3.0 release metadata, generated views and repository checks."""
from __future__ import annotations
import json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"package.json"
data=json.loads(p.read_text())
if data["version"]!="3.2.1":raise ValueError("Unexpected existing version")
data["version"]="3.3.0"
for path in ("docs/releases/v3.3.0.json","docs/releases/v3.3.0.md",
             "docs/maintenance-audit-2026-10-12-v3.3.md","docs/sources/curated-v3.3.0.skills.json"):
    if path not in data["files"]:data["files"].append(path)
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
manifest={
  "tag":"v3.3.0","package_version":"3.3.0","title":"v3.3.0 · 高价值 Skills 精选增强",
  "prerelease":False,"generate_notes":False,"changelog_range":"v3.2.1..v3.3.0",
  "canonical_skills":294,
  "highlights":[
    "Add seven curated skills with all selected runtime assets and source artifacts at immutable commits",
    "Upgrade existing Agent Browser to the official CLI workflow without duplicating its public route",
    "Go performance/benchmark/observability, architecture review, HTML visualization, Live Panel and Azure Diagnostics",
    "Retain 287 existing canonical routes and generate 294 compatible OpenClaw skills"],
  "release_gates":[
    "All required CI workflows succeed on exact merged main",
    "Complete repository and package tests pass; generated views are deterministic",
    "Independent release asset download, SHA256 check, npm version and canonical counts pass"],
  "validation_boundaries":{
    "upstream":"Reviewed fixed upstream commit references, not a blanket claim of live current versions.",
    "runtime":"Static and isolated checks only; no real browser session, live Azure API or production validation.",
    "compatibility":"Seven additive public skills, one existing skill refreshed; no paths removed."
  },
  "breaking_changes":[],
  "audit":"docs/maintenance-audit-2026-10-12-v3.3.md"
}
(ROOT/"docs/releases/v3.3.0.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
notes="""# v3.3.0 · 高价值技能精选增强

本版本由 v3.2.1 升级而来：新增 7 个独立技能、更新原有 Agent Browser 1 个，合计 **294 个规范 Skills / 16 分类**。

## 精选收录
- Go: golang-performance、golang-benchmark、golang-observability，涵盖 pprof、benchstat、GC、OTel、Prometheus 与告警。
- improve-codebase-architecture：补齐 codebase-design、deepening 等依赖性资料，不再强制调用缺失的外部 Skill 工具。
- answer-me-with-html：保留 800KB 左右的 CLI 与所需参考，但收窄为用户明确要求 HTML 时才启动。
- live-panel：收录动画模板、完整 Python 渲染脚本、JSON 配置样例与运动设计文档；不包含非运行时的演示 MP4 和截图。
- azure-diagnostics：收录 AKS、App Service、VM、Functions、Messaging 的完整排障资料与诊断脚本，默认不自动执行。
- agent-browser：保持原有技能名，升级为 Vercel 官方 CLI 参考与授权感知流程。

## 可追溯性与安全
每个适配都有固定上游 Commit、来源、许可检查点、受管文件 SHA256 和本地修改边界；Go、HTML、Live Panel、Azure、架构均为 MIT，Agent Browser 为 Apache-2.0。不自动安装 CLI、访问云服务、操作真实浏览器、覆盖用户全局配置或声称静态测试等同生产实测。

[完整审计说明](../maintenance-audit-2026-10-12-v3.3.md)。

## 发布验证
精确合并 main SHA 的 Repository Validation、skills-provenance-ci、CodeQL 通过后，Verified Release 构建 npm/source 归档与 SHA256 清单，草稿下载独立核验文件内容、版本、294 个公开技能，再公开 Latest。
"""
(ROOT/"docs/releases/v3.3.0.md").write_text(notes)
audit="""# v3.3.0 来源、取舍与完整资源审计（2026-10-12）

基线 v3.2.1: 287 个规范入口，新增 7 个，升级 agent-browser 1 个，预计总计 294，继续保留 16 分类。

## 来源与固定提交

| 源 | 固定提交 | 许可证 | 新增/更新 |
| --- | --- | --- | --- |
| samber/cc-skills-golang | 8e899e20ff0cd4dc524af3993e4c62d8ee8c5717 | MIT | 三个 Go 技能 |
| mattpocock/skills | 49dd158d1076134a641b33efb035946536778336 | MIT | 架构审查 |
| QingYunA/answer-me-with-html | 5d5b86ddbeea500b7fec6b3e80ad273ad875b005 | MIT | HTML 解释 |
| ythx-101/live-panel-skill | 2a5dc1ea9983c193f20c9ff4000c8a11efb3b5e1 | MIT | 动态架构面板 |
| microsoft/azure-skills | 0727d81638d64b6888f796287ee00baecfb08ced | MIT | Azure 故障诊断 |
| vercel-labs/agent-browser | d9570915f4dd6504dee4070379d2c4f79d81dbb2 | Apache-2.0 | 升级已有入口 |

## 取舍与风险

- Go：完整收录方法正文、references 和附带的可执行告警资源；不把上游 evals 超大测试数据伪装成运行时依赖。
- 架构：打包 codebase-design、Deepening 和 HTML 报告模板，修复对宿主不可用 Skill Tool 的强制依赖。
- HTML：收录独立打包 CLI、settings/video 参考；静态语法验证，不自启动、不擅自发内容到第三方 API。
- Live Panel：保留 assets/template.html、scripts 和 example config；示例视频/PNG 体积较大且与运行无关，不进入最终安装包。
- Azure：全部本地脚本、troubleshooting 和 references 受管；真实 Azure RBAC、API、Inspektor Gadget 等需单独授权。
- Browser：继续沿用原 agent-browser 名称，不复制另一份入口；新文档与模板来自固定版本。
- 上游原始指令不能提升权限；安装/授权/云端操作由用户和宿主决定。
- 不声称 GitHub 当日每个上游所有可选分支均最新，也不把 CI 静态测试称作线上操作验证。

## 门禁
规范源 294/294 来源覆盖、完整 YAML/质量/授权来源审计、OpenClaw 294 入口、可执行脚本语法、npm 包文件与 MIT/Apache 许可、Node/Windows 安装器测试、源码/安装包 SHA256 下载核验。
"""
(ROOT/"docs/maintenance-audit-2026-10-12-v3.3.md").write_text(audit)
ch=ROOT/"CHANGELOG.md"
text=ch.read_text()
left=text.index("## [Unreleased]");right=text.index("## [3.2.1]")
new="""## [Unreleased]

<!-- AUTO-CHANGELOG:START -->
### 自动更新 / Automated updates

变更范围 / Revision range: v3.3.0..HEAD.

此范围内暂无可归类的变更。 / No categorized changes in this range.
<!-- AUTO-CHANGELOG:END -->

## [3.3.0] - 2026-10-12

### Added / 新增
- golang-performance / golang-benchmark / golang-observability。
- improve-codebase-architecture、answer-me-with-html、live-panel、azure-diagnostics。

### Changed / 更新
- agent-browser 基于官方 CLI 与固定许可证资料升级，但保留现有唯一公共路径。
- 增量引入完整被选中运行资源、许可证副本、SHA256 来源映射及按需权限规则。

### Validation / 验证
- 16 类、294 个规范入口；运行门禁与 Github Release 制品 SHA256 完整性核对。

"""
ch.write_text(text[:left]+new+text[right:])
for path,marker,content in (
 ("README.md","## 为什么值得收藏","## v3.3.0 精选增强\n\nGo 三件套、架构重构、HTML 可视化、动态架构面板和 Azure 诊断；升级已有 Agent Browser，完整固定上游来源并遵守授权边界。\n\n"),
 ("README.en.md","## v3.2.0:","## v3.3.0 Curated Engineering Enhancements\n\nGo profiling, benchmarking and observability; architecture deepening, HTML reports, animated topology panels and Azure diagnostics, plus an official CLI upgrade to the existing Agent Browser. Pinned provenance and permission-aware guidance included.\n\n")
):
    p=ROOT/path;old=p.read_text()
    if marker not in old:raise ValueError("Missing README anchor: "+path)
    p.write_text(old.replace(marker,content+marker,1))
# Verify references and executable file syntax without running imported third-party scripts.
import ast
for f in (ROOT/"skills/multimodal-media/live-panel/scripts").glob("*.py"):
    ast.parse(f.read_text(encoding="utf-8"),filename=str(f))
node=ROOT/"skills/office-white-collar/answer-me-with-html/scripts/am.mjs"
subprocess.run(["node","--check",str(node)],check=True,cwd=ROOT)
print("Runtime scripts parse correctly",flush=True)
subprocess.run([sys.executable,"scripts/enrich_frontmatter.py"],cwd=ROOT,check=True)
subprocess.run([sys.executable,"scripts/refresh_repo_views.py"],cwd=ROOT,check=True)
subprocess.run([sys.executable,"scripts/migrate_provenance_v2.py","--mapping","docs/sources/curated-v3.3.0.skills.json","--write","--refresh-managed-digests"],cwd=ROOT,check=True)
import hashlib
for item in json.loads((ROOT/"docs/sources/curated-v3.3.0.skills.json").read_text())["skills"]:
    rec=item["managed_files"][0]
    print("DIGEST",item["normalized_slug"],rec["sha256"]==hashlib.sha256((ROOT/rec["path"]).read_bytes()).hexdigest(),flush=True)
subprocess.run([sys.executable,"scripts/validate_repository.py","--refresh"],cwd=ROOT,check=True)
print("PASS v3.3.0 full pipeline, 294 canonical",flush=True)
