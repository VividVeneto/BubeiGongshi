"""CORE-67 阶段1：dto_emit 单元测试（只用 CORE-100 类型图替身，不读 schema 原文）。"""

from __future__ import annotations

import builtins
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dto_emit
import dto_schema as ds

#: 仓库根；Dart 运行期用例的临时区落在 build/ 下（build/ 不入库）。
REPO = Path(__file__).resolve().parent.parent.parent
WORK = REPO / "build" / "dto-test"


def ref(source: str, pointer: str) -> ds.SchemaRef:
    """图边：<schema 文件>#<Pointer>。"""
    return ds.SchemaRef("%s#%s" % (source, pointer))


def string_node(source, pointer, *, title=None, fmt=None, enum=None, nullable=False):
    """string 节点；fmt/enum 决定生成的 Dart 类型与实际读器。"""
    values = None
    if enum is not None:
        values = tuple(ds.SchemaScalar(kind="string", value=item) for item in enum)
    return ds.SchemaNode(ref=ref(source, pointer), title=title, nullable=nullable,
                         kind="string", enum_values=values,
                         limits=ds.SchemaLimits(format=fmt))


def int_node(source, pointer, *, title=None, fmt=None, nullable=False):
    """integer 节点（int64 也是 integer + format）。"""
    return ds.SchemaNode(ref=ref(source, pointer), title=title, nullable=nullable,
                         kind="integer", limits=ds.SchemaLimits(format=fmt))


def number_node(source, pointer, *, title=None, nullable=False):
    """number 节点。"""
    return ds.SchemaNode(ref=ref(source, pointer), title=title, nullable=nullable,
                         kind="number")


def bool_node(source, pointer, *, title=None, nullable=False):
    """boolean 节点。"""
    return ds.SchemaNode(ref=ref(source, pointer), title=title, nullable=nullable,
                         kind="boolean")


def array_node(source, pointer, item, *, title=None, nullable=False):
    """array 节点。"""
    return ds.SchemaNode(ref=ref(source, pointer), title=title, nullable=nullable,
                         kind="array", item=item)


def object_node(source, pointer, title, fields, *, nullable=False):
    """object 节点；fields 是 (wire, dart, SchemaRef, required) 四元组。"""
    node_fields = tuple(
        ds.SchemaField(wire_name=wire, dart_name=dart, value=value, required=required)
        for wire, dart, value, required in fields)
    return ds.SchemaNode(ref=ref(source, pointer), title=title, nullable=nullable,
                         kind="object", fields=node_fields)


def ref_node(source, pointer, target, *, title=None):
    """ref 别名节点。"""
    return ds.SchemaNode(ref=ref(source, pointer), title=title, nullable=False,
                         kind="ref", target=target)


def shape_node(source, pointer, kind, *, title=None):
    """阶段1 不支持的形状：union/tuple/map。"""
    return ds.SchemaNode(ref=ref(source, pointer), title=title, nullable=False, kind=kind)


def op_node(name, request, ok, *, schema=None, sensitive=(), stage="S0"):
    """一个 ready op。"""
    source = schema or (name.split(".", 1)[0] + ".schema.json")
    return ds.ReadySchemaOp(op=name, owner="CORE-67", stage=stage, scope="none",
                            mode="call", schema=source, request=request, ok=ok,
                            error_codes=(), sensitive_paths=tuple(sensitive),
                            reads_engine_snapshot=False)


def pending_op(name, *, reason="等待字段设计闭合", stage="S4"):
    """一个 pending op。"""
    return ds.PendingSchemaOp(op=name, owner="CORE-67", stage=stage, scope="none",
                              mode=None, schema=None, blocked_reason=reason)


class Graph:
    """手搭类型图，包成与 CORE-100 同形的只读 SchemaBundle。"""

    def __init__(self):
        self.nodes: list[ds.SchemaNode] = []

    def add(self, node):
        """登记一个节点并原样返回。"""
        self.nodes.append(node)
        return node

    def bundle(self, *ops, pending=(), valid=True, diagnostics=()):
        """打包成替身 bundle（_index 与 SchemaBundle.node 一致）。"""
        index = {node.ref.id: node for node in self.nodes}
        return ds.SchemaBundle(
            valid=valid, ready=tuple(ops), pending=tuple(pending),
            nodes=tuple(self.nodes),
            named=tuple(node.ref for node in self.nodes if node.title is not None),
            diagnostics=tuple(diagnostics), _index=index)


