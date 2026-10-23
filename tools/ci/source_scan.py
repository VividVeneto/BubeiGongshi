#!/usr/bin/env python3
"""CORE-69 阶段1：源码词法扫描（Token 流）与目录扫描。

只做词法：括号不平衡不报错（卡 S0_CORE-69:43）；未闭合字符串/块注释、非法 UTF-8、
未登记后缀都收敛成 GateError（退出码 2）。CORE-71 与 CORE-74 只导入 tokens/
scan_tree/LANGUAGE_BY_SUFFIX 与 Token，不复制词法逻辑（卡:12）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path, PurePosixPath
from typing import Sequence

import common
from common import KIND_CODE, KIND_COMMENT, KIND_STRING, GateError, Token

LANGUAGE_BY_SUFFIX = {
    ".rs": "rust",
    ".dart": "dart",
    ".h": "cpp",
    ".hpp": "cpp",
    ".c": "cpp",
    ".cc": "cpp",
    ".cpp": "cpp",
}

DEFAULT_SUFFIXES = tuple(LANGUAGE_BY_SUFFIX)

LANGUAGES = frozenset({"rust", "dart", "cpp"})

# 只认 ASCII 空白；U+2028/U+2029 是普通字符，不能当分隔符（准备 K69-08）。
_ASCII_WHITESPACE = " \t\n\r\v\f"


def _utf8_len(char: str) -> int:
    """返回单个字符的 UTF-8 字节长度。"""
    code = ord(char)
    if code < 0x80:
        return 1
    if code < 0x800:
        return 2
    if code < 0x10000:
        return 3
    return 4


def _block_comment_end(text: str, index: int, nested: bool) -> int:
    """返回块注释结束后的下标；未闭合返回 -1。Rust 支持嵌套。"""
    size = len(text)
    depth = 1
    cursor = index + 2
    while cursor < size:
        if text.startswith("*/", cursor):
            depth -= 1
            cursor += 2
            if depth == 0:
                return cursor
            continue
        if nested and text.startswith("/*", cursor):
            depth += 1
            cursor += 2
            continue
        cursor += 1
    return -1


def _quoted_end(
    text: str,
    index: int,
    quote: str,
    escapes: bool = True,
    allow_newline: bool = False,
) -> int:
    """返回单引号/双引号字符串结束后的下标；允许转义，默认不跨行，未闭合返回 -1。

    Rust 普通双引号字符串允许裸换行（卡:43），只有该分支传 allow_newline=True。
    """
    size = len(text)
    cursor = index + 1
    while cursor < size:
        char = text[cursor]
        if escapes and char == "\\":
            cursor += 2
            continue
        if char == quote:
            return cursor + 1
        if char == "\n" and not allow_newline:
            return -1
        cursor += 1
    return -1


def _triple_end(text: str, index: int, quote: str, escapes: bool) -> int:
    """返回 Dart 三引号字符串结束后的下标；未闭合返回 -1。"""
    size = len(text)
    marker = quote * 3
    cursor = index + 3
    while cursor < size:
        if escapes and text[cursor] == "\\":
            cursor += 2
            continue
        if text.startswith(marker, cursor):
            return cursor + 3
        cursor += 1
    return -1


def _dart_string_end(text: str, index: int, raw: bool) -> int:
    """Dart 字符串：支持三引号与 raw 前缀；raw 形式不解析转义。"""
    quote = text[index]
    if text.startswith(quote * 3, index):
        return _triple_end(text, index, quote, escapes=not raw)
    return _quoted_end(text, index, quote, escapes=not raw)


def _rust_raw_end(text: str, index: int) -> int | None:
    """Rust r"..." / r#"..."#；不是 raw 前缀返回 None，未闭合返回 -1。"""
    size = len(text)
    cursor = index + 1
    hashes = 0
    while cursor < size and text[cursor] == "#":
        hashes += 1
        cursor += 1
    if cursor >= size or text[cursor] != '"':
        return None
    terminator = '"' + "#" * hashes
    close = text.find(terminator, cursor + 1)
    if close < 0:
        return -1
    return close + len(terminator)


