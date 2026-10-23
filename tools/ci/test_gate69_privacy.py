#!/usr/bin/env python3
"""CORE-69 阶段2 DEP-5/6 与 PRIV-1/2 验收测试。

对照 SADD/Test/S0/S0_CORE-69_TEST.md 第 6～9 行与卡 SADD/S0/S0_CORE-69_基座.md 第 12、39 行。
运行：python -m unittest tools.ci.test_gate69_privacy -v
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import common
import check_privacy

CI_DIR = Path(__file__).resolve().parent
FIXTURES = CI_DIR / "tests" / "fixtures" / "gate69_phase2"
SNIPPETS = FIXTURES / "snippets"
SCRIPT = CI_DIR / "check_privacy.py"
REPO_ROOT = CI_DIR.parent.parent

NETWORK_POLICY = "contracts/policies/network-construction.yaml"
DEP6_POLICY = "contracts/policies/dep6_symbols.txt"
PLATFORM_POLICY = "contracts/policies/platform-check-patterns.json"

NETWORK_TEXT = (
    "# 测试用网络构造白名单\n"
    "version: 1\n"
    "allow:\n"
    "  - app/lib/platform/android/net/**/*.dart\n"
    "  - app/lib/platform/windows/net/**/*.dart\n"
)
PLATFORM_TEXT = (
    '{"version": 1, "patterns": [\n'
    '  {"library": "dart:io", "receiver": "Platform",'
    ' "member": "isAndroid|isWindows|isLinux|isMacOS|isIOS|isFuchsia|operatingSystem"},\n'
    '  {"library": "package:flutter/foundation.dart", "receiver": null, "member": "defaultTargetPlatform|kIsWeb"},\n'
    '  {"library": "package:flutter/foundation.dart", "receiver": "TargetPlatform",'
    ' "member": "android|windows|linux|macOS|iOS|fuchsia"}\n'
    "]}\n"
)


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


class RepoCase(unittest.TestCase):
    """临时仓库：三份 Dart 侧策略 + 待扫描的 Dart 文件。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.write_policy(NETWORK_POLICY, NETWORK_TEXT)
        self.write_policy(DEP6_POLICY, (FIXTURES / "dep6_symbols.txt").read_text(encoding="utf-8"))
        self.write_policy(PLATFORM_POLICY, PLATFORM_TEXT)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write_policy(self, rel: str, text: str) -> None:
        write_file(self.root, rel, text)

    def dart(self, rel: str, fixture: str) -> str:
        text = snippet(fixture)
        write_file(self.root, rel, text)
        return text

    def run_cli(self, root: Path | None = None) -> tuple[int, str, str]:
        return common.run([str(SCRIPT), "--root", str(root or self.root)])

    def findings(self, root: Path | None = None) -> list[tuple]:
        items, _warnings = check_privacy.check(root or self.root)
        return [(item.path, item.line, item.rule) for item in items]

    def warnings(self, root: Path | None = None) -> list[str]:
        _items, warnings = check_privacy.check(root or self.root)
        return warnings

    def assert_gate(self, policy: str, kind: str = "") -> None:
        code, out, err = self.run_cli()
        self.assertEqual(code, 2, msg=err)
        self.assertEqual(out, "")
        lines = [item for item in err.splitlines() if item.strip()]
        self.assertEqual(len(lines), 1, msg=err)
        self.assertIn("GATE-1", lines[0])
        self.assertTrue(lines[0].startswith(policy + ": "), msg=lines[0])
        if kind:
            self.assertIn(kind, lines[0])