def emit(bundle, manifest="fixture.manifest.json"):
    """跑一次生成，返回 (result, {路径: 文本})。"""
    result = dto_emit.emit(bundle, manifest)
    return result, {item.path: item.text for item in result.files}


def echo_graph():
    """一个含常见形状的 fixture 图：request{text} → ok{echo,count,ratio,flag,amount,level,tags,db_key,note}。"""
    graph = Graph()
    src = "fixture-echo.schema.json"
    ok_fields = [
        ("echo", "echo", ref(src, "/$defs/ok/properties/echo"), True),
        ("count", "count", ref(src, "/$defs/ok/properties/count"), True),
        ("ratio", "ratio", ref(src, "/$defs/ok/properties/ratio"), True),
        ("flag", "flag", ref(src, "/$defs/ok/properties/flag"), True),
        ("amount", "amount", ref(src, "/$defs/ok/properties/amount"), True),
        ("level", "level", ref(src, "/$defs/ok/properties/level"), True),
        ("tags", "tags", ref(src, "/$defs/ok/properties/tags"), True),
        ("db_key", "dbKey", ref(src, "/$defs/ok/properties/db_key"), True),
    ]
    graph.add(object_node(src, "/$defs/request", "FixtureEchoRequest",
                          [("text", "text", ref(src, "/$defs/request/properties/text"), True)]))
    graph.add(object_node(src, "/$defs/ok", "FixtureEchoOk", ok_fields))
    graph.add(string_node(src, "/$defs/request/properties/text"))
    graph.add(string_node(src, "/$defs/ok/properties/echo"))
    graph.add(int_node(src, "/$defs/ok/properties/count", fmt="int64"))
    graph.add(number_node(src, "/$defs/ok/properties/ratio"))
    graph.add(bool_node(src, "/$defs/ok/properties/flag"))
    graph.add(string_node(src, "/$defs/ok/properties/amount", fmt="decimal"))
    graph.add(string_node(src, "/$defs/ok/properties/level", enum=("debug", "info", "warn")))
    graph.add(array_node(src, "/$defs/ok/properties/tags",
                         ref(src, "/$defs/ok/properties/tags/items")))
    graph.add(string_node(src, "/$defs/ok/properties/tags/items"))
    graph.add(string_node(src, "/$defs/ok/properties/db_key", fmt="base64"))
    request = ref(src, "/$defs/request")
    ok = ref(src, "/$defs/ok")
    return graph, request, ok



class TestHeader(unittest.TestCase):
    """验收：固定头、来源与 generator 常量、无时间戳、字节确定性。"""

    def setUp(self):
        self.graph, self.request, self.ok = echo_graph()
        self.result, self.files = emit(self.graph.bundle(
            op_node("fixture.echo", self.request, self.ok)))
        self.text = self.files["fixture.g.dart"]

    def test_header_three_lines(self):
        """头三行：GENERATED 标记、generator 常量、manifest 与 schema 来源。"""
        lines = self.text.splitlines()
        self.assertEqual(lines[0], "// GENERATED CODE - DO NOT MODIFY BY HAND.")
        self.assertEqual(lines[1], "// generator: CORE-67 v1")
        self.assertIn("manifest=fixture.manifest.json", lines[2])
        self.assertIn("fixture-echo.schema.json", lines[2])

    def test_no_timestamp_in_output(self):
        """输出不含日期/时间戳，重复运行逐字节相同。"""
        self.assertNotRegex(self.text, r"\d{4}-\d{2}-\d{2}")
        self.assertNotIn("DateTime.now", self.text)
        again, files = emit(self.graph.bundle(
            op_node("fixture.echo", self.request, self.ok)))
        self.assertEqual(dict(self.files), files)

    def test_format_off_directive(self):
        """生成物整体关闭 dart format，保持生成器排版稳定。"""
        self.assertEqual(self.text.splitlines()[3], "// dart format off")

    def test_has_generated_header_detects_only_generated(self):
        """has_generated_header 只看头两行，不误判普通 Dart 文件。"""
        self.assertTrue(dto_emit.has_generated_header(self.text))
        self.assertFalse(dto_emit.has_generated_header("// hand written\nclass A {}"))


