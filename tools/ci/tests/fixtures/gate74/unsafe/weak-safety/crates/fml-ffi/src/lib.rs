//! SAFETY 说明过短、无字母或窗口过远的夹具。

/// 说明过短。
pub fn too_short(ptr: *const u8) -> u8 {
    // SAFETY: ok
    unsafe { *ptr }
}

/// 说明无字母。
pub fn no_letter(ptr: *const u8) -> u8 {
    // SAFETY: 12345678
    unsafe { *ptr }
}

/// 说明在窗口外。
// SAFETY: 这行注释距离 unsafe 起始行超过三行。
pub fn out_of_window(ptr: *const u8) -> u8 {
    let _ = ptr;

    unsafe { *ptr }
}
