# API 字段、对象与成本边界审查

Original local reference, Copyright (c)2026 seaworld008, MIT

## 数据流与攻击前提

请求经过代理、路由、解析器、身份恢复和业务服务，最后进入存储、队列或第三方调用。
攻击者可以绕过页面直接构造 JSON、重复查询参数、批量请求和旧版本 API 调用。
每个入口都要确认主体从哪里恢复、对象由谁选择、字段能改变什么，以及成本由谁承担。
内部 API、已登录请求和 server-config 中的 URL 都可能跨越租户或服务权限边界。

## 自写示例：批量赋值扩大权限

```python
def unsafe_patch_profile(row, body):
    row.update(body)
    return row
```

若 `row` 同时保存 `role` 或 `tenant_id`，调用者就能借普通资料编辑修改权限。
修正示例只处理已经解析为普通字典的请求；主体由可信会话层提供，不读 body 中的身份。
传输层须先限制请求大小，并拒绝重复 JSON 键；解析要求另见[反序列化](deserialization.md)。

```python
def patch_profile(row, actor, body):
    if actor is None or (row['user_id'], row['tenant_id']) != (
        actor['user_id'], actor['tenant_id']
    ):
        raise PermissionError('profile unavailable')
    if type(body) is not dict or not body or set(body) - {'display_name', 'timezone'}:
        raise ValueError('unsupported fields')
    changes = {}
    if 'display_name' in body:
        name = body['display_name']
        if type(name) is not str or not 1 <= len(name) <= 80:
            raise ValueError('invalid display name')
        if any(ord(char) < 32 or ord(char) == 127 for char in name):
            raise ValueError('control character')
        changes['display_name'] = name
    if 'timezone' in body:
        zone = body['timezone']
        if type(zone) is not str or zone not in {'UTC', 'Asia/Shanghai'}:
            raise ValueError('unsupported timezone')
        changes['timezone'] = zone
    result = dict(row)
    result.update(changes)
    return {key: result[key] for key in ('display_name', 'timezone')}
```

本例返回可公开的资料投影，不承担数据库持久化；集成时仅保存 `changes` 对应的允许字段。
若改成数据库写入，须把主体、租户和对象条件放入同一次写入，并处理版本冲突。
代码验证完全部字段才构造结果，不能先写一个字段再因第二个字段错误退出。
展示名仍是文字，前端按输出上下文处理，不能把通过此校验的值当可信 HTML。

## 协议与成本需要单独拒绝的情形

- 不支持的方法、媒体类型、未知字段、超量数组及多义参数应有明确失败响应。
- 分页上限同时限制响应体积；导出、聚合、搜索和 GraphQL 嵌套还需单独预算。
- 计费和写操作限制主体、租户、目标资源与并发，单一 IP 限流不能覆盖分布式调用。
- 重试同一支付或创建请求需要持久化幂等键并绑定请求内容，不能把冲突覆盖成成功。
- 资源 URL、回调 URL 和代理转发要限制出站目的地及重定向，不能只检查初始域名。
- 上传需限制实际接收字节和解压后大小；不能信任 `Content-Length` 或文件后缀。
- 旧版本、批量入口、任务消费者须执行相同对象策略；路由名称相似不是策略证据。
- CORS 仅约束部分浏览器读取行为，不能替代身份、授权或[CSRF](csrf.md) 控制。

## 正反验收输入

| 输入 | 预期 |
| --- | --- |
| 本人资料，`{"display_name":"测试","timezone":"UTC"}` | 返回两项资料，身份与角色不变 |
| `{"role":"admin"}` 或 `{"tenant_id":"other"}` | 拒绝全部修改 |
| `{"display_name":null}`、列表或空对象 | 拒绝，不隐式转换 |
| 本人合法名字加非法 timezone | 整体拒绝，原记录不变 |
| 其他租户对象加合法字段 | 拒绝，不泄露是否存在私有资料 |
| 重复 JSON 键或超限请求体 | 在调用本函数前拒绝 |

只用合成账户和测试对象验收，不向真实外部 API 发送攻击请求。

## 易误报与适用边界

允许 PATCH 不等于批量赋值漏洞，必须证明哪些输入字段能到达受保护属性。
公开、只读、有限大小的 API 可以不要求登录；仍需评估成本和公开数据的确定范围。
本例的两个时区是业务枚举示范，实际产品应使用明确的完整支持集合。
返回对象投影不等于删除数据库中的敏感字段；二者需要分别验证。

## 实际验证证据

保留路由到服务/存储的调用链、允许字段集合、错误路径与写入前后差异。
记录批量和旧版本入口的授权结果，以及实际网关和应用的大小、超时、并发配置。
静态审阅不能证明代理解析一致、限流已部署或重试一定只产生一次副作用。

## 官方接口核对入口

- [Python JSON API](https://docs.python.org/3/library/json.html)
- [HTTP 语义规范](https://www.rfc-editor.org/rfc/rfc9110.html)

先核对项目框架、解析器与代理版本；不同组件对重复字段和请求边界的解释可能不同。