class TestCodec(unittest.TestCase):
    """验收：数值映射与严格 codec 边界（阶段1 的形状）。"""

    def setUp(self):
        graph, request, ok = echo_graph()
        self.text = emit(graph.bundle(op_node("fixture.echo", request, ok)))[1]["fixture.g.dart"]

    def test_scalar_type_mapping(self):
        """int64→int、decimal→String、number→double、base64→Uint8List、array→List。"""
        self.assertIn("final int count;", self.text)
        self.assertIn("final String amount;", self.text)
        self.assertIn("final double ratio;", self.text)
        self.assertIn("final bool flag;", self.text)
        self.assertIn("final List<String> tags;", self.text)
        self.assertIn("final Uint8List dbKey;", self.text)

    def test_wide_numbers_stay_text(self):
        """decimal/uint64/int128 走 readString，绝不经过 double 往返。"""
        self.assertIn("amount: readString(json, 'amount')", self.text)
        self.assertNotIn("readDouble(json, 'amount')", self.text)
        self.assertNotIn("double.parse", self.text)

    def test_readers_are_strict(self):
        """必填缺失/类型不符抛 FormatException；数组为不可修改视图。"""
        self.assertIn("if (value is String) return value;", self.text)
        self.assertIn("throw FormatException('字段 ' + key + ' 应为 string');", self.text)
        self.assertIn("List<T>.unmodifiable(value.map<T>(decode))", self.text)

    def test_non_finite_number_rejected(self):
        """number 读器拒绝非有限值（绕过 jsonDecode 直接构造 Map 时也拒绝）。"""
        self.assertIn("if (value is double && value.isFinite) return value;", self.text)
        self.assertIn("double readDouble(Map<String, Object?> json, String key) {", self.text)

    def test_unknown_enum_wire_throws(self):
        """未知 enum wire 取值抛 FormatException，并带 byWire 索引。"""
        self.assertIn("enum FixtureEchoOkLevel {", self.text)
        self.assertIn("debug('debug'),", self.text)
        self.assertIn("throw FormatException('未知 FixtureEchoOkLevel wire 取值: ", self.text)
        self.assertIn("static const Map<String, FixtureEchoOkLevel> byWire", self.text)

    def test_enum_tojson_writes_wire_value(self):
        """enum 字段按 wire 文本写出。"""
        self.assertIn("'level': level.wire,", self.text)
        self.assertIn("level: readEnum(json, 'level', FixtureEchoOkLevel.fromWire)", self.text)

    def test_base64_encoded_on_write(self):
        """base64 字段读成字节、写成 base64 文本。"""
        self.assertIn("dbKey: readBytes(json, 'db_key')", self.text)
        self.assertIn("'db_key': base64Encode(dbKey),", self.text)
        self.assertIn("import 'dart:convert';", self.text)

    def test_from_json_ignores_unknown_keys(self):
        """fromJson 只按键取值，不遍历 map，未知键自然被忽略。"""
        self.assertNotIn("json.keys", self.text)
        self.assertNotIn("json.entries", self.text)

    def test_to_json_writes_declared_fields_only(self):
        """toJson 的键集合 = 声明字段，顺序 = 声明顺序（卡未要求排序）。"""
        body = self.text.split("Map<String, Object?> toJson() {")[1].split("  }")[0]
        keys = re.findall(r"'([^']+)':", body)
        self.assertEqual(keys, [
            "echo", "count", "ratio", "flag", "amount", "level", "tags", "db_key"])

    def test_uuid_and_date_time_are_string(self):
        """uuid/date-time → String，读器为 readString。"""
        graph = Graph()
        src = "meta.schema.json"
        graph.add(object_node(src, "/$defs/ok", "MetaOk", [
            ("id", "id", ref(src, "/$defs/ok/properties/id"), True),
            ("at", "at", ref(src, "/$defs/ok/properties/at"), True),
        ]))
        graph.add(string_node(src, "/$defs/ok/properties/id", fmt="uuid"))
        graph.add(string_node(src, "/$defs/ok/properties/at", fmt="date-time"))
        graph.add(object_node(src, "/$defs/request", "MetaRequest", []))
        text = emit(graph.bundle(op_node("meta.get", ref(src, "/$defs/request"),
                                         ref(src, "/$defs/ok"))))[1]["meta.g.dart"]
        self.assertIn("final String id;", text)
        self.assertIn("final String at;", text)
        self.assertIn("id: readString(json, 'id')", text)


