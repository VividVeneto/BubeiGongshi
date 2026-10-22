//! 不背公式（BubeiGongshi）的全领域共享错误模型 crate。
//!
//! 边界：只承载错误码与错误类型，不做 I/O、不读时钟、不依赖任何其他 `fml-*` crate；
//! 所有领域 crate 都可以依赖本 crate（CORE-01 依赖方向的通用例外）。
//!
//! 线程模型：类型只做值传递，不持有锁、不启动线程、不缓存全局状态。
//!
//! 错误语义：错误值只描述失败原因与必要上下文，不携带 I/O 句柄、平台对象或时间戳；
//! 需要时间或输入数据时由调用方显式传入（`now_ms`、种子、文件内容）。
//!
//! 当前状态：CORE-01 只建立 crate 边界与 lint 骨架
//! （`forbid(unsafe_code)`、`deny(missing_docs)`），**不声明任何占位 API**。
//! 正式的错误码枚举与错误类型由 CORE-02 在 `contracts/errors/registry.yaml`
//! 登记后交付；在此之前引用本 crate 的公共项会编译失败，而不是拿到占位实现。

#![forbid(unsafe_code)]
#![deny(missing_docs)]
