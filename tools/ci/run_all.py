#!/usr/bin/env python3
"""CORE-41 单入口编排：按 manifest 顺序执行门禁脚本并聚合退出码。

命令行：`python tools/ci/run_all.py [--root .] [--manifest tools/ci/manifest.json]
[--out build/ci] [--release] [--only <id>]... [--step-timeout <秒>]`。

产物：`<out>/run_all.json`（steps 按 manifest 顺序，忽略时间字段后字节稳定）与
`<out>/pending.json`（`{version:1,items:[{card,target,reason}]}`）；终端最后一行为
`run_all: <n> steps, <e> error, <f> fail, <p> pending`。

判定顺序：先按目标存在性记 pending-target（不执行），再判定 error
（error_kind 非 null、exit 为 null 或 exit 不在 0/1 内，含解释器返回 2 与 3），
其余 exit 1 记 fail、exit 0 记 pass；任一步 error 则总退出 2，否则任一 1 则 1，
否则 0；--release 时存在 pending 也退出 1。--release 另附带 HA-002 窄消费者：
当次 maint 报告出现 `SAMPLE-WAIVER[HA-002]: ` 前缀即发布拒绝（总退出 1），
当次报告缺失、损坏或未由本轮更新按工具错误退出 2。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

MANIFEST_VERSION = 1
DEFAULT_MANIFEST = "tools/ci/manifest.json"
DEFAULT_OUT = "build/ci"
DEFAULT_DISCOVERY = "."
DEFAULT_STEP_TIMEOUT = 900
GRACE_SECONDS = 5.0
TAIL_LINES = 50
INTERPRETERS = ("python", "node")
DOCS_TOOL_OWNER = "SADD"
KINDS = ("card", "docs-tool")
STEP_KEYS = frozenset({"id", "owner", "kind", "target", "argv", "release_args"})
HA002_PREFIX = "SAMPLE-WAIVER[HA-002]: "
HA002_REPORT = "build/maint.json"
HA002_STEP = "maint-report"


class ManifestError(Exception):
    """manifest 结构不合法。"""


def _error(message: str) -> int:
    """打印工具错误并返回退出码 2。"""
    print(f"run_all: {message}", file=sys.stderr)
    return 2


def _str_list(value: Any, where: str) -> list[str]:
    """校验并复制字符串数组。"""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ManifestError(f"{where} 必须是字符串数组")
    return list(value)


def load_manifest(path: Path) -> list[dict[str, Any]]:
    """读取并严格校验 manifest，失败抛 ManifestError。"""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestError(f"无法读取 manifest {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ManifestError(f"manifest 不是合法 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("manifest 顶层必须是对象")
    version = data.get("version")
    if isinstance(version, bool) or version != MANIFEST_VERSION:
        raise ManifestError(f"manifest.version 必须为 {MANIFEST_VERSION}")
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list):
        raise ManifestError("manifest.steps 必须是数组")
    steps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_step in enumerate(raw_steps):
        where = f"steps[{index}]"
        if not isinstance(raw_step, dict):
            raise ManifestError(f"{where} 必须是对象")
        unknown = set(raw_step) - STEP_KEYS
        if unknown:
            raise ManifestError(f"{where} 含未知字段 {sorted(unknown)}")
        step_id = raw_step.get("id")
        if not isinstance(step_id, str) or not step_id:
            raise ManifestError(f"{where}.id 必须是非空字符串")
        if step_id in seen:
            raise ManifestError(f"id 重复: {step_id}")
        seen.add(step_id)
        owner = raw_step.get("owner")
        if not isinstance(owner, str) or not owner:
            raise ManifestError(f"{where}.owner 必须是非空字符串")
        kind = raw_step.get("kind", "card")
        if kind not in KINDS:
            raise ManifestError(f"{where}.kind 非 card/docs-tool: {kind!r}")
        if kind == "docs-tool" and owner != DOCS_TOOL_OWNER:
            raise ManifestError(f"{where}: docs-tool 步骤 owner 必须为 {DOCS_TOOL_OWNER}")
        if kind == "card" and owner == DOCS_TOOL_OWNER:
            raise ManifestError(f"{where}: card 步骤 owner 不得为 {DOCS_TOOL_OWNER}")
        argv = _str_list(raw_step.get("argv"), f"{where}.argv")
        if not argv:
            raise ManifestError(f"{where}.argv 不得为空")
        if argv[0] not in INTERPRETERS:
            raise ManifestError(f"{where}.argv[0] 只能是 python 或 node: {argv[0]!r}")
        release_args = _str_list(raw_step.get("release_args", []), f"{where}.release_args")
        target = raw_step.get("target")
        if target is not None and (not isinstance(target, str) or not target):
            raise ManifestError(f"{where}.target 必须是非空字符串")
        steps.append(
            {
                "id": step_id,
                "owner": owner,
                "kind": kind,
                "argv": argv,
                "release_args": release_args,
                "target": target,
            }
        )
    return steps


def _unittest_targets(root: Path, args: list[str]) -> list[str]:
    """把 python -m unittest 解析成真实测试文件（发现目录展开，0 个时回落目录本身）。

    发现目录展开后逐个文件判定存在性，避免该步因为去找不存在的 unittest.py 永久
    pending；目录内没有任何匹配测试文件时返回目录本身，它不满足“普通文件存在”，
    于是该步记 pending-target 而不是把 Ran 0 当通过。
    """
    if not args or args[0] != "discover":
        names = [item for item in args if not item.startswith("-")]
        return names or [DEFAULT_DISCOVERY]
    start = DEFAULT_DISCOVERY
    pattern = "test*.py"
    index = 1
    while index < len(args):
        item = args[index]
        if item in ("-s", "--start-directory") and index + 1 < len(args):
            start = args[index + 1]
            index += 2
        elif item in ("-p", "--pattern") and index + 1 < len(args):
            pattern = args[index + 1]
            index += 2
        elif item in ("-t", "--top-level-directory") and index + 1 < len(args):
            index += 2
        else:
            index += 1
    base = root / start
    found: list[str] = []
    if base.is_dir():
        for path in sorted(base.rglob(pattern)):
            if not path.is_file():
                continue
            # 与 unittest 一致：只有逐级包目录（含 __init__.py）才会被递归发现。
            parts = path.relative_to(base).parts[:-1]
            directory = base
            package = True
            for part in parts:
                directory = directory / part
                if not (directory / "__init__.py").is_file():
                    package = False
                    break
            if package:
                found.append(path.relative_to(root).as_posix())
    return found or [start]


def step_targets(step: dict[str, Any], root: Path) -> list[str]:
    """按卡片规则推定步骤目标路径（显式 target 优先）。"""
    if step["target"] is not None:
        return [step["target"]]
    argv = step["argv"]
    rest = argv[1:]
    if argv[0] == "python":
        if rest[:2] == ["-m", "unittest"]:
            return _unittest_targets(root, rest[2:])
        if rest[:1] == ["-m"] and len(rest) > 1:
            module = rest[1].replace(".", "/")
            return [module + ".py", module + "/__init__.py"]
        if rest and not rest[0].startswith("-"):
            return [rest[0]]
        return []
    if "--test" in rest:
        index = rest.index("--test")
        return [item for item in rest[index + 1 :] if not item.startswith("-")]
    if rest and not rest[0].startswith("-"):
        return [rest[0]]
    return []


def missing_targets(root: Path, step: dict[str, Any]) -> list[str]:
    """返回缺失目标路径；空表示该步 active。"""
    return [item for item in step_targets(step, root) if not (root / item).is_file()]


def _spawn_kwargs() -> dict[str, Any]:
    """子进程放入独立进程组，超时可终止整棵进程树。"""
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _terminate(pid: int, force: bool) -> None:
    """终止整棵进程树：POSIX 发信号给进程组，Windows 交给 taskkill /T。"""
    if os.name == "nt":
        command = ["taskkill", "/PID", str(pid), "/T"]
        if force:
            command.append("/F")
        try:
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except OSError:
            pass
        return
    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.killpg(os.getpgid(pid), sig)
    except OSError:
        pass


def tail(text: str) -> str:
    """取末 TAIL_LINES 行原文；行内字符不改写。"""
    if not text:
        return ""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines[-TAIL_LINES:])


def execute_step(
    step: dict[str, Any], root: Path, timeout: float, release: bool, pending_path: Path
) -> dict[str, Any]:
    """执行一个步骤，返回 exit/error_kind/duration_ms 与完整输出。"""
    argv = list(step["argv"])
    if release and step["release_args"]:
        argv = argv[:1] + argv[1:] + list(step["release_args"])
    interpreter = sys.executable if argv[0] == "python" else shutil.which("node")
    started = time.monotonic()
    if interpreter is None:
        return {
            "exit": None,
            "error_kind": "unavailable",
            "duration_ms": 0,
            "stdout": "",
            "stderr": f"run_all: 解释器缺失: {argv[0]}",
        }
    command = [interpreter] + argv[1:]
    # 内部登记通道只绑定本轮 out；不继承其他运行的 CORE_CI_PENDING。
    child_env = dict(os.environ, CORE_CI_PENDING=str(pending_path.resolve()))
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(root),
            env=child_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            **_spawn_kwargs(),
        )
    except OSError as exc:
        duration = int(round((time.monotonic() - started) * 1000))
        return {
            "exit": None,
            "error_kind": "unavailable",
            "duration_ms": duration,
            "stdout": "",
            "stderr": f"run_all: 无法启动 {argv[0]}: {exc}",
        }
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate(proc.pid, force=False)
        deadline = time.monotonic() + GRACE_SECONDS
        while time.monotonic() < deadline and proc.poll() is None:
            time.sleep(0.05)
        if proc.poll() is None:
            _terminate(proc.pid, force=True)
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
    duration = int(round((time.monotonic() - started) * 1000))
    return {
        "exit": None if timed_out else proc.returncode,
        "error_kind": "timeout" if timed_out else None,
        "duration_ms": duration,
        "stdout": out or "",
        "stderr": err or "",
    }


def _snapshot(path: Path) -> tuple[int, int] | None:
    """记录报告文件 (mtime_ns, size)，不存在返回 None。"""
    try:
        stat = path.stat()
    except OSError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


def _read_pending(path: Path) -> tuple[list[dict[str, str]], str | None]:
    """读取既有 pending 条目；不存在视为空，损坏按工具错误。"""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ([], None)
    except (OSError, UnicodeError) as exc:
        return ([], f"无法读取 {path.name}: {exc}")
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return ([], f"{path.name} 不是合法 JSON: {exc}")
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return ([], f"{path.name} 缺少 items 数组")
    collected: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            return ([], f"{path.name} 含非对象条目")
        if not all(isinstance(item.get(key), str) for key in ("card", "target", "reason")):
            return ([], f"{path.name} 条目缺少 card/target/reason")
        collected.append({"card": item["card"], "target": item["target"], "reason": item["reason"]})
    return (collected, None)


def _merge_pending(existing: list[dict[str, str]], own: list[dict[str, str]]) -> list[dict[str, str]]:
    """按 (card,target) 去重并排序。"""
    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, str]] = []
    for item in existing + own:
        key = (item["card"], item["target"])
        if key in seen:
            continue
        seen.add(key)
        merged.append({"card": item["card"], "target": item["target"], "reason": item["reason"]})
    merged.sort(key=lambda item: (item["card"], item["target"]))
    return merged


def _write_json(path: Path, payload: Any) -> None:
    """UTF-8 写 JSON（缩进 2、末行换行）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def ha002_verdict(
    root: Path, records: list[dict[str, Any]], before: tuple[int, int] | None
) -> tuple[int | None, str | None]:
    """HA-002 窄消费者：返回 (覆盖退出码, 诊断)；None 表示不干预。"""
    record = next((item for item in records if item["id"] == HA002_STEP), None)
    if record is None or record["_state"] == "pending":
        return (None, None)
    path = root / HA002_REPORT
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return (2, f"HA-002 消费：当次 maint 报告缺失（{HA002_REPORT}）")
    try:
        data = json.loads(raw)
    except ValueError:
        return (2, f"HA-002 消费：当次 maint 报告损坏（{HA002_REPORT}）")
    if before is not None and _snapshot(path) == before:
        return (2, "HA-002 消费：maint 报告未由本轮更新，旧报告不得顶替")
    violations = data.get("violations") if isinstance(data, dict) else None
    if not isinstance(violations, list):
        return (2, "HA-002 消费：当次 maint 报告缺少 violations 数组")
    for item in violations:
        message = item.get("message") if isinstance(item, dict) else None
        if isinstance(message, str) and message.startswith(HA002_PREFIX):
            return (1, f"HA-002 发布拒绝：当次 maint 报告含样品豁免标记（{HA002_PREFIX.strip()}）")
    return (None, None)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(prog="run_all", description="CORE-41 检查编排")
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--step-timeout", type=int, default=DEFAULT_STEP_TIMEOUT)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """执行全部步骤并返回聚合退出码。"""
    args = parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        return _error(f"--root 不是目录: {args.root}")
    if args.step_timeout <= 0:
        return _error("--step-timeout 必须为正整数")
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    try:
        steps = load_manifest(manifest_path)
    except ManifestError as exc:
        return _error(f"manifest 非法: {exc}")
    if args.only:
        known = {step["id"] for step in steps}
        unknown = [item for item in args.only if item not in known]
        if unknown:
            return _error("--only 未匹配 manifest 步骤: " + ",".join(unknown))
        wanted = set(args.only)
        steps = [step for step in steps if step["id"] in wanted]
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    pending_path = out_dir / "pending.json"
    for stale in (out_dir / "run_all.json", pending_path):
        try:
            stale.unlink()
        except FileNotFoundError:
            pass
    before = _snapshot(root / HA002_REPORT) if args.release else None
    records: list[dict[str, Any]] = []
    for step in steps:
        missing = missing_targets(root, step)
        if missing:
            reason = ",".join(missing)
            records.append(
                {
                    "id": step["id"],
                    "owner": step["owner"],
                    "exit": None,
                    "duration_ms": 0,
                    "error_kind": None,
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "_state": "pending",
                    "_reason": reason,
                }
            )
            print(f"[pending] {step['id']} ({step['owner']}) 缺少目标: {reason}")
            continue
        outcome = execute_step(step, root, args.step_timeout, args.release, pending_path)
        if outcome["stdout"]:
            sys.stdout.write(outcome["stdout"])
        if outcome["stderr"]:
            sys.stderr.write(outcome["stderr"])
        code = outcome["exit"]
        if outcome["error_kind"] is not None or code is None or code not in (0, 1):
            state = "error"
        elif code == 1:
            state = "fail"
        else:
            state = "pass"
        records.append(
            {
                "id": step["id"],
                "owner": step["owner"],
                "exit": code,
                "duration_ms": outcome["duration_ms"],
                "error_kind": outcome["error_kind"],
                "stdout_tail": tail(outcome["stdout"]),
                "stderr_tail": tail(outcome["stderr"]),
                "_state": state,
            }
        )
        print(
            f"[{state}] {step['id']} ({step['owner']}) exit={code} "
            f"error_kind={outcome['error_kind']} {outcome['duration_ms']}ms"
        )
    existing, pending_error = _read_pending(pending_path)
    if pending_error is not None:
        return _error(pending_error)
    own_pending = [
        {"card": item["owner"], "target": item["id"], "reason": item["_reason"]}
        for item in records
        if item["_state"] == "pending"
    ]
    merged = _merge_pending(existing, own_pending)
    _write_json(pending_path, {"version": 1, "items": merged})
    steps_doc = [
        {
            "id": item["id"],
            "owner": item["owner"],
            "exit": item["exit"],
            "duration_ms": item["duration_ms"],
            "error_kind": item["error_kind"],
            "stdout_tail": item["stdout_tail"],
            "stderr_tail": item["stderr_tail"],
        }
        for item in records
    ]
    _write_json(out_dir / "run_all.json", {"version": 1, "steps": steps_doc})
    errors = sum(1 for item in records if item["_state"] == "error")
    fails = sum(1 for item in records if item["_state"] == "fail")
    pendings = len(merged)
    total = 2 if errors else 1 if fails else 1 if (pendings and args.release) else 0
    if args.release:
        override, message = ha002_verdict(root, records, before)
        if message is not None:
            print(f"run_all: {message}", file=sys.stderr)
        if override is not None:
            total = max(total, override)
    print(f"run_all: {len(records)} steps, {errors} error, {fails} fail, {pendings} pending")
    return total


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
