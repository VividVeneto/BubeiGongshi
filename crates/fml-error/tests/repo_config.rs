//! CORE-01 测试方案第 1、2、3、6、7 条：仓库骨架、工程配置、锁版与依赖清单断言。
//!
//! 本测试只读仓库文件与 cargo 元数据，不实现检查器（CORE-69/CORE-41 消费同一批文件）。
//!
//! “仅本卡产物”按卡的合法范围解释（差异留档见
//! `temp/review/s0r1-core01-expansion-fix/卡片问题留档.md`）：后续卡新增 crate、`app/lib` 目录与
//! 平台原生工程，只要仍在 CORE-01 卡给出的成员清单（`contracts/policies/dep-allow.yaml` 预留键）、
//! 依赖上界、目录布局与 lint 约束内即通过；未登记成员、越级依赖、缺基座文件、布局外路径与放宽
//! lint 仍判失败。判据集中在下面的纯函数里，仓库断言与夹具断言共用同一套。

use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;
use std::process::Command;

use serde_json::{Value, json};
use yaml_rust2::YamlLoader;

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
// ---------------------------------------------------------------------------
// 骨架包含式判据：CORE-01 卡给的是合法范围，不是“本卡产物清单”。
// ---------------------------------------------------------------------------

/// CORE-01 卡列出的 app/lib 非特性顶层目录（子树由对应卡填充）。
const APP_LIB_RESERVED_DIRS: &[&str] = &["binding", "ports", "composition", "render", "l10n"];

/// CORE-01 卡列出的 app/lib/<feature> 特性目录。
const APP_LIB_FEATURES: &[&str] = &[
    "account",
    "sync",
    "recognition",
    "study",
    "study_stats",
    "library",
    "editor",
    "calc",
    "packs",
    "settings",
    "privacy",
    "export",
    "net",
    "design",
];

/// CORE-01 卡列出的 app/lib/ui/<feature> 界面目录。
const APP_UI_FEATURES: &[&str] = &[
    "shell",
    "design",
    "editor",
    "library",
    "study",
    "study_stats",
    "books",
    "calc",
    "packs",
    "recognition",
    "settings",
];

/// 卡允许出现受审计 unsafe 的 crate；其余 crate 必须 `#![forbid(unsafe_code)]`。
const AUDITED_UNSAFE_CRATES: &[&str] = &["fml-ffi", "fml-imgproc", "fml-recognize-local"];

/// 平台原生工程目录：共享界面只面向 Windows 与 Android。
const APP_PLATFORM_DIRS: &[&str] = &["android", "windows"];

/// 读 contracts/policies/dep-allow.yaml 的 crates 映射：crate → 允许的本仓库直接依赖。
///
/// 这份上界表是成员清单与依赖上界的唯一来源，CORE-69 消费同一文件。
fn dep_allow_registry() -> BTreeMap<String, BTreeSet<String>> {
    let text = read("contracts/policies/dep-allow.yaml");
    let documents = YamlLoader::load_from_str(&text)
        .unwrap_or_else(|e| panic!("dep-allow.yaml 不是合法 YAML：{e}"));
    assert_eq!(
        documents.len(),
        1,
        "dep-allow.yaml 必须恰好包含一个 YAML 文档"
    );
    let crates = documents[0]["crates"]
        .as_hash()
        .unwrap_or_else(|| panic!("dep-allow.yaml 缺少 crates 映射"));
    let mut registry = BTreeMap::new();
    for (key, value) in crates {
        let name = key
            .as_str()
            .unwrap_or_else(|| panic!("crates 的键必须是字符串：{key:?}"))
            .to_string();
        let allowed: BTreeSet<String> = value
            .as_vec()
            .unwrap_or_else(|| panic!("{name} 的允许上界必须是数组"))
            .iter()
            .map(|item| {
                item.as_str()
                    .unwrap_or_else(|| panic!("{name} 的允许项必须是字符串"))
                    .to_string()
            })
            .collect();
        registry.insert(name, allowed);
    }
    registry
}

/// app/lib 下的相对路径是否落在 CORE-01 布局内；合法返回 None，否则返回违例说明。
fn app_lib_path_violation(path: &str) -> Option<String> {
    let Some(rest) = path.strip_prefix("app/lib/") else {
        return Some(format!("{path} 不在 app/lib 下"));
    };
    let parts: Vec<&str> = rest.split('/').collect();
    let Some(top) = parts.first().copied() else {
        return Some(format!("app/lib 下缺少文件名：{path}"));
    };
    if parts.len() == 1 {
        // 顶层只有空壳 main.dart 与平台卡写入的 main_<平台>.dart。
        return if top == "main.dart" || (top.starts_with("main_") && top.ends_with(".dart")) {
            None
        } else {
            Some(format!(
                "app/lib/ 顶层只允许 main.dart 与 main_<平台>.dart：{path}"
            ))
        };
    }
    if top == "platform" {
        // 平台实现只按端口落到 android/、windows/。
        return match parts.get(1) {
            Some(platform) if APP_PLATFORM_DIRS.contains(platform) && parts.len() > 2 => None,
            _ => Some(format!(
                "app/lib/platform/ 下只允许 android/ 与 windows/，且需落到具体文件：{path}"
            )),
        };
    }
    if top == "ui" {
        let Some(feature) = parts.get(1) else {
            return Some(format!("app/lib/ui/ 下必须是 <feature>/<文件>：{path}"));
        };
        // 界面目录不另立白名单：<feature> 必须在本卡的 <feature> 名单里（CORE-01:29 的
        // 11 个界面名与 lib/<feature> 名的并集），CORE-63:25 的 ui/account/ 因此也在内。
        let known_feature = APP_UI_FEATURES.contains(feature) || APP_LIB_FEATURES.contains(feature);
        return if !known_feature {
            Some(format!(
                "app/lib/ui/{feature}/ 不在 CORE-01 的 <feature> 名单内（lib/<feature> ∪ ui/<feature>）：{path}"
            ))
        } else if parts.len() == 2 {
            Some(format!("app/lib/ui/{feature}/ 下必须落到文件：{path}"))
        } else {
            None
        };
    }
    if APP_LIB_RESERVED_DIRS.contains(&top) || APP_LIB_FEATURES.contains(&top) {
        None
    } else {
        Some(format!("app/lib/{top}/ 不在 CORE-01 布局内：{path}"))
    }
}

