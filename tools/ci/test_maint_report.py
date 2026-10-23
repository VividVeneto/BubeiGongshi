#!/usr/bin/env python3
"""CORE-71 maint_report.py 自测（标准库 unittest）。

逐条对应 SADD/Test/S0/S0_CORE-71_TEST.md 三条验收：复杂度与阈值（A 组）、稳定性与阈值装配
（B 组）、LCOV 与 previous（C 组）、报告/注解/周报/生成物（D 组）、HA-002 工程样品豁免
（W 组，窄快照、精确路径、不泛化 generated、不降覆盖）与内部契约（E 组）。

每个用例在独立临时 root 上以子进程运行 maint_report.py（与 CI 调用方式一致）；输入夹具在
tools/ci/tests/fixtures/maint_report/，临时 root 由用例拼装。Rust 复杂度用例真实调用
tools/requirements.txt 锁定的 lizard，不 skip、不用替身。
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import common  # noqa: E402
import maint_report  # noqa: E402

SCRIPT = HERE / "maint_report.py"
FIXTURES = HERE / "tests" / "fixtures" / "maint_report"
REPO_ROOT = HERE.parents[1]
CODES_RS = REPO_ROOT / "crates" / "fml-error" / "src" / "codes.rs"
NL = chr(10)

THRESHOLD_LINES = (
    "file_max_lines: 800",
    "fn_max_ccn: 15",
    "core_line_coverage: 0.80",
    "dart_ccn_warn_only: true",
)


class MaintReportTest(unittest.TestCase):
    """公共夹具：临时 root、源文件、LCOV、core-sources 与 CLI 调用。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, relative: str, text: str) -> Path:
        """在临时 root 下写文件并返回绝对路径。"""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def write_bytes(self, relative: str, data: bytes) -> Path:
        """按原始字节写文件（行尾与快照指纹用例必须精确到字节，不走 write_text 的换行转换）。"""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def fixture(self, name: str) -> str:
        """读取静态夹具原文。"""
        return (FIXTURES / name).read_text(encoding="utf-8")

    def thresholds(self, **overrides: object) -> None:
        """写 thresholds.yaml；缺省即卡面默认四键。"""
        values = {
            "file_max_lines": 800,
            "fn_max_ccn": 15,
            "core_line_coverage": "0.80",
            "dart_ccn_warn_only": "true",
        }
        values.update(overrides)
        lines = ["# 自测阈值"]
        for key in ("file_max_lines", "fn_max_ccn", "core_line_coverage", "dart_ccn_warn_only"):
            value = values.get(key)
            if value is None:
                continue
            lines.append(key + ": " + str(value))
        self.write("tools/ci/thresholds.yaml", NL.join(lines) + NL)

    def lcov(self, records: list[tuple[str, list[int]]], name: str = "build/core.lcov") -> Path:
        """按 (路径, 行计数列表) 生成 LCOV；LF/LH 与逐行计算一致。"""
        lines: list[str] = []
        for path, counts in records:
            lines.append("SF:" + path)
            hit = 0
            for index, count in enumerate(counts, start=1):
                lines.append("DA:" + str(index) + "," + str(count))
                if count > 0:
                    hit += 1
            lines.append("LF:" + str(len(counts)))
            lines.append("LH:" + str(hit))
            lines.append("end_of_record")
        return self.write(name, NL.join(lines) + NL)

    def core_sources(self, paths: list[str], name: str = "build/core-sources.json") -> Path:
        """写 core-sources.json（按字节序去重排序）。"""
        ordered = sorted(set(paths), key=lambda item: item.encode("utf-8"))
        return self.write(name, json.dumps({"version": 1, "paths": ordered}, ensure_ascii=False))

    def run_cli(self, *extra: str, out: str = "build/maint.md", lcov: str | None = "build/core.lcov",
                core: str | None = "build/core-sources.json", annotations: bool = False):
        """运行 maint_report.py，返回 (退出码, stdout, stderr)。"""
        argv = [sys.executable, str(SCRIPT), "--root", str(self.root), "--out", str(self.root / out)]
        if lcov is not None:
            argv += ["--lcov", str(self.root / lcov)]
        if core is not None:
            argv += ["--core-sources", str(self.root / core)]
        if annotations:
            argv += ["--annotations"]
        argv += [str(item) for item in extra]
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8")
        return proc.returncode, proc.stdout, proc.stderr

    def report(self, out: str = "build/maint.md") -> dict:
        """读取同名 JSON 报告。"""
        return json.loads((self.root / out).with_suffix(".json").read_text(encoding="utf-8"))

    def markdown(self, out: str = "build/maint.md") -> str:
        """读取 maint.md 正文。"""
        return (self.root / out).read_text(encoding="utf-8")

    def dart_case(self, text: str, **overrides: object):
        """单 Dart 文件 + 全命中 LCOV 的最小 root。"""
        self.thresholds(**overrides)
        self.write("app/lib/a.dart", text)
        self.core_sources(["app/lib/a.dart"])
        self.lcov([("app/lib/a.dart", [1, 1, 1, 1])])
        return self.run_cli()

    def rust_case(self, text: str, **overrides: object):
        """单 Rust 文件 + 全命中 LCOV 的最小 root。"""
        self.thresholds(**overrides)
        self.write("crates/a/src/lib.rs", text)
        self.core_sources(["crates/a/src/lib.rs"])
        self.lcov([("crates/a/src/lib.rs", [1, 1, 1, 1])])
        return self.run_cli()

    def file_entry(self, path: str) -> dict:
        """取报告中某个文件的度量条目。"""
        for item in self.report()["files"]:
            if item["path"] == path:
                return item
        self.fail("报告中没有文件条目：" + path)


