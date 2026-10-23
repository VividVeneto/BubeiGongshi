#!/usr/bin/env python3
"""CORE-74 ERR 族检查器：注册表生成物漂移（ERR-1）、未登记错误码（ERR-2）与注册表重复（ERR-3）。

用法：python tools/ci/check_errors.py [--root <仓库根>] [--registry contracts/errors/registry.yaml]
退出码：0 无发现；1 有发现（ERR-1/ERR-2/ERR-3）；2 门禁错误（GATE-1）。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_REGISTRY = "contracts/errors/registry.yaml"
GEN_ERRORS_NAME = "gen_errors.py"
SCAN_ROOTS = ("crates", "server", "app/lib")
SCAN_SUFFIXES = (".rs", ".dart")
EXCLUDED_DIRS = frozenset(
    {"tests", "benches", "examples", "fixtures", "build", "contracts", "SADD", "installer"}
)
EXCLUDED_SUFFIXES = (".g.dart",)
EXCLUDED_FILES = frozenset({"crates/fml-error/src/codes.rs"})
CODE_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")
DRIFT_RE = re.compile(r"^gen_errors: 生成物漂移 (.+)$")
FINDING_PREFIX = "gen_errors: "
REGISTRY_ERROR = "实现注册表未启用：--registry 指向的 registry.yaml 不存在"
REGISTRY_SHAPE = "注册表不可解析：{reason}"


def _parser(common):
    """构造参数解析器；argparse 的报错转成 GateError。"""
    class _Parser(argparse.ArgumentParser):
        def error(self, message):  # noqa: D102 - 覆盖基类
            raise common.GateError(None, message)

    parser = _Parser(prog="check_errors.py", description=__doc__)
    parser.add_argument("--root", default=None, help="仓库根目录（缺省为本脚本上溯两级）")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY, help="错误码注册表路径")
    return parser


def _load_yaml(common):
    """按需导入 PyYAML。"""
    try:
        import yaml  # noqa: PLC0415 - 延迟导入以便给出 GateError
    except ImportError as exc:  # pragma: no cover - 环境缺依赖
        raise common.GateError(None, f"依赖 PyYAML 不可用：{exc}") from exc
    return yaml


def _registry_entries(common, yaml, path):
    """读取注册表条目：[(code, message_key, line)]，行号取条目起点。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise common.GateError(str(path), f"注册表不可读：{exc.strerror}") from exc
    try:
        root = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError as exc:
        raise common.GateError(str(path), REGISTRY_SHAPE.format(reason=exc)) from exc
    if not isinstance(root, yaml.MappingNode):
        raise common.GateError(str(path), REGISTRY_SHAPE.format(reason="顶层必须是映射"))
    entries_node = None
    for key, value in root.value:
        if getattr(key, "value", None) == "entries":
            entries_node = value
            break
    if not isinstance(entries_node, yaml.SequenceNode):
        raise common.GateError(str(path), REGISTRY_SHAPE.format(reason="entries 必须是列表"))
    entries = []
    for item in entries_node.value:
        if not isinstance(item, yaml.MappingNode):
            raise common.GateError(str(path), REGISTRY_SHAPE.format(reason="entries 元素必须是映射"))
        fields = {}
        line = item.start_mark.line + 1
        for key, value in item.value:
            if getattr(key, "value", None) in ("code", "message_key"):
                fields[key.value] = getattr(value, "value", None)
                line = key.start_mark.line + 1
        code = fields.get("code")
        if not isinstance(code, str):
            raise common.GateError(str(path), REGISTRY_SHAPE.format(reason="条目缺少 code"))
        entries.append((code, fields.get("message_key"), line))
    if not entries:
        raise common.GateError(str(path), REGISTRY_SHAPE.format(reason="entries 为空"))
    return entries


def _duplicates(common, label, entries):
    """ERR-3：同一 code 多条、或同一 message_key 多码。"""
    findings = []
    seen_codes = {}
    seen_keys = {}
    for code, message_key, line in entries:
        seen_codes.setdefault(code, []).append(line)
        if isinstance(message_key, str):
            seen_keys.setdefault(message_key, []).append((code, line))
    for code, lines in seen_codes.items():
        if len(lines) > 1:
            findings.append(
                common.Finding(label, lines[1], "ERR-3", f"错误码 {code} 在注册表中重复登记")
            )
    for key, owners in seen_keys.items():
        codes = sorted({code for code, _line in owners})
        if len(codes) > 1:
            code, line = owners[1]
            findings.append(
                common.Finding(
                    label, line, "ERR-3", f"message_key {key} 被多个错误码共用：{'、'.join(codes)}"
                )
            )
    findings.sort(key=lambda finding: (finding.line or 0, finding.message))
    return findings


