//! CORE-01 测试方案第 1、2、3、6、7 条：仓库骨架、工程配置、锁版与依赖清单断言。
//!
//! 本测试只读仓库文件与 cargo 元数据，不实现检查器（CORE-69/CORE-41 消费同一批文件）。

use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;
use std::process::Command;

use serde_json::{Value, json};

/// 仓库根目录（由 crate 位置推出，避免依赖当前工作目录）。
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .expect("crate 应位于 <仓库根>/crates/fml-error")
        .to_path_buf()
}

/// 读取仓库内文件。
fn read(rel: &str) -> String {
    let path = repo_root().join(rel);
    std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("读取 {} 失败：{e}", path.display()))
}

/// 仓库内路径是否存在。
fn exists(rel: &str) -> bool {
    repo_root().join(rel).exists()
}

/// 递归收集目录下的文件（相对仓库根）。
fn collect_files(rel_dir: &str, out: &mut Vec<String>) {
    let dir = repo_root().join(rel_dir);
    let Ok(entries) = std::fs::read_dir(&dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            collect_files(&path.to_string_lossy(), out);
        } else if let Ok(relative) = path.strip_prefix(repo_root()) {
            out.push(relative.to_string_lossy().replace('\\', "/"));
        }
    }
}

/// 列出目录下的直接子目录名（排序）。
fn subdirs(rel_dir: &str) -> Vec<String> {
    let mut out = Vec::new();
    if let Ok(entries) = std::fs::read_dir(repo_root().join(rel_dir)) {
        for entry in entries.flatten() {
            if entry.path().is_dir() {
                out.push(entry.file_name().to_string_lossy().to_string());
            }
        }
    }
    out.sort();
    out
}

/// 取分节正文（从 `[header]` 到下一个 `[` 行）。
fn section<'a>(text: &'a str, header: &str) -> &'a str {
    let needle = format!("\n{header}\n");
    let start = match text.find(&needle) {
        Some(index) => index + needle.len(),
        None => {
            let head = format!("{header}\n");
            match text.strip_prefix(&head) {
                Some(_) => head.len(),
                None => return "",
            }
        }
    };
    let rest = &text[start..];
    let end = rest
        .find("\n[")
        .map(|index| index + 1)
        .unwrap_or(rest.len());
    &rest[..end]
}

/// 取分节里 `key = value` 的右值。
fn kv<'a>(block: &'a str, key: &str) -> Option<&'a str> {
    block.lines().find_map(|line| {
        let (k, v) = line.split_once('=')?;
        if k.trim() == key {
            Some(v.trim())
        } else {
            None
        }
    })
}

/// 取出文本里所有双引号字符串。
fn quoted(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut current = String::new();
    let mut inside = false;
    for ch in text.chars() {
        match ch {
            '"' => {
                if inside {
                    out.push(std::mem::take(&mut current));
                }
                inside = !inside;
            }
            _ if inside => current.push(ch),
            _ => {}
        }
    }
    out
}

/// 运行 cargo metadata（离线、按锁文件）。
fn cargo_metadata(no_deps: bool) -> Value {
    let mut command = Command::new("cargo");
    command.current_dir(repo_root()).args([
        "metadata",
        "--format-version",
        "1",
        "--locked",
        "--offline",
    ]);
    if no_deps {
        command.arg("--no-deps");
    }
    let output = command.output().expect("无法执行 cargo metadata");
    assert!(
        output.status.success(),
        "cargo metadata 失败：{}",
        String::from_utf8_lossy(&output.stderr)
    );
    serde_json::from_slice(&output.stdout).expect("cargo metadata 输出不是合法 JSON")
}

