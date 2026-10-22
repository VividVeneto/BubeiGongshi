//! CORE-02 测试方案 T-03～T-08（阶段1）：构造、规范顺序、errors-v1 正例与负例、
//! 注册表全量对照与反序列化拒绝规则。
//!
//! T-05/T-06 里的 Dart 侧断言只登记不执行（Dart 异常桥属阶段2，见卡"两阶段交付"）。

use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;

use fml_error::{Diagnostic, ErrorCode, FmlError, Severity, TraceId};
use serde_json::{Map, Value, json};
use yaml_rust2::{Yaml, YamlLoader};

/// errors-v1 向量里使用的真实 32 位小写 trace_id。
const TRACE: &str = "3f8b2c1d4e5f60718293a4b5c6d7e8f9";

/// 负例 allowed 的 9 种 why 取值（卡"errors-v1 向量"）。
const WHY_VALUES: [&str; 9] = [
    "unknown_field",
    "wrong_type",
    "range",
    "trace_format",
    "domain_mismatch",
    "retryable_mismatch",
    "severity_mismatch",
    "recovery_invalid",
    "envelope_invalid",
];

/// 仓库根目录（由 crate 位置推出）。
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(2)
        .expect("crate 应位于 <仓库根>/crates/fml-error")
        .to_path_buf()
}

/// 读取仓库内文本文件。
fn read(rel: &str) -> String {
    let path = repo_root().join(rel);
    std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("读取 {} 失败：{e}", path.display()))
}

/// 把 YAML 节点转成 JSON 值（注册表只用映射、数组、字符串、整数与布尔）。
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
            let mut object = Map::new();
            for (key, value) in entries {
                let Yaml::String(name) = key else {
                    panic!("{rel} 的映射键必须是字符串：{key:?}");
                };
                object.insert(name.clone(), yaml_to_json(value, rel));
            }
            Value::Object(object)
        }
        Yaml::Alias(index) => panic!("{rel} 含 YAML 别名（#{index}），注册表不得使用"),
        Yaml::BadValue => panic!("{rel} 含无法解析的 YAML 节点"),
    }
}

/// 读取仓库内 YAML 文件并转成 JSON 值。
fn read_yaml(rel: &str) -> Value {
    let text = read(rel);
    let mut documents =
        YamlLoader::load_from_str(&text).unwrap_or_else(|e| panic!("{rel} 不是合法 YAML：{e}"));
    assert_eq!(documents.len(), 1, "{rel} 必须恰好包含一个 YAML 文档");
    yaml_to_json(&documents.remove(0), rel)
}

/// 读取仓库内 JSON 文件。
fn read_json(rel: &str) -> Value {
    serde_json::from_str(&read(rel)).unwrap_or_else(|e| panic!("{rel} 不是合法 JSON：{e}"))
}

/// 注册表顶层与条目列表。
fn registry() -> Value {
    read_yaml("contracts/errors/registry.yaml")
}

/// 解析错误码文本，失败即断言失败。
fn code(text: &str) -> ErrorCode {
    text.parse::<ErrorCode>()
        .unwrap_or_else(|e| panic!("{text} 应能解析为 ErrorCode：{e}"))
}

/// 只填必填字段的诊断。
fn diag(code: ErrorCode) -> Diagnostic {
    Diagnostic {
        code,
        severity: code.severity(),
        node_path: None,
        input_range: None,
        args: BTreeMap::new(),
        recovery: None,
        needs_confirm: false,
    }
}

/// 测试侧按卡复算变体名：每段 ASCII 小写后仅首字母大写再连接。
fn expected_variant(text: &str) -> String {
    let mut name = String::new();
    for segment in text.split('_') {
        let lower = segment.to_ascii_lowercase();
        let mut chars = lower.chars();
        if let Some(first) = chars.next() {
            name.push(first.to_ascii_uppercase());
            name.push_str(chars.as_str());
        }
    }
    name
}

/// 测试侧按卡复算消息键：首个下划线切命名空间与余部，分别小写后以点连接。
fn expected_message_key(text: &str) -> String {
    let (namespace, rest) = text.split_once('_').expect("错误码至少含一个下划线");
    format!(
        "err.{}.{}",
        namespace.to_ascii_lowercase(),
        rest.to_ascii_lowercase()
    )
}

