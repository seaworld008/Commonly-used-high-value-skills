# 当模型、页面和长连接都能提出操作请求

Original local reference, Copyright (c)2026 seaworld008, MIT

协作笔记支持用模型建议标签，并通过 WebSocket 推送编辑结果。
一名协作者可以写入稍后被模型检索的文字；页面和客户端还能提交自己的消息。
系统若把模型产出的动作名、对象编号或权限标志当成授权决定，就跨越了协作者原有的权限范围。

## 缺陷示例

调度器直接交付模型指定的操作和笔记。能影响提示上下文的人因此有机会改变操作范围。

```javascript
function unsafeProposal(proposal, dispatch) {
  return dispatch(proposal.action, proposal.note);
}
```

## 修正示例

此工具唯一能力是为当前打开的笔记添加一种预定义标签。
proposal 来自已经解码的 JSON。binding 由服务端在选择笔记时建立，包含会话主体和目标编号。
commitLabel 是项目注入的事务写入器，按当前主体、笔记归属及最新编辑权限有条件地写入。

```javascript
function applyLabel(proposal, binding, commitLabel) {
  if (proposal === null || typeof proposal !== "object" ||
      Array.isArray(proposal)) {
    throw new TypeError("expected proposal object");
  }
  const keys = Object.keys(proposal);
  if (keys.length !== 1 || keys[0] !== "label") {
    throw new TypeError("unexpected proposal fields");
  }
  const label = proposal.label;
  if (label !== "review" && label !== "follow-up") {
    throw new RangeError("unknown label");
  }
  return commitLabel(binding.actor, binding.note, label);
}
```

调用边界须处理写入器的拒绝；写入器发现权限已撤销时影响行数应为零。
提示模板里要求模型遵循规则有助于输出质量，能否执行操作由持有权限的代码决定。
检索数据按当前主体与租户过滤；送给外部模型前另行核对允许披露的字段。

## 同一功能里的其他入口

| 入口 | 容易忽略的前提 | 审查落点 |
| --- | --- | --- |
| 偏好设置的深层合并 | 请求能定义属性路径；之后的授权读取继承属性 | 拒绝未知键，用显式字段创建新值；字典可用 Map，检查所有读取者 |
| DOM 的命名属性 | 协作者可插入带 id 或 name 的标记，页面按全局名取配置 | 把能力和配置存在模块局部变量；显式获取并验证预期节点 |
| WebSocket 握手 | 浏览器可能自动附带会话，其他站点可以尝试建立连接 | 校验允许源和会话，在订阅与写入时重新核对具体资源；处理注销和撤权 |
| 消息队列 | 连接级授权先于当前消息，旧队列可能重放 | 限制帧大小与发送速率，将去重键绑定主体与资源，按实际提交结果回执 |
| 检索文档、工具结果 | 内容由第三方编写，后来出现在模型上下文 | 当作数据；模型建议经有限动作集处理，敏感操作单独绑定用户意图 |

## 用惰性替身验收

- 输入仅含 label=review 的普通 JSON 对象；记录写入器收到的主体和笔记来自 binding。
- 提案额外带 note、action 或其他键；应抛错且写入次数为零。
- 输入空对象、数组或未定义的标签；应在事务前拒绝。
- 同一条合法标签提案遇上已撤销权限；模拟条件更新失败，核对接口没有发出成功回执。
- 在普通模块存放配置时，用同名的页面元素作夹具，确认配置读取结果未受影响。
- 会话过期后重发合成的订阅消息，验收服务端不再交付笔记事件。

## 哪些证据能区分风险

模型能复述文档中的指令，不足以说明它能调用写入器；取证需要工具清单、调度路径及授权结果。
普通对象里出现特殊键也不等于原型已改变，检查赋值目的对象、合并函数版本以及安全敏感的读取点。
在测试替身中记录参数名与调用计数即可；不要把真实提示、笔记、模型密钥或会话送至外部。
浏览器如何解释协作者的标记，见[页面输出位置](xss.md)。

平台资料：[浏览器 WebSocket 接口](https://websockets.spec.whatwg.org/)。
