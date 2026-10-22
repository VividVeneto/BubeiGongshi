#!/usr/bin/env python3
"""CORE-100：DTO schema 编译、类型图与严格校验（下层库）。

`compile_manifest` 把 `contracts/dto/manifest.json` 与受限 JSON Schema
2020-12 子集编译成可信类型图，供 CORE-67 的 Dart 生成器消费（ADR-V5-55/56）：

* 只读清单与其引用的 schema 文件：不读 `SADD/`、不 import 其它工具、不写文件、
  不设退出码、不提供 CLI。
* 失败时返回 `valid=False` 的 SchemaBundle：`ready`/`nodes`/`named` 必须为空，
  诊断至少含一条 `error`。
* 清单本身不可读（含权限）原样抛出 `OSError`；本库自身缺陷或依赖不可用抛
  `SchemaToolError`。两者都不得写成 `valid=false`。

诊断 `code` 是稳定标识（CORE-67 原样透传，不改写）；`source` 是
`contracts/dto` 下的相对 POSIX 路径；`pointer` 是 JSON Pointer。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

__all__ = [ "STAGES", "Stage", "SchemaRef", "SchemaScalar", "SchemaLimits", "SchemaField",
    "SchemaCase", "SchemaNode", "ReadySchemaOp", "PendingSchemaOp", "SchemaDiagnostic",
    "SchemaToolError", "SchemaBundle", "compile_manifest",
]

Stage = Literal["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"]
STAGES: tuple[Stage, ...] = ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7")

ScalarKind = Literal["string", "integer", "number", "boolean", "null"]
NodeKind = Literal[ "object", "map", "array", "tuple", "union", "ref",
    "string", "integer", "number", "boolean", "null",
]
Format = Literal[ "uuid", "date-time", "int64", "uint64", "int128", "positive-int128",
    "decimal", "base64",
]

_SCOPES = frozenset({"none", "device", "profile"})
_MODES = frozenset({"call", "submit"})
_STATUSES = frozenset({"ready", "pending"})
_SCALAR_KINDS = frozenset({"string", "integer", "number", "boolean", "null"})
_KIND_SET = _SCALAR_KINDS | frozenset({"object", "array"})
FORMATS: tuple[Format, ...] = (
    "uuid", "date-time", "int64", "uint64", "int128", "positive-int128", "decimal", "base64",
)
DIALECT = "https://json-schema.org/draft/2020-12/schema"
ENGINE_SNAPSHOT_CODE = "ENGINE_UNAVAILABLE"
MANIFEST_SOURCE = "contracts/dto/manifest.json"

#: CORE-03 统一信封/句柄/取消码的归属集合（按 CORE-03 卡错误码表 owner 列，
#: 不按 FFI_ 前缀猜）。本库只拒绝这些码，不维护逐 op 集合。
CORE03_OWNED_CODES = frozenset({ "FFI_BAD_ARG", "FFI_BUSY", "FFI_PANIC", "FFI_STALE_HANDLE",
    "FFI_UNKNOWN_OP", "FFI_VERSION_MISMATCH", })

# 诊断码（稳定标识）。
D_MANIFEST_JSON = "MANIFEST_JSON"
D_MANIFEST_SHAPE = "MANIFEST_SHAPE"
D_MANIFEST_KEY = "MANIFEST_KEY"
D_MANIFEST_OP = "MANIFEST_OP"
D_MANIFEST_OWNER = "MANIFEST_OWNER"
D_MANIFEST_STAGE = "MANIFEST_STAGE"
D_MANIFEST_STATUS = "MANIFEST_STATUS"
D_MANIFEST_MODE = "MANIFEST_MODE"
D_MANIFEST_SCOPE = "MANIFEST_SCOPE"
D_MANIFEST_SCHEMA = "MANIFEST_SCHEMA"
D_MANIFEST_BLOCKED = "MANIFEST_BLOCKED_REASON"
D_MANIFEST_CODES = "MANIFEST_ERROR_CODES"
D_MANIFEST_PATHS = "MANIFEST_SENSITIVE_PATHS"
D_MANIFEST_SNAPSHOT = "MANIFEST_SNAPSHOT"
D_MANIFEST_GATE = "MANIFEST_STAGE_GATE"
D_MANIFEST_SKIP = "MANIFEST_STAGE_SKIP"
D_SCHEMA_JSON = "SCHEMA_JSON"
D_SCHEMA_KEYWORD = "SCHEMA_KEYWORD"
D_SCHEMA_TYPE = "SCHEMA_TYPE"
D_SCHEMA_SHAPE = "SCHEMA_SHAPE"
D_SCHEMA_REF = "SCHEMA_REF"
D_SCHEMA_TITLE = "SCHEMA_TITLE"
D_SCHEMA_OBJECT = "SCHEMA_OBJECT"
D_SCHEMA_MAP = "SCHEMA_MAP"
D_SCHEMA_ARRAY = "SCHEMA_ARRAY"
D_SCHEMA_UNION = "SCHEMA_UNION"
D_SCHEMA_NULLABLE = "SCHEMA_NULLABLE"
D_SCHEMA_LIMITS = "SCHEMA_LIMITS"
D_SCHEMA_FORMAT = "SCHEMA_FORMAT"
D_SCHEMA_NAME = "SCHEMA_NAME"
D_SCHEMA_EXAMPLE = "SCHEMA_EXAMPLE"

_ANNOTATIONS = frozenset({
    "title", "description", "examples", "default", "writeOnly", "x-sensitive", })
_STRUCTURAL = frozenset({ "type", "properties", "required", "additionalProperties", "items",
    "prefixItems", "minimum", "maximum", "minLength", "maxLength", "pattern",
    "minItems", "maxItems", "format", "enum", "const", "oneOf", "$ref", "$defs", "$schema", })
_KEYS = _ANNOTATIONS | _STRUCTURAL
_ROOT_KEYS = frozenset({"$schema", "title", "description", "$defs", "examples", "$ref"})
_REF_SIBLINGS = frozenset({"title", "description"})
_NULL_BRANCH_KEYS = frozenset({"type", "title", "description"})

_BASE_KEYS = ("op", "owner", "stage", "status", "mode", "scope", "schema",
              "error_codes", "sensitive_paths")
_OP_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_OWNER_RE = re.compile(r"^(?:CORE|AND|WIN)-\d+$")
_WIRE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_TITLE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_STAMP_RE = re.compile( r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
_INT_RE = re.compile(r"^-?(?:0|[1-9]\d*)$")
_UINT_RE = re.compile(r"^(?:0|[1-9]\d*)$")
_DEC_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")
_B64_RE = re.compile(r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$")
_INT64_MIN = -(2 ** 63)
_INT64_MAX = 2 ** 63 - 1
_INT128_MIN = -(2 ** 127)
_INT128_MAX = 2 ** 127 - 1
_UINT64_MAX = 2 ** 64 - 1


def _b(text: str) -> bytes:
    """排序键：UTF-8 字节序。"""
    return text.encode("utf-8")


def _pjoin(pointer: str, token: str) -> str:
    """JSON Pointer 拼接（按 RFC 6901 转义）。"""
    escaped = str(token).replace("~", "~0").replace("/", "~1")
    return pointer + "/" + escaped


def _scalar(value: Any) -> tuple[ScalarKind, Any] | None:
    """把 JSON 标量解码为 (kind, value)；非标量返回 None。"""
    if value is None:
        return ("null", None)
    if isinstance(value, bool):
        return ("boolean", value)
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, int):
        return ("integer", value)
    if isinstance(value, Decimal):
        return ("number", value)
    return None


def _json_kind(value: Any) -> str:
    """运行时实例的 JSON 类型名（供 examples/default 校验）。"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, Decimal):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def _dart_name(wire: str) -> str | None:
    """snake_case 到 lowerCamelCase；非法 wire 名返回 None。"""
    if not _WIRE_RE.match(wire):
        return None
    head, *rest = wire.split("_")
    if any(part == "" for part in rest):
        return None
    return head + "".join(part[0].upper() + part[1:] for part in rest)


