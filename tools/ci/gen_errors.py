#!/usr/bin/env python3
"""从 `contracts/errors/registry.yaml` 生成错误码制品。

生成物（按 `code` 升序，结果确定，连续运行逐字节一致）：

- `crates/fml-error/src/codes.rs`
- `app/lib/binding/error_codes.g.dart`
- `contracts/errors/README.md`
- `contracts/errors/ownership.yaml`
- `contracts/policies/shared-writes.json` 的 error 投影（其他类别保持原样）

退出码：0 生成成功或 `--check` 无漂移；1 `--check` 检出漂移；2 输入或环境错误
（registry 或 arb 不可解析、缺 PyYAML、结构校验失败）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - 环境错误，由 main 转成退出码 2
    yaml = None

EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_INPUT = 2

REGISTRY_PATH = "contracts/errors/registry.yaml"
ARB_PATH = "app/lib/l10n/errors_zh.arb"
OWNERSHIP_PATH = "contracts/errors/ownership.yaml"
README_PATH = "contracts/errors/README.md"
SHARED_WRITES_PATH = "contracts/policies/shared-writes.json"
CODES_RS_PATH = "crates/fml-error/src/codes.rs"
DART_PATH = "app/lib/binding/error_codes.g.dart"

NAMESPACES = (
    "AST", "CONTENT", "PARSE", "TYPE", "NOTATION", "UNIT", "EVAL", "ENGINE",
    "DERIVE", "TYPESET", "EXPORT", "STORE", "LIB", "PACK", "STUDY", "GRADE",
    "CRYPTO", "AUTH", "SYNC", "BACKUP", "PRIVACY", "RECOG", "IMG", "CLOUD",
    "FFI", "PLATFORM", "NET", "SERVER",
)

ENTRY_FIELDS = frozenset({
    "code", "namespace", "owner", "severity", "message_key", "fix_hint",
    "retryable", "since", "deprecated_since", "surface", "http_status",
})

REQUIRED_FIELDS = (
    "code", "namespace", "owner", "severity", "message_key", "retryable",
    "since", "surface",
)

CODE_RE = re.compile(r"^[A-Z]+(_[A-Z0-9]+)+$")
OWNER_RE = re.compile(r"^(CORE|AND|WIN)-[0-9]{2}$")

SEVERITY_TO_RUST = {"error": "Error", "warning": "Warning", "info": "Info"}
SURFACES = ("client", "server", "both")
DEFAULT_HTTP_STATUS = 400
HTTP_STATUS_MIN = 400
HTTP_STATUS_MAX = 599


class InputError(Exception):
    """注册表、消息资源或环境的输入错误（退出码 2）。"""


def derive_message_key(code: str) -> str:
    """按首个下划线切分命名空间与余部，分别小写并以点连接。"""
    namespace, _, rest = code.partition("_")
    return "err." + namespace.lower() + "." + rest.lower()


def derive_domain(code: str) -> str:
    """命名空间前缀去下划线小写。"""
    return code.partition("_")[0].lower()


def variant_of(code: str) -> str:
    """按注册表 code 生成变体名：每段 ASCII 小写后首字母大写。"""
    return "".join(part.lower().capitalize() for part in code.split("_"))


def _where(code: Any, index: int) -> str:
    if isinstance(code, str) and code:
        return "条目 " + code + " "
    return "第 " + str(index + 1) + " 条 "


def _require_str(raw: dict[str, Any], key: str, where: str) -> str:
    value = raw[key]
    if not isinstance(value, str):
        raise InputError(where + "的 " + key + " 必须是字符串")
    if not value:
        raise InputError(where + "的 " + key + " 不得为空")
    return value


def _require_bool(raw: dict[str, Any], key: str, where: str) -> bool:
    value = raw[key]
    if not isinstance(value, bool):
        raise InputError(where + "的 " + key + " 必须是布尔值")
    return value


def _require_int(raw: dict[str, Any], key: str, where: str) -> int:
    value = raw[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise InputError(where + "的 " + key + " 必须是整数")
    return value


def load_yaml_text(path: Path) -> Any:
    """读并解析 YAML，失败转 InputError。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError("无法读取 " + str(path) + "：" + str(exc)) from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise InputError("无法解析 " + str(path) + "：" + str(exc)) from exc


