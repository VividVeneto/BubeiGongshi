//! Public ABI shape, canonical fixture and concurrency checks (same fixture on both hosts).
use fmlcore::{abi::*, ops::*};
use serde_json::{Value, json};
fn take(buf: FmlBuf) -> Vec<u8> {
    assert!(!buf.ptr.is_null());
    // SAFETY: Returned core allocation is live and copied before free.
    let bytes = unsafe { std::slice::from_raw_parts(buf.ptr, buf.len) }.to_vec();
    assert_eq!(fml_free_buffer(buf), 0);
    bytes
}
#[test]
fn header_and_static_manifest_consistency() {
    let header = include_str!("../../../contracts/include/fmlcore.h");
    assert!(header.contains("#define FML_ABI_MAJOR 1"));
    assert!(header.contains("#define FML_ABI_MINOR 0"));
    let caps: Value = serde_json::from_slice(&take(fml_capabilities())).unwrap();
    assert_eq!(
        caps["abi"],
        format!("{}.{}", fml_abi_version() >> 16, fml_abi_version() & 65535)
    );
    assert_eq!(caps["build"]["app"], env!("CARGO_PKG_VERSION"));
    assert_eq!(caps["build"]["target"], env!("FML_TARGET"));
    assert_eq!(caps["build"]["git"], env!("FML_GIT"));
    assert_eq!(
        caps["build"]["test_build"],
        cfg!(any(feature = "test_ops", feature = "abi_major_bump"))
    );
    let manifest: Value =
        serde_json::from_str(include_str!("../../../contracts/dto/manifest.json")).unwrap();
    let names: std::collections::HashSet<_> = OPS.iter().map(|e| e.op).collect();
    assert_eq!(names.len(), OPS.len());
    assert_eq!(caps["ops"].as_array().unwrap().len(), OPS.len());
    for e in OPS {
        let projected = caps["ops"]
            .as_array()
            .unwrap()
            .iter()
            .find(|v| v["op"] == e.op)
            .unwrap();
        assert_eq!(projected["dto"], 1);
        assert_eq!(projected["budget"], BUDGET_OPS.contains(&e.op));
        assert_eq!(
            projected["mode"],
            if e.mode == OpMode::Sync {
                "call"
            } else {
                "submit"
            }
        );
        if !cfg!(feature = "test_ops") {
            let rows = manifest["ops"].as_array().unwrap();
            let row = rows.iter().find(|v| v["op"] == e.op).unwrap();
            assert_eq!(row["mode"], projected["mode"]);
            assert_eq!(
                row["scope"],
                match e.scope {
                    Scope::None => "none",
                    Scope::Device => "device",
                    Scope::Profile => "profile",
                }
            );
        }
    }
    if !cfg!(feature = "test_ops") {
        assert!(OPS.is_empty());
    }
}
#[test]
fn error_fixtures_remain_canonical() {
    let fixture: Value =
        serde_json::from_str(include_str!("../../../contracts/vectors/errors-v1.json")).unwrap();
    assert_eq!(fixture["error_version"], 1);
    for case in fixture["cases"].as_array().unwrap() {
        let parsed = serde_json::from_value::<fml_error::FmlError>(case["input"]["error"].clone());
        if case["valid"] == false {
            assert!(parsed.is_err(), "{}", case["id"]);
        } else {
            assert_eq!(
                serde_json::to_string(&parsed.unwrap()).unwrap(),
                case["canonical"].as_str().unwrap()
            );
        }
    }
}
#[test]
fn identical_wire_fixture_and_parallel_calls() {
    let fixture: Value = serde_json::from_str(include_str!("fixtures/unknown.json")).unwrap();
    let req = serde_json::to_vec(&fixture["request"]).unwrap();
    let expected = fixture["response"].as_str().unwrap();
    let workers: Vec<_> = (0..8)
        .map(|_| {
            let req = req.clone();
            std::thread::spawn(move || {
                for _ in 0..100 {
                    let mut out = FmlBuf::default();
                    // SAFETY: Static C name, live input vector and exclusive aligned output.
                    let s = unsafe {
                        fml_call(c"missing.op".as_ptr(), req.as_ptr(), req.len(), &mut out)
                    };
                    assert_eq!(s, -2);
                    assert_eq!(
                        String::from_utf8(take(out)).unwrap(),
                        serde_json::from_str::<Value>(include_str!("fixtures/unknown.json"))
                            .unwrap()["response"]
                    );
                }
            })
        })
        .collect();
    for w in workers {
        w.join().unwrap();
    }
    assert!(expected.contains("FFI_UNKNOWN_OP"));
}
#[test]
fn ffi_codes_match_registry_source() {
    let registry = include_str!("../../../contracts/errors/registry.yaml");
    for (status, code) in [
        (-1, "FFI_BAD_ARG"),
        (-2, "FFI_UNKNOWN_OP"),
        (-3, "FFI_VERSION_MISMATCH"),
        (-4, "FFI_STALE_HANDLE"),
        (-5, "FFI_PANIC"),
        (-6, "FFI_BUSY"),
    ] {
        let block = registry
            .split(&format!(
                "- code: {code}
"
            ))
            .nth(1)
            .unwrap()
            .split(
                "
- code:",
            )
            .next()
            .unwrap();
        assert!(block.contains("severity: error"));
        let retry = status == -6;
        assert!(block.contains(&format!("retryable: {retry}")));
        let error = fml_error::FmlError::new(code.parse().unwrap());
        assert_eq!(error.retryable, retry);
        assert_eq!(serde_json::to_value(error).unwrap()["domain"], json!("ffi"));
    }
}
