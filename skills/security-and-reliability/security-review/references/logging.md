# 一次角色变更应该留下怎样的记录

Original local reference, Copyright (c)2026 seaworld008, MIT

角色管理接口收到请求后作出授权决定，应用、反向代理和审计消费者可能各自产生记录。
租户管理员能改自己的显示名或请求备注，但不应能替另一名操作者留下事件。
还要画出读者范围：业务接口看不到的字段，进入集中日志后可能被更多人长期检索。

## 缺陷示例

这里让请求决定操作者和换行位置，并把自由文本带入长期存储。
即使接入层已认证，正文里的操作者声明仍由请求者控制。

```python
def unsafe_event(request):
    return f"role.change by={request['display']} note={request['note']}"
```

## 修正示例

接口适配器只从会话和授权后的目标对象取内部编号，决定取自实际执行结果。
示例序列化一个固定事件，供按行收集 JSON 的采集器使用；写入器拒收不合契约的字段。

```python
import json
import re

def role_event(actor_id, subject_id, result):
    for value in (actor_id, subject_id):
        if not isinstance(value, str) or not re.fullmatch(r"u-[0-9]{1,12}", value):
            raise ValueError("invalid account identifier")
    if result not in ("applied", "denied"):
        raise ValueError("invalid role result")
    event = {
        "event": "role.change",
        "actor": actor_id,
        "subject": subject_id,
        "result": result,
    }
    return json.dumps(event, separators=(",", ":")) + "\n"
```

备注、Cookie、认证头和整个请求对象没有进入此接口的入口。
实际写入时增加来自可信时钟的时间，以及服务端生成的事件编号。多租户系统需绑定租户范围。
用户编号仍可能属于个人信息，检查索引的读权限、导出权限、保留期限与备份的过期策略。

## 检查记录是否对应真实效果

- 对已提交的变更生成 applied。先记成功再提交事务会留下不存在的成功操作。
- 需要保证写操作和事件一致时，在同一事务写业务记录与待发送事件，消费者按事件编号去重。
- 拒绝事件独立记录；放在将要回滚的业务事务内，会把拒绝证据一起丢掉。
- 输入无效时记录固定的失败类别，避免在异常处理或调试日志中再次输出原始对象。
- 单独核对采集器的限流和截断。反复拒绝产生的事件不应耗尽业务进程的磁盘。

## 合成验收

| 输入或故障 | 观察结果 |
| --- | --- |
| u-2 对 u-5 的操作被拒 | 解码得到 denied，只有一个 JSON 事件 |
| 客户端备注含换行和合成标记 | 适配器忽略备注，标记未出现在事件和旁路日志 |
| 传入含换行的主体编号 | 序列化前抛错，写入器收不到记录 |
| 结果为调用方自报的任意句子 | 字段拒绝，未落入结果索引 |
| 已提交事件重复投递 | 审计视图按同一事件编号保留一次 |

## 容易误判的情形

JSON 编码可以维持记录边界，但下游转为纯文本、CSV 或 HTML 时会引入新的解释规则。
变量出现在日志调用中不能直接说明泄露；检查其来源、敏感度、格式化器和真实目的地。
用本地内存写入器与合成标记观察事件数量，再核对项目采集器解析后的字段及访问策略。
取证时保留字段名、事件数和脱敏配置，不导出人员操作记录。

异常响应与内部诊断的分工见[错误处理](error-handling.md)。

平台资料：[Python JSON 编码器](https://docs.python.org/3/library/json.html#json.dumps)。
