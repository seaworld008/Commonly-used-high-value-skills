---
name: rust-engineer
description: 'Implement and review Rust code: ownership, typed errors, trait contracts, async cancellation, unsafe/FFI invariants, API compatibility, and measured performance.'
zh_description: "用于 Rust 实现与审查：分析所有权和错误类型、设计 trait 与异步取消、核对 unsafe/FFI 不变量、兼容性和性能证据。"
version: "1.1.0"
author: "seaworld008"
source: "in-house"
source_url: ""
license: "MIT"
tags: ["development", "engineer", "rust"]
created_at: "2026-11-17"
updated_at: "2026-11-17"
quality: 4
complexity: "intermediate"
---

# Rust 实现与审查

本技能由 seaworld008 在本仓库独立编写，以 MIT 发布；版本号描述本地技能，不代表任何外部项目的发布。

## 触发条件

适用于 Rust 功能实现、编译错误定位、库 API 审查、并发任务生命周期检查，以及有基准数据的性能改进。
输入以具体代码、失败诊断、调用方式及兼容性约束为主；仅解释其他语言或安装工具链时无需加载本技能。

## 核心工作流

1. 先定位相关 crate 的 `Cargo.toml`、`Cargo.lock`、`rust-toolchain.toml`（或 `rust-toolchain`）、CI 与现有测试，确认 edition、MSRV、features、target 和运行时。
2. 沿调用链列出资源归属：谁创建、谁借用、谁能修改、何时释放；检查正常、错误、取消和 panic 四种退出路径。
3. 给出能复现问题的最小输入，先运行相关测试或编译失败用例，再修改职责最明确的一层。
4. 保持项目既有工具链与依赖策略；不自动升级 edition、提高 MSRV、放宽 trait 或加入运行时来消除报错。
5. 对比修改前后的公开签名、可观察行为和测试结果，说明仍缺哪些平台、版本或动态检查证据。

## 所有权与借用：先确定数据寿命

- 返回引用时指出它来自哪个输入；生命周期参数表达约束，不会延长局部变量或临时值的寿命。
- 同一数据的共享读取与排他修改必须满足借用约束。优先缩短借用范围、分离字段或调整处理顺序。
- 若结果必须独立于输入存在，拥有数据才合理；说明复制的大小和频率。`clone` 是语义与成本选择，不是借用报错的通用修复。
- `Arc` 只提供共享所有权，不自动提供内部可变性或消除数据竞争；`Mutex` 需要明确锁范围、锁顺序和失败策略。
- 审查 `RefCell` 的运行时借用失败、迭代中修改容器、跨 `await` 保存 guard，以及自引用结构的移动风险。

### 原创示例：借用解析、类型化错误与最小 trait

返回值借用输入键名；格式错误和数字错误可分别匹配，底层解析错误保留在错误链中。
`Sink` 只要求一次写入，不要求无关的 `Clone`、`Send`、`Sync` 或静态生命周期。
实现必须遵守“错误时不写入”的契约；trait 声明本身不能替实现证明这件事。

