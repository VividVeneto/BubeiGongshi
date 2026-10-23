#!/usr/bin/env python3
"""替身：原样回显参数，验证 argv 不经 shell 拼接、不展开通配。"""
import json
import sys

print(json.dumps(sys.argv[1:], ensure_ascii=False))
sys.exit(0)
