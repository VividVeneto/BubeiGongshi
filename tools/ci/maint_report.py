#!/usr/bin/env python3
"""CORE-71 可维护性度量与阈值报告（maint_report）。

CLI（卡 S0_CORE-71:12）：
  python tools/ci/maint_report.py --root . --out <maint.md> [--previous <maint.json>]
      [--annotations] --lcov <core.lcov> --core-sources <core-sources.json>

本卡只做度量、阈值、LCOV 覆盖率与周比较：不采集覆盖率、不编排 CI 作业（CORE-41）、
不复制 CORE-74 的 unsafe/ABI 判据；unsafe/FFI 数量只入报告与周报对比，不参与退出码与阈值。
Rust 复杂度取锁定版本 lizard；Dart 复杂度用 CORE-69 词法 token 近似，只消费
Token.kind == "code" 的 token（注释与字符串字面量不计入），本卡不实现第二套词法器。

退出码：0 无违规；1 阈值违规（Dart 超阈值且 dart_ccn_warn_only=true 时只记录 warning）；
2 配置/输入/工具错误（唯一通道 common.GateError，stderr 单行 GATE-1，不打印半份报告）。

JSON 字段固定、不含时间戳；files 与 violations 按 path（同级按 line）排序，其余路径数组按
字节序升序，同一输入重复运行逐字节一致。

HA-002（工程样品局限，新 RL 待收回）：只对 crates/fml-error/src/codes.rs 的获准快照、在默认
800/15 下产生的 file-lines 与 rust-ccn 两项超限按样品豁免，这两项不计入退出码；真实度量与
两条原违规仍完整写入报告，message 前缀 SAMPLE-WAIVER[HA-002]: ，Markdown 显式声明，发布侧
（CORE-41 --release）必须按该前缀拒绝。其他路径、其他规则、覆盖率不足与工具错误一律不豁免；
快照、路径形态或阈值配置一变即自动回到严格判定。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Sequence

import common
import source_scan
from common import KIND_CODE, GateError, Token

NL = chr(10)

# 阈值四键（卡:14）：未知键、缺键、类型或范围不符、YAML 解析失败一律退出 2。
THRESHOLD_KEYS = ("file_max_lines", "fn_max_ccn", "core_line_coverage", "dart_ccn_warn_only")

# 领域集合（卡:18；CORE-01 领域 crate 表在 v5.3.4 的可读快照，运行时唯一来源是 CORE-01 表）。
DOMAIN_CRATES = (
    "fml-ast", "fml-latex", "fml-notation", "fml-units", "fml-type", "fml-eval",
    "fml-derive", "fml-typeset", "fml-export", "fml-srs", "fml-grade", "fml-study",
    "fml-crypto",
)
SYNC_MERGE_PATH = "crates/fml-sync/src/merge.rs"
GENERATED_REPORT_PATH = "crates/fml-error/src/codes.rs"

SOURCE_SUFFIXES = (".rs", ".dart")
MEASURE_ROOT_DIRS = ("crates", "app", "server")
SKIP_DIR_NAMES = frozenset({"build", "node_modules", ".dart_tool", "target", ".git", "temp"})

# HA-002 工程样品豁免（窄范围、集中、可整体删除）：只对本卡唯一生成物的获准快照、在默认
# 800/15 下产生的两个实际超限规则临时放行（temp/review/s0r4-ha002-astra/分析与推荐.md 推荐 B，
# 新 RL 待收回）。真实度量与原违规必须保留；不泛化到其他 generated 文件、不改阈值配置、
# 不新增 CLI 开关、环境变量或 JSON 字段。
HA002_PATH = GENERATED_REPORT_PATH
HA002_SNAPSHOT_SHA256 = "3c58d636b0a86d8c5164bc5dd4596118314bc0dc333d5b96b46f6c3c8d010c49"
HA002_WAIVED_RULES = ("file-lines", "rust-ccn")
HA002_DEFAULT_LIMITS = (800, 15)
HA002_MARKER = "SAMPLE-WAIVER[HA-002]: "

CONTROL_HEADS = frozenset({"if", "for", "while", "switch", "catch", "else", "do", "try", "assert"})
DECISION_WORDS = frozenset({"if", "for", "while", "catch"})

LCOV_KNOWN_PREFIXES = ("TN:", "SF:", "FN:", "FNDA:", "FNF:", "FNH:", "BRDA:", "BRF:",
                       "BRH:", "DA:", "LF:", "LH:")
IDENT_START = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_$")
IDENT_CHAR = IDENT_START | frozenset("0123456789")


@dataclass(frozen=True)
class Thresholds:
    """阈值配置：core_line_coverage 以精确有理数保存，判定不使用浮点。"""

    file_max_lines: int
    fn_max_ccn: int
    core_line_coverage: Fraction
    dart_ccn_warn_only: bool


@dataclass
class FunctionMetric:
    """Dart 近似复杂度的一个函数/闭包记录。"""

    name: str
    line: int
    ccn: int


@dataclass
class FileMetric:
    """单个源文件的度量结果：长度、最大圈复杂度与生成物标记。"""

    path: str
    lines: int
    max_ccn: int
    generated: bool


@dataclass(frozen=True)
class SampleWaiver:
    """HA-002 样品豁免判定：applied 为真时只放行获准路径的两个获准规则。"""

    path: str
    applied: bool
    reason: str
    snapshot_sha256: str | None

    def covers(self, rule: str, path: str) -> bool:
        """该违规是否落在获准范围内：精确路径 + 获准规则，两者同时成立才算豁免。"""
        return self.applied and path == self.path and rule in HA002_WAIVED_RULES


@dataclass
class LcovRecord:
    """一条 LCOV 记录：SF 路径、DA 行计数、可选 LF/LH 逐行声明。"""

    source: str
    lines: dict[int, int]
    declared_lf: int | None
    declared_lh: int | None


@dataclass
class CoverageResult:
    """覆盖率结果：命中数、可执行行总数、阈值判定与说明。"""

    hit: int
    total: int
    ratio: float | None
    missing: list[str]
    excluded: list[str]
    pending_target: bool
    passed: bool


def thresholds_path(root: Path) -> Path:
    """阈值文件固定位于 <root>/tools/ci/thresholds.yaml（本卡创建并读取）。"""
    return root / "tools" / "ci" / "thresholds.yaml"


def _load_yaml(text: str, path: str) -> object:
    """用 PyYAML 解析；缺 PyYAML 或语法错误都是配置错误（退出 2）。"""
    try:
        import yaml
    except ImportError as exc:  # 外部前提：tools/requirements.txt 锁定 PyYAML
        raise GateError(path, "缺少 PyYAML（见 tools/requirements.txt）") from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise GateError(path, "YAML 解析失败：" + str(exc).replace(NL, " ")) from exc


def _require_int(data: dict, key: str, path: str) -> int:
    """取正整数键；bool 是 int 子类，必须单独排除。"""
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise GateError(path, "阈值键 " + key + " 必须是整数")
    if value <= 0:
        raise GateError(path, "阈值键 " + key + " 必须大于 0")
    return value


def _require_ratio(data: dict, key: str, path: str) -> Fraction:
    """取 0 < x <= 1 的覆盖率阈值；支持 '2/3' 这类精确有理数写法。"""
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise GateError(path, "阈值键 " + key + " 必须是 0<x<=1 的数")
    try:
        ratio = Fraction(str(value).strip())
    except (ValueError, ZeroDivisionError) as exc:
        raise GateError(path, "阈值键 " + key + " 不是可解析的数：" + str(value)) from exc
    if ratio <= 0 or ratio > 1:
        raise GateError(path, "阈值键 " + key + " 必须满足 0 < x <= 1")
    return ratio


def load_thresholds(path: Path) -> Thresholds:
    """读取并校验阈值文件；缺键、未知键、类型或范围不符、解析失败一律退出 2。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GateError(str(path), "阈值文件不可读：" + (exc.strerror or type(exc).__name__)) from exc
    data = _load_yaml(text, str(path))
    if not isinstance(data, dict):
        raise GateError(str(path), "阈值文件顶层必须是映射")
    unknown = sorted(set(data) - set(THRESHOLD_KEYS))
    if unknown:
        raise GateError(str(path), "未知阈值键：" + ",".join(unknown))
    missing = [key for key in THRESHOLD_KEYS if key not in data]
    if missing:
        raise GateError(str(path), "缺少阈值键：" + ",".join(missing))
    warn_only = data["dart_ccn_warn_only"]
    if not isinstance(warn_only, bool):
        raise GateError(str(path), "阈值键 dart_ccn_warn_only 必须是布尔值")
    return Thresholds(
        file_max_lines=_require_int(data, "file_max_lines", str(path)),
        fn_max_ccn=_require_int(data, "fn_max_ccn", str(path)),
        core_line_coverage=_require_ratio(data, "core_line_coverage", str(path)),
        dart_ccn_warn_only=warn_only,
    )