/// 一个工作区成员的最小事实集（仓库断言与夹具断言共用同一判据）。
struct MemberFacts<'a> {
    /// Cargo 包名。
    name: &'a str,
    /// 清单路径（绝对或相对皆可，判据按路径尾部比对）。
    manifest_path: &'a str,
    /// 清单正文。
    manifest: &'a str,
    /// `src/lib.rs` 正文；库 crate 没有该文件时为 None。
    lib: Option<&'a str>,
    /// `src/main.rs` 正文；二进制成员（CORE-22 的 fml-server）只有它。
    ///
    /// CORE-22:108 的 server 主包是 `server/src/{main.rs,config.rs,...}`，SADD 全文没有
    /// `server/src/lib.rs`，故基座文件按“lib.rs 或 main.rs 二选一”判定。
    main: Option<&'a str>,
    /// 本仓库内的直接依赖包名（cargo metadata 中 source 为 null 的那些）。
    local_deps: &'a [String],
}

/// 成员清单是否落在 `crates/<name>/Cargo.toml`，或 server 成员落在 `server/Cargo.toml`。
fn manifest_location_ok(name: &str, manifest_path: &str) -> bool {
    let path = manifest_path.replace('\\', "/");
    let path = path.trim_start_matches("./");
    if name == "fml-server" {
        path == "server/Cargo.toml" || path.ends_with("/server/Cargo.toml")
    } else {
        let expected = format!("crates/{name}/Cargo.toml");
        path == expected || path.ends_with(&format!("/{expected}"))
    }
}

/// `// SAFETY: 说明` 里的说明正文；没有说明或不是 SAFETY 注释时返回 None。
fn safety_text(comment: &str) -> Option<&str> {
    let rest = comment.trim().strip_prefix("//")?.trim_start();
    let note = rest.strip_prefix("SAFETY:")?.trim();
    (!note.is_empty()).then_some(note)
}

/// 收集没有 `// SAFETY:` 说明的 `unsafe` 块（CORE-01:133）。
///
/// 按行判定：代码位置出现 `unsafe` 关键字（`unsafe {`、`unsafe fn/impl/trait/extern`）时，
/// 本行行尾或起始行前 3 行内（CORE-74:14 的窗口口径）必须有非空 `// SAFETY:`；
/// 空行、普通语句或属性隔开不影响判定，`unsafe_code` 这类 lint 名不算块。
fn unsafe_blocks_without_safety(source: &str) -> Vec<String> {
    const BLOCK_MARKERS: &[&str] = &[
        "unsafe {",
        "unsafe{",
        "unsafe fn ",
        "unsafe impl ",
        "unsafe trait ",
        "unsafe extern ",
    ];
    // CORE-74:14：unsafe 起始行前 3 行内的非空 `// SAFETY:` 都算数。
    const SAFETY_WINDOW: usize = 3;
    let lines: Vec<&str> = source.lines().collect();
    let mut missing = Vec::new();
    for (at, line) in lines.iter().enumerate() {
        let code = line.split("//").next().unwrap_or_default();
        if !BLOCK_MARKERS.iter().any(|marker| code.contains(marker)) {
            continue;
        }
        let trailing = &line[code.len()..];
        let has_safety = safety_text(trailing).is_some()
            || lines[at.saturating_sub(SAFETY_WINDOW)..at]
                .iter()
                .any(|above| safety_text(above.trim()).is_some());
        if !has_safety {
            missing.push(format!("第 {} 行 {}", at + 1, line.trim()));
        }
    }
    missing
}

/// 成员的必需要素与依赖上界检查；返回全部违例（空表示合法）。
fn member_violations(
    member: &MemberFacts<'_>,
    registry: &BTreeMap<String, BTreeSet<String>>,
) -> Vec<String> {
    let name = member.name;
    // 受审计 unsafe crate 不能继承根 workspace.lints：unsafe_code = "forbid" 经 CLI -F 生效、
    // crate 属性无法覆盖，CORE-01:133 让它们改用逐块 // SAFETY:（真实 cargo 最小例见修复报告 B1）。
    let audited = AUDITED_UNSAFE_CRATES.contains(&name);
    let mut violations = Vec::new();
    let registered = registry.get(name);
    if registered.is_none() {
        violations.push(format!(
            "{name} 未在 contracts/policies/dep-allow.yaml 预留清单登记"
        ));
    }
    if !manifest_location_ok(name, member.manifest_path) {
        let expected = if name == "fml-server" {
            "server/Cargo.toml".to_string()
        } else {
            format!("crates/{name}/Cargo.toml")
        };
        violations.push(format!(
            "{name} 的清单路径应为 {expected}，实际 {}",
            member.manifest_path
        ));
    }
    if kv(section(member.manifest, "[package]"), "publish") != Some("false") {
        violations.push(format!("{name} 必须声明 publish = false"));
    }
    // CORE-01:93 要求 crate 显式继承 workspace.lints；受审计 crate 例外（见上）。
    if !audited && kv(section(member.manifest, "[lints]"), "workspace") != Some("true") {
        violations.push(format!("{name} 必须 [lints] workspace = true"));
    }
    // 基座文件：库 crate 看 src/lib.rs，二进制成员（CORE-22 的 fml-server）看 src/main.rs。
    let sources: Vec<&str> = member.lib.into_iter().chain(member.main).collect();
    if sources.is_empty() {
        violations.push(format!("{name} 缺少基座文件 src/lib.rs 或 src/main.rs"));
    }
    if let Some(lib) = member.lib {
        if !lib.contains("#![deny(missing_docs)]") {
            violations.push(format!("{name} 的 src/lib.rs 必须 #![deny(missing_docs)]"));
        }
        if !audited && !lib.contains("#![forbid(unsafe_code)]") {
            violations.push(format!(
                "{name} 不在受审计 unsafe 名单（{AUDITED_UNSAFE_CRATES:?}），src/lib.rs 必须 #![forbid(unsafe_code)]"
            ));
        }
    }
    if audited {
        for source in &sources {
            let missing = unsafe_blocks_without_safety(source);
            if !missing.is_empty() {
                violations.push(format!(
                    "{name} 的 unsafe 块缺非空 // SAFETY: 注释（CORE-01:133）：{}",
                    missing.join("；")
                ));
            }
        }
    }
    if let Some(allowed) = registered {
        for dep in member.local_deps {
            if dep == name {
                violations.push(format!("{name} 不得依赖自身"));
            } else if !allowed.contains(dep) {
                violations.push(format!(
                    "{name} 不得依赖 {dep}：dep-allow.yaml 的允许上界为 {allowed:?}"
                ));
            }
        }
    }
    violations
}