class PolicyErrorTests(RepoCase):
    """三份 Dart 侧策略的四类配置错误都只走 GATE-1。"""

    def test_network_missing(self) -> None:
        (self.root / NETWORK_POLICY).unlink()
        self.assert_gate(NETWORK_POLICY, "缺少策略文件")

    def test_network_unknown_field(self) -> None:
        self.write_policy(NETWORK_POLICY, NETWORK_TEXT + "extra: 1\n")
        self.assert_gate(NETWORK_POLICY, "未知字段")

    def test_network_version_not_one(self) -> None:
        self.write_policy(NETWORK_POLICY, NETWORK_TEXT.replace("version: 1", "version: 2"))
        self.assert_gate(NETWORK_POLICY, "version")

    def test_network_duplicate_key(self) -> None:
        self.write_policy(NETWORK_POLICY, NETWORK_TEXT + NETWORK_TEXT.split("allow:")[0].splitlines()[1] + "\n")
        self.assert_gate(NETWORK_POLICY, "重复")

    def test_network_duplicate_entry(self) -> None:
        text = NETWORK_TEXT + "  - app/lib/platform/android/net/**/*.dart\n"
        self.write_policy(NETWORK_POLICY, text)
        self.assert_gate(NETWORK_POLICY, "重复")

    def test_dep6_missing(self) -> None:
        (self.root / DEP6_POLICY).unlink()
        self.assert_gate(DEP6_POLICY, "缺少策略文件")

    def test_dep6_unknown_prefix(self) -> None:
        self.write_policy(DEP6_POLICY, "version:1\nfield:engine.parse\n")
        self.assert_gate(DEP6_POLICY)

    def test_dep6_version_not_one(self) -> None:
        self.write_policy(DEP6_POLICY, "version:2\nop:engine.parse\n")
        self.assert_gate(DEP6_POLICY, "version")

    def test_dep6_duplicate_symbol(self) -> None:
        self.write_policy(DEP6_POLICY, "version:1\nop:engine.parse\nop:engine.parse\n")
        self.assert_gate(DEP6_POLICY, "重复")

    def test_dep6_missing_version_line(self) -> None:
        self.write_policy(DEP6_POLICY, "op:engine.parse\n")
        self.assert_gate(DEP6_POLICY, "version")

    def test_platform_missing(self) -> None:
        (self.root / PLATFORM_POLICY).unlink()
        self.assert_gate(PLATFORM_POLICY, "缺少策略文件")

    def test_platform_unknown_field(self) -> None:
        self.write_policy(PLATFORM_POLICY, PLATFORM_TEXT.replace('{"version": 1,', '{"version": 1, "extra": 0,'))
        self.assert_gate(PLATFORM_POLICY, "未知字段")

    def test_platform_version_not_one(self) -> None:
        self.write_policy(PLATFORM_POLICY, PLATFORM_TEXT.replace('"version": 1', '"version": 2'))
        self.assert_gate(PLATFORM_POLICY, "version")

    def test_platform_duplicate_key(self) -> None:
        self.write_policy(PLATFORM_POLICY, PLATFORM_TEXT.replace('{"version": 1,', '{"version": 1, "version": 1,'))
        self.assert_gate(PLATFORM_POLICY, "重复")

    def test_platform_pattern_unknown_field(self) -> None:
        text = PLATFORM_TEXT.replace('"receiver": null,', '"receiver": null, "extra": 1,')
        self.write_policy(PLATFORM_POLICY, text)
        self.assert_gate(PLATFORM_POLICY, "未知字段")

    def test_root_not_directory(self) -> None:
        code, out, err = self.run_cli(self.root / "nope")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("-: GATE-1 "), msg=err)


class Dep5UiTests(RepoCase):
    def test_http_packages_in_ui(self) -> None:
        text = self.dart("app/lib/ui/home/http_page.dart", "ui_http.dart")
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["DEP-5", "DEP-5"])
        self.assertEqual([item[1] for item in found], [line_of(text, "package:http"), line_of(text, "package:dio")])

    def test_binding_import_in_ui(self) -> None:
        text = self.dart("app/lib/ui/home/binding_page.dart", "ui_binding.dart")
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["DEP-5", "DEP-5"])
        self.assertEqual([item[1] for item in found], [1, 2])

    def test_generated_dto_import_is_exempt(self) -> None:
        self.dart("app/lib/ui/home/dto_page.dart", "ui_binding_dto.dart")
        self.assertEqual(self.findings(), [])

    def test_platform_import_in_ui(self) -> None:
        self.dart("app/lib/ui/home/ports_page.dart", "ui_platform.dart")
        self.assertEqual([item[2] for item in self.findings()], ["DEP-5"])

    def test_holding_identifiers_in_ui(self) -> None:
        text = self.dart("app/lib/ui/home/holds_page.dart", "ui_holds.dart")
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["DEP-5", "DEP-5", "DEP-5"])
        self.assertEqual(
            [item[1] for item in found],
            [
                line_of(text, "final AppDeps deps;"),
                line_of(text, "final CoreBinding binding;"),
                line_of(text, "final PlatformPorts ports;"),
            ],
        )

    def test_deeply_nested_ui_file_is_scanned(self) -> None:
        self.dart("app/lib/ui/a/b/c/d/e/deep_page.dart", "ui_http.dart")
        self.assertEqual(len(self.findings()), 2)

    def test_non_ui_file_not_checked_for_part_a(self) -> None:
        # 非 ui 文件不做 DEP-5(a)；同一份 HTTP 导入仍按 PRIV-1 报（网络包白名单外导入）。
        self.dart("app/lib/home/http_page.dart", "ui_http.dart")
        self.assertEqual([item[2] for item in self.findings()], ["PRIV-1", "PRIV-1"])


