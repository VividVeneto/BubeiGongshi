#!/usr/bin/env python3
"""CORE-74 门禁 ABI-1：公共 C 头契约与 abi-v* 基准标签的比较。

判据见 S0_CORE-74:14。Finding、GateError 与退出码收敛由 CORE-69 的 common 提供，
字符串/注释跨度由 CORE-69 的 source_scan 提供：本脚本不复制公共类型、不另写词法器。

- 只解析公共头需要的 C 子集：include 守卫、#include、对象式 #define、
  FML_ABI_MAJOR/FML_ABI_MINOR 十进制值、typedef struct 字段、函数声明与 typedef
  别名；函数式宏、#undef、条件分支等超出子集的语法按 GATE-1 退 2，不猜。
- 版本单调：主版本或次版本回退报 ABI-1；破坏性变化（删函数/删宏/改签名/删 struct/
  改字段）要求主版本提升，纯新增要求 (主,次) 提升，其余按无差异处理。
- 基准只取本仓库可达的 abi-v<MAJOR>.<MINOR>.<PATCH> 标签（git tag --list abi-v*
  加 merge-base --is-ancestor）；首个版本用 --first-release 自证且不创建标签。
- 浅 clone 无法判定可达标签，退 2 并提示 fetch-depth: 0 或 --first-release。

退出码：0 无 Finding，1 有 Finding，2 输入/环境错误（唯一通道 GATE-1）。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # pragma: no cover - 运行期由 main 延迟导入，缺失时走 GATE-1
    from common import Finding

DEFAULT_HEADER = "contracts/include/fmlcore.h"
TAG_PREFIX = "abi-v"
VERSION_MACROS = ("FML_ABI_MAJOR", "FML_ABI_MINOR")
_TAG_RE = re.compile(r"^abi-v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
_TYPE_QUALIFIERS = frozenset(
    {"const", "volatile", "unsigned", "signed", "short", "long", "struct", "union", "enum"}
)
_ALLOWED_DIRECTIVES = frozenset({"ifndef", "ifdef", "endif", "include", "define", "pragma"})
_EXTERN_BLOCK_START_RE = re.compile(r"\bextern\b[^{};]*\{")
_FUNCTION_RE = re.compile(rf"^(?P<result>.+?)\s+(?P<name>{_IDENT})\s*\((?P<params>.*)\)$", re.S)
_STRUCT_RE = re.compile(
    rf"^typedef\s+struct\s+(?:(?P<tag>{_IDENT})\s*)?\{{(?P<body>.*)\}}\s*(?P<name>{_IDENT})$",
    re.S,
)
_ALIAS_RE = re.compile(rf"^typedef\s+(?P<type>.+?)\s+(?P<name>{_IDENT})$", re.S)
_FUNCTION_POINTER_RE = re.compile(
    rf"^typedef\s+(?P<result>.+?)\s*\(\s*\*\s*(?P<name>{_IDENT})\s*\)\s*\((?P<params>.*)\)$",
    re.S,
)
_DECLARATOR_RE = re.compile(rf"^(?P<type>.+?)\s*(?P<name>{_IDENT})(?P<suffix>(\[[^\]]*\])*)$", re.S)


class _Syntax(Exception):
    """头文件语法超出 CORE-74 解析子集；由调用方转成 GATE-1 单行错误。"""


@dataclass(frozen=True)
class Function:
    """公共函数声明：返回类型与参数类型文本都已规范化。"""
    name: str
    result: str
    params: tuple[str, ...]
    line: int


@dataclass(frozen=True)
class Struct:
    """公共 struct：字段顺序与类型文本都参与比较。"""
    name: str
    fields: tuple[tuple[str, str], ...]
    line: int


@dataclass
class Header:
    """一份头文件的 ABI 形状。"""
    major: int
    minor: int
    version_lines: tuple[int, int]
    functions: dict[str, Function] = field(default_factory=dict)
    structs: dict[str, Struct] = field(default_factory=dict)
    macros: dict[str, str] = field(default_factory=dict)


def _parser(common) -> argparse.ArgumentParser:
    """参数错误同样走 GATE-1：不打印 usage，交给 common.main 收敛成单行。"""
    class _Parser(argparse.ArgumentParser):
        def error(self, message: str) -> None:  # type: ignore[override]
            raise common.GateError(None, (message or "参数错误").splitlines()[0])

    parser = _Parser(prog="check_abi.py", add_help=False)
    parser.add_argument("--root", default=None, help="仓库根，缺省为脚本上溯两级")
    parser.add_argument("--header", default=DEFAULT_HEADER, help="仓库相对的公共头路径")
    parser.add_argument("--base-ref", default=None, help="基准 abi-v* 标签")
    parser.add_argument("--first-release", action="store_true", help="首个版本自证，不创建标签")
    return parser


def _normalize_type(text: str) -> str:
    """折叠空白并统一指针/数组写法，避免排版差异被当成 ABI 变化。"""
    compact = " ".join(text.split())
    compact = re.sub(r"\s*\*\s*", "*", compact)
    compact = re.sub(r"\s*\[\s*", "[", compact)
    compact = re.sub(r"\s*\]\s*", "]", compact)
    return compact.strip()


def _sanitize(text: str, tokens) -> str:
    """把字符串与注释跨度替换成空格，保留换行与行数；C 子集只按代码区域判定。

    `extern "C"` 的字符串与注释里的 `;`/`{}` 不参与结构解析，因此遮罩在 B2 修复后仍必需。
    """
    chars = list(text)
    positions: dict[int, int] = {}
    offset = 0
    for index, char in enumerate(text):
        positions[offset] = index
        offset += len(char.encode("utf-8"))
    for token in tokens:
        if token.kind == "code":
            continue
        start = positions.get(token.offset)
        if start is None:
            raise _Syntax("词法偏移无法映射回字符下标")
        for position in range(start, min(start + len(token.text), len(chars))):
            if chars[position] != "\n":
                chars[position] = " "
    return "".join(chars)


def _line_of(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def _split_top(text: str, separator: str) -> list[str]:
    """按 depth 0 的分隔符切分，括号内的分隔符保留。"""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if char == separator and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    parts.append("".join(current))
    return parts


def _strip_parameter_name(raw: str) -> str:
    """去掉参数名，只留类型文本；unsigned int 这类标识符属于类型本身。"""
    text = _normalize_type(raw)
    if not text:
        return ""
    if " " not in text and not text.endswith("]") and "*" not in text:
        return text
    if text.endswith(")"):
        return text
    match = _DECLARATOR_RE.match(text)
    if match is None:
        return text
    head = match.group("type").strip()
    words = head.split(" ")
    if words and words[-1] in _TYPE_QUALIFIERS:
        return text
    return _normalize_type(head + match.group("suffix"))


def _parse_parameters(text: str, line: int) -> tuple[str, ...]:
    raw_parts = [part for part in (piece.strip() for piece in _split_top(text, ",")) if part]
    if not raw_parts:
        return ()
    types = tuple(_strip_parameter_name(part) for part in raw_parts)
    if types == ("void",):
        return ()
    if any(not item for item in types):
        raise _Syntax(f"第 {line} 行：参数类型为空")
    return types


def _parse_fields(body: str, line: int) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for piece in _split_top(body, ";"):
        if not piece.strip():
            continue
        text = _normalize_type(piece)
        if len(_split_top(text, ",")) > 1:
            raise _Syntax(f"第 {line} 行：不支持一行声明多个字段")
        match = _DECLARATOR_RE.match(text)
        if match is None:
            raise _Syntax(f"第 {line} 行：无法识别的字段声明")
        fields.append((match.group("name"), _normalize_type(match.group("type") + match.group("suffix"))))
    return fields


def _parse_typedef(body: str, line: int, header: Header) -> None:
    struct = _STRUCT_RE.match(body)
    if struct is not None:
        inner = struct.group("body")
        if "{" in inner or "}" in inner:
            raise _Syntax(f"第 {line} 行：不支持嵌套 struct")
        name = struct.group("name")
        if name in header.structs:
            raise _Syntax(f"第 {line} 行：struct {name} 重复定义")
        header.structs[name] = Struct(name, tuple(_parse_fields(inner, line)), line)
        return
    if _FUNCTION_POINTER_RE.match(body) is not None or _ALIAS_RE.match(body) is not None:
        return
    raise _Syntax(f"第 {line} 行：无法识别的 typedef")


def _parse_function(body: str, line: int, header: Header) -> None:
    match = _FUNCTION_RE.match(body)
    if match is None:
        raise _Syntax(f"第 {line} 行：无法识别的声明")
    name = match.group("name")
    if name in header.functions:
        raise _Syntax(f"第 {line} 行：函数 {name} 重复声明")
    header.functions[name] = Function(
        name,
        _normalize_type(match.group("result")),
        _parse_parameters(match.group("params"), line),
        line,
    )


def _neutralize_extern_blocks(text: str) -> str:
    """把 extern "C" { ... } 折成纯声明序列：只抹掉开头与收尾括号，保持长度与行号。"""
    chars = list(text)
    spans: list[tuple[int, int]] = []
    for match in _EXTERN_BLOCK_START_RE.finditer(text):
        open_index = match.end() - 1
        depth = 0
        end = -1
        for position in range(open_index, len(text)):
            if text[position] == "{":
                depth += 1
            elif text[position] == "}":
                depth -= 1
                if depth == 0:
                    end = position
                    break
        if end < 0:
            raise _Syntax(f"第 {_line_of(text, match.start())} 行：extern 块未闭合")
        spans.append((match.start(), open_index + 1))
        spans.append((end, end + 1))
    for begin, stop in spans:
        for position in range(begin, stop):
            if chars[position] != "\n":
                chars[position] = " "
    return "".join(chars)


def _parse_declarations(text: str, first_line: int, header: Header) -> None:
    """按顶层分号切声明块；被花括号包裹的块（extern "C"）递归展开。"""
    text = _neutralize_extern_blocks(text)
    depth = 0
    start = 0
    boundaries: list[tuple[int, int]] = []
    for index, char in enumerate(text):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
            if depth < 0:
                raise _Syntax(f"第 {_line_of(text, index)} 行：括号不配对")
        elif char == ";" and depth == 0:
            boundaries.append((start, index))
            start = index + 1
    if depth != 0:
        raise _Syntax("括号不配对：文件末尾仍未闭合")
    tail = text[start:]
    if tail.strip():
        raise _Syntax(f"第 {_line_of(text, start + len(tail) - len(tail.lstrip()))} 行：最后一个声明缺少分号")
    for begin, end in boundaries:
        raw = text[begin:end]
        body = raw.strip()
        if not body:
            continue
        offset = begin + len(raw) - len(raw.lstrip())
        line = first_line + text.count("\n", 0, offset)
        if body.startswith("{") and body.endswith("}"):
            _parse_declarations(body[1:-1], line, header)
        elif body.startswith("typedef"):
            _parse_typedef(body, line, header)
        else:
            _parse_function(body, line, header)


def _preprocess(text: str) -> tuple[str, dict[str, str], tuple[int, int]]:
    """剥离预处理指令（保持行号），返回声明正文、宏表与版本宏行号。"""
    cleaned: list[str] = []
    macros: dict[str, str] = {}
    version_lines: dict[str, int] = {}
    for number, line in enumerate(text.splitlines(keepends=True), start=1):
        stripped = line.strip()
        if not stripped.startswith("#"):
            cleaned.append(line)
            continue
        if stripped.endswith("\\"):
            raise _Syntax(f"第 {number} 行：不支持宏续行")
        keyword, _, rest = stripped[1:].strip().partition(" ")
        keyword, rest = keyword.strip(), rest.strip()
        if keyword not in _ALLOWED_DIRECTIVES:
            raise _Syntax(f"第 {number} 行：不支持的预处理指令 #{keyword}")
        if keyword == "define":
            match = re.fullmatch(rf"(?P<name>{_IDENT})(?P<rest>.*)", rest, re.S)
            if match is None:
                raise _Syntax(f"第 {number} 行：无法识别的 #define")
            name, tail = match.group("name"), match.group("rest")
            if tail.startswith("("):
                raise _Syntax(f"第 {number} 行：不支持函数式宏 {name}")
            if name in macros:
                raise _Syntax(f"第 {number} 行：宏 {name} 重复定义")
            value = _normalize_type(tail)
            macros[name] = value
            if name in VERSION_MACROS:
                if not re.fullmatch(r"\d+", value):
                    raise _Syntax(f"第 {number} 行：{name} 必须是十进制整数")
                version_lines[name] = number
        cleaned.append("\n" if line.endswith("\n") else "")
    missing = [name for name in VERSION_MACROS if name not in version_lines]
    if missing:
        raise _Syntax("缺少版本宏：" + "、".join(missing))
    return "".join(cleaned), macros, (version_lines[VERSION_MACROS[0]], version_lines[VERSION_MACROS[1]])


def _header_from_text(common, source_scan, text: str, label: str) -> Header:
    """用临时 .h 文件取得字符串/注释跨度后解析；语法越界转成 GATE-1。"""
    with tempfile.TemporaryDirectory(prefix="core74-abi-") as directory:
        scratch = Path(directory) / "header.h"
        scratch.write_bytes(text.encode("utf-8"))
        try:
            tokens = source_scan.tokens(scratch)
        except common.GateError as error:  # 词法层错误改挂到真实路径上
            raise common.GateError(label, getattr(error, "message", str(error))) from error
    try:
        cleaned = _sanitize(text, tokens)
        declarations, macros, version_lines = _preprocess(cleaned)
        header = Header(
            major=int(macros[VERSION_MACROS[0]]),
            minor=int(macros[VERSION_MACROS[1]]),
            version_lines=version_lines,
            macros={name: value for name, value in macros.items() if name not in VERSION_MACROS},
        )
        _parse_declarations(declarations, 1, header)
    except _Syntax as error:
        raise common.GateError(label, str(error)) from error
    return header


def _load_header(common, source_scan, path: Path, label: str) -> Header:
    try:
        text = path.read_bytes().decode("utf-8")  # 按字节解码，保证偏移与词法层一致
    except OSError as error:
        raise common.GateError(label, f"头文件不可读：{error.strerror or error}") from error
    except UnicodeDecodeError as error:
        raise common.GateError(label, f"头文件不是 UTF-8：{error.reason}") from error
    return _header_from_text(common, source_scan, text, label)


def _git(common, root: Path, arguments: Sequence[str]) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        raise common.GateError(None, f"git 不可用：{error.strerror or error}") from error
    return completed.returncode, completed.stdout, completed.stderr


def _reachable_tags(common, root: Path) -> list[tuple[tuple[int, int, int], str]]:
    code, stdout, stderr = _git(common, root, ["tag", "--list", TAG_PREFIX + "*"])
    if code != 0:
        raise common.GateError(None, f"git tag 失败：{stderr.strip() or code}")
    tags: list[tuple[tuple[int, int, int], str]] = []
    for name in stdout.split():
        match = _TAG_RE.match(name)
        if match is None:
            continue
        code, _, stderr = _git(common, root, ["merge-base", "--is-ancestor", name, "HEAD"])
        if code == 0:
            tags.append((tuple(int(part) for part in match.groups()), name))
        elif code != 1:
            raise common.GateError(None, f"无法判定基准可达性：{stderr.strip() or code}")
    return sorted(tags)


def _baseline_text(common, root: Path, base_ref: str, header_relative: str) -> str:
    code, stdout, stderr = _git(common, root, ["show", f"{base_ref}:{header_relative}"])
    if code != 0:
        raise common.GateError(None, f"基准头 {header_relative} 不可读：{stderr.strip() or code}")
    return stdout


def _resolve_base(common, root: Path, header_relative: str, args) -> tuple[str, str] | None:
    """返回 (基准头文本, 基准标签)；--first-release 返回 None；非法基准一律 GATE-1。"""
    if args.base_ref and args.first_release:
        raise common.GateError(None, "--base-ref 与 --first-release 不能同时给出")
    if args.first_release:
        if _reachable_tags(common, root):
            raise common.GateError(None, "已存在可达的 abi-v* 基准标签，不能声明 --first-release")
        return None
    if args.base_ref:
        if _TAG_RE.match(args.base_ref) is None:
            raise common.GateError(None, "基准必须是 abi-v<MAJOR>.<MINOR>.<PATCH> 标签")
        code, stdout, stderr = _git(
            common, root, ["rev-parse", "--verify", "--quiet", args.base_ref + "^{commit}"]
        )
        if code != 0 or not stdout.strip():
            raise common.GateError(None, f"基准标签不可解析：{stderr.strip() or code}")
        code, _, stderr = _git(common, root, ["merge-base", "--is-ancestor", args.base_ref, "HEAD"])
        if code != 0:
            raise common.GateError(None, f"基准标签不是 HEAD 的祖先：{stderr.strip() or code}")
        base_ref = args.base_ref
    else:
        code, stdout, _ = _git(common, root, ["rev-parse", "--is-shallow-repository"])
        if code == 0 and stdout.strip() == "true":
            raise common.GateError(None, "浅 clone 缺少基准历史：请用 fetch-depth: 0 或用 --first-release")
        tags = _reachable_tags(common, root)
        if not tags:
            raise common.GateError(None, "没有可达的 abi-v* 基准标签：首个版本请加 --first-release")
        base_ref = tags[-1][1]
    return _baseline_text(common, root, base_ref, header_relative), base_ref


def _compare(common, label: str, baseline: Header, current: Header) -> list:
    """比较两份头文件：先判版本单调，再区分破坏性变化与纯新增。"""
    findings = []
    breaking: list[str] = []
    additive: list[str] = []
    for name, old in baseline.functions.items():
        new = current.functions.get(name)
        if new is None:
            breaking.append(f"删除函数 {name}")
        elif new.result != old.result or new.params != old.params:
            breaking.append(f"函数签名变化 {name}")
    for name, old in baseline.structs.items():
        new = current.structs.get(name)
        if new is None:
            breaking.append(f"删除 struct {name}")
        elif new.fields[: len(old.fields)] != old.fields:
            breaking.append(f"struct {name} 字段被修改或重排")
        elif len(new.fields) > len(old.fields):
            additive.append(f"struct {name} 追加字段")
    for name, old in baseline.macros.items():
        if name not in current.macros:
            breaking.append(f"删除宏 {name}")
        elif current.macros[name] != old:
            breaking.append(f"宏取值变化 {name}")
    for name in current.functions:
        if name not in baseline.functions:
            additive.append(f"新增函数 {name}")
    for name in current.structs:
        if name not in baseline.structs:
            additive.append(f"新增 struct {name}")
    for name in current.macros:
        if name not in baseline.macros:
            additive.append(f"新增宏 {name}")
    if current.major < baseline.major:
        findings.append(common.Finding(label, current.version_lines[0], "ABI-1", "ABI 主版本回退"))
    elif current.major == baseline.major and current.minor < baseline.minor:
        findings.append(common.Finding(label, current.version_lines[1], "ABI-1", "ABI 次版本回退"))
    if breaking and current.major <= baseline.major:
        findings.append(
            common.Finding(label, None, "ABI-1", "破坏性变更需提升 ABI 主版本：" + "；".join(breaking))
        )
    bumped = (current.major, current.minor) > (baseline.major, baseline.minor)
    if additive and not bumped:
        findings.append(common.Finding(label, None, "ABI-1", "新增 ABI 需提升版本：" + "；".join(additive)))
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    """命令行入口：先延迟导入 CORE-69 的公共层，再按 common.main 收敛退出码。"""
    try:
        import common
        import source_scan
    except ImportError:
        print("-: GATE-1 依赖 CORE-69 的 common/source_scan 尚未交付", file=sys.stderr)
        return 2

    def body():
        arguments = list(sys.argv[1:] if argv is None else argv)
        args = _parser(common).parse_args(arguments)
        root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
        if not root.is_dir():
            raise common.GateError(None, f"仓库根不是目录：{root}")
        header = Path(args.header)
        if header.is_absolute():
            raise common.GateError(None, "--header 必须是仓库相对路径")
        relative = header.as_posix()
        current = _load_header(common, source_scan, root / relative, relative)
        resolved = _resolve_base(common, root, relative, args)
        if resolved is None:
            print("ABI baseline: first-release")
            return []
        text, base_ref = resolved
        baseline = _header_from_text(common, source_scan, text, f"{base_ref}:{relative}")
        return _compare(common, relative, baseline, current)

    return common.main(body)


if __name__ == "__main__":
    sys.exit(main())
