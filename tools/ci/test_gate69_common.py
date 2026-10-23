"""CORE-69 阶段1：common.py 的自测（标准库 unittest，无需 pytest）。

覆盖测试方案 S0_CORE-69_TEST.md:6 的 GATE-1 通道属性（退出2只走 GATE-1、stderr 单行、
stdout 为空、不输出部分 Finding、环境错误 path 为 `-`）与 :7 的导入面，
按准备材料 T31～T36/T41 编号组织；DEP/PRIV 与四份 policy 的四类配置错误属阶段2。
"""

from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

CI_DIR = Path(__file__).resolve().parent
if str(CI_DIR) not in sys.path:
    sys.path.insert(0, str(CI_DIR))

import common  # noqa: E402

GATE_LINE_RE = re.compile(r"^(?P<path>.+): GATE-1 (?P<message>\S.*)$")


def capture(fn):
    """执行 fn，返回 (返回值, stdout, stderr)。"""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        value = fn()
    return value, out.getvalue(), err.getvalue()


def raised_gate_error(path: str | None, message: str):
    def body():
        raise common.GateError(path, message)

    return body


class FindingFormatTest(unittest.TestCase):
    def test_t36_emit_exit_codes_and_formats(self) -> None:
        """有 Finding 返回 1，无 Finding 返回 0；文件级不带 `:None` 段。"""
        line_finding = common.Finding("a.rs", 3, "DEP-1", "未登记依赖")
        file_finding = common.Finding("crates/fml-ast/Cargo.toml", None, "GATE-1", "环")
        code, out, err = capture(lambda: common.emit([line_finding, file_finding]))
        self.assertEqual(code, 1)
        self.assertEqual(
            out,
            "a.rs:3: DEP-1 未登记依赖\n"
            "crates/fml-ast/Cargo.toml: GATE-1 环\n",
        )
        self.assertEqual(err, "")
        empty_code, empty_out, _ = capture(lambda: common.emit([]))
        self.assertEqual(empty_code, 0)
        self.assertEqual(empty_out, "")

    def test_t36b_emit_writes_nothing_to_stderr(self) -> None:
        code, _, err = capture(lambda: common.emit([common.Finding("a.rs", 1, "DEP-1", "x")]))
        self.assertEqual((code, err), (1, ""))

    def test_finding_message_has_no_trailing_newline_dependency(self) -> None:
        """一 Finding 一行：message 中的换行不会被当成多行输出。"""
        _, out, _ = capture(lambda: common.emit([common.Finding("a.rs", 1, "DEP-1", "one")]))
        self.assertEqual(out.count("\n"), 1)


class GateErrorChannelTest(unittest.TestCase):
    def test_t31_gate_error_stdout_empty(self) -> None:
        code, out, _ = capture(lambda: common.main(raised_gate_error("a.rs", "未闭合字符串")))
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_t32_stderr_single_line(self) -> None:
        _, _, err = capture(lambda: common.main(raised_gate_error("a.rs", "未闭合字符串")))
        self.assertEqual(len(err.splitlines()), 1)

    def test_t33_gate_error_line_format(self) -> None:
        _, _, err = capture(lambda: common.main(raised_gate_error("tools/ci/x.rs", "块注释未闭合")))
        match = GATE_LINE_RE.match(err.rstrip("\n"))
        self.assertIsNotNone(match, err)
        assert match is not None
        self.assertEqual(match.group("path"), "tools/ci/x.rs")
        self.assertEqual(match.group("message"), "块注释未闭合")

    def test_t34_environment_path_is_dash(self) -> None:
        code, out, err = capture(lambda: common.main(raised_gate_error(None, "未知参数 --nope")))
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("-: GATE-1 "), err)
        self.assertEqual(len(err.splitlines()), 1)

    def test_t34b_gate_error_rule_is_gate1(self) -> None:
        error = common.GateError("a.rs", "x")
        self.assertEqual(error.rule, "GATE-1")
        self.assertEqual(error.path, "a.rs")
        self.assertEqual(error.message, "x")

    def test_main_returns_emit_code_when_no_gate_error(self) -> None:
        code, out, err = capture(
            lambda: common.main(lambda: [common.Finding("a.rs", 2, "DEP-1", "x")])
        )
        self.assertEqual((code, out, err), (1, "a.rs:2: DEP-1 x\n", ""))
        clean, clean_out, _ = capture(lambda: common.main(lambda: []))
        self.assertEqual((clean, clean_out), (0, ""))

    def test_t32b_duck_typed_gate_error_is_recognised(self) -> None:
        """同一脚本被两处以不同模块名导入时 GateError 身份不同，仍须按 GATE-1 收敛。"""

        class GateError(Exception):  # 模拟另一份 common 模块里的同名异常
            def __init__(self, path, message):
                super().__init__(message)
                self.path = path
                self.message = message

            @property
            def rule(self):
                return "GATE-1"

        def body():
            raise GateError("a.rs", "另一份 common")

        code, out, err = capture(lambda: common.main(body))
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("a.rs: GATE-1 "), err)


