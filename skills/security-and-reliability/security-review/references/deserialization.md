# 外部字节到业务对象的反序列化审查

Original local reference, Copyright (c)2026 seaworld008, MIT

## 数据流与攻击前提

上传文件、Cookie、消息队列、缓存和数据库 blob 都可能成为反序列化器的输入。
攻击者可能控制完整字节、某些字段、类型标签或被高权限 worker 读取的缓存条目。
“在服务器存储过”不消除原始输入的控制权；签名也只证明持钥方签过这些字节。
审查解码过程中是否执行构造器、导入模块、访问文件/网络，以及解码后能调用什么操作。

## 自写示例：外部输入恢复可执行对象

```python
import pickle

def unsafe_job(raw):
    return pickle.loads(raw)
```

危险发生在恢复对象期间，事后检查返回对象类型已经太晚；不要运行不可信 pickle 做验证。修正示例定义只含版本、数量与文字标签的 JSON 协议，不支持对象类型、回调或动态类。

```python
import json

def reject_constant(value):
    raise ValueError('non-finite number')

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result

def parse_job(raw):
    if type(raw) is not bytes or len(raw) > 4096:
        raise ValueError('invalid message size')
    try:
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                          parse_constant=reject_constant)
    except (ValueError, RecursionError) as error:
        raise ValueError('invalid message encoding') from error
    if type(data) is not dict or set(data) != {'version', 'count', 'label'}:
        raise ValueError('invalid shape')
    if type(data['version']) is not int or data['version'] != 1:
        raise ValueError('unsupported version')
    if type(data['count']) is not int or not 1 <= data['count'] <= 100:
        raise ValueError('invalid count')
    label = data['label']
    if type(label) is not str or not 1 <= len(label) <= 64:
        raise ValueError('invalid label')
    if any(ord(char) < 32 or ord(char) == 127 for char in label):
        raise ValueError('invalid label text')
    return {'version': 1, 'count': data['count'], 'label': label}
```

代码拒绝重复键、非有限数、未知字段、布尔数量和所有嵌套业务结构。结构检查在解析后完成；接收前的字节上限限制解析工作量，不能只在解析完成后限制大小。
若上游压缩或分块传输，须对解压/累计接收字节也施加上限，不能相信声明的长度。
`label` 仅是普通文字，不允许当模板、命令或路径执行；解码成功仍要检查任务主体权限。

## 不同格式需要拒绝的能力

- YAML/XML/其他对象格式核对实际解析器版本、类型构造器、外部实体和网络读取行为。
- 关闭不需要的对象恢复或外部引用；若无法禁用，应更换数据协议而非只过滤个别类名。
- 归档和模型文件可能封装对象加载、文件覆盖或巨大展开内容，应按内部格式逐层审查。
- 不把签名 pickle 当通用外部协议，签名者受控范围和密钥泄漏后的执行能力仍然危险。
- 不在解析失败后回退到 `eval`、pickle、宽松 YAML 或另一个可执行格式。
- 业务动作从固定枚举映射到处理函数，不把消息里的模块名、类名或方法名直接反射执行。

## 正反验收输入

| 输入 | 预期 |
| --- | --- |
| `{"version":1,"count":2,"label":"sample"}` 的 UTF-8 字节 | 返回三个规范字段 |
| 重复 count 键、NaN、无效 UTF-8 | 拒绝，不调度任务 |
| count 为 true、0、101、浮点数或字符串 | 拒绝，不隐式转换 |
| 多余 `class` 字段、嵌套 label 或未知 version | 拒绝，不尝试动态导入 |
| 超过 4096 字节或标签包含换行 | 拒绝，不截断后继续解析 |
| 字段正确但任务属于另一主体 | 业务授权拒绝，不因解析通过放行 |

负例使用无执行能力的假数据，不制作或加载会运行命令的 exploit 载荷。
## 易误报与适用边界

由同进程刚生成且不会被外界修改的对象快照与不可信网络输入风险不同，应证明来源约束。
JSON 本身不恢复 Python 类，但后续动态导入或任意字段合并仍可引入危险能力。
本例只支持很小的平面消息；大文档需要专门的流式解析、深度预算与资源隔离。

## 实际验证证据

记录每个输入来源、实际解析函数及参数、类型钩子和解码后接收点的调用链。
保留大小/重复键/类型错误验收结果，并证明失败路径没有入队、导入或其他副作用。
静态语法检查不能证明上游解压有界，也不能证明所有缓存和 worker 都采用同一解析器。
## 官方接口核对入口

- [Python JSON](https://docs.python.org/3/library/json.html)
- [Python pickle 的对象恢复语义](https://docs.python.org/3/library/pickle.html)

先核对当前项目 Python 和第三方解析器版本；不要凭函数名推断默认安全选项。
