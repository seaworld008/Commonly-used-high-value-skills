# 发布任务消费的字节来自哪次审阅

Original local reference, Copyright (c)2026 seaworld008, MIT

发布流水线从缓存取出一个转换器包，在持有发布权限的任务中使用它。
贡献者也许只能写测试分支，却可以填充共享缓存、修改构建脚本或改变包解析顺序。
要把缓存写入者、预期摘要的发布者和最终执行包的身份分别画出来。

## 缺陷示例

缓存包自带摘要，校验通过仅说明二者彼此一致。
能够同时替换字节与摘要的一方，实际上可以决定构建任务将要消费的内容。

```python
import hashlib

def unsafe_cache_check(blob, cache_metadata):
    return hashlib.sha256(blob).hexdigest() == cache_metadata["sha256"]
```

## 修正示例

发布者固定本轮发布的包名、版本、目标平台和预期摘要；锁定表由受保护的发布输入提供。
缓存仅返回有大小上限的 bytes。校验后把同一份不可变字节交给后续步骤，避免重新按路径取包。

```python
import hashlib

def select_package(release_lock, name, version, platform, blob):
    expected = release_lock.get((name, version, platform))
    if expected is None:
        raise ValueError("package outside release lock")
    if type(blob) is not bytes or len(blob) > 8 * 1024 * 1024:
        raise ValueError("unsupported package")
    if hashlib.sha256(blob).hexdigest() != expected:
        raise ValueError("package digest mismatch")
    return blob
```

接收端应在下载过程中实施大小限制。此函数处理的是已经有界的内存输入。
若被审变更本身就能重写发布锁、验证函数或后续入口，需要从受保护的工作流版本执行验证。
摘要不说明内容没有缺陷。审阅过的版本、可变标签、默认分支及本地修改需各自标识清楚。

## 查找可以绕开发行输入的路径

- 解析私有包时核对命名空间与注册表映射；查明同名公共包或传递依赖能否覆盖预期来源。
- 核对锁文件能否约束实际安装器、所有平台与传递依赖；检查缺失依赖时是否回退到在线最新版本。
- 将 PR 检查与发布身份拆开。列出检出哪一提交、哪些钩子可执行、可写工作区与令牌权限。
- CI 动作、构建镜像和辅助脚本同样是依赖。检查实际解析的提交或镜像摘要，以及更新它的主体。
- 验签时把来源、构建者身份、工作流和产物摘要绑定到本轮预期；来源证明也需要可信验证入口。
- 对共享运行器、持久缓存和制品中转检查跨分支读写权限。缓存命中不应跳过内容校验。
- 若签名或部署可通过短期身份完成，核对签发条件中的仓库、引用和环境，避免测试作业继承发布权限。

## 用内存夹具验收

| 输入 | 预期 |
| --- | --- |
| 锁中存在的包名、版本、平台；字节与摘要匹配 | 返回同一份 bytes |
| 缓存换成其他合成字节并附带自己的摘要 | 验证仍以发布锁为准，拒绝选用 |
| 已锁定版本，平台改为未审阅目标 | 查表失败，不进入后续消费步骤 |
| 缓存传入可变 bytearray 或超长输入 | 校验入口拒绝 |
| 未受信分支尝试写发布锁 | 在宿主权限边界被拒绝，取得脱敏的策略或测试记录 |

## 容易误判和待取证据

仅发现测试工程中存在安装脚本，还需查明它是否在具有凭据或可写产物的上下文运行。
反之，构建时不持有发布令牌，仍可能污染下一阶段自动签名的制品。
保存解析后的依赖标识、锁来源、工作流触发条件、实际执行身份与产物摘要。
本地用字节串验证选择函数，无需下载、安装或执行待审包。核对项目实际安装器版本后再判断锁语义。

发布失败时的外部错误展示见[错误处理](error-handling.md)。

平台资料：[Python 消息摘要接口](https://docs.python.org/3/library/hashlib.html)。
