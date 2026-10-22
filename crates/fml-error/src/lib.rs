//! 不背公式（BubeiGongshi）全领域共享的错误模型。
//!
//! 提供注册表驱动的错误码（ErrorCode）、诊断（Diagnostic）、追踪标识（TraceId）与一次
//! 失败（FmlError）。错误码、级别、可重试、消息键、surface 与 HTTP 状态全部来自
//! contracts/errors/registry.yaml，由 tools/ci/gen_errors.py 生成 codes.rs；手写代码只
//! 消费生成结果，不另行登记码表。
//!
//! # 边界
//!
//! 只做错误码元数据的运行时视图与错误值的构造、序列化与校验；不做日志、不做 I/O、
//! 不读文件与网络、不依赖 UI 或解析 crate（CORE-01 依赖方向）。消息文案在
//! app/lib/l10n/errors_zh.arb，本 crate 只给出消息键。
//!
//! # 线程模型
//!
//! 全部类型均为 Send + Sync 的纯值类型，可在任意线程构造与传递；无全局可变状态、
//! 无锁、无内部缓存。
//!
//! # 错误语义
//!
//! 注册表缺码与字段越界属构建期错误，由生成器以非零退出码报告。运行期错误值是数据
//! 而非 panic 源：未知码解析返回 UnknownErrorCode，与注册表不一致的 domain、
//! retryable、severity、recovery 在序列化与反序列化时都拒绝。追踪标识全零表示“本次
//! 调用尚未填入”，只允许在领域内往返，传输边界必须填入真实值。
//!
//! # 当前状态
//!
//! CORE-02 阶段1：错误模型、注册表、生成器与 contracts/vectors/errors-v1.json 已交付；
//! Dart 侧 FmlException 与 DiagnosticDto 属阶段2（CORE-67 之后）。

#![forbid(unsafe_code)]
#![deny(missing_docs)]

use std::collections::BTreeMap;
use std::fmt;

use serde::de::Error as _;
use serde::ser::Error as _;
use serde::{Deserialize, Deserializer, Serialize, Serializer};

pub mod codes;

pub use codes::{ErrorCode, UnknownErrorCode};

/// 追踪标识的字节数，文本形式固定为 32 位小写十六进制。
const TRACE_ID_BYTES: usize = 16;

/// trace_id 文本格式错误的提示，序列化与反序列化共用。
const TRACE_FORMAT_ERROR: &str = "trace_id 必须是 32 位小写十六进制字符串";

/// 一次调用链的追踪标识；全零表示本次调用尚未填入。
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub struct TraceId(pub [u8; TRACE_ID_BYTES]);

impl TraceId {
    /// 是否为全零值（尚未填入追踪标识）。
    pub fn is_zero(self) -> bool {
        self.0.iter().all(|byte| *byte == 0)
    }
}

impl fmt::Display for TraceId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for byte in self.0 {
            write!(f, "{byte:02x}")?;
        }
        Ok(())
    }
}

impl Serialize for TraceId {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.collect_str(self)
    }
}

impl<'de> Deserialize<'de> for TraceId {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let text = String::deserialize(deserializer)?;
        parse_trace_id(&text)
            .map(TraceId)
            .ok_or_else(|| D::Error::custom(TRACE_FORMAT_ERROR))
    }
}

/// 解析 32 位小写十六进制文本为 16 字节；长度、大小写或字符不符返回 None。
fn parse_trace_id(text: &str) -> Option<[u8; TRACE_ID_BYTES]> {
    let bytes = text.as_bytes();
    if bytes.len() != TRACE_ID_BYTES * 2
        || !bytes
            .iter()
            .all(|byte| matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
    {
        return None;
    }
    let mut id = [0u8; TRACE_ID_BYTES];
    for (index, byte) in id.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&text[index * 2..index * 2 + 2], 16).ok()?;
    }
    Some(id)
}

/// 诊断级别，与注册表的 severity 列一一对应；线上格式为小写单词。
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    /// 失败：当前操作无法继续，调用方按修复建议修正后重试。
    Error,
    /// 警告：结果可用但可能不符合预期，界面提示后即可继续。
    Warning,
    /// 提示：纯信息性诊断，不影响结果。
    Info,
}

/// 一条诊断：错误码加可选的定位、参数与修复建议。
///
/// 线上字段顺序固定为 code、severity、node_path、input_range、args、recovery、
/// needs_confirm，可选字段为 None 时省略。input_range 是源文本的 UTF-8 半开字节区间
/// [start, end)，要求 start <= end。
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Diagnostic {
    /// 诊断自身的错误码。
    pub code: ErrorCode,
    /// 诊断级别，必须等于 code.severity()。
    pub severity: Severity,
    /// 出错节点在 AST 中的路径（如 /root/args/0）。
    pub node_path: Option<String>,
    /// 源文本中出错部分的 UTF-8 半开字节区间。
    pub input_range: Option<(u32, u32)>,
    /// 消息模板的位置参数，按键升序存放。
    pub args: BTreeMap<String, String>,
    /// 修复建议消息键：只对 fix_hint 为 true 的码可用，且等于 message_key 加 .fix。
    pub recovery: Option<String>,
    /// 应用这条修复建议前是否需要用户确认。
    pub needs_confirm: bool,
}