def load_registry(path: Path) -> tuple[int, list[Any]]:
    """读 registry.yaml 顶层并校验结构。"""
    document = load_yaml_text(path)
    if not isinstance(document, dict):
        raise InputError(str(path) + " 顶层必须是映射")
    unknown = sorted(str(key) for key in set(document) - {"registry_version", "entries"})
    if unknown:
        raise InputError("registry.yaml 顶层含未知字段：" + "、".join(unknown))
    for key in ("registry_version", "entries"):
        if key not in document:
            raise InputError("registry.yaml 缺字段 " + key)
    version = document["registry_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise InputError("registry_version 必须是 ≥ 1 的整数")
    entries = document["entries"]
    if not isinstance(entries, list) or not entries:
        raise InputError("registry.yaml 的 entries 必须是非空列表")
    return version, entries


def load_arb(path: Path) -> dict[str, Any]:
    """读简中消息资源 errors_zh.arb。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError("无法读取 " + str(path) + "：" + str(exc)) from exc
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError("无法解析 " + str(path) + "：" + str(exc)) from exc
    if not isinstance(document, dict):
        raise InputError(str(path) + " 顶层必须是对象")
    return document


def validate_entries(
    version: int, raw_entries: list[Any], arb: dict[str, Any]
) -> list[dict[str, Any]]:
    """校验全部条目与消息资源，返回按 code 升序的规范化结果。"""
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    variants: dict[str, str] = {}
    for index, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            raise InputError("第 " + str(index + 1) + " 条必须是映射")
        where = _where(raw.get("code"), index)
        unknown = sorted(str(key) for key in set(raw) - ENTRY_FIELDS)
        if unknown:
            raise InputError(where + "含未知字段：" + "、".join(unknown))
        for key in REQUIRED_FIELDS:
            if key not in raw:
                raise InputError(where + "缺字段 " + key)

        code = _require_str(raw, "code", where)
        where = "条目 " + code + " "
        if not CODE_RE.match(code):
            raise InputError(where + "的 code 不符合 ^[A-Z]+(_[A-Z0-9]+)+$")
        if code in seen:
            raise InputError("重复的 code：" + code)
        seen.add(code)

        namespace = _require_str(raw, "namespace", where)
        if namespace not in NAMESPACES:
            raise InputError(where + "的 namespace 不在命名空间列表中：" + namespace)
        actual = code.partition("_")[0]
        if actual != namespace:
            raise InputError(where + "的 code 首段 " + actual + " 与 namespace " + namespace + " 不符")

        owner = _require_str(raw, "owner", where)
        if not OWNER_RE.match(owner):
            raise InputError(where + r"的 owner 不符合卡号格式 ^(CORE|AND|WIN)-\d{2}$：" + owner)

        severity = _require_str(raw, "severity", where)
        if severity not in SEVERITY_TO_RUST:
            raise InputError(where + "的 severity 必须是 error/warning/info：" + severity)

        message_key = _require_str(raw, "message_key", where)
        expected_key = derive_message_key(code)
        if message_key != expected_key:
            raise InputError(where + "的 message_key 必须是派生值 " + expected_key)

        fix_hint = _require_bool(raw, "fix_hint", where) if "fix_hint" in raw else False
        retryable = _require_bool(raw, "retryable", where)

        since = _require_int(raw, "since", where)
        if not 1 <= since <= version:
            raise InputError(where + "的 since 必须在 1..registry_version(" + str(version) + ") 内")

        deprecated_since = None
        if "deprecated_since" in raw:
            deprecated_since = _require_int(raw, "deprecated_since", where)
            if not since <= deprecated_since <= version:
                raise InputError(where + "的 deprecated_since 必须在 since..registry_version 内")

        surface = _require_str(raw, "surface", where)
        if surface not in SURFACES:
            raise InputError(where + "的 surface 必须是 client/server/both：" + surface)
        http_status = None
        if "http_status" in raw:
            http_status = _require_int(raw, "http_status", where)
            if surface == "client":
                raise InputError(where + "的 surface 为 client 时不得填 http_status")
            if not HTTP_STATUS_MIN <= http_status <= HTTP_STATUS_MAX:
                raise InputError(where + "的 http_status 必须在 400..599 内")
        elif surface != "client":
            http_status = DEFAULT_HTTP_STATUS

        variant = variant_of(code)
        if variant in variants:
            raise InputError("变体名冲突：" + variants[variant] + " 与 " + code + " 都转换为 " + variant)
        variants[variant] = code

        entries.append(
            {
                "code": code,
                "owner": owner,
                "severity": severity,
                "message_key": message_key,
                "fix_hint": fix_hint,
                "retryable": retryable,
                "since": since,
                "deprecated_since": deprecated_since,
                "surface": surface,
                "http_status": http_status,
                "variant": variant,
                "domain": derive_domain(code),
            }
        )

    entries.sort(key=lambda entry: entry["code"])
    validate_messages(entries, arb)
    return entries


def validate_messages(entries: list[dict[str, Any]], arb: dict[str, Any]) -> None:
    """消息资源：基键存在、fix_hint 有 .fix、无孤儿 .fix 键。"""
    base_keys = {entry["message_key"] for entry in entries}
    fix_keys = {entry["message_key"] for entry in entries if entry["fix_hint"]}
    code_of = {entry["message_key"]: entry["code"] for entry in entries}
    for entry in entries:
        key = entry["message_key"]
        if key not in arb:
            raise InputError("条目 " + entry["code"] + " 的消息键缺失：" + key)
        if entry["fix_hint"] and key + ".fix" not in arb:
            raise InputError("条目 " + entry["code"] + " 声明 fix_hint 但缺消息键：" + key + ".fix")
    for key in arb:
        if not key.endswith(".fix"):
            continue
        base = key[: -len(".fix")]
        if base not in base_keys:
            raise InputError("孤儿修复建议消息键（基键不是已登记码）：" + key)
        if base not in fix_keys:
            raise InputError("条目 " + code_of[base] + " 未声明 fix_hint，但存在多余消息键：" + key)


CODES_RS_TEMPLATE = """//! 由 `tools/ci/gen_errors.py` 从 `contracts/errors/registry.yaml` 生成的错误码表。
//!
//! 请勿手工编辑：先改注册表，再运行 `python tools/ci/gen_errors.py`。

use std::fmt;
use std::str::FromStr;

use serde::{Deserialize, Deserializer, Serialize, Serializer};

use crate::Severity;

/// 注册表中不存在的错误码：解析失败时返回，不 panic、不回退、不丢未知值。
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct UnknownErrorCode;

#[rustfmt::skip]
impl fmt::Display for UnknownErrorCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { f.write_str("错误码未在 registry.yaml 中登记") }
}

