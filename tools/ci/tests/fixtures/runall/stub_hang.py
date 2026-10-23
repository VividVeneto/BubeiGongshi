#!/usr/bin/env python3
"""替身：派孙进程后挂起，供超时终止整棵进程树测试。

用法：stub_hang.py <孙进程 pid 文件>
"""
import subprocess
import sys
import time
from pathlib import Path

child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
Path(sys.argv[1]).write_text(str(child.pid), encoding="utf-8")
print(f"stub_hang: 已派孙进程 {child.pid}", flush=True)
time.sleep(600)
