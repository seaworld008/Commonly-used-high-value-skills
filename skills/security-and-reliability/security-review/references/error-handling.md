# 授权依赖出错时，下载接口应返回什么

Original local reference, Copyright (c)2026 seaworld008, MIT

仓单下载接口接收仓单编号，先询问权限服务，再从对象存储读取文件。
仓库职员有会话就能发起请求，但只有部分职员有权读取指定仓单。
权限服务超时是一种可达状态，调用方无需控制服务本身，便可能碰上这个窗口。

## 沿两条路径审查

- 从超时、取消、无结果和响应格式异常，分别追到第一次文件读取。
- 从异常对象追到 HTTP 正文、响应头、任务状态页和稍后发送的失败通知。
- 看授权调用是否绑定当前主体、具体仓单和读取动作。不得把上一次其他仓单的成功结果用作降级值。
- 查看流式响应开始写头的时间。发送首个字节以后再转换为错误响应，已经无法收回数据。

## 缺陷示例

这个适配器把权限系统的中断转换为肯定答复。下游只看布尔值，丢失了判断依据。

```python
def unsafe_permit(check, actor, manifest):
    try:
        return check(actor, manifest)
    except TimeoutError:
        return True
```

## 修正示例

此例定义 check 契约为返回布尔值，缺失或无权返回 False，暂时不可用时抛出 TimeoutError。
actor 由会话层产生，read_manifest 是只能在授权后调用的仓单读取器。

```python
def download(check, read_manifest, actor, manifest):
    try:
        decision = check(actor, manifest)
    except TimeoutError:
        return 503, {"error": "access_check_unavailable"}
    if decision is False:
        return 404, {"error": "manifest_unavailable"}
    if decision is not True:
        return 503, {"error": "access_check_unavailable"}
    return 200, read_manifest(manifest)
```

未知决定走依赖故障分支。此处的 404 用于同时隐藏缺失仓单和无权仓单。
HTTP 适配器还要将未处理异常映射为固定的 5xx，并禁止共享缓存保存私有下载和错误响应。
需要排障时返回服务端生成的关联号，在有访问控制的内部记录中关联失败阶段。

## 用替身记录读取次数

| check 输入或行为 | 预期结果 |
| --- | --- |
| 同一职员与仓单，返回 True | 200，读取器仅收到该仓单编号一次 |
| 返回 False | 404，读取次数为零 |
| 返回 None 或字符串 "true" | 503，读取次数为零 |
| 抛出带合成诊断标记的 TimeoutError | 503，正文没有标记，读取次数为零 |
| 读取器抛出未映射的异常 | 经项目实际 HTTP 错误处理层得到通用 5xx |

## 判断范围及待取证据

页面配色服务故障时回退到默认配色，与访问决策的回退有不同后果。
同样，源码里构造了含栈信息的异常，只在确认非特权读者能收到这些信息时才能认定外泄。
逐一核对代理、调试中间件、后台任务和通知模板对同一错误的呈现方式。
如果失败发生在写入操作之后，另取事务回滚、幂等键或重试时的写入次数作为证据。
用合成标记保存一份脱敏错误响应和存储替身的调用记录；真实文件或令牌没有取证必要。

持久化错误事件时另见[日志审查](logging.md)。

平台资料：[HTTP 状态语义](https://www.rfc-editor.org/rfc/rfc9110.html)。