```rust
// example: borrowed_record
use std::error::Error;
use std::fmt;
use std::num::ParseIntError;

#[derive(Debug, PartialEq)]
struct Record<'a> {
    key: &'a str,
    count: u32,
}

#[derive(Debug)]
enum RecordError {
    MissingSeparator,
    EmptyKey,
    InvalidCount(ParseIntError),
}

impl fmt::Display for RecordError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingSeparator => write!(f, "missing equals sign"),
            Self::EmptyKey => write!(f, "empty record key"),
            Self::InvalidCount(e) => write!(f, "invalid record count: {e}"),
        }
    }
}

impl Error for RecordError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::InvalidCount(e) => Some(e),
            _ => None,
        }
    }
}

fn parse_record(input: &str) -> Result<Record<'_>, RecordError> {
    let (key, value) = input.split_once('=')
        .ok_or(RecordError::MissingSeparator)?;
    if key.is_empty() {
        return Err(RecordError::EmptyKey);
    }
    let count = value.parse().map_err(RecordError::InvalidCount)?;
    Ok(Record { key, count })
}

trait Sink {
    type Error;
    // On Err, the sink must retain its previous state.
    fn write(&mut self, record: &Record<'_>) -> Result<(), Self::Error>;
}

fn deliver<S: Sink>(sink: &mut S, record: &Record<'_>) -> Result<(), S::Error> {
    sink.write(record)
}

struct Budget(u32);
impl Sink for Budget {
    type Error = &'static str;
    fn write(&mut self, record: &Record<'_>) -> Result<(), Self::Error> {
        let remaining = self.0.checked_sub(record.count).ok_or("over budget")?;
        self.0 = remaining;
        Ok(())
    }
}

#[test]
fn borrows_key_and_delivers() {
    let input = String::from("jobs=3");
    let record = parse_record(&input).unwrap();
    assert_eq!(record.key.as_ptr(), input.as_ptr());
    let mut budget = Budget(5);
    assert_eq!(deliver(&mut budget, &record), Ok(()));
    assert_eq!(budget.0, 2);
}

#[test]
fn rejects_bad_input_with_distinct_errors() {
    assert!(matches!(parse_record("jobs"), Err(RecordError::MissingSeparator)));
    assert!(matches!(parse_record("=2"), Err(RecordError::EmptyKey)));
    for input in ["jobs=-1", "jobs=x", "jobs=4294967296"] {
        let error = parse_record(input).unwrap_err();
        assert!(matches!(error, RecordError::InvalidCount(_)));
        assert!(error.source().is_some());
    }
}

#[test]
fn failed_delivery_preserves_state() {
    let mut budget = Budget(2);
    let record = parse_record("jobs=3").unwrap();
    assert_eq!(deliver(&mut budget, &record), Err("over budget"));
    assert_eq!(budget.0, 2);
}

#[test]
fn accepts_count_limits() {
    assert_eq!(parse_record("jobs=0").unwrap().count, 0);
    assert_eq!(parse_record("jobs=4294967295").unwrap().count, u32::MAX);
    assert!(matches!(parse_record("jobs="), Err(RecordError::InvalidCount(_))));
}
```

反例应得到 `E0502`：后续仍使用共享借用时，不能对同一容器进行排他修改。
修复时先判断能否先使用 `first` 再 `push`；若业务需要独立快照，再有意识地拥有一份数据。

```rust,compile_fail
// example: overlapping_borrows
fn main() {
    let mut names = vec![String::from("alpha")];
    let first = &names[0];
    names.push(String::from("beta"));
    println!("{first}");
}
```

## 错误类型与 trait 边界

- 库边界按调用者是否需要恢复来区分错误；格式、权限、重试条件和内部缺陷不应只剩同一条字符串。
- `?` 传播已有失败；用 `From` 或明确的 `map_err` 转换时保留有用的原因和上下文，日志避免泄露输入秘密。
- `unwrap`、`expect` 适用于测试或可证明的不变量；对用户输入、网络失败、锁中毒等运行时失败给出明确策略。
- 泛型静态分发适合保留具体类型和编译期约束；`dyn Trait` 适合异构集合或运行时边界，先核对 dyn 兼容性和分配成本。
- 将 `Send`、`Sync`、生命周期约束放到确实跨线程或被运行时保存的位置。异步返回值、关联类型和错误类型也可能影响这些边界。
- 审查孤儿规则、公开关联类型、blanket impl 的重叠与下游实现者；新增要求或 impl 可能破坏既有调用者。

反例应得到 `E0277`：`Rc` 不能通过 `thread::spawn` 移交到另一线程。
若任务可以留在当前线程，应改变调度方式；只有确实需要线程共享所有权且内部数据约束满足时才考虑 `Arc`。