/// 注册表条目按 code 排序后的 (code, entry) 列表。
fn sorted_entries() -> Vec<(String, Value)> {
    let doc = registry();
    let entries = doc["entries"].as_array().expect("entries 必须是数组");
    let mut out: Vec<(String, Value)> = entries
        .iter()
        .map(|entry| {
            let text = entry["code"]
                .as_str()
                .expect("code 必须是字符串")
                .to_owned();
            (text, entry.clone())
        })
        .collect();
    out.sort_by(|left, right| left.0.cmp(&right.0));
    out
}

/// T-03：new 只派生 domain/retryable，不填诊断与追踪标识；From 与 new 一致。
#[test]
fn t03_new_derives_metadata_and_starts_empty() {
    let error = FmlError::new(ErrorCode::UnitOverflow);
    assert_eq!(error.code, ErrorCode::UnitOverflow);
    assert_eq!(
        error.domain, "unit",
        "domain 必须取注册表命名空间的小写形式"
    );
    assert!(
        !error.retryable,
        "UNIT_OVERFLOW 在注册表中 retryable 为否，new 必须取生成值"
    );
    assert!(error.diagnostics.is_empty(), "new 不带任何诊断");
    assert!(error.trace_id.is_zero(), "new 的 trace_id 必须是全零");
    assert_eq!(
        FmlError::from(ErrorCode::UnitOverflow),
        error,
        "From 必须等于 new"
    );

    let retryable = FmlError::new(ErrorCode::FfiBusy);
    assert!(retryable.retryable, "FFI_BUSY 在注册表中可重试");
    assert_eq!(retryable.domain, "ffi");
}

/// T-03：with_diagnostic 只追加、保序、不改外层 code。
#[test]
fn t03_with_diagnostic_appends_in_order() {
    let mut first = diag(ErrorCode::TypeDimConflict);
    first.node_path = Some("/root/body/0".to_owned());
    let second = diag(ErrorCode::TypeDimConflict);
    let error = FmlError::new(ErrorCode::TypeDimConflict)
        .with_diagnostic(first.clone())
        .with_diagnostic(second.clone());
    assert_eq!(error.code, ErrorCode::TypeDimConflict);
    assert_eq!(
        error.diagnostics,
        vec![first, second],
        "诊断必须保持追加顺序"
    );
}

/// T-03：with_trace 只在全零时填入，非零值不覆盖。
#[test]
fn t03_with_trace_only_fills_zero() {
    let trace = TraceId(*b"0123456789abcdef");
    let error = FmlError::new(ErrorCode::UnitOverflow).with_trace(trace);
    assert_eq!(error.trace_id, trace);

    let other = TraceId(*b"fedcba9876543210");
    let kept = error.clone().with_trace(other);
    assert_eq!(kept.trace_id, trace, "非零 trace_id 不得被覆盖");

    let zero = FmlError::new(ErrorCode::UnitOverflow).with_trace(TraceId::default());
    assert!(zero.trace_id.is_zero(), "填入全零等于仍然未填入");
}

/// T-03：公开 API 不提供覆盖 domain/retryable 的构造器或方法。
#[test]
fn t03_no_public_override_of_derived_metadata() {
    let lib = read("crates/fml-error/src/lib.rs");
    for forbidden in [
        "with_retryable",
        "with_domain",
        "set_retryable",
        "set_domain",
    ] {
        assert!(
            !lib.contains(forbidden),
            "错误模型不得提供覆盖注册表派生值的 API：{forbidden}"
        );
    }
    let codes = read("crates/fml-error/src/codes.rs");
    for forbidden in [
        "with_retryable",
        "with_domain",
        "set_retryable",
        "set_domain",
    ] {
        assert!(
            !codes.contains(forbidden),
            "生成的码表不得提供覆盖 API：{forbidden}"
        );
    }
}

