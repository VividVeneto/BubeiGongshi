#!/usr/bin/env python3
"""CORE-41 领域源码集合生成：按 CORE-71 覆盖率协议从 git 已跟踪文件取集合。

命令行：`python tools/ci/core_sources.py --root . --out build/coverage/core-sources.json`。
集合 = CORE-01 领域 crate 表 13 个 crate 的 `crates/<name>/src` 下已跟踪 `.rs`
文件，加 `crates/fml-sync/src/merge.rs`；按字节序去重，排除任何路径分量
tests/fixtures 的文件与 `*.g.rs`，排除清单写到 stderr。集合为空时写空 paths、
退出 0 并在 pending.json 登记 core-sources 的 pending-target；非 git 仓库或 git
不可用退出 2。产物固定 `{version:1,paths:[仓库相对POSIX路径]}`。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DOMAIN_CRATES = (
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
)
SYNC_ONLY_FILES = ("crates/fml-sync/src/merge.rs",)
EXCLUDED_COMPONENTS = frozenset({"tests", "fixtures"})
PENDING_PATH = "build/ci/pending.json"
CORE_SOURCES_TARGET = "core-sources"
EMPTY_REASON = "领域源码集合为空：13 个领域 crate 与 crates/fml-sync/src/merge.rs 均无已跟踪 .rs 文件"


class CoreSourcesError(Exception):
    """git 不可用或目录不是仓库。"""


def git(root: Path, args: list[str]) -> str:
    """运行 git 并返回 stdout；失败抛 CoreSourcesError。"""
    try:
        result = subprocess.run(
            ["git", "-C", str(root)] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise CoreSourcesError(f"git 不可用: {exc}") from exc
    if result.returncode != 0:
        message = (result.stderr or "").strip().splitlines()
        detail = message[-1] if message else f"exit={result.returncode}"
        raise CoreSourcesError(f"git {' '.join(args)} 失败: {detail}")
    return result.stdout


def ensure_repository(root: Path) -> None:
    """确认 root 是 git 工作树。"""
    git(root, ["rev-parse", "--show-toplevel"])


def tracked_files(root: Path, path: str) -> list[str]:
    """按字面路径取已跟踪文件（不使用花括号、不以通配展开）。"""
    return [line.strip() for line in git(root, ["ls-files", "--", path]).splitlines() if line.strip()]


def exclusion_reason(path: str) -> str | None:
    """返回排除原因；None 表示收录。"""
    parts = path.split("/")
    if path.endswith(".g.rs"):
        return "生成产物 *.g.rs"
    if EXCLUDED_COMPONENTS.intersection(parts):
        return "路径分量 tests/fixtures"
    if not path.endswith(".rs"):
        return "非 .rs 文件"
    return None


def collect(root: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """收集候选并分类，返回 (收录路径, 排除清单)。"""
    candidates: list[str] = []
    for crate in DOMAIN_CRATES:
        candidates.extend(tracked_files(root, f"crates/{crate}/src"))
    for path in SYNC_ONLY_FILES:
        candidates.extend(item for item in tracked_files(root, path) if item == path)
    kept: list[str] = []
    excluded: list[tuple[str, str]] = []
    for path in candidates:
        reason = exclusion_reason(path)
        if reason is None:
            kept.append(path)
        else:
            excluded.append((path, reason))
    ordered = sorted(set(kept), key=lambda item: item.encode("utf-8"))
    return (ordered, excluded)


def write_json(path: Path, payload: object) -> None:
    """UTF-8 写 JSON（缩进 2、末行换行）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def register_pending(root: Path) -> None:
    """集合为空时在 pending.json 登记 core-sources 的 pending-target。"""
    path = root / PENDING_PATH
    items: list[dict[str, str]] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_items = data.get("items") if isinstance(data, dict) else None
        if isinstance(raw_items, list):
            items = [item for item in raw_items if isinstance(item, dict)]
    except (OSError, ValueError):
        items = []
    entry = {"card": "CORE-41", "target": CORE_SOURCES_TARGET, "reason": EMPTY_REASON}
    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in items + [entry]:
        card = item.get("card")
        target = item.get("target")
        reason = item.get("reason")
        if not all(isinstance(value, str) for value in (card, target, reason)):
            continue
        key = (card, target)
        if key in seen:
            continue
        seen.add(key)
        merged.append({"card": card, "target": target, "reason": reason})
    merged.sort(key=lambda item: (item["card"], item["target"]))
    write_json(path, {"version": 1, "items": merged})


def parse_args(argv: list[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(prog="core_sources", description="CORE-41 领域源码集合")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="build/coverage/core-sources.json")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """生成 core-sources.json 并返回退出码。"""
    args = parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"core_sources: --root 不是目录: {args.root}", file=sys.stderr)
        return 2
    out = Path(args.out)
    if not out.is_absolute():
        out = root / out
    try:
        ensure_repository(root)
        kept, excluded = collect(root)
    except CoreSourcesError as exc:
        print(f"core_sources: {exc}", file=sys.stderr)
        return 2
    for path, reason in excluded:
        print(f"core_sources: 排除 {path}（{reason}）", file=sys.stderr)
    write_json(out, {"version": 1, "paths": kept})
    print(f"core_sources: 收录 {len(kept)} 个文件，排除 {len(excluded)} 个", file=sys.stderr)
    if not kept:
        register_pending(root)
        print("core_sources: 集合为空，已登记 pending-target（core-sources）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
