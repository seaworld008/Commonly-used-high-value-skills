# v3.3.0 来源、取舍与完整资源审计（2026-10-12）

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