/// T-04：FmlError 与 Diagnostic 的字段声明顺序就是规范顺序。
#[test]
fn t04_field_declaration_order() {
    let lib = read("crates/fml-error/src/lib.rs");
    let start = lib
        .find("pub struct FmlError {")
        .expect("必须声明 FmlError");
    let block = &lib[start..];
    let order = [
        "pub code:",
        "pub domain:",
        "pub retryable:",
        "pub trace_id:",
        "pub diagnostics:",
    ];
    let mut last = 0;
    for field in order {
        let position = block
            .find(field)
            .unwrap_or_else(|| panic!("缺少字段 {field}"));
        assert!(
            position >= last,
            "FmlError 字段顺序必须为 {order:?}，{field} 位置异常"
        );
        last = position;
    }

    let start = lib
        .find("pub struct Diagnostic {")
        .expect("必须声明 Diagnostic");
    let block = &lib[start..];
    let order = [
        "pub code:",
        "pub severity:",
        "pub node_path:",
        "pub input_range:",
        "pub args:",
        "pub recovery:",
        "pub needs_confirm:",
    ];
    let mut last = 0;
    for field in order {
        let position = block
            .find(field)
            .unwrap_or_else(|| panic!("缺少字段 {field}"));
        assert!(
            position >= last,
            "Diagnostic 字段顺序必须为 {order:?}，{field} 位置异常"
        );
        last = position;
    }
}

/// T-04 运行时侧：序列化键顺序与声明顺序一致。
#[test]
fn t04_serialized_key_order() {
    let mut diagnostic = diag(ErrorCode::ParseSyntax);
    diagnostic.node_path = Some("/root".to_owned());
    diagnostic.input_range = Some((0, 3));
    diagnostic.recovery = Some("err.parse.syntax.fix".to_owned());
    let error = FmlError::new(ErrorCode::ParseSyntax).with_diagnostic(diagnostic);
    let text = serde_json::to_string(&error).expect("合规错误值必须能序列化");

    let mut last = 0;
    for key in [
        "\"code\"",
        "\"domain\"",
        "\"retryable\"",
        "\"trace_id\"",
        "\"diagnostics\"",
    ] {
        let position = text
            .find(key)
            .unwrap_or_else(|| panic!("缺少键 {key}：{text}"));
        assert!(position >= last, "FmlError 序列化键顺序错：{text}");
        last = position;
    }
    let mut last = 0;
    for key in [
        "\"code\"",
        "\"severity\"",
        "\"node_path\"",
        "\"input_range\"",
        "\"args\"",
        "\"recovery\"",
        "\"needs_confirm\"",
    ] {
        let position = text
            .rfind(key)
            .unwrap_or_else(|| panic!("缺少键 {key}：{text}"));
        assert!(position >= last, "Diagnostic 序列化键顺序错：{text}");
        last = position;
    }
}

