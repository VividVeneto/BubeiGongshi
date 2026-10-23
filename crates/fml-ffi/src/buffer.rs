use crate::abi::FmlBuf;
use std::sync::{Mutex, MutexGuard};
struct Allocation {
    id: u64,
    bytes: Box<[u8]>,
}
struct Buffers {
    next: u64,
    live: Vec<Allocation>,
}
static BUFFERS: Mutex<Buffers> = Mutex::new(Buffers {
    next: 1,
    live: Vec::new(),
});
pub(crate) fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex.lock().unwrap_or_else(|poison| poison.into_inner())
}
#[cfg(test)]
thread_local! { pub(crate) static FAIL: std::cell::Cell<bool> = const { std::cell::Cell::new(false) }; }
pub(crate) fn allocate(bytes: Vec<u8>) -> FmlBuf {
    #[cfg(test)]
    if FAIL.with(|flag| flag.get()) {
        return FmlBuf::default();
    }
    let mut table = lock(&BUFFERS);
    if table.next == 0 || table.live.try_reserve(1).is_err() {
        return FmlBuf::default();
    }
    let id = table.next;
    table.next = id.checked_add(1).unwrap_or(0);
    let mut bytes = bytes.into_boxed_slice();
    let buf = FmlBuf {
        ptr: bytes.as_mut_ptr(),
        len: bytes.len(),
        allocation_id: id,
    };
    table.live.push(Allocation { id, bytes });
    buf
}
pub(crate) fn free(buf: FmlBuf) -> i32 {
    let mut table = lock(&BUFFERS);
    let Some(i) = table.live.iter().position(|a| {
        a.id == buf.allocation_id && a.bytes.as_ptr() == buf.ptr && a.bytes.len() == buf.len
    }) else {
        return -1;
    };
    table.live.swap_remove(i);
    0
}
