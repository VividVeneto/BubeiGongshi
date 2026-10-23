#!/usr/bin/env python3
"""CORE-69 阶段2 DEP-1～4 验收测试。

对照 SADD/Test/S0/S0_CORE-69_TEST.md 第 6～9 行与卡 SADD/S0/S0_CORE-69_基座.md 第 12、39 行。
运行：cd tools/ci && python -m unittest test_gate69_deps -v
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import common
import check_deps
import source_scan

CI_DIR = Path(__file__).resolve().parent
FIXTURES = CI_DIR / "tests" / "fixtures" / "gate69_phase2"
SNIPPETS = FIXTURES / "snippets"
SCRIPT = CI_DIR / "check_deps.py"
REPO_ROOT = CI_DIR.parent.parent

ALLOW_HEADER = "# 测试用依赖允许表\nversion: 1\ncrates:\n"

BASE_ALLOW = {
    "fml-error": [],
    "fml-ast": ["fml-error"],
    "fml-store": ["fml-ast", "fml-error"],
    "fml-ffi": ["fml-ast", "fml-store", "fml-error"],
    "fml-pack": ["fml-store", "fml-error"],
    "fml-sync": ["fml-sync-proto", "fml-error"],
    "fml-sync-proto": ["fml-error"],
    "fml-server": ["fml-sync-proto", "fml-error"],
}

# DEP-1 测试要建一些"已实现但依赖为空"的辅助 crate，必须同时登记进策略表，
# 否则"已实现包缺策略条目"会先触发 GATE-1。
HELPER_ALLOW = {
    **BASE_ALLOW,
    "fml-latex": ["fml-error"],
    "fml-typeset": ["fml-error"],
    "fml-srs": ["fml-error"],
}


def snippet(name: str) -> str:
    return (SNIPPETS / name).read_text(encoding="utf-8")


def line_of(text: str, needle: str, occurrence: int = 0) -> int:
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(needle, start + 1)
    return text[:start].count("\n") + 1


def write_file(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def allow_text(allow: dict[str, list[str]]) -> str:
    lines = [ALLOW_HEADER.rstrip("\n")]
    for name, deps in allow.items():
        lines.append(f"  {name}: [{', '.join(deps)}]")
    return "\n".join(lines) + "\n"


def cargo_manifest(name: str, deps: str = "") -> str:
    head = f'[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2024"\n'
    return head + ("\n[dependencies]\n" + deps if deps else "")


def path_dep(name: str, target: str) -> str:
    return f'{name} = {{ path = "{target}" }}\n'


class RepoCase(unittest.TestCase):
    """在临时目录里搭一个最小仓库：dep-allow.yaml + 若干 Cargo.toml。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.write_allow(BASE_ALLOW)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write_allow(self, allow: dict[str, list[str]] | str) -> None:
        self.write_allow_text(allow if isinstance(allow, str) else allow_text(allow))

    def write_allow_text(self, text: str) -> None:
        write_file(self.root, "contracts/policies/dep-allow.yaml", text)

    def crate(self, name: str, deps: str = "", rel: str | None = None) -> None:
        write_file(self.root, (rel or f"crates/{name}") + "/Cargo.toml", cargo_manifest(name, deps))

    def ensure(self, *names: str) -> None:
        for name in names:
            if not (self.root / f"crates/{name}/Cargo.toml").is_file():
                self.crate(name)

    def run_cli(self, root: Path | None = None) -> tuple[int, str, str]:
        return common.run([str(SCRIPT), "--root", str(root or self.root)])

    def findings(self, root: Path | None = None) -> list[tuple]:
        items, _warnings = check_deps.check(root or self.root)
        return [(item.path, item.line, item.rule) for item in items]

    def messages(self, rel: str) -> list[str]:
        items, _warnings = check_deps.check(self.root)
        return [item.message for item in items if item.path == rel]


