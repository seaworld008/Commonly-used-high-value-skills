# 更新日志自动化

周更只维护 `CHANGELOG.md` 中 `## [Unreleased]` 下的
`AUTO-CHANGELOG:START` / `AUTO-CHANGELOG:END` 区块。
人工整理的双语说明、历史版本、链接和退役记录不属于自动化写入范围。

## 生成与验收

```bash
python scripts/generate_changelog.py --since last-tag --preserve-history --dry-run
python scripts/generate_changelog.py --since last-tag --preserve-history
python -m pytest -q tests/test_generate_changelog.py
git diff --check
```

- 默认从最近的可达 tag 开始，使用排他的提交范围；手动运行也可指定 ref 或日期。
- 重复生成应无变化；仅修改 `CHANGELOG.md` 的提交不会产生下一轮自动更新。
- 缺失文件、缺失或重复 Unreleased、错位或重复区块标记均拒绝写入。
- Git 查询失败必须非零退出，不得以“没有更新”掩盖错误。
- 发布时可将人工审核后的内容移入新版本章节，但必须删除旧的自动区块标记；
  这些标记只能在 Unreleased 内出现一次。
- 不带 `--preserve-history` 是独立发布说明生成模式，会替换输出文件；
  不得用于周更覆盖已维护的 `CHANGELOG.md`。

## GitHub 权限与合并

仓库允许 Actions 创建和批准 PR，但默认 `GITHUB_TOKEN` 权限保持 `read`。
只有 Changelog 工作流显式申请 `contents: write` 和 `pull-requests: write`；
开启仓库权限不代表授权机器人自动批准或合并自身 PR。

使用 `GITHUB_TOKEN` 创建的 PR 可能没有触发其他 PR 工作流。维护者必须确认
当前 head 的 Repository Validation、provenance 和 CodeQL 检查实际运行并成功；
无检查不等于通过。必要时由已认证维护者关闭再重新打开 PR，触发正常的
`pull_request: reopened` 验证。不得使用管理员绕过检查。

合并前还要核对人工历史没有删除、工作区干净、PR 可合并；合并后更新 main，
检查准确合并提交上的远程结果。
