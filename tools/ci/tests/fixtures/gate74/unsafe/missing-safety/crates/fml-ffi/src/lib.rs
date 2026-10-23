//! 白名单 crate 缺 SAFETY 注释的夹具。

/// 读取裸指针指向的一个字节。
pub fn read_ptr(ptr: *const u8) -> u8 {
    unsafe { *ptr }
}
