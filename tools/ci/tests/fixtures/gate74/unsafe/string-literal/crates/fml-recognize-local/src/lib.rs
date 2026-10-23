//! unsafe 只出现在字符串字面量与标识符里的夹具。

/// 字符串与标识符里出现 unsafe 不代表构造。
pub fn describe() -> (&'static str, u8) {
    let unsafe_flag: u8 = 1;
    ("unsafe { *ptr }", unsafe_flag)
}