/// T-05：errors-v1 向量结构、正例反序列化再序列化必须逐字节等于 canonical。
#[test]
fn t05_vectors_structure_and_positive_cases() {
    let doc = read_json("contracts/vectors/errors-v1.json");
    assert_eq!(doc["schema"], json!(1), "向量顶层必须有 schema: 1");
    assert_eq!(doc["error_version"], json!(1), "error_version 必须为 1");
    let cases = doc["cases"].as_array().expect("cases 必须是数组");

    let mut ids = BTreeSet::new();
    let mut positives = 0_usize;
    let (mut multi, mut empty, mut omitted, mut zero_trace) = (false, false, false, false);
    let (mut warning, mut info, mut fix, mut no_fix) = (false, false, false, false);

    for case in cases {
        let id = case["id"].as_str().expect("id 必须是字符串");
        if case.get("valid").is_some() {
            continue;
        }
        assert!(ids.insert(id.to_owned()), "正例 id 不得重复：{id}");

        let input = case["input"].as_object().expect("正例 input 必须是对象");
        assert_eq!(input.len(), 1, "正例 input 必须是根信封 {{error: …}}：{id}");
        let error_value = case["input"]["error"].clone();
        assert!(
            error_value.is_object(),
            "正例 input 必须有 error 对象：{id}"
        );

        let error: FmlError = serde_json::from_value(error_value)
            .unwrap_or_else(|e| panic!("{id} 反序列化失败：{e}"));
        let text = serde_json::to_string(&error).expect("再序列化必须成功");
        let canonical = case["canonical"].as_str().expect("canonical 必须是字符串");
        assert_eq!(text, canonical, "{id} 的规范序列化必须逐字节等于 canonical");

        positives += 1;
        let diagnostics = error.diagnostics.len();
        multi |= diagnostics >= 2;
        empty |= diagnostics == 0;
        zero_trace |= error.trace_id.is_zero();
        for diagnostic in &error.diagnostics {
            omitted |= case["input"]["error"]["diagnostics"]
                .as_array()
                .is_some_and(|items| items.iter().any(|item| item.get("needs_confirm").is_none()));
            fix |= diagnostic.recovery.is_some();
            no_fix |= diagnostic.recovery.is_none();
            warning |= diagnostic.severity == Severity::Warning;
            info |= diagnostic.severity == Severity::Info;
        }
    }

    assert!(
        positives >= 8,
        "正例必须覆盖至少 8 类情况，实际 {positives}"
    );
    assert!(multi, "正例必须包含多条诊断");
    assert!(empty, "正例必须包含空诊断数组");
    assert!(omitted, "正例必须包含省略可选字段的输入");
    assert!(zero_trace, "正例必须包含领域内零 trace_id");
    assert!(warning && info, "正例必须分别包含 warning 与 info 诊断");
    assert!(fix, "正例必须包含 fix_hint 为 true 且带 recovery 的码");
    assert!(no_fix, "正例必须包含不输出 recovery 的码");

    // args 乱序：原文里至少有一处 args 的键序不是升序，规范输出仍按键升序。
    let raw = read("contracts/vectors/errors-v1.json");
    let mut found_unordered = false;
    let mut from = 0;
    while let Some(start) = raw[from..].find("\"args\":") {
        let mut head = from + start + "\"args\":".len();
        while raw.as_bytes()[head] != b'{' {
            head += 1;
        }
        head += 1;
        let end = head + raw[head..].find('}').expect("args 必须有右括号");
        let keys: Vec<&str> = raw[head..end]
            .split(',')
            .map(|pair| pair.split(':').next().unwrap_or("").trim_matches('"'))
            .collect();
        let sorted = keys.windows(2).all(|window| window[0] <= window[1]);
        found_unordered |= !sorted;
        from = end;
    }
    assert!(
        found_unordered,
        "至少一条正例的输入 args 键序与规范顺序不同"
    );
}

/// T-06：负例每条都必须被拒绝，且 why 覆盖 9 种取值。
#[test]
fn t06_negative_cases_are_rejected() {
    let doc = read_json("contracts/vectors/errors-v1.json");
    let cases = doc["cases"].as_array().expect("cases 必须是数组");
    let mut ids = BTreeSet::new();
    let mut whys = BTreeSet::new();
    let mut negatives = 0_usize;

    for case in cases {
        let Some(valid) = case.get("valid") else {
            continue;
        };
        let id = case["id"].as_str().expect("id 必须是字符串");
        assert!(ids.insert(id.to_owned()), "负例 id 不得重复：{id}");
        assert_eq!(valid, &json!(false), "{id} 负例必须写 valid: false");
        let why = case["why"].as_str().expect("负例必须写 why");
        assert!(
            WHY_VALUES.contains(&why),
            "{id} 的 why 不在允许取值内：{why}"
        );
        whys.insert(why.to_owned());
        negatives += 1;

        let input = case["input"].as_object().expect("负例 input 必须是对象");
        match why {
            "envelope_invalid" => {
                let has_error_object = input.get("error").is_some_and(Value::is_object);
                assert!(
                    !has_error_object,
                    "{id} 的 envelope_invalid 必须是缺 error 键或 error 非对象"
                );
            }
            _ => {
                let error_value = input
                    .get("error")
                    .unwrap_or_else(|| panic!("{id} 的负例必须带 error 对象"));
                assert!(
                    serde_json::from_value::<FmlError>(error_value.clone()).is_err(),
                    "{id} 必须被拒绝（why={why}）"
                );
                if why == "unknown_field" {
                    let known = ["code", "domain", "retryable", "trace_id", "diagnostics"];
                    let extras: Vec<&String> = error_value
                        .as_object()
                        .expect("error 必须是对象")
                        .keys()
                        .filter(|key| !known.contains(&key.as_str()))
                        .collect();
                    assert!(
                        !extras.is_empty(),
                        "{id} 的 unknown_field 必须写在 error 对象层"
                    );
                    let mut stripped = error_value.clone();
                    for key in extras {
                        stripped.as_object_mut().expect("对象").remove(key);
                    }
                    assert!(
                        serde_json::from_value::<FmlError>(stripped).is_ok(),
                        "{id} 去掉未知字段后必须可以解析，证明失败原因是该未知字段"
                    );
                }
            }
        }
    }

    assert!(negatives >= 9, "负例至少 9 条，实际 {negatives}");
    for why in WHY_VALUES {
        assert!(whys.contains(why), "负例必须覆盖 why={why}");
    }
}

