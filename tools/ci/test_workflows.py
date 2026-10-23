"""CORE-41 CI 片段验收测试（ci.yml / weekly.yml / CODEOWNERS / acceptance_jobs.json）。"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CI = REPO / ".github/workflows/ci.yml"
WEEKLY = REPO / ".github/workflows/weekly.yml"
CODEOWNERS = REPO / ".github/CODEOWNERS"
ACCEPTANCE = REPO / "tools/ci/acceptance_jobs.json"
BASH = shutil.which("bash")


def load(path: Path) -> dict:
    """读取并解析 workflow（YAML 1.1 把 on: 解析为布尔键）。"""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def triggers(data: dict) -> dict:
    """取触发器节点，兼容 on 被解析为 True 的情况。"""
    return data.get("on", data.get(True)) or {}


def job_runs(data: dict, name: str) -> str:
    """拼接一个作业所有步骤的 run 文本。"""
    steps = data["jobs"][name].get("steps") or []
    return "\n".join(step.get("run", "") for step in steps)


@unittest.skipIf(yaml is None, "需要 PyYAML")
class WorkflowCase(unittest.TestCase):
    """ci.yml / weekly.yml 结构与关键命令。"""

    def test_ci_jobs_and_needs_chain(self):
        """ci.yml 固定 lint→test→checks→build→deny 的 needs 链。"""
        data = load(CI)
        self.assertEqual(list(data["jobs"]), ["lint", "test", "checks", "build", "deny"])
        self.assertEqual(data["jobs"]["lint"].get("needs") or [], [])
        self.assertEqual(data["jobs"]["test"]["needs"], "lint")
        self.assertEqual(data["jobs"]["checks"]["needs"], "test")
        self.assertEqual(data["jobs"]["build"]["needs"], "checks")
        self.assertEqual(data["jobs"]["deny"]["needs"], "build")
        on = triggers(data)
        self.assertIn("push", on)
        self.assertIn("pull_request", on)

    def test_ci_each_job_reads_locked_versions(self):
        """每个作业的开头都把 toolchain.py 的九键写进 GITHUB_ENV，不写字面版本。"""
        data = load(CI)
        for name in data["jobs"]:
            with self.subTest(job=name):
                text = job_runs(data, name)
                self.assertIn("tools/ci/toolchain.py --root . --format env", text)
                self.assertIn("$GITHUB_ENV", text)

    def test_ci_has_no_version_literals(self):
        """ci.yml 不出现三段式版本字面量，全部来自 env 表达式。"""
        text = CI.read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"\b\d+\.\d+\.\d+\b", text), [])

    def test_ci_swallows_no_errors(self):
        """ci.yml 不用 continue-on-error 或 || true 吞错。"""
        text = CI.read_text(encoding="utf-8")
        self.assertNotIn("continue-on-error", text)
        self.assertNotIn("|| true", text)
        self.assertNotIn("||true", text)

    def test_ci_key_commands(self):
        """关键命令落在对应作业：格式化/静态检查、覆盖率、聚合入口、deny。"""
        data = load(CI)
        lint = job_runs(data, "lint")
        self.assertIn("cargo fmt --all --check", lint)
        self.assertIn("cargo clippy --workspace --all-targets -- -D warnings", lint)
        self.assertIn("dart format", lint)
        self.assertIn("flutter analyze", lint)
        test = job_runs(data, "test")
        self.assertIn("cargo test --workspace", test)
        self.assertIn("cargo llvm-cov --workspace --all-targets --lcov", test)
        self.assertIn("build/coverage/core.lcov", test)
        self.assertIn("flutter test", test)
        checks = job_runs(data, "checks")
        self.assertIn('python -m unittest discover -s tools/ci -p "test_*.py"', checks)
        self.assertIn("python tools/ci/run_all.py", checks)
        # 「Ran 0 tests」不能当验收：发现目录必须显式给出，且当前确有匹配的测试文件。
        discovered = sorted((REPO / "tools" / "ci").glob("test_*.py"))
        self.assertGreaterEqual(
            len(discovered), 1, "checks 作业的 unittest 发现目录里没有测试文件"
        )
        self.assertIn('-s tools/ci', checks)
        deny = job_runs(data, "deny")
        self.assertIn("cargo deny check", deny)
        self.assertIn('--version "$CARGO_DENY"', deny)
        build = job_runs(data, "build")
        self.assertIn("windows-latest", json.dumps(data["jobs"]["build"].get("strategy")))
        self.assertIn("ctest", build)
        self.assertIn("flutter build apk --release", build)

    def test_weekly_triggers_and_jobs(self):
        """weekly.yml 每周一 03:00 定时并支持手动触发，含 maint/audit/fuzz 三作业。"""
        data = load(WEEKLY)
        on = triggers(data)
        self.assertEqual(on["schedule"], [{"cron": "0 3 * * 1"}])
        self.assertIn("workflow_dispatch", on)
        self.assertEqual(sorted(data["jobs"]), ["audit", "fuzz", "maint"])
        text = WEEKLY.read_text(encoding="utf-8")
        self.assertNotIn("continue-on-error", text)
        self.assertNotIn("|| true", text)
        self.assertEqual(re.findall(r"\b\d+\.\d+\.\d+\b", text), [])

    def test_weekly_maint_regenerates_and_compares(self):
        """maint 作业取上周构件做周对比，产 lcov→core-sources→maint_report 并回传。"""
        data = load(WEEKLY)
        maint = job_runs(data, "maint")
        self.assertIn("gh run download --name weekly-maint", maint)
        self.assertIn("--previous build/previous/maint.json", maint)
        self.assertIn("tools/ci/core_sources.py --root . --out build/coverage/core-sources.json", maint)
        self.assertIn("--lcov build/coverage/core.lcov", maint)
        self.assertIn("--core-sources build/coverage/core-sources.json", maint)
        self.assertIn("--annotations", maint)
        upload = [
            step for step in data["jobs"]["maint"]["steps"]
            if step.get("uses", "").startswith("actions/upload-artifact")
        ]
        self.assertEqual(len(upload), 1)
        self.assertEqual(upload[0]["with"]["name"], "weekly-maint")
        self.assertIn("build/maint.md", upload[0]["with"]["path"])

    def test_weekly_audit_archives_json(self):
        """audit 作业安装锁版 cargo-audit，导出 JSON 并归档。"""
        data = load(WEEKLY)
        audit = job_runs(data, "audit")
        self.assertIn('cargo install cargo-audit --version "$CARGO_AUDIT"', audit)
        self.assertIn("cargo audit --json", audit)
        self.assertIn("build/audit/cargo-audit.json", audit)
        upload = [
            step for step in data["jobs"]["audit"]["steps"]
            if step.get("uses", "").startswith("actions/upload-artifact")
        ]
        self.assertEqual(upload[0]["with"]["name"], "weekly-audit")
        self.assertEqual(upload[0].get("if"), "always()")

    def fuzz_script(self) -> str:
        """取 fuzz 作业里跑目标的那一步脚本。"""
        data = load(WEEKLY)
        for step in data["jobs"]["fuzz"]["steps"]:
            if "fuzz run" in step.get("run", ""):
                return step["run"]
        self.fail("weekly.yml 缺少 fuzz run 步骤")

    def run_fuzz(self, targets: list, cargo_body: str):
        """在临时目录用替身 cargo 执行 fuzz 脚本。"""
        root = Path(tempfile.mkdtemp(prefix="fuzz-")).resolve()
        self.addCleanup(shutil.rmtree, root, True)
        (root / "fuzz/fuzz_targets").mkdir(parents=True)
        for name in targets:
            (root / "fuzz/fuzz_targets" / (name + ".rs")).write_text("// target\n", encoding="utf-8")
        script = root / "run-fuzz.sh"
        script.write_text(self.fuzz_script(), encoding="utf-8")
        bindir = root / "bin"
        bindir.mkdir()
        cargo = bindir / "cargo"
        cargo.write_text(cargo_body, encoding="utf-8")
        cargo.chmod(0o755)
        summary = root / "summary.md"
        summary.write_text("", encoding="utf-8")
        env = dict(os.environ)
        env["PATH"] = os.pathsep.join([str(bindir), "/usr/bin", "/bin", "/mingw64/bin"])
        env["GITHUB_STEP_SUMMARY"] = str(summary)
        env["FUZZ_NIGHTLY"] = "nightly-test"
        proc = subprocess.run(
            [BASH, str(script)], cwd=str(root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=env,
        )
        return proc, root, summary

    def test_fuzz_crash_fails_job_and_archives_artifact(self):
        """替身 cargo 崩溃：脚本退出 1，并把崩溃目标写进 step summary 与归档目录。"""
        cargo = "\n".join(
            [
                "#!/usr/bin/env bash",
                'prefix=""',
                'for arg in "$@"; do',
                '  case "$arg" in',
                '    -artifact_prefix=*) prefix="${arg#-artifact_prefix=}" ;;',
                "  esac",
                "done",
                'if [ -n "$prefix" ]; then printf crash > "${prefix}crash-1"; fi',
                "exit 1",
                "",
            ]
        )
        proc, root, summary = self.run_fuzz(["alpha", "beta"], cargo)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertTrue((root / "build/fuzz/alpha/crash-1").exists())
        self.assertTrue((root / "build/fuzz/beta/crash-1").exists())
        text = summary.read_text(encoding="utf-8")
        self.assertIn("alpha", text)
        self.assertIn("beta", text)
        self.assertIn("崩溃", text)

    def test_fuzz_passes_when_no_targets(self):
        """没有 fuzz 目标时脚本退出 0（不因空 glob 报错）。"""
        proc, _root, summary = self.run_fuzz([], "#!/usr/bin/env bash\nexit 99\n")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(summary.read_text(encoding="utf-8"), "")

    def test_fuzz_passes_when_target_ok(self):
        """目标全部跑通时脚本退出 0，不写崩溃摘要。"""
        proc, root, summary = self.run_fuzz(["alpha"], "#!/usr/bin/env bash\nexit 0\n")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(summary.read_text(encoding="utf-8"), "")
        self.assertTrue((root / "build/fuzz/alpha").is_dir())


class RepositoryMetadataCase(unittest.TestCase):
    """CODEOWNERS / acceptance_jobs.json / shared-writes 登记。"""

    def test_codeowners_requires_two_owners_per_protected_path(self):
        """三个受保护目录各 ≥2 名不同 owner，并写明分支保护为人工步骤。"""
        text = CODEOWNERS.read_text(encoding="utf-8")
        rules = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            pattern, *owners = stripped.split()
            rules[pattern] = owners
        for pattern in ("/crates/fml-crypto/", "/crates/fml-sync/", "/contracts/"):
            with self.subTest(pattern=pattern):
                owners = rules.get(pattern, [])
                self.assertGreaterEqual(len(owners), 2)
                self.assertEqual(len(set(owners)), len(owners))
                for owner in owners:
                    self.assertTrue(owner.startswith("@"), owner)
        self.assertIn("manual", text)
        self.assertIn("required approvals=2", text)
        self.assertIn("CODEOWNERS", text)
        self.assertIn("占位", text)

    def test_acceptance_jobs_contract(self):
        """acceptance_jobs.json 冻结为 {version:1, rows:[]}。"""
        self.assertEqual(
            json.loads(ACCEPTANCE.read_text(encoding="utf-8")), {"version": 1, "rows": []}
        )

    def test_shared_writes_registers_ci_yml(self):
        """契约把 .github/workflows/ci.yml 的所有权登记给 CORE-41。"""
        data = json.loads(
            (REPO / "contracts/policies/shared-writes.json").read_text(encoding="utf-8")
        )
        entries = data.get("writes") or data.get("entries") or []
        hits = [
            entry for entry in entries
            if entry.get("key") == ".github/workflows/ci.yml" and entry.get("owner") == "CORE-41"
        ]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].get("kind"), "file")


if __name__ == "__main__":
    unittest.main()
