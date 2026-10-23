"""CORE-41 run_all.py 验收测试（退出码、pending 分流、进程树、HA-002 消费者、稳定性）。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUN_ALL = HERE / "run_all.py"
MANIFEST = HERE / "manifest.json"
FIXTURES = HERE / "tests" / "fixtures" / "runall"
PYTHON = sys.executable
# CORE-74 交接片段发布的四个自测文件（脚本未合入时按 pending-target 记录）
GATE74_SELFTESTS = (
    "tools/ci/tests/test_gate74_unsafe.py",
    "tools/ci/tests/test_gate74_abi.py",
    "tools/ci/tests/test_gate74_errors.py",
    "tools/ci/tests/test_gate74_entrypoints.py",
)


def process_alive(pid: int) -> bool:
    """判断 pid 是否仍存活（Windows 用 tasklist，POSIX 用 os.kill）。"""
    if os.name == "nt":
        completed = subprocess.run(
            ["tasklist", "/FI", "PID eq " + str(pid)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return str(pid) in (completed.stdout or "")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class RunAllCase(unittest.TestCase):
    """在临时库里运行 run_all.py；桩脚本复制到 tools/ci/tests/fixtures/runall。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="runall-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.stubs_rel = "tools/ci/tests/fixtures/runall"
        target = self.root / self.stubs_rel
        target.mkdir(parents=True)
        for item in FIXTURES.iterdir():
            if item.is_file():
                shutil.copy2(item, target / item.name)

    def stub(self, name: str) -> str:
        """返回桩脚本的仓库相对路径。"""
        return self.stubs_rel + "/" + name

    def step(self, step_id, argv, owner="CORE-41", **extra):
        """构造 manifest 步骤。"""
        item = {"id": step_id, "owner": owner, "argv": argv}
        item.update(extra)
        return item

    def write_manifest(self, steps, name="manifest.json"):
        """写临时 manifest。"""
        path = self.root / name
        path.write_text(
            json.dumps({"version": 1, "steps": steps}, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def run_all(self, *args, manifest="manifest.json", env=None):
        """运行 run_all.py 并返回 CompletedProcess。"""
        command = [PYTHON, str(RUN_ALL), "--root", str(self.root), "--manifest", manifest]
        command.extend(args)
        full_env = dict(os.environ)
        if env is not None:
            full_env.update(env)
        return subprocess.run(
            command,
            cwd=str(self.root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=full_env,
        )

    def last_line(self, proc) -> str:
        """终端最后一行的聚合计数。"""
        return proc.stdout.strip().splitlines()[-1]

    def read_json(self, rel):
        """读取产物 JSON。"""
        return json.loads((self.root / rel).read_text(encoding="utf-8"))

    def test_exit_codes_aggregate(self):
        """退出码 0/1/2 分别记 pass/fail/error；error 优先于 fail。"""
        self.write_manifest(
            [
                self.step("ok", ["python", self.stub("stub_ok.py")]),
                self.step("bad", ["python", self.stub("stub_fail.py")]),
                self.step("err", ["python", self.stub("stub_exit2.py")]),
            ]
        )
        proc = self.run_all()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(self.last_line(proc), "run_all: 3 steps, 1 error, 1 fail, 0 pending")
        doc = self.read_json("build/ci/run_all.json")
        self.assertEqual([item["id"] for item in doc["steps"]], ["ok", "bad", "err"])
        self.assertEqual([item["exit"] for item in doc["steps"]], [0, 1, 2])
        self.assertEqual(self.read_json("build/ci/pending.json")["items"], [])

        self.write_manifest(
            [
                self.step("ok", ["python", self.stub("stub_ok.py")]),
                self.step("bad", ["python", self.stub("stub_fail.py")]),
            ]
        )
        proc = self.run_all()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(self.last_line(proc), "run_all: 2 steps, 0 error, 1 fail, 0 pending")

    def test_unknown_exit_code_is_error_and_missing_interpreter(self):
        """未知退出码与解释器缺失都记 error，不是 fail。"""
        self.write_manifest([self.step("odd", ["python", self.stub("stub_exit3.py")])])
        proc = self.run_all()
        self.assertEqual(proc.returncode, 2)
        doc = self.read_json("build/ci/run_all.json")
        self.assertEqual(doc["steps"][0]["exit"], 3)
        self.assertIsNone(doc["steps"][0]["error_kind"])
        self.assertEqual(self.last_line(proc), "run_all: 1 steps, 1 error, 0 fail, 0 pending")

        self.write_manifest([self.step("nodeless", ["node", "--version"])])
        proc = self.run_all(env={"PATH": ""})
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        doc = self.read_json("build/ci/run_all.json")
        self.assertEqual(doc["steps"][0]["error_kind"], "unavailable")
        self.assertIsNone(doc["steps"][0]["exit"])

    def test_manifest_validation_rejects_six_classes(self):
        """manifest 闭式校验：六类非法都退出 2 且不执行、不写 run_all.json。"""
        good = {"version": 1, "steps": [self.step("ok", ["python", self.stub("stub_ok.py")])]}
        cases = {
            "version": dict(good, version=2),
            "duplicate": {
                "version": 1,
                "steps": [
                    self.step("dup", ["python", self.stub("stub_ok.py")]),
                    self.step("dup", ["python", self.stub("stub_ok.py")]),
                ],
            },
            "interpreter": {"version": 1, "steps": [self.step("sh", ["bash", "-c", "true"])]},
            "kind": {"version": 1, "steps": [self.step("k", ["python", self.stub("stub_ok.py")], kind="script")]},
            "owner": {"version": 1, "steps": [self.step("d", ["python", self.stub("stub_ok.py")], owner="CORE-99", kind="docs-tool")]},
            "card-owner": {"version": 1, "steps": [self.step("c", ["python", self.stub("stub_ok.py")], owner="SADD")]},
            "unknown-field": {"version": 1, "steps": [dict(self.step("u", ["python", self.stub("stub_ok.py")]), timeout=5)]},
        }
        for name, payload in cases.items():
            with self.subTest(name=name):
                (self.root / "manifest.json").write_text(
                    json.dumps(payload, ensure_ascii=False), encoding="utf-8"
                )
                proc = self.run_all()
                self.assertEqual(proc.returncode, 2, name + " " + proc.stdout + proc.stderr)
                self.assertIn("manifest 非法", proc.stderr)
                self.assertFalse((self.root / "build/ci/run_all.json").exists())

    def test_argv_is_literal_no_shell_expansion(self):
        """含 ; 与 * 的参数原样传给子进程；* 与目录参与存在性判定为 pending。"""
        self.write_manifest(
            [
                self.step("echo", ["python", self.stub("stub_echo.py"), "a;b", "*"]),
                self.step("glob", ["node", "--test", "*"]),
                self.step("dir", ["node", "--test", "tools"]),
            ]
        )
        proc = self.run_all()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('["a;b", "*"]', proc.stdout)
        doc = self.read_json("build/ci/run_all.json")
        self.assertEqual(doc["steps"][1]["exit"], None)
        self.assertEqual(doc["steps"][2]["exit"], None)
        items = self.read_json("build/ci/pending.json")["items"]
        self.assertEqual([item["target"] for item in items], ["dir", "glob"])
        self.assertEqual(items[0]["card"], "CORE-41")
        self.assertIn("*", items[1]["reason"])

    def test_pending_target_not_executed_and_release_rejects_pending(self):
        """目标缺失先分流为 pending-target、不执行；--release 拒 pending，开发态放行。"""
        missing = "tools/ci/does-not-exist.py"
        self.write_manifest([self.step("gone", ["python", missing])])
        proc = self.run_all()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.last_line(proc), "run_all: 1 steps, 0 error, 0 fail, 1 pending")
        self.assertIn("[pending] gone (CORE-41)", proc.stdout)
        doc = self.read_json("build/ci/run_all.json")
        self.assertIsNone(doc["steps"][0]["exit"])
        items = self.read_json("build/ci/pending.json")["items"]
        self.assertEqual(items, [{"card": "CORE-41", "target": "gone", "reason": missing}])

        proc = self.run_all("--release")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(self.last_line(proc), "run_all: 1 steps, 0 error, 0 fail, 1 pending")

    def test_failure_is_fail_not_skip(self):
        """目标存在但退出 1 记 fail，不得记 SKIP/pending。"""
        self.write_manifest([self.step("bad", ["python", self.stub("stub_fail.py")], owner="CORE-70")])
        proc = self.run_all()
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.last_line(proc), "run_all: 1 steps, 0 error, 1 fail, 0 pending")
        self.assertEqual(self.read_json("build/ci/pending.json")["items"], [])

    def test_timeout_terminates_whole_process_tree(self):
        """超时后整棵进程树被终止：孙进程也死，记 error/timeout。"""
        pid_file = self.root / "hang.pid"
        self.write_manifest([self.step("hang", ["python", self.stub("stub_hang.py"), "hang.pid"])])
        proc = self.run_all("--step-timeout", "1")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        doc = self.read_json("build/ci/run_all.json")
        record = doc["steps"][0]
        self.assertIsNone(record["exit"])
        self.assertEqual(record["error_kind"], "timeout")
        self.assertGreaterEqual(record["duration_ms"], 1000)
        self.assertTrue(pid_file.exists(), "孙进程 pid 文件未生成")
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and process_alive(pid):
            time.sleep(0.1)
        self.assertFalse(process_alive(pid), "超时后孙进程仍存活，进程树未整棵终止")

    def test_run_all_json_is_stable_and_tails_last_lines(self):
        """两次运行除 duration_ms 外字节相同；stdout_tail 保留原始末行。"""
        self.write_manifest(
            [
                self.step("ok", ["python", self.stub("stub_ok.py")]),
                self.step("echo", ["python", self.stub("stub_echo.py"), "x"]),
            ]
        )
        self.assertEqual(self.run_all().returncode, 0)
        first = self.read_json("build/ci/run_all.json")
        self.assertEqual(self.run_all().returncode, 0)
        second = self.read_json("build/ci/run_all.json")
        for item in first["steps"] + second["steps"]:
            self.assertIsInstance(item["duration_ms"], int)
            item["duration_ms"] = 0
        self.assertEqual(
            json.dumps(first, ensure_ascii=False, sort_keys=True),
            json.dumps(second, ensure_ascii=False, sort_keys=True),
        )
        self.assertEqual(first["steps"][0]["stdout_tail"], "stub_ok")
        self.assertEqual(first["steps"][0]["stderr_tail"], "")

    def test_finding_line_preserved_verbatim(self):
        """Finding 行按原文保留，不改格式、不吞 stderr。"""
        self.write_manifest([self.step("deps", ["python", self.stub("stub_finding.py")], owner="CORE-69")])
        proc = self.run_all()
        self.assertEqual(proc.returncode, 1)
        record = self.read_json("build/ci/run_all.json")["steps"][0]
        self.assertEqual(record["owner"], "CORE-69")
        self.assertEqual(record["stdout_tail"], "crates/a/src/x.rs:12: DEP-1 msg")
        self.assertEqual(proc.stdout.splitlines()[0], "crates/a/src/x.rs:12: DEP-1 msg")

    def test_release_args_only_appended_in_release(self):
        """release_args 只在 --release 时追加到 argv 末尾。"""
        self.write_manifest(
            [self.step("echo", ["python", self.stub("stub_echo.py")], release_args=["--release"])]
        )
        dev = self.run_all()
        self.assertEqual(dev.returncode, 0, dev.stdout + dev.stderr)
        self.assertIn("[]", dev.stdout)
        released = self.run_all("--release")
        self.assertEqual(released.returncode, 0, released.stdout + released.stderr)
        self.assertIn('["--release"]', released.stdout)

    def test_only_filters_and_rejects_unknown(self):
        """--only 仅本地筛步骤；未知步骤名退出 2。"""
        self.write_manifest(
            [
                self.step("a", ["python", self.stub("stub_ok.py")]),
                self.step("b", ["python", self.stub("stub_ok.py")]),
            ]
        )
        proc = self.run_all("--only", "b")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(self.last_line(proc), "run_all: 1 steps, 0 error, 0 fail, 0 pending")
        proc = self.run_all("--only", "zzz")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--only 未匹配", proc.stderr)

    def test_root_and_manifest_errors(self):
        """--root/--manifest/--step-timeout 非法输入退出 2。"""
        proc = subprocess.run(
            [PYTHON, str(RUN_ALL), "--root", str(self.root / "nope")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--root 不是目录", proc.stderr)
        (self.root / "afile").write_text("x", encoding="utf-8")
        proc = subprocess.run(
            [PYTHON, str(RUN_ALL), "--root", str(self.root / "afile")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(self.run_all(manifest="absent.json").returncode, 2)
        self.write_manifest([self.step("ok", ["python", self.stub("stub_ok.py")])])
        self.assertEqual(self.run_all("--step-timeout", "0").returncode, 2)

    def test_pending_json_merged_and_sorted(self):
        """步骤登记与 pending-target 条目按 (card,target) 去重排序后合并。"""
        seeded = json.dumps(
            {
                "version": 1,
                "items": [
                    {"card": "CORE-41", "target": "core-sources", "reason": "集合为空"},
                    {"card": "CORE-41", "target": "gone", "reason": "旧原因"},
                ],
            },
            ensure_ascii=False,
        )
        self.write_manifest(
            [
                self.step("seed", ["python", self.stub("stub_pending.py"), "build/ci/pending.json", seeded]),
                self.step("gone", ["python", "tools/ci/none.py"]),
            ]
        )
        proc = self.run_all()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.read_json("build/ci/pending.json")["items"]
        self.assertEqual([item["target"] for item in items], ["core-sources", "gone"])
        # 既有条目优先：同一 (card,target) 不重复登记，保留先写入的原因。
        self.assertEqual(items[1]["reason"], "旧原因")
        self.assertEqual(len(items), 2)

    def test_pending_json_corruption_is_tool_error(self):
        """步骤写坏的 pending.json 按工具错误退出 2，不静默覆盖。"""
        self.write_manifest(
            [
                self.step("seed", ["python", self.stub("stub_pending.py"), "build/ci/pending.json", "{not json"]),
            ]
        )
        proc = self.run_all()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("pending.json", proc.stderr)
        self.assertEqual(
            (self.root / "build/ci/pending.json").read_text(encoding="utf-8"), "{not json"
        )


class UnittestDiscoveryCase(unittest.TestCase):
    """python -m unittest 聚合入口：识别真实发现目录，0 个测试时不许当通过。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="runall-unittest-"))
        self.addCleanup(shutil.rmtree, self.root, True)

    step = RunAllCase.step
    write_manifest = RunAllCase.write_manifest
    run_all = RunAllCase.run_all
    last_line = RunAllCase.last_line
    read_json = RunAllCase.read_json

    def write(self, rel: str, content: str):
        """在临时库写文件。"""
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def unittest_step(self, *extra):
        """构造 python -m unittest 聚合步。"""
        argv = ["python", "-m", "unittest", "discover", *extra]
        return self.step("py-selftest", argv)

    def test_discovery_dir_expands_to_real_files_and_runs(self):
        """发现目录展开成真实测试文件：步骤执行、Ran 1 test、判 pass。"""
        self.write(
            "checks/test_sample.py",
            "import unittest\n\n\nclass Sample(unittest.TestCase):\n"
            "    def test_ok(self):\n        self.assertTrue(True)\n",
        )
        self.write_manifest([self.unittest_step("-s", "checks", "-p", "test_*.py", "-v")])
        proc = self.run_all()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self.last_line(proc), "run_all: 1 steps, 0 error, 0 fail, 0 pending"
        )
        record = self.read_json("build/ci/run_all.json")["steps"][0]
        self.assertEqual(record["exit"], 0)
        self.assertIsNone(record["error_kind"])
        # unittest 把结果写到 stderr（不是 stdout），tail 同样原样归档。
        self.assertIn("Ran 1 test", record["stderr_tail"])
        self.assertEqual(self.read_json("build/ci/pending.json")["items"], [])

    def test_discovery_without_matching_tests_is_pending_not_pass(self):
        """发现目录里 0 个测试：记 pending-target（目录本身），不当 Ran 0 通过。"""
        self.write("checks/notes.txt", "no tests here\n")
        self.write_manifest([self.unittest_step("-s", "checks")])
        proc = self.run_all()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self.last_line(proc), "run_all: 1 steps, 0 error, 0 fail, 1 pending"
        )
        self.assertEqual(
            self.read_json("build/ci/pending.json")["items"],
            [{"card": "CORE-41", "target": "py-selftest", "reason": "checks"}],
        )
        self.assertIsNone(self.read_json("build/ci/run_all.json")["steps"][0]["exit"])
        release = self.run_all("--release")
        self.assertEqual(release.returncode, 1, release.stdout)

    def test_discovery_follows_package_directories_only(self):
        """只有逐级包目录被递归（与 unittest 一致），散放子目录不参与发现。"""
        self.write("checks/test_top.py", "import unittest\n\n\nclass Top(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n")
        self.write("checks/pkg/__init__.py", "")
        self.write("checks/pkg/test_inner.py", "import unittest\n\n\nclass Inner(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n")
        self.write("checks/loose/test_loose.py", "import unittest\n\n\nclass Loose(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n")
        self.write_manifest([self.unittest_step("-s", "checks", "-p", "test_*.py")])
        proc = self.run_all()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        tail = self.read_json("build/ci/run_all.json")["steps"][0]["stderr_tail"]
        self.assertIn("Ran 2 tests", tail)

    def test_discovery_pattern_decides_presence(self):
        """-p 模式决定发现结果；模式不匹配即 pending，不把空跑当 green。"""
        self.write("checks/test_sample.py", "import unittest\n\n\nclass Sample(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n")
        self.write_manifest([self.unittest_step("-s", "checks", "-p", "check_*.py")])
        proc = self.run_all()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self.last_line(proc), "run_all: 1 steps, 0 error, 0 fail, 1 pending"
        )
        self.assertEqual(
            self.read_json("build/ci/pending.json")["items"][0]["reason"], "checks"
        )


class HaTwoCase(unittest.TestCase):
    """HA-002 窄消费者：--release 时拒绝样品豁免与不可信 maint 报告。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="runall-ha002-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        target = self.root / "tools/ci/tests/fixtures/runall"
        target.mkdir(parents=True)
        for item in FIXTURES.iterdir():
            if item.is_file():
                shutil.copy2(item, target / item.name)
        self.manifest = self.root / "manifest.json"
        self.write_manifest([self.step("maint-report", "CORE-71")])

    def step(self, step_id, owner):
        """maint-report 步：桩按环境变量写 build/maint.json。"""
        return {
            "id": step_id,
            "owner": owner,
            "argv": ["python", "tools/ci/tests/fixtures/runall/stub_maint.py", "build/maint.json"],
        }

    def write_manifest(self, steps):
        """写 manifest。"""
        self.manifest.write_text(
            json.dumps({"version": 1, "steps": steps}, ensure_ascii=False), encoding="utf-8"
        )

    def run_all(self, *args, env=None):
        """运行 run_all。"""
        command = [PYTHON, str(RUN_ALL), "--root", str(self.root), "--manifest", str(self.manifest)]
        command.extend(args)
        full_env = dict(os.environ)
        if env is not None:
            full_env.update(env)
        return subprocess.run(
            command, cwd=str(self.root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=full_env,
        )

    def test_clean_report_passes_on_release(self):
        """无标记的当次报告不干预（--release 通过）。"""
        proc = self.run_all("--release", env={"RUNALL_MAINT": '{"version": 1, "violations": []}'})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("HA-002", proc.stderr)

    def test_marker_rejected_on_release_only(self):
        """含 SAMPLE-WAIVER[HA-002] 标记：--release 退出 1，开发态不干预。"""
        payload = json.dumps(
            {"version": 1, "violations": [{"rule": "HA-002", "message": "SAMPLE-WAIVER[HA-002]: 样品豁免 A"}]},
            ensure_ascii=False,
        )
        dev = self.run_all(env={"RUNALL_MAINT": payload})
        self.assertEqual(dev.returncode, 0, dev.stdout + dev.stderr)
        proc = self.run_all("--release", env={"RUNALL_MAINT": payload})
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("HA-002 发布拒绝", proc.stderr)

    def test_missing_report_is_error(self):
        """当次报告不存在：--release 退出 2。"""
        proc = self.run_all("--release", env={"RUNALL_MAINT": ""})
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("报告缺失", proc.stderr)

    def test_corrupt_report_is_error(self):
        """当次报告不是合法 JSON：--release 退出 2。"""
        proc = self.run_all("--release", env={"RUNALL_MAINT": "{not json"})
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("报告损坏", proc.stderr)

    def test_stale_report_not_trusted(self):
        """旧报告未由本轮更新时退出 2，旧豁免不能顶替。"""
        report = self.root / "build/maint.json"
        report.parent.mkdir(parents=True)
        report.write_text(
            json.dumps({"version": 1, "violations": [{"message": "SAMPLE-WAIVER[HA-002]: 旧"}]}),
            encoding="utf-8",
        )
        proc = self.run_all("--release", env={"RUNALL_MAINT": ""})
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("未由本轮更新", proc.stderr)

    def test_missing_violations_array_is_error(self):
        """报告缺 violations 数组：--release 退出 2。"""
        proc = self.run_all("--release", env={"RUNALL_MAINT": '{"version": 1}'})
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("缺少 violations", proc.stderr)

    def test_other_violations_do_not_trigger(self):
        """别的规则或缺失 message 的违规不算 HA-002 标记。"""
        payload = json.dumps(
            {"version": 1, "violations": [{"rule": "OTHER", "message": "其他违规"}, {"rule": "X"}]},
            ensure_ascii=False,
        )
        proc = self.run_all("--release", env={"RUNALL_MAINT": payload})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("HA-002", proc.stderr)

    def test_pending_maint_step_does_not_trigger(self):
        """maint-report 步 pending 时先分流，不判 error/不消费报告。"""
        self.write_manifest(
            [{"id": "maint-report", "owner": "CORE-71", "argv": ["python", "tools/ci/maint_report.py"]}]
        )
        proc = self.run_all("--release")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertNotIn("HA-002", proc.stderr)


class ManifestRepositoryCase(unittest.TestCase):
    """仓库内 manifest 的形状与逐项 argv（不写 *、不靠发现目录）。"""

    def setUp(self):
        self.doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.steps = {item["id"]: item for item in self.doc["steps"]}

    def test_order_and_owners(self):
        """16 步顺序与 owner 固定（含新增的 dto-drift、gate74-selftest 两个真实接线步）。"""
        self.assertEqual(self.doc["version"], 1)
        self.assertEqual(
            [item["id"] for item in self.doc["steps"]],
            [
                "reservations", "check-deps", "check-privacy", "check-unsafe", "check-abi",
                "check-errors", "check-sadd", "sadd-stats", "sadd-audit", "sadd-selftest",
                "dtocheck", "dtocheck-selftest", "dto-drift", "gate74-selftest",
                "core-sources", "maint-report",
            ],
        )
        self.assertEqual(self.steps["reservations"]["owner"], "CORE-75")
        self.assertEqual(self.steps["check-deps"]["owner"], "CORE-69")
        self.assertEqual(self.steps["check-privacy"]["owner"], "CORE-69")
        for name in ("check-unsafe", "check-abi", "check-errors"):
            self.assertEqual(self.steps[name]["owner"], "CORE-74")
        self.assertEqual(self.steps["check-sadd"]["owner"], "CORE-70")
        for name in ("sadd-stats", "sadd-audit"):
            self.assertEqual(self.steps[name]["owner"], "CORE-76")
        self.assertEqual(self.steps["core-sources"]["owner"], "CORE-41")
        self.assertEqual(self.steps["maint-report"]["owner"], "CORE-71")
        self.assertEqual(self.steps["dto-drift"]["owner"], "CORE-67")
        self.assertEqual(self.steps["gate74-selftest"]["owner"], "CORE-74")
        for name in ("sadd-selftest", "dtocheck", "dtocheck-selftest"):
            self.assertEqual(self.steps[name]["owner"], "SADD")
            self.assertEqual(self.steps[name]["kind"], "docs-tool")

    def test_argv_are_literal_and_targets_exist(self):
        """argv 只含 python/node 与字面参数；本卡与文档工具引用的脚本必须真实存在。

        他卡脚本（CORE-69/70/71/74/75/76）尚未落地时按 pending-target 记录，
        这里只固定它们必须是仓库相对路径，不伪造存在性。
        """
        for item in self.doc["steps"]:
            with self.subTest(step=item["id"]):
                self.assertIn(item["argv"][0], ("python", "node"))
                self.assertNotIn("*", " ".join(item["argv"]))
                for arg in item["argv"][1:]:
                    if not arg.endswith((".py", ".mjs")) or arg.startswith("-"):
                        continue
                    if item["owner"] == "CORE-41" or item.get("kind") == "docs-tool":
                        self.assertTrue((REPO / arg).exists(), arg)
                    else:
                        self.assertTrue(arg.startswith("tools/"), arg)

    def test_selftests_list_each_file(self):
        """7 个 SADD 自测与 6 个 DTOcheck 自测逐文件列明，不用目录或通配符。"""
        sadd = self.steps["sadd-selftest"]["argv"]
        self.assertEqual(sadd[:2], ["node", "--test"])
        self.assertEqual(len(sadd) - 2, 7)
        self.assertEqual(
            [Path(item).name for item in sadd[2:]],
            [
                "pack.test.mjs", "current.test.mjs", "reservations.test.mjs",
                "cardiff.test.mjs", "audit.test.mjs", "stats.test.mjs", "structure.test.mjs",
            ],
        )
        dto = self.steps["dtocheck-selftest"]["argv"]
        self.assertEqual(dto[:2], ["node", "--test"])
        self.assertEqual(len(dto) - 2, 6)
        self.assertEqual(
            [Path(item).name for item in dto[2:]],
            [
                "cards.test.mjs", "dto.test.mjs", "layout.test.mjs",
                "xref.test.mjs", "registry.test.mjs", "yaml-lite.test.mjs",
            ],
        )

    def test_existing_checks_use_real_argv(self):
        """既有检查脚本按真实 argv 调用（sadd/check-sadd/core-sources/maint-report）。"""
        self.assertEqual(self.steps["check-sadd"]["argv"], ["python", "tools/ci/check_sadd.py", "--sadd", "SADD", "--out", "build/check-sadd"])
        self.assertEqual(self.steps["check-sadd"]["release_args"], ["--release"])
        self.assertEqual(self.steps["sadd-stats"]["argv"], ["node", "tools/sadd/stats.mjs", "--check"])
        self.assertEqual(
            self.steps["sadd-audit"]["argv"],
            ["node", "tools/sadd/audit.mjs", "--sadd", "SADD", "--out", "build/sadd/audit.json"],
        )
        self.assertEqual(self.steps["dtocheck"]["argv"], ["node", "tools/DTOcheck/run.mjs", "--strict"])
        self.assertEqual(self.steps["reservations"]["argv"], ["node", "tools/sadd/reservations.mjs"])
        maint = self.steps["maint-report"]["argv"]
        self.assertIn("--lcov", maint)
        self.assertIn("build/coverage/core.lcov", maint)
        self.assertIn("--core-sources", maint)
        self.assertIn("build/coverage/core-sources.json", maint)
        self.assertIn("--annotations", maint)
        for name in ("check-deps", "check-privacy", "check-unsafe"):
            self.assertEqual(
                self.steps[name]["argv"], ["python", "tools/ci/%s.py" % name.replace("-", "_"), "--root", "."]
            )
        self.assertEqual(
            self.steps["check-abi"]["argv"],
            ["python", "tools/ci/check_abi.py", "--root", ".", "--base-ref", "abi-v1.0.0"],
        )
        self.assertEqual(
            self.steps["check-errors"]["argv"],
            ["python", "tools/ci/check_errors.py", "--root", "."],
        )

    def test_release_consumers_only(self):
        """只有声明 release_args 的步骤在 --release 追加参数。"""
        consumers = [item["id"] for item in self.doc["steps"] if "release_args" in item]
        self.assertEqual(consumers, ["check-sadd", "dto-drift"])
        self.assertEqual(self.steps["dto-drift"].get("release_args"), ["--release"])

    def test_dto_drift_step_matches_generator_fragment(self):
        """manifest 的 dto-drift 与 CORE-67 生成器内发布的片段逐字段一致。"""
        sys.path.insert(0, str(HERE))
        try:
            import gen_dto
        finally:
            sys.path.remove(str(HERE))
        self.assertEqual(self.steps["dto-drift"], json.loads(gen_dto.CI_STEP_FRAGMENT))

    def test_gate74_selftest_lists_each_file(self):
        """CORE-74 自测走 python -m unittest 并逐个列文件，不用通配或目录。"""
        argv = self.steps["gate74-selftest"]["argv"]
        self.assertEqual(argv[:3], ["python", "-m", "unittest"])
        self.assertEqual(argv[3:], list(GATE74_SELFTESTS))


class DtoDriftCase(unittest.TestCase):
    """CORE-67 的 dto-drift 接入聚合入口：跑真实生成器，漂移必须让聚合失败。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dto-drift-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "tools" / "ci").mkdir(parents=True)
        for name in ("gen_dto.py", "dto_emit.py", "dto_schema.py"):
            shutil.copy2(HERE / name, self.root / "tools" / "ci" / name)
        shutil.copytree(REPO / "contracts/dto", self.root / "contracts" / "dto")
        self.out = self.root / "app" / "lib" / "binding" / "dto"
        self.out.parent.mkdir(parents=True)
        shutil.copytree(REPO / "app/lib/binding/dto", self.out)
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(
            json.dumps({"version": 1, "steps": [{
                "id": "dto-drift",
                "owner": "CORE-67",
                "argv": ["python", "tools/ci/gen_dto.py", "--check",
                         "--report", "build/dto/drift.json"],
            }]}, ensure_ascii=False),
            encoding="utf-8",
        )

    def run_all(self, *extra):
        """在临时根跑聚合入口；run_all.py 与生成器都用仓库内的真实文件。"""
        return subprocess.run(
            [PYTHON, str(RUN_ALL), "--root", str(self.root), "--manifest", str(self.manifest),
             "--out", "build/ci", *extra],
            cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )

    def pending(self):
        """读本次聚合写出的 pending.json。"""
        path = self.root / "build" / "ci" / "pending.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_matching_outputs_pass(self):
        """生成物与清单一致 → 该步 pass、聚合退 0、无 pending。"""
        done = self.run_all()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("[pass] dto-drift (CORE-67) exit=0", done.stdout)
        self.assertEqual(done.stdout.strip().splitlines()[-1], "run_all: 1 steps, 0 error, 0 fail, 0 pending")
        self.assertEqual(self.pending()["items"], [])

    def test_drifted_output_fails_aggregate(self):
        """手改生成物 → 该步 fail、聚合退 1，不能记 pending 或通过。"""
        target = sorted(self.out.glob("*.g.dart"))[0]
        target.write_text(
            target.read_text(encoding="utf-8") + "// hand edit" + chr(10), encoding="utf-8"
        )
        done = self.run_all()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("[fail] dto-drift (CORE-67) exit=1", done.stdout)
        self.assertEqual(done.stdout.strip().splitlines()[-1], "run_all: 1 steps, 0 error, 1 fail, 0 pending")
        record = json.loads((self.root / "build" / "ci" / "run_all.json").read_text(encoding="utf-8"))
        self.assertEqual(record["steps"][0]["exit"], 1)
        self.assertEqual(self.pending()["items"], [])

    def test_missing_outputs_fail_aggregate_not_pending(self):
        """生成目录整体缺失 → 生成器退 1，聚合记 fail 而不是跳过。"""
        shutil.rmtree(self.out)
        done = self.run_all()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("[fail] dto-drift (CORE-67) exit=1", done.stdout)
        self.assertEqual(self.pending()["items"], [])


class Gate74SelfTestCase(unittest.TestCase):
    """CORE-74 自测接缝：脚本未合入记 pending，合入后必须真跑，0 tests 不算通过。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="gate74-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "tools" / "ci" / "tests").mkdir(parents=True)
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(
            json.dumps({"version": 1, "steps": [{
                "id": "gate74-selftest",
                "owner": "CORE-74",
                "argv": ["python", "-m", "unittest", *GATE74_SELFTESTS],
            }]}, ensure_ascii=False),
            encoding="utf-8",
        )

    def write(self, name, text):
        """在临时根写一个自测文件。"""
        (self.root / name).write_text(text, encoding="utf-8")

    def run_all(self, *extra):
        """在临时根跑聚合入口。"""
        return subprocess.run(
            [PYTHON, str(RUN_ALL), "--root", str(self.root), "--manifest", str(self.manifest),
             "--out", "build/ci", *extra],
            cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )

    def pending(self):
        """读本次聚合写出的 pending.json。"""
        path = self.root / "build" / "ci" / "pending.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_absent_scripts_are_pending_and_release_fails(self):
        """四个自测文件都不在 → 记 pending-target，不执行、不伪造通过；--release 退 1。"""
        done = self.run_all()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("[pending] gate74-selftest (CORE-74)", done.stdout)
        self.assertEqual(done.stdout.strip().splitlines()[-1], "run_all: 1 steps, 0 error, 0 fail, 1 pending")
        self.assertEqual(
            self.pending()["items"],
            [{"card": "CORE-74", "target": "gate74-selftest", "reason": ",".join(GATE74_SELFTESTS)}],
        )
        release = self.run_all("--release")
        self.assertEqual(release.returncode, 1, release.stdout + release.stderr)

    def test_landed_scripts_run(self):
        """四个自测文件合入后真跑 unittest，四例通过、聚合退 0。"""
        body = (
            "import unittest" + chr(10) + chr(10) + chr(10)
            + "class Gate(unittest.TestCase):" + chr(10)
            + "    def test_ok(self):" + chr(10)
            + "        self.assertTrue(True)" + chr(10)
        )
        for name in GATE74_SELFTESTS:
            self.write(name, body)
        done = self.run_all()
        output = done.stdout + done.stderr
        self.assertEqual(done.returncode, 0, output)
        self.assertIn("[pass] gate74-selftest (CORE-74) exit=0", done.stdout)
        self.assertIn("Ran 4 tests", output)
        self.assertEqual(self.pending()["items"], [])

    def test_present_but_empty_scripts_are_not_green(self):
        """四个文件都在但没有任何用例 → unittest 退 5，聚合记 error、退 2，不当通过。"""
        for name in GATE74_SELFTESTS:
            self.write(name, '"""waiting for CORE-74."""' + chr(10))
        done = self.run_all()
        output = done.stdout + done.stderr
        self.assertEqual(done.returncode, 2, output)
        self.assertIn("[error] gate74-selftest (CORE-74) exit=5", done.stdout)
        self.assertEqual(done.stdout.strip().splitlines()[-1], "run_all: 1 steps, 1 error, 0 fail, 0 pending")
        record = json.loads((self.root / "build" / "ci" / "run_all.json").read_text(encoding="utf-8"))
        self.assertEqual(record["steps"][0]["exit"], 5)




if __name__ == "__main__":
    unittest.main()
