"""CORE-67 阶段1：gen_dto 命令行行为测试（退出码、报告格式、写盘边界、参数透传）。

两条路各自验证一部分：真实 fixture 清单走完整链路（manifest → CORE-100 类型图 →
生成 → 报告），替身 compile_manifest 验证“只消费类型图”、参数透传与错误映射。
临时输出一律落在 build/dto-test/ 下（build/ 不入库），报告里因此是仓库相对路径。
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dto_emit
import dto_schema as ds
import gen_dto

#: 仓库根；报告里的路径都相对它。
REPO = Path(__file__).resolve().parent.parent.parent
#: 本卡 fixture 清单（CORE-100 的 test_a08 复用同一份）。
FIXTURE = REPO / "tools" / "ci" / "tests" / "fixtures" / "dto" / "fixture.manifest.json"
#: 测试临时区。
WORK = REPO / "build" / "dto-test"
#: --check 报告的固定键集（卡 :22）。
REPORT_KEYS = {"version", "mode", "manifest", "required_stage", "release",
               "ready", "pending", "skipped", "files", "diagnostics", "exit"}
#: files[] 与 diagnostics[] 每项的固定键集。
FILE_KEYS = {"path", "status", "sha256", "expected_sha256"}
DIAG_KEYS = {"severity", "code", "op", "file", "pointer", "message"}


# ---- 替身类型图（与 CORE-100 同形的只读 bundle）-----------------------------

def _ref(source: str, pointer: str) -> ds.SchemaRef:
    """图边：<schema 文件>#<Pointer>。"""
    return ds.SchemaRef("%s#%s" % (source, pointer))


def _node(source: str, pointer: str, kind: str, *, title: str | None = None,
          fields: tuple = (), item: ds.SchemaRef | None = None) -> ds.SchemaNode:
    """一个类型图节点。"""
    return ds.SchemaNode(ref=_ref(source, pointer), title=title, nullable=False,
                         kind=kind, fields=tuple(fields), item=item)


def _field(wire: str, dart: str, value: ds.SchemaRef, required: bool = True) -> ds.SchemaField:
    """一个对象字段。"""
    return ds.SchemaField(wire_name=wire, dart_name=dart, value=value, required=required)


def _op(name: str, request: ds.SchemaRef, ok: ds.SchemaRef, schema: str) -> ds.ReadySchemaOp:
    """一个 ready op。"""
    return ds.ReadySchemaOp(op=name, owner="CORE-67", stage="S0", scope="none",
                            mode="call", schema=schema, request=request, ok=ok,
                            error_codes=(), sensitive_paths=(),
                            reads_engine_snapshot=False)


def _pending(name: str) -> ds.PendingSchemaOp:
    """一个 pending op。"""
    return ds.PendingSchemaOp(op=name, owner="CORE-67", stage="S4", scope="none",
                              mode=None, schema=None, blocked_reason="等待字段设计闭合")


def _bundle(nodes: tuple = (), ready: tuple = (), pending: tuple = (),
            valid: bool = True) -> ds.SchemaBundle:
    """把手搭节点包成与 compile_manifest 同形的 bundle。"""
    nodes = tuple(nodes)
    return ds.SchemaBundle(
        valid=valid, ready=tuple(ready), pending=tuple(pending), nodes=nodes,
        named=tuple(node.ref for node in nodes if node.title is not None),
        diagnostics=(), _index={node.ref.id: node for node in nodes})


def _echo_stub() -> ds.SchemaBundle:
    """最小可生成图：request{text} → ok{echo}。"""
    src = "fixture-echo.schema.json"
    nodes = (
        _node(src, "/$defs/request", "object", title="FixtureEchoRequest",
              fields=(_field("text", "text", _ref(src, "/$defs/request/properties/text")),)),
        _node(src, "/$defs/request/properties/text", "string"),
        _node(src, "/$defs/ok", "object", title="FixtureEchoOk",
              fields=(_field("echo", "echo", _ref(src, "/$defs/ok/properties/echo")),)),
        _node(src, "/$defs/ok/properties/echo", "string"),
    )
    return _bundle(nodes, (_op("fixture.echo", _ref(src, "/$defs/request"),
                               _ref(src, "/$defs/ok"), src),))


