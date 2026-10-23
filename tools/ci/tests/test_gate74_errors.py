"""CORE-74 ERR-1/ERR-2/ERR-3 验收测试（S0_CORE-74:14）。

本地证据：python -m unittest discover -s tools/ci/tests -p "test_gate74_*.py"
夹具 errors/base 只含 registry、arb 与 shared-writes 三个输入；生成物先由真实的
tools/ci/gen_errors.py 写出，再让 check_errors.py 判定，避免手写生成物掩盖漂移。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CI_DIR = Path(__file__).resolve().parents[1]
SCRIPT = CI_DIR / "check_errors.py"
GENERATOR = CI_DIR / "gen_errors.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gate74" / "errors" / "base"
REGISTRY = "contracts/errors/registry.yaml"
DUPLICATE = """  - code: FFI_BAD_ARG
    namespace: FFI
    owner: CORE-03
    severity: error
    message_key: err.ffi.dup
    retryable: false
    since: 1
    surface: client
"""


def run_script(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


class ErrorsGateTest(unittest.TestCase):
    """ERR-1 转发、ERR-2 扫描面与 ERR-3 注册表重复。"""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "root"
        shutil.copytree(FIXTURES, self.root)
        generated = subprocess.run(
            [sys.executable, str(GENERATOR), "--root", str(self.root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_generated_repository_has_no_findings(self) -> None:
        completed = run_script(self.root)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stdout.strip(), "")

    def test_unregistered_code_reported(self) -> None:
        self.write("crates/fml-ffi/src/lib.rs", 'pub const KEY: &str = "FFI_UNKNOWN_CODE";\n')
        completed = run_script(self.root)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.strip(),
            "crates/fml-ffi/src/lib.rs:1: ERR-2 错误码 FFI_UNKNOWN_CODE 未在 registry.yaml 登记",
        )

    def test_registered_module_and_lowercase_keys_ignored(self) -> None:
        self.write(
            "app/lib/feature/codes.dart",
            'const registered = "AST_JSON_INVALID";\n'
            'const macro = "FML_ABI_MAJOR";\n'
            'const reserved = "FML_THEME_MISSING";\n'
            'const lower = "ffi_bad_arg";\n'
            'const comment = "not a code at all";\n',
        )
        completed = run_script(self.root)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_generated_dart_and_tests_are_excluded(self) -> None:
        """测试目录、生成物与 contracts/SADD 不在 ERR-2 扫描面内（条目 ⑬）。"""
        self.write("app/lib/feature/theme.g.dart", 'const sample = "FFI_NOT_IN_REGISTRY";\n')
        self.write("crates/fml-ffi/tests/it.rs", 'pub const OTHER: &str = "FFI_ALSO_UNKNOWN";\n')
        self.write("contracts/errors/sample.rs", 'pub const DOC: &str = "FFI_DOC_ONLY";\n')
        self.write("SADD/sample.dart", 'const doc = "FFI_SADD_ONLY";\n')
        completed = run_script(self.root)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_ownership_drift_reported_as_err_1(self) -> None:
        """owner 与 ownership.yaml 不一致按 ERR-1 报出，不报 ERR-3（条目 ⑮）。"""
        ownership = self.root / "contracts/errors/ownership.yaml"
        ownership.write_text(
            ownership.read_text(encoding="utf-8").replace("CORE-03", "CORE-99"),
            encoding="utf-8",
        )
        completed = run_script(self.root)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.strip(),
            "contracts/errors/ownership.yaml: ERR-1 生成物与 registry.yaml 不一致",
        )

    def test_unparsable_arb_reports_gate(self) -> None:
        """arb 不可解析由生成器退 2，门禁按 GATE-1 转发而不是 Finding（条目 ⑨⑯）。"""
        self.write("app/lib/l10n/errors_zh.arb", "{ not json\n")
        completed = run_script(self.root)
        self.assertEqual(completed.returncode, 2, completed.stdout)
        self.assertEqual(completed.stdout.strip(), "")
        self.assertIn("GATE-1", completed.stderr)

    def test_drift_reported_as_err_1(self) -> None:
        codes = self.root / "crates/fml-error/src/codes.rs"
        codes.write_text(codes.read_text(encoding="utf-8") + "// tampered\n", encoding="utf-8")
        completed = run_script(self.root)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.strip(),
            "crates/fml-error/src/codes.rs: ERR-1 生成物与 registry.yaml 不一致",
        )

    def test_missing_registry_reports_gate(self) -> None:
        (self.root / REGISTRY).unlink()
        completed = run_script(self.root)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("实现注册表未启用", completed.stderr)

    def test_duplicate_code_reported_as_err_3(self) -> None:
        registry = self.root / REGISTRY
        registry.write_text(
            registry.read_text(encoding="utf-8").replace("  - code: FFI_BAD_ARG", DUPLICATE + "  - code: FFI_BAD_ARG", 1),
            encoding="utf-8",
        )
        completed = run_script(self.root)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("ERR-3 错误码 FFI_BAD_ARG 在注册表中重复登记", completed.stdout)
        self.assertNotIn("ERR-1", completed.stdout)

    def test_duplicate_message_key_reported_as_err_3(self) -> None:
        registry = self.root / REGISTRY
        registry.write_text(
            registry.read_text(encoding="utf-8").replace(
                "message_key: err.ffi.bad_arg", "message_key: err.ast.json_invalid"
            ),
            encoding="utf-8",
        )
        completed = run_script(self.root)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("ERR-3 message_key err.ast.json_invalid 被多个错误码共用", completed.stdout)

    def test_unparsable_registry_reports_gate(self) -> None:
        self.write(REGISTRY, "entries: [\n")
        completed = run_script(self.root)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("注册表不可解析", completed.stderr)

    def test_registry_outside_contracts_reports_gate(self) -> None:
        self.write(
            "elsewhere/registry.yaml",
            (self.root / REGISTRY).read_text(encoding="utf-8"),
        )
        completed = run_script(self.root, "--registry", "elsewhere/registry.yaml")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("必须是 <root>/contracts/errors/registry.yaml", completed.stderr)


if __name__ == "__main__":
    unittest.main()