class TestNaming(unittest.TestCase):
    """验收 4 的阶段1 部分：命名规则①②③⑥的纯函数与内联 enum 名。"""

    def test_title_to_pascal_case(self):
        """规则①：title → PascalCase，不加前后缀。"""
        self.assertEqual(dto_emit.type_name_for("draw_cmd"), "DrawCmd")
        self.assertEqual(dto_emit.type_name_for("FormulaNode"), "FormulaNode")

    def test_core_type_collision_appends_value(self):
        """规则⑥：撞 Dart 核心类型或保留字时追加 Value。"""
        self.assertEqual(dto_emit.type_name_for("String"), "StringValue")
        self.assertEqual(dto_emit.type_name_for("object"), "ObjectValue")

    def test_member_names_are_lower_camel(self):
        """规则②：Dart 字段名 lowerCamelCase，非法/保留名追加 Value。"""
        self.assertEqual(dto_emit.camel("db_key"), "dbKey")
        self.assertEqual(dto_emit.camel("needs_confirm"), "needsConfirm")
        self.assertEqual(dto_emit.camel("default"), "defaultValue")

    def test_enum_member_names(self):
        """wire 取值 → 合法且不撞 Enum 自带成员的成员名。"""
        self.assertEqual(dto_emit.enum_member_for("move-to"), "moveTo")
        self.assertEqual(dto_emit.enum_member_for("info"), "info")
        self.assertEqual(dto_emit.enum_member_for("name"), "nameValue")


class TestImmutability(unittest.TestCase):
    """验收：不可变值对象（const 构造、final 字段、脱敏 toString）。"""

    def setUp(self):
        graph, request, ok = echo_graph()
        self.text = emit(graph.bundle(
            op_node("fixture.echo", request, ok,
                    sensitive=("/ok/db_key",))))[1]["fixture.g.dart"]

    def test_final_class_with_const_constructor(self):
        """类声明为 final class，构造函数是 const。"""
        self.assertIn("final class FixtureEchoOk {", self.text)
        self.assertIn("const FixtureEchoOk({", self.text)

    def test_all_fields_are_final(self):
        """类体内字段声明一律 final（无 setter、无可变字段）。"""
        bodies = re.findall(r"(?ms)^final class \w+ \{\n(.*?)^\}$", self.text)
        self.assertTrue(bodies, "未找到 final class 类体")
        fields = [
            line
            for body in bodies
            for line in body.splitlines()
            if re.match(r"^  [A-Za-z_][A-Za-z0-9_<>,? ]* [a-zA-Z_][A-Za-z0-9_]*;$", line)
        ]
        self.assertTrue(fields, "类体内未找到字段声明")
        for line in fields:
            self.assertTrue(line.startswith("  final "), line)
        self.assertNotRegex(self.text, r"^\s+set ")

    def test_sensitive_field_redacted_in_to_string(self):
        """sensitive_paths 命中字段在 toString 输出 <redacted>，但仍参与 toJson。"""
        line = [item for item in self.text.splitlines() if "return 'FixtureEchoOk(" in item][0]
        self.assertIn("dbKey: <redacted>", line)
        self.assertNotIn("dbKey: " + dto_emit._DOLLAR + "dbKey", line)
        self.assertIn("'db_key': base64Encode(dbKey),", self.text)


