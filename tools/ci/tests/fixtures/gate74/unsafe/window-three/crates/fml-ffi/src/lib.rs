// SAFETY: 调用方保证指针在本次调用期间至少可读一字节
pub fn wrapper() -> u8 { 0 }
pub fn inner() -> u8 { 1 }
pub unsafe fn touch(ptr: *const u8) -> u8 {
    *ptr
}
