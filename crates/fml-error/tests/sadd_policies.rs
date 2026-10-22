//! CORE-01 测试方案第 4 条：四份机器可读架构策略的解析与初始值逐项断言。
//!
//! 本测试只做数据断言，不实现拒绝引擎（未知字段/版本/重复元素的拒绝归 CORE-69）。

use std::path::PathBuf;

use serde_json::{Value, json};
use yaml_rust2::{Yaml, YamlLoader};

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

/// 把 YAML 节点转成 JSON 值，便于与 JSON 策略文件统一断言。
///
/// 四份策略文件只用映射（键为字符串）、数组、字符串、整数与布尔，故不为其他节点编造映射：
/// 出现浮点、别名或坏值时直接失败，避免把解析歧义悄悄当成通过。
fn yaml_to_json(node: &Yaml, rel: &str) -> Value {
    match node {
        Yaml::Null => Value::Null,
        Yaml::Boolean(flag) => json!(flag),
        Yaml::Integer(number) => json!(number),
        Yaml::String(text) => json!(text),
        Yaml::Real(text) => text
            .parse::<f64>()
            .ok()
            .and_then(serde_json::Number::from_f64)
            .map(Value::Number)
            .unwrap_or_else(|| panic!("{rel} 含无法表示的浮点数：{text}")),
        Yaml::Array(items) => {
            Value::Array(items.iter().map(|item| yaml_to_json(item, rel)).collect())
        }
        Yaml::Hash(entries) => {
            let mut object = serde_json::Map::new();
            for (key, value) in entries {
                let Yaml::String(name) = key else {
                    panic!("{rel} 的映射键必须是字符串：{key:?}");
                };
                object.insert(name.clone(), yaml_to_json(value, rel));
            }
            Value::Object(object)
        }
        Yaml::Alias(index) => panic!("{rel} 含 YAML 别名（#{index}），策略文件不得使用"),
        Yaml::BadValue => panic!("{rel} 含无法解析的 YAML 节点"),
    }
}

/// 读取 YAML 策略文件并转成 JSON 值。
fn read_yaml(rel: &str) -> Value {
    let text = read(rel);
    let mut documents =
        YamlLoader::load_from_str(&text).unwrap_or_else(|e| panic!("{rel} 不是合法 YAML：{e}"));
    assert_eq!(documents.len(), 1, "{rel} 必须恰好包含一个 YAML 文档");
    yaml_to_json(&documents.remove(0), rel)
}

/// 读取 JSON 策略文件。
fn read_json(rel: &str) -> Value {
    let text = read(rel);
    serde_json::from_str(&text).unwrap_or_else(|e| panic!("{rel} 不是合法 JSON：{e}"))
}

/// 取对象的键集合（排序后）。
fn keys(value: &Value) -> Vec<String> {
    let mut out: Vec<String> = value
        .as_object()
        .unwrap_or_else(|| panic!("应为对象：{value}"))
        .keys()
        .cloned()
        .collect();
    out.sort();
    out
}

/// 取字符串数组。
fn strings(value: &Value, what: &str) -> Vec<String> {
    value
        .as_array()
        .unwrap_or_else(|| panic!("{what} 应为数组：{value}"))
        .iter()
        .map(|v| {
            v.as_str()
                .unwrap_or_else(|| panic!("{what} 的元素应为字符串：{v}"))
                .to_string()
        })
        .collect()
}