/// T-06 增补（N2）：共享错误向量必须含 input_range 的负端点负例，
/// 且这些负例只因符号被拒绝——端点抬成非负后同一文档必须可解析。
#[test]
fn t06_range_negatives_cover_negative_endpoints() {
    let doc = read_json("contracts/vectors/errors-v1.json");
    let cases = doc["cases"].as_array().expect("cases 必须是数组");

    let mut negative_start = 0_usize;
    let mut negative_end = 0_usize;
    let mut reversed = 0_usize;
    let mut upper_overflow = 0_usize;

    for case in cases {
        if case.get("valid").and_then(Value::as_bool) != Some(false) {
            continue;
        }
        if case["why"].as_str() != Some("range") {
            continue;
        }
        let id = case["id"].as_str().expect("id 必须是字符串");
        let error_value = case["input"]["error"].clone();
        let diagnostics = error_value["diagnostics"]
            .as_array()
            .unwrap_or_else(|| panic!("{id} 的 range 负例必须带 diagnostics 数组"));
        let mut seen = false;
        for diagnostic in diagnostics {
            let Some(range) = diagnostic.get("input_range") else {
                continue;
            };
            let pair = range.as_array().expect("input_range 必须是数组");
            assert_eq!(pair.len(), 2, "{id} 的 input_range 必须恰有两个端点");
            let start = pair[0].as_i64().expect("input_range 端点必须是整数");
            let end = pair[1].as_i64().expect("input_range 端点必须是整数");
            seen = true;
            // 四类互斥：负 start / 负 end / 非负倒序 / 上界溢出。
            if start < 0 || end < 0 {
                if start < 0 {
                    negative_start += 1;
                }
                if end < 0 {
                    negative_end += 1;
                }
            } else if start > end {
                reversed += 1;
            } else if end > i64::from(u32::MAX) {
                upper_overflow += 1;
            } else {
                panic!("{id} 的 why=range 却给出合法区间 [{start},{end}]");
            }
            assert!(
                serde_json::from_value::<FmlError>(error_value.clone()).is_err(),
                "{id} 的 range 负例必须被真实解码流程拒绝"
            );
        }
        assert!(seen, "{id} 的 why=range 必须给出 input_range");
    }

    assert!(reversed >= 1, "共享语料必须保留非负倒序负例（现有 [10,5]）");
    assert!(
        upper_overflow >= 1,
        "共享语料必须保留上界溢出负例（现有 [0,4294967296]）"
    );
    assert!(
        negative_start >= 1,
        "共享语料必须含负 start 的 range 负例（N2）"
    );
    assert!(
        negative_end >= 1,
        "共享语料必须含负 end 的 range 负例（N2）"
    );

    // 两条新增负例的具体语义：负 start 与「负 start 且负 end」。
    for (id, want_start, want_end) in [("ERR-NEG-12", -1_i64, 5_i64), ("ERR-NEG-13", -5, -2)] {
        let case = cases
            .iter()
            .find(|case| case["id"].as_str() == Some(id))
            .unwrap_or_else(|| panic!("缺少负端点向量 {id}"));
        assert_eq!(case["valid"], json!(false), "{id} 必须写 valid: false");
        assert_eq!(case["why"], json!("range"), "{id} 的 why 必须是 range");
        let mut error_value = case["input"]["error"].clone();
        let pair = error_value["diagnostics"][0]["input_range"]
            .as_array()
            .unwrap_or_else(|| panic!("{id} 必须给出 input_range"))
            .clone();
        assert_eq!(
            Value::Array(pair),
            json!([want_start, want_end]),
            "{id} 的 input_range 端点不对"
        );
        assert!(
            serde_json::from_value::<FmlError>(error_value.clone()).is_err(),
            "{id} 必须被真实解码流程拒绝"
        );
        // 只抹平符号（-1,5 -> 0,5；-5,-2 -> 0,0），其余字段不动。
        error_value["diagnostics"][0]["input_range"] = json!([want_start.max(0), want_end.max(0)]);
        assert!(
            serde_json::from_value::<FmlError>(error_value).is_ok(),
            "{id} 的端点抬成非负后必须可以解析，证明拒绝原因是负值"
        );
    }

    // 端点边界与同类错误：上界本身收，上界 +1 与倒序仍拒。
    let mut boundary = cases
        .iter()
        .find(|case| case["id"].as_str() == Some("ERR-NEG-12"))
        .map(|case| case["input"]["error"].clone())
        .expect("ERR-NEG-12 必须存在");
    boundary["diagnostics"][0]["input_range"] = json!([0, u64::from(u32::MAX)]);
    assert!(
        serde_json::from_value::<FmlError>(boundary.clone()).is_ok(),
        "input_range 上界 [0,4294967295] 必须可解析"
    );
    boundary["diagnostics"][0]["input_range"] = json!([0, u64::from(u32::MAX) + 1]);
    assert!(
        serde_json::from_value::<FmlError>(boundary.clone()).is_err(),
        "上界 +1 必须被拒绝"
    );
    boundary["diagnostics"][0]["input_range"] = json!([9, 4]);
    assert!(
        serde_json::from_value::<FmlError>(boundary).is_err(),
        "非负倒序 [9,4] 必须被拒绝"
    );
}

