//! SAFETY 注释位于 unsafe 同一行行尾的夹具。

/// 读取裸指针指向的一个字节。
pub fn read_ptr(ptr: *const u8) -> u8 {
    unsafe { *ptr } // SAFETY: 调用方保证指针指向至少一个可读字节。
}
