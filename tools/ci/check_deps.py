#!/usr/bin/env python3
"""CORE-69 阶段2：Rust 侧依赖方向与平台隔离检查（DEP-1～4）。

用法：python tools/ci/check_deps.py --root .

退出码：0 无 Finding、1 有 Finding、2 策略/输入错误（只经 GATE-1 单行 stderr 输出）。
"""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

import yaml

import common
import source_scan

RULE_DEP1 = "DEP-1"
RULE_DEP2 = "DEP-2"
RULE_DEP3 = "DEP-3"
RULE_DEP4 = "DEP-4"

POLICY_REL = "contracts/policies/dep-allow.yaml"
MANIFEST_NAME = "Cargo.toml"
SKIP_DIRS = frozenset(
    {"target", "build", ".git", "node_modules", ".dart_tool", "temp", ".venv", "__pycache__", ".idea"}
)
POLICY_KEYS = frozenset({"version", "crates"})
DEP_SECTIONS = ("dependencies", "dev-dependencies", "build-dependencies")

# 卡 SADD/S0/S0_CORE-69_基座.md:39 的常量镜像（检查器不读 SADD）。
DOMAIN_CRATES = frozenset(
    {
        "fml-ast",
        "fml-latex",
        "fml-notation",
        "fml-units",
        "fml-type",
        "fml-eval",
        "fml-derive",
        "fml-typeset",
        "fml-export",
        "fml-srs",
        "fml-grade",
        "fml-study",
        "fml-crypto",
        "fml-sync",
    }
)
STORAGE_CRATES = frozenset({"fml-store", "fml-ffi"})
FFI_SRC_PREFIX = "crates/fml-ffi/src/"

_HEADER = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_ENTRY = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*=\s*(.*)$")
_QUALIFIED = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*::")
_RUST_FS = re.compile(r"\bstd\s*::\s*fs\b")
_RUST_NET = re.compile(r"\bstd\s*::\s*net\b")
_RUST_TIME = re.compile(r"\bstd\s*::\s*time\s*::\s*SystemTime\b")


class _DuplicateKey(Exception):
    """YAML/JSON 解析期的重复键。"""


class _UniqueKeyLoader(yaml.SafeLoader):
    """安全加载器：映射内重复键直接报错。"""


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    loader.flatten_mapping(node)
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise _DuplicateKey(key)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _first_line(exc: BaseException) -> str:
    text = str(exc).strip().splitlines()
    return text[0] if text else exc.__class__.__name__