/// T-07：全部错误码的生成视图与注册表逐条一致。
#[test]
fn t07_generated_metadata_matches_registry() {
    let doc = registry();
    let version = doc["registry_version"]
        .as_u64()
        .expect("registry_version 必须是整数");
    let entries = sorted_entries();
    assert!(version >= 1, "registry_version 必须 >= 1");

    let mut all: Vec<&str> = ErrorCode::all().map(|item| item.as_str()).collect();
    assert_eq!(
        all.len(),
        entries.len(),
        "ErrorCode::all() 的数量必须等于注册表条目数"
    );
    assert!(
        all.windows(2).all(|window| window[0] < window[1]),
        "ErrorCode::all() 必须按 code 升序且唯一"
    );
    all.sort_unstable();

    for (text, entry) in &entries {
        let parsed = code(text);
        assert_eq!(parsed.as_str(), text, "as_str 必须返回 code 原文");
        assert_eq!(format!("{parsed}"), *text, "Display 必须等于 as_str");
        assert_eq!(
            format!("{parsed:?}"),
            expected_variant(text),
            "{text} 的变体名必须按分段规则生成"
        );
        assert_eq!(
            parsed.domain(),
            entry["namespace"]
                .as_str()
                .expect("namespace")
                .to_ascii_lowercase(),
            "{text} 的 domain 必须取命名空间"
        );
        let severity = match entry["severity"].as_str().expect("severity") {
            "error" => Severity::Error,
            "warning" => Severity::Warning,
            "info" => Severity::Info,
            other => panic!("{text} 的 severity 非法：{other}"),
        };
        assert_eq!(
            parsed.severity(),
            severity,
            "{text} 的 severity 必须与注册表一致"
        );
        assert_eq!(
            parsed.retryable(),
            entry["retryable"].as_bool().expect("retryable"),
            "{text} 的 retryable 必须与注册表一致"
        );
        assert_eq!(
            parsed.fix_hint(),
            entry
                .get("fix_hint")
                .and_then(Value::as_bool)
                .unwrap_or(false),
            "{text} 的 fix_hint 缺省为 false"
        );
        assert_eq!(
            parsed.message_key(),
            expected_message_key(text),
            "{text} 的 message_key 必须按派生规则生成"
        );
        assert_eq!(
            entry["message_key"].as_str().expect("message_key"),
            expected_message_key(text),
            "{text} 在注册表里的 message_key 必须等于派生值"
        );
        let surface = entry["surface"].as_str().expect("surface 必须填写");
        assert_eq!(parsed.surface(), surface, "{text} 的 surface 必须返回原文");
        assert_eq!(
            parsed.is_server_output(),
            matches!(surface, "server" | "both"),
            "{text} 的 is_server_output 必须与 surface 同源"
        );
        let expected_http = match entry.get("http_status").and_then(Value::as_u64) {
            Some(value) => Some(u16::try_from(value).expect("http_status 必须落在 u16")),
            None if parsed.is_server_output() => Some(400),
            None => None,
        };
        assert_eq!(
            parsed.http_status(),
            expected_http,
            "{text} 的 http_status 必须与注册表一致"
        );
    }
}

