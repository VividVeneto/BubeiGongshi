"""tools/ci/gen_errors.py 的自测（标准库 unittest，无需 pytest）。

覆盖测试方案 T-01（生成器确定性与结构拒绝）、T-02（消息资源校验）、
T-09（registry 是唯一输入、镜像一致、--check 退出码与不写盘）。
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parent / "gen_errors.py"

REGISTRY_PATH = "contracts/errors/registry.yaml"
ARB_PATH = "app/lib/l10n/errors_zh.arb"
SHARED_WRITES_PATH = "contracts/policies/shared-writes.json"
CODES_RS_PATH = "crates/fml-error/src/codes.rs"
DART_PATH = "app/lib/binding/error_codes.g.dart"
README_PATH = "contracts/errors/README.md"
OWNERSHIP_PATH = "contracts/errors/ownership.yaml"
GENERATED = (CODES_RS_PATH, DART_PATH, README_PATH, OWNERSHIP_PATH, SHARED_WRITES_PATH)

BASE_REGISTRY = {
    "registry_version": 1,
    "entries": [
        {
            "code": "AST_JSON_INVALID",
            "namespace": "AST",
            "owner": "CORE-05",
            "severity": "error",
            "message_key": "err.ast.json_invalid",
            "retryable": False,
            "since": 1,
            "surface": "client",
        },
        {
            "code": "AUTH_LOGIN_FAILED",
            "namespace": "AUTH",
            "owner": "CORE-45",
            "severity": "warning",
            "message_key": "err.auth.login_failed",
            "retryable": True,
            "since": 1,
            "surface": "server",
            "http_status": 401,
        },
        {
            "code": "PARSE_SYNTAX",
            "namespace": "PARSE",
            "owner": "CORE-05",
            "severity": "error",
            "message_key": "err.parse.syntax",
            "fix_hint": True,
            "retryable": False,
            "since": 1,
            "surface": "client",
        },
    ],
}

BASE_ARB = {
    "@@locale": "zh",
    "err.ast.json_invalid": "公式结构无效。",
    "err.auth.login_failed": "登录失败。",
    "err.parse.syntax": "公式语法有误。",
    "err.parse.syntax.fix": "检查括号是否配对后重试。",
}

BASE_SHARED_WRITES = {
    "version": 1,
    "entries": [
        {
            "kind": "error",
            "key": "STALE_CODE",
            "owner": "CORE-99",
            "point": "contracts/errors/registry.yaml",
        },
        {"kind": "route", "key": "/home", "owner": "CORE-05", "point": "app/lib/ui/home.dart"},
        {"kind": "file", "key": "app/lib/main.dart", "owner": "CORE-05", "point": "app/lib/main.dart"},
    ],
}


def variant_of(code: str) -> str:
    """复算生成器的变体名转换规则。"""
    return "".join(part.lower().capitalize() for part in code.split("_"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def build_fixture(root: Path, registry=None, arb=None, shared=None) -> Path:
    """在 root 下写出最小 registry/arb/shared-writes 输入。"""
    write_yaml(root / REGISTRY_PATH, BASE_REGISTRY if registry is None else registry)
    write_json(root / ARB_PATH, BASE_ARB if arb is None else arb)
    write_json(root / SHARED_WRITES_PATH, BASE_SHARED_WRITES if shared is None else shared)
    return root


def run_generator(root: Path, *args: str) -> subprocess.CompletedProcess:
    """以给定仓库根运行生成器，返回完整进程结果。"""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONWARNINGS": "error::SyntaxWarning"},
    )


def entry_by_code(registry: dict, code: str) -> dict:
    """取出注册表中指定 code 的条目（可变引用）。"""
    for entry in registry["entries"]:
        if entry["code"] == code:
            return entry
    raise AssertionError("fixture 缺少 " + code)


class FixtureCase(unittest.TestCase):
    """每个用例在独立临时目录里造输入。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def generate(self) -> None:
        """正常生成一次并断言退出码 0。"""
        result = run_generator(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def read(self, relative: str) -> str:
        """读取生成物文本。"""
        return (self.root / relative).read_text(encoding="utf-8")

    def mutate_registry(self, mutate) -> None:
        """基于基准注册表改一处后写盘（消息资源与 shared-writes 一并就位）。"""
        build_fixture(self.root)
        registry = copy.deepcopy(BASE_REGISTRY)
        mutate(registry)
        write_yaml(self.root / REGISTRY_PATH, registry)


class T01DeterminismTest(FixtureCase):
    """T-01：同一输入连续生成逐字节一致，重复运行不写盘。"""

    def test_two_runs_are_byte_identical(self) -> None:
        build_fixture(self.root)
        self.generate()
        first = {relative: self.read(relative) for relative in GENERATED}
        result = run_generator(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("已是最新", result.stdout)
        second = {relative: self.read(relative) for relative in GENERATED}
        self.assertEqual(first, second)

    def test_two_roots_agree(self) -> None:
        build_fixture(self.root)
        self.generate()
        with tempfile.TemporaryDirectory() as other:
            other_root = build_fixture(Path(other))
            self.assertEqual(run_generator(other_root).returncode, 0)
            for relative in GENERATED:
                self.assertEqual(
                    self.read(relative),
                    (other_root / relative).read_text(encoding="utf-8"),
                    relative,
                )


class T01RejectionTest(FixtureCase):
    """T-01：结构错误一律退出码 2 并指出条目。"""

    def assert_rejected(self, fragment: str, code: str | None) -> None:
        result = run_generator(self.root)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(fragment, result.stderr)
        if code is not None:
            self.assertIn(code, result.stderr)

    def test_duplicate_code(self) -> None:
        self.mutate_registry(lambda registry: registry["entries"].append(
            copy.deepcopy(registry["entries"][0])
        ))
        self.assert_rejected("重复的 code", "AST_JSON_INVALID")

    def test_unknown_namespace(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "PARSE_SYNTAX").update({"namespace": "PARSEX"})
        )
        self.assert_rejected("不在命名空间列表中", "PARSE_SYNTAX")

    def test_namespace_does_not_match_first_segment(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "PARSE_SYNTAX").update({"namespace": "TYPE"})
        )
        self.assert_rejected("与 namespace", "PARSE_SYNTAX")

    def test_missing_message_key(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "AST_JSON_INVALID").pop("message_key")
        )
        self.assert_rejected("缺字段 message_key", "AST_JSON_INVALID")

    def test_condition_field_is_rejected(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "AST_JSON_INVALID").update(
                {"condition": "触发条件不属注册表"}
            )
        )
        self.assert_rejected("含未知字段：condition", "AST_JSON_INVALID")

    def test_missing_surface(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "AST_JSON_INVALID").pop("surface")
        )
        self.assert_rejected("缺字段 surface", "AST_JSON_INVALID")

    def test_invalid_surface(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "AST_JSON_INVALID").update({"surface": "edge"})
        )
        self.assert_rejected("surface 必须是 client/server/both", "AST_JSON_INVALID")

    def test_client_surface_rejects_http_status(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "AST_JSON_INVALID").update({"http_status": 400})
        )
        self.assert_rejected("surface 为 client 时不得填 http_status", "AST_JSON_INVALID")

    def test_http_status_out_of_range(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "AUTH_LOGIN_FAILED").update({"http_status": 399})
        )
        self.assert_rejected("http_status 必须在 400..599 内", "AUTH_LOGIN_FAILED")

    def test_http_status_not_integer(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "AUTH_LOGIN_FAILED").update({"http_status": "401"})
        )
        self.assert_rejected("http_status 必须是整数", "AUTH_LOGIN_FAILED")

    def test_since_below_one(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "AST_JSON_INVALID").update({"since": 0})
        )
        self.assert_rejected("since 必须在 1..registry_version", "AST_JSON_INVALID")

    def test_since_above_registry_version(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "AST_JSON_INVALID").update({"since": 2})
        )
        self.assert_rejected("since 必须在 1..registry_version", "AST_JSON_INVALID")

    def test_deprecated_since_before_since(self) -> None:
        self.mutate_registry(
            lambda registry: registry.update({"registry_version": 3})
            or entry_by_code(registry, "AST_JSON_INVALID").update(
                {"since": 2, "deprecated_since": 1}
            )
        )
        self.assert_rejected("deprecated_since 必须在 since..registry_version 内", "AST_JSON_INVALID")

    def test_owner_format(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "AST_JSON_INVALID").update({"owner": "core-5"})
        )
        self.assert_rejected("owner 不符合卡号格式", "AST_JSON_INVALID")

    def test_variant_collision(self) -> None:
        def add_both(registry: dict) -> None:
            for code, key in (("PARSE_SYNTAX2", "err.parse.syntax2"), ("PARSE_SYNTAX_2", "err.parse.syntax_2")):
                registry["entries"].append(
                    {
                        "code": code,
                        "namespace": "PARSE",
                        "owner": "CORE-05",
                        "severity": "error",
                        "message_key": key,
                        "retryable": False,
                        "since": 1,
                        "surface": "client",
                    }
                )

        self.mutate_registry(add_both)
        write_json(
            self.root / ARB_PATH,
            {**BASE_ARB, "err.parse.syntax2": "另一条。", "err.parse.syntax_2": "又一条。"},
        )
        self.assert_rejected("变体名冲突", None)

    def test_deprecated_entry_still_generated(self) -> None:
        self.mutate_registry(
            lambda registry: entry_by_code(registry, "AST_JSON_INVALID").update(
                {"deprecated_since": 1}
            )
        )
        self.generate()
        self.assertIn("AST_JSON_INVALID", self.read(README_PATH))
        self.assertIn("废弃", self.read(README_PATH))
        self.assertIn("AstJsonInvalid", self.read(CODES_RS_PATH))

    def test_unparsable_registry_is_exit_2(self) -> None:
        build_fixture(self.root)
        (self.root / REGISTRY_PATH).write_text("[::\n", encoding="utf-8")
        self.assert_rejected("无法解析", None)

    def test_missing_registry_is_exit_2(self) -> None:
        build_fixture(self.root)
        (self.root / REGISTRY_PATH).unlink()
        self.assert_rejected("无法读取", None)


