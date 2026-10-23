//! 白名单 crate 的合规 unsafe 夹具。

/// 读取裸指针指向的一个字节。
pub fn read_ptr(ptr: *const u8) -> u8 {
    // SAFETY: 调用方保证指针指向至少一个可读字节。
    unsafe { *ptr }
}