def nullable_graph():
    """required 与 nullable 的四种组合 + 阶段1 各形状的可空变体（卡 :38）。"""
    graph = Graph()
    src = "fixture-nullable.schema.json"
    ok_fields = [
        ("note", "note", ref(src, "/$defs/ok/properties/note"), True),
        ("opt_note", "optNote", ref(src, "/$defs/ok/properties/opt_note"), False),
        ("plain", "plain", ref(src, "/$defs/ok/properties/plain"), True),
        ("opt_plain", "optPlain", ref(src, "/$defs/ok/properties/opt_plain"), False),
        ("meta", "meta", ref(src, "/$defs/ok/properties/meta"), True),
        ("opt_meta", "optMeta", ref(src, "/$defs/ok/properties/opt_meta"), False),
        ("tags", "tags", ref(src, "/$defs/ok/properties/tags"), True),
        ("opt_tag_list", "optTagList", ref(src, "/$defs/ok/properties/opt_tag_list"), False),
        ("blob", "blob", ref(src, "/$defs/ok/properties/blob"), True),
        ("level", "level", ref(src, "/$defs/ok/properties/level"), True),
        ("count", "count", ref(src, "/$defs/ok/properties/count"), True),
        ("ratio", "ratio", ref(src, "/$defs/ok/properties/ratio"), True),
        ("flag", "flag", ref(src, "/$defs/ok/properties/flag"), True),
    ]
    graph.add(object_node(src, "/$defs/request", "NullableRequest", [
        ("text", "text", ref(src, "/$defs/request/properties/text"), True)]))
    graph.add(string_node(src, "/$defs/request/properties/text"))
    graph.add(object_node(src, "/$defs/ok", "NullableOk", ok_fields))
    graph.add(string_node(src, "/$defs/ok/properties/note", nullable=True))
    graph.add(string_node(src, "/$defs/ok/properties/opt_note", nullable=True))
    graph.add(string_node(src, "/$defs/ok/properties/plain"))
    graph.add(string_node(src, "/$defs/ok/properties/opt_plain"))
    graph.add(object_node(src, "/$defs/ok/properties/meta", "NullableMeta", [
        ("id", "id", ref(src, "/$defs/ok/properties/meta/properties/id"), True)],
        nullable=True))
    graph.add(string_node(src, "/$defs/ok/properties/meta/properties/id"))
    graph.add(object_node(src, "/$defs/ok/properties/opt_meta", "NullableOptMeta", [
        ("id", "id", ref(src, "/$defs/ok/properties/opt_meta/properties/id"), True)],
        nullable=True))
    graph.add(string_node(src, "/$defs/ok/properties/opt_meta/properties/id"))
    graph.add(array_node(src, "/$defs/ok/properties/tags",
                         ref(src, "/$defs/ok/properties/tags/items"), nullable=True))
    graph.add(string_node(src, "/$defs/ok/properties/tags/items"))
    graph.add(array_node(src, "/$defs/ok/properties/opt_tag_list",
                         ref(src, "/$defs/ok/properties/opt_tag_list/items")))
    graph.add(string_node(src, "/$defs/ok/properties/opt_tag_list/items"))
    graph.add(string_node(src, "/$defs/ok/properties/blob", fmt="base64", nullable=True))
    graph.add(string_node(src, "/$defs/ok/properties/level", enum=("off", "on"),
                          nullable=True))
    graph.add(int_node(src, "/$defs/ok/properties/count", fmt="int64", nullable=True))
    graph.add(number_node(src, "/$defs/ok/properties/ratio", nullable=True))
    graph.add(bool_node(src, "/$defs/ok/properties/flag", nullable=True))
    return graph, ref(src, "/$defs/request"), ref(src, "/$defs/ok")


def dart_exe() -> str | None:
    """找 Dart SDK：优先 sdk 的 dart.exe，其次 Flutter bin 下的 dart 再定位 cache。"""
    exe = shutil.which("dart.exe")
    if exe:
        return exe
    found = shutil.which("dart")
    if found is None:
        return None
    candidate = Path(found).resolve().parent / "cache" / "dart-sdk" / "bin" / "dart.exe"
    return str(candidate) if candidate.is_file() else found