def _cpp_raw_end(text: str, index: int) -> int | None:
    """C++ R"delim(...)delim"；不是 raw 前缀返回 None，未闭合返回 -1。"""
    open_paren = text.find("(", index + 2)
    if open_paren < 0 or open_paren - (index + 2) > 16:
        return None
    delimiter = text[index + 2:open_paren]
    terminator = ")" + delimiter + '"'
    close = text.find(terminator, open_paren + 1)
    if close < 0:
        return -1
    return close + len(terminator)


def _is_lifetime(text: str, index: int) -> bool:
    """Rust 单引号：后接标识符字符且其后没有闭合单引号时按生命周期（kind=code）。"""
    size = len(text)
    nxt = text[index + 1] if index + 1 < size else ""
    if not nxt or not (nxt.isalpha() or nxt == "_"):
        return False
    following = text[index + 2] if index + 2 < size else ""
    return following != "'"


class _Scanner:
    """单遍扫掠：字节偏移与行号随扫描同步累计，不从文本下标反推（卡:43）。"""

    def __init__(self, text: str, language: str, path: str) -> None:
        self.text = text
        self.size = len(text)
        self.language = language
        self.path = path
        self.index = 0
        self.offset = 0
        self.line = 1
        self.tokens: list[Token] = []

    def advance(self, end: int) -> None:
        """前进到下标 end（不含），累计 UTF-8 字节数，只在 \\n 处增行。"""
        text = self.text
        while self.index < end and self.index < self.size:
            char = text[self.index]
            self.offset += _utf8_len(char)
            if char == "\n":
                self.line += 1
            self.index += 1

    def append(self, kind: str, start: int, offset: int, line: int) -> None:
        self.tokens.append(Token(self.text[start:self.index], offset, line, kind))

    def scan(self) -> list[Token]:
        text = self.text
        run_start = -1
        run_offset = 0
        run_line = 0
        while self.index < self.size:
            if text[self.index] in _ASCII_WHITESPACE:
                if run_start >= 0:
                    self.append(KIND_CODE, run_start, run_offset, run_line)
                    run_start = -1
                self.advance(self.index + 1)
                continue
            if self.at_literal():
                if run_start >= 0:
                    self.append(KIND_CODE, run_start, run_offset, run_line)
                    run_start = -1
                self.take_literal()
                continue
            if run_start < 0:
                run_start, run_offset, run_line = self.index, self.offset, self.line
            self.advance(self.index + 1)
        if run_start >= 0:
            self.append(KIND_CODE, run_start, run_offset, run_line)
        return self.tokens

    def at_literal(self) -> bool:
        """当前位置是否注释或字符串开头；只判定不移动下标（卡:37、卡:43）。"""
        if self.text.startswith("//", self.index) or self.text.startswith("/*", self.index):
            return True
        return self.string_end() is not None

    def take_literal(self) -> bool:
        """在当前位置识别注释或字符串并整段消耗；都不是返回 False。"""
        text = self.text
        start, offset, line = self.index, self.offset, self.line
        if text.startswith("//", self.index):
            kind = KIND_COMMENT
            end = text.find("\n", self.index)
            if end < 0:
                end = self.size
        elif text.startswith("/*", self.index):
            kind = KIND_COMMENT
            end = _block_comment_end(text, self.index, nested=self.language == "rust")
            if end < 0:
                raise GateError(self.path, "块注释未闭合")
        else:
            kind = KIND_STRING
            end = self.string_end()
            if end is None:
                return False
            if end < 0:
                raise GateError(self.path, "字符串未闭合")
        self.advance(end)
        self.append(kind, start, offset, line)
        return True

    def string_end(self) -> int | None:
        """当前字符若是字符串开头，返回结束后的下标（未闭合 -1）；否则 None。"""
        text = self.text
        index = self.index
        char = text[index]
        size = self.size
        if self.language == "rust":
            if char == "r":
                raw = _rust_raw_end(text, index)
                if raw is not None:
                    return raw
            if char == '"':
                return _quoted_end(text, index, '"', allow_newline=True)
            if char == "'":
                if _is_lifetime(text, index):
                    return None
                return _quoted_end(text, index, "'")
            return None
        if self.language == "dart":
            if char == "r" and index + 1 < size and text[index + 1] in "'\"":
                return _dart_string_end(text, index + 1, raw=True)
            if char in "'\"":
                return _dart_string_end(text, index, raw=False)
            return None
        if char == "R" and index + 1 < size and text[index + 1] == '"':
            raw = _cpp_raw_end(text, index)
            if raw is not None:
                return raw
        if char in "'\"":
            return _quoted_end(text, index, char)
        return None