impl std::error::Error for UnknownErrorCode {}

/// 一条错误码在注册表中的元数据。
struct Meta {
    code: &'static str,
    domain: &'static str,
    severity: Severity,
    retryable: bool,
    message_key: &'static str,
    fix_hint: bool,
    surface: &'static str,
    http_status: Option<u16>,
}

/// 注册表元数据，按 `code` 升序，与 `ErrorCode` 的声明顺序一致。
#[rustfmt::skip]
static META: &[Meta] = &[
@META@
];

/// 全部已登记错误码，按注册表 `code` 升序。
#[rustfmt::skip]
static ALL: &[ErrorCode] = &[
@ALL@
];

/// 注册表登记的错误码：声明顺序与注册表 `code` 升序一致，`meta()` 按该顺序取元数据。
#[rustfmt::skip]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum ErrorCode {
@VARIANTS@
}

#[rustfmt::skip]
impl ErrorCode {
    /// 注册表中该码的元数据；枚举声明顺序与 META 一致，故按判别值索引。
    fn meta(self) -> &'static Meta { &META[self as usize] }

    /// 全部已登记错误码，按注册表 `code` 升序。
    pub fn all() -> impl Iterator<Item = ErrorCode> { ALL.iter().copied() }

    /// 注册表 `code` 原文。
    pub fn as_str(self) -> &'static str { self.meta().code }