def load_core_sources(path: Path) -> list[str]:
    """读取 core-sources.json；版本非 1、重复、未按字节序、越界路径都退出 2。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GateError(str(path), "core-sources 不可读：" + (exc.strerror or type(exc).__name__)) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GateError(str(path), "core-sources 不是合法 JSON：" + exc.msg) from exc
    if not isinstance(data, dict):
        raise GateError(str(path), "core-sources 顶层必须是对象")
    if data.get("version") != 1:
        raise GateError(str(path), "core-sources version 必须为 1")
    paths = data.get("paths")
    if not isinstance(paths, list) or any(not isinstance(item, str) for item in paths):
        raise GateError(str(path), "core-sources paths 必须是字符串数组")
    seen: set[str] = set()
    previous: bytes | None = None
    for item in paths:
        _require_relative_path(item, str(path))
        if item in seen:
            raise GateError(str(path), "core-sources paths 有重复路径：" + item)
        seen.add(item)
        key = item.encode("utf-8")
        if previous is not None and key <= previous:
            raise GateError(str(path), "core-sources paths 必须按字节序去重排序：" + item)
        previous = key
    return list(paths)


def _require_relative_path(value: str, origin: str) -> None:
    """仓库相对 POSIX 路径：拒绝绝对路径、反斜杠、上跳与空段。"""
    if not value or value.startswith("/") or "\\" in value:
        raise GateError(origin, "不是仓库相对 POSIX 路径：" + value)
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise GateError(origin, "路径含空段、当前目录或上跳：" + value)


def _token_end(token: Token) -> int:
    """token 的字节结束偏移：offset 加原文的 UTF-8 字节长度。"""
    return token.offset + len(token.text.encode("utf-8"))


def require_ordered_tokens(path: str, tokens: Sequence[Token]) -> None:
    """校验词法层交付的 token 流：偏移单调、互不重叠。

    CORE-69 的 tokens() 是唯一词法层；本卡只按 kind 投影，不修补其输出。若上游给出的
    流出现重叠（已知阶段1缺陷 B2），说明 code 投影会混入字面量文本，此时按工具错误退出 2，
    绝不据此产出看似正常的复杂度数字。
    """
    previous_end = 0
    for token in tokens:
        if token.offset < previous_end:
            raise GateError(path, "词法 token 流偏移不单调或相互重叠（位置 " + str(token.offset) + "）")
        previous_end = _token_end(token)


def code_chars(path: str, tokens: Sequence[Token]) -> list[tuple[str, int]]:
    """把 kind=code 的 token 投影成 (字符, 行号) 序列；不做任何字符串/注释识别。"""
    require_ordered_tokens(path, tokens)
    chars: list[tuple[str, int]] = []
    for token in tokens:
        if token.kind != KIND_CODE:
            continue
        if chars:
            chars.append((" ", token.line))  # 保留 token 边界，避免 void/f 与 else if 被粘成一个词
        for char in token.text:
            chars.append((char, token.line))
    return chars


def _atoms(chars: Sequence[tuple[str, int]]) -> list[tuple[str, int]]:
    """把 code 投影切成标识符与单字符/双字符运算符原子，保留行号。"""
    atoms: list[tuple[str, int]] = []
    index = 0
    size = len(chars)
    while index < size:
        char, line = chars[index]
        if char in " \t\r\n":
            index += 1
            continue
        if char in IDENT_START:
            cursor = index + 1
            while cursor < size and chars[cursor][0] in IDENT_CHAR:
                cursor += 1
            atoms.append(("".join(item[0] for item in chars[index:cursor]), line))
            index = cursor
            continue
        following = chars[index + 1][0] if index + 1 < size else ""
        if char == "&" and following == "&":
            atoms.append(("&&", line))
            index += 2
            continue
        if char == "|" and following == "|":
            atoms.append(("||", line))
            index += 2
            continue
        if char == "=" and following == ">":
            atoms.append(("=>", line))
            index += 2
            continue
        if char == "?" and following in ("?", "."):
            third = chars[index + 2][0] if index + 2 < size else ""
            eaten = 3 if following == "?" and third == "=" else 2
            atoms.append(("".join(item[0] for item in chars[index:index + eaten]), line))
            index += eaten
            continue
        atoms.append((char, line))
        index += 1
    return atoms


def _ternary_colon(atoms: Sequence[tuple[str, int]], start: int) -> bool:
    """判断 start 处的问号是否属于三元表达式：同层之后先遇到冒号而不是语句边界。"""
    depth = 0
    for atom, _line in atoms[start + 1:]:
        if atom in ("(", "["):
            depth += 1
        elif atom in (")", "]"):
            if depth == 0:
                return False
            depth -= 1
        elif atom in ("{", "}", ";"):
            if depth == 0:
                return False
        elif atom == "," and depth == 0:
            return False
        elif atom == ":" and depth == 0:
            return True
    return False


class _DartScan:
    """Dart 复杂度近似：按括号/花括号配对定位函数体，再按卡列出的判定点加分。

    这是近似而非精确 CFG（卡:16）。左花括号前紧邻右圆括号、且该括号对之间只有参数时
    才算函数体起点；控制关键字（if/for/while/switch/catch/else/do/try/assert）后的块不算
    函数头；箭头符号记为箭头函数或闭包并单独计分；无法判定的形态输出 warning 并列人工项。
    """

    def __init__(self, path: str, atoms: Sequence[tuple[str, int]]) -> None:
        self.path = path
        self.atoms = atoms
        self.frames: list[dict] = []
        self.parens: list[dict] = []
        self.last_closed: dict | None = None
        self.functions: list[FunctionMetric] = []
        self.warnings: list[str] = []

    def target(self) -> FunctionMetric | None:
        """当前最内层函数/闭包记录；不在函数体内时为 None。"""
        for frame in reversed(self.frames):
            if frame["fn"] is not None:
                return frame["fn"]
        return None

    def bump(self) -> None:
        """给最内层函数/闭包加一分；顶层代码不计分。"""
        fn = self.target()
        if fn is not None:
            fn.ccn += 1

    def push_block(self, fn: FunctionMetric | None) -> None:
        """压入一层作用域；fn 为 None 表示普通块。"""
        self.frames.append({"fn": fn, "arrow": False})

    def push_function(self, name: str, line: int) -> None:
        """压入一个函数体作用域，初值 1。"""
        fn = FunctionMetric(name=name, line=line, ccn=1)
        self.functions.append(fn)
        self.frames.append({"fn": fn, "arrow": False})

    def push_arrow(self, name: str, line: int) -> None:
        """压入箭头函数或闭包作用域，初值 1；在语句边界收口。"""
        fn = FunctionMetric(name=name, line=line, ccn=1)
        self.functions.append(fn)
        self.frames.append({"fn": fn, "arrow": True})

    def close_arrows(self) -> None:
        """语句或参数边界收口：弹出栈顶的箭头函数作用域。"""
        while self.frames and self.frames[-1]["arrow"]:
            self.frames.pop()

    def open_brace(self, index: int) -> None:
        """遇到左花括号：识别函数体起点或普通块。"""
        line = self.atoms[index][1]
        cursor = index - 1
        while cursor > 0 and self.atoms[cursor][0] in ("async", "sync", "*"):
            cursor -= 1
        previous = self.atoms[cursor][0] if cursor >= 0 else ""
        group = self.last_closed
        if previous == ")" and group is not None and group["close"] == cursor:
            head = group["head"]
            if head in CONTROL_HEADS:
                self.push_block(None)
                return
            if not group["flat"]:
                self.warnings.append("无法判定函数头：第 " + str(line) + " 行括号内含语句或花括号，按普通块处理")
                self.push_block(None)
                return
            self.push_function(head if head else "(closure)", line)
            return
        self.push_block(None)

    def open_arrow(self, index: int) -> None:
        """遇到箭头符号：记为箭头函数或闭包，名字取前一个标识符（若有）。"""
        line = self.atoms[index][1]
        name = "(arrow)"
        if index:
            previous = self.atoms[index - 1][0]
            if previous and previous[0] in IDENT_START:
                name = previous
        self.push_arrow(name, line)

    def scan(self) -> list[FunctionMetric]:
        """单遍扫描：维护花括号/圆括号栈并在判定点加分。"""
        atoms = self.atoms
        for index, (atom, line) in enumerate(atoms):
            if atom == "(":
                previous = atoms[index - 1][0] if index else ""
                head = previous if previous and previous[0] in IDENT_START else ""
                self.parens.append({"flat": True, "head": head, "close": -1})
                continue
            if atom == ")":
                if self.parens:
                    group = self.parens.pop()
                    group["close"] = index
                    self.last_closed = group
                self.close_arrows()
                continue
            if atom in (";", ",", "[", "]"):
                self.close_arrows()
                if atom == ";":
                    for group in self.parens:
                        group["flat"] = False
                continue
            if atom == "{":
                self.open_brace(index)
                continue
            if atom == "}":
                if self.frames:
                    self.frames.pop()
                else:
                    self.warnings.append("无法判定函数头：第 " + str(line) + " 行出现多余的右花括号")
                continue
            if atom == "=>":
                self.open_arrow(index)
                continue
            if atom in DECISION_WORDS or atom == "case" or atom in ("&&", "||"):
                self.bump()
            elif atom == "?" and _ternary_colon(atoms, index):
                self.bump()
        if self.frames:
            self.warnings.append("无法判定函数头：文件结束时仍有 " + str(len(self.frames)) + " 层花括号未闭合")
        return self.functions


def dart_functions(path: str, tokens: Sequence[Token]) -> tuple[list[FunctionMetric], list[str]]:
    """返回 Dart 文件的近似函数表与人工项 warning。"""
    atoms = _atoms(code_chars(path, tokens))
    scan = _DartScan(path, atoms)
    return scan.scan(), scan.warnings


def _iter_sources(root: Path) -> list[tuple[str, Path]]:
    """按字节序列出待度量源文件：只取 crates/app/server 下的 .rs 与 .dart。

    生成物 *.g.dart 不入表（卡:16 的唯一排除项）；crates/fml-error/src/codes.rs 入表并标
    generated=true。不做目录外遍历，不依赖文件系统返回顺序。
    """
    found: list[tuple[str, Path]] = []
    for name in MEASURE_ROOT_DIRS:
        base = root / name
        if not base.is_dir():
            continue
        for candidate in base.rglob("*"):
            if not candidate.is_file():
                continue
            relative_parts = candidate.relative_to(root).parts
            if any(part in SKIP_DIR_NAMES for part in relative_parts):
                continue
            if candidate.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            relative = PurePosixPath(*relative_parts).as_posix()
            if relative.endswith(".g.dart"):
                continue
            found.append((relative, candidate))
    found.sort(key=lambda item: item[0].encode("utf-8"))
    return found


def _count_lines(data: bytes) -> int:
    """物理行数：换行符个数，末行无换行时补 1；空文件为 0。"""
    if not data:
        return 0
    total = data.count(b"\n")
    if not data.endswith(b"\n"):
        total += 1
    return total


def _lizard_max_ccn(path: Path) -> int:
    """用锁定版本的 lizard 求 Rust 文件最大圈复杂度；缺工具或分析失败退出 2。"""
    try:
        import lizard
    except ImportError as exc:
        raise GateError(None, "缺少 lizard（见 tools/requirements.txt）") from exc
    try:
        info = lizard.analyze_file(str(path))
    except Exception as exc:  # lizard 对异常输入抛各种异常，统一收敛为工具错误
        reason = type(exc).__name__ + ": " + str(exc).replace(NL, " ")
        raise GateError(str(path), "lizard 分析失败：" + reason) from exc
    if info is None:
        raise GateError(str(path), "lizard 未返回分析结果")
    return max((item.cyclomatic_complexity for item in info.function_list), default=0)


def measure_files(root: Path) -> tuple[list[FileMetric], dict[str, list[Token]], list[str]]:
    """度量文件长度与最大圈复杂度，返回度量表、token 流缓存与人工项 warning。"""
    metrics: list[FileMetric] = []
    cache: dict[str, list[Token]] = {}
    warnings: list[str] = []
    for relative, absolute in _iter_sources(root):
        try:
            data = absolute.read_bytes()
        except OSError as exc:
            reason = exc.strerror or type(exc).__name__
            raise GateError(relative, "无法读取文件：" + reason) from exc
        language = source_scan.LANGUAGE_BY_SUFFIX.get(absolute.suffix.lower())
        stream = source_scan.tokens(absolute, language)
        cache[relative] = stream
        require_ordered_tokens(relative, stream)
        if language == "rust":
            max_ccn = _lizard_max_ccn(absolute)
        else:
            functions, file_warnings = dart_functions(relative, stream)
            warnings.extend(file_warnings)
            max_ccn = max((item.ccn for item in functions), default=0)
        metrics.append(FileMetric(path=relative, lines=_count_lines(data), max_ccn=max_ccn,
                                  generated=relative == GENERATED_REPORT_PATH))
    return metrics, cache, warnings


def snapshot_sha256(path: Path) -> str:
    """获准快照指纹：CRLF→LF 规范化后的 SHA256（不删空白/注释、不重写源文件）。"""
    try:
        data = path.read_bytes()
    except OSError as exc:
        reason = exc.strerror or type(exc).__name__
        raise GateError(str(path), "无法读取生成物快照：" + reason) from exc
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _is_plain_file(path: Path) -> bool:
    """获准路径必须是普通文件：符号链接、目录与其他类型一律不豁免。"""
    return path.is_file() and not path.is_symlink()


def evaluate_sample_waiver(root: Path, metrics: Sequence[FileMetric],
                           thresholds: Thresholds) -> SampleWaiver:
    """判定 HA-002 样品豁免是否适用；任何一项不成立都按原配置严格判定。

    判定项（全部成立才应用）：精确仓库相对路径、既定生成物识别出的 generated=true、
    普通非符号链接文件、LF 规范化快照指纹一致、阈值仍为默认 800/15。任一变化都只记录
    未应用原因并回到严格阈值，不自动续期、不更新指纹。
    """
    metric = next((item for item in metrics if item.path == HA002_PATH), None)
    if metric is None:
        return SampleWaiver(HA002_PATH, False, "获准路径不在本次度量表内", None)
    if not metric.generated:
        return SampleWaiver(HA002_PATH, False, "获准路径未由既定生成物识别标为 generated", None)
    absolute = root / HA002_PATH
    if not _is_plain_file(absolute):
        return SampleWaiver(HA002_PATH, False, "获准路径不是普通非符号链接文件", None)
    snapshot = snapshot_sha256(absolute)
    if snapshot != HA002_SNAPSHOT_SHA256:
        return SampleWaiver(HA002_PATH, False, "HA-002 快照不匹配，豁免未应用", snapshot)
    if (thresholds.file_max_lines, thresholds.fn_max_ccn) != HA002_DEFAULT_LIMITS:
        return SampleWaiver(HA002_PATH, False, "阈值非默认 800/15，按配置严格判定", snapshot)
    return SampleWaiver(HA002_PATH, True,
                        "仅获准路径的 file-lines 与 rust-ccn 两项超限按工程样品放行", snapshot)


def _word_positions(text: str, word: str) -> list[int]:
    """返回 word 在 text 中按标识符边界出现的位置。"""
    positions: list[int] = []
    start = 0
    while True:
        index = text.find(word, start)
        if index < 0:
            return positions
        before = text[index - 1] if index else ""
        after = text[index + len(word)] if index + len(word) < len(text) else ""
        if (not before or before not in IDENT_CHAR) and (not after or after not in IDENT_CHAR):
            positions.append(index)
        start = index + len(word)


def _comment_before(tokens: Sequence[Token], index: int) -> bool:
    """token[index] 之前紧邻的注释里是否有以 SAFETY: 开头的非空行。"""
    cursor = index - 1
    while cursor >= 0 and tokens[cursor].kind == "comment":
        for line in tokens[cursor].text.splitlines():
            stripped = line.strip().lstrip("/").strip()
            if stripped.startswith("SAFETY:"):
                return True
        cursor -= 1
    return False


def count_unsafe_ffi(tokens: Sequence[Token]) -> dict:
    """按词法 token 统计 unsafe 与 FFI 形态；只入报告与周报对比，不参与退出码。"""
    blocks = 0
    safety_missing = 0
    extern_c_blocks = 0
    exported_symbols = 0
    for index, token in enumerate(tokens):
        if token.kind != "code":
            continue
        text = token.text
        for _position in _word_positions(text, "unsafe"):
            blocks += 1
            if not _comment_before(tokens, index):
                safety_missing += 1
        for _position in _word_positions(text, "extern"):
            following = tokens[index + 1] if index + 1 < len(tokens) else None
            if following is not None and following.kind == "string" and following.text.strip().lower() == '"c"':
                after = tokens[index + 2] if index + 2 < len(tokens) else None
                if after is not None and after.kind == "code" and after.text.lstrip().startswith(("{", "fn")):
                    extern_c_blocks += 1
        if re.search(r"#\[\s*(no_mangle|export_name)", text):
            tail = ""
            for offset in (1, 2, 3):
                if index + offset < len(tokens) and tokens[index + offset].kind == "code":
                    tail += tokens[index + offset].text
            if "extern" in tail:
                exported_symbols += 1
    return {
        "blocks": blocks,
        "safety_missing": safety_missing,
        "extern_c_blocks": extern_c_blocks,
        "exported_symbols": exported_symbols,
    }


def _normalize_source(value: str, root: Path, origin: str) -> str:
    """把 SF 规范化为 root 内相对 POSIX 路径；越界一律退出 2。"""
    cleaned = value.strip().replace("\\", "/")
    if not cleaned:
        raise GateError(origin, "空的 SF 记录")
    if cleaned.startswith("/") or re.match(r"^[A-Za-z]:/", cleaned):
        try:
            relative = Path(cleaned).resolve().relative_to(root.resolve())
        except (OSError, ValueError) as exc:
            raise GateError(origin, "SF 越出 root：" + cleaned) from exc
        return relative.as_posix()
    parts = cleaned.split("/")
    if any(part == ".." for part in parts):
        raise GateError(origin, "SF 含上跳路径：" + cleaned)
    return "/".join(part for part in parts if part not in ("", "."))


def _parse_int(text: str, origin: str, what: str) -> int:
    """解析非负整数；非法或负数退出 2（不静默按 0 处理）。"""
    stripped = text.strip()
    if not re.fullmatch(r"-?[0-9]+", stripped):
        raise GateError(origin, what + " 不是整数：" + stripped)
    value = int(stripped)
    if value < 0:
        raise GateError(origin, what + " 为负数：" + stripped)
    return value


def parse_lcov(path: Path, root: Path) -> list[LcovRecord]:
    """解析 LLVM llvm-cov 导出的 LCOV；格式损坏、重复 DA/SF、越界路径退出 2。"""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise GateError(str(path), "LCOV 不可读：" + (exc.strerror or type(exc).__name__)) from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError(str(path), "LCOV 不是合法 UTF-8（第 " + str(exc.start) + " 字节）") from exc
    origin = str(path)
    if not text.strip():
        raise GateError(origin, "LCOV 为空报告")
    records: list[LcovRecord] = []
    seen_sources: set[str] = set()
    source: str | None = None
    counts: dict[int, int] = {}
    declared_lf: int | None = None
    declared_lh: int | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith(LCOV_KNOWN_PREFIXES) and line != "end_of_record":
            raise GateError(origin, "LCOV 格式损坏：" + line[:40])
        if line.startswith("SF:"):
            if source is not None:
                raise GateError(origin, "上一条记录缺少 end_of_record")
            normalized = _normalize_source(line[3:], root, origin)
            if normalized in seen_sources:
                raise GateError(origin, "重复的 SF 记录：" + normalized)
            seen_sources.add(normalized)
            source = normalized
            counts = {}
            declared_lf = None
            declared_lh = None
            continue
        if line == "end_of_record":
            if source is None:
                raise GateError(origin, "end_of_record 前缺少 SF")
            hit = sum(1 for value in counts.values() if value > 0)
            if declared_lf is not None and declared_lf != len(counts):
                raise GateError(origin, "LF 与逐行计算不符：" + source)
            if declared_lh is not None and declared_lh != hit:
                raise GateError(origin, "LH 与逐行计算不符：" + source)
            records.append(LcovRecord(source=source, lines=counts, declared_lf=declared_lf,
                                      declared_lh=declared_lh))
            source = None
            continue
        if source is None:
            raise GateError(origin, "SF 之前的记录行：" + line[:40])
        if line.startswith("DA:"):
            fields = line[3:].split(",")
            if len(fields) < 2:
                raise GateError(origin, "DA 记录字段不足：" + line[:40])
            number = _parse_int(fields[0], origin, "DA 行号")
            if number == 0:
                raise GateError(origin, "DA 行号非法：" + line[:40])
            count = _parse_int(fields[1], origin, "DA 计数")
            if number in counts:
                raise GateError(origin, "重复的 DA 记录：" + source + ":" + str(number))
            counts[number] = count
            continue
        if line.startswith("LF:"):
            declared_lf = _parse_int(line[3:], origin, "LF")
            continue
        if line.startswith("LH:"):
            declared_lh = _parse_int(line[3:], origin, "LH")
    if source is not None:
        raise GateError(origin, "最后一条记录缺少 end_of_record")
    return records


def evaluate_coverage(records: Sequence[LcovRecord], core_paths: Sequence[str],
                      thresholds: Thresholds) -> CoverageResult:
    """按集合内 DA 唯一行计算覆盖率，并以 hit*den >= num*total 判定阈值。"""
    by_source = {record.source: record for record in records}
    wanted = set(core_paths)
    excluded = sorted((record.source for record in records if record.source not in wanted),
                      key=lambda item: item.encode("utf-8"))
    if not core_paths:
        return CoverageResult(hit=0, total=0, ratio=None, missing=[], excluded=excluded,
                              pending_target=True, passed=True)
    hit = 0
    total = 0
    without_lines: list[str] = []
    for relative in core_paths:
        record = by_source.get(relative)
        if record is None:
            raise GateError(None, "LCOV 缺少核心源文件记录：" + relative)
        if not record.lines:
            without_lines.append(relative)
            continue
        total += len(record.lines)
        hit += sum(1 for value in record.lines.values() if value > 0)
    if total == 0:
        raise GateError(None, "覆盖率分母为 0：集合内没有可执行行，不能按通过处理")
    numerator = thresholds.core_line_coverage.numerator
    denominator = thresholds.core_line_coverage.denominator
    passed = hit * denominator >= numerator * total
    return CoverageResult(hit=hit, total=total, ratio=hit / total, missing=without_lines,
                          excluded=excluded, pending_target=False, passed=passed)


def collect_violations(metrics: Sequence[FileMetric], thresholds: Thresholds,
                       coverage: CoverageResult, waiver: SampleWaiver) -> tuple[list[dict], int]:
    """生成违规列表与退出码：Dart 超阈值在 warn_only 时只记录 warning。

    HA-002 获准违规（精确路径 + 获准规则 + 判定已应用）保留在列表里，message 加固定前缀且
    不计入 blocking；其他任何违规照旧阻断。
    """
    violations: list[dict] = []
    blocking = 0

    def add(rule: str, path: str, message: str, blocks: bool) -> None:
        """登记一条违规：退出码只由未豁免的阻断项决定。"""
        nonlocal blocking
        waived = waiver.covers(rule, path)
        if blocks and not waived:
            blocking += 1
        violations.append({"rule": rule, "path": path, "line": None,
                           "message": HA002_MARKER + message if waived else message,
                           "waived": waived})

    for metric in metrics:
        if metric.lines > thresholds.file_max_lines:
            add("file-lines", metric.path,
                "文件长度 " + str(metric.lines) + " 超过 file_max_lines "
                + str(thresholds.file_max_lines), True)
        if metric.path.endswith(".rs") and metric.max_ccn > thresholds.fn_max_ccn:
            add("rust-ccn", metric.path,
                "Rust 最大圈复杂度 " + str(metric.max_ccn) + " 超过 fn_max_ccn "
                + str(thresholds.fn_max_ccn), True)
        if metric.path.endswith(".dart") and metric.max_ccn > thresholds.fn_max_ccn:
            add("dart-ccn", metric.path,
                "Dart 近似圈复杂度 " + str(metric.max_ccn) + " 超过 fn_max_ccn "
                + str(thresholds.fn_max_ccn), not thresholds.dart_ccn_warn_only)
    if not coverage.pending_target and not coverage.passed:
        add("coverage", "core-sources",
            "核心行覆盖率 " + str(coverage.hit) + "/" + str(coverage.total)
            + " 低于 core_line_coverage " + str(thresholds.core_line_coverage), True)
    violations.sort(key=lambda item: (item["path"].encode("utf-8"), item["line"] or 0, item["rule"]))
    return violations, 1 if blocking else 0


def build_document(metrics: Sequence[FileMetric], unsafe: dict, ffi: dict,
                   coverage: CoverageResult, violations: Sequence[dict]) -> dict:
    """按卡:12 的固定字段构造同名 JSON；不含任何时间字段。"""
    return {
        "version": 1,
        "files": [{"path": item.path, "lines": item.lines, "max_ccn": item.max_ccn,
                   "generated": item.generated} for item in metrics],
        "unsafe": {"blocks": unsafe["blocks"], "safety_missing": unsafe["safety_missing"],
                   "files": unsafe["files"]},
        "ffi": {"extern_c_blocks": ffi["extern_c_blocks"],
                "exported_symbols": ffi["exported_symbols"], "files": ffi["files"]},
        "coverage": {"hit": coverage.hit, "total": coverage.total, "ratio": coverage.ratio,
                     "missing": coverage.missing},
        "violations": [{"rule": item["rule"], "path": item["path"], "line": item["line"],
                        "message": item["message"]} for item in violations],
    }


def _escape_annotation(value: str, property_value: bool) -> str:
    """GitHub workflow command 转义；不写入源码行，只写规则名、阈值与实测值。"""
    text = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if property_value:
        text = text.replace(":", "%3A").replace(",", "%2C")
    return text


def format_annotations(violations: Sequence[dict], thresholds: Thresholds) -> list[str]:
    """把违规渲染成 GitHub path/line/rule 注解行；消息不含源代码。"""
    lines: list[str] = []
    for item in violations:
        if item.get("waived"):
            level = "warning"  # HA-002 获准违规：工程样品放行，仍显式展示
        elif item["rule"] == "dart-ccn" and thresholds.dart_ccn_warn_only:
            level = "warning"
        else:
            level = "error"
        properties = "file=" + _escape_annotation(item["path"], True)
        if item["line"] is not None:
            properties += ",line=" + str(item["line"])
        properties += ",title=" + _escape_annotation(item["rule"], True)
        lines.append("::" + level + " " + properties + "::" + _escape_annotation(item["message"], False))
    return lines


def load_previous(path: Path) -> dict:
    """读取上周报告 JSON；损坏、version 非 1、缺必需字段一律退出 2，不降级为 baseline。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GateError(str(path), "previous 不可读：" + (exc.strerror or type(exc).__name__)) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GateError(str(path), "previous 不是合法 JSON：" + exc.msg) from exc
    if not isinstance(data, dict):
        raise GateError(str(path), "previous 顶层必须是对象")
    if data.get("version") != 1:
        raise GateError(str(path), "previous version 必须为 1")
    required = ("files", "unsafe", "ffi", "coverage", "violations")
    missing = [key for key in required if key not in data]
    if missing:
        raise GateError(str(path), "previous 缺少字段：" + ",".join(missing))
    return data