impl Diagnostic {
    /// 与注册表比对：级别、区间顺序与修复建议派生规则。
    fn validate(&self) -> Result<(), &'static str> {
        if self.severity != self.code.severity() {
            return Err("diagnostic.severity 必须等于该码在注册表中的 severity");
        }
        if let Some((start, end)) = self.input_range
            && start > end
        {
            return Err("input_range 必须是 start <= end 的 UTF-8 半开字节区间");
        }
        match &self.recovery {
            None => Ok(()),
            Some(_) if !self.code.fix_hint() => Err("该码未声明 fix_hint，不得给出 recovery"),
            Some(recovery) if *recovery == format!("{}.fix", self.code.message_key()) => Ok(()),
            Some(_) => Err("recovery 必须等于该码的 message_key 加 .fix"),
        }
    }
}

/// Diagnostic 的线上格式，字段顺序即规范字节顺序，未声明的键拒绝。
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct DiagnosticWire {
    code: ErrorCode,
    severity: Severity,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    node_path: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    input_range: Option<(u32, u32)>,
    #[serde(default)]
    args: BTreeMap<String, String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    recovery: Option<String>,
    #[serde(default)]
    needs_confirm: bool,
}

impl Serialize for Diagnostic {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        self.validate().map_err(S::Error::custom)?;
        DiagnosticWire {
            code: self.code,
            severity: self.severity,
            node_path: self.node_path.clone(),
            input_range: self.input_range,
            args: self.args.clone(),
            recovery: self.recovery.clone(),
            needs_confirm: self.needs_confirm,
        }
        .serialize(serializer)
    }
}

impl<'de> Deserialize<'de> for Diagnostic {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let wire = DiagnosticWire::deserialize(deserializer)?;
        let diagnostic = Self {
            code: wire.code,
            severity: wire.severity,
            node_path: wire.node_path,
            input_range: wire.input_range,
            args: wire.args,
            recovery: wire.recovery,
            needs_confirm: wire.needs_confirm,
        };
        diagnostic.validate().map_err(D::Error::custom)?;
        Ok(diagnostic)
    }
}

/// 一次失败：错误码加注册表派生的域与可重试标记，附带诊断与追踪标识。
///
/// 字段声明顺序即规范序列化顺序；domain 与 retryable 只能由 code 派生（FmlError::new），
/// 不提供覆盖它们的构造器或方法。诊断参数可能含用户原文，只在数据里存在，不进 Display。
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FmlError {
    /// 错误码，语义、级别与 surface 由注册表定义。
    pub code: ErrorCode,
    /// 调度域，必须等于 code.domain()。
    pub domain: String,
    /// 是否可重试，必须等于 code.retryable()。
    pub retryable: bool,
    /// 本次调用的追踪标识；领域内可为全零，传输边界必须是真实值。
    pub trace_id: TraceId,
    /// 诊断列表，保持发生顺序。
    pub diagnostics: Vec<Diagnostic>,
}

impl FmlError {
    /// 按注册表元数据构造错误：域与可重试取生成值，无诊断，追踪标识为全零。
    pub fn new(code: ErrorCode) -> Self {
        Self {
            code,
            domain: code.domain().to_owned(),
            retryable: code.retryable(),
            trace_id: TraceId::default(),
            diagnostics: Vec::new(),
        }
    }

    /// 追加一条诊断，保持追加顺序，不改外层 code。
    #[must_use]
    pub fn with_diagnostic(mut self, diagnostic: Diagnostic) -> Self {
        self.diagnostics.push(diagnostic);
        self
    }

    /// 填入本次调用的追踪标识；仅当当前仍为全零值时生效，非零不覆盖。
    #[must_use]
    pub fn with_trace(mut self, trace_id: TraceId) -> Self {
        if self.trace_id.is_zero() {
            self.trace_id = trace_id;
        }
        self
    }

    /// 与注册表比对：域与可重试必须由 code 派生。
    fn validate(&self) -> Result<(), &'static str> {
        if self.domain != self.code.domain() {
            return Err("domain 必须等于该码在注册表中的 domain");
        }
        if self.retryable != self.code.retryable() {
            return Err("retryable 必须等于该码在注册表中的 retryable");
        }
        Ok(())
    }
}

impl From<ErrorCode> for FmlError {
    fn from(code: ErrorCode) -> Self {
        Self::new(code)
    }
}

impl fmt::Display for FmlError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} (trace_id {})", self.code, self.trace_id)
    }
}

impl std::error::Error for FmlError {}

/// FmlError 的线上格式，字段顺序即规范字节顺序，未声明的键拒绝。
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct FmlErrorWire {
    code: ErrorCode,
    domain: String,
    retryable: bool,
    trace_id: TraceId,
    #[serde(default)]
    diagnostics: Vec<Diagnostic>,
}

impl Serialize for FmlError {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        self.validate().map_err(S::Error::custom)?;
        FmlErrorWire {
            code: self.code,
            domain: self.domain.clone(),
            retryable: self.retryable,
            trace_id: self.trace_id,
            diagnostics: self.diagnostics.clone(),
        }
        .serialize(serializer)
    }
}

impl<'de> Deserialize<'de> for FmlError {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let wire = FmlErrorWire::deserialize(deserializer)?;
        let error = Self {
            code: wire.code,
            domain: wire.domain,
            retryable: wire.retryable,
            trace_id: wire.trace_id,
            diagnostics: wire.diagnostics,
        };
        error.validate().map_err(D::Error::custom)?;
        Ok(error)
    }
}
