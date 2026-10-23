#!/usr/bin/env python3
"""替身：输出一条 Finding 行后以退出码 1 结束。"""
import sys

print("crates/a/src/x.rs:12: DEP-1 msg")
sys.exit(1)