/// 把 "MIT OR Apache-2.0" 拆成标识符。
///
/// 斜杠是旧式的 OR 写法（如 arraydeque 声明的 "MIT/Apache-2.0"），同样按两项抄录。
fn license_tokens(expression: &str) -> Vec<String> {
    expression
        .replace(['(', ')'], " ")
        .split(" OR ")
        .flat_map(|part| part.split(" AND "))
        .flat_map(|part| part.split('/'))
        .map(|token| token.trim().to_string())
        .filter(|token| !token.is_empty())
        .collect()
}

/// 已安装的 cargo-deny 版本（先直接调用子命令二进制，再退回 cargo deny）。
fn cargo_deny_version() -> String {
    let direct = Command::new("cargo-deny").arg("--version").output();
    let output = match direct {
        Ok(output) if output.status.success() => output,
        _ => {
            let output = Command::new("cargo")
                .args(["deny", "--version"])
                .output()
                .expect("无法执行 cargo deny --version");
            assert!(
                output.status.success(),
                "cargo deny --version 失败：{}",
                String::from_utf8_lossy(&output.stderr)
            );
            output
        }
    };
    String::from_utf8_lossy(&output.stdout)
        .split_whitespace()
        .last()
        .expect("cargo deny --version 输出为空")
        .to_string()
}
#[test]
fn workspace_members_are_only_fml_error() {
    let metadata = cargo_metadata(true);
    let mut names: Vec<String> = metadata["packages"]
        .as_array()
        .expect("packages 应为数组")
        .iter()
        .map(|package| {
            package["name"]
                .as_str()
                .expect("包名应为字符串")
                .to_string()
        })
        .collect();
    names.sort();
    assert_eq!(
        names,
        vec!["fml-error".to_string()],
        "工作区成员只能有本卡建出的 fml-error"
    );
    assert!(!exists("server"), "server/ 由 CORE-22 创建，本卡不得预建");
    assert_eq!(
        subdirs("crates"),
        vec!["fml-error".to_string()],
        "crates/ 下只能有 fml-error"
    );
}

#[test]
fn fml_error_is_docs_and_lint_skeleton_only() {
    let lib = read("crates/fml-error/src/lib.rs");
    assert!(
        lib.contains("#![forbid(unsafe_code)]"),
        "领域 crate 必须 forbid(unsafe_code)"
    );
    assert!(
        lib.contains("#![deny(missing_docs)]"),
        "missing_docs 必须用 crate 属性显式声明"
    );
    for forbidden in [
        "pub fn",
        "pub struct",
        "pub enum",
        "pub trait",
        "pub type",
        "pub const",
        "pub static",
        "pub use",
    ] {
        assert!(
            !lib.contains(forbidden),
            "CORE-01 骨架不得声明公共项，发现：{forbidden}"
        );
    }

    let manifest = read("crates/fml-error/Cargo.toml");
    assert!(
        manifest.contains("publish = false"),
        "自有 crate 必须标为未发布"
    );
    assert!(
        section(&manifest, "[lints]").contains("workspace = true"),
        "骨架必须显式继承 workspace.lints"
    );

    let readme = read("crates/fml-error/README.md");
    for needle in ["边界", "线程模型", "错误语义", "当前状态"] {
        assert!(readme.contains(needle), "crate README 缺少：{needle}");
    }
}

#[test]
fn root_manifest_declares_workspace_contract() {
    let manifest = read("Cargo.toml");
    let workspace = section(&manifest, "[workspace]");
    assert_eq!(kv(workspace, "resolver"), Some("\"2\""), "resolver 应为 2");
    assert_eq!(
        kv(workspace, "members"),
        Some("[\"crates/*\"]"),
        "members 应为 crates/*"
    );

    let package = section(&manifest, "[workspace.package]");
    assert_eq!(kv(package, "version"), Some("\"0.1.0\""));
    assert!(
        kv(package, "edition").is_some(),
        "workspace.package 必须声明 edition"
    );

    let dependencies = section(&manifest, "[workspace.dependencies]");
    // serde 随策略读取改成 yaml-rust2 后不再有消费者，卡 :93 的
    // workspace-dependencies unused = deny 不允许留无人使用的共享依赖条目。
    for name in ["serde_json", "yaml-rust2"] {
        assert!(
            kv(dependencies, name).is_some(),
            "workspace.dependencies 缺少：{name}"
        );
    }

    let lints = section(&manifest, "[workspace.lints.rust]");
    assert_eq!(kv(lints, "missing_docs"), Some("\"deny\""));
    assert_eq!(kv(lints, "unsafe_code"), Some("\"forbid\""));
}