```rust,compile_fail
// example: non_send_thread
use std::rc::Rc;
fn main() {
    let value = Rc::new(7);
    std::thread::spawn(move || println!("{value}"));
}
```

## async 取消与结构化并发

先识别项目现有 executor，记录每个任务的 owner、完成结果去向、取消信号和退出等待位置。
把子任务放入有界作用域或项目已有的任务集合；限制并发数、队列容量和外部资源占用。
超时表示调用者停止等待，不天然表示外部副作用停止；重试前考虑幂等键、事务状态和重复提交。

- 检查每个 `await` 前后已发生的状态变化；future 被丢弃后，已消费的输入、部分写入和锁保护状态是否仍满足契约。
- `select` 的未胜出分支可能被丢弃；按具体 API 核实取消安全性，需要持续进度时将状态提升到分支之外。
- 不让阻塞 I/O 或 CPU 长循环占住运行时工作线程。用现有阻塞任务设施或受控线程，并给长操作合作式停止点。
- 已使用 Tokio 时，丢弃 `JoinHandle` 会失去等待入口，任务仍可能继续；显式管理 handle 的所有权。
- Tokio 的 `abort` 是取消请求，应等待并检查终止结果；取消通常需要到可让出执行的边界，已运行的阻塞任务不能保证被立即停止。
- 跨 `await` 持锁可能产生死锁或拖慢其他任务，即使编译通过也需检查。先取出最小快照再释放锁，或用专门任务管理资源。

### 原创示例：用 std 展示取消协议与退出等待

这是同步线程的生命周期示例，不模拟 executor。`thread::scope` 需要 Rust 1.63 或更新版本；
旧 MSRV 项目应选用其已有方案，而不是为了复制示例提高 MSRV。
每个子任务有边界清楚的输入；失败后请求其他任务停止，并显式收集所有 handle 的结果。
示例只接受两块工作，避免按输入无限创建线程。`Relaxed` 足够，因为标志只传递停止意图，不发布其他数据。

```rust
// example: scoped_cancellation
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;

#[derive(Debug, PartialEq)]
enum WorkError { Cancelled, Rejected, Overflow, Panicked }

fn bounded_sum(parts: [&[u8]; 2], cancel: &AtomicBool) -> Result<u64, WorkError> {
    thread::scope(|scope| {
        let mut handles = Vec::new();
        for part in parts {
            handles.push(scope.spawn(move || {
                if cancel.load(Ordering::Relaxed) {
                    return Err(WorkError::Cancelled);
                }
                let mut sum = 0_u64;
                for &value in part {
                    if cancel.load(Ordering::Relaxed) {
                        return Err(WorkError::Cancelled);
                    }
                    if value == 255 {
                        cancel.store(true, Ordering::Relaxed);
                        return Err(WorkError::Rejected);
                    }
                    sum = match sum.checked_add(u64::from(value)) {
                        Some(next) => next,
                        None => {
                            cancel.store(true, Ordering::Relaxed);
                            return Err(WorkError::Overflow);
                        }
                    };
                }
                Ok(sum)
            }));
        }
        let mut total = 0_u64;
        let mut failure = None;
        for handle in handles {
            let result = match handle.join() {
                Ok(result) => result,
                Err(_) => Err(WorkError::Panicked),
            };
            match result {
                Ok(sum) => match total.checked_add(sum) {
                    Some(next) => total = next,
                    None => {
                        cancel.store(true, Ordering::Relaxed);
                        failure = Some(WorkError::Overflow);
                    }
                },
                Err(error) => {
                    cancel.store(true, Ordering::Relaxed);
                    // Preserve the first substantive failure over cancellation.
                    if failure.is_none() || failure == Some(WorkError::Cancelled) {
                        failure = Some(error);
                    }
                }
            }
        }
        failure.map_or(Ok(total), Err)
    })
}

#[test]
fn completes_both_workers() {
    assert_eq!(bounded_sum([&[1, 2], &[3, 4]], &AtomicBool::new(false)), Ok(10));
}

#[test]
fn honours_preexisting_cancel() {
    assert_eq!(bounded_sum([&[1], &[2]], &AtomicBool::new(true)), Err(WorkError::Cancelled));
    assert_eq!(bounded_sum([&[], &[]], &AtomicBool::new(true)), Err(WorkError::Cancelled));
}

#[test]
fn joins_after_domain_failure() {
    let cancel = AtomicBool::new(false);
    assert_eq!(bounded_sum([&[255], &[1, 2]], &cancel), Err(WorkError::Rejected));
    assert!(cancel.load(Ordering::Relaxed));
}
```

