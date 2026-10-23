use fml_error::TraceId;
use std::{
    collections::hash_map::RandomState,
    hash::BuildHasher,
    sync::{
        OnceLock,
        atomic::{AtomicU64, Ordering},
    },
};
static PREFIX: OnceLock<u64> = OnceLock::new();
static SEQUENCE: AtomicU64 = AtomicU64::new(1);
pub(crate) fn pack(prefix: u64, sequence: u64) -> TraceId {
    let mut bytes = [0; 16];
    bytes[..8].copy_from_slice(&prefix.to_be_bytes());
    bytes[8..].copy_from_slice(&sequence.to_be_bytes());
    if bytes == [0; 16] {
        bytes[0] = 1;
    }
    TraceId(bytes)
}
pub(crate) fn fresh() -> TraceId {
    let prefix = *PREFIX.get_or_init(|| RandomState::new().hash_one("fml-ffi/trace/v1"));
    pack(prefix, SEQUENCE.fetch_add(1, Ordering::Relaxed))
}
// Panic recovery never re-enters the RandomState initializer.
pub(crate) fn emergency() -> TraceId {
    pack(0x666d6c2d70616e69, SEQUENCE.fetch_add(1, Ordering::Relaxed))
}
