"""CORE-41 core_sources.py 验收测试（tracked 集合、排除规则、排序、空集合 pending）。"""
import json
import os
import subprocess
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TOOL = HERE / "core_sources.py"
PYTHON = sys.executable

DOMAIN_CRATES = [
    "fml-ast",
    "fml-latex",
    "fml-notation",
    "fml-units",
    "fml-type",
    "fml-eval",
    "fml-derive",
    "fml-typeset",
    "fml-export",
    "fml-srs",
    "fml-grade",
    "fml-study",
    "fml-crypto",
]


class CoreSourcesCase(unittest.TestCase):
    """在临时 git 仓库上运行 core_sources.py。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="coresrc-")).resolve()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.git("init", "-q")

    def git(self, *args):
        """在临时仓库运行 git。"""
        proc = subprocess.run(
            ["git", "-C", str(self.root)] + list(args),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout

    def touch(self, path: str, track: bool = True, text: str = "// x\n"):
        """写入文件并按需加入索引。"""
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        if track:
            self.git("add", "--", path)
        return target

    def run_tool(self, *args, root=None, env=None):
        """运行 core_sources.py。"""
        target = Path(root if root is not None else self.root)
        command = [PYTHON, str(TOOL), "--root", str(target)]
        command.extend(args)
        # cwd 只在目录真实存在时设置，否则 --root 缺失用例无法启动子进程。
        workdir = str(target) if target.is_dir() else None
        return subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=workdir, env=env,
        )

    def out_path(self) -> Path:
        """默认产物路径。"""
        return self.root / "build/coverage/core-sources.json"

    def read_out(self) -> dict:
        """读取产物。"""
        return json.loads(self.out_path().read_text(encoding="utf-8"))

    def test_collects_tracked_rs_sorted_and_deduped(self):
        """只收 13 个领域 crate 的 src 下已跟踪 .rs，按 UTF-8 字节序去重排序。"""
        self.touch("crates/fml-ast/src/lib.rs")
        self.touch("crates/fml-ast/src/node.rs")
        self.touch("crates/fml-type/src/lib.rs")
        self.touch("crates/fml-crypto/src/x.rs")
        self.touch("crates/fml-srs/src/deck.rs")
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self.read_out(),
            {
                "version": 1,
                "paths": [
                    "crates/fml-ast/src/lib.rs",
                    "crates/fml-ast/src/node.rs",
                    "crates/fml-crypto/src/x.rs",
                    "crates/fml-srs/src/deck.rs",
                    "crates/fml-type/src/lib.rs",
                ],
            },
        )
        self.assertIn("收录 5 个文件", proc.stderr)

    def test_all_thirteen_crates_are_covered(self):
        """13 个领域 crate 每个都参与收集。"""
        for crate in DOMAIN_CRATES:
            self.touch(f"crates/{crate}/src/lib.rs")
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        paths = self.read_out()["paths"]
        self.assertEqual(len(paths), 13)
        self.assertEqual(
            paths, [f"crates/{crate}/src/lib.rs" for crate in sorted(DOMAIN_CRATES)]
        )

    def test_sync_only_merge_rs(self):
        """fml-sync 只收录 src/merge.rs，其他文件不收。"""
        self.touch("crates/fml-sync/src/merge.rs")
        self.touch("crates/fml-sync/src/lib.rs")
        self.touch("crates/fml-sync/src/store.rs")
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.read_out()["paths"], ["crates/fml-sync/src/merge.rs"])

    def test_non_domain_crates_excluded(self):
        """fml-store / fml-error 等非领域 crate 不进集合。"""
        self.touch("crates/fml-store/src/lib.rs")
        self.touch("crates/fml-error/src/lib.rs")
        self.touch("crates/fml-ffi/src/lib.rs")
        self.touch("crates/fml-ast/src/lib.rs")
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.read_out()["paths"], ["crates/fml-ast/src/lib.rs"])

    def test_exclusions_and_reasons(self):
        """tests/fixtures 分量、*.g.rs、非 .rs 文件被排除并把原因写到 stderr。"""
        self.touch("crates/fml-ast/src/lib.rs")
        self.touch("crates/fml-ast/src/generated.g.rs")
        self.touch("crates/fml-ast/src/tests/mod.rs")
        self.touch("crates/fml-ast/src/fixtures/data.rs")
        self.touch("crates/fml-ast/src/note.md")
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.read_out()["paths"], ["crates/fml-ast/src/lib.rs"])
        self.assertIn("crates/fml-ast/src/generated.g.rs", proc.stderr)
        self.assertIn("*.g.rs", proc.stderr)
        self.assertIn("crates/fml-ast/src/tests/mod.rs", proc.stderr)
        self.assertIn("路径分量 tests/fixtures", proc.stderr)
        self.assertIn("crates/fml-ast/src/note.md", proc.stderr)
        self.assertIn("非 .rs 文件", proc.stderr)
        self.assertIn("排除 4 个", proc.stderr)

    def test_untracked_files_are_ignored(self):
        """未跟踪文件不进集合（只从 git 索引取）。"""
        self.touch("crates/fml-ast/src/lib.rs")
        self.touch("crates/fml-ast/src/new.rs", track=False)
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.read_out()["paths"], ["crates/fml-ast/src/lib.rs"])

    def test_empty_set_registers_pending(self):
        """集合为空时写空 paths、退出 0 并登记 core-sources pending-target。"""
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.read_out(), {"version": 1, "paths": []})
        pending = json.loads((self.root / "build/ci/pending.json").read_text(encoding="utf-8"))
        self.assertEqual(pending["version"], 1)
        self.assertEqual(
            pending["items"],
            [
                {
                    "card": "CORE-41",
                    "target": "core-sources",
                    "reason": "领域源码集合为空：13 个领域 crate 与 crates/fml-sync/src/merge.rs 均无已跟踪 .rs 文件",
                }
            ],
        )
        self.assertIn("pending-target", proc.stderr)

    def test_empty_set_keeps_existing_pending_entries(self):
        """为空时登记 pending 不覆盖其他卡已有条目，重复键保留先写入的原因。"""
        pending_path = self.root / "build/ci/pending.json"
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "items": [
                        {"card": "CORE-69", "target": "check-deps", "reason": "脚本未实现"},
                        {"card": "CORE-41", "target": "core-sources", "reason": "旧原因"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        items = json.loads(pending_path.read_text(encoding="utf-8"))["items"]
        self.assertEqual(
            [(item["card"], item["target"]) for item in items],
            [("CORE-41", "core-sources"), ("CORE-69", "check-deps")],
        )
        self.assertEqual(items[0]["reason"], "旧原因")

    def test_explicit_pending_channel_does_not_touch_default(self):
        """内部通道可定向登记；独立默认路径兼容由empty_set用例覆盖。"""
        default = self.root / "build/ci/pending.json"
        default.parent.mkdir(parents=True)
        default.write_text("old unrelated output", encoding="utf-8")
        custom = self.root / "build/custom ci/pending.json"
        env = dict(os.environ, CORE_CI_PENDING=str(custom))
        proc = self.run_tool(env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(default.read_text(encoding="utf-8"), "old unrelated output")
        self.assertEqual(json.loads(custom.read_text(encoding="utf-8"))["items"][0]["target"], "core-sources")

    def test_invalid_pending_fails_closed_without_overwriting(self):
        """独立运行亦不静默丢弃损坏登记。"""
        pending = self.root / "build/ci/pending.json"
        pending.parent.mkdir(parents=True)
        for bad in (b"{bad", b"[]", b'{"items":[null]}', b'{"items":[{"card":1}]}', b"\xff"):
            with self.subTest(bad=bad):
                pending.write_bytes(bad)
                proc = self.run_tool()
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("pending.json", proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)
                self.assertEqual(pending.read_bytes(), bad)

    def test_non_empty_set_writes_no_pending(self):
        """非空集合不写 pending.json。"""
        self.touch("crates/fml-ast/src/lib.rs")
        self.assertEqual(self.run_tool().returncode, 0)
        self.assertFalse((self.root / "build/ci/pending.json").exists())

    def test_non_git_directory_exits_two(self):
        """非 git 目录退出 2，不写产物。"""
        plain = Path(tempfile.mkdtemp(prefix="plain-")).resolve()
        self.addCleanup(shutil.rmtree, plain, True)
        proc = self.run_tool(root=plain)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("git", proc.stderr)
        self.assertFalse((plain / "build/coverage/core-sources.json").exists())

    def test_git_unavailable_exits_two(self):
        """git 不可用退出 2。"""
        self.touch("crates/fml-ast/src/lib.rs")
        env = dict(os.environ)
        env["PATH"] = ""
        proc = self.run_tool(env=env)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("git 不可用", proc.stderr)

    def test_root_not_directory_exits_two(self):
        """--root 不是目录退出 2。"""
        proc = self.run_tool(root=self.root / "missing")
        self.assertEqual(proc.returncode, 2)

    def test_out_relative_to_root(self):
        """--out 相对路径按 --root 解析。"""
        self.touch("crates/fml-ast/src/lib.rs")
        proc = self.run_tool("--out", "build/other.json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads((self.root / "build/other.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["paths"], ["crates/fml-ast/src/lib.rs"])
        self.assertFalse(self.out_path().exists())

    def test_real_repository_subset_of_tracked(self):
        """真实仓库产物是已跟踪 .rs 的子集且形状合法（不反推 LCOV）。"""
        out = Path(tempfile.mkdtemp(prefix="coresrc-out-")).resolve()
        self.addCleanup(shutil.rmtree, out, True)
        proc = self.run_tool("--out", str(out / "core-sources.json"), root=REPO)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads((out / "core-sources.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], 1)
        tracked = subprocess.run(
            ["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        ).stdout.splitlines()
        tracked_set = set(tracked)
        for path in payload["paths"]:
            self.assertIn(path, tracked_set)
            self.assertTrue(path.endswith(".rs"))
            self.assertTrue(path.startswith("crates/"))
        self.assertEqual(payload["paths"], sorted(payload["paths"]))


if __name__ == "__main__":
    unittest.main()