#: Dart 探针：直接运行生成物，验证 required/nullable 的存在性与类型两条轴。
_PROBE = """import 'fixture.g.dart';

Map<String, Object?> base() {
  return <String, Object?>{
    'note': 'n',
    'plain': 'p',
    'meta': null,
    'tags': null,
    'blob': null,
    'level': null,
    'count': null,
    'ratio': null,
    'flag': null,
  };
}

void expectFormatException(void Function() body, String label) {
  try {
    body();
  } on FormatException {
    print('THROW ' + label);
    return;
  }
  throw StateError(label + ' 没有抛 FormatException');
}

void main() {
  expectFormatException(
      () => NullableOk.fromJson(base()..remove('note')), 'note');
  final NullableOk withNull = NullableOk.fromJson(base()..['note'] = null);
  if (withNull.note != null) {
    throw StateError('显式 null 应读成 null');
  }
  final Map<String, Object?> written = withNull.toJson();
  if (!written.containsKey('note') || written['note'] != null) {
    throw StateError('toJson 必须写出 note 键且值为 null');
  }
  if (withNull.optNote != null || withNull.optPlain != null) {
    throw StateError('未必填字段缺键应为 null');
  }
  expectFormatException(
      () => NullableOk.fromJson(base()..remove('plain')), 'plain');
  expectFormatException(
      () => NullableOk.fromJson(base()..remove('meta')), 'meta');
  expectFormatException(
      () => NullableOk.fromJson(base()..remove('tags')), 'tags');
  expectFormatException(
      () => NullableOk.fromJson(base()..remove('blob')), 'blob');
  expectFormatException(
      () => NullableOk.fromJson(base()..remove('level')), 'level');
  expectFormatException(
      () => NullableOk.fromJson(base()..remove('count')), 'count');
  expectFormatException(
      () => NullableOk.fromJson(base()..remove('ratio')), 'ratio');
  expectFormatException(
      () => NullableOk.fromJson(base()..remove('flag')), 'flag');

  final NullableOk typed = NullableOk.fromJson(base()
    ..['meta'] = <String, Object?>{'id': 'm1'}
    ..['tags'] = <Object?>['a', 'b']
    ..['blob'] = 'AAAA'
    ..['level'] = 'on'
    ..['count'] = 7
    ..['ratio'] = 1
    ..['flag'] = true);
  if (typed.meta == null || typed.meta!.id != 'm1') {
    throw StateError('可空对象解码失败');
  }
  if (typed.tags == null || typed.tags!.length != 2) {
    throw StateError('可空数组解码失败');
  }
  try {
    typed.tags!.add('c');
    throw StateError('tags 应为不可修改视图');
  } on UnsupportedError {
    print('THROW tags unmodifiable');
  }
  if (typed.blob == null || typed.blob!.length != 3) {
    throw StateError('可空 base64 解码失败');
  }
  if (typed.level != NullableOkLevel.onValue) {
    throw StateError('可空 enum 解码失败');
  }
  if (typed.count != 7 || typed.ratio != 1.0 || typed.flag != true) {
    throw StateError('可空数值解码失败');
  }
  final Map<String, Object?> typedJson = typed.toJson();
  if (typedJson['meta'] == null || typedJson['tags'] == null ||
      typedJson['blob'] != 'AAAA' || typedJson['level'] != 'on') {
    throw StateError('可空字段编码失败');
  }
  print('OK all');
}
"""