class PolicyErrorTests(RepoCase):
    """四类配置错误都只走 GATE-1：stderr 单行、stdout 为空、退出 2。"""

    def assert_gate(self, expected_in_message: str = "") -> None:
        code, out, err = self.run_cli()
        self.assertEqual(code, 2, msg=err)
        self.assertEqual(out, "")
        lines = err.strip().splitlines()
        self.assertEqual(len(lines), 1, msg=err)
        self.assertIn("GATE-1", lines[0])
        self.assertTrue(lines[0].startswith("contracts/policies/dep-allow.yaml: "), msg=lines[0])
        if expected_in_message:
            self.assertIn(expected_in_message, lines[0])

    def test_missing_policy_file(self) -> None:
        (self.root / "contracts/policies/dep-allow.yaml").unlink()
        self.assert_gate("缺少策略文件")

    def test_unknown_field(self) -> None:
        self.write_allow_text("# 未知顶层字段\nversion: 1\ncrates:\n  fml-error: []\nunknown_key: 1\n")
        self.assert_gate("未知字段")

    def test_version_not_one(self) -> None:
        self.write_allow_text("# 版本非 1\nversion: 2\ncrates:\n  fml-error: []\n")
        self.assert_gate("version")

    def test_duplicate_package_key(self) -> None:
        self.write_allow_text("# 重复键\nversion: 1\ncrates:\n  fml-error: []\n  fml-error: []\n")
        self.assert_gate("重复")

    def test_duplicate_element(self) -> None:
        self.write_allow_text("# 重复元素\nversion: 1\ncrates:\n  fml-ast: [fml-error, fml-error]\n")
        self.assert_gate("重复")

    def test_wildcard_element(self) -> None:
        self.write_allow_text("# 通配符\nversion: 1\ncrates:\n  fml-ast: ['*']\n")
        self.assert_gate("*")

    def test_self_dependency(self) -> None:
        self.write_allow_text("# 自依赖\nversion: 1\ncrates:\n  fml-ast: [fml-ast]\n")
        self.assert_gate("自依赖")

    def test_crates_not_mapping(self) -> None:
        self.write_allow_text("# crates 非映射\nversion: 1\ncrates: []\n")
        self.assert_gate("crates")

    def test_implemented_package_without_entry(self) -> None:
        self.crate("fml-extra")
        self.assert_gate("fml-extra")

    def test_root_not_directory(self) -> None:
        code, out, err = self.run_cli(self.root / "nope")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("-: GATE-1 "), msg=err)


