"""tools/ci/check_sadd.py 的自测（标准库 unittest，无需 pytest）。

覆盖 CORE-70 测试方案第 4 条：参数透传、退出码保留（0 无违例 / 1 违例 / 2 读写解析错误），
以及 --release 门禁对 acceptance_jobs.json 缺失的退出码 2。结构规则本身由
tools/sadd/structure.test.mjs 逐条覆盖，这里只用最小夹具验证入口转发。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_sadd.py"
BT = chr(96)
CARD_REL = "SADD/S0/S0_CORE-01_基座.md"

CARD = "\n".join([
    "### CORE-01 骨架",
    "",
    "**目标**：测试卡；Q1。",
    "",
    "**范围**",
    "- 包含：演示",
    "- 不包含：别的",
    "",
    "**依赖**：—",
    "",
    "**接口契约**",
    "见 [README](../README.md)。",
    "",
    "| 错误码 | 级别 | 可重试 | 触发条件 |",
    "| --- | --- | --- | --- |",
    "| " + BT + "DEMO_FAIL" + BT + " | error | 否 | 测试 |",
    "",
    "**实现约束**",
    "- 无",
    "",
    "**验收标准**：测试方案全文见 [Test/S0/S0_CORE-01_TEST.md](../Test/S0/S0_CORE-01_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。",
    "",
    "**规模**：约 100 行；仓库根。",
    "",
])

README = "\n".join([
    "# SADD：测试 v5.3.3",
    "",
    "## 4. 版本说明",
    "",
    "| 版本 | 日期 | 说明 |",
    "| --- | --- | --- |",
    "| **v5.3.3** | **2026-10-20** | **现行本地基线** |",
    "",
    "## 5. 需求基线",
    "",
    "| 编号 | 需求 | 卡 |",
    "| --- | --- | --- |",
    "| R01 | 需求一 | CORE-01 |",
    "",
    "## 6. 已确认与待确认事项",
    "",
    "| 编号 | 问题 | 影响模块 |",
    "| --- | --- | --- |",
    "| Q1 | 问题一 | CORE-01 |",
    "",
])

OVERVIEW_CORE = "\n".join([
    "# 01 公共核心 v5.3.3",
    "",
    "## 2. 建议实施顺序",
    "",
    "| 阶段 | 模块 | 出口 |",
    "| --- | --- | --- |",
    "| S0 骨架 | CORE-01 | x |",
    "",
    "## 3. 模块索引",
    "",
    "| 编号 | 名称 | 代码位置 | 直接依赖 | 预估规模 |",
    "| --- | --- | --- | --- | --- |",
    "| CORE-01 | 骨架 | 仓库根 | — | 100 |",
    "",
    "## 4. 模块卡",
    "",
    "<!-- sadd:card CORE-01 -->",
    "",
])

OVERVIEW_OTHER = "\n".join([
    "# 其他端 v5.3.3",
    "",
    "## 2. 建议实施顺序",
    "",
    "| 阶段 | 模块 | 出口 |",
    "| --- | --- | --- |",
    "",
])

TEST_PLAN = "\n".join([
    "# CORE-01 测试方案",
    "",
    "**验收标准**",
    "- [R01] 第一条验收",
    "",
])

CHECKS = {key: "pass" for key in ("a", "b", "c", "d", "e", "f", "g", "S1", "S2", "S3", "S4", "S5", "S6")}

APPENDIX = "\n".join([
    "# 附录D",
    "",
    "## D.10 现行卡表",
    "",
    "| 编号 | 阶段 | v5.3.3 复核 | 当前状态 |",
    "| --- | --- | --- | --- |",
    "| CORE-01 | S0 | B | 就绪（D.12 P2-CORE-01） |",
    "",
    "## D.12 复核记录",
    "",
    "| 记录 | 卡 | 复核人 / 日期 | 复核输入字符 / 段 | a～g | S1～S6 | 发现、处理及调用方确认 | conclusion |",
    "| --- | --- | --- | --- | --- | --- | --- | --- |",
    "| P2-CORE-01 | CORE-01 | r1 / 2026-10-22 | 10 / 1 | PPPPPPP | PPPPPP | 无 | pass |",
    "",
    "## D.13 其他",
    "",
    "无。",
    "",
])

REVIEWS = {
    "version": 1,
    "entries": [{
        "record": "P2-CORE-01", "card": "CORE-01", "grade": "B", "reviewer": "r1",
        "date": "2026-10-22", "materialChars": 10, "segments": 1, "checks": CHECKS,
        "blockers": [], "conclusion": "pass", "consumerConfirmation": None, "history": [],
    }],
}

REGISTRY = "\n".join([
    "registry_version: 1",
    "entries:",
    "  - code: DEMO_FAIL",
    "    severity: error",
    "    surface: client",
    "",
])

CI_YML = "\n".join(["name: ci", "on: [push]", "jobs:", "  build:", "    runs-on: windows-latest", ""])

FILES = {
    CARD_REL: CARD,
    "SADD/README.md": README,
    "SADD/core/00-总览.md": OVERVIEW_CORE,
    "SADD/and/00-总览.md": OVERVIEW_OTHER.replace("其他端", "02 Android 端"),
    "SADD/win/00-总览.md": OVERVIEW_OTHER.replace("其他端", "03 Windows 端"),
    "SADD/Test/S0/S0_CORE-01_TEST.md": TEST_PLAN,
    "SADD/附录D-编码就绪检查记录.md": APPENDIX,
    "SADD/reports/v5.3.3-reviews.json": json.dumps(REVIEWS, ensure_ascii=False, indent=2),
    "contracts/errors/registry.yaml": REGISTRY,
    "contracts/dto/manifest.json": json.dumps({"version": 1, "ops": []}, ensure_ascii=False),
    "contracts/policies/shared-writes.json": json.dumps({"version": 1, "entries": []}, ensure_ascii=False),
    ".github/workflows/ci.yml": CI_YML,
}


def make_repo(root: Path) -> None:
    """写入最小合法夹具（结构与 tools/sadd/structure.test.mjs 同构）。"""
    for rel, text in FILES.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))


@unittest.skipUnless(shutil.which("node"), "PATH 上没有 node")
class CheckSaddEntry(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        make_repo(self.root)
        self.out = self.root / "build/check-sadd"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_entry(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )

    def test_valid_fixture_exits_0_and_writes_structure_json(self) -> None:
        done = self.run_entry("--root", str(self.root), "--out", str(self.out))
        self.assertEqual(done.returncode, 0, done.stderr)
        payload = json.loads((self.out / "structure.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["findings"], [])
        self.assertIn("共 0 项违例", done.stdout)

    def test_violation_exits_1(self) -> None:
        card = self.root / CARD_REL
        card.write_text(card.read_text(encoding="utf-8").replace("**实现约束**\n- 无\n\n", ""), encoding="utf-8")
        done = self.run_entry("--root", str(self.root), "--out", str(self.out))
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertIn("SADD-1 missing field 实现约束", done.stdout)

    def test_unknown_argument_exits_2(self) -> None:
        done = self.run_entry("--root", str(self.root), "--unknown")
        self.assertEqual(done.returncode, 2)
        self.assertIn("未知参数", done.stderr)

    def test_missing_material_dir_exits_2(self) -> None:
        done = self.run_entry("--root", str(self.root), "--material", str(self.root / "NOWHERE"), "--out", str(self.out))
        self.assertEqual(done.returncode, 2)
        self.assertIn("material", done.stderr)

    def test_release_without_acceptance_jobs_exits_2(self) -> None:
        done = self.run_entry("--root", str(self.root), "--release", "--out", str(self.out))
        self.assertEqual(done.returncode, 2)
        self.assertIn("acceptance_jobs.json", done.stderr)


if __name__ == "__main__":
    unittest.main()
