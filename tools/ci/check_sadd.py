#!/usr/bin/env python3
"""CI 入口（CORE-70）：把参数原样转给 tools/sadd/structure.mjs 并保留其退出码。

用法：python tools/ci/check_sadd.py --sadd SADD [--material <目录>] --out <目录> [--release]
退出码沿用 structure.mjs：0 无 error、1 存在违例、2 读写/解析错误（含找不到 node）。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "sadd" / "structure.mjs"


def main(argv: list[str]) -> int:
    """转发参数；返回子进程退出码，找不到 node 或无法启动时返回 2。"""
    node = shutil.which("node")
    if node is None:
        print("check-sadd: 找不到 node 可执行文件", file=sys.stderr)
        return 2
    try:
        done = subprocess.run([node, str(SCRIPT), *argv], check=False)
    except OSError as error:
        print(f"check-sadd: {error}", file=sys.stderr)
        return 2
    return done.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