class RunTest(unittest.TestCase):
    def test_t35_no_partial_findings(self) -> None:
        """脚本先 emit 一条 Finding 再抛 GateError：stdout 必须为空。"""
        script_body = (
            "from common import Finding, GateError, emit\n"
            "\n"
            "\n"
            "def main(argv):\n"
            "    emit([Finding('a.rs', 1, 'GATE-1', '先产出的半份')])\n"
            "    raise GateError('b.rs', '未闭合块注释')\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script_under_test.py"
            script.write_text(script_body, encoding="utf-8")
            code, out, err = common.run([str(script), "--root", tmp])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, "b.rs: GATE-1 未闭合块注释\n")

    def test_run_without_script_is_environment_error(self) -> None:
        code, out, err = common.run([])
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("-: GATE-1 "), err)

    def test_run_missing_script_is_environment_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = common.run([str(Path(tmp) / "nope.py")])
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("-: GATE-1 "), err)

    def test_run_rejects_non_callable_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "script_without_main.py"
            script.write_text("VALUE = 1\n", encoding="utf-8")
            code, out, err = common.run([str(script)])
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("-: GATE-1 "), err)


class RunMatchesMainTest(unittest.TestCase):
    def test_t37_run_matches_main(self) -> None:
        """run(argv) 与直接调用脚本 main 对同一输入产出相同的码与输出。"""
        script_body = (
            "from common import Finding, main as gate_main\n"
            "\n"
            "\n"
            "def body(argv):\n"
            "    return [Finding('a.rs', 2, 'GATE-1', '同一条')]\n"
            "\n"
            "\n"
            "def main(argv):\n"
            "    return gate_main(lambda: body(argv))\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "consistent_script.py"
            script.write_text(script_body, encoding="utf-8")
            code, out, err = common.run([str(script), "--root", tmp])
            main_code, main_out, main_err = capture(
                lambda: common.main(lambda: [common.Finding("a.rs", 2, "GATE-1", "同一条")])
            )
        self.assertEqual(code, 1)
        self.assertEqual(out, "a.rs:2: GATE-1 同一条\n")
        self.assertEqual(err, "")
        self.assertEqual((main_code, main_out, main_err), (code, out, err))

    def test_t38_clean_run_exits_zero(self) -> None:
        """无 Finding 时退出 0，stdout 与 stderr 均为空。"""
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "clean_script.py"
            script.write_text(
                "from common import main as gate_main\n"
                "\n"
                "\n"
                "def main(argv):\n"
                "    return gate_main(lambda: [])\n",
                encoding="utf-8",
            )
            code, out, err = common.run([str(script)])
            main_code, main_out, main_err = capture(lambda: common.main(lambda: []))
        self.assertEqual((code, out, err), (0, "", ""))
        self.assertEqual((main_code, main_out, main_err), (0, "", ""))


class PublicSurfaceTest(unittest.TestCase):
    def test_t41_public_surface(self) -> None:
        """Finding/Token/GateError/emit/run/main 只在 common 定义，且形态按卡:12。"""
        for name in ("Finding", "Token", "GateError", "emit", "run", "main"):
            self.assertTrue(hasattr(common, name), name)
        token = common.Token("x", 0, 1, "code")
        self.assertEqual(
            (token.text, token.offset, token.line, token.kind), ("x", 0, 1, "code")
        )
        finding = common.Finding("a.rs", None, "GATE-1", "m")
        self.assertIsNone(finding.line)
        with self.assertRaises(Exception):
            finding.rule = "DEP-1"  # frozen dataclass


if __name__ == "__main__":
    unittest.main()
