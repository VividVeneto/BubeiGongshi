"""CORE-74 UNSAFE-1/UNSAFE-2 验收测试（S0_CORE-74:14）。

本地证据：python -m unittest discover -s tools/ci/tests -p "test_gate74_*.py"
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CI_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CI_DIR))

import check_unsafe  # noqa: E402  本卡脚本自身，用于常量镜像断言

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gate74" / "unsafe"
REPO_ROOT = CI_DIR.parents[1]
SCRIPT = CI_DIR / "check_unsafe.py"


def run_gate(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


class UnsafeGateTest(unittest.TestCase):
    """UNSAFE-1 白名单、UNSAFE-2 SAFETY 窗口与扫描面。"""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "root"

    def run_case(self, case: str) -> subprocess.CompletedProcess[str]:
        shutil.copytree(FIXTURES / case, self.root)
        return run_gate(self.root)

    def test_whitelist_mirrors_core01(self) -> None:
        """白名单常量与 CORE-01:133 的三名完全一致（按内容定位，不绑固定行号）。"""
        card = REPO_ROOT / "SADD" / "S0" / "S0_CORE-01_基座.md"
        lines = [
            line
            for line in card.read_text(encoding="utf-8").splitlines()
            if "forbid(unsafe_code)" in line and "SAFETY:" in line
        ]
        self.assertEqual(len(lines), 1, f"CORE-01 的 unsafe 白名单行应唯一：{lines}")
        self.assertEqual(
            set(re.findall(r"`(fml-[a-z-]+)`", lines[0])), set(check_unsafe.UNSAFE_WHITELIST)
        )
        self.assertEqual(len(check_unsafe.UNSAFE_WHITELIST), 3)

    def test_safety_seam_matches_core01_real_test(self) -> None:
        """SAFETY 判据与 CORE-01 真实测试（repo_config.rs）的窗口/内联接缝对齐。

        窗口行长与同行行尾由 CORE-01 真实测试锁定；内容下界（8 个非空白字符且含字母）
        由本卡卡文规定，故本门禁严于 CORE-01 的「非空」——差异在此显式断言，避免悄悄漂移。
        """
        seam = REPO_ROOT / "crates" / "fml-error" / "tests" / "repo_config.rs"
        text = seam.read_text(encoding="utf-8")
        window = re.findall(r"const SAFETY_WINDOW: usize = (\d+);", text)
        self.assertEqual(window, [str(check_unsafe.SAFETY_LOOKBACK_LINES)])
        self.assertIn("safety_text(trailing).is_some()", text)
        self.assertIn("lines[at.saturating_sub(SAFETY_WINDOW)..at]", text)
        self.assertIn("(!note.is_empty()).then_some(note)", text)
        card = REPO_ROOT / "SADD" / "S0" / "S0_CORE-74_基座.md"
        requirement = [
            line
            for line in card.read_text(encoding="utf-8").splitlines()
            if "不足8个非空白字符" in line
        ]
        self.assertEqual(len(requirement), 1, requirement)
        self.assertIn("或不含字母", requirement[0])
        self.assertEqual(check_unsafe.SAFETY_MIN_CHARS, 8)

    def test_real_repository_scan_is_clean(self) -> None:
        """真实树回归：仓库自身扫描 0 Finding、退 0（CORE-69 词法层修复后的实测面）。

        s0r4 时该命令在 crates/fml-error/tests/doc_lints.rs 退 2（字符串未闭合）；本用例
        即锁住那次上游修复：换行字符串与字面量相邻的 code run 不再让扫描中断。
        """
        completed = run_gate(REPO_ROOT)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stdout.strip(), "")

    def test_clean_whitelisted_crate_passes(self) -> None:
        completed = self.run_case("clean")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "")
        self.assertEqual(completed.stderr.strip(), "")

    def test_non_whitelisted_crate_reports_unsafe_1(self) -> None:
        completed = self.run_case("bad-crate")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.strip(), "crates/fml-ast/src/lib.rs:6: UNSAFE-1 fml-ast 不在 unsafe 白名单"
        )

    def test_server_member_reports_unsafe_1(self) -> None:
        completed = self.run_case("server-member")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.strip(), "server/src/main.rs:6: UNSAFE-1 server 不在 unsafe 白名单"
        )

    def test_missing_safety_reports_unsafe_2(self) -> None:
        completed = self.run_case("missing-safety")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.strip(),
            "crates/fml-ffi/src/lib.rs:5: UNSAFE-2 缺少 SAFETY: 注释",
        )

    def test_short_letterless_and_out_of_window_reasons(self) -> None:
        completed = self.run_case("weak-safety")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "crates/fml-ffi/src/lib.rs:6: UNSAFE-2 SAFETY 说明不足 8 个非空白字符",
                "crates/fml-ffi/src/lib.rs:12: UNSAFE-2 SAFETY 说明不含字母",
                "crates/fml-ffi/src/lib.rs:20: UNSAFE-2 SAFETY: 注释须位于 unsafe 起始行前 3 行内或同行行尾",
            ],
        )

    def test_safety_on_same_line_passes(self) -> None:
        completed = self.run_case("line-end")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_string_literal_and_identifier_are_not_unsafe(self) -> None:
        completed = self.run_case("string-literal")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_tests_directory_is_scanned(self) -> None:
        completed = self.run_case("tests-inside")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.strip(),
            "crates/fml-ffi/tests/it.rs:7: UNSAFE-2 缺少 SAFETY: 注释",
        )

    def test_empty_and_punctuation_safety_report_unsafe_2(self) -> None:
        """空说明与纯标点说明都按不足 8 个非空白字符报 UNSAFE-2（条目 ③）。"""
        completed = self.run_case("empty-safety")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "crates/fml-ffi/src/lib.rs:2: UNSAFE-2 SAFETY 说明不足 8 个非空白字符",
                "crates/fml-ffi/src/lib.rs:7: UNSAFE-2 SAFETY 说明不足 8 个非空白字符",
            ],
        )

    def test_safety_three_lines_above_with_statements_between_passes(self) -> None:
        """SAFETY 与 unsafe 之间隔着普通语句、恰好 3 行窗口内仍算合规（条目 ④）。"""
        completed = self.run_case("window-three")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_missing_root_reports_gate(self) -> None:
        completed = run_gate(Path(tempfile.gettempdir()) / "core74-missing-root")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("GATE-1", completed.stderr)


if __name__ == "__main__":
    unittest.main()