/// 初始依赖上界表（CORE-01 卡:98-122，落盘用完整 Cargo package name）。
const DEP_ALLOW_TABLE: &[(&str, &[&str])] = &[
    ("fml-error", &[]),
    ("fml-ast", &["fml-error"]),
    ("fml-latex", &["fml-ast", "fml-error"]),
    ("fml-units", &["fml-ast", "fml-error"]),
    (
        "fml-notation",
        &["fml-ast", "fml-latex", "fml-units", "fml-error"],
    ),
    (
        "fml-type",
        &["fml-ast", "fml-units", "fml-notation", "fml-error"],
    ),
    (
        "fml-eval",
        &["fml-ast", "fml-type", "fml-units", "fml-error"],
    ),
    (
        "fml-derive",
        &[
            "fml-ast",
            "fml-type",
            "fml-units",
            "fml-eval",
            "fml-notation",
            "fml-error",
        ],
    ),
    ("fml-typeset", &["fml-ast", "fml-latex", "fml-error"]),
    (
        "fml-export",
        &["fml-ast", "fml-latex", "fml-typeset", "fml-error"],
    ),
    ("fml-srs", &["fml-ast", "fml-error"]),
    (
        "fml-grade",
        &[
            "fml-ast",
            "fml-latex",
            "fml-notation",
            "fml-units",
            "fml-type",
            "fml-eval",
            "fml-srs",
            "fml-error",
        ],
    ),
    (
        "fml-study",
        &[
            "fml-ast",
            "fml-latex",
            "fml-notation",
            "fml-units",
            "fml-type",
            "fml-eval",
            "fml-srs",
            "fml-grade",
            "fml-error",
        ],
    ),
    ("fml-crypto", &["fml-ast", "fml-error"]),
    ("fml-sync-proto", &["fml-error"]),
    ("fml-imgproc", &["fml-ast", "fml-error"]),
    (
        "fml-recognize-local",
        &["fml-ast", "fml-imgproc", "fml-error"],
    ),
    (
        "fml-recognize",
        &[
            "fml-ast",
            "fml-latex",
            "fml-notation",
            "fml-units",
            "fml-type",
            "fml-imgproc",
            "fml-recognize-local",
            "fml-error",
        ],
    ),
    (
        "fml-pack",
        &["fml-ast", "fml-crypto", "fml-store", "fml-error"],
    ),
    (
        "fml-store",
        &[
            "fml-ast",
            "fml-latex",
            "fml-notation",
            "fml-units",
            "fml-type",
            "fml-eval",
            "fml-derive",
            "fml-typeset",
            "fml-export",
            "fml-srs",
            "fml-grade",
            "fml-study",
            "fml-crypto",
            "fml-sync-proto",
            "fml-sync",
            "fml-recognize",
            "fml-error",
        ],
    ),
    (
        "fml-sync",
        &["fml-ast", "fml-crypto", "fml-sync-proto", "fml-error"],
    ),
    (
        "fml-ffi",
        &[
            "fml-ast",
            "fml-latex",
            "fml-notation",
            "fml-units",
            "fml-type",
            "fml-eval",
            "fml-derive",
            "fml-typeset",
            "fml-export",
            "fml-srs",
            "fml-grade",
            "fml-study",
            "fml-crypto",
            "fml-sync-proto",
            "fml-imgproc",
            "fml-recognize-local",
            "fml-recognize",
            "fml-pack",
            "fml-store",
            "fml-sync",
            "fml-error",
        ],
    ),
    ("fml-server", &["fml-error", "fml-sync-proto"]),
];

#[test]
fn dep_allow_matches_initial_table_and_is_acyclic() {
    let doc = read_yaml("contracts/policies/dep-allow.yaml");
    assert_eq!(
        keys(&doc),
        vec!["crates".to_string(), "version".to_string()]
    );
    assert_eq!(
        doc["version"],
        json!(1),
        "dep-allow.yaml 的 version 必须为 1"
    );

    let crates = &doc["crates"];
    let mut expected: Vec<String> = DEP_ALLOW_TABLE.iter().map(|(k, _)| k.to_string()).collect();
    expected.sort();
    assert_eq!(
        keys(crates),
        expected,
        "crates 键集合必须等于卡片初始表，不多不少"
    );

    let mut edges: std::collections::BTreeMap<String, Vec<String>> =
        std::collections::BTreeMap::new();
    for (name, allowed) in DEP_ALLOW_TABLE {
        let actual = strings(&crates[*name], name);
        let mut actual_sorted = actual.clone();
        actual_sorted.sort();
        let mut expected_sorted: Vec<String> = allowed.iter().map(|s| s.to_string()).collect();
        expected_sorted.sort();
        assert_eq!(
            actual_sorted, expected_sorted,
            "{name} 的允许依赖必须与初始表逐项一致"
        );

        let mut deduped = actual.clone();
        deduped.sort();
        deduped.dedup();
        assert_eq!(deduped.len(), actual.len(), "{name} 的允许依赖不得重复");

        for dep in &actual {
            assert!(
                dep.starts_with("fml-"),
                "{name} 的依赖必须是完整 Cargo package name：{dep}"
            );
            assert_ne!(dep, name, "{name} 不得自依赖");
            assert!(!dep.contains('*'), "{name} 的依赖不得含通配符：{dep}");
            assert!(
                crates.get(dep.as_str()).is_some(),
                "{name} 的依赖 {dep} 必须是本表已登记的包"
            );
        }
        edges.insert(name.to_string(), actual);
    }

    // pack -> store 与 store -> sync 允许，反向不允许（卡:124）。
    assert!(edges["fml-pack"].contains(&"fml-store".to_string()));
    assert!(edges["fml-store"].contains(&"fml-sync".to_string()));
    assert!(!edges["fml-store"].contains(&"fml-pack".to_string()));
    assert!(!edges["fml-sync"].contains(&"fml-store".to_string()));

    // 图中环无条件拒绝（卡:96）：深度优先检查无环。
    fn visit(
        node: &str,
        edges: &std::collections::BTreeMap<String, Vec<String>>,
        visiting: &mut Vec<String>,
        done: &mut Vec<String>,
    ) {
        if done.iter().any(|d| d == node) {
            return;
        }
        assert!(
            !visiting.iter().any(|v| v == node),
            "依赖图存在环：{visiting:?} -> {node}"
        );
        visiting.push(node.to_string());
        for next in edges.get(node).map(|v| v.as_slice()).unwrap_or(&[]) {
            visit(next, edges, visiting, done);
        }
        visiting.pop();
        done.push(node.to_string());
    }

    let mut done = Vec::new();
    for (node, _) in DEP_ALLOW_TABLE {
        visit(node, &edges, &mut Vec::new(), &mut done);
    }
}

