"""CORE-74 ABI-1 验收测试（S0_CORE-74:14）。

本地证据：python -m unittest discover -s tools/ci/tests -p "test_gate74_*.py"
夹具 tools/ci/tests/fixtures/gate74/abi/base.h 是 CORE-03 固定 C 子集的样板；变体在
测试内按文本替换生成，保证每个用例只差一处 ABI 形状。
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CI_DIR = Path(__file__).resolve().parents[1]
SCRIPT = CI_DIR / "check_abi.py"
HEADER = "contracts/include/fmlcore.h"
BASE = (Path(__file__).resolve().parent / "fixtures" / "gate74" / "abi" / "base.h").read_text(
    encoding="utf-8"
)


def run_gate(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def with_minor(text: str) -> str:
    return text.replace("#define FML_ABI_MINOR 0", "#define FML_ABI_MINOR 1")


def with_major(text: str) -> str:
    return text.replace("#define FML_ABI_MAJOR 1", "#define FML_ABI_MAJOR 2")


ADDITIVE = BASE.replace(
    "uint32_t fml_abi_version(void);",
    "uint32_t fml_abi_version(void);\nuint32_t fml_extra(void);",
)
REMOVED = BASE.replace("FmlStatus fml_context_create(FmlContext **out);\n", "")
STRUCT_APPEND = BASE.replace(
    "    uint8_t *ptr;\n} FmlBuf;", "    uint8_t *ptr;\n    uint32_t flags;\n} FmlBuf;"
)
STRUCT_INSERT = BASE.replace(
    "    uint64_t len;\n", "    uint64_t len;\n    uint32_t flags;\n"
)


class AbiGateTest(unittest.TestCase):
    """基准解析、版本单调与破坏性/新增判定。"""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repo"

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def write(self, text: str) -> None:
        target = self.root / HEADER
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))

    def init(self, text: str = BASE) -> None:
        self.root.mkdir(parents=True)
        self.write(text)
        self.git("init", "-q")
        self.git("config", "user.email", "review@example.invalid")
        self.git("config", "user.name", "review")
        self.commit("base")

    def commit(self, message: str = "change") -> None:
        self.git("add", "-A")
        completed = self.git("commit", "-q", "-m", message)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def tag(self, name: str = "abi-v1.0.0") -> None:
        completed = self.git("tag", name)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_first_release_without_tags(self) -> None:
        self.init()
        completed = run_gate(self.root, "--first-release")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "ABI baseline: first-release")

    def test_no_baseline_tag_requires_first_release(self) -> None:
        self.init()
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("没有可达的 abi-v* 基准标签", completed.stderr)

    def test_clean_header_matches_baseline(self) -> None:
        self.init()
        self.tag()
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_additive_requires_version_bump(self) -> None:
        self.init()
        self.tag()
        self.write(ADDITIVE)
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.strip(),
            "contracts/include/fmlcore.h: ABI-1 新增 ABI 需提升版本：新增函数 fml_extra",
        )

    def test_additive_with_minor_bump_passes(self) -> None:
        self.init()
        self.tag()
        self.write(with_minor(ADDITIVE))
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_breaking_requires_major_bump(self) -> None:
        self.init()
        self.tag()
        self.write(REMOVED)
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("破坏性变更需提升 ABI 主版本：删除函数 fml_context_create", completed.stdout)

    def test_breaking_allowed_with_major_bump(self) -> None:
        self.init()
        self.tag()
        self.write(with_major(REMOVED))
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_macro_value_change_is_breaking(self) -> None:
        self.init()
        self.tag()
        self.write(BASE.replace("#define FML_STATUS_KIND_COUNT 8", "#define FML_STATUS_KIND_COUNT 9"))
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("宏取值变化 FML_STATUS_KIND_COUNT", completed.stdout)

    def test_struct_append_field_with_minor_bump_passes(self) -> None:
        self.init()
        self.tag()
        self.write(with_minor(STRUCT_APPEND))
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_struct_insert_field_is_breaking(self) -> None:
        self.init()
        self.tag()
        self.write(with_minor(STRUCT_INSERT))
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("struct FmlBuf 字段被修改或重排", completed.stdout)

    def test_minor_regression_reports_line(self) -> None:
        self.init(with_minor(BASE))
        self.tag("abi-v1.1.0")
        self.write(BASE)
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.strip(), "contracts/include/fmlcore.h:5: ABI-1 ABI 次版本回退"
        )

    def test_major_regression_reports_line(self) -> None:
        self.init(with_major(BASE))
        self.tag("abi-v2.0.0")
        self.write(BASE)
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(
            completed.stdout.strip(), "contracts/include/fmlcore.h:4: ABI-1 ABI 主版本回退"
        )

    def test_base_ref_must_be_ancestor(self) -> None:
        self.init()
        self.tag()
        branch = self.git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.git("checkout", "-q", "-b", "side")
        self.write(BASE + "\n")
        self.commit("side")
        self.tag("abi-v1.2.0")
        self.git("checkout", "-q", branch)
        completed = run_gate(self.root, "--base-ref", "abi-v1.2.0")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("基准标签不是 HEAD 的祖先", completed.stderr)

    def test_base_ref_must_look_like_abi_tag(self) -> None:
        """文档标签（sadd-v*、archive/*）与裸版本号都不是 ABI 基准（条目 ⑲）。"""
        self.init()
        self.tag()
        for ref in ("sadd-v5.2.1", "archive/sadd-v4.0", "v1.0.0"):
            with self.subTest(ref=ref):
                completed = run_gate(self.root, "--base-ref", ref)
                self.assertEqual(completed.returncode, 2, completed.stdout)
                self.assertIn("基准必须是 abi-v", completed.stderr)

    def test_unparsable_base_ref_reports_gate(self) -> None:
        """名字合法但解析不到的基准退 2，不得当成无基准放过（条目 ⑳）。"""
        self.init()
        self.tag()
        completed = run_gate(self.root, "--base-ref", "abi-v9.9.9")
        self.assertEqual(completed.returncode, 2, completed.stdout)
        self.assertIn("基准标签不可解析", completed.stderr)

    def test_minor_reset_after_major_bump_is_allowed(self) -> None:
        """主版本提升后次版本可以归零（条目 ⑧）。"""
        self.init(BASE.replace("#define FML_ABI_MINOR 0", "#define FML_ABI_MINOR 3"))
        self.tag("abi-v1.3.0")
        self.write(with_major(BASE))
        self.commit("major bump resets minor")
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_first_release_rejected_when_tag_exists(self) -> None:
        self.init()
        self.tag()
        completed = run_gate(self.root, "--first-release")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("不能声明 --first-release", completed.stderr)

    def test_both_flags_are_rejected(self) -> None:
        self.init()
        self.tag()
        completed = run_gate(self.root, "--base-ref", "abi-v1.0.0", "--first-release")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--base-ref 与 --first-release 不能同时给出", completed.stderr)

    def test_function_like_macro_is_out_of_subset(self) -> None:
        self.init()
        self.write(BASE + "#define FML_ALIGN(x) ((x))\n")
        completed = run_gate(self.root, "--first-release")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("不支持函数式宏 FML_ALIGN", completed.stderr)

    def test_undef_is_out_of_subset(self) -> None:
        self.init()
        self.write(BASE + "#undef FML_ABI_MINOR\n")
        completed = run_gate(self.root, "--first-release")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("不支持的预处理指令 #undef", completed.stderr)

    def test_missing_header_is_gate_error(self) -> None:
        self.init()
        (self.root / HEADER).unlink()
        completed = run_gate(self.root, "--first-release")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("头文件不可读", completed.stderr)

    def test_crlf_header_matches_lf_baseline(self) -> None:
        self.init()
        self.tag()
        self.write(BASE.replace("\n", "\r\n"))
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_shallow_clone_requires_flag(self) -> None:
        self.init()
        self.tag()
        target = Path(tempfile.mkdtemp(prefix="core74-shallow-")) / "shallow"
        cloned = subprocess.run(
            ["git", "clone", "-q", "--depth", "1", self.root.as_uri(), str(target)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if cloned.returncode != 0:
            self.skipTest("环境不支持浅 clone：" + cloned.stderr.strip())
        completed = run_gate(target)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("浅 clone 缺少基准历史", completed.stderr)

    def test_comment_masking_keeps_shape(self) -> None:
        """注释里的声明文本与 `;`/`{}` 不参与 ABI 解析（`_sanitize` 在 B2 修复后仍必需）。

        若去掉字符串/注释遮罩，块注释里的 `typedef struct { int a; } Fake;` 会被当成
        新增 struct、注释里的 `extern "C" {` 会改变作用域，本用例随即报 ABI-1/ GATE-1。
        """
        self.init()
        self.tag()
        masked = BASE.replace(
            "#define FML_STATUS_KIND_COUNT 8\n",
            "#define FML_STATUS_KIND_COUNT 8\n"
            "/* 说明：typedef struct { int a; } Fake; extern \"C\" { */\n"
            "// 行注释：uint32_t fake_extra(void);\n",
        )
        self.assertNotEqual(masked, BASE)
        self.write(masked)
        completed = run_gate(self.root)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stdout.strip(), "")

    def test_real_repository_without_header_reports_gate(self) -> None:
        """真实树：CORE-03 头未落地时退 2 并报 GATE-1，不把「缺头」当通过（卡:16）。"""
        repo = CI_DIR.parents[1]
        if (repo / HEADER).is_file():
            self.skipTest("CORE-03 头已落地，真实 ABI 验收改由 abi-v* 基准标签覆盖")
        completed = run_gate(repo)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("GATE-1 头文件不可读", completed.stderr)
        self.assertEqual(completed.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
