# 限定代查服务可以联系的目的端

Original local reference, Copyright (c)2026 seaworld008, MIT

构建面板允许维护者代查制品系统的健康状态。请求由面板服务发出，使用它自己的网络位置。
能使用面板的人可能没有直接访问该网络的权限。即便状态页只显示成功或失败，出站副作用仍然存在。
查清谁能写目的地址：请求参数、项目设置、可编辑的集成记录和重定向响应都有各自的写入者。

## 缺陷示例

租户可编辑的集成记录决定连接地址。定时任务读取记录并生成以下请求计划，无需原操作者在线。

```python
def unsafe_probe_plan(integration):
    return "GET", integration["status_url"]
```

## 修正示例

业务只需查询两个已审定的端点，所以请求者仅能选择连接器编号。
granted 从当前主体的服务端授权结果取得；不能从请求携带的列表构造。
本例生成计划，实际发送由受控传输层负责。

```python
def status_plan(connector, granted):
    targets = {
        "builds": "https://builds.example.test/health",
        "packages": "https://packages.example.test/ready",
    }
    if not isinstance(connector, str) or connector not in targets:
        raise ValueError("unknown connector")
    if connector not in granted:
        raise PermissionError("connector unavailable")
    return {
        "method": "GET",
        "url": targets[connector],
        "follow_redirects": False,
    }
```

其中 follow_redirects 是应用计划字段。核对当前 HTTP 客户端的实际 API，
在发送适配器中显式关闭自动跳转；把任何 3xx 作为查询失败，不能再次拿 Location 建立连接。
禁止透传入站 Cookie、认证头和代理设置。若供应商需要凭据，凭据应只绑定对应受审连接器。

## 目的端可以变动时

- 固定名称的 DNS、服务发现记录和出站代理也能改变最终连接。确认谁能修改它们以及生效的网络策略。
- 自定义 URL 产品需要独立设计。使用与连接器一致的解析规则，限制协议、端口、用户信息和目的范围。
- 检查实际选择的 IPv4、IPv6 及映射地址，覆盖本机、私网、链路本地、保留地址与环境自有内部网段。
- 多地址、重试和重解析会改变连接目标。策略须约束每次实际连接；解析后再按原名自由拨号会留下时间差。
- 若由代理解析或拨号，在代理处约束目的端。保留 TLS 的主机名和证书验证。
- 业务确需跳转时，逐跳重新授权，限制跳数并隔离凭据。成功连接也要限制读时长、响应字节和解压后大小。

## 验收计划与发送适配器

| 夹具 | 应观察到的证据 |
| --- | --- |
| 已获准查询 builds | 只生成固定 GET 计划，URL 的路径和端口不由请求者提供 |
| 传完整 URL 或未知编号 | 构造器拒绝，发送替身调用数为零 |
| 已知编号但主体无权使用 | 权限错误，发送替身调用数为零 |
| 首跳替身返回带 Location 的 302 | 适配器报告失败，替身仅接到一次请求 |
| 首次解析与重试返回不同范围地址 | 有地址策略的拨号替身记录第二次拒绝，未传响应内容 |

## 判断与取证范围

代码中出现 HTTP 客户端不代表调用方能改变目标；反过来，来自服务端配置也不能终止追踪。
记录配置写权限、授权输入、客户端版本、代理解析位置、重定向选项以及测试拨号决策。
默认使用内存响应和解析替身。无需探测内部地址、云元数据或第三方站点，也不应转发真实凭据。
如果唯一可用的观察是生成的计划，应将实际拨号和出口策略列作待验证项。

解析文档时的隐式网络请求见[文件处理](file-security.md)。

平台资料：[Python URL 解析接口及其验证边界](https://docs.python.org/3/library/urllib.parse.html#url-parsing-security)。