#[test]
fn dep6_symbols_have_one_header_and_exact_entries() {
    let text = read("contracts/policies/dep6_symbols.txt");
    assert!(text.is_ascii(), "dep6_symbols.txt 必须为 ASCII 文本");

    let mut headers = Vec::new();
    let mut ops = Vec::new();
    let mut types = Vec::new();
    for (index, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if line == "version:1" {
            headers.push(index);
        } else if let Some(op) = line.strip_prefix("op:") {
            assert!(
                op.chars()
                    .all(|c| c.is_ascii_alphanumeric() || c == '.' || c == '_'),
                "op 名应为精确词法：{line}"
            );
            ops.push(op.to_string());
        } else if let Some(ty) = line.strip_prefix("type:") {
            assert!(
                ty.chars().all(|c| c.is_ascii_alphanumeric() || c == '_'),
                "type 名应为精确词法：{line}"
            );
            types.push(ty.to_string());
        } else {
            panic!("dep6_symbols.txt 出现未知行：{line}");
        }
    }

    assert_eq!(headers, vec![0], "唯一非注释头 version:1 且必须在首行");
    assert_eq!(
        ops,
        vec![
            "engine.parse",
            "engine.check",
            "calc.evaluate",
            "calc.solvable_targets",
            "typeset.layout",
            "typeset.glyph_outlines",
            "derive.rank",
            "derive.substitute",
            "derive.run_plan",
        ],
        "op 初始清单必须逐项一致且有序"
    );
    assert_eq!(
        types,
        vec!["FormulaNode", "DimensionFull", "DisplayList"],
        "type 初始清单必须逐项一致且有序"
    );
}

#[test]
fn platform_check_patterns_match_initial_rules() {
    let doc = read_json("contracts/policies/platform-check-patterns.json");
    assert_eq!(
        keys(&doc),
        vec!["patterns".to_string(), "version".to_string()]
    );
    assert_eq!(doc["version"], json!(1));

    let mut triples: Vec<(String, Option<String>, String)> = Vec::new();
    for pattern in doc["patterns"].as_array().expect("patterns 应为数组") {
        assert_eq!(
            keys(pattern),
            vec![
                "library".to_string(),
                "member".to_string(),
                "receiver".to_string()
            ],
            "每条规则只能有 library/receiver/member 三个键"
        );
        let library = pattern["library"]
            .as_str()
            .expect("library 应为字符串")
            .to_string();
        let receiver = pattern["receiver"].as_str().map(|s| s.to_string());
        let member = pattern["member"]
            .as_str()
            .expect("member 应为字符串")
            .to_string();
        assert!(!member.contains('*'), "member 不支持正则/通配：{member}");
        triples.push((library, receiver, member));
    }

    let mut expected: Vec<(String, Option<String>, String)> = Vec::new();
    for member in [
        "isAndroid",
        "isWindows",
        "isLinux",
        "isMacOS",
        "isIOS",
        "isFuchsia",
        "operatingSystem",
    ] {
        expected.push((
            "dart:io".to_string(),
            Some("Platform".to_string()),
            member.to_string(),
        ));
    }
    for member in ["defaultTargetPlatform", "kIsWeb"] {
        expected.push((
            "package:flutter/foundation.dart".to_string(),
            None,
            member.to_string(),
        ));
    }
    for member in ["android", "windows", "linux", "macOS", "iOS", "fuchsia"] {
        expected.push((
            "package:flutter/foundation.dart".to_string(),
            Some("TargetPlatform".to_string()),
            member.to_string(),
        ));
    }

    assert_eq!(
        triples.len(),
        expected.len(),
        "初始规则条数应为 15（每个 member 独立一项）"
    );
    for item in &expected {
        assert!(triples.contains(item), "缺少初始规则：{item:?}");
    }
    let mut deduped = triples.clone();
    deduped.sort();
    deduped.dedup();
    assert_eq!(deduped.len(), triples.len(), "规则不得重复");
}

#[test]
fn network_construction_allows_only_platform_net_files() {
    let doc = read_yaml("contracts/policies/network-construction.yaml");
    assert_eq!(keys(&doc), vec!["allow".to_string(), "version".to_string()]);
    assert_eq!(doc["version"], json!(1));
    assert_eq!(
        strings(&doc["allow"], "allow"),
        vec![
            "app/lib/platform/android/net/**/*.dart".to_string(),
            "app/lib/platform/windows/net/**/*.dart".to_string(),
        ],
        "只豁免两个平台 net 目录，privacy/、composition/ 不豁免"
    );
}