def _format_ok(fmt: str, value: str) -> bool:
    """按冻结的 8 种 format 精确校验字符串（不经 float 中转）。"""
    if fmt == "uuid":
        return bool(_UUID_RE.match(value))
    if fmt == "base64":
        return bool(_B64_RE.match(value))
    if fmt == "date-time":
        if not _STAMP_RE.match(value):
            return False
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return True
    if fmt == "decimal":
        return bool(_DEC_RE.match(value))
    if fmt == "uint64":
        return bool(_UINT_RE.match(value)) and int(value) <= _UINT64_MAX
    if fmt == "positive-int128":
        return bool(_UINT_RE.match(value)) and 1 <= int(value) <= _INT128_MAX
    if fmt == "int64":
        ok = bool(_INT_RE.match(value)) and value != "-0"
        return ok and _INT64_MIN <= int(value) <= _INT64_MAX
    if fmt == "int128":
        ok = bool(_INT_RE.match(value)) and value != "-0"
        return ok and _INT128_MIN <= int(value) <= _INT128_MAX
    return False


@dataclass(frozen=True)
class SchemaRef:
    """图上的引用边：`<文件相对名>#<规范 Pointer>`。"""

    id: str


@dataclass(frozen=True)
class SchemaScalar:
    """规范化后的 JSON 标量（enum/const 与判别值）。"""

    kind: ScalarKind
    value: str | int | Decimal | bool | None


@dataclass(frozen=True)
class SchemaLimits:
    """已规范化的数值/长度/格式约束；未指定为 None。"""

    minimum: int | Decimal | None = None
    maximum: int | Decimal | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    min_items: int | None = None
    max_items: int | None = None
    format: Format | None = None


@dataclass(frozen=True)
class SchemaField:
    """对象字段：wire 名、Dart 名与值节点边。"""

    wire_name: str
    dart_name: str
    value: SchemaRef
    required: bool


@dataclass(frozen=True)
class SchemaCase:
    """互斥 union 的一个分支及其判别方式。"""

    branch: SchemaRef
    match: Literal["field_const", "external_key", "scalar_enum"]
    key: str | None
    values: tuple[SchemaScalar, ...]


@dataclass(frozen=True)
class SchemaNode:
    """类型图节点；kind 决定启用哪些字段，其余保持 ()/None。"""

    ref: SchemaRef
    title: str | None
    nullable: bool
    kind: NodeKind
    fields: tuple[SchemaField, ...] = ()
    item: SchemaRef | None = None
    prefix: tuple[SchemaRef, ...] = ()
    cases: tuple[SchemaCase, ...] = ()
    target: SchemaRef | None = None
    enum_values: tuple[SchemaScalar, ...] | None = None
    const_value: SchemaScalar | None = None
    limits: SchemaLimits = field(default_factory=SchemaLimits)


@dataclass(frozen=True)
class ReadySchemaOp:
    """就绪 op：字段设计闭合，可生成 DTO。"""

    op: str
    owner: str
    stage: Stage
    scope: Literal["none", "device", "profile"]
    mode: Literal["call", "submit"]
    schema: str
    request: SchemaRef
    ok: SchemaRef
    error_codes: tuple[str, ...]
    sensitive_paths: tuple[str, ...]
    reads_engine_snapshot: bool


@dataclass(frozen=True)
class PendingSchemaOp:
    """未就绪 op：原样列出，但绝不计通过。"""

    op: str
    owner: str
    stage: Stage
    scope: Literal["none", "device", "profile"]
    mode: Literal["call", "submit"] | None
    schema: None
    blocked_reason: str


@dataclass(frozen=True)
class SchemaDiagnostic:
    """一条编译诊断。"""

    severity: Literal["info", "warning", "error"]
    code: str
    source: str
    pointer: str
    op: str | None
    message: str


class SchemaToolError(Exception):
    """本库内部故障（消费方映射为工具错误，不得当作 `valid=false`）。"""


@dataclass(frozen=True)
class SchemaBundle:
    """编译结果：类型图 + 就绪/未就绪清单 + 诊断。"""

    valid: bool
    ready: tuple[ReadySchemaOp, ...]
    pending: tuple[PendingSchemaOp, ...]
    nodes: tuple[SchemaNode, ...]
    named: tuple[SchemaRef, ...]
    diagnostics: tuple[SchemaDiagnostic, ...]
    _index: dict[str, SchemaNode] = field( default_factory=dict, repr=False, compare=False)

    def node(self, ref: SchemaRef) -> SchemaNode:
        """按 id 取节点：只读索引，不写文件、不触发编译。"""
        return self._index[ref.id]


