---
name: skill-vetter
description: '在安装前审计技能安全性，识别恶意指令、越权行为与高风险配置。'
version: "1.0.0"
author: "seaworld008"
source: "in-house"
source_url: ""
tags: '["security", "skill", "vetter"]'
created_at: "2026-03-15"
updated_at: "2026-03-20"
quality: 2
complexity: "intermediate"
---

# Skill Vetter

建议在安装任何社区技能或未经验证的第三方工具前，优先执行本技能进行安全前置审计。Skill Vetter 是确保 Agent 运行环境纯净、防止敏感数据外泄的首道防线。它通过静态代码分析、权限拓扑扫描及恶意模式匹配，为用户提供一份详尽的“安全体检报告”。

## 安装

```bash
npx clawhub@latest install skill-vetter
```

## 核心能力

- **检测潜在恶意/可疑指令**：识别 `rm -rf /`, `curl | bash`, `eval(base64_decode(...))` 等典型的后门或破坏性代码模式。
- **识别高风险权限与外部依赖**：透视技能所需的 OAuth Scope (如 Gmail 全读写权限)、文件系统访问范围及第三方 API 请求域名。
- **输出风险等级与处置建议**：根据发现的问题自动判定为 `Critical`, `High`, `Medium`, `Low` 四个等级，并给出相应的“沙盒运行”或“拒绝安装”建议。

## 触发条件 / When to Use

- **首次安装新技能**：特别是从 GitHub、Gitee 或其他非官方验证渠道获取的技能。
- **技能版本升级**：在执行 `clawhub update` 后，检查新版本是否悄悄增加了一些敏感权限或更改了核心逻辑。
- **可疑行为追溯**：当 Agent 在执行某个任务过程中出现异常报错或试图访问无关目录时，使用 `skill-vetter` 对该技能进行二次复核。
- **合规性审查**：在企业环境下，确保所有安装的 Agent 技能符合内部数据安全策略。
- **安全演练/红蓝对抗**：作为防御方，模拟识别和拦截具有攻击性的恶意技能。

## 核心能力 / Core Capabilities

### 1. 静态代码嗅探 (Static Analysis)
- **操作步骤**：
  1. 解压待审查技能的源码包。
  2. 使用正则表达式和 AST (抽象语法树) 扫描 `SKILL.md`, `index.js`, `package.json` 等关键文件。
  3. 检索敏感 API 调用（如 `process.env`, `fs.writeFileSync`）。
- **最佳实践**：不仅要检查明文代码，还要通过 `skill-vetter` 识别经过简单混淆（Obfuscation）的代码块。

### 2. 权限地图扫描 (Permission Mapping)
- **操作步骤**：
  1. 提取技能声明的 `manifest.json` 或 frontmatter 中的权限列表。
  2. 交叉对比系统白名单。
  3. 如果技能请求了不相称的高级权限（如“天气查询技能”请求“读取浏览器 Cookies”），标记为 `Red Flag`。
- **最佳实践**：优先推荐具有 `Least Privilege` (最小权限原则) 的技能。

### 3. 外部网络连接审计 (Egress Audit)
- **操作步骤**：
  1. 识别代码中硬编码的 URL 或 IP 地址。
  2. 匹配已知的恶意域名黑名单。
  3. 报告是否存在通过 DNS Tunneling 或其他手段窃取数据的风险。
- **最佳实践**：对于闭源（Binary）或加密的技能，建议在隔离环境（Sandbox）中通过流量监控来进行审计。

### 4. 依赖链安全分析 (Dependency Chain Check)
- **操作步骤**：
  1. 深度遍历 `node_modules` 或相关依赖树。
  2. 结合 `Snyk` 或 `GitHub Advisory` 数据库检查已知 CVE 漏洞。

## 常用命令/模板 / Common Patterns

### 安全审计报告模板 (Vetting Report Template)
```markdown
### 技能基本信息
- **名称**: [target-skill-name]
- **版本**: [version]
- **作者**: [developer-handle]
- **来源**: [url/source]

### 综合风险评分: [B+ (Medium Risk)]

### 风险项详情
1. **网络通信 (Network)**: 发现连接到 `api.unknown-cloud.xyz`。
   - *影响*: 可能泄露用户会话 Token。
   - *建议*: 配置防火墙策略，拦截该域名。
2. **敏感权限 (Privilege)**: 请求了 `root_directory_access`。
   - *影响*: 该技能具备全盘删除能力。
   - *建议*: 修改权限配置文件，仅限制在 `/tmp/agent-workdir`。

### 最终结论 (Decision Support)
> [✓] 安全安装
> [!] 风险提示（需沙盒运行）
> [X] 拦截安装
```

### 快速扫描命令示例
```bash
# 扫描本地下载的技能包
skill-vetter scan --path ./downloaded-skill --format json --output report.json
```

## 进阶应用场景 / Advanced Use Cases

### 1. 自动化 CI/CD 安全门禁
- 在 Agent 平台的开发流水线中，集成 `skill-vetter`。只有通过 A+ 级安全审计的技能才允许合并进 `main` 分支或上架到企业私有仓库。

### 2. 动态行为隔离 (Dynamic Sandboxing)
- 结合 `skill-vetter` 的初步判断，为高风险技能自动生成 `docker-compose.yml` 配置文件，将其运行在完全隔离的容器环境中。

## 边界与限制 / Boundaries

- **误报风险 (False Positives)**：合法的管理工具（如 `backup-skill`）也会使用高敏感 API，可能被标记为高风险。
- **无法完全覆盖动态运行**：静态分析难以捕捉到在运行时动态下载并执行的代码（Remote Code Execution）。
- **性能开销**：对包含数万个小文件的复杂技能进行深度 AST 扫描可能需要数分钟时间。
- **零日漏洞识别局限**：对于此前从未出现过的全新恶意模式，本技能可能存在盲点。
- **闭源技能审计深度**：如果不具备二进制反汇编能力，对编译后的 `.exe` 或 `.so` 文件的审计深度有限。

## 最佳实践总结

1. **先审后用**：将 `skill-vetter` 设为全局钩子，在 `install` 命令执行前自动触发。
2. **信任等级划分**：为不同来源设置信任分。官方 > 认证作者 > 社区贡献 > 匿名源码。
3. **定期全量复核**：每月对已安装的所有技能进行一次“大体检”。
4. **人工审计辅助**：对于 `Critical` 级别的报警，Agent 必须强制暂停并提示由具有安全背景的人员进行人工复核。
5. **最小化 Scope**：如果一个技能只需读取文件，就不要给它写入权限。
