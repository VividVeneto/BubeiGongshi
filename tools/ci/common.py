#!/usr/bin/env python3
"""CORE-69 阶段1：门禁脚本共用的数据类型、GATE-1 通道与入口收敛。

Finding、Token、GateError、emit、run、main 与 GATE-1 规则号在仓库里只在此处定义，
CORE-74 与 CORE-71 只导入这些符号、不复制类型、不另写词法层（卡 S0_CORE-69:12）。

退出码：0 无 Finding，1 有 Finding，2 输入/配置/环境错误（唯一通道 GateError）。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_GATE = 2

RULE_GATE = "GATE-1"

KIND_CODE = "code"
KIND_STRING = "string"
KIND_COMMENT = "comment"

_MODULE_DIR = Path(__file__).resolve().parent
_INTERPRETERS = {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}


@dataclass(frozen=True)
class Finding:
    """一条门禁结果：path 为仓库相对 POSIX 路径，line 为 1 基行号，文件级为 None。"""

    path: str
    line: int | None
    rule: str
    message: str

    def format(self) -> str:
        """按终端约定渲染：行级带 :line 段，文件级不带。"""
        if self.line is None:
            return f"{self.path}: {self.rule} {self.message}"
        return f"{self.path}:{self.line}: {self.rule} {self.message}"


@dataclass(frozen=True)
class Token:
    """词法单元：text 是原文切片，offset 是 0 基 UTF-8 字节偏移，line 1 基取起始行。"""

    text: str
    offset: int
    line: int
    kind: str


class GateError(Exception):
    """退出码 2 的唯一通道；path 为 None 表示与文件无关的参数/环境错误。"""

    rule = RULE_GATE

    def __init__(self, path: str | None, message: str) -> None:
        super().__init__(message)
        self.path = path
        self.message = message

    def format_line(self) -> str:
        """渲染 stderr 单行：<path>: GATE-1 <message>，无路径时以 - 占位。"""
        where = self.path if self.path is not None else "-"
        return f"{where}: {self.rule} {self.message}"


def emit(findings: Sequence[Finding]) -> int:
    """逐行打印 Finding，返回 1；无 Finding 时返回 0。"""
    items = list(findings)
    for finding in items:
        print(finding.format())
    return EXIT_FINDINGS if items else EXIT_OK


def main(cli: Callable[[], Iterable[Finding]]) -> int:
    """执行检查体并收敛：先收集 Finding 再打印，GateError 只写 stderr 一行并返回 2。"""
    try:
        findings = list(cli())
    except BaseException as exc:  # 需区分 GATE-1 与真实缺陷，后者原样抛出
        line = _gate_line(exc)
        if line is None:
            raise
        print(line, file=sys.stderr)
        return EXIT_GATE
    return emit(findings)


def run(argv: Sequence[str]) -> tuple[int, str, str]:
    """以数组参数运行一个检查脚本（不经 shell），返回 (退出码, stdout, stderr)。

    argv[0] 是脚本路径，允许带 python/python3 前缀（CI 步骤里写法不同）；
    脚本抛 GateError 时丢弃已产出的 stdout，只返回单行 stderr，退出码 2。
    """
    args = [str(item) for item in argv]
    if args and Path(args[0]).name.lower() in _INTERPRETERS:
        args = args[1:]
    if not args:
        return _gate_result(GateError(None, "缺少脚本路径"))
    script = Path(args[0])
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            module = _load_script(script)
            code = module.main(args[1:])
    except BaseException as exc:
        line = _gate_line(exc)
        if line is None:
            raise
        return EXIT_GATE, "", line + "\n"
    return int(code), out.getvalue(), err.getvalue()


def _gate_result(error: GateError) -> tuple[int, str, str]:
    return EXIT_GATE, "", error.format_line() + "\n"


def _load_script(script: Path) -> types.ModuleType:
    """按文件载入检查脚本；找不到脚本、载入失败或无 main 都收敛成 GateError。"""
    if not script.is_file():
        raise GateError(None, f"脚本不存在：{script}")
    for directory in (script.parent, _MODULE_DIR):
        entry = str(directory)
        if entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)
    spec = importlib.util.spec_from_file_location(f"_gate69_script_{script.stem}", script)
    if spec is None or spec.loader is None:
        raise GateError(None, f"无法载入脚本：{script}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except BaseException as exc:
        if _gate_line(exc) is not None:
            raise
        raise GateError(None, f"脚本载入失败：{type(exc).__name__}: {exc}") from exc
    if not callable(getattr(module, "main", None)):
        raise GateError(None, f"脚本没有 main：{script}")
    return module


def _gate_line(exc: BaseException) -> str | None:
    """识别 GATE-1 异常并渲染单行；同一脚本可能以两个模块名导入，故按属性判定。"""
    if isinstance(exc, GateError):
        return exc.format_line()
    path = getattr(exc, "path", None)
    message = getattr(exc, "message", None)
    if getattr(exc, "rule", None) == RULE_GATE and isinstance(message, str):
        where = path if path is not None else "-"
        return f"{where}: {RULE_GATE} {message}"
    return None
