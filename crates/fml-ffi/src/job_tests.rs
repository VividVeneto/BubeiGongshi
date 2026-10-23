use super::*;
use crate::{abi::*, actor};
use serde_json::{Value, json};
use std::{ffi::CString, sync::mpsc, time::Duration};
const TRACE: &str = "1234567890abcdef1234567890abcdef";
struct Gate {
    state: Mutex<(usize, bool)>,
    changed: Condvar,
}
static GATES: Mutex<BTreeMap<u64, Arc<Gate>>> = Mutex::new(BTreeMap::new());
type Event = (
    u64,
    usize,
    usize,
    u64,
    i32,
    i32,
    usize,
    std::thread::ThreadId,
);
static EVENTS: Mutex<Option<mpsc::Sender<Event>>> = Mutex::new(None);
pub(crate) fn receive(id: u64, buf: FmlBuf, user: usize) {
    let event = (
        id,
        buf.ptr as usize,
        buf.len,
        buf.allocation_id,
        fml_cancel(id),
        fml_register_completion(None, std::ptr::null_mut()),
        user,
        std::thread::current().id(),
    );
    if let Some(tx) = lock(&EVENTS).as_ref() {
        let _ = tx.send(event);
    }
}
pub(crate) fn gate(ctx: &OpCtx<'_>, body: &Value) {
    if let Some(id) = body["gate"].as_u64() {
        let gate = lock(&GATES)[&id].clone();
        let mut state = lock(&gate.state);
        state.0 += 1;
        gate.changed.notify_all();
        while !state.1 {
            let (next, timeout) = gate
                .changed
                .wait_timeout(state, Duration::from_secs(10))
                .unwrap();
            state = next;
            assert!(
                !timeout.timed_out(),
                "test must release its finite handler gate"
            );
        }
    }
    if body["cooperate"] == true {
        while !ctx.cancel.is_cancelled() {
            std::thread::yield_now();
        }
    }
    if body["allocation_fail"] == true {
        buffer::FAIL.with(|f| f.set(true));
    }
}
fn new_gate(id: u64) -> Arc<Gate> {
    let gate = Arc::new(Gate {
        state: Mutex::new((0, false)),
        changed: Condvar::new(),
    });
    lock(&GATES).insert(id, gate.clone());
    gate
}
fn entered(gate: &Gate, n: usize) {
    let state = lock(&gate.state);
    let (state, timeout) = gate
        .changed
        .wait_timeout_while(state, Duration::from_secs(10), |s| s.0 < n)
        .unwrap();
    assert!(!timeout.timed_out() && state.0 >= n);
}
fn release(gate: &Gate) {
    lock(&gate.state).1 = true;
    gate.changed.notify_all();
}
fn request(body: Value) -> Value {
    json!({"v":1,"trace_id":TRACE,"body":body})
}
fn submit(op: &str, req: Value) -> (i32, u64) {
    let name = CString::new(op).unwrap();
    let bytes = serde_json::to_vec(&req).unwrap();
    let mut id = 99;
    // SAFETY: Names/requests live through the call, output is exclusive and aligned.
    let s = unsafe { fml_submit(name.as_ptr(), bytes.as_ptr(), bytes.len(), &mut id) };
    (s, id)
}
fn profile(h: u64, body: Value) -> Value {
    let mut req = request(body);
    req["profile_handle"] = json!(h.to_string());
    req
}
fn idle() {
    let state = lock(&STATE);
    let (state, timed) = CHANGED
        .wait_timeout_while(state, Duration::from_secs(10), |s| !s.jobs.is_empty())
        .unwrap();
    assert!(
        !timed.timed_out(),
        "jobs failed to drain: {}",
        state.jobs.len()
    );
    assert!(state.queue.is_empty());
}
fn event(rx: &mpsc::Receiver<Event>, id: u64) -> (FmlBuf, Value) {
    let (actual, ptr, len, allocation_id, cancel, register, user, thread) =
        rx.recv_timeout(Duration::from_secs(10)).unwrap();
    assert_eq!(actual, id);
    assert_eq!((cancel, register, user), (1, -6, 17));
    assert_ne!(thread, std::thread::current().id());
    let buf = FmlBuf {
        ptr: ptr as *mut u8,
        len,
        allocation_id,
    };
    let value = if ptr == 0 {
        Value::Null
    } else {
        // SAFETY: Callback transferred this live allocation, not freed until after inspection.
        serde_json::from_slice(unsafe { std::slice::from_raw_parts(buf.ptr, len) }).unwrap()
    };
    (buf, value)
}
#[test]
fn async_lifecycle_concurrency_and_ownership() {
    let (tx, rx) = mpsc::channel();
    *lock(&EVENTS) = Some(tx);
    assert_eq!(fml_register_completion(None, std::ptr::null_mut()), 0);
    assert_eq!(submit("fake.async", request(json!({}))), (-1, 0));
    assert_eq!(
        fml_register_completion(
            Some(crate::abi::callback_tests::done),
            17usize as *mut c_void
        ),
        0
    );
    for (op, req, expected) in [
        ("missing", request(json!({})), -2),
        ("fake.echo", request(json!({})), -2),
        ("fake.async", json!({"v":2,"trace_id":TRACE,"body":{}}), -3),
        (
            "fake.async",
            json!({"v":1,"trace_id":"0".repeat(32),"body":{}}),
            -1,
        ),
        ("fake.async_profile", request(json!({})), 1),
        ("fake.async_profile", profile(u64::MAX, json!({})), -4),
        ("fake.async", profile(1, json!({})), -1),
    ] {
        assert_eq!(submit(op, req), (expected, 0));
    }
    let mut id = 9;
    // SAFETY: All invalid null/oversize arguments are rejected before dereference.
    unsafe {
        assert_eq!(fml_submit(std::ptr::null(), b"{}".as_ptr(), 2, &mut id), -1);
        assert_eq!(id, 0);
        assert_eq!(
            fml_submit(c"fake.async".as_ptr(), std::ptr::null(), 0, &mut id),
            -1
        );
        assert_eq!(
            fml_submit(
                c"fake.async".as_ptr(),
                b"{}".as_ptr(),
                16 * 1024 * 1024 + 1,
                &mut id
            ),
            -1
        );
        assert_eq!(
            fml_submit(
                c"fake.async".as_ptr(),
                b"{}".as_ptr(),
                2,
                std::ptr::null_mut()
            ),
            -1
        );
    }
    // Request/name allocations above are dropped on return; worker must only use owned state.
    for (op, error, trace) in [
        ("fake.async", None, TRACE),
        ("fake.async_error", Some("EVAL_TIMEOUT"), TRACE),
        (
            "fake.async_traced",
            Some("EVAL_TIMEOUT"),
            "07070707070707070707070707070707",
        ),
        ("fake.async_panic", Some("FFI_PANIC"), TRACE),
        ("fake.async_invalid", Some("FFI_PANIC"), TRACE),
    ] {
        let (s, id) = submit(op, request(json!({"payload":"owned","v":999})));
        assert_eq!(s, 0);
        let (buf, reply) = event(&rx, id);
        assert_eq!(reply["trace_id"], trace);
        assert_eq!(reply["v"], 1);
        if let Some(error) = error {
            assert_eq!(reply["error"]["code"], error);
            assert_eq!(reply["error"]["trace_id"], trace);
        } else {
            assert_eq!(reply["ok"]["echo"]["payload"], "owned");
        }
        assert_eq!(fml_cancel(id), 1);
        assert_eq!(fml_register_completion(None, std::ptr::null_mut()), -6);
        assert_eq!(
            fml_free_buffer(FmlBuf {
                allocation_id: 0,
                ..buf
            }),
            -1
        );
        assert_eq!(fml_register_completion(None, std::ptr::null_mut()), -6);
        assert_eq!(fml_free_buffer(buf), 0);
        assert_eq!(fml_free_buffer(buf), -1);
        idle();
        assert_eq!(fml_cancel(id), -4);
    }
    // Occupy every worker, then fill queue+running to exactly 64 without timing guesses.
    let gate = new_gate(1);
    let workers = std::thread::available_parallelism()
        .map_or(1, |n| n.get())
        .min(4);
    let mut ids = Vec::new();
    for _ in 0..64 {
        let (s, id) = submit("fake.async", request(json!({"gate":1})));
        assert_eq!(s, 0);
        ids.push(id);
    }
    entered(&gate, workers);
    assert_eq!(lock(&gate.state).0, workers);
    assert_eq!(submit("fake.async", request(json!({}))), (-6, 0));
    assert_eq!(fml_register_completion(None, std::ptr::null_mut()), -6);
    let queued = ids.pop().unwrap();
    assert_eq!(fml_cancel(queued), 0);
    assert_eq!(fml_cancel(queued), -4);
    let (queued_handle, queued_actor) = actor::fixture("queued");
    let (s, closed_job) = submit("fake.async_profile", profile(queued_handle, json!({})));
    assert_eq!(s, 0);
    assert_eq!(fml_close_handle(queued_handle), 0);
    assert!(actor::lookup(queued_handle).is_none());
    assert_eq!(fml_cancel(closed_job), -4);
    drop(queued_actor);
    let (s, refill) = submit("fake.async", request(json!({"gate":1})));
    assert_eq!(s, 0);
    assert!(refill > queued);
    ids.push(refill);
    let first = ids[0];
    let (done_tx, done_rx) = mpsc::channel();
    let cancel_thread = std::thread::spawn(move || {
        let s = fml_cancel(first);
        done_tx.send(s).unwrap();
    });
    {
        let state = lock(&STATE);
        let (_state, timed) = CHANGED
            .wait_timeout_while(state, Duration::from_secs(10), |s| {
                !s.jobs[&first].cancel.is_cancelled()
            })
            .unwrap();
        assert!(!timed.timed_out());
    }
    assert!(
        matches!(done_rx.try_recv(), Err(mpsc::TryRecvError::Empty)),
        "noncooperative handler must not report premature cancel=0"
    );
    // Cancel queued jobs synchronously, running jobs concurrently; release gate only after flags.
    let threads: Vec<_> = ids
        .into_iter()
        .skip(1)
        .map(|id| std::thread::spawn(move || fml_cancel(id)))
        .collect();
    {
        let state = lock(&STATE);
        let (_state, timed) = CHANGED
            .wait_timeout_while(state, Duration::from_secs(10), |s| {
                s.jobs.values().any(|j| !j.cancel.is_cancelled())
            })
            .unwrap();
        assert!(!timed.timed_out());
    }
    release(&gate);
    assert_eq!(done_rx.recv_timeout(Duration::from_secs(10)).unwrap(), 0);
    cancel_thread.join().unwrap();
    for t in threads {
        assert_eq!(t.join().unwrap(), 0);
    }
    idle();
    assert!(rx.try_recv().is_err());
    // Native close must return while the finite noncooperative handler still holds its lease.
    let (a_handle, a) = actor::fixture("A");
    let weak = Arc::downgrade(&a);
    let (b_handle, b) = actor::fixture("B");
    let gate = new_gate(2);
    let (s, job) = submit(
        "fake.async_profile",
        profile(a_handle, json!({"gate":2,"profile_id":"A"})),
    );
    assert_eq!(s, 0);
    entered(&gate, 1);
    assert_eq!(fml_close_handle(a_handle), 0);
    assert_eq!(fml_close_handle(a_handle), -6);
    assert!(a.is_closing());
    assert!(!a.retire());
    assert!(a.lease().is_none());
    assert_eq!(
        submit("fake.async_profile", profile(a_handle, json!({}))),
        (-4, 0)
    );
    assert!(actor::lookup(a_handle).is_some());
    // Close already supplied cancellation; wait only for actual exit, then stale is expected.
    release(&gate);
    idle();
    assert!(actor::lookup(a_handle).is_none());
    assert_eq!(fml_cancel(job), -4);
    drop(a);
    assert!(weak.upgrade().is_none());
    assert_eq!(fml_close_handle(a_handle), -4);
    let mut bad = profile(b_handle, json!({"profile_id":"A"}));
    assert_eq!(submit("fake.async_profile", bad.clone()), (-1, 0));
    bad["v"] = json!(2);
    assert_eq!(submit("fake.async_profile", bad), (-3, 0));
    let (s, job) = submit(
        "fake.async_profile",
        profile(b_handle, json!({"profile_id":"B"})),
    );
    assert_eq!(s, 0);
    let (buf, reply) = event(&rx, job);
    assert_eq!(reply["ok"]["echo"]["profile_id"], "B");
    assert_eq!(fml_close_handle(b_handle), -6);
    assert!(!b.is_closing());
    assert_eq!(fml_free_buffer(buf), 0);
    idle();
    assert_eq!(fml_close_handle(b_handle), 0);
    drop(b);
    for _ in 0..100 {
        let (h, a) = actor::fixture("reclaim");
        let weak = Arc::downgrade(&a);
        assert!(h > b_handle);
        assert_eq!(fml_close_handle(h), 0);
        assert!(actor::lookup(h).is_none());
        drop(a);
        assert!(weak.upgrade().is_none());
    }
    // A cooperative CPU handler drains without a timer or a forced thread kill.
    let (s, job) = submit("fake.async", request(json!({"cooperate":true})));
    assert_eq!(s, 0);
    assert_eq!(fml_cancel(job), 0);
    idle();
    assert!(rx.try_recv().is_err());
    // Competing cancel/completion: either cancel=0 with no callback, or commit=1 exactly once.
    for n in 10..50 {
        let gate = new_gate(n);
        let (s, job) = submit("fake.async", request(json!({"gate":n})));
        assert_eq!(s, 0);
        entered(&gate, 1);
        let start = Arc::new(std::sync::Barrier::new(2));
        let other = start.clone();
        let thread = std::thread::spawn(move || {
            other.wait();
            fml_cancel(job)
        });
        start.wait();
        release(&gate);
        match thread.join().unwrap() {
            0 => {
                idle();
                assert!(rx.try_recv().is_err());
            }
            1 => {
                let (buf, _) = event(&rx, job);
                assert_eq!(fml_free_buffer(buf), 0);
                idle();
                assert!(rx.try_recv().is_err());
            }
            s => panic!("unexpected cancel race status {s}"),
        }
    }
    // Alloc failure is contained in the worker, callback still terminates with a null triple.
    let (s, job) = submit("fake.async", request(json!({"allocation_fail":true})));
    assert_eq!(s, 0);
    let (buf, reply) = event(&rx, job);
    assert!(buf.ptr.is_null() && reply.is_null());
    idle();
    // Exhaustion is terminal; never recycle job identities into a stale caller's ID.
    lock(&STATE).next = u64::MAX;
    let (s, job) = submit("fake.async", request(json!({})));
    assert_eq!((s, job), (0, u64::MAX));
    let (buf, _) = event(&rx, job);
    assert_eq!(fml_free_buffer(buf), 0);
    idle();
    assert_eq!(submit("fake.async", request(json!({}))), (-6, 0));
    assert_eq!(fml_cancel(job), -4);
    assert_eq!(fml_register_completion(None, std::ptr::null_mut()), 0);
    assert_eq!(submit("fake.async", request(json!({}))), (-1, 0));
    assert_eq!(fml_cancel(0), -4);
    *lock(&EVENTS) = None;
}