def compare_reports(previous: dict, current: dict) -> list[str]:
    """周报对比：文件、覆盖率与违规的行级差异；输出稳定排序的文本行。"""
    lines: list[str] = []
    before = {item["path"]: item for item in previous["files"]}
    after = {item["path"]: item for item in current["files"]}
    added = sorted(set(after) - set(before), key=lambda item: item.encode("utf-8"))
    removed = sorted(set(before) - set(after), key=lambda item: item.encode("utf-8"))
    lines.append("- 文件数：" + str(len(before)) + " -> " + str(len(after))
                 + "（新增 " + str(len(added)) + "，移除 " + str(len(removed)) + "）")
    for path in added:
        lines.append("- 新增文件：" + path)
    for path in removed:
        lines.append("- 移除文件：" + path)
    for path in sorted(set(before) & set(after), key=lambda item: item.encode("utf-8")):
        old, new = before[path], after[path]
        if old.get("lines") != new.get("lines") or old.get("max_ccn") != new.get("max_ccn"):
            lines.append("- 度量变化：" + path + " 行数 " + str(old.get("lines")) + " -> "
                         + str(new.get("lines")) + "，max_ccn " + str(old.get("max_ccn")) + " -> "
                         + str(new.get("max_ccn")))
    old_cov = previous["coverage"]
    new_cov = current["coverage"]
    lines.append("- 覆盖率：" + str(old_cov.get("hit")) + "/" + str(old_cov.get("total")) + " -> "
                 + str(new_cov.get("hit")) + "/" + str(new_cov.get("total")))
    old_unsafe, new_unsafe = previous["unsafe"], current["unsafe"]
    lines.append("- unsafe：块 " + str(old_unsafe.get("blocks")) + " -> " + str(new_unsafe.get("blocks"))
                 + "，缺 SAFETY " + str(old_unsafe.get("safety_missing")) + " -> "
                 + str(new_unsafe.get("safety_missing")))
    old_ffi, new_ffi = previous["ffi"], current["ffi"]
    lines.append("- FFI：extern C " + str(old_ffi.get("extern_c_blocks")) + " -> "
                 + str(new_ffi.get("extern_c_blocks")) + "，导出符号 "
                 + str(old_ffi.get("exported_symbols")) + " -> " + str(new_ffi.get("exported_symbols")))
    old_rules = [item.get("rule") + " " + item.get("path") for item in previous["violations"]]
    new_rules = [item.get("rule") + " " + item.get("path") for item in current["violations"]]
    for item in sorted(set(new_rules) - set(old_rules)):
        lines.append("- 新增违规：" + item)
    for item in sorted(set(old_rules) - set(new_rules)):
        lines.append("- 消除违规：" + item)
    return lines


