# GLM API 配置指南

## 凭据与安全检查

Stage 2/3 从显式传入的进程环境读取 `GLM_API_KEY`。沿用已有账号、数据共享和 setup 授权，通过安全注入方式配置；不要搜索登录文件、shell profile 或其他账号，不把 key 写入源码、命令历史、shell 追踪或报告。

只检查存在性，Python 在进程内部读取环境，返回布尔状态：

```bash
python -c 'import os, sys; sys.exit(0 if os.environ.get("GLM_API_KEY") else 1)'
```

非空值退出 0，缺失或空值退出 1；不输出原值。不要通过 echo、printenv、全量 env 或 shell 变量展开做诊断；即使最终只输出“已设置”，xtrace 也可能记录展开的参数。

缺 key 时包装器在启动核心 CLI 前退出 1；核心 CLI 在词典 Stage 1 后退出 1。数据库 `--validate` 不测试提供商连通性，凭据存在也不证明权限/余额/模型可用。

## 随包提供商配置

当前提供商为 GLM 的 Anthropic 兼容 messages 接口；默认模型 `GLM-4.6`，备用 `GLM-4.5-Air`，以 `scripts/core/ai_processor_async.py` 实现为准。这是随包配置说明，未联网确认服务当前可用性或价格。

请求使用 `Authorization: Bearer`、`anthropic-version` 和 JSON 内容类型。代码在 Python 进程中构造请求头；不要把 Authorization 输出到日志或命令行。支持环境依赖为 httpx、filelock，HTTP/2 可选，不强迫安装 h2。普通调用无需手动复制 GLM key 到其他提供商变量。

## 获取和轮换

在已有授权下，通过提供商官方控制台管理自己的 key。新建/轮换后安全更新运行环境；不要把完整 key 发给排障人员。费用、模型可用性、额度以账号当前控制台为准，离线文档无法验收。

## 故障排查

- 401/403：核对当前账号授权和 key 状态，报告脱敏状态码。
- 超时/限流：检查账号配额和网络；保留失败状态，不把部分文本当成功。
- 主备模型均失败：Stage 2 未交付，检查退出 1 与本次 manifest；不保证宿主专用 fallback 标记。
- 无网络或未获数据共享授权：运行 Stage 1 或在已有授权内人工校正，保留原稿与不确定性，不打开浏览器。

详细参数和实际产物见 `script_parameters.md`，排障只记录必要状态，不能输出 key、请求头或原稿正文。