class _Compiler:
    """一次编译的全部中途状态。"""

    def __init__(self, manifest_path: Path) -> None:
        self._path = manifest_path
        self._base = manifest_path.parent
        self._docs: dict[str, Any] = {}
        self._nodes: dict[str, SchemaNode] = {}
        self._building: set[str] = set()
        self._titles: dict[str, str] = {}
        self._diags: list[SchemaDiagnostic] = []
        self._cases_where: tuple[str, str, str | None] = ("", "", None)

    # ---------- 诊断 ----------

    def _err(self, code: str, source: str, pointer: str, op: str | None, message: str) -> None:
        self._diags.append(SchemaDiagnostic("error", code, source, pointer, op, message))

    def _info(self, code: str, source: str, pointer: str, op: str | None, message: str) -> None:
        self._diags.append(SchemaDiagnostic("info", code, source, pointer, op, message))

    # ---------- 文档与引用 ----------

    def _doc(self, name: str, op: str | None) -> Any:
        if name in self._docs:
            return self._docs[name]
        path = self._base / name
        if not path.is_file():
            self._err(D_SCHEMA_JSON, name, "", op, "`schema 文件不存在：`%s" % name)
            self._docs[name] = None
            return None
        text = path.read_text(encoding="utf-8")
        doc: Any
        try:
            doc = json.loads(text, parse_float=Decimal, parse_constant=_no_constant)
        except ValueError as exc:
            self._err(D_SCHEMA_JSON, name, "", op, "`schema 不是合法 JSON：`%s" % exc)
            doc = None
        self._docs[name] = doc
        if isinstance(doc, dict):
            unknown = sorted(set(doc) - _ROOT_KEYS)
            if unknown:
                self._err(D_SCHEMA_KEYWORD, name, "", op,
                          "`schema 文档根含未知关键字：`%s" % ", ".join(unknown))
            if "$schema" in doc and doc["$schema"] != DIALECT:
                self._err(D_SCHEMA_KEYWORD, name, "/$schema", op,
                          "`文档根 $schema 取值必须是 2020-12 方言`")
        return doc

    def _resolve(self, raw_ref: Any, doc: str, pointer: str,
                 op: str | None) -> SchemaRef | None:
        if not isinstance(raw_ref, str) or raw_ref == "":
            self._err(D_SCHEMA_REF, doc, pointer, op, "`$ref 必须是非空字符串`")
            return None
        name, _, fragment = raw_ref.partition("#")
        name = name or doc
        if "/" in name or "\\" in name or name.startswith(".") or name == "":
            self._err(D_SCHEMA_REF, doc, pointer, op, "`$ref 目标必须是同目录文件名：`%s" % raw_ref)
            return None
        if fragment and not fragment.startswith("/"):
            self._err(D_SCHEMA_REF, doc, pointer, op, "`$ref 指针必须以 / 开头：`%s" % raw_ref)
            return None
        target_doc = self._doc(name, op)
        if target_doc is None:
            return None
        node: Any = target_doc
        for token in [t for t in fragment.split("/") if t]:
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(node, dict) and token in node:
                node = node[token]
            elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
                node = node[int(token)]
            else:
                self._err(D_SCHEMA_REF, doc, pointer, op, "`$ref 目标不存在：`%s" % raw_ref)
                return None
        self._build(name, fragment, node, op)
        return SchemaRef("%s#%s" % (name, fragment))

    # ---------- 类型图 ----------

    def _build(self, doc: str, pointer: str, raw: Any, op: str | None) -> SchemaRef:
        rid = "%s#%s" % (doc, pointer)
        if rid in self._nodes or rid in self._building:
            return SchemaRef(rid)
        self._building.add(rid)
        try:
            node = self._node(doc, pointer, raw, op, SchemaRef(rid), False)
        finally:
            self._building.discard(rid)
        if node is not None:
            self._nodes[rid] = node
        return SchemaRef(rid)

    def _title(self, raw: dict, doc: str, pointer: str, op: str | None) -> str | None:
        title = raw.get("title")
        if title is None:
            return None
        here = "%s#%s" % (doc, pointer)
        if not isinstance(title, str) or not _TITLE_RE.match(title):
            self._err(D_SCHEMA_TITLE, doc, pointer, op, "`title 必须是非空 PascalCase 类型名`")
            return None
        if self._titles.setdefault(title, here) != here:
            self._err(D_SCHEMA_TITLE, doc, pointer, op, "`title 非全局唯一：`%s" % title)
            return None
        return title

    def _node(self, doc: str, pointer: str, raw: Any, op: str | None,
              ref: SchemaRef, nullable: bool) -> SchemaNode | None:
        if not isinstance(raw, dict):
            self._err(D_SCHEMA_SHAPE, doc, pointer, op, "`schema 节点必须是 JSON 对象`")
            return None
        keys = set(raw)
        if "$schema" in keys:
            if pointer != "":
                self._err(D_SCHEMA_KEYWORD, doc, pointer, op, "`$schema 只允许出现在文档根`")
                return None
            if raw["$schema"] != DIALECT:
                self._err(D_SCHEMA_KEYWORD, doc, pointer, op, "`文档根 $schema 取值必须是 2020-12 方言`")
                return None
        unknown = sorted(keys - _KEYS)
        if unknown:
            self._err(D_SCHEMA_KEYWORD, doc, pointer, op, "`含白名单外关键字：`%s" % ", ".join(unknown))
            return None
        for name in ("writeOnly", "x-sensitive"):
            if name in raw and not isinstance(raw[name], bool):
                self._err(D_SCHEMA_KEYWORD, doc, pointer, op, "%s `只允许布尔值`" % name)
                return None
        title = self._title(raw, doc, pointer, op)
        if "oneOf" in keys:
            return self._union(doc, pointer, raw, op, ref, title, nullable)
        if "$ref" in keys:
            extra = sorted((keys - {"$ref"}) - _REF_SIBLINGS)
            if extra:
                self._err(D_SCHEMA_REF, doc, pointer, op, "`$ref 只能与 title/description 并存`")
                return None
            target = self._resolve(raw["$ref"], doc, pointer, op)
            if target is None:
                return None
            return SchemaNode(ref, title, nullable, "ref", target=target)
        kind = raw.get("type")
        if kind is None:
            if "const" in keys:
                kind = (_scalar(raw["const"]) or ("", None))[0]
            elif "enum" in keys and isinstance(raw["enum"], list) and raw["enum"]:
                kind = (_scalar(raw["enum"][0]) or ("", None))[0]
        if not isinstance(kind, str) or kind not in _KIND_SET:
            self._err(D_SCHEMA_TYPE, doc, pointer, op, "`节点类型只允许单一字符串类型`")
            return None
        return self._typed(doc, pointer, raw, op, ref, title, nullable, kind, keys)

    def _typed(self, doc: str, pointer: str, raw: dict, op: str | None,
               ref: SchemaRef, title: str | None, nullable: bool, kind: str,
               keys: set[str]) -> SchemaNode | None:
        limit_keys = { "string": {"minLength", "maxLength", "pattern", "format"},
            "integer": {"minimum", "maximum"}, "number": {"minimum", "maximum"},
            "array": {"items", "prefixItems", "minItems", "maxItems"},
            "object": {"properties", "required", "additionalProperties"},
        }.get(kind, set())
        allowed = {"type", "enum", "const", "$defs"} | limit_keys
        extra = sorted((keys - allowed) - _ANNOTATIONS)
        if extra:
            self._err(D_SCHEMA_KEYWORD, doc, pointer, op,
                      "`关键字与节点类型不符或不在白名单：`%s" % ", ".join(extra))
            return None
        if kind == "object":
            node = self._object(doc, pointer, raw, op, ref, title, nullable)
        elif kind == "array":
            node = self._array(doc, pointer, raw, op, ref, title, nullable)
        else:
            node = self._leaf(doc, pointer, raw, op, ref, title, nullable, kind)
        if node is None:
            return None
        self._annotations(doc, pointer, raw, op)
        return node

    def _leaf(self, doc: str, pointer: str, raw: dict, op: str | None,
              ref: SchemaRef, title: str | None, nullable: bool,
              kind: str) -> SchemaNode | None:
        enum_values: tuple[SchemaScalar, ...] | None = None
        const_value: SchemaScalar | None = None
        if "enum" in raw:
            values = raw["enum"]
            if not isinstance(values, list) or not values:
                self._err(D_SCHEMA_TYPE, doc, pointer, op, "`enum 必须是非空数组`")
                return None
            decoded = []
            for value in values:
                scalar = _scalar(value)
                if scalar is None or scalar[0] != kind:
                    self._err(D_SCHEMA_TYPE, doc, pointer, op, "`enum 值必须是该节点类型的 JSON 标量`")
                    return None
                decoded.append(SchemaScalar(*scalar))
            if len(set(decoded)) != len(decoded):
                self._err(D_SCHEMA_TYPE, doc, pointer, op, "`enum 值不得重复`")
                return None
            enum_values = tuple(decoded)
        if "const" in raw:
            scalar = _scalar(raw["const"])
            if scalar is None or scalar[0] != kind:
                self._err(D_SCHEMA_TYPE, doc, pointer, op, "`const 必须是该节点类型的 JSON 标量`")
                return None
            if enum_values is not None:
                self._err(D_SCHEMA_TYPE, doc, pointer, op, "`enum 与 const 不得并存`")
                return None
            const_value = SchemaScalar(*scalar)
        limits = self._limits(doc, pointer, raw, op)
        return SchemaNode(ref, title, nullable, kind, enum_values=enum_values,
                          const_value=const_value, limits=limits)

    def _limits(self, doc: str, pointer: str, raw: dict, op: str | None) -> SchemaLimits:
        def number(name: str) -> int | Decimal | None:
            if name not in raw:
                return None
            value = raw[name]
            if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
                self._err(D_SCHEMA_LIMITS, doc, pointer, op, "%s `必须是整数或小数`" % name)
                return None
            return value

        def count(name: str) -> int | None:
            if name not in raw:
                return None
            value = raw[name]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                self._err(D_SCHEMA_LIMITS, doc, pointer, op, "%s `必须是非负整数`" % name)
                return None
            return value

        minimum = number("minimum")
        maximum = number("maximum")
        min_length = count("minLength")
        max_length = count("maxLength")
        min_items = count("minItems")
        max_items = count("maxItems")
        pattern = raw.get("pattern")
        if pattern is not None:
            if not isinstance(pattern, str):
                self._err(D_SCHEMA_LIMITS, doc, pointer, op, "`pattern 必须是字符串`")
                pattern = None
            else:
                try:
                    re.compile(pattern)
                except re.error:
                    self._err(D_SCHEMA_LIMITS, doc, pointer, op, "`pattern 必须能编译`")
                    pattern = None
        fmt = raw.get("format")
        if fmt is not None:
            if not isinstance(fmt, str) or fmt not in FORMATS:
                self._err(D_SCHEMA_FORMAT, doc, pointer, op, "`format 必须是冻结的 8 种之一`")
                fmt = None
        for low, high, label in ( (minimum, maximum, "minimum/maximum"),
            (min_length, max_length, "minLength/maxLength"),
            (min_items, max_items, "minItems/maxItems"),
        ):
            if low is not None and high is not None and low > high:
                self._err(D_SCHEMA_LIMITS, doc, pointer, op, "%s `下界不得超过上界`" % label)
        return SchemaLimits(minimum, maximum, min_length, max_length, pattern,
                            min_items, max_items, fmt)

    def _object(self, doc: str, pointer: str, raw: dict, op: str | None,
                ref: SchemaRef, title: str | None, nullable: bool) -> SchemaNode | None:
        props = raw.get("properties")
        extra = raw.get("additionalProperties")
        required = raw.get("required", [])
        if not isinstance(required, list) or any(
                not isinstance(name, str) for name in required):
            self._err(D_SCHEMA_OBJECT, doc, pointer, op, "`required 必须是字符串数组`")
            return None
        if len(set(required)) != len(required):
            self._err(D_SCHEMA_OBJECT, doc, pointer, op, "`required 不得重复`")
            return None
        if props is not None and not isinstance(props, dict):
            self._err(D_SCHEMA_OBJECT, doc, pointer, op, "`properties 必须是对象`")
            return None
        if not props and isinstance(extra, dict):
            if required:
                self._err(D_SCHEMA_MAP, doc, pointer, op, "`有类型 map 不允许 required`")
                return None
            if set(extra) != {"type"} or extra.get("type") != "string":
                self._err(D_SCHEMA_MAP, doc, pointer, op,
                          "`有类型 map 只允许 additionalProperties 为 {type: string}`")
                return None
            item = self._build(doc, _pjoin(pointer, "additionalProperties"), extra, op)
            return SchemaNode(ref, title, nullable, "map", item=item)
        if props is None:
            props = {}
        if extra is not False:
            self._err(D_SCHEMA_OBJECT, doc, pointer, op,
                      "`object 必须显式 additionalProperties:false`")
            return None
        missing = sorted(set(required) - set(props))
        if missing:
            self._err(D_SCHEMA_OBJECT, doc, pointer, op,
                      "`required 引用了未声明字段：`%s" % ", ".join(missing))
            return None
        fields: list[SchemaField] = []
        darts: dict[str, str] = {}
        for name in sorted(props, key=_b):
            dart = _dart_name(name)
            if dart is None:
                self._err(D_SCHEMA_NAME, doc, pointer, op, "`wire 名必须是 snake_case：`%s" % name)
                return None
            if dart in darts:
                self._err(D_SCHEMA_NAME, doc, pointer, op,
                          "`wire 名转换后与 %s 冲突：`%s" % (darts[dart], name))
                return None
            darts[dart] = name
            value = self._build(doc, _pjoin(_pjoin(pointer, "properties"), name),
                                props[name], op)
            fields.append(SchemaField(name, dart, value, name in required))
        return SchemaNode(ref, title, nullable, "object", fields=tuple(fields))

    def _array(self, doc: str, pointer: str, raw: dict, op: str | None,
               ref: SchemaRef, title: str | None, nullable: bool) -> SchemaNode | None:
        limits = self._limits(doc, pointer, raw, op)
        if "prefixItems" in raw:
            if raw.get("items") is not False:
                self._err(D_SCHEMA_ARRAY, doc, pointer, op, "`定长 tuple 必须 items:false`")
                return None
            parts = raw["prefixItems"]
            if not isinstance(parts, list) or not parts:
                self._err(D_SCHEMA_ARRAY, doc, pointer, op, "`prefixItems 必须是非空数组`")
                return None
            if (limits.min_items != len(parts) or limits.max_items != len(parts)):
                self._err(D_SCHEMA_ARRAY, doc, pointer, op,
                          "`定长 tuple 必须用 minItems/maxItems 固定为分支长度`")
                return None
            prefix = tuple( self._build(doc, pointer + "/prefixItems/" + str(index), part, op)
                for index, part in enumerate(parts)
            )
            return SchemaNode(ref, title, nullable, "tuple", prefix=prefix, limits=limits)
        if "items" not in raw:
            self._err(D_SCHEMA_ARRAY, doc, pointer, op, "`array 必须声明 items，不得生成任意 JSON`")
            return None
        item = self._build(doc, _pjoin(pointer, "items"), raw["items"], op)
        return SchemaNode(ref, title, nullable, "array", item=item, limits=limits)

    def _union(self, doc: str, pointer: str, raw: dict, op: str | None,
               ref: SchemaRef, title: str | None, nullable: bool) -> SchemaNode | None:
        extra = sorted((set(raw) - {"oneOf"}) - _ANNOTATIONS)
        if extra:
            self._err(D_SCHEMA_UNION, doc, pointer, op, "`oneOf 只能与注解并存`")
            return None
        branches = raw["oneOf"]
        if not isinstance(branches, list) or len(branches) < 2:
            self._err(D_SCHEMA_UNION, doc, pointer, op, "`oneOf 至少两支`")
            return None
        nulls = [ index for index, branch in enumerate(branches)
            if isinstance(branch, dict) and branch.get("type") == "null"
            and set(branch) <= _NULL_BRANCH_KEYS
        ]
        if nulls:
            if len(branches) != 2:
                self._err(D_SCHEMA_NULLABLE, doc, pointer, op, "`nullable 的唯一编码是恰两支 oneOf`")
                return None
            if len(nulls) == 2:
                self._err(D_SCHEMA_NULLABLE, doc, pointer, op, "`nullable 不得两支都是 null`")
                return None
            other = branches[1 - nulls[0]]
            if not isinstance(other, dict) or "oneOf" in other:
                self._err(D_SCHEMA_NULLABLE, doc, pointer, op, "`nullable 的非 null 侧不得是 union`")
                return None
            merged = dict(other)
            for name in ("title", "description"):
                if name in raw:
                    merged[name] = raw[name]
            return self._node(doc, pointer, merged, op, ref, True)
        self._cases_where = (doc, pointer, op)
        cases: list[SchemaCase] = []
        seen: dict[str, int] = {}
        scalar_seen = False
        for index, branch in enumerate(branches):
            bref = self._build(doc, pointer + "/oneOf/" + str(index), branch, op)
            if not isinstance(branch, dict):
                self._err(D_SCHEMA_UNION, doc, pointer, op, "`union 分支必须是 schema 对象`")
                return None
            bkind = branch.get("type")
            if bkind is None and "const" in branch:
                bkind = (_scalar(branch["const"]) or ("", None))[0]
            if bkind in {"string", "integer", "number"} and isinstance(
                    branch.get("enum"), list):
                if scalar_seen:
                    self._err(D_SCHEMA_UNION, doc, pointer, op, "`union 至多一个标量分支`")
                    return None
                scalar_seen = True
                values_list: list[SchemaScalar] = []
                for value in branch["enum"]:
                    scalar = _scalar(value)
                    if scalar is None:
                        self._err(D_SCHEMA_UNION, doc, pointer, op,
                                  "`union 判别值必须是 JSON 标量`")
                        return None
                    values_list.append(SchemaScalar(*scalar))
                values = tuple(values_list)
                cases.append(SchemaCase(bref, "scalar_enum", None, values))
                for scalar in values:
                    if not self._case_key(seen, scalar.value, index):
                        return None
            elif bkind == "object":
                required = branch.get("required") or []
                props = branch.get("properties") or {}
                consts = [ name for name in required
                    if isinstance(props.get(name), dict) and "const" in props[name]
                ]
                if len(consts) == 1:
                    scalar = _scalar(props[consts[0]]["const"])
                    if scalar is None:
                        self._err(D_SCHEMA_UNION, doc, pointer, op, "`union 判别值必须是 JSON 标量`")
                        return None
                    cases.append(SchemaCase(bref, "field_const", consts[0],
                                            (SchemaScalar(*scalar),)))
                    if not self._case_key(seen, scalar[1], index):
                        return None
                elif not consts and len(required) == 1:
                    cases.append(SchemaCase(bref, "external_key", required[0], ()))
                    if not self._case_key(seen, required[0], index):
                        return None
                else:
                    self._err(D_SCHEMA_UNION, doc, pointer, op, "`union 对象分支必须有唯一判别键`")
                    return None
            else:
                self._err(D_SCHEMA_UNION, doc, pointer, op, "`union 分支必须是带 enum 的标量或对象`")
                return None
        return SchemaNode(ref, title, nullable, "union", cases=tuple(cases))

    def _case_key(self, seen: dict[str, int], value: Any, index: int) -> bool:
        if isinstance(value, str):
            tag = value
        elif value is None:
            tag = "\x00null"
        elif isinstance(value, bool):
            tag = "\x00b%d" % value
        elif isinstance(value, (int, Decimal)):
            tag = "\x00n%s" % value
        else:
            tag = "\x00?%r" % (value,)
        if tag in seen:
            self._err(D_SCHEMA_UNION, *self._cases_where, "`union 判别键/判别值重复：`%s" % tag)
            return False
        seen[tag] = index
        return True

    # ---------- 注解与实例校验 ----------

    def _same(self, left: Any, right: Any) -> bool:
        if isinstance(left, bool) or isinstance(right, bool):
            return isinstance(left, bool) and isinstance(right, bool) and left == right
        numeric = (int, Decimal)
        if isinstance(left, numeric) and isinstance(right, numeric):
            return left == right
        if type(left) is not type(right):
            return False
        return left == right

    def _annotations(self, doc: str, pointer: str, raw: dict, op: str | None) -> None:
        if "examples" in raw:
            items = raw["examples"]
            if not isinstance(items, list) or not items:
                self._err(D_SCHEMA_EXAMPLE, doc, pointer, op, "`examples 必须是非空数组`")
            else:
                for index, value in enumerate(items):
                    self._value(doc, raw, op, pointer + "/examples/" + str(index), value,
                                "examples[%d]" % index)
        if "default" in raw:
            self._value(doc, raw, op, _pjoin(pointer, "default"), raw["default"], "default")

    def _value(self, doc: str, raw: Any, op: str | None, pointer: str,
               value: Any, where: str, depth: int = 0) -> None:
        if depth > 24:
            self._err(D_SCHEMA_EXAMPLE, doc, pointer, op, "%s `嵌套过深`" % where)
            return
        if not isinstance(raw, dict):
            return
        if "$ref" in raw:
            target = raw["$ref"]
            if not isinstance(target, str) or target == "":
                self._err(D_SCHEMA_REF, doc, pointer, op,
                          "%s `的 $ref 必须是非空字符串`" % where)
                return
            name, _, fragment = target.partition("#")
            name = name or doc
            if name == "" or "/" in name or Path(name).name != name or name.startswith("."):
                self._err(D_SCHEMA_REF, doc, pointer, op,
                          "%s `的 $ref 目标必须是同目录文件名：`%s" % (where, target))
                return
            if fragment and not fragment.startswith("/"):
                self._err(D_SCHEMA_REF, doc, pointer, op,
                          "%s `的 $ref 指针必须以 / 开头：`%s" % (where, target))
                return
            node: Any = self._doc(name, op)
            if node is None:
                return
            for token in [t for t in fragment.split("/") if t]:
                token = token.replace("~1", "/").replace("~0", "~")
                if isinstance(node, dict) and token in node:
                    node = node[token]
                elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
                    node = node[int(token)]
                else:
                    self._err(D_SCHEMA_REF, name, fragment, op,
                              "%s `的 $ref 目标不存在：`%s" % (where, target))
                    return
            self._value(name, node, op, pointer, value, where, depth + 1)
            return
        if isinstance(raw.get("oneOf"), list):
            matched = 0
            for branch in raw["oneOf"]:
                mark = len(self._diags)
                self._value(doc, branch, op, pointer, value, where, depth + 1)
                if len(self._diags) == mark:
                    matched += 1
                else:
                    del self._diags[mark:]
            if matched != 1:
                self._err(D_SCHEMA_EXAMPLE, doc, pointer, op,
                          "%s `不满足互斥 oneOf（匹配 %d 支）`" % (where, matched))
            return
        if "const" in raw:
            if not self._same(value, raw["const"]):
                self._err(D_SCHEMA_EXAMPLE, doc, pointer, op, "%s `与 const 不符`" % where)
            return
        if isinstance(raw.get("enum"), list):
            if not any(self._same(value, item) for item in raw["enum"]):
                self._err(D_SCHEMA_EXAMPLE, doc, pointer, op, "%s `不在 enum 内`" % where)
            return
        kind = raw.get("type")
        if not isinstance(kind, str):
            return
        actual = _json_kind(value)
        if kind == "integer":
            match = actual == "integer" or ( actual == "number" and value.is_finite()
                and value == value.to_integral_value())
        elif kind == "number":
            match = actual in {"integer", "number"}
        else:
            match = actual == kind
        if not match:
            self._err(D_SCHEMA_EXAMPLE, doc, pointer, op,
                      "%s `类型应为 %s，实际 %s`" % (where, kind, actual))
            return
        if kind == "object":
            props = raw.get("properties") or {}
            if not isinstance(props, dict):
                props = {}
            for name in raw.get("required") or []:
                if name not in value:
                    self._err(D_SCHEMA_EXAMPLE, doc, pointer, op,
                              "%s `缺必填字段 %s`" % (where, name))
            for name, item in value.items():
                child = "%s.%s" % (where, name)
                if name in props:
                    self._value(doc, props[name], op, _pjoin(pointer, name), item,
                                child, depth + 1)
                elif isinstance(raw.get("additionalProperties"), dict):
                    self._value(doc, raw["additionalProperties"], op,
                                _pjoin(pointer, name), item, child, depth + 1)
                elif raw.get("additionalProperties") is False:
                    self._err(D_SCHEMA_EXAMPLE, doc, pointer, op,
                              "%s `含未声明字段 %s`" % (where, name))
        elif kind == "array":
            parts = raw.get("prefixItems")
            if isinstance(parts, list) and raw.get("items") is False:
                if len(value) != len(parts):
                    self._err(D_SCHEMA_EXAMPLE, doc, pointer, op,
                              "%s `定长 tuple 长度应为 %d`" % (where, len(parts)))
                else:
                    for index, (part, item) in enumerate(zip(parts, value)):
                        self._value(doc, part, op, "%s/%d" % (pointer, index), item,
                                    "%s[%d]" % (where, index), depth + 1)
            elif isinstance(raw.get("items"), dict):
                for index, item in enumerate(value):
                    self._value(doc, raw["items"], op, "%s/%d" % (pointer, index),
                                item, "%s[%d]" % (where, index), depth + 1)
            low, high = raw.get("minItems"), raw.get("maxItems")
            if isinstance(low, int) and len(value) < low:
                self._err(D_SCHEMA_EXAMPLE, doc, pointer, op, "%s `少于 minItems`" % where)
            if isinstance(high, int) and len(value) > high:
                self._err(D_SCHEMA_EXAMPLE, doc, pointer, op, "%s `多于 maxItems`" % where)
        elif kind == "string":
            low, high = raw.get("minLength"), raw.get("maxLength")
            if isinstance(low, int) and len(value) < low:
                self._err(D_SCHEMA_EXAMPLE, doc, pointer, op, "%s `短于 minLength`（按码位计）" % where)
            if isinstance(high, int) and len(value) > high:
                self._err(D_SCHEMA_EXAMPLE, doc, pointer, op, "%s `长于 maxLength`（按码位计）" % where)
            pattern = raw.get("pattern")
            if isinstance(pattern, str):
                try:
                    hit = re.search(pattern, value) is not None
                except re.error:
                    hit = True
                if not hit:
                    self._err(D_SCHEMA_EXAMPLE, doc, pointer, op, "%s `不满足 pattern`" % where)
            fmt = raw.get("format")
            if isinstance(fmt, str) and fmt in FORMATS and not _format_ok(fmt, value):
                self._err(D_SCHEMA_EXAMPLE, doc, pointer, op,
                          "%s `不满足 format %s`" % (where, fmt))
        else:
            low, high = raw.get("minimum"), raw.get("maximum")
            if low is not None and value < low:
                self._err(D_SCHEMA_EXAMPLE, doc, pointer, op, "%s `小于 minimum`" % where)
            if high is not None and value > high:
                self._err(D_SCHEMA_EXAMPLE, doc, pointer, op, "%s `大于 maximum`" % where)

    # ---------- 敏感路径 ----------

    def _sensitive(self, raw: Any, root: str, out: list[str], depth: int = 0) -> None:
        if not isinstance(raw, dict) or depth > 24:
            return
        if raw.get("x-sensitive") is True or raw.get("writeOnly") is True:
            out.append(root)
            return
        props = raw.get("properties")
        if isinstance(props, dict):
            for name in sorted(props, key=_b):
                self._sensitive(props[name], "%s/%s" % (root, name), out, depth + 1)
        if isinstance(raw.get("items"), dict):
            self._sensitive(raw["items"], root + "/*", out, depth + 1)
        if isinstance(raw.get("prefixItems"), list):
            for part in raw["prefixItems"]:
                self._sensitive(part, root + "/*", out, depth + 1)
        if isinstance(raw.get("additionalProperties"), dict):
            self._sensitive(raw["additionalProperties"], root + "/*", out, depth + 1)

    # ---------- manifest 条目 ----------

    def _codes(self, entry: dict, source: str, pointer: str,
               label: str | None) -> tuple[str, ...] | None:
        value = entry.get("error_codes")
        if not isinstance(value, list):
            self._err(D_MANIFEST_CODES, source, _pjoin(pointer, "error_codes"),
                      label, "`error_codes 必须是字符串数组`")
            return None
        seen: list[str] = []
        for code in value:
            if not isinstance(code, str) or not code:
                self._err(D_MANIFEST_CODES, source, _pjoin(pointer, "error_codes"),
                          label, "`error_codes 只能是非空字符串`")
                return None
            if code in CORE03_OWNED_CODES:
                self._err(D_MANIFEST_CODES, source, _pjoin(pointer, "error_codes"),
                          label, "`error_codes 不得包含 CORE-03 归属码：`%s" % code)
                return None
            seen.append(code)
        if len(set(seen)) != len(seen):
            self._err(D_MANIFEST_CODES, source, _pjoin(pointer, "error_codes"),
                      label, "`error_codes 不得重复`")
            return None
        order = [_b(code) for code in seen]
        if order != sorted(order):
            self._err(D_MANIFEST_CODES, source, _pjoin(pointer, "error_codes"),
                      label, "`error_codes 必须按 UTF-8 字节序排序`")
            return None
        return tuple(seen)

    def _paths(self, entry: dict, source: str, pointer: str,
               label: str | None) -> tuple[str, ...] | None:
        value = entry.get("sensitive_paths")
        if not isinstance(value, list):
            self._err(D_MANIFEST_PATHS, source, _pjoin(pointer, "sensitive_paths"),
                      label, "`sensitive_paths 必须是字符串数组`")
            return None
        seen: list[str] = []
        for path in value:
            if not isinstance(path, str) or not path.startswith("/"):
                self._err(D_MANIFEST_PATHS, source, _pjoin(pointer, "sensitive_paths"), label,
                          "`sensitive_paths 必须是 JSON Pointer`")
                return None
            if path.split("/")[1] not in {"body", "ok"}:
                self._err(D_MANIFEST_PATHS, source, _pjoin(pointer, "sensitive_paths"), label,
                          "`sensitive_paths 必须从信封根 /body 或 /ok 开始`")
                return None
            seen.append(path)
        if len(set(seen)) != len(seen):
            self._err(D_MANIFEST_PATHS, source, _pjoin(pointer, "sensitive_paths"),
                      label, "`sensitive_paths 不得重复`")
            return None
        order = [_b(path) for path in seen]
        if order != sorted(order):
            self._err(D_MANIFEST_PATHS, source, _pjoin(pointer, "sensitive_paths"),
                      label, "`sensitive_paths 必须按 UTF-8 字节序排序`")
            return None
        return tuple(seen)

    def _ready_schema(self, name: str, op: str | None, declared: tuple[str, ...] | None
                      ) -> tuple[SchemaRef, SchemaRef] | None:
        if not (self._base / name).is_file():
            self._err(D_MANIFEST_SCHEMA, name, "", op, "`schema 文件不存在：`%s" % name)
            return None
        doc = self._doc(name, op)
        if not isinstance(doc, dict):
            return None
        defs = doc.get("$defs")
        if not isinstance(defs, dict):
            self._err(D_MANIFEST_SCHEMA, name, "", op, "`schema 缺少 $defs`")
            return None
        for key in ("request", "ok"):
            if key not in defs:
                self._err(D_MANIFEST_SCHEMA, name, "/$defs", op, "`schema 缺少 $defs.%s`" % key)
                return None
        examples = doc.get("examples")
        if not isinstance(examples, list) or not examples:
            self._err(D_MANIFEST_SCHEMA, name, "/examples", op, "`schema 缺少非空 examples`")
        else:
            for index, item in enumerate(examples):
                if not isinstance(item, dict):
                    self._err(D_MANIFEST_SCHEMA, name, "/examples/%d" % index, op,
                              "`examples 条目必须是对象`")
                    continue
                if "request" not in item or "ok" not in item:
                    self._err(D_MANIFEST_SCHEMA, name, "/examples/%d" % index, op,
                              "`examples 条目必须同时给出 request 与 ok`")
                    continue
                self._value(name, defs["request"], op,
                            "/examples/%d/request" % index, item["request"],
                            "examples[%d].request" % index)
                self._value(name, defs["ok"], op, "/examples/%d/ok" % index,
                            item["ok"], "examples[%d].ok" % index)
        request = self._build(name, "/$defs/request", defs["request"], op)
        ok = self._build(name, "/$defs/ok", defs["ok"], op)
        found: list[str] = []
        self._sensitive(defs["request"], "/body", found)
        self._sensitive(defs["ok"], "/ok", found)
        derived = tuple(sorted(set(found), key=_b))
        if declared is not None and declared != derived:
            self._err(D_MANIFEST_PATHS, name, "/$defs", op,
                      "`manifest sensitive_paths 与 schema x-sensitive 不一致：`"
                      "manifest=%s schema=%s" % (list(declared), list(derived)))
        return (request, ok)

    def _entry(self, index: int, entry: Any, state: dict) -> None:
        pointer = "/ops/%d" % index
        source = MANIFEST_SOURCE
        mark = len(self._diags)
        if not isinstance(entry, dict):
            self._err(D_MANIFEST_SHAPE, source, pointer, None, "`manifest 条目必须是 JSON 对象`")
            return
        op = entry.get("op")
        label = op if isinstance(op, str) and op else None
        status = entry.get("status")
        base = set(_BASE_KEYS)
        if status == "ready":
            allowed = base | {"reads_engine_snapshot"}
        elif status == "pending":
            allowed = base | {"blocked_reason"}
        else:
            allowed = base | {"reads_engine_snapshot", "blocked_reason"}
        for name in sorted(set(entry) - allowed):
            self._err(D_MANIFEST_KEY, source, _pjoin(pointer, name), label,
                      "`条目含未知键：`%s" % name)
        for name in _BASE_KEYS:
            if name not in entry:
                self._err(D_MANIFEST_KEY, source, pointer, label, "`条目缺键：`%s" % name)
        if label is None or not _OP_RE.match(label):
            self._err(D_MANIFEST_OP, source, _pjoin(pointer, "op"), label,
                      "`op 必须是两段及以上的小写点分标识`")
        elif label in state["ops"]:
            self._err(D_MANIFEST_OP, source, _pjoin(pointer, "op"), label, "`op 重复定义`")
        else:
            state["ops"].add(label)
        owner = entry.get("owner")
        if not isinstance(owner, str) or not _OWNER_RE.match(owner):
            self._err(D_MANIFEST_OWNER, source, _pjoin(pointer, "owner"), label,
                      "`owner 必须是现行卡号`")
            owner = None
        stage = entry.get("stage")
        if stage not in STAGES:
            self._err(D_MANIFEST_STAGE, source, _pjoin(pointer, "stage"), label,
                      "`stage 必须是 S0..S7`")
            stage = None
        if status not in _STATUSES:
            self._err(D_MANIFEST_STATUS, source, _pjoin(pointer, "status"), label,
                      "`status 只能是 ready 或 pending`")
        mode = entry.get("mode")
        if mode is not None and mode not in _MODES:
            self._err(D_MANIFEST_MODE, source, _pjoin(pointer, "mode"), label,
                      "`mode 只能是 call、submit 或 null`")
            mode = None
        elif status == "ready" and mode is None:
            self._err(D_MANIFEST_MODE, source, _pjoin(pointer, "mode"), label,
                      "`ready 必须给出 mode`")
        scope = entry.get("scope")
        if scope not in _SCOPES:
            self._err(D_MANIFEST_SCOPE, source, _pjoin(pointer, "scope"), label,
                      "`scope 只能是 none、device 或 profile`")
            scope = None
        codes = self._codes(entry, source, pointer, label)
        paths = self._paths(entry, source, pointer, label)
        if status == "ready":
            raw_snapshot = entry.get("reads_engine_snapshot")
            snapshot: bool | None = raw_snapshot if isinstance(raw_snapshot, bool) else None
            if snapshot is None:
                self._err(D_MANIFEST_SNAPSHOT, source,
                          _pjoin(pointer, "reads_engine_snapshot"), label,
                          "`ready 必须显式给出布尔 reads_engine_snapshot`")
            elif codes is not None and (ENGINE_SNAPSHOT_CODE in codes) != snapshot:
                self._err(D_MANIFEST_SNAPSHOT, source,
                          _pjoin(pointer, "reads_engine_snapshot"), label,
                          "`reads_engine_snapshot 必须与 error_codes 是否含 "
                          "ENGINE_UNAVAILABLE 双向一致`")
            name = entry.get("schema")
            refs = None
            if not isinstance(name, str) or not name:
                self._err(D_MANIFEST_SCHEMA, source, _pjoin(pointer, "schema"),
                          label, "`ready 必须给出 schema 文件名`")
                name = None
            elif "/" in name or "\\" in name or name.startswith(".") or not name.endswith(".json"):
                self._err(D_MANIFEST_SCHEMA, source, _pjoin(pointer, "schema"),
                          label, "`schema 必须是 contracts/dto 下的相对文件名`")
                name = None
            else:
                refs = self._ready_schema(name, label, paths)
            if (len(self._diags) == mark and refs is not None
                    and label is not None and owner is not None
                    and scope is not None and mode is not None
                    and codes is not None and paths is not None
                    and snapshot is not None and stage is not None and name is not None):
                state["ready"].append( ReadySchemaOp(label, owner, stage, scope, mode, name,
                                  refs[0], refs[1], codes, paths, snapshot))
                state["gates"].append((label, stage, False))
        elif status == "pending":
            schema = entry.get("schema")
            if schema is not None:
                self._err(D_MANIFEST_SCHEMA, source, _pjoin(pointer, "schema"),
                          label, "`pending 的 schema 必须是 null`")
            raw_reason = entry.get("blocked_reason")
            reason = raw_reason if isinstance(raw_reason, str) and raw_reason.strip() else None
            if reason is None:
                self._err(D_MANIFEST_BLOCKED, source, _pjoin(pointer, "blocked_reason"), label,
                          "`pending 必须给出非空 blocked_reason`")
            if (len(self._diags) == mark and label is not None
                    and owner is not None and scope is not None
                    and codes is not None and paths is not None
                    and reason is not None and stage is not None):
                state["pending"].append(
                    PendingSchemaOp(label, owner, stage, scope, mode, None, reason))
                state["gates"].append((label, stage, True))

    # ---------- 入口 ----------

    def run(self, required_stage: Stage | None, release: bool) -> SchemaBundle:
        source = MANIFEST_SOURCE
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError:
            raise
        except UnicodeDecodeError as exc:
            self._err(D_MANIFEST_JSON, source, "", None, "`manifest 不是合法 UTF-8：`%s" % exc)
            return self._bundle([], [])
        try:
            root = json.loads(text, parse_float=Decimal, parse_constant=_no_constant)
        except ValueError as exc:
            self._err(D_MANIFEST_JSON, source, "", None, "`manifest 不是合法 JSON：`%s" % exc)
            return self._bundle([], [])
        if not isinstance(root, dict):
            self._err(D_MANIFEST_SHAPE, source, "", None, "`manifest 根必须是 JSON 对象`")
            return self._bundle([], [])
        for name in sorted(set(root) - {"version", "ops"}):
            self._err(D_MANIFEST_KEY, source, "/" + name, None, "`manifest 根含未知键：`%s" % name)
        version = root.get("version")
        if version is not None and ( isinstance(version, bool) or not isinstance(version, int)
                or version < 1):
            self._err(D_MANIFEST_SHAPE, source, "/version", None, "`version 必须是正整数`")
        ops = root.get("ops")
        if not isinstance(ops, list):
            self._err(D_MANIFEST_SHAPE, source, "/ops", None, "`ops 必须是数组`")
            return self._bundle([], [])
        state: dict = {"ops": set(), "ready": [], "pending": [], "gates": []}
        for index, entry in enumerate(ops):
            self._entry(index, entry, state)
        need = None if required_stage is None else STAGES.index(required_stage)
        for label, stage, pending in state["gates"]:
            if not pending:
                continue
            rank = STAGES.index(stage)
            if release:
                self._err(D_MANIFEST_GATE, source, "", label,
                          "`release 不允许存在 pending 条目（`%s `阶段` %s）" % (label, stage))
            elif need is not None:
                if rank <= need:
                    self._err(D_MANIFEST_GATE, source, "", label,
                              "`op %s 在阶段 %s 仍未就绪`" % (label, stage))
                else:
                    self._info(D_MANIFEST_SKIP, source, "", label, "`op %s 显式 SKIP：阶段 %s 晚于 %s`"
                               % (label, stage, required_stage))
        return self._bundle(state["ready"], state["pending"])

    def _bundle(self, ready: list, pending: list) -> SchemaBundle:
        diags = tuple(sorted( self._diags,
            key=lambda item: (_b(item.source), _b(item.pointer), _b(item.op or ""),
                              _b(item.code), _b(item.severity), _b(item.message)), ))
        ordered = tuple(sorted(pending, key=lambda item: _b(item.op)))
        if any(diag.severity == "error" for diag in diags):
            return SchemaBundle(False, (), ordered, (), (), diags)
        nodes = tuple(self._nodes[rid] for rid in sorted(self._nodes, key=_b))
        named = tuple( node.ref for node in sorted((item for item in nodes if item.title),
                               key=lambda item: _b(item.title))
        )
        index = {node.ref.id: node for node in nodes}
        ready_sorted = tuple(sorted(ready, key=lambda item: _b(item.op)))
        return SchemaBundle(True, ready_sorted, ordered, nodes, named, diags, index)


def _no_constant(name: str) -> Any:
    """拒绝 NaN/Infinity 等非标准 JSON 常量（数值只走 int/Decimal）。"""
    raise ValueError("JSON 常量 %s 不被接受" % name)


def compile_manifest(manifest_path: Path, required_stage: Stage | None = None,
                     release: bool = False) -> SchemaBundle:
    """把 manifest 与其引用的受限 schema 编译成可信类型图。

    required_stage 给定时，早于或等于该阶段的 pending 条目是错误，晚于该阶段的
    pending 条目只记一条显式 SKIP 的 info；release=True 时任何 pending 都是错误。
    清单不可读原样抛 OSError；本库内部故障抛 SchemaToolError。两种情况都不写成
    valid=False。
    """
    if required_stage is not None and required_stage not in STAGES:
        raise SchemaToolError( "required_stage 必须是 %s 之一：%r" % (STAGES, required_stage))
    if not isinstance(release, bool):
        raise SchemaToolError("release 必须是布尔值")
    return _Compiler(Path(manifest_path)).run(required_stage, release)
