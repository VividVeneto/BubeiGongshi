use crate::{abi::FmlHandle, buffer::lock};
use std::sync::{Arc, Mutex};
/// Origin of the shared close transition.
#[derive(Clone, Copy)]
pub enum CloseTrigger {
    /// Native C close, retire when synchronous leases drain.
    NativeClose,
    /// Store-owned close, caller must drain resources before retire.
    StoreClose,
}
/// Outcome of a nonblocking close request.
#[derive(Debug, PartialEq, Eq)]
pub enum CloseReply {
    /// Closing accepted; new leases are rejected.
    Accepted,
    /// Already closing or a committed completion still owns delivery resources.
    Busy,
    /// Retired actor.
    Stale,
}
#[derive(Default)]
struct State {
    leases: usize,
    closing: bool,
    retired: bool,
    native: bool,
}
/// An immutable slot/generation identity with synchronized lease/close state.
pub struct HandleActor {
    pub(crate) handle: FmlHandle,
    pub(crate) profile: Option<String>,
    state: Mutex<State>,
}
/// A synchronous lease; dropping it releases the actor without holding a dispatch lock.
pub struct Lease<'a>(&'a HandleActor);
impl HandleActor {
    pub(crate) fn new(handle: FmlHandle, profile: Option<String>) -> Self {
        Self {
            handle,
            profile,
            state: Mutex::new(State::default()),
        }
    }
    /// Take a lease unless closing or retired.
    pub fn lease(&self) -> Option<Lease<'_>> {
        self.acquire().then(|| Lease(self))
    }
    pub(crate) fn acquire(&self) -> bool {
        let mut state = lock(&self.state);
        if state.closing || state.retired || state.leases == usize::MAX {
            return false;
        }
        state.leases += 1;
        true
    }
    /// Whether close has begun (also true after retirement).
    pub fn is_closing(&self) -> bool {
        lock(&self.state).closing
    }
    /// Atomically reject new leases; never wait for existing ones.
    pub fn begin_close(&self, trigger: CloseTrigger) -> CloseReply {
        crate::jobs::close(self, trigger)
    }
    pub(crate) fn close_gate(&self, trigger: CloseTrigger) -> CloseReply {
        let mut state = lock(&self.state);
        if state.retired {
            return CloseReply::Stale;
        }
        if state.closing {
            return CloseReply::Busy;
        }
        state.closing = true;
        state.native = matches!(trigger, CloseTrigger::NativeClose);
        state.retired = state.native && state.leases == 0;
        self.reclaim(&state);
        CloseReply::Accepted
    }
    /// Retire only a closing actor with no leases; never resurrect an identity.
    pub fn retire(&self) -> bool {
        let mut state = lock(&self.state);
        if !state.closing || state.leases != 0 {
            return false;
        }
        state.retired = true;
        self.reclaim(&state);
        true
    }
    fn reclaim(&self, state: &State) {
        if state.retired {
            lock(&HANDLES).retain(|actor| actor.handle != self.handle);
        }
    }
    pub(crate) fn release(&self) {
        let mut state = lock(&self.state);
        state.leases -= 1;
        state.retired |= state.native && state.closing && state.leases == 0;
        self.reclaim(&state);
    }
}
impl Drop for Lease<'_> {
    fn drop(&mut self) {
        self.0.release();
    }
}
static HANDLES: Mutex<Vec<Arc<HandleActor>>> = Mutex::new(Vec::new());
pub(crate) fn lookup(handle: FmlHandle) -> Option<Arc<HandleActor>> {
    lock(&HANDLES)
        .iter()
        .find(|actor| actor.handle == handle)
        .cloned()
}
// No public producer before Store. Test slots are monotonically allocated, never recycled.
#[cfg(test)]
pub(crate) fn fixture(profile: &str) -> (FmlHandle, Arc<HandleActor>) {
    let mut table = lock(&HANDLES);
    static NEXT: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(1);
    let slot = NEXT
        .try_update(
            std::sync::atomic::Ordering::Relaxed,
            std::sync::atomic::Ordering::Relaxed,
            |slot| (slot < (1 << 48)).then_some(slot + 1),
        )
        .expect("fixture handle slots exhausted; never reuse generations");
    let handle = (1 << 48) | slot;
    let actor = Arc::new(HandleActor::new(handle, Some(profile.into())));
    table.push(actor.clone());
    (handle, actor)
}