class Dep5HttpTests(RepoCase):
    def test_platform_ports_http_read_outside_composition(self) -> None:
        text = self.dart("app/lib/home/ports_state.dart", "state_ports.dart")
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["DEP-5"])
        self.assertEqual(found[0][1], line_of(text, "ports.http"))

    def test_appdeps_http_is_not_an_error(self) -> None:
        self.dart("app/lib/home/deps_state.dart", "state_deps.dart")
        self.assertEqual(self.findings(), [])
        self.assertEqual(self.warnings(), [])

    def test_undeterminable_receiver_is_only_a_warning(self) -> None:
        self.dart("app/lib/home/indirect.dart", "state_indirect.dart")
        self.assertEqual(self.findings(), [])
        warnings = self.warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("port.http", warnings[0])
        self.assertIn("人工", warnings[0])

    def test_assignment_chain_resolves(self) -> None:
        text = self.dart("app/lib/home/chain_state.dart", "state_chain.dart")
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["DEP-5"])
        self.assertEqual(found[0][1], line_of(text, "alias.http"))

    def test_composition_is_exempt(self) -> None:
        self.dart("app/lib/composition/composition_ports.dart", "composition_ports.dart")
        self.assertEqual(self.findings(), [])

    def test_ui_file_hits_part_a_and_part_b_separately(self) -> None:
        # ui 文件同时受 DEP-5(a) 与 (b)：字段声明命中 (a)，ports.http 命中 (b)，两条都是 DEP-5。
        text = self.dart("app/lib/ui/home/ports_state.dart", "state_ports.dart")
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["DEP-5", "DEP-5"])
        self.assertEqual([item[1] for item in found], [line_of(text, "final PlatformPorts ports;"), line_of(text, "ports.http")])


class LexicalErrorTests(RepoCase):
    """词法层失败经检查器收敛为 GATE-1，括号不配对不是错误。"""

    def test_unclosed_string_is_gate(self) -> None:
        write_file(self.root, "app/lib/ui/home/broken.dart", "final s = 'abc;\n")
        code, out, err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        lines = err.strip().splitlines()
        self.assertEqual(len(lines), 1, msg=err)
        self.assertTrue(lines[0].endswith("broken.dart: GATE-1 字符串未闭合"), msg=lines[0])

    def test_unbalanced_brackets_are_not_an_error(self) -> None:
        write_file(self.root, "app/lib/home/broken.dart", "void f() {\n  g();\n")
        code, out, err = self.run_cli()
        self.assertEqual((code, out, err), (0, "", ""))


class Dep6Tests(RepoCase):
    def test_platform_symbols_reported(self) -> None:
        text = self.dart("app/lib/platform/android/adapter.dart", "platform_ops.dart")
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["DEP-6", "DEP-6", "DEP-6"])
        self.assertEqual(
            [item[1] for item in found],
            [
                line_of(text, "'engine.parse')"),
                line_of(text, "'typeset.layout')"),
                line_of(text, "FormulaNode"),
            ],
        )

    def test_const_outside_call_not_reported(self) -> None:
        text = self.dart("app/lib/platform/android/adapter.dart", "platform_ops.dart")
        lines = {item[1] for item in self.findings()}
        self.assertNotIn(line_of(text, "const String kOp"), lines)

    def test_descriptive_strings_and_comments_not_reported(self) -> None:
        self.dart("app/lib/platform/android/doc.dart", "platform_ops_string.dart")
        self.assertEqual(self.findings(), [])

    def test_dart_outside_platform_not_scanned(self) -> None:
        self.dart("app/lib/ui/home/adapter.dart", "platform_ops_string.dart")
        self.assertEqual(self.findings(), [])

    def test_type_token_in_annotation_only(self) -> None:
        text = "Object? render(DisplayList list) => null;\n"
        self.dart("app/lib/platform/android/draw.dart", "platform_ops_string.dart")
        write_file(self.root, "app/lib/platform/android/render.dart", text)
        found = [item for item in self.findings() if item[0].endswith("render.dart")]
        self.assertEqual([(item[1], item[2]) for item in found], [(1, "DEP-6")])


