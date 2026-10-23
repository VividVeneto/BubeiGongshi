//! 白名单 crate 的 tests/ 也在扫描面内：缺 SAFETY 一样报。

#[test]
fn reads_byte() {
    let value: u8 = 7;
    let pointer = &value as *const u8;
    unsafe { *pointer };
}
