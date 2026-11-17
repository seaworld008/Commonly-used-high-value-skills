# 浏览器附带凭据的跨站写操作审查

Original local reference, Copyright (c)2026 seaworld008, MIT

## 数据流与攻击前提

恶意站点诱导浏览器发送请求，浏览器可能自动附带目标站点的 Cookie 或其他环境凭据。
目标服务若只确认会话有效而不确认用户有意从可信页面发起操作，就可能执行跨站写入。
关注改密、转账、改邮箱、绑定账户、退出和登录等状态变化，不只检查表单页面。
SameSite 的 site 与 Origin 的源不是同一范围；受攻击者控制的同站子域也需要评估。

## 自写示例：把有效会话当成充分条件

```python
def unsafe_email_change(session, body):
    if session is None:
        raise PermissionError('login required')
    return {'user_id': session['user_id'], 'new_email': body['email']}
```

这段代码若由接收表单的路由调用，攻击站点可能在受害者 Cookie 下提交新邮箱。
修正示例是只接受 JSON POST 的同源页面接口守卫，执行成功后才进入业务处理。
`session['csrf']` 由服务用 `secrets.token_hex(32)` 生成并绑定会话，仅发给可信页面。

```python
import hmac
import re

APP_ORIGIN = 'https://app.example.invalid'

def require_csrf(method, origin, content_type, token, session):
    if session is None:
        raise PermissionError('login required')
    if method != 'POST':
        raise ValueError('method not allowed')
    if origin != APP_ORIGIN:
        raise PermissionError('untrusted origin')
    if type(content_type) is not str or content_type.split(';', 1)[0].strip().lower() != 'application/json':
        raise ValueError('unsupported media type')
    expected = session.get('csrf')
    if any(type(v) is not str or not re.fullmatch(r'[0-9a-f]{64}', v) for v in (token, expected)):
        raise PermissionError('invalid csrf token')
    if not hmac.compare_digest(token, expected):
        raise PermissionError('invalid csrf token')
```

适配器从单一 Origin 头和专用 token 头取值，拒绝重复头，不接受 URL 查询参数中的 token。
不得让请求 Host 或未验证的代理转发头决定 `APP_ORIGIN`；部署时替换为审核过的实际源。
不带 Origin、值为 `null`、格式异常或来源不同的请求按本接口约定拒绝。
需要非浏览器客户端时定义独立的非 Cookie 凭据入口，不能给此守卫加任意缺头放行分支。
JSON 和自定义头只是额外约束；宽松 CORS 或同源脚本被控制时不能依靠预检保证安全。

## 必须与路由共同落实的控制

- GET、HEAD 和 OPTIONS 不改变业务状态；不能在守卫前完成写入或发送外部请求。
- 登录后更换会话及 CSRF token，退出时销毁；登录接口也需绑定发起会话防止登录 CSRF。
- Cookie 设置 Secure、HttpOnly 与合适的 SameSite，缩小 Domain/Path 范围并核对代理 TLS 终止。
- CORS 凭据响应只授予明确可信源，不把任意请求 Origin 反射成允许源。
- token 不进入 URL、访问日志、分析事件或跨源页面，错误响应不回显它。
- HTML 表单流程若必须支持，应使用会话 token 和对应媒体类型的独立验证路径。
- 更改邮箱、支付等高风险动作还需授权和再次确认；CSRF 验证不会授予业务权限。
- 存在 XSS 时，同源恶意脚本通常可调用接口或读取 token，必须另行修复脚本注入。

## 正反验收输入

| 输入组合 | 预期 |
| --- | --- |
| 正常会话、准确 Origin、JSON POST、匹配 token | 进入业务处理 |
| 跨源站点表单提交且带有效会话 | 拒绝，不写数据库 |
| Origin 为 `null`、缺失或带额外后缀 | 拒绝 |
| 同源但 token 缺失、取自另一会话或被改动 | 拒绝 |
| 正确 token 但 GET 或 text/plain | 拒绝，不改变状态 |
| 守卫失败时业务函数计数器 | 保持零，证明无先行副作用 |

只使用受控测试站点和假账户；没有授权时不在真实用户浏览器中投递表单。

## 易误报与适用边界

仅通过显式 Authorization bearer token 认证、完全不接受环境凭据的入口可能不具备相同 CSRF 前提。
应核查 Cookie 回退、Basic 认证和代理身份等实际路径，不能只看文档声称使用 bearer。
本例故意拒绝缺 Origin 的客户端；兼容需求应设计可证明的替代路径，不静默放开。
CSRF token 不解决 XSS、跨租户越权或被盗会话；同站子域和嵌入页面还需浏览器实际验收。

## 实际验证证据

保留路由方法、凭据类型、实际 Cookie 属性与各拒绝路径的数据库前后状态。
真实浏览器核对跨站/同站子域、预检、重定向和会话轮换，记录请求头及无敏感值结果。
单元调用守卫只证明条件分支，不能证明浏览器发哪些 Cookie 或代理保留哪些头。

## 官方接口核对入口

- [Fetch 的源、凭据与 CORS 模型](https://fetch.spec.whatwg.org/)
- [HTML 表单模型](https://html.spec.whatwg.org/multipage/forms.html)

先核对项目框架 CSRF 中间件、代理和目标浏览器版本，不以名称相似推断行为相同。
