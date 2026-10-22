"""CORE-67 阶段1：把 CORE-100 类型图发成不可变 Dart DTO 与严格 codec。

本模块只消费 dto_schema.SchemaBundle（类型图）与 manifest 文件名：不读 SADD、
不二次解析 schema 文本、不依赖 CORE-56/CORE-03 的实现。阶段1 覆盖 object、
具名与内联 enum、array、ref 别名、标量与 base64 codec；union、tuple、typed map
与无 title 的内联 object 属阶段2，遇到即拒绝生成（退出码 1，码 DTO_SCHEMA_INVALID）。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

import dto_schema as ds

#: 生成物首行的固定标记（CLI 用它判定“这是生成物”）。
GENERATED_MARKER = "// GENERATED CODE - DO NOT MODIFY BY HAND."
#: 生成物第二行的生成器标识，与标记一起构成生成物判定。
GENERATOR_LINE = "// generator: CORE-67 v1"
#: 生成物保持生成器排版：整文件关闭 dart format（app/ 的 format 检查据此稳定）。
FORMAT_OFF = "// dart format off"
#: 共享类型所在的 schema 文件名与对应的生成文件名。
TYPES_SOURCE = "types.schema.json"
TYPES_FILE = "types.g.dart"

#: 本卡自己的四个诊断码（其余诊断码原样透传 CORE-100）。
D_SCHEMA_INVALID = "DTO_SCHEMA_INVALID"
D_NAME_CONFLICT = "DTO_NAME_CONFLICT"
D_PENDING_SKIP = "DTO_PENDING_SKIP"
D_HEADER_MISSING = "DTO_HEADER_MISSING"

_SPLIT_RE = re.compile(r"[^0-9A-Za-z]+")

#: 生成 Dart 字面量时要处理的三个字符（用 chr 写，源码里不出现转义）。
_BACKSLASH = chr(92)
_DOLLAR = chr(36)
_QUOTE = chr(39)

#: Dart 保留字：类型名撞上时按命名规则⑥追加 Value。
_RESERVED = frozenset({
    "abstract", "as", "assert", "async", "await", "base", "break", "case", "catch",
    "class", "const", "continue", "covariant", "default", "deferred", "do", "dynamic",
    "else", "enum", "export", "extends", "extension", "external", "factory", "false",
    "final", "finally", "for", "get", "hide", "if", "implements", "import", "in",
    "interface", "is", "late", "library", "mixin", "new", "null", "of", "on", "operator",
    "part", "required", "rethrow", "return", "sealed", "set", "show", "static", "super",
    "switch", "sync", "this", "throw", "true", "try", "type", "typedef", "var", "void",
    "when", "while", "with", "yield",
})

#: Dart 核心/常用类型名：撞上时同样追加 Value（规则⑥）。
_CORE_TYPES = frozenset({
    "Object", "String", "int", "double", "bool", "num", "List", "Map", "Set",
    "Iterable", "Future", "Stream", "Function", "Type", "Symbol", "Record", "Never",
    "Null", "Enum", "Comparable", "DateTime", "Duration", "Uri", "BigInt", "Exception",
    "Error", "Uint8List",
})

#: 枚举成员名不可用的标识（Enum 自带成员与生成器自用的静态成员）。
_ENUM_MEMBERS = frozenset({
    "name", "index", "values", "hashCode", "runtimeType", "toString", "noSuchMethod",
    "wire", "byWire", "fromWire",
})


@dataclass(frozen=True)
class Diagnostic:
    """一条生成诊断；file/pointer/op 缺失时为 None。"""

    severity: str
    code: str
    file: str | None
    pointer: str | None
    op: str | None
    message: str


@dataclass(frozen=True)
class EmittedFile:
    """一个应存在的生成文件：相对 <out> 的路径与完整文本。"""

    path: str
    text: str

    @property
    def sha256(self) -> str:
        """文本按 UTF-8 编码后的 sha256 十六进制。"""
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EmitResult:
    """一次生成的完整结果。"""

    files: tuple[EmittedFile, ...]
    diagnostics: tuple[Diagnostic, ...]
    refused: bool
    skipped: tuple[str, ...] = ()


def has_generated_header(text: str) -> bool:
    """按头两行判定“生成物”：同时含 GENERATED 标记与 CORE-67 v1 生成器行。"""
    lines = text.splitlines()
    head = "\n".join(lines[:2])
    return GENERATED_MARKER in head and GENERATOR_LINE in head


def pascal(text: str) -> str:
    """把 title/字段名转成 PascalCase；只拆非字母数字分隔符。"""
    parts = [part for part in _SPLIT_RE.split(text) if part]
    return "".join(part[:1].upper() + part[1:] for part in parts) or "Dto"


def type_name_for(title: str) -> str:
    """命名规则①+⑥：title → 类名，撞保留字或核心类型时追加 Value。"""
    name = pascal(title)
    if name in _RESERVED or name in _CORE_TYPES:
        name += "Value"
    return name


def _enum_wire(item: object) -> str:
    """枚举取值：SchemaScalar 取 value，纯字符串原样返回。"""
    if isinstance(item, ds.SchemaScalar):
        return item.value
    return str(item)


def enum_member_for(wire: str) -> str:
    """wire 取值 → Dart 枚举成员名（非法/保留名追加 Value）。"""
    parts = [part for part in _SPLIT_RE.split(wire) if part]
    if not parts:
        member = "v"
    else:
        member = parts[0][:1].lower() + parts[0][1:]
        member += "".join(part[:1].upper() + part[1:] for part in parts[1:])
    if not member[:1].isalpha():
        member = "v" + member
    if member in _RESERVED or member in _ENUM_MEMBERS:
        member += "Value"
    return member


def _source_of(ref_id: str) -> str:
    return ref_id.split("#", 1)[0]


def _pointer_of(ref_id: str) -> str:
    parts = ref_id.split("#", 1)
    return parts[1] if len(parts) == 2 else ""



@dataclass
class _Decl:
    """一个待渲染的声明：类、枚举或别名。"""

    dart_name: str
    node: ds.SchemaNode
    file: str
    sort_key: str
    op: str
    kind: str
    target: str = ""
    refs: set[str] = field(default_factory=set)
    helpers: set[str] = field(default_factory=set)
    libs: set[str] = field(default_factory=set)
    rows: list = field(default_factory=list)


class _Builder:
    """一次生成的全部状态：命名、声明收集、渲染。"""

    def __init__(self, bundle: ds.SchemaBundle, manifest_name: str) -> None:
        self.bundle = bundle
        self.manifest_name = manifest_name
        self.nodes: dict[str, ds.SchemaNode] = {node.ref.id: node for node in bundle.nodes}
        self.schema_domain: dict[str, str] = {}
        for op in bundle.ready:
            self.schema_domain[op.schema] = op.op.split(".", 1)[0]
        self.names: dict[str, str] = {}
        self.used: dict[str, str] = {}
        self.decls: list[_Decl] = []
        self.diagnostics: list[Diagnostic] = []
        self.sensitive: set[tuple[str, str]] = set()
        self.refused = False
        self.decl_by_name: dict[str, _Decl] = {}
        self.wrapper_sources: set[str] = set()
        self.files: tuple[EmittedFile, ...] = ()
        for op in bundle.ready:
            for path in op.sensitive_paths:
                self._mark_sensitive(op, path)

    # ---- 公共入口 -------------------------------------------------------

    def build(self) -> None:
        """收集声明、判定不支持形状并渲染全部文件。"""
        kinds: dict[str, set[str]] = {}
        for node in self.nodes.values():
            kinds.setdefault(_source_of(node.ref.id), set()).add(node.kind)
        self.wrapper_sources = {source for source, seen in kinds.items() if seen == {"ref"}}
        for op in self.bundle.ready:
            for ref in (op.request, op.ok):
                self._type_text(ref.id, "", "", op.op, None)
        index = 0
        while index < len(self.decls):
            decl = self.decls[index]
            if decl.kind == "object":
                for fld in decl.node.fields:
                    decl.rows.append((self._member_for(fld), fld)
                        + self._field(fld, decl.dart_name, decl.op, decl))
            index += 1
        self.decl_by_name = {decl.dart_name: decl for decl in self.decls}
        self.files = self._render_files()

    def result(self) -> EmitResult:
        """打包结果；拒绝生成时不给任何文件。"""
        diagnostics = tuple(sorted(self.diagnostics, key=_diag_key))
        return EmitResult(tuple() if self.refused else self.files, diagnostics, self.refused)

    # ---- 诊断与敏感字段 -------------------------------------------------

    def _note(self, code: str, message: str, ref_id: str, op: str,
              severity: str = "error") -> None:
        self.diagnostics.append(Diagnostic(
            severity=severity, code=code, file=_source_of(ref_id),
            pointer=_pointer_of(ref_id), op=op, message=message))
        if severity == "error":
            self.refused = True

    def _unsupported(self, node: ds.SchemaNode, op: str) -> None:
        self._note(
            D_SCHEMA_INVALID,
            "阶段1 不支持的形状 %s（%s）；按卡规模行留待阶段2" % (node.kind, node.ref.id),
            node.ref.id, op)

    def _mark_sensitive(self, op: ds.ReadySchemaOp, path: str) -> None:
        parts = [part for part in path.split("/") if part]
        if len(parts) < 2:
            return
        root = {"body": op.request, "ok": op.ok}.get(parts[0])
        if root is None:
            return
        concrete = self._concrete(root.id)
        self.sensitive.add((concrete.ref.id, parts[1]))

    # ---- 命名与类型 -----------------------------------------------------

    def _claim(self, base: str, node: ds.SchemaNode) -> tuple[str, bool]:
        owner = self.used.get(base)
        if owner is None or owner == node.ref.id:
            self.used[base] = node.ref.id
            return base, True
        return base, False

    def _file_for(self, node: ds.SchemaNode, op: str) -> str:
        source = _source_of(node.ref.id)
        if source == TYPES_SOURCE or source in self.wrapper_sources:
            return TYPES_FILE
        domain = self.schema_domain.get(source)
        if domain is not None:
            return domain + ".g.dart"
        return op.split(".", 1)[0] + ".g.dart"

    def _concrete(self, ref_id: str) -> ds.SchemaNode:
        """跟随 ref 链到具体节点；自引用环就地停下。"""
        node = self.nodes[ref_id]
        seen: set[str] = set()
        while node.kind == "ref" and node.target is not None and node.ref.id not in seen:
            seen.add(node.ref.id)
            node = self.nodes[node.target.id]
        return node


    def _type_text(self, ref_id: str, parent: str, wire: str, op: str,
                   decl: _Decl | None) -> str:
        """节点 → Dart 类型文本；顺带登记具名/内联声明并记录交叉引用。"""
        node = self.nodes[ref_id]
        if node.kind == "ref":
            if node.title is not None:
                return self._named(node, op, decl)
            if node.target is None:
                self._note(D_SCHEMA_INVALID, "ref 节点缺少 target（%s）" % node.ref.id,
                           node.ref.id, op)
                return "Object"
            return self._type_text(node.target.id, parent, wire, op, decl)
        if node.title is not None:
            return self._named(node, op, decl)
        kind = node.kind
        if kind == "string":
            if node.enum_values:
                return self._inline_enum(node, parent, wire, op, decl)
            if node.limits.format == "base64":
                self._use(decl, "bytes", "dart:typed_data")
                return "Uint8List"
            return "String"
        if kind == "integer":
            return "int"
        if kind == "number":
            return "double"
        if kind == "boolean":
            return "bool"
        if kind == "array":
            if node.item is None:
                self._note(D_SCHEMA_INVALID, "array 节点缺少 items（%s）" % node.ref.id,
                           node.ref.id, op)
                return "List<Object?>"
            inner = self._type_text(node.item.id, parent, wire, op, decl)
            return "List<%s>" % inner
        self._unsupported(node, op)
        return "Object"

    def _named(self, node: ds.SchemaNode, op: str, decl: _Decl | None) -> str:
        """具名节点 → 类/枚举/别名，并登记到其声明文件。"""
        existing = self.names.get(node.ref.id)
        if existing is not None:
            if decl is not None:
                decl.refs.add(existing)
            return existing
        base = type_name_for(node.title or "")
        name, ok = self._claim(base, node)
        if not ok:
            self._note(D_NAME_CONFLICT, "类型名 %s 已被占用（title %s）" % (base, node.title),
                       node.ref.id, op)
        self.names[node.ref.id] = name
        kind = "object"
        if node.kind == "ref":
            kind = "alias"
        elif node.kind == "string" and node.enum_values:
            kind = "enum"
        elif node.kind != "object":
            self._unsupported(node, op)
        new_decl = _Decl(
            dart_name=name, node=node, file=self._file_for(node, op),
            sort_key=node.title or name, op=op, kind=kind)
        self.decls.append(new_decl)
        if decl is not None:
            decl.refs.add(name)
        if kind == "alias":
            if node.target is not None:
                new_decl.target = self._type_text(node.target.id, name, "", op, new_decl)
            new_decl.refs.add(new_decl.target)
        return name

    def _inline_enum(self, node: ds.SchemaNode, parent: str, wire: str, op: str,
                     decl: _Decl | None) -> str:
        """内联 enum 命名（规则③）：<父类><字段 Pascal>，冲突再追加 Kind。"""
        existing = self.names.get(node.ref.id)
        if existing is not None:
            if decl is not None:
                decl.refs.add(existing)
            return existing
        base = parent + pascal(wire)
        name, ok = self._claim(base, node)
        if not ok:
            name, ok = self._claim(base + "Kind", node)
            if not ok:
                self._note(D_NAME_CONFLICT, "内联 enum 名 %s 冲突（%s）" % (base, node.ref.id),
                           node.ref.id, op)
        self.names[node.ref.id] = name
        self.decls.append(_Decl(
            dart_name=name, node=node, file=self._file_for(node, op),
            sort_key=base, op=op, kind="enum"))
        if decl is not None:
            decl.refs.add(name)
        return name

    def _use(self, decl: _Decl | None, helper: str, lib: str | None = None) -> None:
        if decl is None:
            return
        decl.helpers.add(helper)
        if lib is not None:
            decl.libs.add(lib)


    # ---- 字段：类型、读、写 ---------------------------------------------

    def _member_for(self, fld: ds.SchemaField) -> str:
        """字段名：优先 dto_schema 的 dart_name，非法或撞成员名时回退。"""
        name = fld.dart_name
        if not name[:1].isalpha() or name in _RESERVED or name in _ENUM_MEMBERS:
            return camel(fld.wire_name) + "Value"
        return name

    def _type_nullable(self, fld: ds.SchemaField) -> bool:
        """字段类型是否加 ?：节点自身 nullable，或 schema 未列为必填。"""
        return self.nodes[fld.value.id].nullable or not fld.required

    def _read_suffix(self, fld: ds.SchemaField) -> str:
        """读器后缀：required 与 nullable 独立（卡 :38）。

        必填非空 → 严格读器（缺失或 null 都抛）；必填可空 → presence 读器
        （键必须出现、值可为 null）；非 required → 缺键与显式 null 均映射 null。
        """
        if not fld.required:
            return "OrNull"
        return "Present" if self.nodes[fld.value.id].nullable else ""

    def _field(self, fld: ds.SchemaField, parent: str, op: str,
               decl: _Decl) -> tuple[str, str, str]:
        """字段 → (类型文本, 读表达式, 写表达式)。"""
        type_text = self._type_text(fld.value.id, parent, fld.wire_name, op, decl)
        nullable = self._type_nullable(fld)
        if nullable:
            type_text += "?"
        read = self._decode(fld.value.id, fld.wire_name, self._read_suffix(fld), op, decl)
        write = self._encode(fld.value.id, self._member_for(fld), nullable, decl)
        return type_text, read, write

    def _decode(self, ref_id: str, key: str, suffix: str, op: str,
                decl: _Decl | None) -> str:
        """字段值 → 读表达式；严格/presence 读器在缺失或类型错时抛 FormatException。"""
        node = self._concrete(ref_id)
        name = self.names.get(node.ref.id)
        if node.kind == "object":
            if node.title is None or name is None:
                return "const <String, Object?>{}"
            self._use(decl, "readObject" + suffix)
            return "readObject%s(json, %s, %s.fromJson)" % (
                suffix, _dart_string(key), name)
        if node.kind == "array":
            if node.item is None:
                return "List<Object?>.unmodifiable(<Object?>[])"
            element = self._element_decode(node.item.id, op, decl)
            self._use(decl, "readList" + suffix)
            return "readList%s(json, %s, %s)" % (
                suffix, _dart_string(key), element)
        if node.kind == "boolean":
            self._use(decl, "readBool" + suffix)
            return "readBool%s(json, %s)" % (suffix, _dart_string(key))
        if node.kind == "integer":
            self._use(decl, "readInt" + suffix)
            return "readInt%s(json, %s)" % (suffix, _dart_string(key))
        if node.kind == "number":
            self._use(decl, "readDouble" + suffix)
            return "readDouble%s(json, %s)" % (suffix, _dart_string(key))
        if node.kind == "string" and node.enum_values and name is not None:
            self._use(decl, "readEnum" + suffix)
            return "readEnum%s(json, %s, %s.fromWire)" % (
                suffix, _dart_string(key), name)
        if node.kind == "string" and node.limits.format == "base64":
            self._use(decl, "readBytes" + suffix)
            return "readBytes%s(json, %s)" % (suffix, _dart_string(key))
        self._use(decl, "readString" + suffix)
        return "readString%s(json, %s)" % (suffix, _dart_string(key))

    def _element_decode(self, ref_id: str, op: str, decl: _Decl | None) -> str:
        """数组元素 → 传给 readList 的解码函数文本。"""
        node = self._concrete(ref_id)
        name = self.names.get(node.ref.id)
        if node.kind == "object" and node.title is not None and name is not None:
            self._use(decl, "asObject")
            return "(Object? value) => %s.fromJson(asObject(value))" % name
        if node.kind == "string" and node.enum_values and name is not None:
            self._use(decl, "asString")
            return "(Object? value) => %s.fromWire(asString(value))" % name
        if node.kind == "array":
            self._note(D_SCHEMA_INVALID, "阶段1 不支持嵌套数组（%s）；按卡规模行留待阶段2"
                       % node.ref.id, node.ref.id, op)
            return "asObject"
        mapping = {
            "boolean": "asBool", "integer": "asInt", "number": "asDouble",
        }
        helper = mapping.get(node.kind)
        if helper is None:
            helper = "asBytes" if node.limits.format == "base64" else "asString"
        self._use(decl, helper)
        return helper


    def _encode(self, ref_id: str, expr: str, soft: bool, decl: _Decl | None) -> str:
        """字段值 → 写表达式；无变换时原样返回（JSON 原生）。"""
        node = self._concrete(ref_id)
        name = self.names.get(node.ref.id)
        if node.kind == "object" and node.title is not None and name is not None:
            return expr + ("?.toJson()" if soft else ".toJson()")
        if node.kind == "string" and node.enum_values and name is not None:
            return expr + ("?.wire" if soft else ".wire")
        if node.kind == "array" and node.item is not None:
            inner = self._element_encode(node.item.id, "item", decl)
            if inner == "item":
                return expr
            self._use(decl, "encodeList")
            if soft:
                return "%s == null ? null : encodeList(%s, %s)" % (expr, expr + "!", inner)
            return "encodeList(%s, %s)" % (expr, inner)
        if node.kind == "string" and node.limits.format == "base64":
            self._use(decl, "base64Encode", "dart:convert")
            if soft:
                return "%s == null ? null : base64Encode(%s!)" % (expr, expr)
            return "base64Encode(%s)" % expr
        return expr

    def _element_encode(self, ref_id: str, param: str, decl: _Decl | None) -> str:
        """数组元素 → 传给 encodeList 的编码函数文本；原生元素返回参数名。"""
        node = self._concrete(ref_id)
        name = self.names.get(node.ref.id)
        if node.kind == "object" and node.title is not None and name is not None:
            return "(%s %s) => %s.toJson()" % (name, param, param)
        if node.kind == "string" and node.enum_values and name is not None:
            return "(%s %s) => %s.wire" % (name, param, param)
        if node.kind == "string" and node.limits.format == "base64":
            self._use(decl, "base64Encode", "dart:convert")
            return "base64Encode"
        return param

    # ---- 渲染 -----------------------------------------------------------

    def _render_files(self) -> tuple[EmittedFile, ...]:
        """按文件分组渲染；组内按 title/类名排序，文件按路径字节序排序。"""
        groups: dict[str, list[_Decl]] = {}
        for decl in self.decls:
            groups.setdefault(decl.file, []).append(decl)
        files = []
        for path in sorted(groups, key=lambda item: item.encode("utf-8")):
            decls = sorted(groups[path], key=lambda d: (d.sort_key, d.dart_name))
            text = self._render_file(path, decls)
            files.append(EmittedFile(path=path, text=text))
        return tuple(files)

    def _render_file(self, path: str, decls: list[_Decl]) -> str:
        """一个文件：三行头、导入、声明体、按需附带的私有解码助手。"""
        schemas = sorted({_source_of(decl.node.ref.id) for decl in decls})
        libs: set[str] = set()
        helpers: set[str] = set()
        imports: set[str] = set()
        for decl in decls:
            libs.update(decl.libs)
            helpers.update(decl.helpers)
            for name in decl.refs:
                other = self.decl_by_name.get(name)
                if other is not None and other.file != path:
                    imports.add(other.file)
        for helper in tuple(helpers):
            helpers.update(_HELPER_DEPS.get(helper, ()))
        for helper in helpers:
            libs.update(_HELPER_LIBS.get(helper, ()))
        lines = [
            GENERATED_MARKER,
            GENERATOR_LINE,
            "// source: manifest=%s; schemas=%s" % (self.manifest_name, ", ".join(schemas)),
            FORMAT_OFF,
            "",
        ]
        for lib in sorted(libs):
            lines.append("import '%s';" % lib)
        for name in sorted(imports):
            lines.append("import '%s';" % name)
        if libs or imports:
            lines.append("")
        for decl in decls:
            lines.append(self._render_decl(decl))
            lines.append("")
        for helper in sorted(helpers):
            source = _HELPER_SOURCES.get(helper)
            if source is not None:
                lines.append(source)
                lines.append("")
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines) + "\n"

    def _render_decl(self, decl: _Decl) -> str:
        if decl.kind == "enum":
            return self._render_enum(decl)
        if decl.kind == "alias":
            return ("/// 共享别名 %s：wire 形状与 %s 相同。\n"
                    "typedef %s = %s;" % (decl.sort_key, decl.target, decl.dart_name,
                                          decl.target))
        return self._render_object(decl)


    def _render_enum(self, decl: _Decl) -> str:
        """枚举：成员带 wire 取值、byWire 索引与严格 fromWire。"""
        values = [_enum_wire(item) for item in (decl.node.enum_values or ())]
        members: list[tuple[str, str]] = []
        seen: set[str] = set()
        for wire in values:
            member = enum_member_for(wire)
            while member in seen:
                member += "Value"
            seen.add(member)
            members.append((member, wire))
        if not members:
            members = [("v", "")]
        lines = ["/// 枚举 " + decl.sort_key + "：wire 取值为 [wire]。"]
        lines.append("enum %s {" % decl.dart_name)
        rendered = [
            "  /// wire 取值 %s。\n  %s(%s)" % (_doc_text(wire), member,
                                              _dart_string(wire))
            for member, wire in members]
        lines.append(",\n".join(rendered) + ";")
        lines.append("")
        lines.append("  const %s(this.wire);" % decl.dart_name)
        lines.append("")
        lines.append("  /// wire 取值（JSON 字符串）。")
        lines.append("  final String wire;")
        lines.append("")
        lines.append("  /// wire 取值 → 成员。")
        lines.append("  static const Map<String, %s> byWire = <String, %s>{" % (
            decl.dart_name, decl.dart_name))
        for member, wire in members:
            lines.append("    %s: %s.%s," % (_dart_string(wire), decl.dart_name, member))
        lines.append("  };")
        lines.append("")
        lines.append("  /// 严格解码：未知 wire 取值抛 [FormatException]。")
        lines.append("  static %s fromWire(String wire) {" % decl.dart_name)
        lines.append("    final %s? found = byWire[wire];" % decl.dart_name)
        lines.append("    if (found == null) {")
        head = "      throw FormatException('未知 %s wire 取值: " % decl.dart_name
        lines.append(head + _DOLLAR + "wire');")
        lines.append("    }")
        lines.append("    return found;")
        lines.append("  }")
        lines.append("}")
        return "\n".join(lines)

    def _render_object(self, decl: _Decl) -> str:
        """对象：const 构造、final 字段、严格 fromJson、toJson 与脱敏 toString。"""
        rows = decl.rows
        lines = ["/// %s：不可变值对象；wire 键见各字段。" % decl.sort_key]
        lines.append("final class %s {" % decl.dart_name)
        if rows:
            lines.append("  /// 由 wire 字段构造。")
            lines.append("  const %s({" % decl.dart_name)
            for member, fld, type_text, read, write in rows:
                lead = "    this." if not fld.required else "    required this."
                lines.append("%s%s," % (lead, member))
            lines.append("  });")
        else:
            lines.append("  /// 无 wire 字段的空对象。")
            lines.append("  const %s();" % decl.dart_name)
        for member, fld, type_text, read, write in rows:
            lines.append("")
            lines.append("  /// wire 键 %s。" % fld.wire_name)
            lines.append("  final %s %s;" % (type_text, member))
        lines.append("")
        lines.append("  /// 严格解码：缺失必填或类型不符抛 [FormatException]。")
        lines.append("  factory %s.fromJson(Map<String, Object?> json) {" % decl.dart_name)
        if rows:
            lines.append("    return %s(" % decl.dart_name)
            for member, fld, type_text, read, write in rows:
                lines.append("      %s: %s," % (member, read))
            lines.append("    );")
        else:
            lines.append("    return const %s();" % decl.dart_name)
        lines.append("  }")
        lines.append("")
        lines.append("  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。")
        lines.append("  Map<String, Object?> toJson() {")
        if rows:
            lines.append("    return <String, Object?>{")
            for member, fld, type_text, read, write in rows:
                lines.append("      %s: %s," % (_dart_string(fld.wire_name), write))
            lines.append("    };")
        else:
            lines.append("    return <String, Object?>{};")
        lines.append("  }")
        lines.append("")
        lines.append("  @override")
        lines.append("  String toString() {")
        clean = []
        for row in rows:
            member = row[0]
            wire = row[1].wire_name
            if (decl.node.ref.id, wire) in self.sensitive:
                clean.append(member + ": <redacted>")
            else:
                clean.append(member + ": " + _DOLLAR + member)
        lines.append("    return %s;" % _describe(decl.dart_name, clean))
        lines.append("  }")
        lines.append("}")
        return "\n".join(lines)



def camel(text: str) -> str:
    """wire 名 → lowerCamelCase；非法标识或撞成员名时追加 Value。"""
    parts = [part for part in _SPLIT_RE.split(text) if part]
    if not parts:
        name = "v"
    else:
        name = parts[0][:1].lower() + parts[0][1:]
        name += "".join(part[:1].upper() + part[1:] for part in parts[1:])
    if not name[:1].isalpha():
        name = "v" + name
    if name in _RESERVED or name in _ENUM_MEMBERS:
        name += "Value"
    return name


def _dart_string(text: str) -> str:
    """Dart 单引号字符串字面量：转义反斜杠、单引号与美元符。"""
    escaped = text.replace(_BACKSLASH, _BACKSLASH * 2)
    escaped = escaped.replace(_QUOTE, _BACKSLASH + _QUOTE)
    escaped = escaped.replace(_DOLLAR, _BACKSLASH + _DOLLAR)
    return _QUOTE + escaped + _QUOTE


def _doc_text(text: str) -> str:
    """doc 注释里的单行文本：折行与反斜杠转义，避免破坏 /// 注释。"""
    return text.replace(_BACKSLASH, _BACKSLASH * 2).replace("\n", _BACKSLASH + "n")