#[test]
fn app_is_shell_only() {
    assert!(exists("app/pubspec.yaml"), "缺少 app/pubspec.yaml");
    assert!(exists("app/lib/main.dart"), "缺少 app/lib/main.dart");
    assert!(
        read("app/analysis_options.yaml").contains("public_member_api_docs: true"),
        "analysis_options 必须显式启用 public_member_api_docs"
    );

    let mut libs = Vec::new();
    collect_files("app/lib", &mut libs);
    assert_eq!(
        libs,
        vec!["app/lib/main.dart".to_string()],
        "app/lib 只允许空壳 main.dart"
    );

    for platform in ["android", "windows", "linux", "macos", "ios"] {
        assert!(
            !exists(&format!("app/{platform}")),
            "平台原生工程由平台卡生成，本卡不得预建 app/{platform}"
        );
    }
    assert!(!exists("app/android/toolchain.versions"));
    assert!(!exists("app/windows/toolchain.versions"));

    let main = read("app/lib/main.dart");
    assert!(
        main.contains("import 'package:flutter/material.dart';"),
        "空壳应只依赖 Flutter 框架本身的界面库"
    );
    let imports: Vec<&str> = main
        .lines()
        .map(str::trim)
        .filter(|line| line.starts_with("import "))
        .collect();
    assert_eq!(imports.len(), 1, "空壳只允许一条 import：{imports:?}");
    for forbidden in ["dart:io", "defaultTargetPlatform", "binding/", "platform/"] {
        assert!(
            imports.iter().all(|line| !line.contains(forbidden)),
            "空壳不得引用：{forbidden}"
        );
    }
}