class Dep1Tests(RepoCase):
    def setUp(self) -> None:
        super().setUp()
        self.crate("fml-error")
        self.crate("fml-ast", path_dep("fml-error", "../fml-error"))
        self.crate("fml-store", path_dep("fml-error", "../fml-error"))

    def test_clean_graph(self) -> None:
        code, out, err = self.run_cli()
        self.assertEqual((code, out, err), (0, "", ""))
        self.assertEqual(self.findings(), [])

    def test_unlisted_edge_reports_dep1_with_line(self) -> None:
        self.write_allow(HELPER_ALLOW)
        self.ensure("fml-latex")
        text = cargo_manifest("fml-ast", path_dep("fml-error", "../fml-error") + path_dep("fml-latex", "../fml-latex"))
        write_file(self.root, "crates/fml-ast/Cargo.toml", text)
        code, out, _err = self.run_cli()
        self.assertEqual(code, 1)
        line = line_of(text, "fml-latex = { path")
        self.assertEqual(out, f"crates/fml-ast/Cargo.toml:{line}: DEP-1 直接依赖 fml-latex 未登记在 dep-allow.yaml\n")

    def test_dev_build_and_target_edges_are_checked(self) -> None:
        self.write_allow(HELPER_ALLOW)
        self.ensure("fml-latex", "fml-typeset", "fml-srs")
        text = cargo_manifest("fml-ast", path_dep("fml-error", "../fml-error"))
        text += "\n[dev-dependencies]\n" + path_dep("fml-latex", "../fml-latex")
        text += "\n[build-dependencies]\n" + path_dep("fml-typeset", "../fml-typeset")
        text += "\n[target.'cfg(unix)'.dependencies]\n" + path_dep("fml-srs", "../fml-srs")
        write_file(self.root, "crates/fml-ast/Cargo.toml", text)
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["DEP-1", "DEP-1", "DEP-1"])
        self.assertEqual(
            [item[1] for item in found],
            [
                line_of(text, "fml-latex = { path"),
                line_of(text, "fml-typeset = { path"),
                line_of(text, "fml-srs = { path"),
            ],
        )

    def test_workspace_inheritance_uses_key_name(self) -> None:
        text = cargo_manifest("fml-ast", "fml-latex = { workspace = true }\n")
        write_file(self.root, "crates/fml-ast/Cargo.toml", text)
        found = self.findings()
        self.assertEqual([(item[2], item[1]) for item in found], [("DEP-1", line_of(text, "fml-latex"))])

    def test_workspace_inherited_registry_dependency_is_ignored(self) -> None:
        write_file(
            self.root,
            "Cargo.toml",
            '[workspace]\nmembers = ["crates/*"]\n\n[workspace.dependencies]\nserde = "1.0.229"\n',
        )
        self.crate("fml-error", "serde = { workspace = true }\n")
        self.assertEqual(self.findings(), [])

    def test_alias_cannot_bypass(self) -> None:
        self.write_allow(HELPER_ALLOW)
        self.ensure("fml-latex")
        text = cargo_manifest("fml-ast", 'renamed = { path = "../fml-latex", package = "fml-latex" }\n')
        write_file(self.root, "crates/fml-ast/Cargo.toml", text)
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["DEP-1"])
        self.assertIn("fml-latex", self.messages("crates/fml-ast/Cargo.toml")[0])

    def test_alias_to_allowed_package_passes(self) -> None:
        text = cargo_manifest("fml-ast", 'fml_error = { path = "../fml-error", package = "fml-error" }\n')
        write_file(self.root, "crates/fml-ast/Cargo.toml", text)
        self.assertEqual(self.findings(), [])

    def test_registry_and_git_do_not_participate(self) -> None:
        text = cargo_manifest(
            "fml-ast",
            'serde = "1"\nserde_json = { version = "1", features = [] }\n'
            'other = { git = "https://example.invalid/x" }\n',
        )
        write_file(self.root, "crates/fml-ast/Cargo.toml", text)
        self.assertEqual(self.findings(), [])

    def test_path_outside_repo_is_gate(self) -> None:
        text = cargo_manifest("fml-ast", path_dep("outside", "../../../outside"))
        write_file(self.root, "crates/fml-ast/Cargo.toml", text)
        code, out, err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn("crates/fml-ast/Cargo.toml: GATE-1 ", err)
        self.assertIn("仓库外", err)

    def test_path_dep_without_manifest_is_gate(self) -> None:
        text = cargo_manifest("fml-ast", path_dep("fml-ghost", "../fml-ghost"))
        write_file(self.root, "crates/fml-ast/Cargo.toml", text)
        code, out, err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("Cargo.toml", err)

    def test_server_edges(self) -> None:
        self.ensure("fml-sync-proto")
        write_file(
            self.root,
            "server/Cargo.toml",
            cargo_manifest("fml-server", path_dep("fml-sync-proto", "../crates/fml-sync-proto")),
        )
        self.assertEqual(self.findings(), [])
        text = cargo_manifest(
            "fml-server",
            path_dep("fml-sync-proto", "../crates/fml-sync-proto") + path_dep("fml-store", "../crates/fml-store"),
        )
        write_file(self.root, "server/Cargo.toml", text)
        found = self.findings()
        self.assertEqual([(item[0], item[2]) for item in found], [("server/Cargo.toml", "DEP-1")])
        self.assertEqual(found[0][1], line_of(text, "fml-store = { path"))

    def test_store_to_pack_rejected(self) -> None:
        self.ensure("fml-pack")
        self.crate("fml-store", path_dep("fml-pack", "../fml-pack"))
        found = self.findings()
        self.assertEqual([(item[0], item[2]) for item in found], [("crates/fml-store/Cargo.toml", "DEP-1")])

    def test_sync_to_store_rejected_as_dep3(self) -> None:
        self.ensure("fml-sync-proto")
        self.crate("fml-sync", path_dep("fml-sync-proto", "../fml-sync-proto") + path_dep("fml-store", "../fml-store"))
        found = self.findings()
        self.assertEqual([(item[0], item[2]) for item in found], [("crates/fml-sync/Cargo.toml", "DEP-3")])

    def test_pack_to_store_is_not_dep3(self) -> None:
        self.ensure("fml-pack")
        self.crate("fml-pack", path_dep("fml-store", "../fml-store"))
        self.assertEqual(self.findings(), [])

    def test_cycle_reports_dep1(self) -> None:
        allow = dict(BASE_ALLOW)
        allow["fml-latex"] = ["fml-units"]
        allow["fml-units"] = ["fml-latex"]
        self.write_allow(allow)
        self.crate("fml-latex", path_dep("fml-units", "../fml-units"))
        self.crate("fml-units", path_dep("fml-latex", "../fml-latex"))
        items, _warnings = check_deps.check(self.root)
        self.assertEqual([item.rule for item in items], ["DEP-1"])
        self.assertIn("环", items[0].message)
        self.assertIn("fml-latex", items[0].message)
        self.assertIn("fml-units", items[0].message)
        self.assertEqual(items[0].path, "crates/fml-latex/Cargo.toml")

    def test_domain_may_depend_on_ast_for_cancel_flag(self) -> None:
        # CORE-01 §依赖方向 1 的取消例外：fml-type 可依赖 fml-ast 只为 CancelFlag，DEP-1 只查上界。
        self.write_allow({**BASE_ALLOW, "fml-type": ["fml-ast", "fml-error"]})
        self.crate("fml-type", path_dep("fml-error", "../fml-error") + path_dep("fml-ast", "../fml-ast"))
        self.assertEqual(self.findings(), [])

    def test_unclosed_block_comment_is_gate(self) -> None:
        write_file(self.root, "crates/fml-ast/src/lib.rs", "/* 未闭合的块注释\nfn f() {}\n")
        code, out, err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn("GATE-1", err)

    def test_unbalanced_brackets_are_not_an_error(self) -> None:
        write_file(self.root, "crates/fml-ast/src/lib.rs", "fn f() {\n    let x = 1;\n")
        code, out, err = self.run_cli()
        self.assertEqual((code, out, err), (0, "", ""))

    def test_reserved_package_needs_no_implementation(self) -> None:
        self.write_allow({**BASE_ALLOW, "fml-grade": ["fml-error"]})
        self.assertEqual(self.findings(), [])

    def test_duplicate_package_name_is_gate(self) -> None:
        write_file(self.root, "crates/copy/Cargo.toml", cargo_manifest("fml-error"))
        code, out, _err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_unparseable_manifest_is_gate(self) -> None:
        write_file(self.root, "crates/broken/Cargo.toml", "this is not toml\n")
        code, out, err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("GATE-1", err)