    /// 调度域：`code` 首段的小写形式。
    pub fn domain(self) -> &'static str { self.meta().domain }

    /// 注册表 `severity`。
    pub fn severity(self) -> Severity { self.meta().severity }

    /// 注册表 `retryable`。
    pub fn retryable(self) -> bool { self.meta().retryable }

    /// 简中消息键。
    pub fn message_key(self) -> &'static str { self.meta().message_key }

    /// 是否有修复建议消息 `message_key + ".fix"`。
    pub fn fix_hint(self) -> bool { self.meta().fix_hint }

    /// 注册表 `surface` 原文：`client`、`server` 或 `both`。
    pub fn surface(&self) -> &'static str { self.meta().surface }

    /// 该码是否可能由服务端输出（`server` 或 `both`）。
    pub fn is_server_output(self) -> bool { matches!(self.meta().surface, "server" | "both") }

    /// 服务端 HTTP 状态码：纯端侧码为 `None`，服务端码未声明时为 400。
    pub fn http_status(self) -> Option<u16> { self.meta().http_status }
}

#[rustfmt::skip]
impl fmt::Display for ErrorCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { f.write_str((*self).as_str()) }
}

#[rustfmt::skip]
impl FromStr for ErrorCode {
    type Err = UnknownErrorCode;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
@FROM_STR@
            _ => Err(UnknownErrorCode),
        }
    }
}

#[rustfmt::skip]
impl TryFrom<&str> for ErrorCode {
    type Error = UnknownErrorCode;

    fn try_from(value: &str) -> Result<Self, Self::Error> { value.parse() }
}

#[rustfmt::skip]
impl Serialize for ErrorCode {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(self.as_str())
    }
}

#[rustfmt::skip]
impl<'de> Deserialize<'de> for ErrorCode {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        String::deserialize(deserializer)?.parse::<ErrorCode>().map_err(serde::de::Error::custom)
    }
}
"""


def rust_bool(value: bool) -> str:
    """Rust 布尔字面量。"""
    return "true" if value else "false"


def render_codes_rs(entries: list[dict[str, Any]]) -> str:
    """渲染 crates/fml-error/src/codes.rs。"""
    meta_lines = []
    all_lines = []
    variant_lines = []
    from_str_lines = []
    for entry in entries:
        status = "None" if entry["http_status"] is None else "Some(" + str(entry["http_status"]) + ")"
        meta_lines.append(
            '    Meta { code: "' + entry["code"] + '", domain: "' + entry["domain"]
            + '", severity: Severity::' + SEVERITY_TO_RUST[entry["severity"]]
            + ", retryable: " + rust_bool(entry["retryable"])
            + ', message_key: "' + entry["message_key"] + '", fix_hint: ' + rust_bool(entry["fix_hint"])
            + ', surface: "' + entry["surface"] + '", http_status: ' + status + " },"
        )
        all_lines.append("    ErrorCode::" + entry["variant"] + ",")
        variant_lines.append("    /// " + entry["code"] + "（owner " + entry["owner"] + "）。")
        variant_lines.append("    " + entry["variant"] + ",")
        from_str_lines.append(
            '            "' + entry["code"] + '" => Ok(ErrorCode::' + entry["variant"] + "),"
        )
    return (
        CODES_RS_TEMPLATE.replace("@META@", "\n".join(meta_lines))
        .replace("@ALL@", "\n".join(all_lines))
        .replace("@VARIANTS@", "\n".join(variant_lines))
        .replace("@FROM_STR@", "\n".join(from_str_lines))
    )


DART_TEMPLATE = """// 由 tools/ci/gen_errors.py 从 contracts/errors/registry.yaml 生成，请勿手工编辑。
// registry_version: @VERSION@；改错误码请先改注册表再重新生成。