def _render_waiver(document: dict, thresholds: Thresholds, waiver: SampleWaiver) -> list[str]:
    """HA-002 段：显式声明样品限定、真实值与发布拒绝，放在报告开头而不是尾部。

    应用时正文必须能独立证明“这是工程样品豁免，不是原卡阈值达标”；未应用时给出原因，
    说明本次按配置严格判定，不自动续期。
    """
    entry = next((item for item in document["files"] if item["path"] == waiver.path), None)
    lines: list[str] = ["## HA-002 工程样品豁免（" + ("已应用" if waiver.applied else "未应用") + "）", ""]
    lines.append("- 精确路径：" + waiver.path)
    if entry is not None:
        lines.append("- 实测：文件 " + str(entry["lines"]) + " 行（阈值 file_max_lines "
                     + str(thresholds.file_max_lines) + "），最大圈复杂度 " + str(entry["max_ccn"])
                     + "（阈值 fn_max_ccn " + str(thresholds.fn_max_ccn) + "）")
    if waiver.applied:
        lines.append("- 快照指纹：SHA256（CRLF→LF 规范化）= " + HA002_SNAPSHOT_SHA256)
        lines.append("- 只放行 file-lines 与 rust-ccn 两项超限；真实度量与这两条原违规保留在 "
                     "files/violations 中，message 前缀 " + HA002_MARKER.strip())
        lines.append("- 不等于原卡阈值达标：工程样品豁免，对外发布必须拒绝，新 RL 待收回")
        lines.append("- 其他路径、其他规则、覆盖率不足与工具错误都不豁免")
    else:
        lines.append("- 未应用原因：" + waiver.reason
                     + ("" if waiver.snapshot_sha256 is None
                        else "（实测快照 SHA256=" + waiver.snapshot_sha256 + "）"))
        lines.append("- 本次按 tools/ci/thresholds.yaml 的配置严格判定；快照或配置变化不会自动续期豁免")
    lines.append("")
    return lines


