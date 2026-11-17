# 在查询编译之前划清结构和值

Original local reference, Copyright (c)2026 seaworld008, MIT

客服界面接收队列名和排序模式，查询当前租户的工单。
收藏的筛选器会在夜间任务中复用，因此从数据库读出的字符串也可能源自低权限用户。
审查时标出每个字段最终占据的位置：比较值、列名、运算符，还是一整段表达式。

## 缺陷示例

查询构造器把显示名称直接写进 SQL 文本。即使名称来自已登录客服，数据库仍按 SQL 语法解释它。

```python
def unsafe_queue_query(queue):
    return f"SELECT ticket_id FROM ticket WHERE queue = '{queue}'"
```

## 修正示例

以下使用 Python sqlite3 的问号占位符。部署使用其他驱动时，核对它自己的绑定接口。
租户编号取自已验证的访问上下文，调用方还需具有该租户的队列检索权限。

```python
def queue_tickets(db, tenant, queue, order):
    ordering = {"first": "ticket_id ASC", "last": "ticket_id DESC"}
    if not isinstance(order, str) or order not in ordering:
        raise ValueError("unsupported order")
    if not isinstance(queue, str) or not 1 <= len(queue) <= 80:
        raise ValueError("unsupported queue")
    statement = (
        "SELECT ticket_id FROM ticket WHERE tenant = ? AND queue = ? "
        "ORDER BY " + ordering[order]
    )
    return db.execute(statement, (tenant, queue)).fetchall()
```

排序是语法位置，由本地映射给出完整片段。队列名永远通过值通道送入驱动。
已有 ORM 的代码也要追到最后一层：原始谓词、动态列名或自定义排序可重新引入字符串编译。

## 对其他解释器提出具体问题

| 目的端 | 需要确认的拒绝点 |
| --- | --- |
| 文档数据库 | 标量筛选字段先做类型检查，服务端构造固定查询对象；拒绝由请求对象定义运算符 |
| 命令行程序 | 固定可执行文件与操作模式，按独立参数传值，并按该程序的选项规则限制操作数 |
| LDAP | 区分过滤器值与 DN 分量，在实际库中使用对应的构造或编码 API |
| 模板引擎 | 模板源来自受控发布物，用户字段仅填入数据上下文；拒绝将存储的正文编译成模板 |
| 搜索或表达式语言 | 明确是否授权用户写表达式，限制可调用的函数、字段和执行成本 |

进程启动时关闭 shell 可消除一层解释；被调用程序仍可能解析选项、配置或嵌套语言。
字符串替换可能适用于一个语法位置，不能自动延伸至嵌套解释器。

## 用内存数据库验收

建立 ticket(tenant, queue, ticket_id) 夹具，两租户都添加名为 O'Brien 的队列。
在本租户插入工单 3 和 8，另一租户插入 9。所有名称和记录均为合成数据。

- 正例：队列 O'Brien 配 last，仅返回 8、3；配 first，仅返回 3、8。
- 反例：排序为 sideways，或队列为对象，在调用 execute 前被拒绝。
- 边界：查询不存在的普通队列应返回空集；单引号作为名称的一部分应能精确匹配。
- 重放同一份收藏条件，确认后台任务从自己的授权上下文取得租户，而非相信收藏记录中的声明。

## 如何判读证据

只拼接不可变映射中的列片段时，字符串拼接本身不足以报告注入。
记录请求和持久化字段的写入者、最终语句模板、绑定参数个数以及实际驱动版本。
生产查询日志可能含客户输入；保留夹具与结果集即可，无需采集真实语句参数。

模板输出还会经过浏览器解释时，继续检查[页面输出位置](xss.md)。

平台资料：[Python sqlite3 参数绑定](https://docs.python.org/3/library/sqlite3.html#how-to-use-placeholders-to-bind-values-in-sql-queries)。