/// 一条错误码的注册表元数据。
final class ErrorCodeMeta {
  /// 创建一条注册表元数据。
  const ErrorCodeMeta({
    required this.code,
    required this.domain,
    required this.severity,
    required this.retryable,
    required this.messageKey,
    required this.fixHint,
    required this.surface,
    this.httpStatus,
  });

  /// 注册表 code 原文。
  final String code;

  /// 调度域：code 首段的小写形式。
  final String domain;

  /// 注册表 severity：error、warning 或 info。
  final String severity;

  /// 注册表 retryable。
  final bool retryable;

  /// 简中消息键。
  final String messageKey;

  /// 是否有修复建议消息 messageKey + '.fix'。
  final bool fixHint;

  /// 注册表 surface：client、server 或 both。
  final String surface;

  /// 服务端 HTTP 状态码；纯端侧码为 null。
  final int? httpStatus;
}

/// 注册表全部错误码元数据，按 code 升序。
// dart format off
const List<ErrorCodeMeta> errorCodeRegistry = <ErrorCodeMeta>[
@ENTRIES@
];
// dart format on
"""


def render_dart(entries: list[dict[str, Any]], version: int) -> str:
    """渲染 app/lib/binding/error_codes.g.dart。"""
    lines = []
    for entry in entries:
        status = "null" if entry["http_status"] is None else str(entry["http_status"])
        lines.append(
            "  ErrorCodeMeta(code: '" + entry["code"] + "', domain: '" + entry["domain"]
            + "', severity: '" + entry["severity"] + "', retryable: "
            + ("true" if entry["retryable"] else "false")
            + ", messageKey: '" + entry["message_key"] + "', fixHint: "
            + ("true" if entry["fix_hint"] else "false")
            + ", surface: '" + entry["surface"] + "', httpStatus: " + status + "),"
        )
    return DART_TEMPLATE.replace("@VERSION@", str(version)).replace("@ENTRIES@", "\n".join(lines))


def render_readme(entries: list[dict[str, Any]], version: int) -> str:
    """渲染 contracts/errors/README.md 的完整错误码表。"""
    lines = [
        "# 错误码注册表",
        "",
        "本目录由 CORE-02 维护：`registry.yaml` 是错误码元数据的唯一真源，其余文件都是",
        "`python tools/ci/gen_errors.py` 生成的镜像，不接受手改。",
        "",
        "- 新增或修改错误码：先改 `registry.yaml` 与 `app/lib/l10n/errors_zh.arb`，再运行生成器。",
        "- 生成物：`crates/fml-error/src/codes.rs`、`app/lib/binding/error_codes.g.dart`、",
        "  `contracts/errors/ownership.yaml`、本文件与 `contracts/policies/shared-writes.json` 的 error 投影。",
        "- 漂移检查：`python tools/ci/gen_errors.py --check`（0 无漂移、1 漂移、2 输入或环境错误）。",
        "",
        "当前 `registry_version`：" + str(version) + "，共 " + str(len(entries)) + " 条。",
        "",
        "| code | owner | severity | retryable | surface | http_status | fix_hint |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        status = "-" if entry["http_status"] is None else str(entry["http_status"])
        code = "`" + entry["code"] + "`"
        if entry["deprecated_since"] is not None:
            code += "（自 v" + str(entry["deprecated_since"]) + " 废弃）"
        lines.append(
            "| " + code + " | " + entry["owner"] + " | " + entry["severity"]
            + " | " + ("是" if entry["retryable"] else "否")
            + " | " + entry["surface"] + " | " + status
            + " | " + ("是" if entry["fix_hint"] else "否") + " |"
        )
    return "\n".join(lines) + "\n"


def render_ownership(entries: list[dict[str, Any]]) -> str:
    """渲染 contracts/errors/ownership.yaml：只有 code 与 owner。"""
    lines = ["# 由 tools/ci/gen_errors.py 从 contracts/errors/registry.yaml 生成，请勿手工编辑。", "version: 1", "entries:"]
    for entry in entries:
        lines.append("  - code: " + entry["code"])
        lines.append("    owner: " + entry["owner"])
    return "\n".join(lines) + "\n"


def render_shared_writes(root: Path, entries: list[dict[str, Any]]) -> str:
    """更新 shared-writes.json 的 error 投影，保留其他类别原序不变。"""
    path = root / SHARED_WRITES_PATH
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputError("无法读取 " + str(path) + "：" + str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise InputError("无法解析 " + str(path) + "：" + str(exc)) from exc
    if not isinstance(document, dict) or not isinstance(document.get("entries"), list):
        raise InputError(str(path) + " 必须是含 entries 列表的对象")
    others = [item for item in document["entries"] if item.get("kind") != "error"]
    errors = [
        {"kind": "error", "key": entry["code"], "owner": entry["owner"], "point": REGISTRY_PATH}
        for entry in entries
    ]
    document["entries"] = errors + others
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def collect_outputs(root: Path) -> dict[str, str]:
    """校验输入并返回全部生成物的期望内容。"""
    if yaml is None:
        raise InputError("缺 PyYAML，请按 tools/requirements.txt 安装")
    version, raw_entries = load_registry(root / REGISTRY_PATH)
    arb = load_arb(root / ARB_PATH)
    entries = validate_entries(version, raw_entries, arb)
    return {
        CODES_RS_PATH: render_codes_rs(entries),
        DART_PATH: render_dart(entries, version),
        README_PATH: render_readme(entries, version),
        OWNERSHIP_PATH: render_ownership(entries),
        SHARED_WRITES_PATH: render_shared_writes(root, entries),
    }


def main(argv: list[str] | None = None) -> int:
    """命令行入口：生成或检查漂移。"""
    parser = argparse.ArgumentParser(description="从错误码注册表生成 Rust、Dart 与契约镜像。")
    parser.add_argument("--check", action="store_true", help="只比较不写盘；漂移时退出码 1")
    parser.add_argument("--root", default=None, help="仓库根，缺省为脚本上溯两级")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    try:
        outputs = collect_outputs(root)
    except InputError as exc:
        print("gen_errors: " + str(exc), file=sys.stderr)
        return EXIT_INPUT

    if args.check:
        drifted = []
        for relative, expected in outputs.items():
            try:
                actual = (root / relative).read_text(encoding="utf-8")
            except OSError:
                drifted.append(relative)
                continue
            if actual != expected:
                drifted.append(relative)
        for relative in drifted:
            print("gen_errors: 生成物漂移 " + relative, file=sys.stderr)
        if drifted:
            return EXIT_DRIFT
        print("gen_errors: 无漂移，共 " + str(len(outputs)) + " 个生成物")
        return EXIT_OK

    changed = []
    for relative, expected in outputs.items():
        target = root / relative
        try:
            actual = target.read_text(encoding="utf-8")
        except OSError:
            actual = None
        if actual == expected:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(expected, encoding="utf-8", newline="\n")
        changed.append(relative)
    for relative in changed:
        print("gen_errors: 已更新 " + relative)
    if not changed:
        print("gen_errors: 生成物已是最新，共 " + str(len(outputs)) + " 个")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
