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
    /// Already closing (job-related busy states belong to phase two).
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
    handle: FmlHandle,
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
        let mut state = lock(&self.state);
        if state.closing || state.retired {
            return None;
        }
        state.leases = state.leases.checked_add(1)?;
        Some(Lease(self))
    }
    /// Whether close has begun (also true after retirement).
    pub fn is_closing(&self) -> bool {
        lock(&self.state).closing
    }
    /// Atomically reject new leases; never wait for existing ones.
    pub fn begin_close(&self, trigger: CloseTrigger) -> CloseReply {
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
        CloseReply::Accepted
    }
    /// Retire only a closing actor with no leases; never resurrect an identity.
    pub fn retire(&self) -> bool {
        let mut state = lock(&self.state);
        if !state.closing || state.leases != 0 {
            return false;
        }
        state.retired = true;
        true
    }
}
impl Drop for Lease<'_> {
    fn drop(&mut self) {
        let mut state = lock(&self.0.state);
        state.leases -= 1;
        state.retired |= state.native && state.closing && state.leases == 0;
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
    let slot = u64::try_from(table.len()).unwrap() + 1;
    assert!(slot < (1 << 48));
    let handle = (1 << 48) | slot;
    let actor = Arc::new(HandleActor::new(handle, Some(profile.into())));
    table.push(actor.clone());
    (handle, actor)
}