def _describe(class_name: str, parts: list[str]) -> str:
    """toString 体：类名(字段: $字段, 敏感: <redacted>)。"""
    if not parts:
        return _QUOTE + class_name + "()" + _QUOTE
    body = ", ".join(parts)
    return _QUOTE + class_name + "(" + body + ")" + _QUOTE


def _diag_key(diag: Diagnostic) -> tuple[str, str, str, str]:
    """诊断排序键：文件、码、操作、消息。"""
    return (diag.file or "", diag.code, diag.op or "", diag.message)


def emit(bundle: ds.SchemaBundle, manifest_name: str) -> EmitResult:
    """纯函数：SchemaBundle → (Dart 文件, 诊断, 是否拒绝, 跳过的 pending)。

    阶段1 只用类型图，不读 schema 原文；CORE-100 的诊断原样转写，
    pending 操作逐条记 DTO_PENDING_SKIP 除非 CORE-100 已为它出过诊断。
    """
    builder = _Builder(bundle, manifest_name)
    for diag in bundle.diagnostics:
        if diag.severity != "error":
            continue
        builder.diagnostics.append(Diagnostic(
            severity="error", code=D_SCHEMA_INVALID,
            file=diag.source or None, pointer=diag.pointer or None,
            op=diag.op or None,
            message="CORE-100 %s：%s" % (diag.code, diag.message)))
    covered = {diag.op for diag in bundle.diagnostics if diag.op}
    skipped = []
    for op in bundle.pending:
        if op.op in covered:
            continue
        skipped.append(op.op)
        builder.diagnostics.append(Diagnostic(
            severity="info", code=D_PENDING_SKIP, file=None, pointer=None, op=op.op,
            message="SKIP pending %s: %s" % (op.op, op.blocked_reason or "未给出原因")))
    if not bundle.valid:
        builder.refused = True
    builder.build()
    result = builder.result()
    return EmitResult(result.files, result.diagnostics, result.refused,
                      tuple(sorted(skipped)))



