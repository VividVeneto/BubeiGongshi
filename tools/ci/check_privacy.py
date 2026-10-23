#!/usr/bin/env python3
"""CORE-69 阶段2：Dart 侧依赖方向与隐私检查（DEP-5、DEP-6、PRIV-1、PRIV-2）。

卡：SADD/S0/S0_CORE-69_基座.md 第 12、39 行；验收：SADD/Test/S0/S0_CORE-69_TEST.md 第 6～9 行。
入口：python tools/ci/check_privacy.py --root .
退出码：0 无发现；1 有发现；2 配置/环境错误（stderr 单行 GATE-1，stdout 为空）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

import yaml

import common
import source_scan

RULE_DEP5 = "DEP-5"
RULE_DEP6 = "DEP-6"
RULE_PRIV1 = "PRIV-1"
RULE_PRIV2 = "PRIV-2"

NETWORK_POLICY = "contracts/policies/network-construction.yaml"
DEP6_POLICY = "contracts/policies/dep6_symbols.txt"
PLATFORM_POLICY = "contracts/policies/platform-check-patterns.json"

APP_LIB = "app/lib/"
UI_PREFIX = "app/lib/ui/"
COMPOSITION_PREFIX = "app/lib/composition/"
PLATFORM_PREFIX = "app/lib/platform/"
HTTP_PREFIXES = ("package:http", "package:dio")
HOLDING_TYPES = ("AppDeps", "CoreBinding", "PlatformPorts")
PLATFORM_PORTS = "PlatformPorts"
NETWORK_OBJECTS = ("HttpClient", "Socket")
DART_SUFFIX = ".dart"

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CHAIN = re.compile(r"(?<![\w.])([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)")
_HTTP_MEMBER = re.compile(
    r"(?<![\w.])((?:[A-Za-z_][A-Za-z0-9_]*\.)*[A-Za-z_][A-Za-z0-9_]*)\s*\.\s*http\b"
)
_CONSTRUCTION = re.compile(r"(?<![\w.])(HttpClient|Socket)(?=\s*[\(.])")
_DECL = re.compile(r"(AppDeps|CoreBinding|PlatformPorts)\s+([a-z_][A-Za-z0-9_]*)")
_ASSIGN = re.compile(r"(?<![\w.])([a-z_][A-Za-z0-9_]*)\s*=\s*([a-z_][A-Za-z0-9_]*)\s*;")
_DTO_EXEMPT = re.compile(r"binding/dto/[^/]*\.g\.dart\Z")


class _Hit(NamedTuple):
    """内部命中：保留字节偏移，便于按 token 去重。

    用 NamedTuple 而不是 dataclass：脚本可能被 common.run 以临时代模块名载入，
    dataclass 会去 sys.modules 查模块而拿到 None。
    """

    path: str
    line: int
    rule: str
    message: str
    offset: int


class _DuplicateKey(Exception):
    """策略文件出现重复键（YAML/JSON 各自在解析期抛出）。"""


class _UniqueKeyLoader(yaml.SafeLoader):
    """拒绝重复键的 SafeLoader；重复键属于配置错误，必须退出 2。"""

    def construct_mapping(self, node, deep=False):  # noqa: ANN001, ANN201
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
            seen = set()
            for key_node, _value in node.value:
                key = self.construct_object(key_node, deep=True)
                if key in seen:
                    raise _DuplicateKey(str(key))
                seen.add(key)
        return super().construct_mapping(node, deep=deep)


class _Parser(argparse.ArgumentParser):
    """参数错误也收敛成 GATE-1，保证 stderr 只有一行。"""

    def error(self, message: str) -> None:  # noqa: D401
        raise common.GateError(None, message.splitlines()[0] if message else "参数错误")


def _read_policy(root: Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        raise common.GateError(rel, f"缺少策略文件：{rel}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise common.GateError(rel, "不是合法 UTF-8") from None
    except OSError as exc:
        raise common.GateError(rel, f"无法读取策略文件：{exc}") from None


def _yaml_load(rel: str, text: str):  # noqa: ANN202
    try:
        return yaml.load(text, Loader=_UniqueKeyLoader)
    except _DuplicateKey as exc:
        raise common.GateError(rel, f"重复的键：{exc}") from None
    except yaml.YAMLError as exc:
        first = str(exc).splitlines()[0] if str(exc) else "未知错误"
        raise common.GateError(rel, f"不是合法 YAML：{first}") from None


def _glob_regex(pattern: str) -> re.Pattern[str]:
    escaped = re.escape(pattern)
    escaped = escaped.replace(r"\*\*/", "(?:.*/)?")
    escaped = escaped.replace(r"\*\*", ".*")
    escaped = escaped.replace(r"\*", "[^/]*")
    return re.compile(escaped + r"\Z")


def _load_network(root: Path) -> list[re.Pattern[str]]:
    data = _yaml_load(NETWORK_POLICY, _read_policy(root, NETWORK_POLICY))
    if not isinstance(data, dict):
        raise common.GateError(NETWORK_POLICY, "策略文件顶层必须是映射")
    unknown = sorted(set(data) - {"version", "allow"})
    if unknown:
        raise common.GateError(NETWORK_POLICY, f"未知字段：{unknown}")
    if data.get("version") != 1:
        raise common.GateError(NETWORK_POLICY, f"version 必须为 1，实际为 {data.get('version')!r}")
    allow = data.get("allow")
    if not isinstance(allow, list):
        raise common.GateError(NETWORK_POLICY, "allow 必须是通配符数组")
    patterns = []
    seen = set()
    for item in allow:
        if not isinstance(item, str) or not item:
            raise common.GateError(NETWORK_POLICY, "allow 的元素必须是非空字符串")
        if item in seen:
            raise common.GateError(NETWORK_POLICY, f"allow 存在重复条目：{item}")
        seen.add(item)
        patterns.append(_glob_regex(item))
    return patterns


def _load_dep6(root: Path) -> tuple[set[str], set[str]]:
    text = _read_policy(root, DEP6_POLICY)
    ops: set[str] = set()
    types: set[str] = set()
    seen: set[str] = set()
    version_seen = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not version_seen:
            if line != "version:1":
                raise common.GateError(DEP6_POLICY, "首行版本头必须为 version:1")
            version_seen = True
            continue
        prefix, _, symbol = line.partition(":")
        symbol = symbol.strip()
        if prefix not in {"op", "type"}:
            raise common.GateError(DEP6_POLICY, f"未知的行前缀：{line}")
        if not symbol:
            raise common.GateError(DEP6_POLICY, f"符号不能为空：{line}")
        if symbol in seen:
            raise common.GateError(DEP6_POLICY, f"重复的符号：{symbol}")
        seen.add(symbol)
        (ops if prefix == "op" else types).add(symbol)
    if not version_seen:
        raise common.GateError(DEP6_POLICY, "缺少版本头 version:1")
    return ops, types


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    seen: dict = {}
    for key, value in pairs:
        if key in seen:
            raise _DuplicateKey(key)
        seen[key] = value
    return seen


def _load_patterns(root: Path) -> list[dict]:
    text = _read_policy(root, PLATFORM_POLICY)
    try:
        data = json.loads(text, object_pairs_hook=_pairs)
    except _DuplicateKey as exc:
        raise common.GateError(PLATFORM_POLICY, f"重复的键：{exc}") from None
    except json.JSONDecodeError as exc:
        raise common.GateError(PLATFORM_POLICY, f"不是合法 JSON：{exc.msg}（第 {exc.lineno} 行）") from None
    if not isinstance(data, dict):
        raise common.GateError(PLATFORM_POLICY, "策略文件顶层必须是映射")
    unknown = sorted(set(data) - {"version", "patterns"})
    if unknown:
        raise common.GateError(PLATFORM_POLICY, f"未知字段：{unknown}")
    if data.get("version") != 1:
        raise common.GateError(PLATFORM_POLICY, f"version 必须为 1，实际为 {data.get('version')!r}")
    raw_patterns = data.get("patterns")
    if not isinstance(raw_patterns, list):
        raise common.GateError(PLATFORM_POLICY, "patterns 必须是数组")
    patterns = []
    for index, item in enumerate(raw_patterns):
        if not isinstance(item, dict):
            raise common.GateError(PLATFORM_POLICY, f"patterns[{index}] 必须是映射")
        unknown = sorted(set(item) - {"library", "receiver", "member"})
        if unknown:
            raise common.GateError(PLATFORM_POLICY, f"未知字段：{unknown}")
        library = item.get("library")
        member = item.get("member")
        receiver = item.get("receiver")
        if not isinstance(library, str) or not library:
            raise common.GateError(PLATFORM_POLICY, f"patterns[{index}].library 必须是非空字符串")
        if not isinstance(member, str) or not member:
            raise common.GateError(PLATFORM_POLICY, f"patterns[{index}].member 必须是非空字符串")
        if receiver is not None and (not isinstance(receiver, str) or not receiver):
            raise common.GateError(PLATFORM_POLICY, f"patterns[{index}].receiver 必须是非空字符串或 null")
        patterns.append(
            {"library": library, "receiver": receiver, "members": frozenset(member.split("|"))}
        )
    return patterns


def _dart_files(root: Path, prefix: str) -> list[str]:
    base = root / prefix.rstrip("/")
    if not base.is_dir():
        return []
    return sorted(path.relative_to(root).as_posix() for path in base.rglob("*" + DART_SUFFIX) if path.is_file())


def _offset(token: common.Token, index: int) -> int:
    return token.offset + len(token.text[:index].encode("utf-8"))


def _imports(tokens: list[common.Token]) -> list[tuple[str, str | None, int, int]]:
    found = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind == common.KIND_CODE and token.text.strip() == "import":
            cursor = index + 1
            while cursor < len(tokens) and tokens[cursor].kind == common.KIND_CODE and not tokens[cursor].text.strip():
                cursor += 1
            if cursor < len(tokens) and tokens[cursor].kind == common.KIND_STRING:
                target = tokens[cursor].text.strip("'\"")
                alias = None
                if cursor + 2 < len(tokens) and tokens[cursor + 1].kind == common.KIND_CODE:
                    if tokens[cursor + 1].text.strip() == "as" and tokens[cursor + 2].kind == common.KIND_CODE:
                        match = _IDENT.match(tokens[cursor + 2].text.strip())
                        alias = match.group(0) if match else None
                found.append((target, alias, tokens[cursor].line, tokens[cursor].offset))
                index = cursor + 1
                continue
        index += 1
    return found


def _declared_types(code_text: str) -> dict[str, str]:
    types: dict[str, str] = {}
    for match in _DECL.finditer(code_text):
        types.setdefault(match.group(2), match.group(1))
    chains = dict(_ASSIGN.findall(code_text))
    changed = True
    while changed:
        changed = False
        for lhs, rhs in chains.items():
            resolved = types.get(rhs)
            if resolved is not None and types.get(lhs) != resolved:
                types[lhs] = resolved
                changed = True
    return types


def _check_ui_imports(rel: str, imports: list[tuple], hits: list[_Hit]) -> None:
    for target, _alias, line, offset in imports:
        if target.startswith(HTTP_PREFIXES):
            message = f"ui 不得导入 HTTP 包：{target}"
        elif "binding/" in target and not _DTO_EXEMPT.search(target):
            message = f"ui 不得导入 binding（仅 binding/dto/*.g.dart 可只读导入）：{target}"
        elif "platform/" in target:
            message = f"ui 不得导入 platform：{target}"
        else:
            continue
        hits.append(_Hit(rel, line, RULE_DEP5, message, offset))


def _check_ui_types(rel: str, tokens: list[common.Token], hits: list[_Hit]) -> None:
    for token in tokens:
        if token.kind != common.KIND_CODE:
            continue
        for match in _IDENT.finditer(token.text):
            name = match.group(0)
            if name in HOLDING_TYPES:
                hits.append(
                    _Hit(rel, token.line, RULE_DEP5, f"ui 不得持有 {name}", _offset(token, match.start()))
                )


def _check_ports_http(
    rel: str, tokens: list[common.Token], hits: list[_Hit], warnings: list[str]
) -> None:
    code_text = " ".join(token.text for token in tokens if token.kind == common.KIND_CODE)
    types = _declared_types(code_text)
    for token in tokens:
        if token.kind != common.KIND_CODE:
            continue
        for match in _HTTP_MEMBER.finditer(token.text):
            receiver = match.group(1).rsplit(".", 1)[-1]
            declared = types.get(receiver)
            offset = _offset(token, match.start())
            if declared == PLATFORM_PORTS:
                hits.append(
                    _Hit(
                        rel,
                        token.line,
                        RULE_DEP5,
                        "composition 之外不得读取 PlatformPorts 的 http 字段",
                        offset,
                    )
                )
            elif declared is None:
                warnings.append(
                    f"{rel}:{token.line}: 无法判定 {receiver}.http 的接收者类型，登记人工复核项（DEP-5 warning）"
                )


def _check_network(rel: str, imports: list[tuple], tokens: list[common.Token], hits: list[_Hit]) -> None:
    for target, _alias, line, offset in imports:
        if target.startswith(HTTP_PREFIXES):
            hits.append(
                _Hit(rel, line, RULE_PRIV1, f"白名单外不得导入网络包：{target}", offset)
            )
    for token in tokens:
        if token.kind != common.KIND_CODE:
            continue
        for match in _CONSTRUCTION.finditer(token.text):
            name = match.group(1)
            hits.append(
                _Hit(
                    rel,
                    token.line,
                    RULE_PRIV1,
                    f"白名单外不得构造网络对象：{name}",
                    _offset(token, match.start()),
                )
            )


def _match_pattern(
    parts: list[str], patterns: list[dict], alias_map: dict[str, str], bare_libs: set[str]
) -> tuple[str | None, str | None] | None:
    for pattern in patterns:
        library, receiver, members = pattern["library"], pattern["receiver"], pattern["members"]
        if len(parts) >= 3 and alias_map.get(parts[-3]) == library:
            if receiver is not None and parts[-2] == receiver and parts[-1] in members:
                return f"{parts[-2]}.{parts[-1]}", None
        if len(parts) >= 2 and alias_map.get(parts[-2]) == library:
            if receiver is None and parts[-1] in members:
                return parts[-1], None
        if library in bare_libs:
            if len(parts) >= 2 and receiver is not None and parts[-2] == receiver and parts[-1] in members:
                return f"{parts[-2]}.{parts[-1]}", None
            if receiver is None and len(parts) == 1 and parts[0] in members:
                return parts[0], None
    for pattern in patterns:
        receiver = pattern["receiver"]
        if receiver is None or len(parts) < 2:
            continue
        if parts[-2] != receiver or parts[-1] not in pattern["members"]:
            continue
        prefix = parts[-3] if len(parts) >= 3 else None
        if prefix is not None and prefix in alias_map:
            continue
        return None, f"{receiver}.{parts[-1]}"
    return None


def _check_platform_checks(
    rel: str,
    imports: list[tuple],
    tokens: list[common.Token],
    patterns: list[dict],
    hits: list[_Hit],
    warnings: list[str],
) -> None:
    alias_map: dict[str, str] = {}
    bare_libs: set[str] = set()
    for target, alias, _line, _offset_value in imports:
        if alias:
            alias_map[alias] = target
        else:
            bare_libs.add(target)
    for token in tokens:
        if token.kind != common.KIND_CODE:
            continue
        for match in _CHAIN.finditer(token.text):
            parts = match.group(1).split(".")
            result = _match_pattern(parts, patterns, alias_map, bare_libs)
            if result is None:
                continue
            matched, unprovable = result
            if matched is not None:
                hits.append(
                    _Hit(
                        rel,
                        token.line,
                        RULE_PRIV2,
                        f"ui 不得判断平台：{matched}",
                        _offset(token, match.start()),
                    )
                )
            elif unprovable is not None:
                warnings.append(
                    f"{rel}:{token.line}: 无法证明 {unprovable} 的来源，登记人工复核项（PRIV-2 warning）"
                )


def _check_platform_symbols(
    rel: str, tokens: list[common.Token], symbols: tuple[set[str], set[str]], hits: list[_Hit]
) -> None:
    ops, types = symbols
    depth = 0
    for token in tokens:
        if token.kind == common.KIND_STRING:
            if depth > 0:
                value = token.text.strip("'\"")
                if value in ops:
                    hits.append(
                        _Hit(rel, token.line, RULE_DEP6, f"平台层不得直接调用领域 op：{value}", token.offset)
                    )
            continue
        if token.kind != common.KIND_CODE:
            continue
        for match in _IDENT.finditer(token.text):
            name = match.group(0)
            if name in types:
                hits.append(
                    _Hit(
                        rel,
                        token.line,
                        RULE_DEP6,
                        f"平台层不得出现领域类型：{name}",
                        _offset(token, match.start()),
                    )
                )
        depth = max(0, depth + token.text.count("(") - token.text.count(")"))


def check(root: Path) -> tuple[list[common.Finding], list[str]]:
    """扫描 root 下的 Dart 源码，返回 (findings, 人工复核 warning)。"""
    root = Path(root)
    if not root.is_dir():
        raise common.GateError(None, f"扫描根不是目录：{root}")
    network = _load_network(root)
    symbols = _load_dep6(root)
    patterns = _load_patterns(root)
    hits: list[_Hit] = []
    warnings: list[str] = []
    for rel in _dart_files(root, APP_LIB):
        tokens = source_scan.tokens(root / rel, "dart")
        imports = _imports(tokens)
        in_ui = rel.startswith(UI_PREFIX)
        if in_ui:
            _check_ui_imports(rel, imports, hits)
            _check_ui_types(rel, tokens, hits)
        if not rel.startswith(COMPOSITION_PREFIX):
            _check_ports_http(rel, tokens, hits, warnings)
        if not any(pattern.match(rel) for pattern in network):
            _check_network(rel, imports, tokens, hits)
        if in_ui:
            _check_platform_checks(rel, imports, tokens, patterns, hits, warnings)
        if rel.startswith(PLATFORM_PREFIX):
            _check_platform_symbols(rel, tokens, symbols, hits)
    dep5_tokens = {(hit.path, hit.offset) for hit in hits if hit.rule == RULE_DEP5}
    hits = [
        hit for hit in hits if not (hit.rule == RULE_PRIV1 and (hit.path, hit.offset) in dep5_tokens)
    ]
    hits.sort(key=lambda hit: (hit.path, hit.line, hit.rule, hit.offset))
    findings = [common.Finding(path=hit.path, line=hit.line, rule=hit.rule, message=hit.message) for hit in hits]
    return findings, warnings


def main(argv: list[str]) -> int:
    """命令行入口：配置错误只走 GATE-1，其余按发现数量返回 0/1。"""
    parser = _Parser(prog="check_privacy.py", description="CORE-69 Dart 侧依赖与隐私检查")
    parser.add_argument("--root", default=".", help="仓库根目录")
    try:
        args = parser.parse_args(argv)
        findings, warnings = check(Path(args.root))
    except common.GateError as exc:
        print(exc.format_line(), file=sys.stderr)
        return common.EXIT_GATE
    for warning in warnings:
        print(warning, file=sys.stderr)
    return common.emit(findings)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))