#[test]
fn toolchain_and_version_files_are_recorded() {
    let toolchain = read("rust-toolchain.toml");
    assert_eq!(
        kv(&toolchain, "channel"),
        Some("\"stable\""),
        "工程样品阶段 Rust channel 为 stable（ADR-V5-15 修订，附录D D.14.8 RL-02）"
    );
    let components = kv(&toolchain, "components").expect("必须声明 components");
    assert!(
        components.contains("\"rustfmt\""),
        "components 必须含 rustfmt"
    );
    assert!(
        components.contains("\"clippy\""),
        "components 必须含 clippy"
    );

    let flutter = read("app/.flutter-version");
    assert_eq!(flutter.trim(), "3.47.7", "Flutter 版本文件只含单行版本");
    assert_eq!(flutter.lines().count(), 1, ".flutter-version 只能有一行");

    let versions = read("tools/toolchain.versions");
    let mut parsed = BTreeMap::new();
    for line in versions
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
    {
        let (key, value) = line
            .split_once('=')
            .unwrap_or_else(|| panic!("非法行：{line}"));
        assert!(
            parsed.insert(key.to_string(), value.to_string()).is_none(),
            "重复键：{key}"
        );
    }
    let expected_keys: BTreeSet<String> = [
        "queried_date",
        "python",
        "node",
        "fuzz_nightly",
        "cargo_fuzz",
        "cargo_deny",
    ]
    .iter()
    .map(|key| (*key).to_string())
    .collect();
    assert_eq!(
        parsed.keys().cloned().collect::<BTreeSet<String>>(),
        expected_keys,
        "tools/toolchain.versions 的键集合必须与卡一致"
    );
    assert_eq!(parsed["python"], "3.14.6");
    assert_eq!(parsed["node"], "24.18.0");
    assert_eq!(parsed["fuzz_nightly"], "2026-10-22");
    assert_eq!(parsed["cargo_fuzz"], "0.13.2");
    assert_eq!(parsed["cargo_deny"], "0.20.2");

    let queried = &parsed["queried_date"];
    let parts: Vec<&str> = queried.split('-').collect();
    assert_eq!(parts.len(), 3, "queried_date 必须是 YYYY-MM-DD：{queried}");
    assert_eq!(parts[0].len(), 4);
    assert_eq!(parts[1].len(), 2);
    assert_eq!(parts[2].len(), 2);
    assert!(queried.chars().all(|c| c.is_ascii_digit() || c == '-'));

    let requirements = read("tools/requirements.txt");
    for line in requirements
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
    {
        let (name, version) = line
            .split_once("==")
            .unwrap_or_else(|| panic!("Python 依赖必须精确锁定：{line}"));
        assert!(
            !name.is_empty() && !version.is_empty(),
            "非法依赖行：{line}"
        );
        assert!(
            version.chars().next().is_some_and(|c| c.is_ascii_digit()),
            "版本必须精确：{line}"
        );
    }
    assert!(
        requirements.contains("PyYAML==6.0.3"),
        "PyYAML 必须锁定 6.0.3"
    );

    // 工程样品阶段：cargo-deny 版本与记录值不一致只告警（测试方案第 3 条，附录D D.14.8 RL-03）。
    let installed = cargo_deny_version();
    if installed != parsed["cargo_deny"] {
        eprintln!(
            "警告：已安装 cargo-deny {installed} 与 tools/toolchain.versions 记录的 {} 不一致（工程样品阶段只告警）",
            parsed["cargo_deny"]
        );
    }

    // 与附录 A 的 ADR-V5-15 回填一致（同一查询日期与同一组锁定值）。
    let appendix = read("SADD/附录A-架构决策与评审记录.md");
    assert!(
        appendix.contains("A.4.9 ADR-V5-15 锁版回填"),
        "附录 A 必须有 ADR-V5-15 的锁版回填小节"
    );
    assert!(
        appendix.contains("queried_date=2026-10-22"),
        "回填须记录查询日期"
    );
    for key in ["python", "node", "fuzz_nightly", "cargo_fuzz", "cargo_deny"] {
        let value = parsed
            .get(key)
            .map(String::as_str)
            .unwrap_or_else(|| panic!("tools/toolchain.versions 缺少 {key}"));
        assert!(appendix.contains(value), "附录 A 回填缺少 {key}={value}");
    }
    assert!(appendix.contains("3.47.7"), "附录 A 回填缺少 Flutter 版本");
}
#[test]
fn deny_toml_declares_four_domains_and_transcribes_lockfile_licenses() {
    let deny = read("deny.toml");

    let licenses = section(&deny, "[licenses]");
    let bans = section(&deny, "[bans]");
    let workspace_dependencies = section(&deny, "[bans.workspace-dependencies]");
    let sources = section(&deny, "[sources]");
    let advisories = section(&deny, "[advisories]");
    assert!(
        !licenses.is_empty() && !bans.is_empty() && !sources.is_empty() && !advisories.is_empty(),
        "licenses、bans、sources、advisories 四域必须同时启用"
    );

    let allow_region = licenses
        .split("allow = [")
        .nth(1)
        .and_then(|rest| rest.split(']').next())
        .expect("[licenses] 必须声明显式 allow 数组");
    let allow: BTreeSet<String> = quoted(allow_region).into_iter().collect();
    assert!(!allow.is_empty(), "allow 不得为空（当前锁文件含第三方包）");
    for entry in &allow {
        assert!(!entry.contains('*'), "allow 禁止通配：{entry}");
        assert!(
            !entry.contains("OR") && !entry.contains("AND"),
            "allow 必须逐项抄录，不得按大类放行：{entry}"
        );
    }
    assert!(
        licenses.contains("private") && licenses.contains("ignore = true"),
        "自有 crate 必须用 [licenses] private = {{ ignore = true }} 忽略"
    );
    assert_eq!(
        kv(licenses, "include-dev"),
        Some("true"),
        "include-dev 必须显式声明"
    );

    assert_eq!(kv(bans, "deny"), Some("[]"), "bans.deny 初始为空");
    assert_eq!(
        kv(bans, "multiple-versions"),
        Some("\"deny\""),
        "multiple-versions 必须为 deny"
    );
    assert_eq!(
        kv(bans, "wildcards"),
        Some("\"deny\""),
        "wildcards 必须为 deny"
    );
    assert_eq!(kv(workspace_dependencies, "duplicates"), Some("\"deny\""));
    assert_eq!(kv(workspace_dependencies, "unused"), Some("\"deny\""));

    // [[bans.skip]] 是唯一的豁免出口：出现时每条必须写 crate、版本区间与理由。
    // 本卡依赖树实测无重复版本，文件里不应出现该表；一旦出现仍要求逐条写全，不得裸豁免。
    let lines: Vec<&str> = deny.lines().collect();
    let mut skips = 0;
    for (at, line) in lines.iter().enumerate() {
        if line.trim() != "[[bans.skip]]" {
            continue;
        }
        skips += 1;
        let entry = lines[at + 1..]
            .iter()
            .take_while(|next| !next.trim_start().starts_with('['))
            .copied()
            .collect::<Vec<&str>>()
            .join("\n");
        for key in ["crate", "version", "reason"] {
            assert!(
                kv(&entry, key).is_some(),
                "第 {skips} 条 [[bans.skip]] 缺少 {key}（每条都要写 crate、版本区间与理由）"
            );
        }
    }
    assert_eq!(skips, 0, "当前依赖树无重复版本，不应使用 [[bans.skip]]");

    assert_eq!(kv(sources, "unknown-registry"), Some("\"deny\""));
    assert_eq!(kv(sources, "unknown-git"), Some("\"deny\""));
    assert_eq!(
        kv(sources, "allow-registry"),
        Some("[\"https://github.com/rust-lang/crates.io-index\"]"),
        "allow-registry 只能写 crates.io index"
    );
    assert_eq!(kv(sources, "allow-git"), Some("[]"));
    assert!(!sources.contains("private"), "sources 不设 private");

    // advisories：卡 :93 要求 vulnerability 与 yanked 均为 deny、ignore 为空。
    // cargo-deny 0.20.2 的 advisories 是 config v2：vulnerability、notice、severity-threshold
    // 三个级别键已被移除（写入即配置错误），漏洞告警固定按错误报告，等价于 deny，故不写该键；
    // unmaintained 与 unsound 只剩收录范围键，没有告警级写法，保持更严的默认值（不静默）。
    assert_eq!(
        kv(advisories, "yanked"),
        Some("\"deny\""),
        "yanked 必须为 deny"
    );
    assert_eq!(
        kv(advisories, "ignore"),
        Some("[]"),
        "advisories.ignore 必须为空，不得静默任何告警"
    );
    for removed in ["vulnerability", "notice", "severity-threshold"] {
        assert!(
            kv(advisories, removed).is_none(),
            "advisories.{removed} 在 cargo-deny 0.20.2 已移除，写入会让配置报错"
        );
    }

    // 抄录完备性：锁文件中第三方包的 SPDX 标识符集合与 allow 完全一致。
    let metadata = cargo_metadata(false);
    let mut lock_tokens: BTreeSet<String> = BTreeSet::new();
    for package in metadata["packages"].as_array().expect("packages 应为数组") {
        if package["source"].is_null() {
            continue;
        }
        let label = format!(
            "{} {}",
            package["name"].as_str().expect("包名"),
            package["version"].as_str().expect("版本")
        );
        let expression = package["license"]
            .as_str()
            .unwrap_or_else(|| panic!("第三方包缺少机器可读许可：{label}"));
        lock_tokens.extend(license_tokens(expression));
    }
    assert_eq!(
        allow, lock_tokens,
        "allow 必须与锁文件中第三方包的许可标识符集合一致（新增依赖时同步抄录）"
    );

    // 自有 crate 用 publish = false 标为未发布。
    let own = metadata["packages"]
        .as_array()
        .expect("packages")
        .iter()
        .find(|package| package["name"] == json!("fml-error"))
        .expect("metadata 缺少 fml-error");
    assert_eq!(own["publish"], json!([]), "fml-error 必须 publish = false");
}

