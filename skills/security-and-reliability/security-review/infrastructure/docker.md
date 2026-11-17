# Docker 构建产物与容器权限审查

Original local reference, Copyright (c)2026 seaworld008, MIT

## 数据流与攻击前提

构建上下文进入构建器，层与缓存进入镜像仓库，镜像再由运行平台加载。
业务请求进入进程后，还可能经挂载目录、网络或 Docker socket 到达宿主资源。
攻击者可能提交构建目录里的文件、控制依赖版本，或利用应用漏洞执行容器内命令。
构建机拥有的仓库凭据不能因此成为产物的一部分；运行身份也不能继承构建身份的权限。
先确认谁能修改 Dockerfile、上下文、基础镜像、启动参数和挂载；它们是不同边界。
“由服务器配置”不能证明可信：租户自定义部署参数和来自 PR 的 CI 参数仍可能由攻击者选择。

## 自写示例：上下文越界进入镜像

下例把整个上下文装入最终镜像，运行时还默认具有 root 身份。
若上下文含发布凭据，事后删除源目录文件不会清除已经发布的镜像层。

```dockerfile
FROM python:3.12-slim
WORKDIR /service
COPY . /service
CMD ["python", "app.py"]
```

修正示例假设交付物只有经过审阅的 `app.py` 与 `public/` 静态目录。
复制前须确认二者没有密钥、符号链接指向的非预期文件或调试转储。
示例标签便于阅读；发布时按项目支持的平台锁定经审阅的真实 digest，不填虚构 digest。

```dockerfile
FROM python:3.12-slim
WORKDIR /service
COPY --chown=0:0 app.py /service/app.py
COPY --chown=0:0 public/ /service/public/
RUN chmod -R go-w /service
USER 10001:10001
CMD ["python", "-B", "app.py"]
```

`COPY` 的显式源拒绝把上下文的任意其他文件装入产物。
root 拥有应用文件且普通运行用户不能修改它们，减少代码落地后的持久化机会。
应用需要写文件时，只为独立数据目录授予权限，不把整个 `/service` 改成可写。
这段 Dockerfile 不包含运行时隔离设置；不能据此宣称网络或宿主挂载已经受限。

## 需要在部署代码中拒绝的能力

- 拒绝租户把 `/var/run/docker.sock`、宿主根目录、设备节点挂入业务容器。
- 拒绝未经逐项论证的 `--privileged`、host PID、host network 与额外 Linux capabilities。
- 在运行定义中设置只读根文件系统、非 root 用户、`no-new-privileges` 和所需的最小能力集。
- 为临时写入使用有容量上限的独立临时卷；限制内存、CPU、进程数和日志增长。
- 出站网络只开放业务所需目的地；同网段、云元数据和控制平面不能因“内网”自动放行。
- 依赖下载所需 secret 使用构建器的临时 secret 挂载，不能写入 `ARG`、`ENV` 或复制层。
- secret 挂载只隐藏注入方式；执行的下载脚本仍能读取并外传它，须审阅脚本和目的地。

## 正反验收输入

| 输入或条件 | 应观察到的结果 |
| --- | --- |
| 在上下文放入无敏感值的 `fixture-private.txt` | 最终镜像所有层中都没有该文件 |
| 正常 `app.py` 与公开静态文件 | 非 root 进程能读取并启动所需代码 |
| 进程尝试改写 `/service/app.py` | 写入失败，应用代码不变 |
| 租户请求 Docker socket 挂载或 privileged | 部署接口拒绝，不能仅在 UI 隐藏选项 |
| 临时目录写满或派生过多进程 | 达到预设限制，其他租户仍可工作 |

镜像层检查只使用专用假凭据；发现真实密钥时先限制访问并轮换，报告不附原值。
构建、拉取、推送和容器启动均须在获授权的隔离环境进行，本指南不自动执行它们。

## 易误报与适用边界

root 构建阶段安装系统包并不等于运行容器以 root 执行业务。
可写数据库卷并非天然漏洞；要核对卷的宿主范围、租户归属和写入身份。
镜像中出现公开证书不等于私钥泄漏；检查内容类型和实际用途。
非 root 不能阻止所有内核漏洞，也不能替代宿主补丁、seccomp 或平台隔离。
此示例适合简单 Python 产物；依赖编译、多阶段构建和其他发行版须另审 ABI 与文件集。

## 实际验证证据

保留镜像 digest、构建来源提交、最终文件清单与运行定义的脱敏版本。
记录 UID/GID、挂载类型及目标、能力、网络策略和资源上限的实际生效值。
分别证明构建 secret 未进入层或日志，以及运行进程不能触达不应访问的宿主资源。
静态 Dockerfile 检查不能验证运行编排覆盖了哪些参数，也不能证明基础镜像无漏洞。

## 官方接口核对入口

- [Dockerfile 指令](https://docs.docker.com/reference/dockerfile/)
- [运行容器的选项](https://docs.docker.com/engine/containers/run/)
- [构建 secret](https://docs.docker.com/build/building/secrets/)

先核对项目实际 Docker Engine、BuildKit 与编排平台版本；本例未承诺所有平台支持相同隔离选项。
