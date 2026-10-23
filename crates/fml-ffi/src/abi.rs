//! The only C calling-convention surface. Every entry point contains unwinding.
use crate::{
    actor, buffer, jobs,
    ops::{CloseReply, CloseTrigger},
    runtime, trace,
};
use std::{
    ffi::{CStr, c_char, c_void},
    panic::{AssertUnwindSafe, catch_unwind},
};
/// Core-owned immutable buffer; free once with the unchanged triple.
#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct FmlBuf {
    /// Readable bytes until freed; never write through this pointer.
    pub ptr: *mut u8,
    /// Number of initialized bytes, without a NUL terminator.
    pub len: usize,
    /// Monotonic process-local allocation identity; zero means no allocation.
    pub allocation_id: u64,
}
impl Default for FmlBuf {
    fn default() -> Self {
        Self {
            ptr: std::ptr::null_mut(),
            len: 0,
            allocation_id: 0,
        }
    }
}
/// High 16 bits generation, low 48 bits slot.
pub type FmlHandle = u64;
/// Cross-thread callback; keep function and user_data alive until unregister succeeds.
// SAFETY: Invocation requires the registered callback lifetime and buffer ownership contract.
pub type FmlCompletion = Option<unsafe extern "C" fn(u64, FmlBuf, *mut c_void)>;

