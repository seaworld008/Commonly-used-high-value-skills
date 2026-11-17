# 业务状态、并发与重复请求审查

Original local reference, Copyright (c)2026 seaworld008, MIT

## 数据流与攻击前提

业务输入先选择订单或库存，再通过状态转换写库，最后可能触发支付、发货或通知。
攻击者可以重复点击、重放成功请求、并发提交、换幂等键或跳过 UI 中的前置步骤。
列出不可破坏的业务约束，例如库存不为负、退款不超过实付、优惠不能重复兑现。
身份验证只说明谁发起操作，不能证明价格、状态、数量或转换次序正确。
## 自写示例：检查和扣减之间的竞态

```python
def unsafe_reserve(conn, sku, qty):
    stock = conn.execute('SELECT available FROM stock WHERE sku=?', (sku,)).fetchone()[0]
    if stock >= qty:
        conn.execute('UPDATE stock SET available=available-? WHERE sku=?', (qty, sku))
```

两个请求都读到库存 1 后各扣 1，即可能产生负库存；重复请求还会重复扣减。
修正示例使用 SQLite 专用连接，`isolation_level=None`、无外层事务，手动控制事务。
`stock` 有唯一键 `(tenant_id, sku)`；`reservations` 有唯一键 `(tenant_id, request_key)`。
`actor` 来自认证及当前租户成员验证；商品是否允许该成员购买须在进入本函数前判定。

```python
def reserve(conn, actor, sku, qty, request_key):
    if actor is None:
        raise PermissionError('not allowed')
    if type(qty) is not int or not 1 <= qty <= 20:
        raise ValueError('invalid quantity')
    if any(type(v) is not str or not 1 <= len(v) <= 80 for v in (sku, request_key)):
        raise ValueError('invalid identifier')
    tenant, user = actor['tenant_id'], actor['user_id']
    conn.execute('BEGIN IMMEDIATE')
    try:
        old = conn.execute(
            'SELECT user_id, sku, qty FROM reservations WHERE tenant_id=? AND request_key=?',
            (tenant, request_key),
        ).fetchone()
        if old is not None:
            if old != (user, sku, qty):
                raise ValueError('idempotency conflict')
        else:
            changed = conn.execute(
                'UPDATE stock SET available=available-? '
                'WHERE tenant_id=? AND sku=? AND available>=?', (qty, tenant, sku, qty),
            ).rowcount
            if changed != 1:
                raise ValueError('insufficient stock')
            conn.execute('INSERT INTO reservations (tenant_id, request_key, user_id, sku, qty) '
                         'VALUES (?, ?, ?, ?, ?)',
                         (tenant, request_key, user, sku, qty))
        conn.execute('COMMIT')
        return request_key
    except Exception:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        raise
```

库存扣减和幂等记录同时提交；发生错误或请求内容冲突时两者都不保留部分变更。
同一 key 的重试返回原预留标识；换 key 是新操作，还需要账号限额和反滥用规则。
生产表增加 `CHECK(available>=0)` 和数量约束；约束是兜底，仍需审阅业务状态机。

## 必须由业务代码拒绝的转换

- 价格、币种、折扣和退款上限从可信账本计算，不采用客户端传来的最终金额。
- 草稿、支付中、已支付、已取消之间定义允许转换，用条件写入阻止过期状态覆盖新状态。
- 退款累计金额与原支付绑定，金额使用最小货币单位整数并核对币种和舍入规则。
- 支付成功回调核对商户、订单、金额、签名与唯一事件 ID，不以回调到达或 HTTP 200 定案。
- 外部副作用不能放在持锁事务中冒充原子操作；可用事务 outbox 与接收端幂等实现恢复。
- 幂等记录保留期覆盖允许的重试窗口；删除记录后重放的行为需要明确设计。

## 正反验收输入

| 输入或调度 | 预期 |
| --- | --- |
| 库存 1，同一主体申请数量 1 | 库存变 0，生成一条预留 |
| 相同 key 和相同内容重试 | 返回原 key，不再扣库存 |
| 相同 key 改数量、商品或主体 | 冲突，库存与原预留不变 |
| 数量 0、负数、`True` 或 21 | 在事务前拒绝 |
| 两个连接用不同 key 抢同一份库存 | 只有一次成功，库存不为负 |
| 扣减后插入预留失败 | 整个事务回滚 |

并发验收须用独立连接与同步起点；单连接串行调用不能证明竞态已覆盖。
## 易误报与适用边界

请求重试本身正常，只有产生额外副作用或返回错配结果才违反幂等约定。
限购与库存是不同约束；本例没有实现每用户限购、支付或过期释放预留。
SQLite 的写锁模型不能直接类推到其他数据库，迁移时核对隔离级别与条件更新语义。

## 实际验证证据

保存初始账本、请求 key/内容的脱敏摘要、并发调度、最终库存与预留条数。
在扣减、提交和外部确认之间注入可控失败，记录恢复后是否重复发货或漏记付款。
静态检查不能证明分布式系统恰好执行一次；必须说明重试和补偿覆盖范围。
## 官方接口核对入口

- [SQLite 事务与锁](https://www.sqlite.org/lang_transaction.html)
- [Python sqlite3 连接事务设置](https://docs.python.org/3/library/sqlite3.html)
