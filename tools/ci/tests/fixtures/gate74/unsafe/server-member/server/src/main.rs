//! server 成员出现 unsafe 的夹具。

/// 读取裸指针指向的一个字节。
pub fn touch(ptr: *const u8) -> u8 {
    // SAFETY: 调用方保证指针指向至少一个可读字节。
    unsafe { *ptr }
}