#: 按需附带的私有解码助手源码；键是生成代码里调用的函数名。
_HELPER_SOURCES: dict[str, str] = {
    "readString": '''/// 严格读取 string 字段。
String readString(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is String) return value;
  throw FormatException('字段 ' + key + ' 应为 string');
}''',
    "readStringOrNull": '''/// 读取可空 string 字段。
String? readStringOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is String) return value;
  throw FormatException('字段 ' + key + ' 应为 string 或 null');
}''',
    "readInt": '''/// 严格读取 int 字段。
int readInt(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is int) return value;
  throw FormatException('字段 ' + key + ' 应为 int');
}''',
    "readIntOrNull": '''/// 读取可空 int 字段。
int? readIntOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is int) return value;
  throw FormatException('字段 ' + key + ' 应为 int 或 null');
}''',
    "readDouble": '''/// 严格读取 number 字段；JSON 整数按 double 收下。
double readDouble(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is int) return value.toDouble();
  if (value is double && value.isFinite) return value;
  throw FormatException('字段 ' + key + ' 应为 number');
}''',
    "readDoubleOrNull": '''/// 读取可空 number 字段。
double? readDoubleOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is int) return value.toDouble();
  if (value is double && value.isFinite) return value;
  throw FormatException('字段 ' + key + ' 应为 number 或 null');
}''',
    "readBool": '''/// 严格读取 bool 字段。
bool readBool(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is bool) return value;
  throw FormatException('字段 ' + key + ' 应为 bool');
}''',
    "readBoolOrNull": '''/// 读取可空 bool 字段。
bool? readBoolOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is bool) return value;
  throw FormatException('字段 ' + key + ' 应为 bool 或 null');
}''',

    "readBytes": '''/// 严格读取 base64 字节字段。
Uint8List readBytes(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  final String? text = value is String ? value : null;
  if (text != null) return base64Decode(text);
  throw FormatException('字段 ' + key + ' 应为 base64 字符串');
}''',
    "readBytesOrNull": '''/// 读取可空 base64 字节字段。
Uint8List? readBytesOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  final String? text = value is String ? value : null;
  if (text != null) return base64Decode(text);
  throw FormatException('字段 ' + key + ' 应为 base64 字符串或 null');
}''',
    "readObject": '''/// 严格读取对象字段并解码。
T readObject<T>(
  Map<String, Object?> json,
  String key,
  T Function(Map<String, Object?>) decode,
) {
  final Object? value = json[key];
  if (value is Map<String, Object?>) return decode(value);
  throw FormatException('字段 ' + key + ' 应为 object');
}''',
    "readObjectOrNull": '''/// 读取可空对象字段并解码。
T? readObjectOrNull<T>(
  Map<String, Object?> json,
  String key,
  T Function(Map<String, Object?>) decode,
) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is Map<String, Object?>) return decode(value);
  throw FormatException('字段 ' + key + ' 应为 object 或 null');
}''',
    "readEnum": '''/// 严格读取枚举字段（wire 字符串）。
T readEnum<T>(
  Map<String, Object?> json,
  String key,
  T Function(String) fromWire,
) {
  final Object? value = json[key];
  if (value is String) return fromWire(value);
  throw FormatException('字段 ' + key + ' 应为字符串枚举');
}''',
    "readEnumOrNull": '''/// 读取可空枚举字段（wire 字符串）。
T? readEnumOrNull<T>(
  Map<String, Object?> json,
  String key,
  T Function(String) fromWire,
) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is String) return fromWire(value);
  throw FormatException('字段 ' + key + ' 应为字符串枚举或 null');
}''',
    "readList": '''/// 严格读取数组字段并逐个解码。
List<T> readList<T>(
  Map<String, Object?> json,
  String key,
  T Function(Object?) decode,
) {
  final Object? value = json[key];
  if (value is List<Object?>) {
    return List<T>.unmodifiable(value.map<T>(decode));
  }
  throw FormatException('字段 ' + key + ' 应为数组');
}''',
    "readListOrNull": '''/// 读取可空数组字段并逐个解码。
List<T>? readListOrNull<T>(
  Map<String, Object?> json,
  String key,
  T Function(Object?) decode,
) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is List<Object?>) {
    return List<T>.unmodifiable(value.map<T>(decode));
  }
  throw FormatException('字段 ' + key + ' 应为数组或 null');
}''',

    "asString": '''/// 把 JSON 值收成 string。
String asString(Object? value) {
  if (value is String) return value;
  throw const FormatException('元素应为 string');
}''',
    "asInt": '''/// 把 JSON 值收成 int。
int asInt(Object? value) {
  if (value is int) return value;
  throw const FormatException('元素应为 int');
}''',
    "asDouble": '''/// 把 JSON 值收成 double。
double asDouble(Object? value) {
  if (value is int) return value.toDouble();
  if (value is double && value.isFinite) return value;
  throw const FormatException('元素应为 number');
}''',
    "asBool": '''/// 把 JSON 值收成 bool。
bool asBool(Object? value) {
  if (value is bool) return value;
  throw const FormatException('元素应为 bool');
}''',
    "asBytes": '''/// 把 JSON 值收成 base64 字节。
Uint8List asBytes(Object? value) {
  if (value is String) return base64Decode(value);
  throw const FormatException('元素应为 base64 字符串');
}''',
    "asObject": '''/// 把 JSON 值收成对象。
Map<String, Object?> asObject(Object? value) {
  if (value is Map<String, Object?>) return value;
  throw const FormatException('元素应为 object');
}''',
    "encodeList": '''/// 把列表逐项编码成 JSON 值。
List<Object?> encodeList<T>(List<T> values, Object? Function(T) encode) {
  return values.map<Object?>(encode).toList(growable: false);
}''',

    "readStringPresent": '''/// 读取必填且可空的 string 字段：键必须出现，值可为 null。
String? readStringPresent(Map<String, Object?> json, String key) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填字段 ' + key);
  }
  return readStringOrNull(json, key);
}''',
    "readIntPresent": '''/// 读取必填且可空的 int 字段：键必须出现，值可为 null。
int? readIntPresent(Map<String, Object?> json, String key) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填字段 ' + key);
  }
  return readIntOrNull(json, key);
}''',
    "readDoublePresent": '''/// 读取必填且可空的 number 字段：键必须出现，值可为 null。
double? readDoublePresent(Map<String, Object?> json, String key) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填字段 ' + key);
  }
  return readDoubleOrNull(json, key);
}''',
    "readBoolPresent": '''/// 读取必填且可空的 bool 字段：键必须出现，值可为 null。
bool? readBoolPresent(Map<String, Object?> json, String key) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填字段 ' + key);
  }
  return readBoolOrNull(json, key);
}''',
    "readBytesPresent": '''/// 读取必填且可空的 base64 字节字段：键必须出现，值可为 null。
Uint8List? readBytesPresent(Map<String, Object?> json, String key) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填字段 ' + key);
  }
  return readBytesOrNull(json, key);
}''',
    "readObjectPresent": '''/// 读取必填且可空的对象字段并解码：键必须出现，值可为 null。
T? readObjectPresent<T>(
  Map<String, Object?> json,
  String key,
  T Function(Map<String, Object?>) decode,
) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填字段 ' + key);
  }
  return readObjectOrNull<T>(json, key, decode);
}''',
    "readEnumPresent": '''/// 读取必填且可空的枚举字段（wire 字符串）：键必须出现，值可为 null。
T? readEnumPresent<T>(
  Map<String, Object?> json,
  String key,
  T Function(String) fromWire,
) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填字段 ' + key);
  }
  return readEnumOrNull<T>(json, key, fromWire);
}''',
    "readListPresent": '''/// 读取必填且可空的数组字段并逐个解码：键必须出现，值可为 null。
List<T>? readListPresent<T>(
  Map<String, Object?> json,
  String key,
  T Function(Object?) decode,
) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填字段 ' + key);
  }
  return readListOrNull<T>(json, key, decode);
}''',
}

#: presence 读器复用可空读器：缺键检查与类型检查分开，不重复类型逻辑。
_HELPER_DEPS: dict[str, tuple[str, ...]] = {
    "readStringPresent": ("readStringOrNull",),
    "readIntPresent": ("readIntOrNull",),
    "readDoublePresent": ("readDoubleOrNull",),
    "readBoolPresent": ("readBoolOrNull",),
    "readBytesPresent": ("readBytesOrNull",),
    "readObjectPresent": ("readObjectOrNull",),
    "readEnumPresent": ("readEnumOrNull",),
    "readListPresent": ("readListOrNull",),
}

#: 助手源码自身需要的 dart: 库；渲染文件时并入导入。
_HELPER_LIBS: dict[str, tuple[str, ...]] = {
    "readBytes": ("dart:convert", "dart:typed_data"),
    "readBytesOrNull": ("dart:convert", "dart:typed_data"),
    "asBytes": ("dart:convert", "dart:typed_data"),
}