class Dep3Tests(RepoCase):
    def setUp(self) -> None:
        super().setUp()
        self.crate("fml-error")
        self.crate("fml-store")
        self.crate("fml-ffi")

    def test_domain_to_store_reports_dep3_even_when_registered(self) -> None:
        allow = dict(BASE_ALLOW)
        allow["fml-ast"] = ["fml-error", "fml-store"]
        self.write_allow(allow)
        text = cargo_manifest("fml-ast", path_dep("fml-error", "../fml-error") + path_dep("fml-store", "../fml-store"))
        write_file(self.root, "crates/fml-ast/Cargo.toml", text)
        found = self.findings()
        self.assertEqual([(item[2], item[1]) for item in found], [("DEP-3", line_of(text, "fml-store = { path"))])

    def test_domain_to_ffi_reports_dep3(self) -> None:
        allow = dict(BASE_ALLOW)
        allow["fml-ast"] = ["fml-error", "fml-ffi"]
        self.write_allow(allow)
        text = cargo_manifest("fml-ast", path_dep("fml-ffi", "../fml-ffi"))
        write_file(self.root, "crates/fml-ast/Cargo.toml", text)
        found = self.findings()
        self.assertEqual([(item[2], item[1]) for item in found], [("DEP-3", line_of(text, "fml-ffi = { path"))])

    def test_same_edge_reports_only_dep3(self) -> None:
        allow = dict(BASE_ALLOW)
        allow["fml-type"] = ["fml-error"]
        self.write_allow(allow)
        text = cargo_manifest("fml-type", path_dep("fml-store", "../fml-store"))
        write_file(self.root, "crates/fml-type/Cargo.toml", text)
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["DEP-3"])

    def test_domain_set_includes_fml_sync(self) -> None:
        self.ensure("fml-sync-proto")
        text = cargo_manifest("fml-sync", path_dep("fml-store", "../fml-store"))
        write_file(self.root, "crates/fml-sync/Cargo.toml", text)
        self.assertEqual([item[2] for item in self.findings()], ["DEP-3"])

    def test_store_may_depend_on_domain(self) -> None:
        self.crate("fml-ast", path_dep("fml-error", "../fml-error"))
        text = cargo_manifest("fml-store", path_dep("fml-ast", "../fml-ast"))
        write_file(self.root, "crates/fml-store/Cargo.toml", text)
        self.assertEqual(self.findings(), [])