def tokens(path: str | Path, language: str | None = None) -> list[Token]:
    """按出现顺序返回文件的 Token 流；后缀未登记、解码失败、读不到都抛 GateError。"""
    file_path = Path(path)
    try:
        data = file_path.read_bytes()
    except OSError as exc:
        reason = exc.strerror or type(exc).__name__
        raise GateError(str(path), f"无法读取文件：{reason}") from exc
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError(str(path), f"不是合法 UTF-8（第 {exc.start} 字节）") from exc
    resolved = language if language is not None else LANGUAGE_BY_SUFFIX.get(file_path.suffix.lower())
    if resolved is None:
        suffix = file_path.suffix.lower()
        raise GateError(str(path), f"未登记的后缀：{suffix or '(无后缀)'}")
    if resolved not in LANGUAGES:
        raise GateError(str(path), f"未知语言：{resolved}")
    return _Scanner(text, resolved, str(path)).scan()


def scan_tree(root: str | Path, suffixes: Sequence[str]) -> list[tuple[str, Token]]:
    """扫描 root 下指定后缀的文件，返回 (相对 root 的 POSIX 路径, Token)。

    路径按字典序排，同一文件内保持出现顺序；suffixes 走 LANGUAGE_BY_SUFFIX，未登记即抛 GateError。
    """
    base = Path(root)
    if not base.is_dir():
        raise GateError(str(root), "扫描根不是目录")
    wanted: list[str] = []
    for raw in suffixes:
        suffix = str(raw).lower()
        if not suffix.startswith("."):
            suffix = "." + suffix
        if suffix not in LANGUAGE_BY_SUFFIX:
            raise GateError(str(root), f"未登记的后缀：{suffix}")
        if suffix not in wanted:
            wanted.append(suffix)
    selected = set(wanted)
    found: list[tuple[str, Path]] = []
    for candidate in base.rglob("*"):
        if not candidate.is_file() or candidate.suffix.lower() not in selected:
            continue
        relative = PurePosixPath(candidate.relative_to(base).as_posix()).as_posix()
        found.append((relative, candidate))
    found.sort(key=lambda item: item[0])
    results: list[tuple[str, Token]] = []
    for relative, candidate in found:
        for token in tokens(candidate, LANGUAGE_BY_SUFFIX[candidate.suffix.lower()]):
            results.append((relative, token))
    return results


class _Parser(argparse.ArgumentParser):
    """参数错误也走 GATE-1：不打印 usage/traceback，交给 common.main 收敛成单行。"""

    def error(self, message: str) -> None:  # type: ignore[override]
        raise GateError(None, message.splitlines()[0] if message else "参数错误")


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="source_scan.py", add_help=False)
    parser.add_argument("--root", default=".")
    parser.add_argument("--suffix", action="append", dest="suffixes", default=None)
    return parser


def main(argv: Sequence[str]) -> int:
    """阶段1 CLI：打印每个文件的 Token 数；词法阶段不产出 Finding。"""
    parser = _build_parser()

    def body() -> list:
        args = parser.parse_args([str(item) for item in argv])
        suffixes = args.suffixes if args.suffixes else list(DEFAULT_SUFFIXES)
        counts: dict[str, int] = {}
        for relative, _token in scan_tree(args.root, suffixes):
            counts[relative] = counts.get(relative, 0) + 1
        for relative in sorted(counts):
            print(f"{relative}: {counts[relative]} token(s)")
        return []

    return common.main(body)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
