---
name: competitors-analysis
description: Compare competitor repositories using verified code and source evidence when technical competitive analysis or repository profiling is requested.
zh_description: "用于基于已核实的代码和来源证据对比竞品代码仓库，开展技术竞品分析或仓库画像。"
version: "1.0.3"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["analysis", "competitors", "growth", "marketing"]'
created_at: "2026-03-04"
updated_at: "2026-11-17"
quality: 5
complexity: "intermediate"
context: fork
agent: general-purpose
argument-hint: '[product-name] [competitor-url]'
---

# Competitors Analysis

Evidence-based competitor tracking and analysis. **All analysis must be based on actual code, never assumptions.**

## When to Use

Use this skill when the user wants to:

- analyze a competitor repository with evidence
- create or update a competitor profile
- compare a competing product's technical stack or architecture
- track competitor changes over time using cloned code

## Usage

Recommended flow:

```text
use the provided checkout (clone only if needed and authorized)
-> inspect source files and metadata
-> cite every factual claim
-> write profile from evidence only
-> run post-analysis verification
```

## CRITICAL: Evidence-Based Analysis Only

**在开始分析之前，必须完成以下检查：**

### Pre-Analysis Checklist

- [ ] 优先使用已提供的可读 checkout；记录路径和 `git rev-parse HEAD`
- [ ] 可以 `ls` 查看目录结构
- [ ] 可以 `cat package.json` (或等效配置文件) 读取版本信息
- [ ] 可以 `git log -1` 标明分析版本；未经远端核对不声称最新

**缺少支撑某项断言的源码时，将该项标为未核实；先检查已有 checkout，只有确需获取且在授权范围内时才克隆。**

### Forbidden Patterns (禁止的表述)

| 禁止 | 原因 |
|------|------|
| "推测..."、"可能..."、"应该..." | 没有证据支持 |
| "架构图（推测版）" | 必须基于实际代码 |
| "未公开"、"未披露" | 如果不知道就不要写 |
| 不带来源的技术细节 | 无法验证 |

### Required Patterns (必须的表述)

| 正确格式 | 示例 |
|----------|------|
| 技术细节 + (来源: 文件:行号) | "使用 better-sqlite3 (来源: package.json:88)" |
| 直接引用 + 来源 | `> "description text" (README.md:3)` |
| 版本号 + 来源 | "版本 1.3.3 (package.json:2)" |

---

## Analysis Workflow

### Step 1: 定位源码与分析版本

```bash
# 仅在缺少 checkout 且已授权获取源码时，使用任务工作目录与可用访问方式
git clone https://github.com/org/repo.git <authorized-workdir>/repo
```

已有 checkout 可直接只读分析；不要求家目录、SSH 或网络更新。记录 commit 和未核实的时效性。

### Step 2: Gather Facts (收集事实)

按顺序读取以下文件，记录关键信息：

**2.1 项目元数据**
```bash
# Node.js 项目
cat package.json | head -20      # name, version, description
cat package.json | grep -A50 dependencies

# Python 项目
cat pyproject.toml               # 或 setup.py, requirements.txt

# Rust 项目
cat Cargo.toml
```

**2.2 项目结构**
```bash
ls -la                           # 根目录结构
ls src/                          # 源码目录
find . -name "*.md" -maxdepth 2  # 文档文件
```

**2.3 核心模块**
```bash
# 找到入口文件
cat main.js | head -50           # 或 index.js, app.py, main.rs
# 找到核心 helpers/utils
ls src/helpers/ 2>/dev/null || ls src/utils/ 2>/dev/null
```

**2.4 README 和文档**
```bash
cat README.md | head -100        # 官方描述
cat CHANGELOG.md | head -50      # 版本历史
```

### Step 3: Deep Dive (深入分析)

针对关键技术点，读取具体实现文件：

```bash
# 示例：分析 ASR 实现
cat src/helpers/whisper.js       # 读取完整文件
grep -n "class.*Manager" src/helpers/*.js  # 找到核心类
```

**记录格式**:
```
| 文件 | 行号 | 发现 |
|------|------|------|
| whisper.js | 33-35 | 使用 WhisperServerManager |
```

### Step 4: Write Profile (撰写分析)