class DartComplexityTest(MaintReportTest):
    """A1-A6：Dart 近似复杂度的固定期望值。"""

    def test_a1_comments_and_strings_do_not_count(self) -> None:
        """注释与字符串字面量里的 if/for/while 不计入复杂度。"""
        code, out, err = self.dart_case(self.fixture("dart_comments_strings.dart"))
        self.assertEqual((code, out), (0, ""), err)
        self.assertEqual(self.file_entry("app/lib/a.dart")["max_ccn"], 1)

    def test_a2_nested_closure_counted_separately(self) -> None:
        """嵌套闭包单独计分：外层 if 与闭包内 if 合计不得合并成 3。"""
        code, out, err = self.dart_case(self.fixture("dart_nested_closure.dart"))
        self.assertEqual((code, out), (0, ""), err)
        functions, warnings = maint_report.dart_functions(
            "a.dart", maint_report.source_scan.tokens(self.root / "app/lib/a.dart", "dart"))
        self.assertEqual([item.ccn for item in functions], [2, 2], warnings)
        self.assertEqual(self.file_entry("app/lib/a.dart")["max_ccn"], 2)

    def test_a3_ternary_adds_one(self) -> None:
        """三元表达式各 +1。"""
        code, out, err = self.dart_case(self.fixture("dart_ternary.dart"))
        self.assertEqual((code, out), (0, ""), err)
        self.assertEqual(self.file_entry("app/lib/a.dart")["max_ccn"], 2)

    def test_a4_fixed_sample_is_three(self) -> None:
        """卡面固定样例 f(){if(a&&b)x();} 期望 3。"""
        code, out, err = self.dart_case(self.fixture("dart_fixed_sample.dart"))
        self.assertEqual((code, out), (0, ""), err)
        self.assertEqual(self.file_entry("app/lib/a.dart")["max_ccn"], 3)

    def test_a5_else_null_aware_not_counted(self) -> None:
        """else、??、?. 不计分。"""
        code, out, err = self.dart_case(self.fixture("dart_else_null.dart"))
        self.assertEqual((code, out), (0, ""), err)
        self.assertEqual(self.file_entry("app/lib/a.dart")["max_ccn"], 2)

    def test_a6_do_while_counts_once(self) -> None:
        """do-while 只计 while 一次。"""
        code, out, err = self.dart_case(self.fixture("dart_do_while.dart"))
        self.assertEqual((code, out), (0, ""), err)
        self.assertEqual(self.file_entry("app/lib/a.dart")["max_ccn"], 2)

    def test_a11_undecidable_function_head_warns(self) -> None:
        """无法判定的函数头输出 warning 并列入人工项，不猜成函数。"""
        text = "void f() {" + NL + "  g(a; b) {" + NL + "  }" + NL + "}" + NL
        code, out, err = self.dart_case(text)
        self.assertEqual((code, out), (0, ""), err)
        self.assertIn("无法判定函数头", self.markdown())

class ThresholdTest(MaintReportTest):
    """A7-A10：文件行数与复杂度阈值对退出码的作用。"""

    def test_a7_file_over_max_lines_exits_one(self) -> None:
        """文件超过 file_max_lines 退出 1。"""
        body = NL.join(["// filler"] * 801) + NL + "pub fn a() {}" + NL
        code, out, err = self.rust_case(body, file_max_lines=800)
        self.assertEqual((code, out), (1, ""), err)
        rules = [item["rule"] for item in self.report()["violations"]]
        self.assertIn("file-lines", rules)

    def test_a8_rust_ccn_over_threshold_exits_one(self) -> None:
        """Rust 复杂度超过 fn_max_ccn 退出 1（真实 lizard）。"""
        code, out, err = self.rust_case(self.fixture("rust_over_threshold.rs"), fn_max_ccn=15)
        self.assertEqual((code, out), (1, ""), err)
        self.assertGreater(self.file_entry("crates/a/src/lib.rs")["max_ccn"], 15)
        self.assertIn("rust-ccn", [item["rule"] for item in self.report()["violations"]])

    def test_a9_dart_over_threshold_warn_only_true(self) -> None:
        """dart_ccn_warn_only=true 时 Dart 超阈值只 warning：退出 0 且报告与注解留痕。"""
        code, out, err = self.dart_case(self.fixture("dart_over_threshold.dart"),
                                        dart_ccn_warn_only="true")
        self.assertEqual((code, out), (0, ""), err)
        self.assertIn("dart-ccn", [item["rule"] for item in self.report()["violations"]])
        code2, out2, err2 = self.run_cli(annotations=True, out="build/maint2.md")
        self.assertEqual(code2, 0, err2)
        self.assertIn("::warning file=app/lib/a.dart", out2)
        self.assertIn("title=dart-ccn", out2)

    def test_a10_dart_over_threshold_warn_only_false_exits_one(self) -> None:
        """dart_ccn_warn_only=false 时 Dart 超阈值退出 1。"""
        code, out, err = self.dart_case(self.fixture("dart_over_threshold.dart"),
                                        dart_ccn_warn_only="false")
        self.assertEqual((code, out), (1, ""), err)
        code2, out2, err2 = self.run_cli(annotations=True, out="build/maint2.md")
        self.assertEqual(code2, 1, err2)
        self.assertIn("::error file=app/lib/a.dart", out2)


