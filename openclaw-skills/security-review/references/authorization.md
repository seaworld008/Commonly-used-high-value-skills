# 主体、资源与操作授权审查

Original local reference, Copyright (c)2026 seaworld008, MIT

## 数据流与攻击前提

认证层给出主体，路由选择资源，业务层尝试读取或写入，后台任务还可能延迟执行。
攻击者通常已有普通账号，可改对象 ID、租户参数、批量列表或队列里的资源标识。
需要证明的是主体在当前租户、对象状态与操作下拥有权限，不能停在“已经登录”。
资源 ID 不可猜测只减少发现机会，不构成对象权限；从日志或分享链接仍可能获得它。

## 自写示例：缺少归属条件的写入

```python
def unsafe_rename(conn, doc_id, title):
    conn.execute('UPDATE documents SET title=? WHERE id=?', (title, doc_id))
```

修正示例的策略是“仅当前租户内文档所有者可改名，且文档仍为 draft”。
`actor` 必须由服务验证会话并查询当前成员关系生成；不能直接取请求里的同名对象。
表中 `(tenant_id, id)` 有唯一约束，`owner_id` 与 `state` 是受保护属性。

```python
def rename_document(conn, actor, doc_id, title):
    if actor is None:
        raise PermissionError('document unavailable')
    if type(doc_id) is not str or not 1 <= len(doc_id) <= 80:
        raise ValueError('invalid document id')
    if type(title) is not str or not 1 <= len(title) <= 120:
        raise ValueError('invalid title')
    with conn:
        result = conn.execute(
            'UPDATE documents SET title=? '
            'WHERE id=? AND tenant_id=? AND owner_id=? AND state=?',
            (title, doc_id, actor['tenant_id'], actor['user_id'], 'draft'),
        )
        if result.rowcount != 1:
            raise PermissionError('document unavailable')
```

归属和可编辑状态与变更处于同一 SQL 语句，避免先读后写期间对象转移或发布。
零行匹配统一失败，调用方不能为“帮助用户”再用无租户查询返回对象详情。
调用前还须验证成员关系仍有效；高风险变更要把成员撤销与写入的竞态纳入事务设计。
管理员与共享编辑者不在本例策略内，应另写明确分支，不能放宽为任意非空角色。

## 跨入口需要拒绝的能力

- 列表、计数、搜索和导出查询都包含租户及可见性条件，不能只保护详情接口。
- 批量接口逐项授权；先约定全部失败还是部分成功，不能让未授权项产生副作用。
- 下载签名 URL 是持有者能力，限制资源、动作与期限，且不能通过替换路径扩大范围。
- 字段授权区分改名、转移所有权、改角色和发布，普通 PATCH 不得覆盖受保护属性。
- Worker 使用服务账号执行任务前，验证委托主体、租户及任务动作，不能信任消息体自报权限。
- 缓存键包含策略所需的租户和主体范围；授权失败不能落入公共缓存命中路径。
- 数据库 RLS 需核对连接池重用时上下文清理、绕过角色和迁移账号权限。
- WebSocket、订阅与长任务要处理成员撤销；建立连接时允许不代表永久允许。
- `403` 或 `404` 的选择应与产品约定一致，但两者都不能先泄露对象正文。

## 正反验收输入

| 主体与对象 | 预期 |
| --- | --- |
| 租户 A 的所有者修改 A/d1 的 draft 标题 | 恰好更新一行 |
| A 的其他普通成员修改 A/d1 | 拒绝，标题不变 |
| B 的成员传入 A/d1 的 ID | 拒绝，不返回标题或归属 |
| 所有者修改已经 published 的 d1 | 拒绝，发布状态不变 |
| 未认证主体或不存在的 ID | 拒绝，不插入替代记录 |
| 更新前文档所有者被转移 | 原所有者的更新不再匹配 |

验收只使用至少两个测试租户和假文档，检查数据库变化而不仅是 HTTP 状态。

## 易误报与适用边界

共享对象、公共资源和平台支持操作可以有不同策略，须找到明确规则及调用方身份。
UUID、隐藏按钮或前端角色检查不足以证明权限；也不能仅因对象 ID 可猜就判定越权成功。
参数化 SQL 解决值注入，不会自动补足主体条件。
该 SQL 示例不覆盖跨服务策略缓存、成员表竞态或多主体协作授权。

## 实际验证证据

保留主体来源、策略定义、实际 SQL 条件和成功/拒绝时数据库前后状态。
记录详情、列表、批量、导出和 worker 各入口的代表用例，不用单个控制器推断全覆盖。
对撤销、对象转移和缓存命中使用受控并发验收，说明存在的时间窗口与事务隔离级别。
静态审阅不能证明生产连接角色、租户上下文或策略服务总是按预期设置。

## 官方接口核对入口

- [Python sqlite3](https://docs.python.org/3/library/sqlite3.html)
- [PostgreSQL 行安全策略](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [SQLite 事务](https://www.sqlite.org/lang_transaction.html)

采用不同数据库时先核对驱动 rowcount、事务模式、隔离级别与当前项目版本。
