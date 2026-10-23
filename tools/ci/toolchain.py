#!/usr/bin/env python3
"""CORE-41 工具链锁版读取：输出九个版本键（env 供工作流写入环境，json 供脚本）。

命令行：`python tools/ci/toolchain.py --root . [--format env|json]`。
读取 `rust-toolchain.toml` 的 channel、`app/.flutter-version` 与
`tools/toolchain.versions`；只读取锁文件，不写入、不改写任何版本键，
缺文件或缺必需键退出 2，不回退默认版本。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RUST_TOOLCHAIN_FILE = "rust-toolchain.toml"
FLUTTER_VERSION_FILE = "app/.flutter-version"
VERSIONS_FILE = "tools/toolchain.versions"

CHANNEL_RE = re.compile(r'^\s*channel\s*=\s*"([^"]+)"\s*$')

VERSION_KEYS = (
    ("PYTHON_VERSION", "python"),
    ("NODE_VERSION", "node"),
    ("FUZZ_NIGHTLY", "fuzz_nightly"),
    ("CARGO_FUZZ", "cargo_fuzz"),
    ("CARGO_DENY", "cargo_deny"),
    ("CARGO_AUDIT", "cargo_audit"),
    ("CARGO_LLVM_COV", "cargo_llvm_cov"),
)

OUTPUT_ORDER = (
    "RUST_VERSION",
    "FLUTTER_VERSION",
    "PYTHON_VERSION",
    "NODE_VERSION",
    "FUZZ_NIGHTLY",
    "CARGO_FUZZ",
    "CARGO_DENY",
    "CARGO_AUDIT",
    "CARGO_LLVM_COV",
)


class ToolchainError(Exception):
    """锁文件缺失或必需键缺失。"""


def read_text(path: Path, display: str) -> str:
    """读取锁文件文本；不存在抛 ToolchainError。"""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ToolchainError(f"无法读取 {display}: {exc}") from exc


def parse_rust_channel(text: str) -> str | None:
    """取 rust-toolchain.toml 的 channel 字面值。"""
    for line in text.splitlines():
        match = CHANNEL_RE.match(line)
        if match is not None:
            return match.group(1)
    return None


def parse_single_line(text: str, display: str) -> str:
    """取单行版本文件的第一行非空内容。"""
    for line in text.splitlines():
        value = line.strip()
        if value:
            return value
    raise ToolchainError(f"{display} 没有版本内容")


def parse_versions(text: str) -> dict[str, str]:
    """解析 key=value 形式的锁版文件。"""
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def resolve(root: Path) -> dict[str, str]:
    """读取全部九键；缺文件或缺键抛 ToolchainError。"""
    versions_text = read_text(root / VERSIONS_FILE, VERSIONS_FILE)
    versions = parse_versions(versions_text)
    rust_text = read_text(root / RUST_TOOLCHAIN_FILE, RUST_TOOLCHAIN_FILE)
    channel = parse_rust_channel(rust_text)
    if channel is None:
        raise ToolchainError(f"{RUST_TOOLCHAIN_FILE} 缺少 channel 键")
    flutter = parse_single_line(
        read_text(root / FLUTTER_VERSION_FILE, FLUTTER_VERSION_FILE), FLUTTER_VERSION_FILE
    )
    resolved = {"RUST_VERSION": channel, "FLUTTER_VERSION": flutter}
    for output_key, source_key in VERSION_KEYS:
        value = versions.get(source_key)
        if value is None or value == "":
            raise ToolchainError(f"{VERSIONS_FILE} 缺少必需键 {source_key}=")
        resolved[output_key] = value
    return resolved


def render(resolved: dict[str, str], fmt: str) -> str:
    """按 env 或 json 格式渲染。"""
    if fmt == "json":
        ordered = {key: resolved[key] for key in OUTPUT_ORDER}
        return json.dumps(ordered, ensure_ascii=False, indent=2) + "\n"
    return "".join(f"{key}={resolved[key]}\n" for key in OUTPUT_ORDER)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(prog="toolchain", description="CORE-41 锁版读取")
    parser.add_argument("--root", default=".")
    parser.add_argument("--format", choices=("env", "json"), default="env")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """读取锁文件并输出九个版本键。"""
    args = parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"toolchain: --root 不是目录: {args.root}", file=sys.stderr)
        return 2
    try:
        resolved = resolve(root)
    except ToolchainError as exc:
        print(f"toolchain: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render(resolved, args.format))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