def render_markdown(document: dict, thresholds: Thresholds, coverage: CoverageResult,
                    comparison: Sequence[str] | None, warnings: Sequence[str],
                    waiver: SampleWaiver) -> str:
    """渲染 maint.md 正文；不含时间戳，重复运行逐字节一致。"""
    lines: list[str] = ["# 可维护性度量报告（CORE-71）", ""]
    if coverage.pending_target:
        lines.append("状态：pending-target（领域源码集合为空，仅开发聚合允许，发布必须拒绝）")
        lines.append("")
    lines.extend(_render_waiver(document, thresholds, waiver))
    lines.append("## 阈值")
    lines.append("")
    lines.append("| 键 | 值 |")
    lines.append("| --- | --- |")
    lines.append("| file_max_lines | " + str(thresholds.file_max_lines) + " |")
    lines.append("| fn_max_ccn | " + str(thresholds.fn_max_ccn) + " |")
    lines.append("| core_line_coverage | " + str(thresholds.core_line_coverage) + " |")
    lines.append("| dart_ccn_warn_only | " + ("true" if thresholds.dart_ccn_warn_only else "false") + " |")
    lines.append("")
    lines.append("## 文件度量")
    lines.append("")
    lines.append("生成物 *.g.dart 不入表；crates/fml-error/src/codes.rs 入表并标 generated=true。")
    lines.append("")
    lines.append("| path | lines | max_ccn | generated |")
    lines.append("| --- | --- | --- | --- |")
    for item in document["files"]:
        lines.append("| " + item["path"] + " | " + str(item["lines"]) + " | " + str(item["max_ccn"])
                     + " | " + ("true" if item["generated"] else "false") + " |")
    lines.append("")
    lines.append("## unsafe 统计")
    lines.append("")
    lines.append("块 " + str(document["unsafe"]["blocks"]) + "，缺 SAFETY 注释 "
                 + str(document["unsafe"]["safety_missing"]) + "，涉及文件 "
                 + str(len(document["unsafe"]["files"])) + "。只入报告与周报对比，不参与退出码。")
    lines.append("")
    for path in document["unsafe"]["files"]:
        lines.append("- " + path)
    lines.append("")
    lines.append("## FFI 统计")
    lines.append("")
    lines.append("extern C 块/声明 " + str(document["ffi"]["extern_c_blocks"]) + "，导出符号 "
                 + str(document["ffi"]["exported_symbols"]) + "，涉及文件 "
                 + str(len(document["ffi"]["files"])) + "。只入报告与周报对比，不参与退出码。")
    lines.append("")
    for path in document["ffi"]["files"]:
        lines.append("- " + path)
    lines.append("")
    lines.append("## 覆盖率")
    lines.append("")
    if coverage.pending_target:
        lines.append("领域源码集合为空：pending-target，不按 0/0 判通过，发布侧必须失败。")
    else:
        lines.append("核心行覆盖率 " + str(coverage.hit) + "/" + str(coverage.total) + "（阈值 "
                     + str(thresholds.core_line_coverage) + "，按 hit*den >= num*total 判定，"
                     + ("通过" if coverage.passed else "不通过") + "）")
    lines.append("")
    lines.append("SF 存在但无 DA（0 可执行行、不参与分子与分母、不判失败）："
                 + (",".join(coverage.missing) if coverage.missing else "无"))
    lines.append("")
    lines.append("集合外文件（列明排除，不参与比例）："
                 + (",".join(coverage.excluded) if coverage.excluded else "无"))
    lines.append("")
    lines.append("## 违规")
    lines.append("")
    if not document["violations"]:
        lines.append("无")
    for item in document["violations"]:
        where = item["path"] if item["line"] is None else item["path"] + ":" + str(item["line"])
        lines.append("- " + item["rule"] + " " + where + " " + item["message"])
    lines.append("")
    lines.append("## 周报对比")
    lines.append("")
    if comparison is None:
        lines.append("baseline（未提供 --previous 或上周报告不存在，本次不计算退化）")
    else:
        lines.extend(comparison)
        if waiver.applied:
            lines.append("- HA-002 样品豁免已应用：以上为真实度量对比，退出 0 不代表原阈值达标")
    lines.append("")
    lines.append("## 人工项")
    lines.append("")
    if not warnings:
        lines.append("无")
    for item in warnings:
        lines.append("- " + item)
    lines.append("")
    return NL.join(lines)


