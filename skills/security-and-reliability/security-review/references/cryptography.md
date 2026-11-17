# 密码学用途、密钥与消息边界审查

Original local reference, Copyright (c)2026 seaworld008, MIT

## 数据流与攻击前提

先区分保密、完整性、来源认证和口令验证；它们需要不同的原语与密钥生命周期。
攻击者可能控制载荷、签名字段、密钥 ID、存储的密文，或重放曾经有效的消息。
TLS 保护一段传输，不能自动证明经过队列、缓存或第三方回调后的消息来源。
列出密钥生成者、保管者、读取进程、租户绑定与轮换方式，不以“环境变量”推断安全。

## 自写示例：公开校验和冒充来源认证

```python
import hashlib

def unsafe_verify(body, signature):
    return hashlib.sha256(body).hexdigest() == signature
```

任何能改 body 的发送者都能重算该摘要，因此它只能帮助发现意外损坏。
修正示例是双方约定的 HMAC-SHA256 协议片段，签名覆盖用途、时间戳和原始字节。
协议需由双方实现一致的字节格式，不能直接拿它验证格式不同的现成支付平台回调。

```python
import hmac
import re

def verify_hook(body, stamp, signature, key, now):
    if type(body) is not bytes or len(body) > 65536:
        raise ValueError('invalid body')
    if type(key) is not bytes or len(key) < 32:
        raise ValueError('invalid key configuration')
    if type(stamp) is not int or stamp <= 0 or abs(now - stamp) > 300:
        raise PermissionError('expired message')
    if type(signature) is not str or not re.fullmatch(r'[0-9a-f]{64}', signature):
        raise PermissionError('invalid signature')
    message = b'invoice-hook/v1\x00' + str(stamp).encode('ascii') + b'\x00' + body
    expected = hmac.digest(key, message, 'sha256').hex()
    if not hmac.compare_digest(expected, signature):
        raise PermissionError('invalid signature')
    return body
```

`key` 必须是经批准的随机密钥，长度门槛不证明熵；测试可使用固定假 key，生产不可。
`now` 来自服务器时钟，`stamp` 的 HTTP 解析必须拒绝多值和多义表示。
先验证原始字节再解析业务数据，不能先把 JSON 重新序列化后计算签名。
此函数通过后仍需核对商户、租户、事件类型与金额，并持久化原子消费唯一事件 ID。
五分钟窗口允许窗口内重放，不能把时间检查称为单次使用保护。

## 代码与部署中应拒绝的选择

- 不自行拼装加密模式；保密使用项目支持且经过维护的 AEAD API，同时校验认证失败。
- 按所选 AEAD 的要求生成 nonce，核对同一密钥下的唯一性及多 worker/重启行为。
- 不接受消息自报的算法或密钥 URL；算法集合和 key ID 到密钥的映射由可信策略选择。
- 同一密钥不跨租户、环境和用途随意复用；用明确上下文绑定，管理轮换与旧 key 到期。
- 密钥不能写入日志、错误信息、镜像层或客户端资源；解密失败不能返回部分明文。
- 口令需要带随机盐的专用慢哈希实现，不能用本例 HMAC 或裸 SHA-256 替代。
- 随机 token 使用平台密码学随机源；固定 seed、时间戳和普通伪随机数不适合凭据。
- 数据库加密与 TLS 都不能替代解密后字段权限和导出控制。

## 正反验收输入

| 输入或事件 | 预期 |
| --- | --- |
| 合同格式内的 body/stamp，使用测试 key 正确签名 | 返回完全相同的原始字节 |
| 修改 body 任意字节或 stamp | 拒绝，不解析业务内容 |
| 使用另一租户 key 或错误用途前缀签名 | 拒绝 |
| 超过时间窗口、非十六进制或长度错误的签名 | 拒绝 |
| key 少于 32 字节 | 配置失败，不回退为无签名模式 |
| 窗口内重放同一有效事件 | HMAC 可通过，业务去重层必须阻止重复副作用 |

用测试消息验证，不发送真实凭据或支付数据，也不把签名验证通过当作付款确认。

## 易误报与适用边界

用于缓存索引或文件去重的普通哈希不一定需要密钥，要先确认是否承担对抗性来源认证。
公开证书、盐与 nonce 不必保密；私钥和共享认证密钥才需要相应保密控制。
HMAC 不加密内容，任何拿到载荷的人仍能读取；共享 key 的双方也都能生成合法签名。
示例没有实现加密、密钥轮换或重放账本，不能宣称完整覆盖 webhook 安全。

## 实际验证证据

记录消息字节格式、测试向量、错误 key/载荷结果、密钥读取身份及轮换演练结果。
对实际加密实现记录算法参数、nonce 产生路径、认证失败行为和存量数据迁移方案。
静态 API 检查不能证明密钥熵、运行权限、时钟正确或历史 nonce 从未重复。

## 官方接口核对入口

- [Python hmac](https://docs.python.org/3/library/hmac.html)
- [Python secrets](https://docs.python.org/3/library/secrets.html)

先核对项目密码库版本及官方参数约束，示例不指定某个第三方库的未知接口。