class StabilityTest(MaintReportTest):
    """B1-B9：重复运行稳定性与阈值装配。"""

    def minimal(self, thresholds_text: str):
        """写指定阈值正文并准备最小可运行输入。"""
        self.write("tools/ci/thresholds.yaml", thresholds_text)
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        self.lcov([("app/lib/a.dart", [1])])
        return self.run_cli()

    def test_b1_two_runs_are_byte_identical(self) -> None:
        """相同输入重复运行，md 与 json 逐字节一致。"""
        self.write("crates/a/src/lib.rs", "pub fn f(x: i32) -> i32 {" + NL + "    if x > 0 { 1 } else { 0 }" + NL + "}" + NL)
        self.thresholds()
        self.core_sources(["crates/a/src/lib.rs"])
        self.lcov([("crates/a/src/lib.rs", [1, 1, 1])])
        first = self.run_cli(out="build/one.md")
        second = self.run_cli(out="build/two.md")
        self.assertEqual((first[0], second[0]), (0, 0), first[2] + second[2])
        for suffix in (".md", ".json"):
            left = (self.root / ("build/one" + suffix)).read_bytes()
            right = (self.root / ("build/two" + suffix)).read_bytes()
            self.assertEqual(left, right, suffix + " 两次运行不一致")

    def test_b2_missing_previous_marks_baseline(self) -> None:
        """--previous 不存在时输出 baseline 标记且不报退化。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        self.lcov([("app/lib/a.dart", [1])])
        code, out, err = self.run_cli("--previous", str(self.root / "build/absent.json"))
        self.assertEqual((code, out), (0, ""), err)
        self.assertIn("baseline", self.markdown())

    def test_b3_unknown_threshold_key_exits_two(self) -> None:
        """未知阈值键退出 2。"""
        text = NL.join(THRESHOLD_LINES + ("foo: 1",)) + NL
        code, out, err = self.minimal(text)
        self.assertEqual((code, out), (2, ""), err)
        self.assertIn("GATE-1", err)
        self.assertIn("未知阈值键", err)

    def test_b4_missing_threshold_key_exits_two(self) -> None:
        """缺阈值键退出 2（不静默补默认值）。"""
        text = NL.join(THRESHOLD_LINES[:3]) + NL
        code, out, err = self.minimal(text)
        self.assertEqual((code, out), (2, ""), err)
        self.assertIn("缺少阈值键", err)

    def test_b5_file_max_lines_zero_exits_two(self) -> None:
        """file_max_lines=0 超出范围退出 2。"""
        text = NL.join(("file_max_lines: 0",) + THRESHOLD_LINES[1:]) + NL
        code, _out, err = self.minimal(text)
        self.assertEqual(code, 2, err)
        self.assertIn("file_max_lines", err)

    def test_b5b_fn_max_ccn_negative_exits_two(self) -> None:
        """fn_max_ccn 为负数退出 2。"""
        text = NL.join((THRESHOLD_LINES[0], "fn_max_ccn: -1") + THRESHOLD_LINES[2:]) + NL
        code, _out, err = self.minimal(text)
        self.assertEqual(code, 2, err)
        self.assertIn("fn_max_ccn", err)

    def test_b5c_coverage_zero_exits_two(self) -> None:
        """core_line_coverage=0 超出范围退出 2。"""
        text = NL.join((THRESHOLD_LINES[0], THRESHOLD_LINES[1], "core_line_coverage: 0.0", THRESHOLD_LINES[3])) + NL
        code, _out, err = self.minimal(text)
        self.assertEqual(code, 2, err)
        self.assertIn("core_line_coverage", err)

    def test_b5d_coverage_above_one_exits_two(self) -> None:
        """core_line_coverage=1.5 超出范围退出 2。"""
        text = NL.join((THRESHOLD_LINES[0], THRESHOLD_LINES[1], "core_line_coverage: 1.5", THRESHOLD_LINES[3])) + NL
        code, _out, err = self.minimal(text)
        self.assertEqual(code, 2, err)

    def test_b5e_dart_warn_only_string_exits_two(self) -> None:
        """dart_ccn_warn_only 写成字符串 "true" 退出 2（不做强转）。"""
        text = NL.join((THRESHOLD_LINES[0], THRESHOLD_LINES[1], THRESHOLD_LINES[2], 'dart_ccn_warn_only: "true"')) + NL
        code, _out, err = self.minimal(text)
        self.assertEqual(code, 2, err)
        self.assertIn("dart_ccn_warn_only", err)

    def test_b6_broken_yaml_exits_two(self) -> None:
        """YAML 解析失败退出 2。"""
        code, _out, err = self.minimal("file_max_lines: [" + NL)
        self.assertEqual(code, 2, err)
        self.assertIn("YAML 解析失败", err)

    def test_b7_threshold_change_moves_exit_code(self) -> None:
        """同一 LCOV 夹具在 0.80 下退出 1、在 2/3 下退出 0。"""
        self.write("crates/a/src/lib.rs", "pub fn f() {}" + NL)
        self.core_sources(["crates/a/src/lib.rs"])
        counts = [1, 1, 1, 1, 1, 1, 1, 0, 0, 0]
        self.lcov([("crates/a/src/lib.rs", counts)])
        self.thresholds()
        strict = self.run_cli(out="build/strict.md")
        self.assertEqual(strict[0], 1, strict[2])
        self.thresholds(core_line_coverage="2/3")
        relaxed = self.run_cli(out="build/relaxed.md")
        self.assertEqual(relaxed[0], 0, relaxed[2])
        self.assertEqual(self.report("build/relaxed.md")["coverage"]["ratio"], 0.7)

    def test_b8_exact_boundary_passes(self) -> None:
        """恰达阈值（4/6 对 2/3）通过，不做四舍五入。"""
        self.write("crates/a/src/lib.rs", "pub fn f() {}" + NL)
        self.core_sources(["crates/a/src/lib.rs"])
        self.lcov([("crates/a/src/lib.rs", [1, 1, 1, 1, 0, 0])])
        self.thresholds(core_line_coverage="2/3")
        code, _out, err = self.run_cli()
        self.assertEqual(code, 0, err)
        self.assertTrue(self.report()["coverage"]["hit"] == 4)

    def test_b9_report_has_fixed_five_parts(self) -> None:
        """报告固定含 files/unsafe/ffi/coverage/violations 与各自子字段。"""
        self.thresholds()
        self.write("crates/a/src/lib.rs", "pub fn f() {}" + NL)
        self.core_sources(["crates/a/src/lib.rs"])
        self.lcov([("crates/a/src/lib.rs", [1])])
        code, _out, err = self.run_cli()
        self.assertEqual(code, 0, err)
        document = self.report()
        self.assertEqual(document["version"], 1)
        self.assertEqual(set(document), {"version", "files", "unsafe", "ffi", "coverage", "violations"})
        self.assertEqual(set(document["files"][0]), {"path", "lines", "max_ccn", "generated"})
        self.assertEqual(set(document["unsafe"]), {"blocks", "safety_missing", "files"})
        self.assertEqual(set(document["ffi"]), {"extern_c_blocks", "exported_symbols", "files"})
        self.assertEqual(set(document["coverage"]), {"hit", "total", "ratio", "missing"})


class LcovTest(MaintReportTest):
    """C1-C14：LCOV 协议、覆盖率判定与 previous 输入校验。"""

    def five_files(self) -> list[str]:
        """建 5 个核心源文件并返回路径。"""
        paths = []
        for index in range(5):
            relative = "crates/c" + str(index) + "/src/lib.rs"
            self.write(relative, "pub fn f" + str(index) + "() {}" + NL)
            paths.append(relative)
        return sorted(paths)

    def test_c1_four_of_five_passes(self) -> None:
        """4/5 = 80% 通过。"""
        paths = self.five_files()
        self.thresholds()
        self.core_sources(paths)
        self.lcov([(path, [1]) for path in paths[:4]] + [(paths[4], [0])])
        code, _out, err = self.run_cli()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.report()["coverage"]["ratio"], 0.8)

    def test_c2_three_of_five_exits_one(self) -> None:
        """3/5 低于 80% 退出 1。"""
        paths = self.five_files()
        self.thresholds()
        self.core_sources(paths)
        self.lcov([(path, [1]) for path in paths[:3]] + [(path, [0]) for path in paths[3:]])
        code, _out, err = self.run_cli()
        self.assertEqual(code, 1, err)
        self.assertIn("coverage", [item["rule"] for item in self.report()["violations"]])

    def test_c3_missing_core_sf_exits_two(self) -> None:
        """缺核心 SF 退出 2，不当作 0/0 通过。"""
        paths = self.five_files()
        self.thresholds()
        self.core_sources(paths)
        self.lcov([(path, [1]) for path in paths[:4]])
        code, out, err = self.run_cli()
        self.assertEqual((code, out), (2, ""), err)
        self.assertIn("缺少核心源文件记录", err)

    def test_c4_empty_lcov_exits_two(self) -> None:
        """空报告退出 2。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        self.write("build/core.lcov", NL)
        code, _out, err = self.run_cli()
        self.assertEqual(code, 2, err)
        self.assertIn("空报告", err)

    def test_c5_missing_lcov_argument_exits_two(self) -> None:
        """缺 --lcov 退出 2。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        self.lcov([("app/lib/a.dart", [1])])
        code, _out, err = self.run_cli(lcov=None)
        self.assertEqual(code, 2, err)
        self.assertIn("缺少必需参数：--lcov", err)

    def test_c5b_missing_core_sources_argument_exits_two(self) -> None:
        """缺 --core-sources 退出 2。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.lcov([("app/lib/a.dart", [1])])
        code, _out, err = self.run_cli(core=None)
        self.assertEqual(code, 2, err)
        self.assertIn("缺少必需参数：--core-sources", err)

    def test_c6_duplicate_da_exits_two(self) -> None:
        """同一 (path,line) 的重复 DA 退出 2。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        text = NL.join(("SF:app/lib/a.dart", "DA:1,1", "DA:1,0", "end_of_record")) + NL
        self.write("build/core.lcov", text)
        code, _out, err = self.run_cli()
        self.assertEqual(code, 2, err)
        self.assertIn("重复的 DA 记录", err)

    def test_c7_negative_count_exits_two(self) -> None:
        """DA 负计数退出 2。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        self.write("build/core.lcov", NL.join(("SF:app/lib/a.dart", "DA:1,-1", "end_of_record")) + NL)
        code, _out, err = self.run_cli()
        self.assertEqual(code, 2, err)
        self.assertIn("负数", err)

    def test_c7b_line_zero_exits_two(self) -> None:
        """DA 行号 0 退出 2。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        self.write("build/core.lcov", NL.join(("SF:app/lib/a.dart", "DA:0,1", "end_of_record")) + NL)
        code, _out, err = self.run_cli()
        self.assertEqual(code, 2, err)

    def test_c8_lf_lh_mismatch_exits_two(self) -> None:
        """LF/LH 与逐行计算不符退出 2。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        text = NL.join(("SF:app/lib/a.dart", "DA:1,1", "LF:6", "LH:1", "end_of_record")) + NL
        self.write("build/core.lcov", text)
        code, _out, err = self.run_cli()
        self.assertEqual(code, 2, err)
        self.assertIn("LF", err)

    def test_c9_sf_outside_root_exits_two(self) -> None:
        """绝对 SF 越出 root 退出 2。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        text = NL.join(("SF:/tmp/outside.rs", "DA:1,1", "end_of_record")) + NL
        self.write("build/core.lcov", text)
        code, _out, err = self.run_cli()
        self.assertEqual(code, 2, err)
        self.assertIn("越出 root", err)

    def test_c10_outside_file_not_counted(self) -> None:
        """集合外文件的覆盖率不抬高比例，且列明排除。"""
        paths = self.five_files()
        self.write("crates/other/src/extra.rs", "pub fn g() {}" + NL)
        self.thresholds()
        self.core_sources(paths)
        self.lcov([(path, [1]) for path in paths[:3]] + [(path, [0]) for path in paths[3:]]
                  + [("crates/other/src/extra.rs", [1, 1, 1])])
        code, _out, err = self.run_cli()
        self.assertEqual(code, 1, err)
        document = self.report()
        self.assertEqual(document["coverage"]["total"], 5)
        self.assertEqual(document["coverage"]["ratio"], 0.6)
        self.assertIn("crates/other/src/extra.rs", self.markdown())

    def test_c11_zero_denominator_exits_two(self) -> None:
        """集合内只有 SF 无 DA 时分母为 0，退出 2。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        self.write("build/core.lcov", NL.join(("SF:app/lib/a.dart", "end_of_record")) + NL)
        code, _out, err = self.run_cli()
        self.assertEqual(code, 2, err)
        self.assertIn("分母为 0", err)

    def test_c12_sf_without_da_ignored(self) -> None:
        """SF 存在但无 DA 的文件视为 0 可执行行：不进分母也不判失败。"""
        paths = self.five_files()
        self.thresholds()
        self.core_sources(paths)
        text = NL.join(("SF:" + paths[0], "end_of_record")) + NL
        for path in paths[1:]:
            text += NL.join(("SF:" + path, "DA:1,1", "end_of_record")) + NL
        self.write("build/core.lcov", text)
        code, _out, err = self.run_cli()
        self.assertEqual(code, 0, err)
        document = self.report()
        self.assertEqual(document["coverage"]["total"], 4)
        self.assertEqual(document["coverage"]["hit"], 4)
        self.assertEqual(document["coverage"]["missing"], [paths[0]])

    def test_c13_duplicate_sf_exits_two(self) -> None:
        """同一 SF 出现两次退出 2。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        text = NL.join(("SF:app/lib/a.dart", "DA:1,1", "end_of_record",
                        "SF:app/lib/a.dart", "DA:1,1", "end_of_record")) + NL
        self.write("build/core.lcov", text)
        code, _out, err = self.run_cli()
        self.assertEqual(code, 2, err)
        self.assertIn("重复的 SF", err)

    def test_c14_previous_corrupt_exits_two(self) -> None:
        """previous 损坏、version 非 1、缺字段都退出 2（不降级为 baseline）。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        self.lcov([("app/lib/a.dart", [1])])
        broken = self.write("build/prev.json", "{not json")
        code, _out, err = self.run_cli("--previous", str(broken), out="build/r1.md")
        self.assertEqual(code, 2, err)

        bad_version = self.write("build/prev2.json", json.dumps({"version": 2, "files": [], "unsafe": {},
                                                                 "ffi": {}, "coverage": {}, "violations": []}))
        code, _out, err = self.run_cli("--previous", str(bad_version), out="build/r2.md")
        self.assertEqual(code, 2, err)
        self.assertIn("version", err)

        missing_field = self.write("build/prev3.json", json.dumps({"version": 1, "files": [], "unsafe": {}}))
        code, _out, err = self.run_cli("--previous", str(missing_field), out="build/r3.md")
        self.assertEqual(code, 2, err)
        self.assertIn("缺少字段", err)