class Priv1Tests(RepoCase):
    def test_allowed_directory_is_exempt(self) -> None:
        self.dart("app/lib/platform/android/net/client.dart", "net_client.dart")
        self.assertEqual(self.findings(), [])

    def test_network_outside_allow_reported(self) -> None:
        text = self.dart("app/lib/home/client.dart", "net_client_outside.dart")
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["PRIV-1", "PRIV-1"])
        self.assertEqual([item[1] for item in found], [line_of(text, "package:http"), line_of(text, "HttpClient()")])

    def test_dart_io_import_alone_not_reported(self) -> None:
        text = "import 'dart:io';\nObject? open() => File('a');\n"
        write_file(self.root, "app/lib/home/files.dart", text)
        self.assertEqual(self.findings(), [])

    def test_same_token_hits_only_dep5(self) -> None:
        self.dart("app/lib/ui/home/http_page.dart", "ui_http.dart")
        rules = [item[2] for item in self.findings()]
        self.assertEqual(rules, ["DEP-5", "DEP-5"])

    def test_other_construction_in_same_file_reported(self) -> None:
        text = snippet("net_client_outside.dart")
        text += "\nObject? open() => Socket.connect('h', 1);\n"
        write_file(self.root, "app/lib/ui/home/client.dart", text)
        found = self.findings()
        self.assertEqual([item[2] for item in found], ["DEP-5", "PRIV-1", "PRIV-1"])
        self.assertEqual(found[0][1], line_of(text, "package:http"))
        self.assertEqual(found[2][1], line_of(text, "Socket.connect"))

    def test_windows_allow_glob_matches(self) -> None:
        self.dart("app/lib/platform/windows/net/client.dart", "net_client.dart")
        self.assertEqual(self.findings(), [])


class Priv2Tests(RepoCase):
    def test_platform_check_in_ui_reported(self) -> None:
        text = self.dart("app/lib/ui/home/check_page.dart", "ui_platform_check.dart")
        found = self.findings()
        self.assertEqual({item[2] for item in found}, {"PRIV-2"})
        self.assertEqual(
            [item[1] for item in found],
            [
                line_of(text, "Platform.isAndroid"),
                line_of(text, "kIsWeb"),
                line_of(text, "defaultTargetPlatform =="),
                line_of(text, "TargetPlatform.windows"),
            ],
        )

    def test_import_alias_resolved(self) -> None:
        text = self.dart("app/lib/ui/home/alias_page.dart", "ui_platform_check_alias.dart")
        found = self.findings()
        self.assertEqual({item[2] for item in found}, {"PRIV-2"})
        self.assertEqual(
            [item[1] for item in found],
            [
                line_of(text, "io.Platform.isWindows"),
                line_of(text, "f.defaultTargetPlatform"),
                line_of(text, "f.TargetPlatform.iOS"),
            ],
        )

    def test_unprovable_import_is_a_warning(self) -> None:
        self.dart("app/lib/ui/home/unprovable_page.dart", "ui_platform_unprovable.dart")
        self.assertEqual(self.findings(), [])
        warnings = self.warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("Platform.isAndroid", warnings[0])
        self.assertIn("人工", warnings[0])

    def test_platform_check_outside_ui_not_scanned(self) -> None:
        self.dart("app/lib/home/check_page.dart", "ui_platform_check.dart")
        self.assertEqual(self.findings(), [])

    def test_alias_for_other_library_does_not_match(self) -> None:
        text = "import 'dart:async' as io;\nbool f() => io.Platform.isAndroid;\n"
        write_file(self.root, "app/lib/ui/home/async_page.dart", text)
        self.assertEqual(self.findings(), [])


class OutputContractTests(RepoCase):
    def test_cli_output_equals_api_output_bytes(self) -> None:
        self.dart("app/lib/ui/home/http_page.dart", "ui_http.dart")
        self.dart("app/lib/home/client.dart", "net_client_outside.dart")
        items, _warnings = check_privacy.check(self.root)
        code, out, _err = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(out, "".join(item.format() + "\n" for item in items))
        again = self.run_cli()
        self.assertEqual((code, out), (again[0], again[1]))

    def test_findings_sorted_by_path(self) -> None:
        self.dart("app/lib/ui/home/http_page.dart", "ui_http.dart")
        self.dart("app/lib/home/client.dart", "net_client_outside.dart")
        self.dart("app/lib/platform/android/adapter.dart", "platform_ops.dart")
        paths = [item[0] for item in self.findings()]
        self.assertEqual(paths, sorted(paths))

    def test_clean_exit_code(self) -> None:
        code, out, err = self.run_cli()
        self.assertEqual((code, out, err), (0, "", ""))

    def test_repository_itself_is_clean(self) -> None:
        code, out, err = self.run_cli(REPO_ROOT)
        self.assertEqual((code, out, err), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