验收时增加真实运行时的取消、超时、panic 和部分 I/O 用例，确认没有遗留任务或重复副作用。
这个 std 示例仅验证两线程聚合与合作式取消；不能据此声称已经验证 Tokio 或硬实时停止上界。

## unsafe 与 FFI：逐项核对不变量

每个 unsafe 边界列出指针来源、分配范围、初始化、对齐、别名、有效期和线程约束。
检查调用方到被调用方的整条链；`SAFETY` 注释是待核对的论证摘要，编译成功或有注释都不是证明。
FFI 还需明确 ABI、整数宽度、结构布局、所有权移交和释放函数配对；不要把 Rust 的 `Vec`、`String` 或 trait object 当成 C ABI 数据。
禁止跨不支持展开的 ABI 传播 panic；转换错误码时不要声称能捕获 UB 或所有 abort。

### 原创示例：外部字节缓冲区的 Rust 侧快照

空指针与长度检查只能排除部分错误。以下函数保留为 `unsafe`，因为无法通过数值检查验证任意地址是否可读。
空长度约定允许空指针；非空指针的有效性仍由调用者证明。返回的是独立快照，外部缓冲区无需被 Rust 释放。

```rust
// example: foreign_snapshot
#[derive(Debug, PartialEq)]
enum BufferError { Null, TooLong }

/// Copy an externally owned buffer into Rust ownership.
///
/// # Safety
/// For nonzero len within isize::MAX, a non-null ptr must designate len
/// initialized bytes in one live allocation, readable for this call.
/// No thread or callback may mutate those bytes while they are read.
unsafe fn snapshot(ptr: *const u8, len: usize) -> Result<Vec<u8>, BufferError> {
    if len == 0 {
        return Ok(Vec::new());
    }
    if ptr.is_null() {
        return Err(BufferError::Null);
    }
    if len > isize::MAX as usize {
        return Err(BufferError::TooLong);
    }
    // SAFETY: the caller supplies the live, initialized, immutable allocation;
    // the guards above exclude null, empty and oversized slice construction.
    let bytes = unsafe { std::slice::from_raw_parts(ptr, len) };
    Ok(bytes.to_vec())
}

#[test]
fn copies_without_taking_foreign_ownership() {
    let mut foreign = vec![10_u8, 20];
    // SAFETY: foreign remains live and no mutation occurs during the call.
    let owned = unsafe { snapshot(foreign.as_ptr(), foreign.len()) }.unwrap();
    foreign[0] = 99;
    assert_eq!(owned, vec![10, 20]);
    assert_eq!(foreign, vec![99, 20]);
}

#[test]
fn rejects_checkable_errors_without_dereference() {
    // SAFETY: these inputs return before reading any address.
    unsafe {
        assert_eq!(snapshot(std::ptr::null(), 0), Ok(Vec::new()));
        assert_eq!(snapshot(std::ptr::null(), 1), Err(BufferError::Null));
        let byte = 1_u8;
        assert_eq!(snapshot(&byte, usize::MAX), Err(BufferError::TooLong));
    }
}
```

