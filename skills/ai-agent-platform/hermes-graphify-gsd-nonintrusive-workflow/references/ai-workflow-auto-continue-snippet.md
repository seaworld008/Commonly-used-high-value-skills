# AI Workflow Auto-Continue Snippet

把下面内容按仓库实际情况并入 `scripts/ai-workflow.sh` 或 README 中：

## Suggested Commands

```bash
./scripts/ai-workflow.sh auto-status
./scripts/ai-workflow.sh auto-trigger manual
./scripts/ai-workflow.sh auto-checkpoint "阶段小结：描述刚完成了什么"
./scripts/ai-workflow.sh auto-mark-complete
./scripts/ai-workflow.sh auto-install
./scripts/ai-workflow.sh auto-uninstall
./scripts/ai-workflow.sh auto-progress
./scripts/ai-workflow.sh auto-runner-show
./scripts/ai-workflow.sh auto-execution-surface-show
./scripts/ai-workflow.sh auto-workflow-state-show
./scripts/ai-workflow.sh auto-handoff-show
./scripts/ai-workflow.sh auto-handoff-set waiting-user-input "缺少必要输入" "请补充需要的参数" "收到输入后重新触发" "继续当前主线"
./scripts/ai-workflow.sh auto-handoff-clear
```

## Suggested User-Facing Explanation

- `auto-status`：查看当前自动续跑是否已达到项目级完成条件
- `auto-trigger`：立刻触发一轮继续执行
- `auto-checkpoint`：在不 commit 的情况下，用“阶段小结”触发一轮继续执行
- `auto-mark-complete`：仅在项目全部完成时运行；它会先做全量验证，再写完成哨兵
- `auto-install`：安装 cron 定时巡检
- `auto-uninstall`：移除 cron 定时巡检
- `auto-progress`：输出面向人类和脚本的当前运行态摘要
- `auto-runner-show`：查看 runner state 与 writer lease
- `auto-execution-surface-show`：查看当前仓库是否是允许写入的推荐执行面
- `auto-workflow-state-show`：查看写回 `.planning/` 的运行态镜像
- `auto-handoff-show`：查看是否存在等待人工输入的 handoff 记录

## Completion Rule Text

推荐在仓库文档中明确写：

> 自动循环开发不会因为单个 task 完成而停止。只有当项目范围内全部任务完成，并且 completion gate 成功执行全量验证、写入 completion sentinel 后，自动循环才会停止。

## Operator Contract Text

推荐同时写清：

> `auto-trigger`、`auto-install` 和任何会绑定运行态元数据的命令，只允许在 `writer_recommended=yes` 的主执行面上运行。额外 sandbox/worktree 默认用于分析与实验，不默认抢占 writer 身份。

## Hook Guidance

推荐：
- `post-commit`：后台触发 `hermes-auto-continue-trigger.sh hook`
- `post-merge`：后台触发 `hermes-auto-continue-trigger.sh merge`

不要：
- 在 hook 中直接跑长时间 agent 会话
- 在 hook 中直接执行全量验证

## Cron Guidance

推荐：
- 每 15 分钟巡检一次
- 只做 watchdog / reconcile / restart-if-needed
- 不要让 cron 自己决定“小 task 完成就停机”