class _Parser(argparse.ArgumentParser):
    """参数错误也走 GATE-1：不打印 usage/traceback，交给 common.main 收敛成单行并退出 2。"""

    def error(self, message: str) -> None:  # type: ignore[override]
        raise GateError(None, message.splitlines()[0] if message else "参数错误")


def _build_parser() -> argparse.ArgumentParser:
    """构造 CLI；缺参数由 execute 显式判定，不静默取默认路径。"""
    parser = _Parser(prog="maint_report.py", add_help=False)
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default=None)
    parser.add_argument("--previous", default=None)
    parser.add_argument("--annotations", action="store_true")
    parser.add_argument("--lcov", default=None)
    parser.add_argument("--core-sources", dest="core_sources", default=None)
    return parser


def execute(parser: argparse.ArgumentParser, argv: Sequence[str]) -> int:
    """执行一次度量：先算完全部结果再写盘，退出 2 的路径不留半份报告。"""
    args = parser.parse_args([str(item) for item in argv])
    for flag, value in (("--out", args.out), ("--lcov", args.lcov),
                        ("--core-sources", args.core_sources)):
        if not value:
            raise GateError(None, "缺少必需参数：" + flag)
    root = Path(args.root)
    if not root.is_dir():
        raise GateError(str(root), "root 不是目录")
    thresholds = load_thresholds(thresholds_path(root))
    core_paths = load_core_sources(Path(args.core_sources))
    records = parse_lcov(Path(args.lcov), root)
    metrics, cache, warnings = measure_files(root)
    unsafe = {"blocks": 0, "safety_missing": 0, "files": []}
    ffi = {"extern_c_blocks": 0, "exported_symbols": 0, "files": []}
    for metric in metrics:
        if not metric.path.endswith(".rs"):
            continue
        counts = count_unsafe_ffi(cache[metric.path])
        unsafe["blocks"] += counts["blocks"]
        unsafe["safety_missing"] += counts["safety_missing"]
        ffi["extern_c_blocks"] += counts["extern_c_blocks"]
        ffi["exported_symbols"] += counts["exported_symbols"]
        if counts["blocks"]:
            unsafe["files"].append(metric.path)
        if counts["extern_c_blocks"] or counts["exported_symbols"]:
            ffi["files"].append(metric.path)
    coverage = evaluate_coverage(records, core_paths, thresholds)
    waiver = evaluate_sample_waiver(root, metrics, thresholds)
    violations, exit_code = collect_violations(metrics, thresholds, coverage, waiver)
    document = build_document(metrics, unsafe, ffi, coverage, violations)
    comparison: list[str] | None = None
    if args.previous:
        previous_path = Path(args.previous)
        if previous_path.is_file():
            comparison = compare_reports(load_previous(previous_path), document)
        else:
            comparison = ["- baseline（上周报告不存在：" + str(args.previous) + "，本次不计算退化）"]
    text = render_markdown(document, thresholds, coverage, comparison, warnings, waiver)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + NL, encoding="utf-8")
    if args.annotations:
        for line in format_annotations(violations, thresholds):
            print(line)
    if waiver.applied:
        print("maint_report: HA-002 样品豁免已应用（" + HA002_PATH
              + "：仅 file-lines 与 rust-ccn，工程样品，发布必须拒绝）")
    if coverage.pending_target:
        print("maint_report: coverage pending-target（领域源码集合为空，发布必须拒绝）")
    return exit_code


def main(argv: Sequence[str]) -> int:
    """入口：GateError 走 common.main 收敛成 stderr 单行 GATE-1 与退出码 2。"""
    parser = _build_parser()
    outcome: dict = {"code": 0}

    def body() -> list:
        try:
            outcome["code"] = execute(parser, argv)
        except GateError:
            raise
        except Exception as exc:  # 内部缺陷也算工具错误：退出 2，不冒充阈值违规（1）
            if os.environ.get("MAINT_REPORT_DEBUG") == "1":
                raise
            detail = type(exc).__name__ + ": " + str(exc).replace(NL, " ")
            raise GateError(None, "工具内部错误：" + detail) from exc
        return []

    code = common.main(body)
    if code == common.EXIT_GATE:
        return code
    return int(outcome["code"])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
