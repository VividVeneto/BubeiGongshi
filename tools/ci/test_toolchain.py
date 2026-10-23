"""CORE-41 toolchain.py 验收测试（九键、只读、缺键/缺文件退出 2、不回退默认）。"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TOOLCHAIN = HERE / "toolchain.py"
PYTHON = sys.executable

KEYS = [
    "RUST_VERSION",
    "FLUTTER_VERSION",
    "PYTHON_VERSION",
    "NODE_VERSION",
    "FUZZ_NIGHTLY",
    "CARGO_FUZZ",
    "CARGO_DENY",
    "CARGO_AUDIT",
    "CARGO_LLVM_COV",
]
VERSIONS = [
    ("PYTHON_VERSION", "python"),
    ("NODE_VERSION", "node"),
    ("FUZZ_NIGHTLY", "fuzz_nightly"),
    ("CARGO_FUZZ", "cargo_fuzz"),
    ("CARGO_DENY", "cargo_deny"),
    ("CARGO_AUDIT", "cargo_audit"),
    ("CARGO_LLVM_COV", "cargo_llvm_cov"),
]


def read_lock_values(root: Path) -> dict:
    """独立解析锁文件，作为对照（不复用被测实现）。"""
    rust = (root / "rust-toolchain.toml").read_text(encoding="utf-8")
    channel = re.search(r'^\s*channel\s*=\s*"([^"]+)"\s*$', rust, re.MULTILINE)
    flutter = ""
    for line in (root / "app/.flutter-version").read_text(encoding="utf-8").splitlines():
        if line.strip():
            flutter = line.strip()
            break
    values = {"RUST_VERSION": channel.group(1), "FLUTTER_VERSION": flutter}
    for line in (root / "tools/toolchain.versions").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if "=" not in stripped or stripped.startswith("#"):
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


class ToolchainCase(unittest.TestCase):
    """在被测脚本的临时根上运行 toolchain.py。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="toolchain-"))
        self.addCleanup(shutil.rmtree, self.root, True)

    def copy_locks(self):
        """把三份锁文件复制到临时根。"""
        (self.root / "app").mkdir(parents=True, exist_ok=True)
        (self.root / "tools").mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / "rust-toolchain.toml", self.root / "rust-toolchain.toml")
        shutil.copy2(REPO / "app/.flutter-version", self.root / "app/.flutter-version")
        shutil.copy2(REPO / "tools/toolchain.versions", self.root / "tools/toolchain.versions")

    def run_toolchain(self, *args, root=None):
        """运行 toolchain.py。"""
        command = [PYTHON, str(TOOLCHAIN), "--root", str(root if root is not None else self.root)]
        command.extend(args)
        return subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )

    def test_env_format_nine_keys_in_order(self):
        """env 格式按固定顺序输出九键，取值来自锁文件。"""
        proc = self.run_toolchain("--format", "env", root=REPO)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [line for line in proc.stdout.splitlines() if line]
        self.assertEqual([line.split("=", 1)[0] for line in lines], KEYS)
        expected = read_lock_values(REPO)
        for line in lines:
            key, value = line.split("=", 1)
            if key in expected:
                self.assertEqual(value, expected[key], key)
        self.assertEqual(dict(line.split("=", 1) for line in lines)["RUST_VERSION"], "stable")
        self.assertEqual(lines[0], "RUST_VERSION=stable")
        self.assertEqual(lines[1], "FLUTTER_VERSION=" + expected["FLUTTER_VERSION"])

    def test_json_format_matches_env(self):
        """json 格式与 env 格式取值一致、键序一致。"""
        env = self.run_toolchain("--format", "env", root=REPO)
        self.assertEqual(env.returncode, 0, env.stderr)
        proc = self.run_toolchain("--format", "json", root=REPO)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(list(data), KEYS)
        self.assertEqual(
            data, {line.split("=", 1)[0]: line.split("=", 1)[1] for line in env.stdout.splitlines()}
        )

    def test_reads_locked_values_not_defaults(self):
        """取值跟随锁文件内容（换值即换输出），不回退猜默认版本。"""
        self.copy_locks()
        (self.root / "rust-toolchain.toml").write_text('channel = "beta"\n', encoding="utf-8")
        (self.root / "app/.flutter-version").write_text("9.9.9\n", encoding="utf-8")
        proc = self.run_toolchain("--format", "env")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        values = dict(line.split("=", 1) for line in proc.stdout.splitlines())
        self.assertEqual(values["RUST_VERSION"], "beta")
        self.assertEqual(values["FLUTTER_VERSION"], "9.9.9")

    def test_read_only_no_write(self):
        """只读：运行前后锁文件字节不变，也不产生新文件。"""
        self.copy_locks()
        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(self.run_toolchain().returncode, 0)
        self.assertEqual(self.run_toolchain("--format", "json").returncode, 0)
        after = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_missing_required_key_exits_two(self):
        """缺任一必需键退出 2，不回退默认值。"""
        self.copy_locks()
        original = (self.root / "tools/toolchain.versions").read_text(encoding="utf-8")
        for _, source_key in VERSIONS:
            with self.subTest(key=source_key):
                kept = [
                    line for line in original.splitlines()
                    if not line.startswith(source_key + "=")
                ]
                (self.root / "tools/toolchain.versions").write_text(
                    "\n".join(kept) + "\n", encoding="utf-8"
                )
                proc = self.run_toolchain()
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn(source_key, proc.stderr)
                self.assertEqual(proc.stdout, "")

    def test_missing_files_and_channel_exit_two(self):
        """缺锁文件、缺 channel、flutter 版本为空都退出 2。"""
        self.copy_locks()
        (self.root / "rust-toolchain.toml").unlink()
        proc = self.run_toolchain()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("rust-toolchain.toml", proc.stderr)

        self.copy_locks()
        (self.root / "rust-toolchain.toml").write_text("[toolchain]\n", encoding="utf-8")
        proc = self.run_toolchain()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("channel", proc.stderr)

        self.copy_locks()
        (self.root / "app/.flutter-version").write_text("", encoding="utf-8")
        proc = self.run_toolchain()
        self.assertEqual(proc.returncode, 2)
        self.assertIn(".flutter-version", proc.stderr)

        self.copy_locks()
        (self.root / "tools/toolchain.versions").unlink()
        self.assertEqual(self.run_toolchain().returncode, 2)

    def test_root_and_format_validation(self):
        """--root 非目录、--format 非法都退出 2。"""
        self.copy_locks()
        self.assertEqual(self.run_toolchain(root=self.root / "nope").returncode, 2)
        self.assertEqual(self.run_toolchain("--format", "yaml").returncode, 2)

    def test_repository_versions_file_has_new_keys(self):
        """真实仓库锁版文件已登记 cargo_audit / cargo_llvm_cov 两键（本卡新增）。"""
        raw = (REPO / "tools/toolchain.versions").read_text(encoding="utf-8")
        self.assertIn("cargo_audit=", raw)
        self.assertIn("cargo_llvm_cov=", raw)
        self.assertIn("queried_date=2026-10-22", raw)


if __name__ == "__main__":
    unittest.main()
