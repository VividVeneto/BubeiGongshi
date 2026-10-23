//! Cargo metadata only; CI supplies the commit being built, never a fabricated hash.
fn main() {
    println!("cargo:rerun-if-env-changed=FML_BUILD_GIT");
    println!(
        "cargo:rustc-env=FML_TARGET={}",
        std::env::var("TARGET").unwrap()
    );
    let git = std::env::var("FML_BUILD_GIT").unwrap_or_else(|_| "unknown".into());
    assert!(
        git == "unknown" || (git.len() == 40 && git.bytes().all(|b| b.is_ascii_hexdigit())),
        "FML_BUILD_GIT must be the full built commit"
    );
    println!("cargo:rustc-env=FML_GIT={git}");
}