fn guard(f: impl FnOnce() -> i32) -> i32 {
    catch_unwind(AssertUnwindSafe(f)).unwrap_or(-5)
}
/// Effective ABI version, including the debug-only mismatch fixture.
// SAFETY: Unique unmangled symbol, matching the checked-in C header.
#[unsafe(no_mangle)]
pub extern "C" fn fml_abi_version() -> u32 {
    catch_unwind(|| (crate::ABI_MAJOR << 16) | crate::ABI_MINOR).unwrap_or(0)
}
/// Allocate capabilities JSON; a null buffer indicates allocation/panic failure.
// SAFETY: Unique unmangled symbol, matching the checked-in C header.
#[unsafe(no_mangle)]
pub extern "C" fn fml_capabilities() -> FmlBuf {
    catch_unwind(|| buffer::allocate(runtime::capabilities())).unwrap_or_default()
}
// SAFETY: Caller keeps readable op/request allocations alive until the owned copy completes.
unsafe fn input(
    op: *const c_char,
    req: *const u8,
    len: usize,
) -> Result<(String, Vec<u8>), runtime::Failure> {
    if op.is_null() || req.is_null() || len > 16 * 1024 * 1024 {
        return Err(runtime::failure(-1));
    }
    // SAFETY: Caller supplies a readable NUL-terminated op and len readable request bytes.
    let name = unsafe { CStr::from_ptr(op) }
        .to_str()
        .map_err(|_| runtime::failure(-1))?;
    // SAFETY: Validated nonnull and bounded length; allocation validity is a caller obligation.
    Ok((
        name.to_owned(),
        unsafe { std::slice::from_raw_parts(req, len) }.to_vec(),
    ))
}
/// Synchronous dispatch; returns 0, 1 or an FFI negative status.
/// # Safety
/// op/req must satisfy the header's readable lifetimes; out must be writable/aligned,
/// nonoverlapping with inputs. Null pointers are rejected, arbitrary invalid pointers are UB.
// SAFETY: Unique unmangled symbol, matching the checked-in C header.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn fml_call(
    op: *const c_char,
    req: *const u8,
    req_len: usize,
    out: *mut FmlBuf,
) -> i32 {
    let mut trace_id = None;
    let outcome = catch_unwind(AssertUnwindSafe(|| {
        if out.is_null() {
            return -1;
        }
        // SAFETY: Caller guarantees a writable aligned output, checked nonnull above.
        unsafe {
            out.write(FmlBuf::default());
        }
        // SAFETY: Forwarding caller obligations; input validates nullable/length conditions.
        let result = unsafe { input(op, req, req_len) }.and_then(|(name, bytes)| {
            runtime::parse(&bytes, &mut trace_id).and_then(|env| runtime::dispatch(&name, env))
        });
        let (status, bytes) = runtime::response(result, runtime::fallback_trace(trace_id));
        let buf = buffer::allocate(bytes);
        let status = if buf.ptr.is_null() && status >= 0 {
            -5
        } else {
            status
        };
        // SAFETY: Same caller-owned output, no retained reference to input/output.
        unsafe {
            out.write(buf);
        }
        status
    }));
    outcome.unwrap_or_else(|_| {
        // Nested containment handles errors in serialization/allocation during panic recovery.
        let _ = catch_unwind(AssertUnwindSafe(|| {
            if !out.is_null() {
                let (_, bytes) = runtime::response(
                    Err(runtime::failure(-5)),
                    trace_id.unwrap_or_else(trace::emergency),
                );
                // SAFETY: Nonnull output remains writable for the duration of the call.
                unsafe {
                    out.write(buffer::allocate(bytes));
                }
            }
        }));
        -5
    })
}
/// Copy and validate a submission, then admit it without waiting for the handler.
/// # Safety
/// Same input obligations as fml_call; job_id is writable/aligned and nonoverlapping.
// SAFETY: Unique unmangled symbol, matching the checked-in C header.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn fml_submit(
    op: *const c_char,
    req: *const u8,
    req_len: usize,
    job_id: *mut u64,
) -> i32 {
    guard(|| {
        if job_id.is_null() {
            return -1;
        }
        // SAFETY: Caller supplies writable aligned job output, checked nonnull.
        unsafe {
            job_id.write(0);
        }
        let mut trace_id = None;
        // SAFETY: Forwarded caller input lifetime/extent obligations.
        let parsed = unsafe { input(op, req, req_len) }.and_then(|(name, bytes)| {
            let env = runtime::parse(&bytes, &mut trace_id)?;
            if !jobs::registered() {
                return Err(runtime::failure(-1));
            }
            runtime::prepare(&name, env, crate::ops::OpMode::Submit)
        });
        let request = match parsed {
            Ok(request) => request,
            Err((status, _)) => return status,
        };
        match jobs::submit(request) {
            Ok(id) => {
                // SAFETY: Caller-owned job output remains valid until this function returns.
                unsafe {
                    job_id.write(id);
                }
                0
            }
            Err(status) => status,
        }
    })
}
/// Cancel before commit and wait for resource release; committed jobs return 1.
// SAFETY: Unique unmangled symbol, matching the checked-in C header.
#[unsafe(no_mangle)]
pub extern "C" fn fml_cancel(job_id: u64) -> i32 {
    guard(|| jobs::cancel(job_id))
}
/// Register, replace or unregister the process-wide callback while idle.
// SAFETY: Unique unmangled symbol, matching the checked-in C header.
#[unsafe(no_mangle)]
pub extern "C" fn fml_register_completion(cb: FmlCompletion, user_data: *mut c_void) -> i32 {
    guard(|| jobs::register(cb, user_data as usize))
}
/// Free only a registry-verified triple; unknown pointers are never dereferenced.
// SAFETY: Unique unmangled symbol, matching the checked-in C header.
#[unsafe(no_mangle)]
pub extern "C" fn fml_free_buffer(buf: FmlBuf) -> i32 {
    guard(|| {
        let status = buffer::free(buf);
        if status == 0 {
            jobs::freed(buf.allocation_id);
        }
        status
    })
}
/// Reject new leases and signal cancellation, without waiting for handlers.
// SAFETY: Unique unmangled symbol, matching the checked-in C header.
#[unsafe(no_mangle)]
pub extern "C" fn fml_close_handle(h: FmlHandle) -> i32 {
    guard(
        || match actor::lookup(h).map(|a| a.begin_close(CloseTrigger::NativeClose)) {
            Some(CloseReply::Accepted) => 0,
            Some(CloseReply::Busy) => -6,
            _ => -4,
        },
    )
}
#[cfg(test)]
#[path = "callback_tests.rs"]
pub(crate) mod callback_tests;
pub(crate) fn deliver(callback: FmlCompletion, id: u64, buf: FmlBuf, user: *mut c_void) {
    if let Some(callback) = callback {
        // SAFETY: Registration is pinned by the live job; caller guarantees callback/user lifetime.
        // No runtime locks are held. The receiver now owns buf and must free it exactly once.
        unsafe {
            callback(id, buf, user);
        }
    }
}
