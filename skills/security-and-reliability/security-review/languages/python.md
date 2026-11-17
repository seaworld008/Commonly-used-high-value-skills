# Python 文件、进程与对象边界审查

Original local reference, Copyright (c)2026 seaworld008, MIT

## 数据流与攻击前提

追踪请求中的文件标识、CLI 参数、任务载荷进入文件打开、子进程、SQL 和对象加载的位置。
路径拼接后仍可能含 `..`、绝对路径或符号链接；字符串前缀相同不证明位于同一目录。
攻击者也可能只拥有上传目录写权限，通过替换链接改变审核与读取之间的目标。
确认执行用户、目录所有者、挂载与后台 worker 身份；“来自服务器配置”不能跳过这一步。

## 自写示例：读取越过报告目录

```python
from pathlib import Path

def unsafe_read(name):
    return (Path('/srv/reports') / name).read_bytes()
```

修正示例适用于支持 `dir_fd` 和 `O_NOFOLLOW` 的 POSIX 平台。
`root_fd` 由服务启动时打开，指向经过权限审阅的报告目录，不能由请求指定。
目录内文件只由可信发布进程写入；攻击者可建硬链接或修改内容时须增加发布隔离。

```python
import os
import re
import stat

LIMIT = 64 * 1024

def read_report(root_fd, name):
    if type(name) is not str or not re.fullmatch(r'[a-z0-9_-]{1,40}\.txt', name):
        raise ValueError('invalid report name')
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open(name, flags, dir_fd=root_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > LIMIT:
            raise ValueError('not a bounded regular file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            content = stream.read(LIMIT + 1)
        if len(content) > LIMIT:
            raise ValueError('report too large')
        return content
    finally:
        os.close(fd)
```

名称语法拒绝分隔符与绝对路径，`O_NOFOLLOW` 拒绝末端符号链接。
`fstat` 检查已经打开的对象，避免先检查路径再打开造成的替换窗口。
`O_NONBLOCK` 避免误开 FIFO 时等待写入者；它不能让任意设备文件访问变得安全。
长度检查覆盖检查后文件增长；它不能保证并发写入时读到同一版本的完整内容。
调用方还须验证主体对这份报告的权限，文件名合法并不表示有权读取。

## 其他 Python 特有审查点

- SQL 值使用驱动参数绑定；排序列和表名通过固定映射选择，不能用值占位符代替标识符验证。
- `subprocess.run([...], shell=False)` 仍须限制程序及工具选项，避免可控 `cwd`、`env` 和插件配置。
- `pickle.load`、动态导入与 `eval` 可以构造执行能力，不能用来解析外部消息或上传附件。
- YAML、模板和 ORM 行为随库版本改变；核对当前项目实际 API，不假设某个默认值永远安全。
- `assert` 不能承担访问控制，优化运行模式可能移除它；使用显式条件和异常。
- `bool` 是 `int` 的子类，金额、数量验证若不接受布尔值应使用准确类型判断。
- 异常日志避免打印完整请求、数据库连接串和令牌；错误响应不暴露 traceback。
- 解压文件审查条目数、展开大小、路径、链接和覆盖行为，不能只检查压缩包文件名。

## 正反验收输入

| 输入或对象 | 预期 |
| --- | --- |
| `daily.txt`，内容是少量测试文字 | 返回原始字节 |
| `../private.txt`、`/etc/hosts`、`a/b.txt` | 在打开文件前拒绝 |
| 指向目录外的 `daily.txt` 符号链接 | 打开失败，不读取目标 |
| 名为 `daily.txt` 的 FIFO | 不等待写入，拒绝非普通文件 |
| 普通文件长度超过 65536 字节 | 拒绝，不返回截断成功结果 |
| 合法名字但属于其他租户 | 上层授权拒绝，不进入读取函数 |

仅在专用临时目录创建假报告和链接，不读取系统文件来证明越界。
权限错误、文件消失和不支持的标志应成为失败，不能回退到不受限的路径读取。

## 易误报与适用边界

`Path.resolve` 的出现不等于漏洞；当路径树不可变且所有者可信时，应评估真实竞态前提。
本例禁止子目录，不能直接用于允许任意层级上传目录的下载接口。
同一目录下的不同租户、硬链接、挂载变化与内容并发修改需要额外设计。
Windows 需使用该平台支持的文件句柄与重解析点控制，不能删掉标志后沿用结论。

## 实际验证证据

记录运行 Python/OS 版本、目录权限、fd 来源与符号链接/FIFO/超限用例结果。
证明拒绝发生在读出数据之前，并检查异常路径始终关闭文件描述符。
生产上的权限、挂载和并发发布机制仍须实际核验；本地语法通过不能证明它们成立。

## 官方接口核对入口

- [Python os 文件描述符 API](https://docs.python.org/3/library/os.html)
- [Python subprocess](https://docs.python.org/3/library/subprocess.html)
- [Python sqlite3 参数绑定](https://docs.python.org/3/library/sqlite3.html)
