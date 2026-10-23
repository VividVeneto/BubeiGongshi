use crate::{abi::*, actor, buffer, ops::*, runtime, trace};
use serde_json::{Value, json};
use std::ffi::CString;
const TRACE: &str = "3f8b2c1d4e5f60718293a4b5c6d7e8f9";
fn request() -> Value {
    json!({"v":1,"trace_id":TRACE,"body":{}})
}
fn call(op: &str, req: Value) -> (i32, Value) {
    let bytes = serde_json::to_vec(&req).unwrap();
    let op = CString::new(op).unwrap();
    let mut out = FmlBuf::default();
    // SAFETY: Owned strings/bytes and aligned output live across this call.
    let status = unsafe { fml_call(op.as_ptr(), bytes.as_ptr(), bytes.len(), &mut out) };
    assert!(!out.ptr.is_null());
    // SAFETY: Live core buffer, copied before its single free.
    let value =
        serde_json::from_slice(unsafe { std::slice::from_raw_parts(out.ptr, out.len) }).unwrap();
    assert_eq!(fml_free_buffer(out), 0);
    (status, value)
}
#[test]
fn trace_matrix_and_dto_source() {
    let (status, ok) = call("fake.echo", request());
    assert_eq!(status, 0);
    assert_eq!(ok["trace_id"], TRACE);
    assert_eq!(ok["ok"]["dto"], 1);
    for (op, status, expected) in [
        ("fake.error", 1, TRACE),
        ("fake.traced", 1, "07070707070707070707070707070707"),
        ("fake.panic", -5, TRACE),
        ("fake.invalid", -5, TRACE),
    ] {
        let (s, v) = call(op, request());
        assert_eq!(s, status);
        assert_eq!(v["trace_id"], expected);
        assert_eq!(v["error"]["trace_id"], expected);
        assert!(v.get("ok").is_none());
    }
    for invalid in [
        Value::Null,
        json!(""),
        json!("0".repeat(32)),
        json!("A".repeat(32)),
        json!("g".repeat(32)),
        json!("a".repeat(31)),
    ] {
        let mut req = request();
        req["trace_id"] = invalid;
        let (s, v) = call("fake.echo", req);
        assert_eq!(s, -1);
        let t = v["trace_id"].as_str().unwrap();
        assert_eq!(t.len(), 32);
        assert_ne!(t, "0".repeat(32));
        assert_eq!(v["error"]["trace_id"], t);
    }
    let mut req = request();
    req.as_object_mut().unwrap().remove("trace_id");
    assert_eq!(call("fake.echo", req).0, -1);
    let mut req = request();
    req["body"]["v"] = json!(999);
    assert_eq!(call("fake.echo", req).0, 0);
    let mut req = request();
    req["v"] = json!(2);
    assert_eq!(call("fake.echo", req.clone()).0, -3);
    assert_eq!(call("unknown.op", req).0, -2);
}
#[test]
fn ownership_and_bad_arguments() {
    let buf = fml_capabilities();
    assert!(!buf.ptr.is_null());
    assert_eq!(
        fml_free_buffer(FmlBuf {
            allocation_id: buf.allocation_id + 1,
            ..buf
        }),
        -1
    );
    assert_eq!(
        fml_free_buffer(FmlBuf {
            len: buf.len + 1,
            ..buf
        }),
        -1
    );
    assert_eq!(
        fml_free_buffer(FmlBuf {
            ptr: std::ptr::dangling_mut(),
            ..buf
        }),
        -1
    );
    assert_eq!(fml_free_buffer(buf), 0);
    assert_eq!(fml_free_buffer(buf), -1);
    let newer = fml_capabilities();
    assert!(newer.allocation_id > buf.allocation_id);
    assert_eq!(fml_free_buffer(newer), 0);
    let mut out = FmlBuf::default();
    let bytes = serde_json::to_vec(&request()).unwrap();
    // SAFETY: Null/oversized inputs are rejected before dereference; other buffers are valid.
    unsafe {
        assert_eq!(
            fml_call(
                c"fake.echo".as_ptr(),
                bytes.as_ptr(),
                bytes.len(),
                std::ptr::null_mut()
            ),
            -1
        );
        for (op, req, len) in [
            (std::ptr::null(), bytes.as_ptr(), bytes.len()),
            (c"fake.echo".as_ptr(), std::ptr::null(), 0),
            (c"fake.echo".as_ptr(), bytes.as_ptr(), 16 * 1024 * 1024 + 1),
            (c"fake.echo".as_ptr(), b"{".as_ptr(), 1),
            (c"fake.echo".as_ptr(), b"\xff".as_ptr(), 1),
        ] {
            assert_eq!(fml_call(op, req, len, &mut out), -1);
            assert_eq!(fml_free_buffer(out), 0);
        }
        buffer::FAIL.with(|f| f.set(true));
        assert_eq!(
            fml_call(c"missing".as_ptr(), bytes.as_ptr(), bytes.len(), &mut out),
            -2
        );
        assert!(out.ptr.is_null());
        assert_eq!(out.len, 0);
        assert_eq!(
            fml_call(c"fake.echo".as_ptr(), bytes.as_ptr(), bytes.len(), &mut out),
            -5
        );
        assert!(out.ptr.is_null());
        buffer::FAIL.with(|f| f.set(false));
    }
}
#[test]
fn budgets_and_caps() {
    for op in BUDGET_OPS {
        let mut req = request();
        req["budget_ms"] = json!(1);
        let (s, v) = call(op, req);
        assert_eq!(s, 1);
        assert_eq!(v["error"]["code"], "EVAL_TIMEOUT");
        assert_eq!(v["trace_id"], TRACE);
    }
    let mut req = request();
    req["budget_ms"] = json!(1);
    let (s, v) = call("fake.echo", req);
    assert_eq!(s, 0);
    assert!(v["ok"]["budget_ms"].is_null());
    let caps: Value = serde_json::from_slice(&runtime::capabilities()).unwrap();
    assert_eq!(caps["build"]["test_build"], true);
    let mut actual: Vec<_> = caps["ops"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|o| o["budget"] == true)
        .map(|o| o["op"].as_str().unwrap())
        .collect();
    actual.sort();
    let mut expected = BUDGET_OPS.to_vec();
    expected.sort();
    assert_eq!(actual, expected);
}
#[test]
fn real_actor_scope_close_and_stale_generation() {
    let (h, a) = actor::fixture("A");
    let (other, _) = actor::fixture("B");
    assert_eq!(
        call("fake.profile", request()).1["error"]["code"],
        "AUTH_NO_PROFILE"
    );
    let mut req = request();
    req["profile_handle"] = json!(h.to_string());
    req["body"]["profile_id"] = json!("A");
    assert_eq!(call("fake.profile", req.clone()).0, 0);
    assert_eq!(call("fake.echo", req.clone()).0, -1);
    req["body"]["profile_id"] = json!("B");
    assert_eq!(call("fake.profile", req.clone()).0, -1);
    req["body"]["profile_id"] = json!("A");
    req["body"]["handle"] = json!(other.to_string());
    assert_eq!(call("fake.profile", req.clone()).0, -1);
    req["body"].as_object_mut().unwrap().remove("handle");
    assert_eq!(fml_close_handle(h + (1 << 48)), -4);
    assert_eq!(fml_close_handle(0), -4);
    let lease = a.lease().unwrap();
    assert_eq!(fml_close_handle(h), 0);
    assert!(a.is_closing());
    assert_eq!(fml_close_handle(h), -6);
    assert!(!a.retire());
    assert_eq!(call("fake.profile", req.clone()).0, -4);
    drop(lease);
    assert_eq!(fml_close_handle(h), -4);
    req["profile_handle"] = json!(other.to_string());
    req["body"]["profile_id"] = json!("B");
    assert_eq!(call("fake.profile", req).0, 0);
    assert_eq!(fml_close_handle(other), 0);
    let (_, store) = actor::fixture("store");
    assert!(!store.retire());
    assert_eq!(
        store.begin_close(CloseTrigger::StoreClose),
        CloseReply::Accepted
    );
    assert_eq!(
        store.begin_close(CloseTrigger::StoreClose),
        CloseReply::Busy
    );
    assert!(store.retire());
    assert_eq!(
        store.begin_close(CloseTrigger::NativeClose),
        CloseReply::Stale
    );
}
#[test]
fn trace_packing_concurrency_and_wrap() {
    assert_eq!(
        trace::pack(1, 2).to_string(),
        "00000000000000010000000000000002"
    );
    assert!(!trace::pack(0, 0).is_zero());
    assert_ne!(trace::pack(9, u64::MAX), trace::pack(9, 0));
    assert!(!trace::emergency().is_zero());
    let workers: Vec<_> = (0..8)
        .map(|_| {
            std::thread::spawn(|| {
                (0..1000)
                    .map(|_| trace::fresh().to_string())
                    .collect::<Vec<_>>()
            })
        })
        .collect();
    let ids: std::collections::HashSet<_> = workers
        .into_iter()
        .flat_map(|w| w.join().unwrap())
        .collect();
    assert_eq!(ids.len(), 8000);
    assert!(
        ids.iter()
            .all(|id| id.len() == 32 && id != "00000000000000000000000000000000")
    );
    let flag = CancelHandle::default();
    assert!(!flag.is_cancelled());
    flag.cancel();
    assert!(flag.is_cancelled());
}
#[test]
fn six_statuses_use_registry_metadata() {
    for (s, name, retryable) in [
        (-1, "FFI_BAD_ARG", false),
        (-2, "FFI_UNKNOWN_OP", false),
        (-3, "FFI_VERSION_MISMATCH", false),
        (-4, "FFI_STALE_HANDLE", false),
        (-5, "FFI_PANIC", false),
        (-6, "FFI_BUSY", true),
    ] {
        let (_, error) = runtime::failure(s);
        assert_eq!(error.code.as_str(), name);
        assert_eq!(error.retryable, retryable);
        assert_eq!(error.domain, "ffi");
        assert_eq!(error.code.severity(), fml_error::Severity::Error);
    }
}