/// 成员集合的检查：基座 fml-error 必须在，成员必须已登记。
fn workspace_violations(
    names: &BTreeSet<String>,
    registry: &BTreeMap<String, BTreeSet<String>>,
) -> Vec<String> {
    let mut violations = Vec::new();
    if !names.contains("fml-error") {
        violations.push("基座 crate fml-error 必须是工作区成员".to_string());
    }
    for name in names {
        if !registry.contains_key(name) {
            violations.push(format!(
                "{name} 未在 contracts/policies/dep-allow.yaml 预留清单登记"
            ));
        }
    }
    violations
}

/// app 空壳与布局的最小事实集。
struct AppShell<'a> {
    /// app/lib 下的全部文件（相对仓库根，'/' 分隔）。
    files: &'a [String],
    /// app/lib/main.dart 正文（缺失时传空串）。
    main_dart: &'a str,
    /// app/analysis_options.yaml 正文（缺失时传空串）。
    analysis_options: &'a str,
}

/// 单个 Dart 文件的 import 限制：视图不 import binding/、platform/，共享界面不发起 HTTP。
///
/// 只扫 `import` 行；符号级与传输层检查归 CORE-69 的静态检查工具。
fn app_import_violations(path: &str, text: &str) -> Vec<String> {
    let in_ui = path.starts_with("app/lib/ui/");
    let mut violations = Vec::new();
    for line in text.lines().map(str::trim) {
        let Some(rest) = line.strip_prefix("import ") else {
            continue;
        };
        // 视图可以只读引用 CORE-67 生成的纯数据 DTO。
        if in_ui && rest.contains("binding/dto/") && rest.contains(".g.dart") {
            continue;
        }
        let forbidden: &[&str] = if in_ui {
            &[
                "binding/",
                "platform/",
                "dart:io",
                "package:http/",
                "package:dio/",
            ]
        } else {
            &[
                "binding/",
                "platform/",
                "dart:io",
                "dart:ffi",
                "package:http/",
            ]
        };
        for needle in forbidden {
            if rest.contains(needle) {
                violations.push(format!("{path} 不得 import {needle}：{line}"));
            }
        }
    }
    violations
}

/// app 空壳必须保留的基座文件与布局约束。
fn app_shell_violations(shell: &AppShell<'_>) -> Vec<String> {
    let mut violations = Vec::new();
    if !shell
        .analysis_options
        .contains("public_member_api_docs: true")
    {
        violations
            .push("app/analysis_options.yaml 必须显式启用 public_member_api_docs".to_string());
    }
    let mut has_main = false;
    for path in shell.files {
        if path == "app/lib/main.dart" {
            has_main = true;
        }
        if let Some(violation) = app_lib_path_violation(path) {
            violations.push(violation);
        }
    }
    if !has_main {
        violations.push("缺少基座文件 app/lib/main.dart".to_string());
    }
    if !shell
        .main_dart
        .contains("import 'package:flutter/material.dart';")
    {
        violations.push(
            "app/lib/main.dart 必须 import 'package:flutter/material.dart';（空壳只依赖 Flutter 界面库）"
                .to_string(),
        );
    }
    violations.extend(app_import_violations("app/lib/main.dart", shell.main_dart));
    violations
}

#[test]
fn workspace_members_stay_within_core01_layout() {
    let registry = dep_allow_registry();
    assert!(
        registry.contains_key("fml-error"),
        "dep-allow.yaml 必须预留基座 crate fml-error"
    );

    let metadata = cargo_metadata(true);
    let packages = metadata["packages"].as_array().expect("packages 应为数组");
    let mut names = BTreeSet::new();
    let mut violations = Vec::new();
    for package in packages {
        let name = package["name"]
            .as_str()
            .expect("包名应为字符串")
            .to_string();
        let manifest_path = package["manifest_path"]
            .as_str()
            .expect("manifest_path 应为字符串");
        // 成员清单必须在 crates/<name>/ 或 server/（判据见 manifest_location_ok）。
        let dir = if name == "fml-server" {
            "server".to_string()
        } else {
            format!("crates/{name}")
        };
        let manifest_rel = format!("{dir}/Cargo.toml");
        let lib_rel = format!("{dir}/src/lib.rs");
        let main_rel = format!("{dir}/src/main.rs");
        let manifest = if exists(&manifest_rel) {
            read(&manifest_rel)
        } else {
            String::new()
        };
        let lib = exists(&lib_rel).then(|| read(&lib_rel));
        // CORE-22 的 fml-server 只有 src/main.rs（binary-only）。
        let main = exists(&main_rel).then(|| read(&main_rel));
        // cargo metadata --no-deps 里 source 为 null 的依赖就是本仓库的 path 依赖。
        let local_deps: Vec<String> = package["dependencies"]
            .as_array()
            .expect("dependencies 应为数组")
            .iter()
            .filter(|dependency| dependency["source"].is_null())
            .map(|dependency| {
                dependency["name"]
                    .as_str()
                    .expect("依赖名应为字符串")
                    .to_string()
            })
            .collect();
        let facts = MemberFacts {
            name: &name,
            manifest_path,
            manifest: &manifest,
            lib: lib.as_deref(),
            main: main.as_deref(),
            local_deps: &local_deps,
        };
        violations.extend(member_violations(&facts, &registry));
        names.insert(name);
    }
    violations.extend(workspace_violations(&names, &registry));

    // crates/ 下每个目录都必须是成员：目录名即包名（由清单路径判据保证）。
    for dir in subdirs("crates") {
        assert!(
            names.contains(&dir),
            "crates/{dir}/ 未成为工作区成员：{names:?}"
        );
    }
    // server/ 由 CORE-22 创建并追加为成员；未创建时不预列，创建后不得只存在于目录。
    if exists("server") {
        assert!(
            exists("server/Cargo.toml"),
            "server/ 存在时必须建为工作区成员"
        );
        assert!(
            names.contains("fml-server"),
            "server/ 存在时必须由 CORE-22 追加为成员 fml-server"
        );
    }
    assert!(violations.is_empty(), "工作区成员违例：\n{violations:#?}");
}