class T02MessageResourceTest(FixtureCase):
    """T-02：消息资源的基键、.fix 与孤儿键校验。"""

    def test_fix_hint_without_fix_key(self) -> None:
        build_fixture(self.root, arb={key: value for key, value in BASE_ARB.items() if key != "err.parse.syntax.fix"})
        result = run_generator(self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("err.parse.syntax.fix", result.stderr)
        self.assertIn("PARSE_SYNTAX", result.stderr)

    def test_orphan_fix_key(self) -> None:
        build_fixture(self.root, arb={**BASE_ARB, "err.ghost.code.fix": "没有基键。"})
        result = run_generator(self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("孤儿修复建议消息键", result.stderr)

    def test_fix_key_for_code_without_fix_hint(self) -> None:
        build_fixture(self.root, arb={**BASE_ARB, "err.ast.json_invalid.fix": "多余的建议。"})
        result = run_generator(self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("未声明 fix_hint", result.stderr)
        self.assertIn("AST_JSON_INVALID", result.stderr)

    def test_missing_base_message_key(self) -> None:
        build_fixture(
            self.root,
            arb={key: value for key, value in BASE_ARB.items() if key != "err.auth.login_failed"},
        )
        result = run_generator(self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("消息键缺失", result.stderr)
        self.assertIn("AUTH_LOGIN_FAILED", result.stderr)


class T09MirrorTest(FixtureCase):
    """T-09：registry 是唯一输入，镜像逐项一致，--check 只比较不写盘。"""

    def test_mirrors_match_registry(self) -> None:
        build_fixture(self.root)
        self.generate()
        codes_rs = self.read(CODES_RS_PATH)
        dart = self.read(DART_PATH)
        readme = self.read(README_PATH)
        ownership = self.read(OWNERSHIP_PATH)
        for entry in BASE_REGISTRY["entries"]:
            code = entry["code"]
            self.assertIn(variant_of(code), codes_rs)
            self.assertIn('"' + code + '"', codes_rs)
            self.assertIn("code: '" + code + "'", dart)
            self.assertIn("messageKey: '" + entry["message_key"] + "'", dart)
            self.assertIn("| `" + code + "` | " + entry["owner"] + " |", readme)
            self.assertIn("  - code: " + code + "\n    owner: " + entry["owner"], ownership)
        status = [
            row for row in readme.splitlines() if row.startswith("| `AUTH_LOGIN_FAILED`")
        ][0]
        self.assertIn("| server | 401 |", status)
        default_status = [
            row for row in readme.splitlines() if row.startswith("| `PARSE_SYNTAX`")
        ][0]
        self.assertIn("| client | - | 是 |", default_status)

    def test_shared_writes_error_projection_and_other_kinds(self) -> None:
        build_fixture(self.root)
        self.generate()
        document = json.loads(self.read(SHARED_WRITES_PATH))
        errors = [item for item in document["entries"] if item["kind"] == "error"]
        self.assertEqual(
            errors,
            [
                {
                    "kind": "error",
                    "key": entry["code"],
                    "owner": entry["owner"],
                    "point": REGISTRY_PATH,
                }
                for entry in sorted(BASE_REGISTRY["entries"], key=lambda item: item["code"])
            ],
        )
        others = [item for item in document["entries"] if item["kind"] != "error"]
        self.assertEqual(
            others,
            [item for item in BASE_SHARED_WRITES["entries"] if item["kind"] != "error"],
        )
        self.assertNotIn("STALE_CODE", self.read(SHARED_WRITES_PATH))

    def test_check_detects_drift_without_writing(self) -> None:
        build_fixture(self.root)
        self.generate()
        target = self.root / CODES_RS_PATH
        original = target.read_text(encoding="utf-8")
        target.write_text(original + "// 手工改动\n", encoding="utf-8")
        result = run_generator(self.root, "--check")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(CODES_RS_PATH, result.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), original + "// 手工改动\n")
        fixed = run_generator(self.root)
        self.assertEqual(fixed.returncode, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_check_reports_clean_after_generation(self) -> None:
        build_fixture(self.root)
        self.generate()
        result = run_generator(self.root, "--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("无漂移", result.stdout)

    def test_missing_generated_file_is_drift(self) -> None:
        build_fixture(self.root)
        self.generate()
        (self.root / DART_PATH).unlink()
        result = run_generator(self.root, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn(DART_PATH, result.stderr)
        self.assertFalse((self.root / DART_PATH).exists())


class T09RepositoryStateTest(unittest.TestCase):
    """T-09：真实仓库的生成物已与 registry 同步。"""

    def test_repository_is_clean(self) -> None:
        repo_root = SCRIPT.parents[2]
        result = run_generator(repo_root, "--check")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