class Dep2Tests(RepoCase):
    def setUp(self) -> None:
        super().setUp()
        self.crate("fml-error")
        self.text = snippet("domain_io.rs")

    def test_domain_io_reported_with_lines(self) -> None:
        write_file(self.root, "crates/fml-ast/src/lib.rs", self.text)
        found = self.findings()
        expected = [
            line_of(self.text, "use std::fs;"),
            line_of(self.text, "use std::net as net_alias;"),
            line_of(self.text, "use std::time::SystemTime;"),
            line_of(self.text, "fs::metadata"),
            line_of(self.text, "net_alias::TcpStream"),
            line_of(self.text, "SystemTime::now"),
            line_of(self.text, "std::fs::read"),
        ]
        self.assertEqual([item[2] for item in found], ["DEP-2"] * len(expected))
        self.assertEqual([item[1] for item in found], expected)
        self.assertEqual({item[0] for item in found}, {"crates/fml-ast/src/lib.rs"})

    def test_instant_duration_and_literals_not_reported(self) -> None:
        write_file(self.root, "crates/fml-ast/src/lib.rs", self.text)
        lines = {item[1] for item in self.findings()}
        self.assertNotIn(line_of(self.text, "use std::time::{Duration, Instant};"), lines)
        self.assertNotIn(line_of(self.text, "const DOC"), lines)
        self.assertNotIn(line_of(self.text, "// 注释里的"), lines)
        self.assertNotIn(line_of(self.text, "Instant::now"), lines)

    def test_non_domain_crate_not_scanned(self) -> None:
        write_file(self.root, "crates/fml-store/src/lib.rs", self.text)
        self.assertEqual(self.findings(), [])

    def test_exit_one_on_domain_io(self) -> None:
        write_file(self.root, "crates/fml-ast/src/lib.rs", self.text)
        code, out, _err = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn("DEP-2", out)
        self.assertNotIn("std::fs::read", out)
        self.assertNotIn("SOURCE", out)