使用 [references/profile_template.md](references/profile_template.md) 模板，确保每个技术细节都有来源标注。

### Step 5: Post-Analysis Verification (分析后验证)

**自检清单**:

- [ ] 所有版本号都有来源标注？
- [ ] 所有技术栈都来自 package.json/Cargo.toml？
- [ ] 架构描述基于实际代码结构？
- [ ] 没有"推测"、"可能"等词汇？
- [ ] 对比表中的竞品数据都有来源？

---

## Directory Structure

```
<authorized-workdir>/competitors/
├── flowzero/              # Flowzero 的竞品
│   ├── openwhispr/        # git clone 的仓库
│   └── ...
└── {product-name}/        # 其他产品

{project}/docs/competitors/
├── README.md              # 索引（标注分析状态）
├── profiles/
│   └── {competitor}.md    # 基于代码的分析
├── landscape/
├── insights/
└── updates/2026/
```

---

## Templates and Checklists

| 文档 | 用途 |
|------|------|
| [references/profile_template.md](references/profile_template.md) | 竞品分析报告模板 |
| [references/analysis_checklist.md](references/analysis_checklist.md) | 分析前/中/后检查清单 |

**关键要求**:
1. 顶部必须标注数据来源路径和 commit hash
2. 每个技术细节必须有 (来源: 文件:行号)
3. 引用 README 内容必须标注行号
4. 无法验证的标记为"待验证"并说明原因
5. 分析完成后运行检查清单中的验证命令

---

## Tech Stack Analysis Guide

### Node.js / JavaScript

| 信息 | 来源文件 | 关键字段 |
|------|----------|----------|
| 版本 | package.json | `version` |
| 依赖 | package.json | `dependencies`, `devDependencies` |
| 入口 | package.json | `main`, `scripts.start` |
| 框架 | package.json | electron, react, vite 等 |

### Python

| 信息 | 来源文件 | 关键字段 |
|------|----------|----------|
| 版本 | pyproject.toml | `[project].version` |
| 依赖 | pyproject.toml / requirements.txt | `dependencies` |
| 入口 | pyproject.toml | `[project.scripts]` |

### Rust

| 信息 | 来源文件 | 关键字段 |
|------|----------|----------|
| 版本 | Cargo.toml | `[package].version` |
| 依赖 | Cargo.toml | `[dependencies]` |

---

## Common Mistakes to Avoid

### 1. 缺少源码证据便作断言

❌ 错误: 从 GitHub 网页或 WebFetch 获取信息后直接写分析
✅ 正确: 使用已提供的 checkout 与宿主可用的文件读取能力逐项核对；只有缺少源码且获取已授权时才克隆。

### 2. 混合事实和推测

❌ 错误:
```markdown
## 技术栈
- Electron (推测基于桌面应用特征)
- 可能使用了 React
```

✅ 正确:
```markdown
## 技术栈 (来源: package.json)
| 依赖 | 版本 | 来源 |
|------|------|------|
| electron | 36.9.5 | package.json:68 |
| react | 19.1.0 | package.json:96 |
```

### 3. 使用过时信息

❌ 错误: 分析时不检查 git log，使用过时的代码
✅ 正确: 分析前运行 `git pull`，记录分析时的 commit hash

### 4. 对比表中竞品数据无来源

❌ 错误:
```markdown
| 维度 | 竞品 | 我们 |
|------|------|------|
| 支持语言 | 25种 | 58种 |
```

✅ 正确:
```markdown
| 维度 | 竞品 | 来源 | 我们 |
|------|------|------|------|
| 支持语言 | 25种 | modelRegistryData.json:9-35 | 58种 (FunASR 官方文档) |
```

---

## Scripts

See [scripts/update-competitors.sh](scripts/update-competitors.sh) for a repository-management template. Its product name is a placeholder and repository mapping is empty: copy it into an authorized workspace and configure both before use. Set `COMPETITORS_BASE` to the authorized directory instead of using its home-directory default. `pull` changes checkouts and is inappropriate for a read-only task.

```bash
./scripts/update-competitors.sh clone   # 克隆所有竞品
./scripts/update-competitors.sh pull    # 更新所有竞品
./scripts/update-competitors.sh status  # 检查状态
```
