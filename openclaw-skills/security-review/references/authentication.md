# 身份恢复与会话生命周期审查

Original local reference, Copyright (c)2026 seaworld008, MIT

## 数据流与攻击前提

凭据或身份提供方响应进入验证器，验证器生成主体，会话再把后续请求关联到该主体。
攻击者可设置普通 HTTP 头、窃取旧会话、反复尝试口令或向错误受众重放有效令牌。
“请求已认证”必须有对应验证步骤；客户端传来的用户名、角色和租户不能自证身份。
反向代理身份头只有在入口清除伪造头、阻断绕过路径并验证代理来源后才能作为证明。

## 自写示例：把自报用户名当成认证

```python
def unsafe_identity(headers):
    return {'user_id': headers['X-User']}
```

下面是单进程内存会话的教学实现，随机 token 用于客户端，服务器仅存 token 摘要。
`sessions` 与 `users` 只能由可信应用代码修改，`now` 来自服务器时钟而非请求字段。
用户表记录当前启用状态，停用账号不会因旧会话仍存在而继续登录。

```python
import hashlib
import re
import secrets

def mint_session(sessions, user_id, now):
    token = secrets.token_hex(32)
    digest = hashlib.sha256(token.encode('ascii')).hexdigest()
    sessions[digest] = {'user_id': user_id, 'expires': now + 1800, 'revoked': False}
    return token

def authenticate(token, sessions, users, now):
    if type(token) is not str or not re.fullmatch(r'[0-9a-f]{64}', token):
        raise PermissionError('invalid session')
    digest = hashlib.sha256(token.encode('ascii')).hexdigest()
    session = sessions.get(digest)
    if session is None or session['revoked'] or now >= session['expires']:
        raise PermissionError('invalid session')
    user = users.get(session['user_id'])
    if user is None or not user['enabled']:
        raise PermissionError('invalid session')
    return {'user_id': session['user_id']}
```

`mint_session` 只能在真实凭据验证成功后调用，不能暴露为“传入 user_id 即发会话”的接口。
这里对高熵随机 token 使用 SHA-256；该选择不能用于人类口令存储。
跨进程部署需要共享会话存储、到期清理与可靠撤销，不能依赖每个 worker 的独立字典。
认证返回主体仍不授予业务权限，资源操作另见[授权审查](authorization.md)。

## 不同凭据必须核对的约束

- 口令使用项目支持的专用慢哈希库和成本参数，验证失败与账号不存在对外表现一致。
- 登录限速覆盖账号与网络来源，记录安全事件但不记录口令、验证码或会话原值。
- 登录和权限升级后更换会话，撤销旧值；退出、改密与停用要有明确撤销范围。
- Cookie 会话设置 `Secure`、`HttpOnly`、合理的 `SameSite`、作用域和过期；同时处理 CSRF。
- 密码重置和验证码使用随机、短期、单次凭据，绑定账号与用途，消费须原子化。
- OAuth/OIDC 回调绑定发起会话、state、nonce 与 PKCE；核对重定向 URI 和身份提供方。
- JWT 用受支持库验证签名、允许算法、issuer、audience 与时间；`decode` 不等于验证。
- `kid` 只能查受控密钥集合，不得变成任意文件路径或请求令牌提供的远程 URL。
- MFA 后才能授予需要 MFA 的会话级别；重置和备用通道不能成为更弱的绕过入口。

## 正反验收输入

| 输入或事件 | 预期 |
| --- | --- |
| 发给启用用户的 token，在到期前使用 | 返回该用户主体 |
| 只发送 `X-User: admin` | 不创建会话，不获得管理员身份 |
| 格式合法但未签发的 64 位十六进制值 | 拒绝 |
| token 修改一个字符 | 拒绝，不返回原用户 |
| `now` 恰好等于 expires | 拒绝 |
| 会话 revoked 或用户 enabled 为 false | 拒绝旧 token |

登录失败测试只在合成账户执行，不对真实账号做口令喷洒，也不在报告中粘贴有效 token。

## 易误报与适用边界

机器身份、客户端证书与 API key 不必采用 Cookie，但同样要验证来源、权限范围和撤销。
随机 token 的快速摘要不是口令哈希缺陷；须先确认输入具有足够熵且不是用户口令。
统一失败响应不能独自消除计时差异和账号枚举，需在实际登录处理链测量。
示例不含口令验证、Cookie 发送或分布式存储，不能直接替换完整认证系统。

## 实际验证证据

记录会话产生点、所有身份入口、有效期边界、撤销传播时间和代理绕过路径的结果。
浏览器里核对实际 Cookie 属性和重登录行为，不能仅依据应用配置文件判断。
身份提供方集成需使用测试租户核对错误 audience、回调错配和旧授权响应，不能外测真实用户。

## 官方接口核对入口

- [Python secrets](https://docs.python.org/3/library/secrets.html)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth PKCE](https://www.rfc-editor.org/rfc/rfc7636.html)

先核对当前项目认证库、Cookie 中间件与 IdP 配置版本，再决定具体参数和迁移方案。
