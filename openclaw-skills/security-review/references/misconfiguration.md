# 谁能在浏览器里读取带会话的报表

Original local reference, Copyright (c)2026 seaworld008, MIT

财务前端与报表 API 部署在不同源。接口根据 Cookie 识别人员和租户。
浏览器是否附带 Cookie 取决于请求设置、站点关系、Cookie 属性和浏览器策略。
如果不受信页面能携带这些凭据、并且 API 允许该源读取响应，该页面便能读到用户可见的报表。

## 缺陷示例

网关把来访源反射成允许源，另外允许携带凭据。租户自建页面也可能成为来访源。

```python
def unsafe_headers(origin):
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
    }
```

## 修正示例

这条路由专供一个浏览器前端进行跨源 GET。其他客户端使用各自授权的路由。
框架先拒绝重复的 Origin 头，将单个字段原样交给函数；生产白名单由有发布权限的人维护。

```python
def report_headers(origin, method):
    headers = {"Vary": "Origin", "Cache-Control": "private, no-store"}
    if origin != "https://reports.example.test":
        return 403, headers
    if method != "GET":
        return 405, {**headers, "Allow": "GET"}
    return 200, {
        **headers,
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
    }
```

只有返回 200 时才进入会话验证、报表授权与读取；前置函数返回 200 本身不授予报表权限。
已有 Vary 的部署应合并字段。此例只演示简单 GET，未提供 OPTIONS 预检处理。
需要预检的路由应单独核对允许的方法和请求头，并在实际请求时再次鉴权。
有副作用的接口还要处理 CSRF；跨源响应不可读不能撤销已经发生的写入。

## 审查最终生效的部署

- 按请求经过的顺序核对 CDN、反向代理、应用中间件各自增删的头。两层各加一次也会改变浏览器行为。
- 租户能否编辑自定义域名、写入动态允许列表，或控制同站子域？追到配置写入者与审核边界。
- 检查生产构建和启动覆盖项。调试页面、示例账号、目录浏览和管理端点可能由环境变量重新打开。
- 代理转发的主机与协议只有在入口剥离来访者自填字段并重设、且服务仅信任指定代理时才有依据。
- 对 HTML 检查嵌入策略、脚本策略，对附件检查内容类型与嗅探策略；先分清实际提供的响应类型。
- 对部署所用版本核对中间件默认值。仅看到仓库示例配置不能说明线上已经采用。

## 路由级验收输入

| 源与方法 | 预期 |
| --- | --- |
| https://reports.example.test 和 GET | 返回单一允许源，继续验证主体与报表归属 |
| 同一域名但协议为 http 或使用不同的非默认端口 | 403，没有允许源，读取次数为零 |
| 字面值 null、无 Origin 或未知站点 | 此跨源专用路由返回 403 |
| 合法源和 POST | 405，报告读取与写入均未开始 |

公开、无凭据的静态字体对所有源开放，与私人报表的读权限不同。
命令行客户端可自行声明 Origin；源匹配不能证明身份。保留脱敏的最终响应头和业务授权结果。
若核验跨源读取，使用隔离测试配置、虚构账号与报表，分别观察允许源和拒绝源的页面结果。
默认审查可在本地调用头部函数，不向实际站点发送带凭据请求。

前端渲染响应时还应检查[页面输出位置](xss.md)。

平台资料：[Fetch 的跨源资源共享协议](https://fetch.spec.whatwg.org/#http-cors-protocol)。