def _scan_files(root):
    """返回需要扫描源码的相对路径（POSIX 形式），按字典序。"""
    found = []
    for scan_root in SCAN_ROOTS:
        base = root / scan_root
        if not base.is_dir():
            continue
        for current, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(name for name in dirnames if name not in EXCLUDED_DIRS)
            for name in sorted(filenames):
                if not name.endswith(SCAN_SUFFIXES):
                    continue
                if name.endswith(EXCLUDED_SUFFIXES):
                    continue
                relative = (Path(current) / name).relative_to(root).as_posix()
                if relative in EXCLUDED_FILES:
                    continue
                found.append(relative)
    return sorted(found)


def _unquote(text):
    """去掉字符串字面量的引号与前缀，返回其内容。"""
    body = text
    for prefix in ("r#", "r", "b", "br", "rb"):
        if body.startswith(prefix) and len(body) > len(prefix) + 1 and body[len(prefix)] in "\"'":
            body = body[len(prefix) :]
            break
    for quote in ('"""', "'''", '"', "'"):
        if body.startswith(quote) and body.endswith(quote) and len(body) >= 2 * len(quote):
            return body[len(quote) : -len(quote)]
    return body


def _unknown_codes(common, source_scan, root, codes, prefixes):
    """ERR-2：字符串字面量中形如已登记命名空间前缀、但未登记的码。"""
    findings = []
    for relative in _scan_files(root):
        path = root / relative
        for token in source_scan.tokens(path):
            if token.kind != common.KIND_STRING:
                continue
            text = _unquote(token.text)
            if not CODE_RE.match(text) or text in codes:
                continue
            if text.split("_", 1)[0] not in prefixes:
                continue
            if text.startswith("FML_"):
                continue
            findings.append(
                common.Finding(relative, token.line, "ERR-2", f"错误码 {text} 未在 registry.yaml 登记")
            )
    return findings


def _gen_root(common, registry):
    """由 registry 路径反推 gen_errors.py 的 --root。"""
    if registry.name != "registry.yaml" or registry.parent.name != "errors":
        raise common.GateError(str(registry), "注册表必须是 <root>/contracts/errors/registry.yaml")
    if registry.parent.parent.name != "contracts":
        raise common.GateError(str(registry), "注册表必须是 <root>/contracts/errors/registry.yaml")
    return registry.parents[2]


def _drift_findings(common, root, registry):
    """ERR-1：调用真实 gen_errors.py --check，把漂移行转成 Finding。"""
    script = Path(__file__).with_name(GEN_ERRORS_NAME)
    if not script.is_file():
        raise common.GateError(None, f"缺少生成器 {GEN_ERRORS_NAME}：无法校验生成物")
    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, str(script), "--check", "--root", str(root)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        check=False,
    )
    stderr = (completed.stderr or "").strip()
    if completed.returncode == 0:
        return []
    if completed.returncode != 1:
        message = stderr[len(FINDING_PREFIX) :] if stderr.startswith(FINDING_PREFIX) else stderr
        raise common.GateError(str(registry), message or "gen_errors.py 执行失败")
    findings = []
    for line in stderr.splitlines():
        match = DRIFT_RE.match(line.strip())
        if match:
            findings.append(
                common.Finding(match.group(1), None, "ERR-1", "生成物与 registry.yaml 不一致")
            )
    if not findings:
        raise common.GateError(str(registry), stderr or "gen_errors.py 报告漂移但未给出生成物路径")
    return findings


def _findings(common, source_scan, yaml, root, registry):
    """汇总三类检查。"""
    if not registry.is_file():
        raise common.GateError(str(registry), REGISTRY_ERROR)
    entries = _registry_entries(common, yaml, registry)
    duplicates = _duplicates(common, str(registry), entries)
    if duplicates:
        return duplicates
    codes = {code for code, _key, _line in entries}
    prefixes = {code.split("_", 1)[0] for code in codes}
    findings = _drift_findings(common, _gen_root(common, registry), registry)
    findings.extend(_unknown_codes(common, source_scan, root, codes, prefixes))
    return findings


def main(argv=None):
    """脚本入口；延迟导入 CORE-69 的 common/source_scan。"""
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        import common  # noqa: PLC0415 - 延迟导入以便给出 GateError
        import source_scan  # noqa: PLC0415
        import yaml  # noqa: PLC0415
    except ImportError as exc:
        sys.stderr.write(f"-: GATE-1 依赖 CORE-69 的 common/source_scan 尚未交付：{exc}\n")
        return 2
    parser = _parser(common)
    try:
        options = parser.parse_args(arguments)
        root = Path(options.root).resolve() if options.root else Path(__file__).parents[2]
        registry_option = Path(options.registry)
        registry = (
            registry_option if registry_option.is_absolute() else (root / registry_option).resolve()
        )
        findings = _findings(common, source_scan, yaml, root, registry)
    except common.GateError as error:
        sys.stderr.write(error.format_line() + "\n")
        return common.EXIT_GATE
    return common.emit(findings)


if __name__ == "__main__":
    sys.exit(main())