class TestRequiredNullable(unittest.TestCase):
    """卡 :38：required 与 nullable 独立；required+nullable 必须出现但可为 null。"""

    def setUp(self):
        graph, request, ok = nullable_graph()
        result, files = emit(graph.bundle(op_node("fixture.nullable", request, ok)))
        self.assertFalse(result.refused)
        self.text = files["fixture.g.dart"]

    def test_required_nullable_constructor_parameter_is_required(self):
        """required 且 nullable：构造参数仍带 required（字段可出现但不可省略）。"""
        self.assertIn("    required this.note,", self.text)
        self.assertIn("    required this.meta,", self.text)
        self.assertIn("    required this.tags,", self.text)
        self.assertIn("    this.optNote,", self.text)
        self.assertIn("    this.optMeta,", self.text)
        self.assertIn("    this.optPlain,", self.text)

    def test_required_nullable_type_keeps_question_mark(self):
        """可空类型照旧加 ?：required+nullable 与非 required 都是可空 Dart 类型。"""
        self.assertIn("  final String? note;", self.text)
        self.assertIn("  final String plain;", self.text)
        self.assertIn("  final String? optPlain;", self.text)
        self.assertIn("  final NullableMeta? meta;", self.text)
        self.assertIn("  final List<String>? tags;", self.text)
        self.assertIn("  final Uint8List? blob;", self.text)
        self.assertIn("  final int? count;", self.text)
        self.assertIn("  final double? ratio;", self.text)
        self.assertIn("  final bool? flag;", self.text)

    def test_required_nullable_readers_require_the_key(self):
        """required+nullable 的读器是 presence 版：键必须出现、值可为 null。"""
        self.assertIn("note: readStringPresent(json, 'note'),", self.text)
        self.assertIn("meta: readObjectPresent(json, 'meta', NullableMeta.fromJson),",
                      self.text)
        self.assertIn("tags: readListPresent(json, 'tags', asString),", self.text)
        self.assertIn("blob: readBytesPresent(json, 'blob'),", self.text)
        self.assertIn("level: readEnumPresent(json, 'level', NullableOkLevel.fromWire),",
                      self.text)
        self.assertIn("count: readIntPresent(json, 'count'),", self.text)
        self.assertIn("ratio: readDoublePresent(json, 'ratio'),", self.text)
        self.assertIn("flag: readBoolPresent(json, 'flag'),", self.text)
        self.assertNotIn("readStringOrNull(json, 'note')", self.text)

    def test_required_non_nullable_and_optional_readers_unchanged(self):
        """非 nullable 仍严格、非 required 仍缺键即 null（阶段1 既有形状无回归）。"""
        self.assertIn("plain: readString(json, 'plain'),", self.text)
        self.assertIn("optNote: readStringOrNull(json, 'opt_note'),", self.text)
        self.assertIn("optPlain: readStringOrNull(json, 'opt_plain'),", self.text)
        self.assertIn("optMeta: readObjectOrNull(json, 'opt_meta', NullableOptMeta.fromJson),",
                      self.text)
        self.assertIn("optTagList: readListOrNull(json, 'opt_tag_list', asString),",
                      self.text)

    def test_present_helpers_check_key_presence(self):
        """presence 读器先查 containsKey 再交给可空读器，缺键抛 FormatException。"""
        self.assertEqual(self.text.count("if (!json.containsKey(key)) {"), 8)
        self.assertIn("throw FormatException('缺少必填字段 ' + key);", self.text)
        for helper in ("readObjectPresent", "readEnumPresent"):
            self.assertIn("T? " + helper + "<T>(", self.text)
        self.assertIn("List<T>? readListPresent<T>(", self.text)
        for helper, kind in (("readStringPresent", "String?"),
                             ("readIntPresent", "int?"),
                             ("readDoublePresent", "double?"),
                             ("readBoolPresent", "bool?"),
                             ("readBytesPresent", "Uint8List?")):
            self.assertIn("%s %s(Map<String, Object?> json, String key) {" % (kind, helper),
                          self.text)

    def test_nullable_fields_still_encode_null(self):
        """可空字段写回 null：对象用 ?.、数组/base64 用 null 分支、标量直写。"""
        self.assertIn("'note': note,", self.text)
        self.assertIn("'meta': meta?.toJson(),", self.text)
        self.assertIn("'tags': tags,", self.text)
        self.assertIn("'blob': blob == null ? null : base64Encode(blob!),", self.text)
        self.assertIn("'level': level?.wire,", self.text)


class TestGeneratedRuntime(unittest.TestCase):
    """把生成物交给真正的 Dart 运行：缺键/显式 null/可选/对象/数组的行为边界。"""

    @unittest.skipUnless(dart_exe(), "需要 Dart SDK（随 app/.flutter-version 的 Flutter）")
    def test_dart_runtime_required_nullable_semantics(self):
        """缺 required+nullable 键抛 FormatException，显式 null 通过；可选仍为 null。"""
        graph, request, ok = nullable_graph()
        files = emit(graph.bundle(op_node("fixture.nullable", request, ok)))[1]
        WORK.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="dart-runtime-", dir=str(WORK)))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "fixture.g.dart").write_text(files["fixture.g.dart"], encoding="utf-8")
        (root / "probe.dart").write_text(_PROBE, encoding="utf-8")
        done = subprocess.run([dart_exe(), "probe.dart"], cwd=str(root),
                              capture_output=True, text=True, encoding="utf-8",
                              timeout=180)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("OK all", done.stdout)
        self.assertIn("THROW note", done.stdout)