不要用悬垂或伪造地址运行普通负向测试：那可能触发 UB，而不是可靠地返回错误。
对安全包装层测试其状态机；使用项目已有的 Miri、sanitizer 或 C harness 时分别记录覆盖范围。
这些工具能发现部分缺陷，不能替代对所有权、别名与外部调用约束的论证。

## API 兼容、MSRV 与 feature/target 矩阵

| 维度 | 从项目取值 | 验收证据 |
| --- | --- | --- |
| Rust 版本 | `rust-version`、工具链文件、CI 声明 | 支持的最低版本和常用版本实际编译；缺版本注明未测 |
| Features | 默认、无默认、受支持的组合 | 检查条件编译、可选依赖、错误类型和公开 API 是否可达 |
| Target | 已承诺的平台与架构 | 区分交叉 `check`、链接和实际运行；不把三者混同 |
| API | 下游调用方式、公开签名、错误/序列化契约 | 运行下游样例与文档测试，列出破坏性变化 |

新增 enum variant、改变 auto trait、trait 新增必需方法、收紧泛型约束或改变 feature 默认值，都需要评估下游兼容性。
`--all-features` 不代表所有组合，互斥 feature 不应硬拼在一起；先按项目已支持的组合生成矩阵。
跨平台检查还应看路径编码、整数转换、原子能力、大小端与 `cfg` 分支，避免只在当前机器成立。

以下命令使用项目当前工具链，按相关 crate 和既有支持矩阵选择，不照抄成无条件全量任务：

```sh
rustc --version
cargo --version
cargo check --locked --offline
cargo test --locked --offline
cargo test --doc --locked --offline
cargo check --no-default-features --locked --offline
```

对指定 feature、package、target，使用项目已有值补充对应参数；工具链选择沿用仓库约定。
离线缺依赖、缺 target 标准库或缺已安装的 fmt/clippy 等组件时记录命令和缺项；不联网安装、不全局改配置。
如果无法运行测试，仍可交付静态审查，但不能把编译推断记成运行通过。

## 测量后做性能优化

1. 固定工作负载、输入分布、release/profile 配置和指标；分别记录吞吐、尾延迟、分配量或峰值内存，保留正确性基线。
2. 使用项目已有基准与分析器定位热点；先区分 I/O 等待、锁争用、重复分配与算法复杂度，避免仅凭代码外观改成 unsafe。
3. 一次改变一个因素，记录样本数、噪声、编译器/target 和数据规模；对比端到端收益，检查最坏输入和回归。
4. 只有证据支持时才引入缓存、批处理、布局调整或更低层实现；将维护成本和目标平台差异一起说明。

## 正反验收与交付

- 正向：正常输入、边界长度、空值、错误传播及恢复路径满足约定；资源在成功和失败后均有明确 owner。
- 反向：借用和跨线程约束由编译失败用例检查；解析失败不写入，取消后不遗留未管理的工作，FFI 不接受未经证明的非空地址。
- 文档中的三个 `rust` 代码块均为独立测试单元，两个 `rust,compile_fail` 代码块应被编译器拒绝；不把拒绝编译算作测试环境故障。
- 本仓库用 `python -m pytest -q tests/test_original_rust_examples.py` 提取原样示例，使用本地 rustc 编译并运行，不下载依赖。
- 报告列出修改的 API、主要不变量、实际运行的命令/版本/矩阵单元与关键结果；将静态推理、运行证据及未覆盖部分分别写清。

## 按需官方事实

- [引用与借用](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html)：核对共享读取、排他修改与引用有效性。
- [Cargo rust-version](https://doc.rust-lang.org/cargo/reference/rust-version.html)：确认项目声明的 MSRV 与已有兼容性约定。
- [Tokio JoinHandle](https://docs.rs/tokio/latest/tokio/task/struct.JoinHandle.html)：仅在项目已使用 Tokio 时核对 handle、取消与阻塞任务边界；以锁定依赖版本的文档为准。