#[test]
fn fml_error_keeps_docs_and_lint_attributes() {
    // CORE-02 把 CORE-01 的文档/lint 骨架替换成正式错误模型，属性与配置约束不变，
    // 只去掉“骨架不得声明公共项”这条随时间失效的断言。
    let lib = read("crates/fml-error/src/lib.rs");
    assert!(
        lib.contains("#![forbid(unsafe_code)]"),
        "领域 crate 必须 forbid(unsafe_code)"
    );
    assert!(
        lib.contains("#![deny(missing_docs)]"),
        "missing_docs 必须用 crate 属性显式声明"
    );

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
    // CORE-01:42：初始 members 只有 crates/*；CORE-22 首次建 server/Cargo.toml 时把
    // "server" 追加进来（NF1：这里不再要求精确等于 ["crates/*"]，其余追加项仍拒绝）。
    let member_entries = quoted(kv(workspace, "members").expect("workspace.members"));
    assert_eq!(
        member_entries.first().map(String::as_str),
        Some("crates/*"),
        "members 必须以 crates/* 开头"
    );
    for extra in &member_entries[1..] {
        assert_eq!(
            extra, "server",
            "members 只允许 CORE-22 追加的 server：{member_entries:?}"
        );
    }

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
fn app_shell_stays_within_layout() {
    assert!(exists("app/pubspec.yaml"), "缺少 app/pubspec.yaml");
    let mut files = Vec::new();
    collect_files("app/lib", &mut files);
    files.sort();
    let main_dart = if exists("app/lib/main.dart") {
        read("app/lib/main.dart")
    } else {
        String::new()
    };
    let analysis_options = if exists("app/analysis_options.yaml") {
        read("app/analysis_options.yaml")
    } else {
        String::new()
    };
    let violations = app_shell_violations(&AppShell {
        files: &files,
        main_dart: &main_dart,
        analysis_options: &analysis_options,
    });
    assert!(
        violations.is_empty(),
        "app 空壳与布局违例：\n{violations:#?}"
    );

    // 视图的 import 限制（只扫 import 行；符号级检查归 CORE-69）。
    let mut import_violations = Vec::new();
    for path in files.iter().filter(|path| path.starts_with("app/lib/ui/")) {
        import_violations.extend(app_import_violations(path, &read(path)));
    }
    assert!(
        import_violations.is_empty(),
        "视图 import 违例：\n{import_violations:#?}"
    );

    // 共享界面只面向 Windows 与 Android：其他平台原生工程不得出现。
    for platform in ["linux", "macos", "ios", "web"] {
        assert!(
            !exists(&format!("app/{platform}")),
            "共享界面只面向 Android 与 Windows，不得预建 app/{platform}"
        );
    }
    // 平台卡可以写 app/<平台>/toolchain.versions，但不得重复记录 Rust 与 Flutter 版本。
    for platform in APP_PLATFORM_DIRS {
        let rel = format!("app/{platform}/toolchain.versions");
        if !exists(&rel) {
            continue;
        }
        for line in read(&rel).lines() {
            let Some((key, _)) = line.split_once('=') else {
                continue;
            };
            let key = key.trim();
            assert!(
                !["rust", "rust_channel", "flutter", "flutter_version", "dart"].contains(&key),
                "{rel} 不得重复记录 {key} 版本：唯一来源是 rust-toolchain.toml 与 app/.flutter-version"
            );
        }
    }
}

/// 合法成员清单夹具：publish = false 且 [lints] workspace = true。
const LEGAL_MANIFEST: &str =
    "[package]\nname = \"fixture\"\npublish = false\n\n[lints]\nworkspace = true\n";

/// 受审计 unsafe crate 的清单夹具：publish = false 且不继承 workspace.lints。
///
/// 根 `workspace.lints.rust.unsafe_code = "forbid"` 经 CLI `-F unsafe-code` 生效，crate 属性
/// 无法覆盖；继承后 crate 里的 unsafe 块必然编译失败（真实 cargo 最小例见修复报告 B1）。
const LEGAL_AUDITED_MANIFEST: &str = "[package]\nname = \"fixture\"\npublish = false\n";

/// 合法领域 crate 的 lib.rs 夹具：禁 unsafe，公共项要有文档。
const LEGAL_LIB: &str =
    "#![forbid(unsafe_code)]\n#![deny(missing_docs)]\n\n/// 占位。\npub fn placeholder() {}\n";

/// 受审计 unsafe crate 的 lib.rs 夹具：与可编译形态一致，每个 unsafe 块带非空 SAFETY 说明。
const AUDITED_LIB: &str = "#![deny(missing_docs)]\n\n/// 占位。\npub fn read_at(pointer: *const u32) -> u32 {\n    // SAFETY: 调用方保证 pointer 有效且对齐。\n    unsafe { std::ptr::read(pointer) }\n}\n";

/// CORE-22 的 fml-server 入口夹具：binary-only，没有 src/lib.rs（SADD 无 server/src/lib.rs）。
const SERVER_MAIN: &str = "//! 服务端入口（CORE-22）。\n\nfn main() {}\n";

/// NF-A 夹具：CORE-74:14 的三行窗口写法（真实 cargo 最小审计 crate 的 src/lib.rs 全文）。
const WINDOW_SAFETY_LIB: &str = "//! NF-A 探针：CORE-74:14 的三行窗口 SAFETY 写法（与修复报告的证据 crate 同字节）。\n#![deny(missing_docs)]\n\n/// 紧邻注释（距 unsafe 行 1 行）。\npub fn read_adjacent(pointer: *const u32) -> u32 {\n    // SAFETY: 调用方保证 pointer 有效且对齐。\n    unsafe { std::ptr::read(pointer) }\n}\n\n/// 空行隔开（距 unsafe 行 2 行）。\npub fn read_across_blank(pointer: *const u32) -> u32 {\n    // SAFETY: 调用方保证 pointer 有效且对齐。\n\n    unsafe { std::ptr::read(pointer) }\n}\n\n/// 普通语句隔开（距 unsafe 行 2 行）。\npub fn read_across_statement(pointer: *const u32) -> u32 {\n    // SAFETY: 调用方保证 pointer 有效且对齐。\n    let offset: usize = 0;\n    unsafe { std::ptr::read(pointer.wrapping_add(offset)) }\n}\n\n/// 空行加语句隔开（距 unsafe 行 3 行）。\npub fn read_across_blank_and_statement(pointer: *const u32) -> u32 {\n    // SAFETY: 调用方保证 pointer 有效且对齐。\n    let offset: usize = 0;\n\n    unsafe { std::ptr::read(pointer.wrapping_add(offset)) }\n}\n";

/// 夹具用的本仓库依赖名列表。
fn deps(names: &[&str]) -> Vec<String> {
    names.iter().map(|name| name.to_string()).collect()
}

/// 夹具成员的违例文本（便于按关键字断言）。
fn joined_violations(
    member: &MemberFacts<'_>,
    registry: &BTreeMap<String, BTreeSet<String>>,
) -> String {
    member_violations(member, registry).join("\n")
}

#[test]
fn fixture_legal_expansion_is_accepted() {
    let registry = dep_allow_registry();

    // 后续卡的合法成员：crates/<name>/ 布局、依赖不越上界、lint 基座齐全。
    for (name, allowed) in [
        ("fml-ast", vec!["fml-error"]),
        ("fml-latex", vec!["fml-ast", "fml-error"]),
        (
            "fml-type",
            vec!["fml-ast", "fml-units", "fml-notation", "fml-error"],
        ),
    ] {
        let local_deps = deps(&allowed);
        let manifest_path = format!("crates/{name}/Cargo.toml");
        let facts = MemberFacts {
            name,
            manifest_path: &manifest_path,
            manifest: LEGAL_MANIFEST,
            lib: Some(LEGAL_LIB),
            main: None,
            local_deps: &local_deps,
        };
        let violations = member_violations(&facts, &registry);
        assert!(violations.is_empty(), "{name} 应被接受：{violations:#?}");
    }

    // 成员集合：基座 fml-error 仍在即合法。
    let names: BTreeSet<String> = ["fml-ast", "fml-error", "fml-latex"]
        .iter()
        .map(|name| name.to_string())
        .collect();
    let set_violations = workspace_violations(&names, &registry);
    assert!(set_violations.is_empty(), "{set_violations:#?}");

    // app/lib 的合法多目录扩展。
    for path in [
        "app/lib/main.dart",
        "app/lib/main_android.dart",
        "app/lib/main_windows.dart",
        "app/lib/binding/dto/types.g.dart",
        "app/lib/ports/share_port.dart",
        "app/lib/platform/android/http_client.dart",
        "app/lib/platform/windows/http_client.dart",
        "app/lib/composition/ports_android.dart",
        "app/lib/render/formula_painter.dart",
        "app/lib/l10n/errors_zh.arb",
        "app/lib/study/session.dart",
        "app/lib/ui/shell/shell_page.dart",
        "app/lib/ui/study/study_page.dart",
    ] {
        assert_eq!(app_lib_path_violation(path), None, "{path} 应被接受");
    }

    // 视图只读引用纯数据 DTO 仍然合法。
    let ui =
        "import 'package:flutter/material.dart';\nimport '../../../binding/dto/types.g.dart';\n";
    let ui_violations = app_import_violations("app/lib/ui/study/study_page.dart", ui);
    assert!(ui_violations.is_empty(), "{ui_violations:#?}");

    // 空壳与新特性目录同时存在时整体判据仍通过。
    let files: Vec<String> = [
        "app/lib/main.dart",
        "app/lib/study/session.dart",
        "app/lib/ui/shell/shell_page.dart",
    ]
    .iter()
    .map(|path| path.to_string())
    .collect();
    let shell = AppShell {
        files: &files,
        main_dart: "import 'package:flutter/material.dart';\n\nvoid main() {}\n",
        analysis_options: "linter:\n  rules:\n    public_member_api_docs: true\n",
    };
    let shell_violations = app_shell_violations(&shell);
    assert!(shell_violations.is_empty(), "{shell_violations:#?}");
}

#[test]
fn fixture_illegal_expansion_is_rejected() {
    let registry = dep_allow_registry();
    let none: Vec<String> = Vec::new();

    // 1. 未登记的新成员。
    let stray = MemberFacts {
        name: "fml-unknown",
        manifest_path: "crates/fml-unknown/Cargo.toml",
        manifest: LEGAL_MANIFEST,
        lib: Some(LEGAL_LIB),
        main: None,
        local_deps: &none,
    };
    assert!(
        joined_violations(&stray, &registry)
            .contains("未在 contracts/policies/dep-allow.yaml 预留清单登记")
    );

    // 2. 缺基座 fml-error。
    let names: BTreeSet<String> = ["fml-ast"].iter().map(|name| name.to_string()).collect();
    assert!(
        workspace_violations(&names, &registry)
            .join("\n")
            .contains("基座 crate fml-error 必须是工作区成员")
    );

    // 3. 清单文件不在 crates/<name>/ 或 server/。
    let stray_args = deps(&["fml-error"]);
    let misplaced = MemberFacts {
        name: "fml-ast",
        manifest_path: "crates/fml-latex/Cargo.toml",
        manifest: LEGAL_MANIFEST,
        lib: Some(LEGAL_LIB),
        main: None,
        local_deps: &stray_args,
    };
    assert!(
        joined_violations(&misplaced, &registry).contains("清单路径应为 crates/fml-ast/Cargo.toml")
    );

    // 4. 基座文件缺失：lib.rs 与 main.rs 都没有（只有其中一个即可，见合法夹具 fml-server）。
    let no_base = MemberFacts {
        name: "fml-ast",
        manifest_path: "crates/fml-ast/Cargo.toml",
        manifest: LEGAL_MANIFEST,
        lib: None,
        main: None,
        local_deps: &none,
    };
    assert!(
        joined_violations(&no_base, &registry).contains("缺少基座文件 src/lib.rs 或 src/main.rs")
    );
    // 5. 放宽 lint：publish 未关、缺 [lints]、缺 forbid(unsafe_code)、缺 missing_docs。
    let loose_manifest =
        "[package]\nname = \"fixture\"\npublish = true\n\n[lints]\nworkspace = true\n";
    let loose = MemberFacts {
        name: "fml-ast",
        manifest_path: "crates/fml-ast/Cargo.toml",
        manifest: loose_manifest,
        lib: Some("#![deny(missing_docs)]\n"),
        main: None,
        local_deps: &none,
    };
    let loose_text = joined_violations(&loose, &registry);
    assert!(
        loose_text.contains("必须声明 publish = false"),
        "{loose_text}"
    );
    assert!(
        loose_text.contains("src/lib.rs 必须 #![forbid(unsafe_code)]"),
        "{loose_text}"
    );

    let no_lints_manifest = "[package]\nname = \"fixture\"\npublish = false\n";
    let no_lints = MemberFacts {
        name: "fml-ast",
        manifest_path: "crates/fml-ast/Cargo.toml",
        manifest: no_lints_manifest,
        lib: Some(LEGAL_LIB),
        main: None,
        local_deps: &none,
    };
    assert!(joined_violations(&no_lints, &registry).contains("必须 [lints] workspace = true"));

    let no_docs = MemberFacts {
        name: "fml-ast",
        manifest_path: "crates/fml-ast/Cargo.toml",
        manifest: LEGAL_MANIFEST,
        lib: Some("#![forbid(unsafe_code)]\n"),
        main: None,
        local_deps: &none,
    };
    assert!(
        joined_violations(&no_docs, &registry).contains("src/lib.rs 必须 #![deny(missing_docs)]")
    );

    // 6. 非法依赖：基座 crate 无本仓库依赖、越级依赖、自依赖。
    let base_with_dep = MemberFacts {
        name: "fml-error",
        manifest_path: "crates/fml-error/Cargo.toml",
        manifest: LEGAL_MANIFEST,
        lib: Some(LEGAL_LIB),
        main: None,
        local_deps: &deps(&["fml-ast"]),
    };
    assert!(joined_violations(&base_with_dep, &registry).contains("不得依赖 fml-ast"));

    let reversed = MemberFacts {
        name: "fml-ast",
        manifest_path: "crates/fml-ast/Cargo.toml",
        manifest: LEGAL_MANIFEST,
        lib: Some(LEGAL_LIB),
        main: None,
        local_deps: &deps(&["fml-type"]),
    };
    assert!(joined_violations(&reversed, &registry).contains("不得依赖 fml-type"));

    let self_dep = MemberFacts {
        name: "fml-ast",
        manifest_path: "crates/fml-ast/Cargo.toml",
        manifest: LEGAL_MANIFEST,
        lib: Some(LEGAL_LIB),
        main: None,
        local_deps: &deps(&["fml-ast"]),
    };
    assert!(joined_violations(&self_dep, &registry).contains("不得依赖自身"));

    // 7. 布局外路径。
    for path in [
        "app/lib/widgets2/button.dart",
        "app/lib/unknown_feature/page.dart",
        "app/lib/ui/unknown/page.dart",
        "app/lib/ui/study.dart",
        "app/lib/study.dart",
        "app/lib/platform/linux/http_client.dart",
        "app/lib/platform/android.dart",
    ] {
        assert!(app_lib_path_violation(path).is_some(), "{path} 应被拒绝");
    }

    // 8. 视图 import 运行时 binding/、平台实现与 HTTP 仍被拒绝。
    let bad_ui = "import 'package:flutter/material.dart';\nimport '../../binding/error_codes.g.dart';\nimport '../../platform/android/http.dart';\nimport 'package:http/http.dart';\n";
    let bad_ui_text = app_import_violations("app/lib/ui/study/study_page.dart", bad_ui).join("\n");
    assert!(
        bad_ui_text.contains("不得 import binding/"),
        "{bad_ui_text}"
    );
    assert!(
        bad_ui_text.contains("不得 import platform/"),
        "{bad_ui_text}"
    );
    assert!(
        bad_ui_text.contains("不得 import package:http/"),
        "{bad_ui_text}"
    );

    // 9. 基座文件缺失或未启用 public_member_api_docs。
    let files: Vec<String> = [
        "app/lib/study/session.dart",
        "app/lib/ui/shell/shell_page.dart",
    ]
    .iter()
    .map(|path| path.to_string())
    .collect();
    let shell = AppShell {
        files: &files,
        main_dart: "",
        analysis_options: "analyzer:\n  errors:\n    unused: warning\n",
    };
    let shell_text = app_shell_violations(&shell).join("\n");
    assert!(
        shell_text.contains("缺少基座文件 app/lib/main.dart"),
        "{shell_text}"
    );
    assert!(
        shell_text.contains("public_member_api_docs"),
        "{shell_text}"
    );
}

/// B1：受审计 unsafe crate 用逐块 `// SAFETY:` 代替继承 workspace.lints（CORE-01:133）。
///
/// 根 `workspace.lints.rust.unsafe_code = "forbid"` 经 CLI `-F unsafe-code` 生效、crate 属性
/// 无法覆盖，受审计 crate 继承它就是不可编译组合；这里要求的正是可编译形态（真实 cargo 最小例
/// 见修复报告 B1）。缺非空 SAFETY 说明仍拒绝，普通 crate 仍必须 forbid(unsafe_code)。
#[test]
fn audited_unsafe_crate_uses_safety_comments_instead_of_workspace_lints() {
    let registry = dep_allow_registry();
    let none: Vec<String> = Vec::new();
    let accepted = MemberFacts {
        name: "fml-ffi",
        manifest_path: "crates/fml-ffi/Cargo.toml",
        manifest: LEGAL_AUDITED_MANIFEST,
        lib: Some(AUDITED_LIB),
        main: None,
        local_deps: &none,
    };
    let violations = member_violations(&accepted, &registry);
    assert!(violations.is_empty(), "{violations:#?}");

    let bare_unsafe = "#![deny(missing_docs)]\n\n/// 占位。\npub fn read_at(pointer: *const u32) -> u32 {\n    unsafe { std::ptr::read(pointer) }\n}\n";
    for (name, source) in [
        ("fml-ffi", bare_unsafe),
        (
            "fml-imgproc",
            "#![deny(missing_docs)]\n\n/// 占位。\npub fn read_at(pointer: *const u32) -> u32 {\n    // SAFETY:\n    unsafe { std::ptr::read(pointer) }\n}\n",
        ),
    ] {
        let member = MemberFacts {
            name,
            manifest_path: &format!("crates/{name}/Cargo.toml"),
            manifest: LEGAL_AUDITED_MANIFEST,
            lib: Some(source),
            main: None,
            local_deps: &none,
        };
        assert!(
            joined_violations(&member, &registry).contains("缺非空 // SAFETY: 注释"),
            "{name} 缺 SAFETY 说明应被拒绝"
        );
    }

    // 受审计例外不解除普通 crate 的 forbid(unsafe_code)。
    let plain_with_unsafe = MemberFacts {
        name: "fml-ast",
        manifest_path: "crates/fml-ast/Cargo.toml",
        manifest: LEGAL_MANIFEST,
        lib: Some(bare_unsafe),
        main: None,
        local_deps: &none,
    };
    assert!(
        joined_violations(&plain_with_unsafe, &registry)
            .contains("src/lib.rs 必须 #![forbid(unsafe_code)]")
    );
}

/// NF-A：SAFETY 判据取 CORE-74:14 的“起始行前 3 行内”窗口，不再要求紧邻连续注释。
///
/// 距 unsafe 起始行 1/2/3 行的非空 `// SAFETY:` 一律合法（空行、普通语句隔开也算）；
/// 非空下界仍来自 CORE-01:133。原因与证据见修复报告 NF-A。
#[test]
fn safety_comment_within_three_line_window_is_accepted() {
    let source = |above: &[&str]| {
        let mut lines = vec!["pub fn read_at(pointer: *const u32) -> u32 {"];
        lines.extend_from_slice(above);
        lines.push("    unsafe { std::ptr::read(pointer) }");
        lines.push("}");
        lines.join("\n") + "\n"
    };
    let note = "    // SAFETY: 调用方保证 pointer 有效且对齐。";
    for (label, above) in [
        ("紧邻 1 行", &[note][..]),
        ("空行隔开 2 行", &[note, ""][..]),
        (
            "普通语句隔开 2 行",
            &[note, "    let offset: usize = 0;"][..],
        ),
        (
            "空行加语句隔开 3 行",
            &[note, "", "    let offset: usize = 0;"][..],
        ),
    ] {
        let text = source(above);
        assert!(
            unsafe_blocks_without_safety(&text).is_empty(),
            "{label} 的 SAFETY 在 3 行窗口内应被接受：{text}"
        );
    }

    // 受审计 crate 的整卡判据同样接受窗口写法：夹具与真实 cargo 最小例同字节。
    let registry = dep_allow_registry();
    let none: Vec<String> = Vec::new();
    let windowed = MemberFacts {
        name: "fml-ffi",
        manifest_path: "crates/fml-ffi/Cargo.toml",
        manifest: LEGAL_AUDITED_MANIFEST,
        lib: Some(WINDOW_SAFETY_LIB),
        main: None,
        local_deps: &none,
    };
    let violations = member_violations(&windowed, &registry);
    assert!(violations.is_empty(), "{violations:#?}");
}

/// NF-A 反面：窗口外注释、空内容、只有空白、无注释与非 SAFETY 注释仍然拒绝。
#[test]
fn safety_comment_outside_window_or_empty_is_rejected() {
    let source = |above: &[&str]| {
        let mut lines = vec!["pub fn read_at(pointer: *const u32) -> u32 {"];
        lines.extend_from_slice(above);
        lines.push("    unsafe { std::ptr::read(pointer) }");
        lines.push("}");
        lines.join("\n") + "\n"
    };
    let note = "    // SAFETY: 调用方保证 pointer 有效且对齐。";
    // 距 unsafe 起始行 4 行：窗口之外，仍拒绝（窗口边界锁定）。
    let far = source(&[note, "", "", "    let offset: usize = 0;"]);
    assert_eq!(
        unsafe_blocks_without_safety(&far),
        vec!["第 6 行 unsafe { std::ptr::read(pointer) }".to_string()]
    );
    // 空内容、只有空白、普通注释、无注释都不是非空 SAFETY（不把任何 // 注释当 SAFETY）。
    for (label, above) in [
        ("空内容", &["    // SAFETY:"][..]),
        ("只有空白", &["    // SAFETY:    "][..]),
        (
            "非 SAFETY 注释",
            &["    // 调用方保证 pointer 有效且对齐。"][..],
        ),
        ("没有注释", &[][..]),
        ("窗口内空内容加空行", &["    // SAFETY:", "", ""][..]),
    ] {
        let text = source(above);
        assert!(
            !unsafe_blocks_without_safety(&text).is_empty(),
            "{label} 仍应被拒绝：{text}"
        );
    }
    // 同行行尾的非空 SAFETY 仍被接受（既有判据不回退）。
    let trailing = "pub fn read_at(pointer: *const u32) -> u32 {\n    unsafe { std::ptr::read(pointer) } // SAFETY: 调用方保证 pointer 有效且对齐。\n}\n";
    assert!(unsafe_blocks_without_safety(trailing).is_empty());
}
/// B2：CORE-22:108 的 fml-server 是 binary-only（`server/src/{main.rs,...}`，无 lib.rs）。
#[test]
fn binary_only_server_member_is_accepted() {
    let registry = dep_allow_registry();
    let server_deps = deps(&["fml-error", "fml-sync-proto"]);
    let server = MemberFacts {
        name: "fml-server",
        manifest_path: "server/Cargo.toml",
        manifest: LEGAL_MANIFEST,
        lib: None,
        main: Some(SERVER_MAIN),
        local_deps: &server_deps,
    };
    let violations = member_violations(&server, &registry);
    assert!(violations.is_empty(), "{violations:#?}");

    // lib.rs 与 main.rs 都缺才是缺基座。
    let none: Vec<String> = Vec::new();
    let no_base = MemberFacts {
        name: "fml-server",
        manifest_path: "server/Cargo.toml",
        manifest: LEGAL_MANIFEST,
        lib: None,
        main: None,
        local_deps: &none,
    };
    assert!(
        joined_violations(&no_base, &registry).contains("缺少基座文件 src/lib.rs 或 src/main.rs")
    );
}

/// B3：界面目录按 CORE-01:29 与 CORE-63:25 的 <feature> 并集判定，不另立白名单。
#[test]
fn ui_feature_directories_follow_the_contract_feature_set() {
    // CORE-63:25 的 ui/account/ 与 CORE-01:29 的 11 个界面名都合法。
    for path in [
        "app/lib/ui/account/login_page.dart",
        "app/lib/ui/books/book_list_page.dart",
        "app/lib/ui/shell/shell_page.dart",
    ] {
        assert_eq!(app_lib_path_violation(path), None, "{path} 应被接受");
    }
    // 契约里没有的界面目录仍拒绝。
    assert!(app_lib_path_violation("app/lib/ui/unknown/page.dart").is_some());
    // 界面目录要落到文件。
    assert!(app_lib_path_violation("app/lib/ui/account").is_some());
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
    // CORE-41 按 ADR-V5-15 首用追加 cargo_audit= 与 cargo_llvm_cov=（工具链九键）。
    let expected_keys: BTreeSet<String> = [
        "queried_date",
        "python",
        "node",
        "fuzz_nightly",
        "cargo_fuzz",
        "cargo_deny",
        "cargo_audit",
        "cargo_llvm_cov",
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
    assert_eq!(parsed["cargo_audit"], "0.22.2");
    assert_eq!(parsed["cargo_llvm_cov"], "0.9.1");

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
        .filter(|needle| lower.contains(**needle))
        .chain(WEIGHTS.iter().filter(|extension| {
            // 后缀必须结束于标识符边界；.pt 不能把合法的 .ptr 字段当成权重。
            // 检查每次出现，避免较早的字段前缀遮蔽后续真实模型路径。
            lower.match_indices(**extension).any(|(start, _)| {
                lower[start + extension.len()..]
                    .chars()
                    .next()
                    .is_none_or(|ch| !ch.is_alphanumeric() && ch != '_')
            })
        }))
        .map(|needle| (*needle).to_string())
        .collect();
    found.sort();
    found.dedup();
    found
}

#[test]
fn yolo_weight_extensions_do_not_match_identifier_prefixes() {
    for text in [
        "buf.ptr.is_null()",
        "a.bytes.as_ptr() == buf.ptr && a.bytes.len() == buf.len",
        "other.ptr",
        "output.ptr == input.ptr",
        "value.pt_count",
        "value.pt2",
        "value.pt字段",
        "value.onnx_session",
        "value.onnx2",
        "value.weights_count",
        "value.weights2",
        r#"let path = "report.ptr";"#,
    ] {
        assert!(yolo_hits(text).is_empty(), "合法标识符不得命中：{text}");
    }
}

#[test]
fn yolo_weight_extensions_match_file_and_string_boundaries() {
    for extension in WEIGHTS {
        for ending in [
            "", "\"", "'", " ", "\n", ";", ")", "]", "}", ",", "/", "\\", "?v=1", "#hash", ".gz",
        ] {
            for prefix in [
                "detector",
                "models/detector",
                r"C:\models\detector",
                "https://host/models/detector",
            ] {
                let text = format!("{prefix}{extension}{ending}");
                assert_eq!(yolo_hits(&text), [*extension], "权重引用必须命中：{text}");
                assert_eq!(yolo_hits(&text.to_uppercase()), [*extension]);
            }
        }
        // 首次出现是标识符前缀时，后续真实扩展名仍必须命中。
        let text = format!("value{extension}_field; load(\"detector{extension}\")");
        assert_eq!(yolo_hits(&text), [*extension]);
        for suffix in ["r", "_field", "2", "字段"] {
            let text = format!("value{extension}{suffix}");
            assert!(yolo_hits(&text).is_empty(), "扩展名前缀不得命中：{text}");
        }
    }
}

#[test]
fn yolo_banned_names_and_hit_order_remain_unchanged() {
    for name in BANNED {
        assert_eq!(yolo_hits(&name.to_uppercase()), [*name]);
        assert_eq!(yolo_hits(&format!("prefix_{name}_implementation")), [*name]);
    }
    assert_eq!(
        yolo_hits("a.pt a.PT b.weights c.onnx YOLO ultralytics darknet"),
        [".onnx", ".pt", ".weights", "darknet", "ultralytics", "yolo"]
    );
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