class Dep4Tests(RepoCase):
    def setUp(self) -> None:
        super().setUp()
        self.crate("fml-error")
        self.crate("fml-ast")
        self.crate("fml-ffi")
        self.text = snippet("extern_c.rs")

    def test_crates_rs_reported(self) -> None:
        write_file(self.root, "crates/fml-ast/src/lib.rs", self.text)
        found = self.findings()
        expected = [
            line_of(self.text, 'unsafe extern "C" fn'),
            line_of(self.text, 'extern "C" {'),
            line_of(self.text, 'extern "C" fn plain_entry'),
        ]
        self.assertEqual([item[2] for item in found], ["DEP-4"] * 3)
        self.assertEqual([item[1] for item in found], expected)

    def test_ffi_src_exempt(self) -> None:
        write_file(self.root, "crates/fml-ffi/src/lib.rs", self.text)
        self.assertEqual(self.findings(), [])

    def test_ffi_tests_outside_src_reported(self) -> None:
        write_file(self.root, "crates/fml-ffi/tests/abi.rs", self.text)
        self.assertEqual([item[2] for item in self.findings()], ["DEP-4"] * 3)

    def test_headers_and_cpp_not_scanned(self) -> None:
        write_file(self.root, "crates/fml-ffi/include/fmlcore.h", self.text)
        write_file(self.root, "contracts/include/fmlcore.h", self.text)
        write_file(self.root, "crates/fml-ast/src/extra.cpp", self.text)
        self.assertEqual(self.findings(), [])

    def test_strings_and_comments_not_reported(self) -> None:
        write_file(self.root, "crates/fml-ast/src/lib.rs", self.text)
        lines = {item[1] for item in self.findings()}
        self.assertNotIn(line_of(self.text, "const DOC"), lines)
        self.assertNotIn(line_of(self.text, "// 注释里的"), lines)


class LanguageInferenceTests(RepoCase):
    """[R18] tokens() 无 language 时按后缀推断；未登记后缀 → 2。"""

    def test_infers_rust(self) -> None:
        path = write_file(self.root, "crates/fml-ast/src/lib.rs", snippet("domain_io.rs"))
        self.assertEqual(source_scan.tokens(path)[0].kind, "comment")
        self.assertEqual(source_scan.tokens(path, "rust")[0].kind, "comment")

    def test_infers_dart(self) -> None:
        path = write_file(self.root, "app/lib/ui/home/http_page.dart", snippet("ui_http.dart"))
        self.assertEqual(source_scan.tokens(path)[0].text, "import")

    def test_infers_cpp(self) -> None:
        path = write_file(self.root, "contracts/include/fmlcore.h", 'extern "C" {\n}\n')
        self.assertEqual(source_scan.tokens(path)[0].text, "extern")

    def test_unregistered_suffix_is_gate(self) -> None:
        path = write_file(self.root, "app/lib/ui/home/notes.txt", "x\n")
        with self.assertRaises(common.GateError):
            source_scan.tokens(path)

    def test_scan_tree_paths_are_repo_relative_and_sorted(self) -> None:
        write_file(self.root, "crates/fml-ast/src/b.rs", "fn b() {}\n")
        write_file(self.root, "crates/fml-ast/src/a.rs", "fn a() {}\n")
        paths = [rel for rel, _token in source_scan.scan_tree(self.root / "crates", {".rs"})]
        self.assertEqual(paths, sorted(paths))
        self.assertIn("fml-ast/src/a.rs", paths)


class OutputContractTests(RepoCase):
    def test_cli_output_equals_api_output_bytes(self) -> None:
        self.write_allow(HELPER_ALLOW)
        self.ensure("fml-latex")
        self.crate("fml-error")
        self.crate("fml-ast", path_dep("fml-latex", "../fml-latex"))
        items, warnings = check_deps.check(self.root)
        self.assertEqual(warnings, [])
        code, out, err = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(out, "".join(item.format() + "\n" for item in items))
        self.assertEqual(err, "")
        again = self.run_cli()
        self.assertEqual((code, out), (again[0], again[1]))

    def test_findings_sorted_by_path(self) -> None:
        self.write_allow(HELPER_ALLOW)
        self.ensure("fml-latex", "fml-typeset", "fml-srs")
        self.crate("fml-error")
        self.crate("fml-ast", path_dep("fml-latex", "../fml-latex") + path_dep("fml-typeset", "../fml-typeset"))
        self.crate("fml-srs", path_dep("fml-latex", "../fml-latex"))
        paths = [item[0] for item in self.findings()]
        self.assertEqual(paths, sorted(paths))

    def test_repository_itself_is_clean(self) -> None:
        code, out, err = self.run_cli(REPO_ROOT)
        self.assertEqual((code, out, err), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
