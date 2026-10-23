//! DEP-4 夹具：extern "C" 只在 crates/fml-ffi/src/ 内允许。
const DOC: &str = "字符串里的 extern \"C\" 不报";

// 注释里的 extern "C" 不报。
unsafe extern "C" fn raw_entry() {}

extern "C" {
    fn other();
}

extern "C" fn plain_entry() {}
