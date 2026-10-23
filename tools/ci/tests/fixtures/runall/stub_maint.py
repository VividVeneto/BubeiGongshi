#!/usr/bin/env python3
"""替身：按环境变量写 maint 报告，供 HA-002 发布拒绝消费测试。

用法：stub_maint.py <报告 JSON 路径>
环境变量：RUNALL_MAINT（报告内容，空表示不写文件）、RUNALL_MAINT_EXIT（退出码）。
"""
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = os.environ.get("RUNALL_MAINT", "")
if payload:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
sys.exit(int(os.environ.get("RUNALL_MAINT_EXIT", "0")))
