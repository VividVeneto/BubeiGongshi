//! CORE-03: process-wide C boundary, synchronous dispatch and bounded async jobs.
//! See the crate README for ownership, caller safety and deferred business integration.
#![deny(missing_docs)]
#![deny(unsafe_op_in_unsafe_fn)]
#[cfg(all(feature = "test_ops", not(debug_assertions)))]
compile_error!("test_ops is forbidden in non-debug builds");
#[cfg(all(feature = "abi_major_bump", not(debug_assertions)))]
compile_error!("abi_major_bump is forbidden in non-debug builds");
pub mod abi;
mod actor;
mod buffer;
mod jobs;
pub mod ops;
mod runtime;
mod trace;
const DTO_MAJOR: u32 = 1;
const ABI_MAJOR: u32 = 1 + cfg!(feature = "abi_major_bump") as u32;
const ABI_MINOR: u32 = 0;
#[cfg(test)]
mod tests;
