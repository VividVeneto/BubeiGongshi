#!/usr/bin/env python3
"""替身：写 pending.json，模拟 core_sources 等步骤登记 pending-target。

用法：stub_pending.py <pending.json 路径> <内容>
"""
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(sys.argv[2], encoding="utf-8")
sys.exit(0)