class ReportContentTest(MaintReportTest):
    """D1-D8：unsafe/FFI 计数、生成物口径、注解、周报与 pending-target。"""

    def test_d1_unsafe_ffi_counts(self) -> None:
        """unsafe 块、缺 SAFETY、extern C 与导出符号按词法计数。"""
        code, out, err = self.rust_case(self.fixture("rust_unsafe_ffi.rs"))
        self.assertEqual((code, out), (0, ""), err)
        document = self.report()
        self.assertEqual(document["unsafe"]["blocks"], 2)
        self.assertEqual(document["unsafe"]["safety_missing"], 1)
        self.assertEqual(document["unsafe"]["files"], ["crates/a/src/lib.rs"])
        self.assertEqual(document["ffi"]["extern_c_blocks"], 2)
        self.assertEqual(document["ffi"]["exported_symbols"], 1)
        self.assertEqual(document["ffi"]["files"], ["crates/a/src/lib.rs"])

    def test_d2_generated_dart_excluded(self) -> None:
        """*.g.dart 完全不入表、不产生违规。"""
        self.thresholds()
        self.write("app/lib/big.g.dart", NL.join(["// filler"] * 2000) + NL)
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        self.lcov([("app/lib/a.dart", [1])])
        code, _out, err = self.run_cli()
        self.assertEqual(code, 0, err)
        paths = [item["path"] for item in self.report()["files"]]
        self.assertNotIn("app/lib/big.g.dart", paths)

    def test_d3_codes_rs_marked_generated(self) -> None:
        """crates/fml-error/src/codes.rs 计入并标 generated=true。"""
        self.thresholds()
        self.write("crates/fml-error/src/codes.rs", NL.join(["// 生成物"] * 5) + NL)
        self.core_sources(["crates/fml-error/src/codes.rs"])
        self.lcov([("crates/fml-error/src/codes.rs", [1])])
        code, _out, err = self.run_cli()
        self.assertEqual(code, 0, err)
        self.assertTrue(self.file_entry("crates/fml-error/src/codes.rs")["generated"])

    def test_d4_codes_rs_participates_in_thresholds(self) -> None:
        """非获准快照的 codes.rs 仍参与文件长度阈值：不继承 HA-002 豁免（C71-P01/HA-002）。"""
        self.thresholds()
        self.write("crates/fml-error/src/codes.rs", NL.join(["// 生成物"] * 901) + NL)
        self.core_sources(["crates/fml-error/src/codes.rs"])
        self.lcov([("crates/fml-error/src/codes.rs", [1])])
        code, _out, err = self.run_cli()
        self.assertEqual(code, 1, err)
        self.assertIn("file-lines", [item["rule"] for item in self.report()["violations"]])

    def test_d5_annotations_use_path_line_rule_without_source(self) -> None:
        """--annotations 输出 path/line/rule 且不含源代码。"""
        self.thresholds()
        self.write("crates/a/src/lib.rs", NL.join(["// filler"] * 801) + NL + "pub fn a() {}" + NL)
        self.core_sources(["crates/a/src/lib.rs"])
        self.lcov([("crates/a/src/lib.rs", [1])])
        code, out, err = self.run_cli(annotations=True)
        self.assertEqual(code, 1, err)
        annotations = [line for line in out.splitlines() if line.startswith("::")]
        self.assertEqual(len(annotations), 1, out)
        self.assertTrue(annotations[0].startswith("::error file=crates/a/src/lib.rs,title=file-lines::"))
        self.assertNotIn("filler", out)

    def test_d6_no_network_or_comment_posting(self) -> None:
        """脚本不发 PR 评论、不做网络调用。"""
        text = SCRIPT.read_text(encoding="utf-8")
        for needle in ("urllib", "http.client", "requests", "socket", "subprocess"):
            self.assertNotIn(needle, text)

    def test_d7_previous_produces_comparison(self) -> None:
        """weekly 对比走 --previous 分支并输出差异段。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources(["app/lib/a.dart"])
        self.lcov([("app/lib/a.dart", [1])])
        first = self.run_cli(out="build/first.md")
        self.assertEqual(first[0], 0, first[2])
        previous = str((self.root / "build/first.md").with_suffix(".json"))
        second = self.run_cli("--previous", previous, out="build/second.md")
        self.assertEqual(second[0], 0, second[2])
        text = self.markdown("build/second.md")
        self.assertIn("文件数：", text)
        self.assertIn("覆盖率：", text)

    def test_d8_empty_core_sources_is_pending_target(self) -> None:
        """领域集合为空 = pending-target：退出 0、正文标记、不按 0/0 判通过。"""
        self.thresholds()
        self.write("app/lib/a.dart", "void f() {" + NL + "}" + NL)
        self.core_sources([])
        self.lcov([("app/lib/a.dart", [1])])
        code, out, err = self.run_cli()
        self.assertEqual(code, 0, err)
        self.assertIn("pending-target", out)
        document = self.report()
        self.assertEqual(document["coverage"], {"hit": 0, "total": 0, "ratio": None, "missing": []})
        self.assertIn("pending-target", self.markdown())


class SampleWaiverTest(MaintReportTest):
    """W1-W15：HA-002 工程样品豁免的窄范围、真实度量保留与反例。

    获准输入全部来自仓库现值的真实快照（crates/fml-error/src/codes.rs 原字节），真实调用
    lizard 得到 239 CCN；夹具内容一旦漂移，W15 会显式失败并提示重新裁定，不自动续期。
    """

    def approved_root(self, data: bytes | None = None) -> None:
        """把获准快照写到精确路径；默认取仓库现值，可传入改写后的字节。"""
        raw = CODES_RS.read_bytes() if data is None else data
        self.write_bytes(maint_report.HA002_PATH, raw)

    def approved_inputs(self, *extra_core: str, **overrides: object) -> None:
        """默认阈值 + 以获准路径为核心源且全覆盖的输入（额外核心源各自 4/4 覆盖）。"""
        self.thresholds(**overrides)
        self.core_sources([maint_report.HA002_PATH, *extra_core])
        records = [(maint_report.HA002_PATH, [1, 1, 1, 1])]
        for path in extra_core:
            records.append((path, [1, 1, 1, 1]))
        self.lcov(records)

    def rule_names(self) -> list[str]:
        """当前报告里的违规规则名序列（按报告排序）。"""
        return [item["rule"] for item in self.report()["violations"]]

    def waived_messages(self) -> list[str]:
        """带 HA-002 前缀的违规消息（应为获准的两条）。"""
        return [item["message"] for item in self.report()["violations"]
                if item["message"].startswith(maint_report.HA002_MARKER)]

    def test_w1_approved_snapshot_waives_exactly_two_rules(self) -> None:
        """获准快照 + 默认 800/15：退出 0，真实 1312/239 与原两条违规保留且带前缀。"""
        self.approved_root()
        self.approved_inputs()
        code, out, err = self.run_cli(annotations=True)
        self.assertEqual(code, 0, err)
        entry = self.file_entry(maint_report.HA002_PATH)
        self.assertEqual((entry["lines"], entry["max_ccn"], entry["generated"]), (1312, 239, True))
        self.assertEqual([(item["rule"], item["path"]) for item in self.report()["violations"]],
                         [("file-lines", maint_report.HA002_PATH), ("rust-ccn", maint_report.HA002_PATH)])
        self.assertEqual(len(self.waived_messages()), 2)
        annotations = [line for line in out.splitlines() if line.startswith("::")]
        self.assertEqual(len(annotations), 2, out)
        for line in annotations:
            self.assertTrue(line.startswith("::warning "), line)
        self.assertIn("HA-002 样品豁免已应用", out)
        text = self.markdown()
        for needle in ("HA-002 工程样品豁免（已应用）", maint_report.HA002_SNAPSHOT_SHA256, "1312",
                       "239", "不等于原卡阈值达标", "发布必须拒绝", "RL 待收回"):
            self.assertIn(needle, text)

    def test_w2_default_limits_are_required(self) -> None:
        """阈值改成 799/14（合法但非默认）即不豁免：退出 1、消息无前缀、正文写未应用原因。"""
        self.approved_root()
        self.approved_inputs(file_max_lines=799)
        code, _out, err = self.run_cli()
        self.assertEqual(code, 1, err)
        self.assertEqual(self.rule_names(), ["file-lines", "rust-ccn"])
        self.assertEqual(self.waived_messages(), [])
        text = self.markdown()
        self.assertIn("HA-002 工程样品豁免（未应用）", text)
        self.assertIn("按配置严格判定", text)
        metrics = maint_report.measure_files(self.root)[0]
        waiver = maint_report.evaluate_sample_waiver(
            self.root, metrics, maint_report.Thresholds(799, 14, Fraction(4, 5), True))
        self.assertFalse(waiver.applied)
        self.assertIn("默认 800/15", waiver.reason)

    def test_w3_looser_threshold_follows_config(self) -> None:
        """阈值放宽到 1312 时按配置判定：只剩 rust-ccn 一条阻断，且不带豁免前缀。"""
        self.approved_root()
        self.approved_inputs(file_max_lines=1312)
        code, _out, err = self.run_cli()
        self.assertEqual(code, 1, err)
        self.assertEqual(self.rule_names(), ["rust-ccn"])
        self.assertEqual(self.waived_messages(), [])

    def test_w4_copy_at_other_path_is_not_waived(self) -> None:
        """同内容复制到其他路径不得取得豁免（只认精确路径）。"""
        self.write_bytes("crates/other/src/codes.rs", CODES_RS.read_bytes())
        self.thresholds()
        self.core_sources(["crates/other/src/codes.rs"])
        self.lcov([("crates/other/src/codes.rs", [1, 1, 1, 1])])
        code, _out, err = self.run_cli()
        self.assertEqual(code, 1, err)
        self.assertEqual(self.rule_names(), ["file-lines", "rust-ccn"])
        self.assertEqual(self.waived_messages(), [])
        self.assertIn("不在本次度量表内", self.markdown())

    def test_w5_similar_basename_is_not_waived(self) -> None:
        """相似 basename（codes_extra.rs）不做通配匹配，不得豁免。"""
        self.write_bytes("crates/fml-error/src/codes_extra.rs", CODES_RS.read_bytes())
        self.thresholds()
        self.core_sources(["crates/fml-error/src/codes_extra.rs"])
        self.lcov([("crates/fml-error/src/codes_extra.rs", [1, 1, 1, 1])])
        code, _out, err = self.run_cli()
        self.assertEqual(code, 1, err)
        self.assertEqual(self.waived_messages(), [])

    def test_w6_modified_snapshot_is_not_waived(self) -> None:
        """快照改动一个字符即回到严格判定：正文写明快照不匹配。"""
        self.approved_root(CODES_RS.read_bytes() + b"// snapshot drift" + NL.encode("utf-8"))
        self.approved_inputs()
        code, _out, err = self.run_cli()
        self.assertEqual(code, 1, err)
        self.assertEqual(self.rule_names(), ["file-lines", "rust-ccn"])
        self.assertEqual(self.waived_messages(), [])
        self.assertIn("快照不匹配", self.markdown())

    def test_w7_crlf_snapshot_is_the_same_snapshot(self) -> None:
        """CRLF 副本按 LF 规范化后是同一快照：同样豁免，物理行数口径不变。"""
        self.approved_root(CODES_RS.read_bytes().replace(b"\n", b"\r\n"))
        self.approved_inputs()
        code, _out, err = self.run_cli()
        self.assertEqual(code, 0, err)
        entry = self.file_entry(maint_report.HA002_PATH)
        self.assertEqual((entry["lines"], entry["max_ccn"]), (1312, 239))
        self.assertEqual(len(self.waived_messages()), 2)

    def test_w8_unwaived_violation_still_blocks(self) -> None:
        """获准快照叠加普通文件 801 行：仍退出 1，且该条注解是 error、获准两条是 warning。"""
        self.approved_root()
        self.write("crates/b/src/lib.rs", NL.join(["// filler"] * 801) + NL)
        self.approved_inputs()
        code, out, err = self.run_cli(annotations=True)
        self.assertEqual(code, 1, err)
        plain = [(item["rule"], item["path"]) for item in self.report()["violations"]
                 if not item["message"].startswith(maint_report.HA002_MARKER)]
        self.assertEqual(plain, [("file-lines", "crates/b/src/lib.rs")])
        self.assertEqual(len(self.waived_messages()), 2)
        self.assertIn("::error file=crates/b/src/lib.rs,title=file-lines::", out)

    def test_w9_coverage_failure_is_not_waived(self) -> None:
        """获准快照叠加覆盖率不足（4/8）：退出 1，coverage 违规不带豁免前缀。"""
        self.approved_root()
        self.write("crates/c/src/lib.rs", "pub fn f() {}" + NL)
        self.thresholds()
        self.core_sources([maint_report.HA002_PATH, "crates/c/src/lib.rs"])
        self.lcov([(maint_report.HA002_PATH, [1, 1, 1, 1]), ("crates/c/src/lib.rs", [0, 0, 0, 0])])
        code, _out, err = self.run_cli()
        self.assertEqual(code, 1, err)
        self.assertIn("coverage", self.rule_names())
        self.assertEqual(self.report()["coverage"]["ratio"], 0.5)
        self.assertEqual(len(self.waived_messages()), 2)

    def test_w9b_waiver_with_pending_target_keeps_both_markers(self) -> None:
        """获准快照 + 领域集合为空：约定仍是 dev 的 pending-target（0），但两个标记同时可见。

        本用例只锁定“豁免不吞掉 pending 表达”：正文与 stdout 都必须写明 pending-target，
        JSON 覆盖率仍是 0/0/None，不得据此声称 0/0 通过。
        """
        self.approved_root()
        self.thresholds()
        self.core_sources([])
        self.lcov([(maint_report.HA002_PATH, [1, 1, 1, 1])])
        code, out, err = self.run_cli()
        self.assertEqual(code, 0, err)
        self.assertIn("HA-002 样品豁免已应用", out)
        self.assertIn("pending-target", out)
        self.assertEqual(self.report()["coverage"], {"hit": 0, "total": 0, "ratio": None, "missing": []})
        text = self.markdown()
        self.assertIn("HA-002 工程样品豁免（已应用）", text)
        self.assertIn("pending-target", text)

    def test_w10_tool_errors_win_over_waiver(self) -> None:
        """配置或参数错误仍是 2：豁免不覆盖工具错误、不提前成功。"""
        self.approved_root()
        self.write("tools/ci/thresholds.yaml", NL.join(THRESHOLD_LINES + ("unknown_key: 1",)) + NL)
        self.core_sources([maint_report.HA002_PATH])
        self.lcov([(maint_report.HA002_PATH, [1])])
        code, out, err = self.run_cli()
        self.assertEqual((code, out), (2, ""), err)
        self.assertIn("未知阈值键", err)
        self.thresholds()
        code, out, err = self.run_cli(lcov=None)
        self.assertEqual((code, out), (2, ""), err)
        self.assertIn("缺少必需参数：--lcov", err)

    def test_w11_symlink_alias_is_not_waived(self) -> None:
        """符号链接别名不得借获准快照取得豁免（本机不允许建链接时跳过）。"""
        target = self.write_bytes("snapshot-target.rs", CODES_RS.read_bytes())
        link = self.root / maint_report.HA002_PATH
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("本机不允许创建符号链接：" + type(exc).__name__)
        self.approved_inputs()
        code, _out, err = self.run_cli()
        self.assertEqual(code, 1, err)
        self.assertEqual(self.waived_messages(), [])
        self.assertIn("不是普通非符号链接文件", self.markdown())

    def test_w12_symlink_guard_is_enforced(self) -> None:
        """普通文件守卫本身可失败：把获准路径判成符号链接时判定必须为未应用。"""
        self.approved_root()
        metrics = maint_report.measure_files(self.root)[0]
        thresholds = maint_report.Thresholds(800, 15, Fraction(4, 5), True)
        self.assertTrue(maint_report.evaluate_sample_waiver(self.root, metrics, thresholds).applied)
        with mock.patch.object(Path, "is_symlink", lambda _path: True):
            waiver = maint_report.evaluate_sample_waiver(self.root, metrics, thresholds)
        self.assertFalse(waiver.applied)
        self.assertIn("符号链接", waiver.reason)

    def test_w13_json_shape_stays_fixed_and_stable(self) -> None:
        """不新增 JSON 字段/阈值键：字段集固定，重复运行 md 与 json 逐字节一致。"""
        self.approved_root()
        self.approved_inputs()
        first = self.run_cli(out="build/one.md")
        second = self.run_cli(out="build/two.md")
        self.assertEqual((first[0], second[0]), (0, 0), first[2] + second[2])
        for suffix in (".md", ".json"):
            left = (self.root / ("build/one" + suffix)).read_bytes()
            right = (self.root / ("build/two" + suffix)).read_bytes()
            self.assertEqual(left, right, suffix + " 两次运行不一致")
        document = self.report("build/one.md")
        self.assertEqual(set(document), {"version", "files", "unsafe", "ffi", "coverage", "violations"})
        self.assertEqual(set(document["files"][0]), {"path", "lines", "max_ccn", "generated"})
        for item in document["violations"]:
            self.assertEqual(set(item), {"rule", "path", "line", "message"})
        self.assertEqual(set(maint_report.THRESHOLD_KEYS),
                         {"file_max_lines", "fn_max_ccn", "core_line_coverage", "dart_ccn_warn_only"})

    def test_w14_previous_compares_real_values(self) -> None:
        """--previous 仍比较真实度量（4/4 -> 4/4），并显式说明退出 0 不代表原阈值达标。"""
        self.approved_root()
        self.approved_inputs()
        first = self.run_cli(out="build/first.md")
        self.assertEqual(first[0], 0, first[2])
        previous = str((self.root / "build/first.md").with_suffix(".json"))
        second = self.run_cli("--previous", previous, out="build/second.md")
        self.assertEqual(second[0], 0, second[2])
        text = self.markdown("build/second.md")
        self.assertIn("覆盖率：4/4 -> 4/4", text)
        self.assertIn("HA-002 样品豁免已应用", text)
        self.assertIn("不代表原阈值达标", text)

    def test_w15_repository_snapshot_matches_policy(self) -> None:
        """仓库现值仍是获准快照：路径为普通文件且 LF 规范化 SHA256 一致。

        生成物一变这里就会失败：豁免必须按新快照重新裁定（发布前由所有者收回），不得自动续期。
        """
        self.assertTrue(CODES_RS.is_file(), str(CODES_RS))
        self.assertFalse(CODES_RS.is_symlink())
        self.assertEqual(maint_report.snapshot_sha256(CODES_RS), maint_report.HA002_SNAPSHOT_SHA256,
                         "生成物已变化：HA-002 豁免须按新快照重新裁定，不得自动续期")


class InternalContractTest(MaintReportTest):
    """E 组：本卡对词法层交付物的输入契约。"""

    def test_e1_overlapping_token_stream_is_gate_error(self) -> None:
        """词法 token 流重叠时按工具错误退出 2，不用它算复杂度。"""
        overlapping = [common.Token("fn f", 0, 1, "code"), common.Token("f(", 2, 1, "code")]
        with self.assertRaises(common.GateError):
            maint_report.require_ordered_tokens("x.rs", overlapping)
        ordered = [common.Token("fn", 0, 1, "code"), common.Token("f", 3, 1, "code")]
        maint_report.require_ordered_tokens("x.rs", ordered)

    def test_e2_lexer_overlap_fixture_exits_two(self) -> None:
        """CORE-69 阶段1 B2（字面量紧邻代码）在修复前必须显式失败，不产出错误复杂度。"""
        tokens = maint_report.source_scan.tokens(FIXTURES / "dart_comments_strings.dart", "dart")
        offsets = [token.offset for token in tokens]
        self.assertEqual(offsets, sorted(offsets), "夹具本身不应触发重叠（上游 B2 修复后仍成立）")


if __name__ == "__main__":
    unittest.main()
