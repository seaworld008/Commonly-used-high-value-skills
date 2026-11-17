# 从下载编号到已经打开的文件

Original local reference, Copyright (c)2026 seaworld008, MIT

报表服务收到下载编号，在租户目录中找文件，并把字节交给响应层。
上传者能填写原始文件名，导入任务也能在索引里留下名称。两个入口都可能影响后续下载。
若读取进程还有索引目录之外的权限，错误的名字解析会把业务授权扩大为文件系统读权限。

## 缺陷示例

先构造一个路径交给发送器。这里既没有核对文件归属，也没有约束 name 的解释方式。

```python
from pathlib import Path

def unsafe_download_path(directory, name):
    return Path(directory) / name
```

## 修正示例

在支持 dir_fd 与 O_NOFOLLOW 的 Unix 本地文件系统上，调用方持有私有报表目录的描述符。
lookup 只在当前主体获准读取该编号时返回服务生成的物理名称，否则返回 None。
存储端只发布写完的普通文件，目录条目只能由受控的存储进程创建。

```python
import os
import re
import stat

def read_report(directory_fd, lookup, actor, report_id):
    name = lookup(actor, report_id)
    if not isinstance(name, str) or not re.fullmatch(r"[0-9a-f]{32}", name):
        raise PermissionError("report unavailable")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open(name, flags, dir_fd=directory_fd)
    try:
        limit = 1024 * 1024
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError("unsupported report")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            body = stream.read(limit + 1)
        if len(body) > limit:
            raise ValueError("report too large")
        return body
    finally:
        os.close(fd)
```

单个名称消除了中间路径分量。检查与读取指向同一已打开对象，读取上限覆盖尺寸变化。
若其他主体可以放入硬链接、替换普通文件或修改内容，还需隔离写入权限和发布目录。
对象存储、Windows 和带重解析点的卷有各自的解析语义，应先验证项目所用平台的原语。

## 上传、解包和文档解析

- 把显示名与存储键分开。下载主动内容时审查实际响应类型、附件策略和提供内容的源。
- 归档先按成员类型与目标目录制定提取计划，拒绝越界名称、链接和设备项。限制成员数与实际解压字节。
- 遇到 XML、SVG 或办公室文档，追到具体解析器。外部实体、外部资源加载和模式解析可引发读文件或出站请求。
- 核对当前解析器版本及所有解析入口；用本地拒绝解析的替身验证外部引用不会触发读取。
- 扩展名或客户端声明的 MIME 类型只描述预期格式。处理不可信文件的转换任务需要自己的资源限额和权限。

## 验收与容易误判处

| 合成夹具 | 预期 |
| --- | --- |
| 已授权编号，物理名合法，内容为小报表 | 返回原字节 |
| 其他租户的编号 | lookup 返回 None，未打开文件 |
| 索引中出现带目录分隔符的物理名 | 打开前拒绝 |
| 合法物理名实际指向测试目录中的符号链接 | 打开失败，无目标内容返回 |
| 普通文件超过 1 MiB | 拒绝，响应层未收到文件字节 |

原始文件名仅作转义后的显示文本时，路径字符本身不能证明发生路径穿越。
取证应记录授权查询条件、已打开目录的来源、写入者、对象类型、拒绝阶段和响应头。
样例验收只需临时目录中的合成文件。文档转换器的出站边界另见[服务端请求](ssrf.md)。

平台资料：[Python 文件描述符与相对目录操作](https://docs.python.org/3/library/os.html#os.open)。