def _load_yaml(path: Path, rel: str) -> object:
    if not path.is_file():
        raise common.GateError(rel, f"缺少策略文件：{rel}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise common.GateError(rel, f"无法读取策略文件：{_first_line(exc)}") from None
    try:
        return yaml.load(text, Loader=_UniqueKeyLoader)
    except _DuplicateKey as exc:
        raise common.GateError(rel, f"重复的键：{exc.args[0]}") from None
    except yaml.YAMLError as exc:
        raise common.GateError(rel, f"不是合法 YAML：{_first_line(exc)}") from None


def _load_allow(root: Path) -> dict[str, list[str]]:
    data = _load_yaml(root / POLICY_REL, POLICY_REL)
    if not isinstance(data, dict):
        raise common.GateError(POLICY_REL, "策略文件顶层必须是映射")
    unknown = sorted(str(key) for key in data if key not in POLICY_KEYS)
    if unknown:
        raise common.GateError(POLICY_REL, f"未知字段：{', '.join(unknown)}")
    if data.get("version") != 1:
        raise common.GateError(POLICY_REL, f"version 必须为 1，实际为 {data.get('version')!r}")
    crates = data.get("crates")
    if not isinstance(crates, dict):
        raise common.GateError(POLICY_REL, "crates 必须是包名到依赖数组的映射")
    allow: dict[str, list[str]] = {}
    for name in crates:
        if not isinstance(name, str) or not name:
            raise common.GateError(POLICY_REL, "crates 的键必须是非空包名")
        deps = crates[name]
        if not isinstance(deps, list):
            raise common.GateError(POLICY_REL, f"crates.{name} 必须是依赖数组")
        seen: set[str] = set()
        for dep in deps:
            if not isinstance(dep, str) or not dep:
                raise common.GateError(POLICY_REL, f"crates.{name} 的元素必须是非空包名")
            if "*" in dep:
                raise common.GateError(POLICY_REL, f"依赖表不允许通配符：{dep}")
            if dep == name:
                raise common.GateError(POLICY_REL, f"依赖表不允许自依赖：{name}")
            if dep in seen:
                raise common.GateError(POLICY_REL, f"依赖数组存在重复元素：{name} → {dep}")
            seen.add(dep)
        allow[name] = list(deps)
    return allow


def _walk_manifests(root: Path) -> list[Path]:
    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise common.GateError(None, f"无法读取目录：{_first_line(exc)}") from None
        for entry in entries:
            if entry.is_dir():
                if entry.name in SKIP_DIRS or entry.name.startswith("."):
                    continue
                stack.append(entry)
            elif entry.name == MANIFEST_NAME:
                found.append(entry)
    return sorted(found, key=lambda item: item.as_posix())


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_manifest(path: Path, rel: str) -> tuple[dict, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise common.GateError(rel, f"无法读取 Cargo.toml：{_first_line(exc)}") from None
    try:
        return tomllib.loads(text), text
    except tomllib.TOMLDecodeError as exc:
        raise common.GateError(rel, f"不是合法 TOML：{_first_line(exc)}") from None


def _section_lines(text: str) -> dict[tuple[str, ...], dict[str, int]]:
    """把清单文本切成 {节路径: {键: 行号}}，只用于 Finding 定位。"""
    lines = text.splitlines()
    result: dict[tuple[str, ...], dict[str, int]] = {}
    current: tuple[str, ...] = ()
    depth = 0
    for index, line in enumerate(lines, start=1):
        if depth > 0:
            depth += line.count("{") - line.count("}")
            continue
        header = _HEADER.match(line)
        if header:
            current = tuple(part.strip() for part in header.group(1).split("."))
            result.setdefault(current, {})
            continue
        if line.lstrip().startswith("#"):
            continue
        entry = _ENTRY.match(line)
        if entry and current:
            result.setdefault(current, {}).setdefault(entry.group(1), index)
            depth = max(0, entry.group(2).count("{") - entry.group(2).count("}"))
    return result


def _entry_line(sections: dict[tuple[str, ...], dict[str, int]], path: tuple[str, ...], name: str) -> int | None:
    table = sections.get(path)
    if table and name in table:
        return table[name]
    for key, value in sections.items():
        if key[-1:] == path[-1:] and name in value:
            return value[name]
    return None


def _workspace_deps(root: Path) -> dict:
    manifest = root / MANIFEST_NAME
    if not manifest.is_file():
        return {}
    try:
        doc, _text = _read_manifest(manifest, MANIFEST_NAME)
    except common.GateError:
        return {}
    workspace = doc.get("workspace")
    if not isinstance(workspace, dict):
        return {}
    deps = workspace.get("dependencies")
    return deps if isinstance(deps, dict) else {}


def _package_name(doc: dict) -> str | None:
    package = doc.get("package")
    if not isinstance(package, dict):
        return None
    name = package.get("name")
    return name if isinstance(name, str) and name else None


def _iter_sections(doc: dict):
    for section in DEP_SECTIONS:
        table = doc.get(section)
        if isinstance(table, dict):
            for name, spec in table.items():
                yield (section,), name, spec
    targets = doc.get("target")
    if isinstance(targets, dict):
        for cfg, table in targets.items():
            if not isinstance(table, dict):
                continue
            for section in DEP_SECTIONS:
                inner = table.get(section)
                if isinstance(inner, dict):
                    for name, spec in inner.items():
                        yield ("target", cfg, section), name, spec


def _resolve_target(
    spec: object,
    key: str,
    manifest_dir: Path,
    root: Path,
    rel: str,
    workspace_deps: dict,
    name_of: dict[str, str],
) -> str | None:
    """返回本地依赖的真实包名；仓库外/缺清单直接 GATE-1；非本地依赖返回 None。"""
    if not isinstance(spec, dict):
        return None
    if spec.get("workspace") is True:
        inherited = workspace_deps.get(key)
        if inherited is None:
            return key
        spec = inherited
        manifest_dir = root
        if not isinstance(spec, dict):
            return None
    path = spec.get("path")
    if not isinstance(path, str):
        return None
    target = (manifest_dir / path).resolve()
    try:
        inside = target.is_relative_to(root.resolve())
    except AttributeError:  # pragma: no cover - Python < 3.9 兜底
        inside = str(target).startswith(str(root.resolve()))
    if not inside:
        raise common.GateError(rel, f"依赖路径指向仓库外：{path}")
    manifest = target / MANIFEST_NAME
    if not manifest.is_file():
        raise common.GateError(rel, f"依赖路径缺少 Cargo.toml：{path}")
    declared = spec.get("package")
    if isinstance(declared, str) and declared:
        return declared
    return name_of.get(target.as_posix(), key)


def _collect(root: Path, workspace_deps: dict) -> tuple[dict[str, str], list[tuple[str, str, int | None, str]]]:
    manifests = _walk_manifests(root)
    docs: dict[str, tuple[str, Path, dict, str]] = {}
    seen: dict[str, str] = {}
    for path in manifests:
        rel = _rel(root, path)
        doc, text = _read_manifest(path, rel)
        name = _package_name(doc)
        if name is None:
            continue
        if name in seen:
            raise common.GateError(rel, f"重复的包名：{name}（已出现在 {seen[name]}）")
        seen[name] = rel
        docs[name] = (rel, path.parent, doc, text)
    name_of = {path.parent.as_posix(): name for name, (_rel_, path, _doc, _text) in docs.items()}
    edges: list[tuple[str, str, int | None, str]] = []
    for name in sorted(docs):
        rel, directory, doc, text = docs[name]
        sections = _section_lines(text)
        for section_path, key, spec in _iter_sections(doc):
            target = _resolve_target(spec, key, directory, root, rel, workspace_deps, name_of)
            if target is None:
                continue
            edges.append((name, rel, _entry_line(sections, section_path, key), target))
    return seen, edges


def _cycles(nodes: list[str], edges: list[tuple[str, str, int | None, str]]) -> list[list[str]]:
    """Tarjan 强连通分量；返回成员数大于 1 的分量。"""
    graph: dict[str, list[str]] = {name: [] for name in nodes}
    for source, _rel, _line, target in edges:
        graph.setdefault(source, []).append(target)
        graph.setdefault(target, [])
    index_of: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    result: list[list[str]] = []
    counter = 0
    for start in sorted(graph):
        if start in index_of:
            continue
        work = [(start, iter(sorted(graph[start])))]
        index_of[start] = low[start] = counter
        counter += 1
        stack.append(start)
        on_stack.add(start)
        while work:
            node, children = work[-1]
            advanced = False
            for child in children:
                if child not in index_of:
                    index_of[child] = low[child] = counter
                    counter += 1
                    stack.append(child)
                    on_stack.add(child)
                    work.append((child, iter(sorted(graph[child]))))
                    advanced = True
                    break
                if child in on_stack:
                    low[node] = min(low[node], index_of[child])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index_of[node]:
                members = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    members.append(member)
                    if member == node:
                        break
                if len(members) > 1:
                    result.append(sorted(members))
    return result


def _check_edges(
    seen: dict[str, str], edges, allow: dict[str, list[str]]
) -> list[common.Finding]:
    findings: list[common.Finding] = []
    for name in sorted(seen):
        if name not in allow:
            raise common.GateError(POLICY_REL, f"dep-allow.yaml 未登记已实现的包：{name}")
    for source, rel, line, target in edges:
        if source in DOMAIN_CRATES and target in STORAGE_CRATES:
            findings.append(
                common.Finding(rel, line, RULE_DEP3, f"领域 crate 不得依赖 {target}")
            )
        elif target not in allow.get(source, []):
            findings.append(
                common.Finding(rel, line, RULE_DEP1, f"直接依赖 {target} 未登记在 dep-allow.yaml")
            )
    return findings


def _domain_io_findings(rel: str, token_items: list[common.Token]) -> list[common.Finding]:
    findings: list[common.Finding] = []
    bound: dict[str, str] = {}
    for index, token in enumerate(token_items):
        if token.kind != common.KIND_CODE or token.text != "use":
            continue
        rest = []
        for follow in token_items[index + 1 :]:
            if follow.kind != common.KIND_CODE:
                break
            rest.append(follow.text.rstrip(";"))
            if follow.text.endswith(";"):
                break
            if len(rest) > 8:
                break
        if not rest:
            continue
        if len(rest) >= 3 and rest[1] == "as":
            base, name = rest[0], rest[2]
        else:
            base = rest[0]
            name = base.rstrip("{}").split("::")[-1].strip("{},")
        kind = _forbidden_kind(base)
        if kind:
            bound[name] = kind
    for token in token_items:
        if token.kind != common.KIND_CODE:
            continue
        kind = _forbidden_kind(token.text)
        if kind is None:
            for match in _QUALIFIED.finditer(token.text):
                kind = bound.get(match.group(1))
                if kind:
                    break
        if kind:
            findings.append(common.Finding(rel, token.line, RULE_DEP2, f"领域 crate 不得直接使用 {kind}"))
    return findings


def _forbidden_kind(text: str) -> str | None:
    if _RUST_FS.search(text):
        return "std::fs（文件 I/O）"
    if _RUST_NET.search(text):
        return "std::net（网络）"
    if _RUST_TIME.search(text):
        return "std::time::SystemTime（时钟）"
    return None


def _extern_c_findings(rel: str, token_items: list[common.Token]) -> list[common.Finding]:
    findings: list[common.Finding] = []
    for index, token in enumerate(token_items):
        if token.kind != common.KIND_CODE or token.text != "extern":
            continue
        following = token_items[index + 1] if index + 1 < len(token_items) else None
        if following is None or following.kind != common.KIND_STRING:
            continue
        if following.text.strip("'\"") != "C":
            continue
        findings.append(common.Finding(rel, token.line, RULE_DEP4, '只有 fml-ffi 允许出现 extern "C"'))
    return findings


def _rust_file_rules(root: Path) -> list[common.Finding]:
    findings: list[common.Finding] = []
    grouped: dict[str, list[common.Token]] = {}
    crates_dir = root / "crates"
    if not crates_dir.is_dir():
        return findings
    for rel, token in source_scan.scan_tree(crates_dir, {".rs"}):
        grouped.setdefault("crates/" + rel, []).append(token)
    for rel in sorted(grouped):
        parts = rel.split("/")
        if len(parts) < 3 or parts[0] != "crates":
            continue
        items = grouped[rel]
        if parts[1] in DOMAIN_CRATES:
            findings.extend(_domain_io_findings(rel, items))
        if not rel.startswith(FFI_SRC_PREFIX):
            findings.extend(_extern_c_findings(rel, items))
    return findings


def check(root: Path) -> tuple[list[common.Finding], list[str]]:
    """返回 (findings, warnings)；warnings 不影响退出码。"""
    root = Path(root)
    if not root.is_dir():
        raise common.GateError(None, f"扫描根不是目录：{root}")
    allow = _load_allow(root)
    workspace_deps = _workspace_deps(root)
    seen, edges = _collect(root, workspace_deps)
    findings = _check_edges(seen, edges, allow)
    for members in _cycles(sorted(seen), edges):
        rel = seen[members[0]]
        findings.append(
            common.Finding(rel, None, RULE_DEP1, f"本地直接依赖存在环：{'、'.join(members)}")
        )
    findings.extend(_rust_file_rules(root))
    findings.sort(key=lambda item: (item.path, item.line or 0, item.rule, item.message))
    return findings, []


def _root_from_args(argv: list[str]) -> Path:
    root: str | None = None
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--root":
            if index + 1 >= len(argv):
                raise common.GateError(None, "--root 需要一个目录参数")
            root = argv[index + 1]
            index += 2
            continue
        if item.startswith("--root="):
            root = item.split("=", 1)[1]
            index += 1
            continue
        raise common.GateError(None, f"未知参数：{item}")
    return Path(root if root is not None else ".")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        root = _root_from_args(arguments)
        findings, warnings = check(root)
    except common.GateError as exc:
        print(exc.format_line(), file=sys.stderr)
        return common.EXIT_GATE
    for line in warnings:
        print(line, file=sys.stderr)
    return common.emit(findings)


if __name__ == "__main__":
    raise SystemExit(main())