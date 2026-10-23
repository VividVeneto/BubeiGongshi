//! unsafe / FFI 计数夹具。

/// 有 SAFETY 注释的 unsafe 块。
pub fn documented() {
    // SAFETY: 调用方已保证指针非空。
    unsafe {
        danger();
    }
}

/// 没有 SAFETY 注释的 unsafe 块。
pub fn undocumented() {
    unsafe {
        danger();
    }
}

#[no_mangle]
pub extern "C" fn exported() {}

extern "C" {
    fn c_api();
}