/// T-07：surface 与 http_status 的生成签名是卡里规定的形式。
#[test]
fn t07_surface_and_http_status_signatures() {
    let codes = read("crates/fml-error/src/codes.rs");
    for signature in [
        "pub fn surface(&self) -> &'static str",
        "pub fn is_server_output(self) -> bool",
        "pub fn http_status(self) -> Option<u16>",
        "pub fn as_str(self) -> &'static str",
        "pub fn domain(self) -> &'static str",
        "pub fn severity(self) -> Severity",
        "pub fn retryable(self) -> bool",
        "pub fn message_key(self) -> &'static str",
        "pub fn fix_hint(self) -> bool",
    ] {
        assert!(codes.contains(signature), "codes.rs 缺少签名：{signature}");
    }
}

/// T-08：未知错误码在 FromStr、TryFrom 与 serde 三处都被拒绝，且不 panic。
#[test]
fn t08_unknown_code_rejected_everywhere() {
    let parsed = "NOT_A_REGISTERED_CODE".parse::<ErrorCode>();
    let error = parsed.expect_err("未知码必须解析失败");
    assert!(
        !format!("{error}").is_empty(),
        "UnknownErrorCode 必须有说明文本"
    );
    assert!(format!("{error:?}").contains("UnknownErrorCode"));

    let converted = ErrorCode::try_from("NOT_A_REGISTERED_CODE");
    assert!(converted.is_err(), "TryFrom<&str> 必须拒绝未知码");

    let from_json: Result<ErrorCode, _> = serde_json::from_str("\"NOT_A_REGISTERED_CODE\"");
    assert!(from_json.is_err(), "serde 必须拒绝未知码");
}

/// T-08：Display 只带错误码与追踪标识，不含诊断参数原文。
#[test]
fn t08_display_hides_diagnostics_and_args() {
    let mut diagnostic = diag(ErrorCode::ParseSyntax);
    diagnostic
        .args
        .insert("input".to_owned(), "SECRET-TOKEN-42".to_owned());
    let error = FmlError::new(ErrorCode::ParseSyntax).with_diagnostic(diagnostic);
    let text = format!("{error}");
    assert!(
        text.contains("PARSE_SYNTAX"),
        "Display 必须包含错误码：{text}"
    );
    assert!(
        text.contains("00000000000000000000000000000000"),
        "Display 必须包含 trace_id"
    );
    assert!(
        !text.contains("SECRET-TOKEN-42"),
        "Display 不得打印诊断参数：{text}"
    );
    assert!(!text.contains("args"), "Display 不得打印诊断结构：{text}");
    use std::error::Error as _;
    assert!(
        error.source().is_none(),
        "错误模型不包装下层错误，source 为 None"
    );
}

/// T-08：与注册表不一致的公开字段在序列化时被拒绝。
#[test]
fn t08_serialize_rejects_inconsistent_values() {
    let mut wrong_domain = FmlError::new(ErrorCode::UnitOverflow);
    wrong_domain.domain = "eval".to_owned();
    assert!(
        serde_json::to_string(&wrong_domain).is_err(),
        "domain 不符必须拒绝序列化"
    );

    let mut wrong_retryable = FmlError::new(ErrorCode::UnitOverflow);
    wrong_retryable.retryable = true;
    assert!(
        serde_json::to_string(&wrong_retryable).is_err(),
        "retryable 不符必须拒绝序列化"
    );

    let mut wrong_severity = diag(ErrorCode::ParseSyntax);
    wrong_severity.severity = Severity::Warning;
    assert!(
        serde_json::to_string(&wrong_severity).is_err(),
        "诊断级别不符必须拒绝序列化"
    );

    let mut reversed = diag(ErrorCode::ParseSyntax);
    reversed.input_range = Some((10, 5));
    assert!(
        serde_json::to_string(&reversed).is_err(),
        "倒序区间必须拒绝序列化"
    );

    let mut recovery = diag(ErrorCode::ParseSyntax);
    recovery.recovery = Some("err.parse.other.fix".to_owned());
    assert!(
        serde_json::to_string(&recovery).is_err(),
        "非派生 recovery 必须拒绝序列化"
    );

    let mut recovery_without_hint = diag(ErrorCode::UnitOverflow);
    recovery_without_hint.recovery = Some("err.unit.overflow.fix".to_owned());
    assert!(
        serde_json::to_string(&recovery_without_hint).is_err(),
        "fix_hint 为 false 的码不得输出 recovery"
    );
}

