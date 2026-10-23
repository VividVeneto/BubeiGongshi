//! Queue -> executing -> committed -> freed. STATE linearizes commit/cancel/close/register.
//! Lock order: STATE -> actor -> handle table; STATE -> buffers. Never invoke foreign code locked.
use crate::{
    abi::FmlCompletion,
    buffer::{self, lock},
    ops::*,
    runtime::Prepared,
};
use std::{
    collections::{BTreeMap, VecDeque},
    ffi::c_void,
    sync::{Arc, Condvar, Mutex, OnceLock},
};
const MAX_INFLIGHT_JOBS: usize = 64;
struct Job {
    handle: Option<u64>,
    cancel: Arc<CancelHandle>,
    committed: bool,
    emitting: bool,
    allocation: u64,
}
struct State {
    callback: (FmlCompletion, usize),
    next: u64,
    jobs: BTreeMap<u64, Job>,
    queue: VecDeque<(u64, Prepared)>,
}
static STATE: Mutex<State> = Mutex::new(State {
    callback: (None, 0),
    next: 1,
    jobs: BTreeMap::new(),
    queue: VecDeque::new(),
});
static CHANGED: Condvar = Condvar::new();
static STARTED: OnceLock<Result<(), ()>> = OnceLock::new();
fn wait(state: std::sync::MutexGuard<'_, State>) -> std::sync::MutexGuard<'_, State> {
    CHANGED.wait(state).unwrap_or_else(|p| p.into_inner())
}
fn start() -> Result<(), ()> {
    *STARTED.get_or_init(|| {
        for _ in 0..std::thread::available_parallelism()
            .map_or(1, |n| n.get())
            .min(4)
        {
            std::thread::Builder::new()
                .name("fml-worker".into())
                .spawn(worker)
                .map_err(|_| ())?;
        }
        Ok(())
    })
}
pub(crate) fn registered() -> bool {
    lock(&STATE).callback.0.is_some()
}
pub(crate) fn register(cb: FmlCompletion, user: usize) -> i32 {
    let mut state = lock(&STATE);
    if !state.jobs.is_empty() {
        return -6;
    }
    state.callback = (cb, user);
    0
}
pub(crate) fn submit(request: Prepared) -> Result<u64, i32> {
    start().map_err(|_| -5)?;
    let mut state = lock(&STATE);
    if state.callback.0.is_none() {
        return Err(-1);
    }
    if request.actor.is_closing() {
        return Err(-4);
    }
    if state.jobs.values().filter(|j| !j.committed).count() >= MAX_INFLIGHT_JOBS {
        return Err(-6);
    }
    let id = state.next;
    if id == 0 {
        return Err(-6);
    }
    state.queue.try_reserve(1).map_err(|_| -5)?;
    let job = Job {
        handle: if request.control {
            None
        } else {
            request.handle
        },
        cancel: Arc::new(CancelHandle::default()),
        committed: false,
        emitting: false,
        allocation: 0,
    };
    state.jobs.insert(id, job);
    state.next = id.checked_add(1).unwrap_or(0);
    state.queue.push_back((id, request));
    CHANGED.notify_all();
    Ok(id)
}
fn worker() {
    loop {
        let (id, request, cancel) = {
            let mut state = lock(&STATE);
            while state.queue.is_empty() {
                state = wait(state);
            }
            let (id, request) = state.queue.pop_front().expect("nonempty queue");
            (id, request, state.jobs[&id].cancel.clone())
        };
        let bytes = if cancel.is_cancelled() {
            Vec::new()
        } else {
            request.complete(&cancel)
        };
        let mut state = lock(&STATE);
        if cancel.is_cancelled() {
            // Drop all request/result/lease state before publishing cancellation completion.
            drop(bytes);
            drop(request);
            drop(cancel);
            state.jobs.remove(&id);
            CHANGED.notify_all();
            continue;
        }
        // No cancellation can cross this checkpoint. Allocation failure delivers a null buffer.
        let buf = std::panic::catch_unwind(|| buffer::allocate(bytes)).unwrap_or_default();
        #[cfg(test)]
        buffer::FAIL.with(|f| f.set(false));
        let job = state.jobs.get_mut(&id).expect("live job");
        job.committed = true;
        job.emitting = true;
        job.allocation = buf.allocation_id;
        let (callback, user) = state.callback;
        drop(state);
        crate::abi::deliver(callback, id, buf, user as *mut c_void);
        drop(request);
        drop(cancel);
        let mut state = lock(&STATE);
        state.jobs.get_mut(&id).expect("emitting job").emitting = false;
        reap(&mut state, id);
    }
}
fn reap(state: &mut State, id: u64) {
    if state
        .jobs
        .get(&id)
        .is_some_and(|j| j.committed && !j.emitting && j.allocation == 0)
    {
        state.jobs.remove(&id);
        CHANGED.notify_all();
    }
}
pub(crate) fn freed(allocation: u64) {
    let mut state = lock(&STATE);
    if let Some((&id, job)) = state
        .jobs
        .iter_mut()
        .find(|(_, j)| j.allocation == allocation)
    {
        job.allocation = 0;
        reap(&mut state, id);
    }
}
pub(crate) fn cancel(id: u64) -> i32 {
    let mut state = lock(&STATE);
    let Some(job) = state.jobs.get(&id) else {
        return -4;
    };
    if job.committed {
        return 1;
    }
    job.cancel.cancel();
    CHANGED.notify_all();
    if let Some(index) = state.queue.iter().position(|(queued, _)| *queued == id) {
        drop(state.queue.remove(index));
        state.jobs.remove(&id);
        CHANGED.notify_all();
    }
    // Condvar releases STATE; close and unrelated jobs/callbacks can progress while we drain.
    while state.jobs.contains_key(&id) {
        state = wait(state);
    }
    0
}
pub(crate) fn close(actor: &HandleActor, trigger: CloseTrigger) -> CloseReply {
    let mut state = lock(&STATE);
    if state
        .jobs
        .values()
        .any(|j| j.handle == Some(actor.handle) && j.committed)
    {
        return CloseReply::Busy;
    }
    let reply = actor.close_gate(trigger);
    if reply == CloseReply::Accepted {
        for job in state
            .jobs
            .values()
            .filter(|j| j.handle == Some(actor.handle))
        {
            job.cancel.cancel();
        }
        while let Some(index) = state
            .queue
            .iter()
            .position(|(_, r)| r.handle == Some(actor.handle) && !r.control)
        {
            let (id, request) = state.queue.remove(index).expect("queued close job");
            drop(request);
            state.jobs.remove(&id);
        }
        CHANGED.notify_all();
    }
    reply
}
#[cfg(test)]
#[path = "job_tests.rs"]
pub(crate) mod tests;