def _two_domain_stub() -> ds.SchemaBundle:
    """两个域各一个 op（各自 schema 文件），外加两个乱序 pending：验证排序。"""
    alpha = "alpha.schema.json"
    beta = "beta.schema.json"
    nodes = (
        _node(alpha, "/$defs/request", "object", title="AlphaRequest", fields=()),
        _node(beta, "/$defs/request", "object", title="BetaRequest", fields=()),
    )
    ready = (
        _op("beta.get", _ref(beta, "/$defs/request"), _ref(beta, "/$defs/request"), beta),
        _op("alpha.get", _ref(alpha, "/$defs/request"), _ref(alpha, "/$defs/request"), alpha),
    )
    return _bundle(nodes, ready, (_pending("fixture.zeta"), _pending("fixture.alpha")))


def _unsupported_stub() -> ds.SchemaBundle:
    """含阶段2 形状（union）：生成必须被拒绝。"""
    src = "fixture-echo.schema.json"
    nodes = (
        _node(src, "/$defs/request", "object", title="FixtureEchoRequest", fields=()),
        _node(src, "/$defs/ok", "union", title="FixtureEchoOk"),
    )
    return _bundle(nodes, (_op("fixture.echo", _ref(src, "/$defs/request"),
                               _ref(src, "/$defs/ok"), src),))


def _conflict_stub() -> ds.SchemaBundle:
    """两个 title 只差大小写：同一类名被占用。"""
    src = "fixture-echo.schema.json"
    nodes = (
        _node(src, "/$defs/a", "object", title="Conflict", fields=()),
        _node(src, "/$defs/b", "object", title="conflict", fields=()),
    )
    ready = (
        _op("fixture.one", _ref(src, "/$defs/a"), _ref(src, "/$defs/a"), src),
        _op("fixture.two", _ref(src, "/$defs/b"), _ref(src, "/$defs/b"), src),
    )
    return _bundle(nodes, ready)


def _aggregate(code: int) -> str:
    """替身 CI 聚合器：与 CORE-41 口径一致 0→pass、1→fail、2→error。"""
    return {0: "pass", 1: "fail"}.get(code, "error")


class TempArea(unittest.TestCase):
    """给每个用例准备干净的 out / report 路径并封装进程内调用。"""

    def setUp(self) -> None:
        WORK.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(
            prefix=self.id().rsplit(".", 1)[-1] + "-", dir=str(WORK)))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.out = self.root / "out"
        self.report = self.root / "drift.json"

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        """进程内跑一次 run()，返回 (退出码, stdout, stderr)。"""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gen_dto.run(list(argv))
        return code, out.getvalue(), err.getvalue()

    def check(self) -> tuple[int, str, str]:
        """对 fixture 清单跑 --check，报告写到 self.report。"""
        return self.run_cli("--check", "--manifest", str(FIXTURE),
                            "--out", str(self.out), "--report", str(self.report))

    def write(self) -> int:
        """对 fixture 清单跑 --write。"""
        return self.run_cli("--write", "--manifest", str(FIXTURE),
                            "--out", str(self.out))[0]

    def load_report(self) -> dict:
        """读回 --check 报告。"""
        return json.loads(self.report.read_text(encoding="utf-8"))


