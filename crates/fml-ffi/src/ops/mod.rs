//! Static op extension surface; no runtime registration and no business handlers yet.
use crate::abi::FmlHandle;
pub use crate::actor::{CloseReply, CloseTrigger, HandleActor, Lease};
use fml_error::{FmlError, TraceId};
use std::sync::atomic::{AtomicBool, Ordering};
/// Permitted invocation entry point.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OpMode {
    /// Fast synchronous call.
    Sync,
    /// Long job (phase two).
    Submit,
}
/// Routing policy, never inferred from a global account.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Scope {
    /// No profile context.
    None,
    /// Device-wide, no profile context.
    Device,
    /// Explicit profile handle required.
    Profile,
}
/// Handler output, with the success DTO encoded as JSON bytes.
pub enum OpReply {
    /// Valid JSON success DTO.
    Ok(Vec<u8>),
    /// Structured domain error; its existing trace is preserved.
    Err(FmlError),
}
/// A cooperative cancellation flag, independent of the AST crate.
#[derive(Default)]
pub struct CancelHandle(AtomicBool);
impl CancelHandle {
    /// Signal cancellation.
    pub fn cancel(&self) {
        self.0.store(true, Ordering::Release);
    }
    /// Read the cancellation signal.
    pub fn is_cancelled(&self) -> bool {
        self.0.load(Ordering::Acquire)
    }
}
/// Borrowed context valid only for this handler invocation.
pub struct OpCtx<'a> {
    /// Registered operation name.
    pub op: &'static str,
    /// Supported top-level DTO major version.
    pub dto: u32,
    /// Invocation mode.
    pub mode: OpMode,
    /// Declared routing scope.
    pub scope: Scope,
    /// Explicit profile handle, if any.
    pub handle: Option<FmlHandle>,
    /// Leased actor (neutral actor for unscoped operations).
    pub actor: &'a HandleActor,
    /// Invocation cancellation flag.
    pub cancel: &'a CancelHandle,
    /// Validated nonzero request trace.
    pub trace_id: TraceId,
    /// Budget only for names in BUDGET_OPS.
    pub budget_ms: Option<u32>,
}
/// Synchronous Rust handler surface; ABI exception isolation surrounds the call.
pub trait OpHandler: Send + Sync {
    /// Read body bytes without retaining context borrows.
    fn call(&self, ctx: &OpCtx<'_>, body: &[u8]) -> OpReply;
}
/// Immutable registration record; DTO version is not a second per-entry source.
pub struct OpEntry {
    /// Unique operation name.
    pub op: &'static str,
    /// Supported invocation mode.
    pub mode: OpMode,
    /// Routing scope.
    pub scope: Scope,
    /// Statically owned handler.
    pub handler: &'static dyn OpHandler,
}
/// Sole budget capability source. Fake implementations are debug/test-only.
pub const BUDGET_OPS: &[&str] = &["engine.parse", "calc.evaluate", "grade.answer"];
#[cfg(any(test, feature = "test_ops"))]
mod fake;
/// Compile-time operation table; production is empty until owner cards register ops.
#[cfg(any(test, feature = "test_ops"))]
pub static OPS: &[OpEntry] = fake::ENTRIES;
/// Compile-time operation table; no production business operations in phase one.
#[cfg(not(any(test, feature = "test_ops")))]
pub static OPS: &[OpEntry] = &[];
pub(crate) fn assert_unique() {
    for (i, entry) in OPS.iter().enumerate() {
        assert!(
            !OPS[..i].iter().any(|other| other.op == entry.op),
            "duplicate op"
        );
    }
}
#[cfg(test)]
mod tests {
    #[test]
    fn op_names_unique() {
        super::assert_unique();
    }
}
