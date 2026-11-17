# JavaScript 输入到执行与浏览器输出的审查

Original local reference, Copyright (c)2026 seaworld008, MIT

## 数据流与攻击前提

检查 HTTP 字段、消息事件、URL 参数如何进入命令参数、对象属性、HTML 或外部请求。
攻击者未必能修改服务器文件；只控制一个文件名或对象键也可能改变命令语义。
Node.js 后端与浏览器代码拥有不同能力，应分别追踪权限和依赖，不共用“已转义”结论。
异步任务必须携带经验证的主体和资源范围，不能从可修改的消息体直接恢复管理员身份。

## 自写示例：文件选择变成 shell 语法

以下函数将用户控制的名字交给 shell；不能运行这个反例来“试试看”。

```javascript
import { exec } from 'node:child_process';
export function unsafeCount(name, callback) {
  exec('wc -c /srv/reports/' + name, callback);
}
```

修正将操作限定为两个公开报告，路径由服务维护，调用方无权修改目录或映射。
私有报告仍需在调用前按主体和报告归属鉴权；这里的公开文件假设不能套用到私有数据。

```javascript
import { execFile } from 'node:child_process';
const reports = new Map([
  ['daily', '/srv/reports/daily.txt'],
  ['weekly', '/srv/reports/weekly.txt'],
]);
export function countPublicReport(name, callback) {
  if (typeof name !== 'string' || !reports.has(name)) {
    throw new TypeError('unknown report');
  }
  return execFile('/usr/bin/wc', ['-c', reports.get(name)], {
    shell: false,
    timeout: 2000,
    maxBuffer: 4096,
    env: { PATH: '/usr/bin:/bin', LANG: 'C' },
  }, callback);
}
```

代码在执行前拒绝未知选择，固定可执行文件与参数位置，不让输入解释成 shell 内容。
固定路径仍须检查所有者和可写性；攻击者可替换报告或二进制时，这个边界即失效。
`execFile` 避免 shell 解析，但任意工具的参数仍可能选择插件、配置或输出路径。
超时与输出上限只限制这一次调用，不能代替请求并发上限与队列长度限制。
路径 `/usr/bin/wc` 是 Unix 示例，部署前核对平台与实际二进制，不能静默回退到 shell。

## 其他必须跟到具体接收点的边界

- `innerHTML`、模板中的原始 HTML 和富文本渲染需区分文字、属性、URL、脚本上下文。
- 普通文本写入 `textContent`；需要富文本时采用项目支持的清洗器并核对版本及允许协议。
- `JSON.parse` 后只投影允许字段；不要把任意键递归合并到原型或共享配置对象。
- `__proto__`、`constructor`、`prototype` 的风险取决于合并实现及后续读取，不能仅搜索字符串定案。
- `fetch` 的 URL 与重定向涉及 SSRF；限制目的地、解析后的地址、每跳重定向和响应体积。
- `postMessage` 接收方验证 `event.origin`、发送窗口和消息结构；发送方指定准确目标源。
- 浏览器中可见的 API 密钥视为公开数据，不能赋予后端管理或跨租户读取能力。
- Promise 拒绝必须落到明确错误路径；失败后不能继续执行扣款、授权或文件发布。

## 正反验收输入

| 输入 | 预期 |
| --- | --- |
| `daily` | 仅请求固定的 daily 文件计数 |
| `weekly` | 仅请求固定的 weekly 文件计数 |
| `daily; echo marker` | 在 `execFile` 之前抛错，不启动子进程 |
| `../../private` 或 `--help` | 拒绝，不读取文件也不改变工具选项 |
| 对象、`null`、带尾随空格的名字 | 拒绝，不隐式转字符串 |
| 合法报告但工具超时 | 回调接收错误，调用方不把它当成成功结果 |

可用替身记录 `execFile` 参数进行本地验收；真实执行只能读取自备的公开测试文件。
浏览器输出用包含 `<b>marker</b>` 的普通文字验收：显示文字而非生成 HTML 元素。

## 易误报与适用边界

常量命令字符串本身不证明注入；必须指出攻击者控制的片段与到达 shell 的路径。
`eval` 出现在构建工具依赖中不等于业务输入能到达它，应检查运行环境与实际参数。
HTML 转义对命令、SQL 和 URL 没有通用保护效果，不能跨接收点复用结论。
本示例只解决公开报告选择和命令构造；私有数据权限、文件竞态、依赖漏洞仍须另审。

## 实际验证证据

保存输入到命令调用的调用链、拒绝分支的执行记录，以及启动参数的无敏感值快照。
记录超时、非零退出码、输出超限如何映射为 API 失败，确认不会返回部分敏感输出。
浏览器验证需记录 DOM 结果、CSP 生效情况和消息源；静态语法检查不能替代这些证据。

## 官方接口核对入口

- [Node.js 子进程 API](https://nodejs.org/api/child_process.html)
- [Node.js 版本发布](https://nodejs.org/en/about/previous-releases)
- [HTML 平台规范](https://html.spec.whatwg.org/multipage/)

先按项目锁定的 Node.js、框架和目标浏览器版本核对行为，本例使用 ES module 语法。
