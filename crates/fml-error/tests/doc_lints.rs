//! CORE-01 验收标准⑤：缺公开文档必须被真实工具链拒绝（Rust 侧）。
//!
//! `repo_config.rs` 只断言配置文本（crate 属性含 `#![deny(missing_docs)]`），不能证明门禁真的会
//! 拒绝。本文件在系统临时目录建一次性 crate，用真实 `cargo doc` 跑“有文档正例”与“仅删文档的
//! 负例”：正例退出 0；负例与正例逐行相同、只删掉 `///`/`//!` 行，必须非零退出并输出
//! missing_docs 诊断。
//!
//! 夹具落在 cargo 注入的 CARGO_TARGET_TMPDIR（target/ 内、已忽略），跑完即删。
//!
//! 夹具保留 crate 内 `#![deny(missing_docs)]`（与 `crates/fml-error/src/lib.rs` 同级的真实策略；
//! 独立夹具无法继承 workspace lints），并照验收命令传 `RUSTDOCFLAGS=-D warnings`。注意
//! `-D warnings` 只提升已发出的告警、不会打开 allow 级的 missing_docs，所以负例必须自带 deny
//! 级属性，否则这个测试会退化成恒过的空断言。

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::time::{SystemTime, UNIX_EPOCH};

/// 夹具 crate 的 deny 级属性（与 fml-error 的 crate 属性一致）。
const DENY_ATTR: &str = "#![deny(missing_docs)]\n";

/// 正例源码：crate 与全部公开项都有文档注释。
const DOCUMENTED_SOURCE: &str = "\
//! 夹具 crate：文档门禁正例。

/// 返回入参加一。
pub fn bump(value: u32) -> u32 {
    value + 1
}

/// 公开结构体，字段与关联函数都有文档。
pub struct Counter {
    /// 当前计数。
    pub count: u32,
}

impl Counter {
    /// 以零计数构造。
    pub const fn new() -> Self {
        Self { count: 0 }
    }

    /// 计数加一并返回新值。
    pub fn bump(&mut self) -> u32 {
        self.count += 1;
        self.count
    }
}
";

/// 删掉所有文档注释行；返回新源码与删除行数，保证负例与正例只差这些行。
fn strip_doc_comments(source: &str) -> (String, usize) {
    let mut kept = String::new();
    let mut removed = 0;
    for line in source.lines() {
        let trimmed = line.trim_start();
        if trimmed.starts_with("///") || trimmed.starts_with("//!") {
            removed += 1;
            continue;
        }
        kept.push_str(line);
        kept.push('\n');
    }
    (kept, removed)
}

/// 承载一次性 crate 的临时目录；删除时递归清理，不污染仓库与后续运行。
///
/// 根目录用 cargo 为集成测试注入的 `CARGO_TARGET_TMPDIR`（`target/` 内的构建产物区，
/// 已由 .gitignore 排除）：受限沙箱下仓库内的测试进程只能写工作区，系统临时目录会被拒绝，
/// 而 cargo 这个目录正是为测试夹具准备的隔离可写位置。
struct TempCrates {
    root: PathBuf,
}

impl TempCrates {
    /// 在 cargo 注入的测试临时目录下建一个本次运行独占的根目录。
    fn new(tag: &str) -> Self {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("系统时钟应晚于 UNIX 纪元")
            .as_nanos();
        let root = PathBuf::from(env!("CARGO_TARGET_TMPDIR")).join(format!(
            "fml-error-doc-lints-{}-{tag}-{nanos}",
            std::process::id()
        ));
        fs::create_dir_all(&root)
            .unwrap_or_else(|e| panic!("创建临时目录失败：{}（{e}）", root.display()));
        Self { root }
    }

    /// 写一个最小 crate；空 [workspace] 表让它不被仓库 workspace 吸收。
    fn write_crate(&self, name: &str, body: &str) -> PathBuf {
        let dir = self.root.join(name);
        fs::create_dir_all(dir.join("src")).expect("创建 crate 目录失败");
        let manifest = format!(
            "[package]\nname = \"{name}\"\nversion = \"0.1.0\"\nedition = \"2024\"\n\
             publish = false\n\n[workspace]\n"
        );
        fs::write(dir.join("Cargo.toml"), manifest).expect("写 Cargo.toml 失败");
        fs::write(dir.join("src/lib.rs"), format!("{DENY_ATTR}{body}")).expect("写 lib.rs 失败");
        dir
    }
}

impl Drop for TempCrates {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.root);
    }
}

/// 用真实 cargo doc 跑验收命令：离线、目标目录隔离在夹具内、RUSTDOCFLAGS=-D warnings。
fn cargo_doc(crate_dir: &Path) -> Output {
    Command::new(env!("CARGO"))
        .current_dir(crate_dir)
        .args(["doc", "--no-deps", "--offline"])
        .env("RUSTDOCFLAGS", "-D warnings")
        .env("CARGO_TARGET_DIR", crate_dir.join("target"))
        .output()
        .expect("无法启动 cargo doc")
}

/// 合并 stdout 与 stderr，断言失败时可读到完整诊断。
fn combined(output: &Output) -> String {
    format!(
        "stdout:\n{}\nstderr:\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    )
}

#[test]
fn cargo_doc_accepts_documented_public_items() {
    let temp = TempCrates::new("positive");
    let dir = temp.write_crate("documented", DOCUMENTED_SOURCE);

    let output = cargo_doc(&dir);
    assert!(
        output.status.success(),
        "含文档的正例必须通过：\n{}",
        combined(&output)
    );
    assert!(
        !combined(&output).contains("missing documentation"),
        "正例不应出现缺文档诊断：\n{}",
        combined(&output)
    );
}

#[test]
fn cargo_doc_rejects_missing_public_docs() {
    let (negative, removed) = strip_doc_comments(DOCUMENTED_SOURCE);
    assert!(
        removed >= 4,
        "正例必须包含公开项文档注释，实际只删除 {removed} 行"
    );
    assert_ne!(negative, DOCUMENTED_SOURCE, "负例必须与正例有差异");

    let temp = TempCrates::new("negative");
    let dir = temp.write_crate("undocumented", &negative);

    let output = cargo_doc(&dir);
    let report = combined(&output);
    assert!(
        !output.status.success(),
        "缺公开文档的负例必须非零退出：\n{report}"
    );
    assert!(
        report.contains("missing documentation"),
        "负例必须报 missing documentation 诊断：\n{report}"
    );
    assert!(
        report.contains("missing_docs"),
        "负例必须指明 missing_docs lint（deny 级来自夹具属性）：\n{report}"
    );
}
