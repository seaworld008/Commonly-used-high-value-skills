# Auto-Continue Best Practices

## Goal

把 Hermes + graphify + GSD 的仓库级自动续跑能力做成：
- 默认继续，不默认停止
- 轻触发、重执行分离
- 有锁、防重入、可恢复
- 只在项目级完成且全量验证通过时停机

## Recommended Architecture

### 1. Event trigger + periodic reconciliation
推荐组合：
- `post-commit`：代码提交后轻量触发
- `post-merge`：同步/合并后轻量触发
- `cron` 或 systemd timer：每 15 分钟巡检一次

职责分工：
- hook：只触发，不做长任务
- timer：兜底巡检、恢复、补触发
- runner：真正执行 Hermes 自动开发

## 2. Single runner + lock
同一仓库同一时间只跑一个自动开发进程。

推荐：
- `flock -n` 或等价锁
- 锁文件放在 `.planning/` 或 `var/` 下
- timer 检测 stale lock / crashed runner 后可恢复

## 3. Completion sentinel
不要通过下面这些条件直接停机：
- 一个小 task 完成
- 某个 phase checklist 局部清空
- 某轮 focused tests 通过
- 某个 helper seam 抽完

推荐只认一个项目级 completion sentinel，例如：
- `.planning/auto-continue-complete.json`

## 4. Evidence-before-completion
completion sentinel 只能由 dedicated completion gate 脚本写入。

这个脚本应该：
1. 跑项目定义的 full verification command
2. 确认工作树干净
3. 记录 HEAD / branch / timestamps
4. 写 evidence doc
5. 最后写 completion sentinel

推荐 evidence doc：
- `docs/auto-continue-completion-evidence.md`

### E2E lesson: temp verification logs must stay outside the repo
真实测试发现，如果 completion gate 把临时验证日志写进仓库内（例如 `.planning/`），它会把自己的工作树弄脏，导致永远无法通过 clean-worktree gate。

推荐做法：
- 临时验证日志写到 `/tmp/...` 或其它仓库外临时目录
- evidence doc 只在最终成功时写回仓库

### E2E lesson: status must ignore runtime artifacts
真实测试还发现，`status.sh` 不能把下面这些运行时/完成态产物当成“项目代码脏状态”：
- completion sentinel
- completion evidence doc
- `.planning/logs/`
- `.planning/checkpoints/`
- lock 文件（如 `.planning/.hermes-auto-continue.lock`）

否则会出现：completion gate 成功写出 sentinel 后，status 又把它自己判成 dirty worktree，永远到不了 `COMPLETE`。

### 实战补充：临时验证日志不要写在仓库内
真实测试里发现，如果 completion gate 把临时验证日志写进仓库内（例如 `.planning/`），它会把自己产生的中间文件误判成 dirty worktree，导致永远无法通过 clean-worktree gate。

推荐做法：
- 临时验证日志写到 `/tmp/...` 或其他仓库外临时目录
- 最终需要长期保存的内容，再复制/渲染到 evidence doc 中
- completion gate 本身不要把“临时文件”写进仓库工作树

## 5. Recommended stop rule
推荐停止规则：
- sentinel 存在
- sentinel.status == `complete`
- sentinel.head == 当前 HEAD
- 工作树干净

否则一律视为 `INCOMPLETE`

### 实战补充：status 需要忽略运行时产物
真实测试里还发现，如果 `status.sh` 直接拿 `git status --porcelain` 做脏工作树判断，而不过滤运行时产物，它会把下面这些文件/目录误判为“项目代码还没完成”：
- completion sentinel 本身
- completion evidence doc
- 自动续跑日志目录
- checkpoint 目录
- runner lock 文件

推荐做法：
- 在 status gate 中对白名单路径做过滤
- 只让**真正的源码/文档改动**影响 dirty worktree 判断
- 运行时产物与完成态产物不应阻止 `COMPLETE`

## 6. Queue semantics
如果你需要 queue，不要无界堆积。

推荐语义：
- one running
- one pending

后来的 pending 可以覆盖旧 pending，因为真正需要的是“继续推进最新仓库状态”，不是重放历史每一个 commit。

## 7. Prompt contract
runner 给 Hermes 的 prompt 里应明确写清：
- 继续当前仓库主线工作
- 默认继续，不默认停止
- 不能因为小 task 完成而停
- 只有在项目全部完成时才允许执行 completion gate
- 完成每轮后继续同步 planning/docs/graphify

## 8. Verification strategy
普通轮次：
- 跑 focused tests
- 不要谎称全仓通过

最终完成轮次：
- 跑 full verification command
- 成功后写 sentinel 和 evidence

## 9. Good repo-local files
- `scripts/hermes-auto-continue-config.sh`
- `scripts/hermes-auto-continue-status.sh`
- `scripts/hermes-auto-continue-trigger.sh`
- `scripts/hermes-auto-continue-checkpoint.sh`
- `scripts/hermes-auto-continue-mark-complete.sh`
- `scripts/install-hermes-auto-continue-cron.sh`
- `.husky/post-commit`
- `.husky/post-merge`
- `docs/auto-continue-workflow.md`

## 10. Anti-patterns
- 在 hook 里直接运行长时间 agent 会话
- 没有锁，导致 cron 和 hook 同时触发多个 agent
- 只靠某个 roadmap 勾选状态判定已完成
- 没有 evidence doc 就写 done sentinel
- 自动化写出 sentinel 后，新的提交却不让 sentinel 失效

## Bottom line

最稳的模式不是“做完一点就停”，而是：

**hook 轻触发 + timer 兜底 + runner 串行推进 + completion gate 严格停机**
