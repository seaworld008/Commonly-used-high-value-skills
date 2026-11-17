# 工单别名从输入到页面节点的最后一步

Original local reference, Copyright (c)2026 seaworld008, MIT

客服能给工单设置别名。值经数据库、JSON 接口和页面状态传递，最终显示在另一名客服的浏览器里。
风险取决于最后写入的位置和页面所在的源。后台保存成功或 JSON 序列化正确都没有决定页面如何解释它。
同一条别名在表格、筛选结果和打印预览中可能使用三个不同的渲染器。

## 缺陷示例

此函数供模板挂载后更新普通标签使用。HTML setter 会把值解析为节点，超出了纯文本字段的用途。

```javascript
function unsafeAlias(labelNode, alias) {
  labelNode.innerHTML = alias;
}
```

## 修正示例

组件代码持有自己创建的普通 HTML span，只负责它的文本内容。
数据来自解码后的 JSON。对不支持的类型和过长字段，在触碰页面之前拒绝。
这里的长度上限以 JavaScript 字符串的 UTF-16 码元计算。

```javascript
function renderAlias(labelNode, alias) {
  if (typeof alias !== "string" || alias.length > 120) {
    throw new TypeError("invalid ticket alias");
  }
  if (labelNode.namespaceURI !== "http://www.w3.org/1999/xhtml" ||
      labelNode.localName !== "span") {
    throw new TypeError("expected alias span");
  }
  labelNode.textContent = alias;
}
```

代码不从用户提供的选择器查找目标。后续组件也应直接使用数据或文本节点，
避免先取出 textContent 又把它交给解析 HTML 的预览器。

## 把来源和输出语境配对

| 来源与写入位置 | 需要检查的地方 |
| --- | --- |
| 查询参数立即回显在服务端 HTML 中 | 检查模板在具体文本或带引号属性中的自动转义，并追踪关闭转义的分支 |
| 数据库字段出现在其他人的工单页面 | 找到能够写该字段的角色和能够读该字段的角色，覆盖历史数据与批量导入 |
| URL 片段进入客户端预览 | 追踪前端路由、解码步骤及最终 DOM setter，服务端日志里可能没有这段值 |
| 字段进入链接目的地 | 按允许的协议、目的与业务语义验证；文本转义不会限制导航行为 |
| 数据嵌入脚本、样式或事件属性 | 优先改为独立数据和受控事件绑定；核对外层 HTML 解析及内层解释器 |
| 允许富文本 | 选定明确的元素、属性与 URL 策略，核对消毒组件版本，检查消毒后的任何再加工 |

脚本策略与可信类型可限制部分危险写入；确认实际响应是否启用、策略是否仅报告，以及哪些策略能产出 HTML。
客户端只向自己显示的草稿，与共享给高权限读者的持久化字段有不同影响。保留写入与查看所需前提。

## 使用无执行能力的页面夹具

- 正例：别名为 北区 12，span 显示这五个字符（含空格），没有元素子节点。
- 边界：别名为 `<b>北区</b>`，页面逐字显示尖括号，span 的 childElementCount 为零。
- 反例：传入对象或 121 个 ASCII 字符，组件抛错，原有文本不变。
- 反例：目标为普通 HTML a 元素，组件拒绝写入。
- 存储路径：使用同一段无害标记保存并重新加载，再打开列表和打印预览，检查所有显示点。

## 判断边界与证据

静态常量写入模板、正常的模板文本插值，与把用户输入交给 HTML 解析器有不同的数据流。
审查时记录组件与模板版本、输入写入者、读者、渲染调用位置及浏览器最终节点类型。
本地替身能验证拒绝发生在赋值前；节点结构、脚本策略和实际预览路径需要在受控页面观察。
使用虚构工单即可，不需要插入活动内容或向外部地址发起请求。

可编辑页面元素影响脚本命名查找的情形见[现代应用的操作边界](modern-threats.md)。

平台资料：[DOM 节点文本赋值语义](https://dom.spec.whatwg.org/#dom-node-textcontent)。