/// T-08：反序列化拒绝未知码、错误类型、越界区间、坏 trace 与恢复键。
#[test]
fn t08_deserialize_rejects_bad_input() {
    let base = json!({
        "code": "PARSE_SYNTAX",
        "domain": "parse",
        "retryable": false,
        "trace_id": TRACE,
        "diagnostics": [],
    });
    assert!(
        serde_json::from_value::<FmlError>(base.clone()).is_ok(),
        "基线必须可解析"
    );

    let mut unknown_code = base.clone();
    unknown_code["code"] = json!("NOT_A_REGISTERED_CODE");
    assert!(serde_json::from_value::<FmlError>(unknown_code).is_err());

    let mut wrong_type = base.clone();
    wrong_type["retryable"] = json!("no");
    assert!(serde_json::from_value::<FmlError>(wrong_type).is_err());

    let mut unknown_field = base.clone();
    unknown_field["condition"] = json!("解析失败");
    assert!(serde_json::from_value::<FmlError>(unknown_field).is_err());

    let mut uppercase_trace = base.clone();
    uppercase_trace["trace_id"] = json!("3F8B2C1D4E5F60718293A4B5C6D7E8F9");
    assert!(serde_json::from_value::<FmlError>(uppercase_trace).is_err());

    let mut short_trace = base.clone();
    short_trace["trace_id"] = json!("3f8b2c1d");
    assert!(serde_json::from_value::<FmlError>(short_trace).is_err());

    let mut non_hex_trace = base.clone();
    non_hex_trace["trace_id"] = json!("3f8b2c1d4e5f60718293a4b5c6d7e8gg");
    assert!(serde_json::from_value::<FmlError>(non_hex_trace).is_err());

    let mut reversed = base.clone();
    reversed["diagnostics"] =
        json!([{"code": "PARSE_SYNTAX", "severity": "error", "input_range": [9, 4]}]);
    assert!(serde_json::from_value::<FmlError>(reversed).is_err());

    let mut overflow = base.clone();
    overflow["diagnostics"] =
        json!([{"code": "PARSE_SYNTAX", "severity": "error", "input_range": [0, 4294967296_u64]}]);
    assert!(serde_json::from_value::<FmlError>(overflow).is_err());

    let mut wrong_args = base.clone();
    wrong_args["diagnostics"] = json!([{"code": "PARSE_SYNTAX", "severity": "error", "args": []}]);
    assert!(serde_json::from_value::<FmlError>(wrong_args).is_err());

    let mut diagnostic_unknown_field = base.clone();
    diagnostic_unknown_field["diagnostics"] =
        json!([{"code": "PARSE_SYNTAX", "severity": "error", "condition": "x"}]);
    assert!(
        serde_json::from_value::<FmlError>(diagnostic_unknown_field).is_err(),
        "Diagnostic 内部未声明键 Rust 侧必须拒绝"
    );

    let mut domain = base.clone();
    domain["domain"] = json!("eval");
    assert!(serde_json::from_value::<FmlError>(domain).is_err());

    let mut retryable = base.clone();
    retryable["retryable"] = json!(true);
    assert!(serde_json::from_value::<FmlError>(retryable).is_err());

    let mut severity = base;
    severity["diagnostics"] = json!([{"code": "PARSE_SYNTAX", "severity": "info"}]);
    assert!(serde_json::from_value::<FmlError>(severity).is_err());
}

/// T-08：零 trace 领域内往返成立，传输边界拒绝零值留给信封层（本 crate 不判定）。
#[test]
fn t08_zero_trace_round_trips_inside_domain() {
    let error = FmlError::new(ErrorCode::UnitOverflow);
    let text = serde_json::to_string(&error).expect("零 trace 领域内必须可序列化");
    assert!(text.contains("\"trace_id\":\"00000000000000000000000000000000\""));
    let back: FmlError = serde_json::from_str(&text).expect("零 trace 领域内必须可反序列化");
    assert_eq!(back, error);
}
