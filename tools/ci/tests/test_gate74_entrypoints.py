"""CORE-74 公共入口契约测试（D5/D6 与卡:34 的入口接入）。

三个门禁脚本只允许通过 CORE-69 的 `common`/`source_scan` 收敛退出码：
依赖缺失时必须给出单行 GATE-1 并退出 2，不能以裸 traceback 退出 1（否则 CORE-41
会把它记成 Finding 失败且格式不合规）。`--root` 必须对三个脚本一致可用。
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CI_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = ("check_unsafe.py", "check_abi.py", "check_errors.py")


class EntrypointContractTest(unittest.TestCase):
    """三脚本的入口与依赖边界。"""

    def run_script(self, script: Path, arguments: list, cwd: Path) -> subprocess.CompletedProcess:
        """在 cwd 下以真实解释器运行脚本，只清除继承的 PYTHONPATH。"""
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, str(script), *arguments],
            cwd=str(cwd),
            env=environment,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def test_scripts_without_core69_report_gate_error(self) -> None:
        """孤立目录里没有 CORE-69 公共层 → 单行 GATE-1、退出 2、无 traceback。"""
        for name in SCRIPTS:
            with self.subTest(script=name), tempfile.TemporaryDirectory() as tmp:
                isolated = Path(tmp) / name
                isolated.write_bytes((CI_DIR / name).read_bytes())
                result = self.run_script(isolated, ["--root", tmp], Path(tmp))
                self.assertEqual(2, result.returncode, result.stderr)
                self.assertEqual("", result.stdout)
                self.assertIn("GATE-1", result.stderr)
                self.assertIn("CORE-69", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_unknown_option_reports_single_gate_line(self) -> None:
        """未知参数 → 单行 GATE-1 与退出 2，不得逃逸为 traceback（诊断边界）。"""
        with tempfile.TemporaryDirectory() as tmp:
            for name in SCRIPTS:
                with self.subTest(script=name):
                    result = self.run_script(
                        CI_DIR / name, ["--root", tmp, "--not-an-option"], Path(tmp)
                    )
                    self.assertEqual(2, result.returncode, result.stderr)
                    self.assertEqual("", result.stdout)
                    self.assertIn("GATE-1", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
