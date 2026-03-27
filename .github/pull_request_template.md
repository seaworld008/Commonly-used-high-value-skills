## 提交类型 / Change Type

- [ ] 新增技能 (New Skill)
- [ ] 更新技能 (Skill Update)
- [ ] 修复问题 (Bug Fix)
- [ ] 文档改进 (Documentation)
- [ ] 脚本/CI 改进 (Tooling)

## 变更说明 / Description

<!-- 简要描述你的变更 -->

## 技能来源 / Skill Source

- [ ] 原创 (in-house)
- [ ] 改编自 / Adapted from: <!-- 注明原始来源 URL 和 License -->

## 检查清单 / Checklist

- [ ] 我已阅读 [CONTRIBUTING.md](./CONTRIBUTING.md)
- [ ] SKILL.md 包含完整的 frontmatter (`name`, `description`, `version`, `tags`)
- [ ] SKILL.md 内容 ≥ 80 行，包含触发条件和核心能力等 Section
- [ ] 已运行 `python scripts/refresh_repo_views.py` 并提交生成文件
- [ ] 已运行 `python scripts/lint_skill_quality.py` 无 FAIL
- [ ] 所有测试通过：`python -m unittest discover tests -v`