const BANNED: &[&str] = &["yolo", "ultralytics", "darknet"];
const WEIGHTS: &[&str] = &[".onnx", ".weights", ".pt"];

/// 扫描文本里的 YOLO 专用依赖与权重痕迹（大小写不敏感）。
fn yolo_hits(text: &str) -> Vec<String> {
    let lower = text.to_lowercase();
    let mut found: Vec<String> = BANNED
        .iter()
        .chain(WEIGHTS.iter())
        .filter(|needle| lower.contains(**needle))
        .map(|needle| (*needle).to_string())
        .collect();
    found.sort();
    found.dedup();
    found
}

#[test]
fn no_yolo_specific_dependency_or_implementation() {
    // 反例：合成命中必须被发现，普通公式文本不得误报。
    assert!(
        !yolo_hits("dep = yolo").is_empty(),
        "合成 YOLO 依赖必须命中"
    );
    assert!(
        !yolo_hits("model = detector.onnx").is_empty(),
        "权重文件必须命中"
    );
    assert!(yolo_hits("x^2 + 1").is_empty(), "普通公式文本不得命中");
    assert!(yolo_hits("FormulaNode").is_empty(), "领域类型名不得命中");

    let mut files = vec![
        "Cargo.toml".to_string(),
        "Cargo.lock".to_string(),
        "app/pubspec.yaml".to_string(),
    ];
    for root in ["crates", "app/lib"] {
        let mut found = Vec::new();
        collect_files(root, &mut found);
        files.extend(found.into_iter().filter(|path| {
            (path.ends_with(".rs") && !path.contains("/tests/")) || path.ends_with(".dart")
        }));
    }
    files.sort();
    files.dedup();

    for file in files {
        let found = yolo_hits(&read(&file));
        assert!(
            found.is_empty(),
            "{file} 含 YOLO 专用依赖或实现痕迹：{found:?}"
        );
    }
}

#[test]
fn versions_are_semver_core_and_match_between_manifests() {
    fn is_semver_core(version: &str) -> bool {
        let parts: Vec<&str> = version.split('.').collect();
        parts.len() == 3
            && parts
                .iter()
                .all(|part| !part.is_empty() && part.chars().all(|c| c.is_ascii_digit()))
    }

    let cargo = read("Cargo.toml");
    let cargo_version = kv(section(&cargo, "[workspace.package]"), "version")
        .expect("workspace.package.version")
        .trim_matches('"');
    assert!(
        is_semver_core(cargo_version),
        "workspace 版本必须是 SemVer：{cargo_version}"
    );

    let pubspec = read("app/pubspec.yaml");
    let pubspec_version = pubspec
        .lines()
        .find_map(|line| line.trim().strip_prefix("version:"))
        .expect("pubspec.yaml 缺少 version")
        .trim();
    let core = pubspec_version.split('+').next().unwrap_or_default();
    assert!(
        is_semver_core(core),
        "pubspec 版本必须是 SemVer：{pubspec_version}"
    );
    assert_eq!(
        core, cargo_version,
        "pubspec 与 workspace 的主版本主体必须一致"
    );
}