class TestCommandLine(TempArea):
    """卡 :20-21：两个入口互斥且必填，参数错误一律工具错误 2。"""

    def script(self, *argv: str) -> int:
        """以子进程跑真实入口，拿到解释器层面的退出码。"""
        done = subprocess.run(
            [sys.executable, str(REPO / "tools" / "ci" / "gen_dto.py"), *argv],
            cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
        return done.returncode

    def test_both_modes_exit_2(self) -> None:
        """--check 与 --write 同时给出 → 2（进程内与子进程都是 2）。"""
        self.assertEqual(self.script("--check", "--write", "--manifest",
                                     str(FIXTURE)), 2)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                gen_dto.run(["--check", "--write"])
        self.assertEqual(ctx.exception.code, 2)

    def test_no_mode_exit_2(self) -> None:
        """两个入口都不给 → 2。"""
        self.assertEqual(self.script("--manifest", str(FIXTURE)), 2)

    def test_unknown_stage_exit_2(self) -> None:
        """--required-stage 取值不在 CORE-100 的 STAGES 里 → 2。"""
        self.assertEqual(self.script("--check", "--required-stage", "S9"), 2)


class TestWrite(TempArea):
    """卡 :20、:49：--write 只写确定文件集，不写报告、不动别的文件。"""

    def test_writes_only_deterministic_file_set(self) -> None:
        """fixture 清单下文件集恰为 fixture.g.dart，且带生成物头。"""
        code, out_text, _ = self.run_cli("--write", "--manifest", str(FIXTURE),
                                         "--out", str(self.out))
        self.assertEqual(code, 0)
        self.assertEqual(sorted(path.name for path in self.out.iterdir()),
                         ["fixture.g.dart"])
        text = (self.out / "fixture.g.dart").read_text(encoding="utf-8")
        self.assertTrue(dto_emit.has_generated_header(text))
        self.assertIn("manifest=fixture.manifest.json", text)
        self.assertIn("fixture.g.dart", out_text)

    def test_write_does_not_write_report(self) -> None:
        """--write 即使给了 --report 也不写报告。"""
        code, _, _ = self.run_cli("--write", "--manifest", str(FIXTURE),
                                  "--out", str(self.out), "--report", str(self.report))
        self.assertEqual(code, 0)
        self.assertFalse(self.report.exists())

    def test_write_leaves_other_files_alone(self) -> None:
        """集合外文件（同目录）不被删除也不被改动。"""
        self.out.mkdir(parents=True)
        keep = self.out / "keep.txt"
        keep.write_text("手工文件\n", encoding="utf-8")
        self.assertEqual(self.write(), 0)
        self.assertEqual(keep.read_text(encoding="utf-8"), "手工文件\n")
        self.assertEqual(sorted(path.name for path in self.out.iterdir()),
                         ["fixture.g.dart", "keep.txt"])

    def test_fixture_emits_required_nullable_note(self) -> None:
        """卡 :38：fixture 的 required+nullable note 走完整链路仍生成必填参数与 presence 读器。"""
        self.assertEqual(self.write(), 0)
        text = (self.out / "fixture.g.dart").read_text(encoding="utf-8")
        self.assertIn("    required this.note,", text)
        self.assertIn("  final String? note;", text)
        self.assertIn("note: readStringPresent(json, 'note'),", text)

    def test_two_writes_are_byte_identical(self) -> None:
        """连续两次 --write 字节相同（无时间戳、无环境依赖）。"""
        self.assertEqual(self.write(), 0)
        first = (self.out / "fixture.g.dart").read_bytes()
        self.assertEqual(self.write(), 0)
        self.assertEqual((self.out / "fixture.g.dart").read_bytes(), first)


class TestCheck(TempArea):
    """卡 :22、:49：报告冻结形状，四态里阶段1 覆盖 missing/match/drift。"""

    def test_match_exit_0_and_report_shape(self) -> None:
        """写后未改：全 match、退出 0、报告键集与取值冻结。"""
        self.assertEqual(self.write(), 0)
        before = (self.out / "fixture.g.dart").read_bytes()
        code, out_text, _ = self.check()
        self.assertEqual(code, 0)
        report = self.load_report()
        self.assertEqual(set(report), REPORT_KEYS)
        self.assertEqual(report["version"], 1)
        self.assertEqual(report["mode"], "check")
        self.assertEqual(report["manifest"], FIXTURE.relative_to(REPO).as_posix())
        self.assertIsNone(report["required_stage"])
        self.assertFalse(report["release"])
        self.assertEqual((report["ready"], report["pending"]), (1, 1))
        self.assertEqual(report["skipped"], ["fixture.pending_echo"])
        self.assertEqual(report["exit"], 0)
        self.assertEqual(len(report["files"]), 1)
        row = report["files"][0]
        self.assertEqual(set(row), FILE_KEYS)
        self.assertEqual(row["path"],
                         (self.out / "fixture.g.dart").relative_to(REPO).as_posix())
        self.assertEqual(row["status"], "match")
        self.assertEqual(row["sha256"], row["expected_sha256"])
        self.assertEqual(len(report["diagnostics"]), 1)
        diag = report["diagnostics"][0]
        self.assertEqual(set(diag), DIAG_KEYS)
        self.assertEqual((diag["severity"], diag["code"], diag["op"]),
                         ("info", "DTO_PENDING_SKIP", "fixture.pending_echo"))
        self.assertIsNone(diag["file"])
        self.assertIsNone(diag["pointer"])
        self.assertTrue(diag["message"].startswith("SKIP pending fixture.pending_echo: "))
        self.assertIn("match=1", out_text)
        self.assertEqual((self.out / "fixture.g.dart").read_bytes(), before)

    def test_check_on_empty_out_missing_exit_1(self) -> None:
        """生成目录为空：files 全 missing、sha256 为 null、退出 1，且不建目录。"""
        code, _, _ = self.check()
        self.assertEqual(code, 1)
        self.assertFalse(self.out.exists())
        report = self.load_report()
        row = report["files"][0]
        self.assertEqual(row["status"], "missing")
        self.assertIsNone(row["sha256"])
        self.assertTrue(row["expected_sha256"])
        self.assertEqual(report["exit"], 1)

    def test_drift_exit_1(self) -> None:
        """手改生成文件 → drift、sha256 与期望不同、退出 1。"""
        self.assertEqual(self.write(), 0)
        target = self.out / "fixture.g.dart"
        target.write_text(target.read_text(encoding="utf-8") + "// 手改\n",
                          encoding="utf-8")
        code, _, _ = self.check()
        self.assertEqual(code, 1)
        report = self.load_report()
        row = report["files"][0]
        self.assertEqual(row["status"], "drift")
        self.assertNotEqual(row["sha256"], row["expected_sha256"])
        self.assertEqual(report["exit"], 1)

    def test_report_is_byte_stable_and_path_free(self) -> None:
        """同一输入两次报告逐字节相同；无盘符、无绝对路径、无时间戳。"""
        self.assertEqual(self.write(), 0)
        self.check()
        first = self.report.read_bytes()
        self.check()
        self.assertEqual(self.report.read_bytes(), first)
        text = first.decode("utf-8")
        self.assertNotRegex(text, r"[A-Za-z]:[\\/]")
        self.assertNotIn(REPO.as_posix(), text)
        self.assertNotRegex(text, r"\d{4}-\d{2}-\d{2}")

    def test_files_and_diagnostics_sorted(self) -> None:
        """files 按 path 字节序、skipped 按 op、diagnostics 按四元组排序。"""
        with mock.patch.object(ds, "compile_manifest", return_value=_two_domain_stub()):
            code, _, _ = self.run_cli(
                "--check", "--manifest", str(self.root / "absent.json"),
                "--out", str(self.out), "--report", str(self.report))
        self.assertEqual(code, 1)
        report = self.load_report()
        paths = [row["path"] for row in report["files"]]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual([Path(item).name for item in paths],
                         ["alpha.g.dart", "beta.g.dart"])
        self.assertEqual(report["skipped"], ["fixture.alpha", "fixture.zeta"])
        keys = [(diag["file"] or "", diag["code"], diag["op"] or "", diag["message"])
                for diag in report["diagnostics"]]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual([diag["op"] for diag in report["diagnostics"]],
                         ["fixture.alpha", "fixture.zeta"])


class TestExitCodes(TempArea):
    """卡 :21：2 不降级为 1，1 不报成 0。"""

    def test_missing_manifest_exit_2(self) -> None:
        """清单读不到（I/O 失败）→ 2，且报告与输出目录都不留痕。"""
        code, _, err = self.run_cli("--check", "--manifest",
                                    str(self.root / "absent.json"),
                                    "--out", str(self.out), "--report", str(self.report))
        self.assertEqual(code, 2)
        self.assertTrue(err.strip())
        self.assertFalse(self.out.exists())
        self.assertFalse(self.report.exists())

    def test_schema_tool_error_exit_2(self) -> None:
        """CORE-100 抛 SchemaToolError → 2。"""
        with mock.patch.object(ds, "compile_manifest",
                               side_effect=ds.SchemaToolError("坏清单")):
            code, _, err = self.run_cli("--write", "--manifest", str(FIXTURE),
                                        "--out", str(self.out))
        self.assertEqual(code, 2)
        self.assertIn("坏清单", err)
        self.assertFalse(self.out.exists())

    def test_unexpected_exception_exit_2(self) -> None:
        """未预期内部异常 → 2（不伪装成漂移）。"""
        with mock.patch.object(ds, "compile_manifest", side_effect=RuntimeError("boom")):
            code, _, err = self.run_cli("--check", "--manifest", str(FIXTURE),
                                        "--out", str(self.out),
                                        "--report", str(self.report))
        self.assertEqual(code, 2)
        self.assertIn("boom", err)
        self.assertFalse(self.report.exists())

    def test_report_not_writable_exit_2(self) -> None:
        """报告路径是目录（写不了）→ 2。"""
        self.assertEqual(self.write(), 0)
        self.report.mkdir(parents=True)
        code, _, _ = self.check()
        self.assertEqual(code, 2)

    def test_valid_false_exit_1_and_no_write(self) -> None:
        """CORE-100 valid=false：--write 不写文件退 1，--check 退 1 且报告 exit=1。"""
        with mock.patch.object(ds, "compile_manifest", return_value=_bundle(valid=False)):
            code, _, err = self.run_cli("--write", "--manifest",
                                        str(self.root / "absent.json"),
                                        "--out", str(self.out))
        self.assertEqual(code, 1)
        self.assertTrue(err.strip())
        self.assertFalse(self.out.exists())
        with mock.patch.object(ds, "compile_manifest", return_value=_bundle(valid=False)):
            code, _, _ = self.run_cli("--check", "--manifest",
                                      str(self.root / "absent.json"),
                                      "--out", str(self.out),
                                      "--report", str(self.report))
        self.assertEqual(code, 1)
        self.assertEqual(self.load_report()["exit"], 1)

    def test_refused_shape_exit_1(self) -> None:
        """不支持的形状（union）：拒绝生成、退 1、不写任何文件并报 DTO_SCHEMA_INVALID。"""
        with mock.patch.object(ds, "compile_manifest", return_value=_unsupported_stub()):
            code, _, _ = self.run_cli("--write", "--manifest",
                                      str(self.root / "absent.json"),
                                      "--out", str(self.out))
        self.assertEqual(code, 1)
        self.assertFalse(self.out.exists())
        with mock.patch.object(ds, "compile_manifest", return_value=_unsupported_stub()):
            code, _, _ = self.run_cli("--check", "--manifest",
                                      str(self.root / "absent.json"),
                                      "--out", str(self.out),
                                      "--report", str(self.report))
        self.assertEqual(code, 1)
        codes = {diag["code"] for diag in self.load_report()["diagnostics"]}
        self.assertIn("DTO_SCHEMA_INVALID", codes)

    def test_name_conflict_exit_1(self) -> None:
        """类型名冲突：退 1 并报 DTO_NAME_CONFLICT。"""
        with mock.patch.object(ds, "compile_manifest", return_value=_conflict_stub()):
            code, _, _ = self.run_cli("--check", "--manifest",
                                      str(self.root / "absent.json"),
                                      "--out", str(self.out),
                                      "--report", str(self.report))
        self.assertEqual(code, 1)
        codes = {diag["code"] for diag in self.load_report()["diagnostics"]}
        self.assertIn("DTO_NAME_CONFLICT", codes)


class TestTypeGraphOnly(TempArea):
    """验收 10：只消费类型图；参数只透传；生成只看图与清单名。"""

    def test_generation_needs_no_schema_files_on_disk(self) -> None:
        """清单与 schema 都不存在、类型图由替身给出时仍能生成（证明未二次解析 schema）。"""
        manifest = self.root / "absent.manifest.json"
        seen: dict[str, object] = {}

        def fake(path, required_stage=None, release=False):
            seen["path"] = path
            seen["required_stage"] = required_stage
            seen["release"] = release
            return _echo_stub()

        with mock.patch.object(ds, "compile_manifest", side_effect=fake):
            code, _, _ = self.run_cli("--write", "--manifest", str(manifest),
                                      "--out", str(self.out))
        self.assertEqual(code, 0)
        self.assertEqual(seen["path"], manifest)
        text = (self.out / "fixture.g.dart").read_text(encoding="utf-8")
        self.assertIn("manifest=absent.manifest.json", text)
        self.assertTrue(dto_emit.has_generated_header(text))

    def test_stage_and_release_are_passed_through(self) -> None:
        """--required-stage 与 --release 原样交给 CORE-100，并写进报告。"""
        seen: dict[str, object] = {}

        def fake(path, required_stage=None, release=False):
            seen["required_stage"] = required_stage
            seen["release"] = release
            return _echo_stub()

        with mock.patch.object(ds, "compile_manifest", side_effect=fake):
            code, _, _ = self.run_cli(
                "--check", "--manifest", str(self.root / "absent.json"),
                "--out", str(self.out), "--report", str(self.report),
                "--required-stage", "S2", "--release")
        self.assertEqual(code, 1)  # 输出目录为空 → missing
        self.assertEqual(seen, {"required_stage": "S2", "release": True})
        report = self.load_report()
        self.assertEqual(report["required_stage"], "S2")
        self.assertTrue(report["release"])

    def test_pending_never_becomes_a_type(self) -> None:
        """pending op 只在 skipped 里出现，生成文件不含它的类型。"""
        bundle = _echo_stub()
        with mock.patch.object(ds, "compile_manifest", return_value=_bundle(
                bundle.nodes, bundle.ready, (_pending("fixture.pending_echo"),))):
            code, _, _ = self.run_cli("--write", "--manifest",
                                      str(self.root / "absent.json"),
                                      "--out", str(self.out))
        self.assertEqual(code, 0)
        text = (self.out / "fixture.g.dart").read_text(encoding="utf-8")
        self.assertNotIn("PendingEcho", text)
        self.assertNotIn("fixture.pending_echo", text)


class TestCiIntegration(TempArea):
    """验收 11：只交步骤片段；替身聚合器把 1 映射 fail、2 映射 error。"""

    def test_fragment_matches_contract(self) -> None:
        """片段 id/owner/argv/release_args 与卡 :56 逐项一致。"""
        step = json.loads(gen_dto.CI_STEP_FRAGMENT)
        self.assertEqual(set(step), {"id", "owner", "argv", "release_args"})
        self.assertEqual(step["id"], "dto-drift")
        self.assertEqual(step["owner"], "CORE-67")
        self.assertEqual(step["argv"][:3],
                         ["python", "tools/ci/gen_dto.py", "--check"])
        self.assertEqual(step["argv"][step["argv"].index("--report") + 1],
                         "build/dto/drift.json")
        self.assertEqual(step["release_args"], ["--release"])

    def test_aggregator_maps_exit_codes(self) -> None:
        """用片段里的 argv 跑真实入口：match→pass、missing→fail、参数错→error。"""
        step = json.loads(gen_dto.CI_STEP_FRAGMENT)
        argv = [sys.executable] + step["argv"][1:] + [
            "--manifest", str(FIXTURE), "--out", str(self.out),
            "--report", str(self.report)]

        def run(extra: list[str]) -> str:
            done = subprocess.run(argv + extra, cwd=str(REPO), capture_output=True,
                                  text=True, encoding="utf-8")
            return _aggregate(done.returncode)

        self.assertEqual(run([]), "fail")          # 空目录 → 1
        subprocess.run([sys.executable, str(REPO / "tools" / "ci" / "gen_dto.py"),
                        "--write", "--manifest", str(FIXTURE), "--out", str(self.out)],
                       cwd=str(REPO), capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run([]), "pass")          # 写后未改 → 0
        self.assertEqual(run(["--write"]), "error")  # 两个入口同给 → 2


class TestNoExtraDependencies(unittest.TestCase):
    """实现约束：只用标准库与 CORE-100 类型图，不 import 领域或运行时实现。"""

    def test_imports_are_stdlib_and_type_graph_only(self) -> None:
        """dto_emit / gen_dto 的导入集合不超出允许名单。"""
        allowed = {"__future__", "argparse", "dataclasses", "hashlib", "json",
                   "pathlib", "re", "sys", "dto_emit", "dto_schema"}
        for name in ("dto_emit.py", "gen_dto.py"):
            tree = ast.parse((REPO / "tools" / "ci" / name).read_text(encoding="utf-8"))
            found: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    found.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    found.add(node.module.split(".")[0])
            self.assertEqual(found - allowed, set(), name)


if __name__ == "__main__":
    unittest.main()
