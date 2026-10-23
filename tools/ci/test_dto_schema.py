#!/usr/bin/env python3
"""CORE-100 验收测试：dto_schema 的类型图、阶段门禁与 invalid 策略。

每条验收至少一条测试；测试只用标准库 unittest（本机无 pytest）。
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import json
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dto_schema as ds

REPO = Path(__file__).resolve().parents[2]
DTO = REPO / "contracts" / "dto"
ECHO = "echo.schema.json"
_DEL = object()


def echo_schema(extra_ok=None, request=None, ok=None, examples=None):
    """最小 S0 自包含 fixture（与 CORE-67 fixture-echo.schema.json 同形）。"""
    doc = {
        "$schema": ds.DIALECT,
        "title": "FixtureEchoSchema",
        "$defs": {
            "request": request if request is not None else {
                "title": "FixtureEchoRequest",
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
            "ok": ok if ok is not None else {
                "title": "FixtureEchoOk",
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
        },
        "examples": examples if examples is not None else [
            {"request": {"text": "hi"}, "ok": {"text": "hi"}},
        ],
    }
    if extra_ok:
        doc["$defs"]["ok"]["properties"].update(extra_ok)
    return doc


def echo_entry(**over):
    """卡里冻结形状的最小 ready 条目。"""
    entry = {
        "op": "fixture.echo",
        "owner": "CORE-67",
        "stage": "S0",
        "status": "ready",
        "mode": "call",
        "scope": "none",
        "schema": ECHO,
        "error_codes": [],
        "sensitive_paths": [],
        "reads_engine_snapshot": False,
    }
    for key, value in over.items():
        if value is _DEL:
            entry.pop(key, None)
        else:
            entry[key] = value
    return entry


def pending_entry(**over):
    entry = {
        "op": "fixture.pending_echo",
        "owner": "CORE-67",
        "stage": "S4",
        "status": "pending",
        "mode": None,
        "scope": "none",
        "schema": None,
        "error_codes": [],
        "sensitive_paths": [],
        "blocked_reason": "等待字段设计闭合",
    }
    for key, value in over.items():
        if value is _DEL:
            entry.pop(key, None)
        else:
            entry[key] = value
    return entry


class Base(unittest.TestCase):
    """临时目录里的最小 S0 fixture。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, payload):
        path = self.dir / name
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def compile(self, entries, schemas=None, raw_manifest=None, **kw):
        for name, payload in (schemas or {ECHO: echo_schema()}).items():
            self.write(name, payload)
        if raw_manifest is not None:
            path = self.write("manifest.json", raw_manifest)
        else:
            path = self.write("manifest.json", {"version": 1, "ops": entries})
        return ds.compile_manifest(path, **kw)

    def codes(self, bundle):
        return [item.code for item in bundle.diagnostics if item.severity == "error"]

    def info_codes(self, bundle):
        return [item.code for item in bundle.diagnostics if item.severity == "info"]

    def assert_invalid(self, bundle, code):
        self.assertFalse(bundle.valid)
        self.assertIn(code, self.codes(bundle))
        self.assertEqual(bundle.ready, ())
        self.assertEqual(bundle.nodes, ())
        self.assertEqual(bundle.named, ())


class ManifestAndFixture(Base):
    """验收 1/8：最小 fixture 端到端与只读返回协议。"""

    def test_a01_fixture_compiles_to_typed_bundle(self):
        bundle = self.compile([echo_entry()])
        self.assertTrue(bundle.valid)
        self.assertEqual(len(bundle.ready), 1)
        op = bundle.ready[0]
        self.assertEqual(op.op, "fixture.echo")
        self.assertEqual(op.error_codes, ())
        self.assertEqual(op.sensitive_paths, ())
        self.assertFalse(op.reads_engine_snapshot)
        request = bundle.node(op.request)
        ok = bundle.node(op.ok)
        self.assertEqual((request.kind, ok.kind), ("object", "object"))
        self.assertEqual(request.title, "FixtureEchoRequest")
        self.assertEqual(ok.title, "FixtureEchoOk")
        field = request.fields[0]
        self.assertEqual(field.wire_name, "text")
        self.assertEqual(field.dart_name, "text")
        self.assertTrue(field.required)
        leaf = bundle.node(field.value)
        self.assertEqual((leaf.kind, leaf.nullable), ("string", False))
        self.assertEqual(leaf.limits, ds.SchemaLimits())

    def test_a08_fixture_only_needs_manifest_and_schema(self):
        # 无 SADD 目录、无其它产物时同一清单给出同一判定。
        self.write(ECHO, echo_schema())
        path = self.write("manifest.json", {"version": 1, "ops": [echo_entry()]})
        first = ds.compile_manifest(path)
        second = ds.compile_manifest(path)
        self.assertTrue(first.valid)
        self.assertEqual(first.nodes, second.nodes)
        self.assertEqual(first.named, second.named)

    def test_a08_bundle_and_nodes_are_read_only(self):
        bundle = self.compile([echo_entry()])
        with self.assertRaises(dataclasses.FrozenInstanceError):
            bundle.valid = False
        with self.assertRaises(dataclasses.FrozenInstanceError):
            bundle.nodes[0].kind = "null"
        self.assertIsInstance(bundle.nodes, tuple)
        self.assertIsInstance(bundle.nodes[0].fields, tuple)
        self.assertIsInstance(bundle.nodes[0].limits, ds.SchemaLimits)
        self.assertEqual(bundle.node(bundle.ready[0].request).title, "FixtureEchoRequest")
        with self.assertRaises(KeyError):
            bundle.node(ds.SchemaRef("echo.schema.json#/$defs/missing"))

    def test_a08_node_access_does_not_touch_files(self):
        bundle = self.compile([echo_entry()])
        before = sorted(p.name for p in self.dir.iterdir())
        stamps = {p.name: p.stat().st_mtime_ns for p in self.dir.iterdir()}
        for ref in bundle.named:
            bundle.node(ref)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), before)
        self.assertEqual({p.name: p.stat().st_mtime_ns for p in self.dir.iterdir()}, stamps)

    def test_a02_edges_are_refs_and_graph_is_closed(self):
        bundle = self.compile([echo_entry()])
        known = {node.ref.id for node in bundle.nodes}
        for node in bundle.nodes:
            for field in node.fields:
                self.assertIsInstance(field.value, ds.SchemaRef)
                self.assertIn(field.value.id, known)
            for edge in (node.item, node.target):
                if edge is not None:
                    self.assertIsInstance(edge, ds.SchemaRef)
                    self.assertIn(edge.id, known)
            for edge in node.prefix:
                self.assertIn(edge.id, known)
            for case in node.cases:
                self.assertIn(case.branch.id, known)
            self.assertNotIsInstance(node, tuple)
        for name in ("fields", "prefix", "cases"):
            self.assertIsInstance(getattr(bundle.nodes[0], name), tuple)


class StageGateAndSnapshot(Base):
    """验收 4/5：阶段门禁、引擎快照双向一致与条目键集冻结。"""

    def test_a05_ready_entry_shape_is_frozen(self):
        bundle = self.compile([echo_entry(extra="x")])
        self.assert_invalid(bundle, ds.D_MANIFEST_KEY)

    def test_a05_pending_rejects_ready_only_field(self):
        bundle = self.compile([pending_entry(reads_engine_snapshot=False)])
        self.assert_invalid(bundle, ds.D_MANIFEST_KEY)

    def test_a05_pending_shape_rules(self):
        for over in (
            {"schema": ECHO},
            {"blocked_reason": "   "},
            {"mode": "stream"},
            {"reads_engine_snapshot": False},
        ):
            with self.subTest(over=over):
                bundle = self.compile([pending_entry(**over)])
                self.assertFalse(bundle.valid)
                self.assertTrue(self.codes(bundle))

    def test_a05_bad_identity_fields(self):
        cases = [
            ({"op": "Fixture"}, ds.D_MANIFEST_OP),
            ({"op": "fixture"}, ds.D_MANIFEST_OP),
            ({"owner": "CORE_67"}, ds.D_MANIFEST_OWNER),
            ({"owner": "CORE-"}, ds.D_MANIFEST_OWNER),
            ({"stage": "S8"}, ds.D_MANIFEST_STAGE),
            ({"scope": "global"}, ds.D_MANIFEST_SCOPE),
            ({"mode": "stream"}, ds.D_MANIFEST_MODE),
            ({"status": "draft"}, ds.D_MANIFEST_STATUS),
            ({"schema": "nested/echo.schema.json"}, ds.D_MANIFEST_SCHEMA),
            ({"schema": "missing.schema.json"}, ds.D_MANIFEST_SCHEMA),
            ({"reads_engine_snapshot": _DEL}, ds.D_MANIFEST_SNAPSHOT),
        ]
        for over, code in cases:
            with self.subTest(over=over):
                bundle = self.compile([echo_entry(**over)])
                self.assert_invalid(bundle, code)

    def test_a05_duplicate_and_multi_segment_ops(self):
        bundle = self.compile([echo_entry(), echo_entry()])
        self.assert_invalid(bundle, ds.D_MANIFEST_OP)
        deep = self.compile([echo_entry(op="fixture.echo.reply")])
        self.assertTrue(deep.valid)
        self.assertEqual(deep.ready[0].op, "fixture.echo.reply")

    def test_a05_schema_must_carry_request_ok_examples(self):
        broken = echo_schema()
        del broken["$defs"]["ok"]
        self.assert_invalid(self.compile([echo_entry()], {ECHO: broken}),
                            ds.D_MANIFEST_SCHEMA)
        broken = echo_schema(examples=[])
        self.assert_invalid(self.compile([echo_entry()], {ECHO: broken}),
                            ds.D_MANIFEST_SCHEMA)
        broken = echo_schema(examples=[{"request": {"text": "hi"}}])
        self.assert_invalid(self.compile([echo_entry()], {ECHO: broken}),
                            ds.D_MANIFEST_SCHEMA)

    def test_a04_snapshot_must_match_engine_code(self):
        bundle = self.compile([echo_entry(reads_engine_snapshot=True)])
        self.assert_invalid(bundle, ds.D_MANIFEST_SNAPSHOT)
        bundle = self.compile([echo_entry(error_codes=["ENGINE_UNAVAILABLE"],
                                          reads_engine_snapshot=False)])
        self.assert_invalid(bundle, ds.D_MANIFEST_SNAPSHOT)
        bundle = self.compile([echo_entry(error_codes=["ENGINE_UNAVAILABLE"],
                                          reads_engine_snapshot=True)])
        self.assertTrue(bundle.valid)

    def test_a04_generation_style_edit_stays_valid_here(self):
        # DTO-26 的口径归 DTOcheck；本库只要求双向一致这一机器事实。
        schemas = {"generation.schema.json": echo_schema()}
        first = dict(echo_entry(op="engine.generation", owner="CORE-73", stage="S1",
                               schema="generation.schema.json"))
        self.assertTrue(self.compile([first], schemas).valid)
        flipped = dict(first, reads_engine_snapshot=True,
                       error_codes=["ENGINE_UNAVAILABLE"])
        bundle = self.compile([flipped], schemas)
        self.assertTrue(bundle.valid)
        self.assertTrue(bundle.ready[0].reads_engine_snapshot)

    def test_a04_pending_gate(self):
        early = self.compile([pending_entry(stage="S1")], required_stage="S2")
        self.assert_invalid(early, ds.D_MANIFEST_GATE)
        late = self.compile([pending_entry(stage="S5"), echo_entry()],
                            required_stage="S2")
        self.assertTrue(late.valid)
        self.assertEqual(len(late.pending), 1)
        self.assertIn(ds.D_MANIFEST_SKIP, self.info_codes(late))
        release = self.compile([pending_entry(stage="S5"), echo_entry()], release=True)
        self.assert_invalid(release, ds.D_MANIFEST_GATE)

    def test_a04_no_required_stage_accepts_self_consistent_entries(self):
        bundle = self.compile([pending_entry(), echo_entry()])
        self.assertTrue(bundle.valid)
        self.assertEqual([item.op for item in bundle.pending], ["fixture.pending_echo"])
        self.assertEqual(bundle.ready[0].op, "fixture.echo")


class ErrorCodesAndSensitivePaths(Base):
    """验收 6/7：错误集合结构与敏感 Pointer 双向一致。"""

    def test_a06_error_codes_structure(self):
        cases = [
            ["ZZZ", "AAA"],
            ["AAA", "AAA"],
            [1],
            ["FFI_BAD_ARG"],
        ]
        for codes in cases:
            with self.subTest(codes=codes):
                bundle = self.compile([echo_entry(error_codes=codes)])
                self.assert_invalid(bundle, ds.D_MANIFEST_CODES)

    def test_a06_prefix_is_not_the_criterion(self):
        bundle = self.compile([echo_entry(error_codes=["FFI_LOCAL_ONLY"])])
        self.assertTrue(bundle.valid)
        self.assertEqual(bundle.ready[0].error_codes, ("FFI_LOCAL_ONLY",))

    def test_a06_no_cross_op_comparison(self):
        # 删掉一个业务码不会让本库报错：逐 op 集合归所有者卡镜像与 DTOcheck。
        bundle = self.compile([echo_entry(error_codes=[])])
        self.assertTrue(bundle.valid)

    def test_a07_sensitive_paths_must_be_sorted_pointers(self):
        for paths in (["ok/db_key"], ["/body/b", "/body/a"], ["/body/a", "/body/a"]):
            with self.subTest(paths=paths):
                bundle = self.compile([echo_entry(sensitive_paths=paths)])
                self.assert_invalid(bundle, ds.D_MANIFEST_PATHS)

    def test_a07_sensitive_paths_must_match_schema(self):
        schema = echo_schema(extra_ok={"db_key": {"type": "string", "x-sensitive": True}})
        bundle = self.compile([echo_entry(sensitive_paths=[])], {ECHO: schema})
        self.assert_invalid(bundle, ds.D_MANIFEST_PATHS)
        ok = self.compile([echo_entry(sensitive_paths=["/ok/db_key"])], {ECHO: schema})
        self.assertTrue(ok.valid)
        self.assertEqual(ok.ready[0].sensitive_paths, ("/ok/db_key",))


def rich_schema():
    """覆盖 union 三种判别、nullable、tuple、map、递归与 enum/const 的 ok 结构。"""
    node = {
        "title": "FixtureNode",
        "oneOf": [
            {"type": "object", "properties": {"k": {"const": "leaf"},
                                              "v": {"type": "integer"}},
             "required": ["k", "v"], "additionalProperties": False},
            {"type": "object", "properties": {"k": {"const": "pair"},
                                              "left": {"$ref": "#/$defs/Node"},
                                              "right": {"$ref": "#/$defs/Node"}},
             "required": ["k", "left", "right"], "additionalProperties": False},
        ],
    }
    ok = {
        "title": "FixtureRichOk",
        "type": "object",
        "properties": {
            "node": {"$ref": "#/$defs/Node"},
            "opt": {"oneOf": [{"type": "string"}, {"type": "null"}]},
            "items": {"type": "array", "items": {"type": "integer", "minimum": 0},
                      "minItems": 0, "maxItems": 4},
            "pair": {"type": "array",
                     "prefixItems": [{"type": "integer"}, {"type": "string"}],
                     "items": False, "minItems": 2, "maxItems": 2},
            "args": {"type": "object", "additionalProperties": {"type": "string"}},
            "kind": {"oneOf": [
                {"type": "string", "enum": ["a", "b"]},
                {"type": "object", "properties": {"c": {"type": "boolean"}},
                 "required": ["c"], "additionalProperties": False},
            ]},
            "shape": {"oneOf": [
                {"type": "object", "properties": {"k": {"const": "dot"},
                                                  "r": {"type": "integer"}},
                 "required": ["k", "r"], "additionalProperties": False},
                {"type": "object", "properties": {"k": {"const": "box"},
                                                  "w": {"type": "integer"}},
                 "required": ["k", "w"], "additionalProperties": False},
            ]},
            "nothing": {"const": None},
            "count": {"type": "integer", "minimum": 0, "maximum": 9223372036854776000},
        },
        "required": ["node"],
        "additionalProperties": False,
    }
    return {
        "$schema": ds.DIALECT,
        "title": "FixtureRichSchema",
        "$defs": {
            "request": {"title": "FixtureRichRequest", "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"], "additionalProperties": False},
            "ok": ok,
            "Node": node,
        },
        "examples": [{"request": {"text": "hi"},
                      "ok": {"node": {"k": "leaf", "v": 1}, "opt": None}}],
    }


class SchemaSubset(Base):
    """验收 2/3/10：冻结子集、nullable 归并、互斥判别与节点不变量。"""

    def setUp(self):
        super().setUp()
        self.bundle = self.compile([echo_entry()], {ECHO: rich_schema()})
        self.assertTrue(self.bundle.valid, self.codes(self.bundle))
        self.ok = self.bundle.node(self.bundle.ready[0].ok)

    def field(self, name):
        for field in self.ok.fields:
            if field.wire_name == name:
                return field
        raise AssertionError(name)

    def test_a03_nullable_merge_keeps_payload(self):
        opt = self.bundle.node(self.field("opt").value)
        self.assertEqual(opt.kind, "string")
        self.assertTrue(opt.nullable)
        self.assertEqual(opt.cases, ())
        self.assertIsNone(opt.target)
        self.assertIn(opt.kind, {"string"})

    def test_a10_kinds_are_exclusive(self):
        for node in self.bundle.nodes:
            if node.kind == "object":
                self.assertTrue(node.fields or node.fields == ())
                self.assertIsNone(node.item)
                self.assertEqual((node.prefix, node.cases), ((), ()))
            if node.kind == "map":
                self.assertEqual(node.fields, ())
                self.assertIsNotNone(node.item)
            if node.kind == "array":
                self.assertIsNotNone(node.item)
                self.assertEqual((node.prefix, node.cases), ((), ()))
            if node.kind == "tuple":
                self.assertTrue(node.prefix)
                self.assertEqual((node.item, node.cases), (None, ()))
            if node.kind == "ref":
                self.assertIsNotNone(node.target)
                self.assertEqual((node.fields, node.cases), ((), ()))
            if node.kind in {"string", "integer", "number", "boolean", "null"}:
                self.assertEqual((node.fields, node.cases, node.prefix),
                                 ((), (), ()))
                self.assertIsNone(node.item)

    def test_a10_array_tuple_and_map(self):
        items = self.bundle.node(self.field("items").value)
        self.assertEqual((items.kind, items.limits.min_items, items.limits.max_items),
                         ("array", 0, 4))
        self.assertEqual(self.bundle.node(items.item).limits.minimum, 0)
        pair = self.bundle.node(self.field("pair").value)
        self.assertEqual(pair.kind, "tuple")
        self.assertEqual(len(pair.prefix), 2)
        self.assertEqual([self.bundle.node(p).kind for p in pair.prefix],
                         ["integer", "string"])
        args = self.bundle.node(self.field("args").value)
        self.assertEqual(args.kind, "map")
        self.assertEqual(self.bundle.node(args.item).kind, "string")
        self.assertEqual(args.fields, ())

    def test_a10_required_is_independent_from_nullable(self):
        opt = self.field("opt")
        self.assertFalse(opt.required)
        self.assertTrue(self.bundle.node(opt.value).nullable)
        node = self.field("node")
        self.assertTrue(node.required)
        self.assertFalse(self.bundle.node(node.value).nullable)

    def test_a03_union_matches_all_three_kinds(self):
        shape = self.bundle.node(self.field("shape").value)
        self.assertEqual(shape.kind, "union")
        self.assertEqual([case.match for case in shape.cases],
                         ["field_const", "field_const"])
        self.assertEqual([case.key for case in shape.cases], ["k", "k"])
        self.assertEqual([case.values[0].value for case in shape.cases], ["dot", "box"])
        kind = self.bundle.node(self.field("kind").value)
        self.assertEqual([case.match for case in kind.cases],
                         ["scalar_enum", "external_key"])
        self.assertEqual([v.value for v in kind.cases[0].values], ["a", "b"])
        self.assertEqual(kind.cases[1].key, "c")
        self.assertEqual(kind.cases[1].values, ())

    def test_a03_null_const_is_not_missing_const(self):
        nothing = self.bundle.node(self.field("nothing").value)
        self.assertEqual(nothing.kind, "null")
        self.assertFalse(nothing.nullable)
        self.assertIsNotNone(nothing.const_value)
        self.assertEqual(nothing.const_value.kind, "null")
        text = self.bundle.node(self.field("opt").value)
        self.assertIsNone(text.const_value)
        self.assertIsNone(text.enum_values)

    def test_a03_nullable_rejections(self):
        bad = {
            "both_null": {"oneOf": [{"type": "null"}, {"type": "null"}]},
            "three_way": {"oneOf": [{"type": "string"}, {"type": "null"},
                                    {"type": "integer"}]},
            "nested_union": {"oneOf": [{"oneOf": [{"type": "string"},
                                                  {"type": "integer"}]},
                                       {"type": "null"}]},
        }
        for name, spec in bad.items():
            with self.subTest(case=name):
                schema = echo_schema()
                schema["$defs"]["ok"]["properties"][name] = spec
                bundle = self.compile([echo_entry()], {ECHO: schema})
                self.assertFalse(bundle.valid)
                self.assertIn(ds.D_SCHEMA_NULLABLE, self.codes(bundle))

    def test_a03_union_rejections(self):
        bad = {
            "no_discriminator": {"oneOf": [
                {"type": "object", "properties": {"a": {"type": "integer"}},
                 "required": ["a", "b"], "additionalProperties": False},
                {"type": "object", "properties": {"c": {"type": "integer"}},
                 "required": ["c"], "additionalProperties": False}]},
            "two_scalars": {"oneOf": [{"type": "string", "enum": ["a"]},
                                      {"type": "string", "enum": ["b"]}]},
            "duplicate_value": {"oneOf": [
                {"type": "object", "properties": {"k": {"const": "a"}},
                 "required": ["k"], "additionalProperties": False},
                {"type": "object", "properties": {"k": {"const": "a"}},
                 "required": ["k"], "additionalProperties": False}]},
            "scalar_collides_key": {"oneOf": [
                {"type": "string", "enum": ["vector"]},
                {"type": "object", "properties": {"vector": {"type": "integer"}},
                 "required": ["vector"], "additionalProperties": False}]},
        }
        for name, spec in bad.items():
            with self.subTest(case=name):
                schema = echo_schema()
                schema["$defs"]["ok"]["properties"][name] = spec
                bundle = self.compile([echo_entry()], {ECHO: schema})
                self.assertFalse(bundle.valid)
                self.assertIn(ds.D_SCHEMA_UNION, self.codes(bundle))

    def test_a03_union_non_scalar_enum_values_are_rejected(self):
        bad = {
            "enum_object": {"type": "string", "enum": [{"a": 1}]},
            "enum_array": {"type": "string", "enum": [["a"]]},
        }
        for name, scalar in bad.items():
            with self.subTest(case=name):
                schema = echo_schema()
                schema["$defs"]["ok"]["properties"][name] = {"oneOf": [
                    scalar,
                    {"type": "object",
                     "properties": {"c": {"type": "integer"}},
                     "required": ["c"], "additionalProperties": False},
                ]}
                bundle = self.compile([echo_entry()], {ECHO: schema})
                self.assert_invalid(bundle, ds.D_SCHEMA_UNION)

    def test_a02_recursive_graph_uses_back_edge(self):
        wrapper = self.bundle.node(self.field("node").value)
        self.assertEqual(wrapper.kind, "ref")
        self.assertEqual(wrapper.target.id, "echo.schema.json#/$defs/Node")
        union = self.bundle.node(wrapper.target)
        self.assertEqual(union.kind, "union")
        deeper = []
        for case in union.cases:
            branch = self.bundle.node(case.branch)
            for item in branch.fields:
                deeper.append(self.bundle.node(item.value))
        back = [item for item in deeper if item.kind == "ref"]
        self.assertTrue(back)
        for item in back:
            self.assertEqual(item.target.id, union.ref.id)
        ids = [item.ref.id for item in self.bundle.nodes]
        self.assertEqual(len(ids), len(set(ids)))

    def test_a09_named_is_exactly_titled_nodes(self):
        titled = {item.title for item in self.bundle.nodes if item.title}
        self.assertEqual({ref.id for ref in self.bundle.named},
                         {item.ref.id for item in self.bundle.nodes if item.title})
        names = [item.title for item in self.bundle.nodes if item.title]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names, sorted(names))
        self.assertIn("FixtureRichRequest", titled)
        self.assertIn("FixtureNode", titled)


class SchemaRules(Base):
    """验收 7/11：白名单、format、limits、examples 与 invalid 策略。"""

    def schema_with_ok_props(self, props, examples=None):
        schema = echo_schema()
        schema["$defs"]["ok"]["properties"].update(props)
        if examples is not None:
            schema["examples"] = examples
        return schema

    def bad_schema(self, props, code, examples=None):
        bundle = self.compile([echo_entry()],
                              {ECHO: self.schema_with_ok_props(props, examples)})
        self.assert_invalid(bundle, code)

    def test_a07_unsupported_keyword_is_rejected(self):
        for props in ({"a": {"type": "string", "patternProperties": {}}},
                      {"a": {"type": "string", "minLength": 1, "if": {}}},
                      {"a": {"$ref": "#/$defs/ok", "$comment": "x"}}):
            with self.subTest(props=props):
                self.bad_schema(props, ds.D_SCHEMA_KEYWORD)

    def test_a07_schema_uri_only_at_root(self):
        self.bad_schema({"a": {"type": "string", "$schema": ds.DIALECT}},
                        ds.D_SCHEMA_KEYWORD)
        wrong = echo_schema()
        wrong["$schema"] = "http://json-schema.org/draft-07/schema#"
        self.assert_invalid(self.compile([echo_entry()], {ECHO: wrong}),
                            ds.D_SCHEMA_KEYWORD)

    def test_a07_format_subset(self):
        self.bad_schema({"a": {"type": "string", "format": "email"}},
                        ds.D_SCHEMA_FORMAT)
        self.bad_schema({"a": {"type": "integer", "format": "uuid"}},
                        ds.D_SCHEMA_KEYWORD)

    def test_a07_format_tables(self):
        valid = {"uuid": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
                 "date-time": "2026-10-22T10:00:00Z",
                 "int64": "-9223372036854775808",
                 "uint64": "18446744073709551615",
                 "int128": "-170141183460469231731687303715884105728",
                 "positive-int128": "1",
                 "decimal": "-0.5",
                 "base64": "aGk="}
        broken = {"uuid": "3f2504e0-4f89-11d3-9a0c",
                  "date-time": "2026-13-22T10:00:00Z",
                  "int64": "9223372036854775808",
                  "uint64": "18446744073709551616",
                  "int128": "1.0",
                  "positive-int128": "0",
                  "decimal": "1e5",
                  "base64": "aGk"}
        def wire(name):
            return "f_" + name.replace("-", "_")
        props = {wire(name): {"type": "string", "format": name} for name in valid}
        props_ok = {wire(name): dict(props[wire(name)], default=valid[name])
                    for name in valid}
        self.assertTrue(self.compile([echo_entry()],
                                     {ECHO: self.schema_with_ok_props(props_ok)}).valid)
        for name, value in broken.items():
            with self.subTest(fmt=name):
                props_bad = dict(props)
                props_bad[wire(name)] = dict(props[wire(name)], default=value)
                self.bad_schema(props_bad, ds.D_SCHEMA_EXAMPLE)

    def test_a07_limits_and_pattern(self):
        self.bad_schema({"a": {"type": "integer", "minimum": 5, "maximum": 1}},
                        ds.D_SCHEMA_LIMITS)
        self.bad_schema({"a": {"type": "string", "pattern": "([a-z"}},
                        ds.D_SCHEMA_LIMITS)
        self.bad_schema({"a": {"type": "string", "minLength": 3, "maxLength": 1}},
                        ds.D_SCHEMA_LIMITS)

    def test_a07_maxlength_counts_code_points(self):
        props = {"a": {"type": "string", "maxLength": 3, "default": "公式解"}}
        self.assertTrue(self.compile([echo_entry()],
                                     {ECHO: self.schema_with_ok_props(props)}).valid)
        self.bad_schema({"a": {"type": "string", "maxLength": 1, "default": "公式"}},
                        ds.D_SCHEMA_EXAMPLE)

    def test_a07_typed_map_is_string_only(self):
        self.bad_schema({"a": {"type": "object",
                               "additionalProperties": {"type": "integer"}}},
                        ds.D_SCHEMA_MAP)
        self.bad_schema({"a": {"type": "object",
                               "additionalProperties": {"type": "string"},
                               "required": ["x"]}}, ds.D_SCHEMA_MAP)

    def test_a07_examples_and_default_must_validate(self):
        self.bad_schema({"a": {"type": "integer", "default": "1"}},
                        ds.D_SCHEMA_EXAMPLE)
        self.bad_schema({"a": {"type": "string", "examples": ["ok", 2]}},
                        ds.D_SCHEMA_EXAMPLE)
        self.bad_schema({"a": {"type": "string"}},
                        ds.D_SCHEMA_EXAMPLE,
                        examples=[{"request": {"text": 5}, "ok": {"text": "hi"}}])
        self.bad_schema({"a": {"type": "integer", "minimum": 2}},
                        ds.D_SCHEMA_EXAMPLE,
                        examples=[{"request": {"text": "hi"},
                                   "ok": {"text": "hi", "a": 1}}])

    def test_a09_objects_and_names(self):
        self.bad_schema({"a": {"type": "object",
                               "properties": {"x": {"type": "string"}}}},
                        ds.D_SCHEMA_OBJECT)
        self.bad_schema({"Text": {"type": "string"}}, ds.D_SCHEMA_NAME)
        self.bad_schema({"a": {"type": "object", "properties": {},
                               "required": ["x"],
                               "additionalProperties": False}}, ds.D_SCHEMA_OBJECT)

    def test_a09_arrays_need_items(self):
        self.bad_schema({"a": {"type": "array", "minItems": 0}}, ds.D_SCHEMA_ARRAY)
        self.bad_schema({"a": {"type": "array",
                               "prefixItems": [{"type": "integer"}],
                               "items": {"type": "integer"},
                               "minItems": 1, "maxItems": 1}}, ds.D_SCHEMA_ARRAY)
        self.bad_schema({"a": {"type": "array",
                               "prefixItems": [{"type": "integer"}],
                               "items": False, "minItems": 1, "maxItems": 2}},
                        ds.D_SCHEMA_ARRAY)

    def test_a09_titles_are_unique_and_pascal(self):
        schema = self.schema_with_ok_props(
            {"a": {"title": "FixtureEchoRequest", "type": "string"}})
        self.assert_invalid(self.compile([echo_entry()], {ECHO: schema}),
                            ds.D_SCHEMA_TITLE)
        self.bad_schema({"a": {"title": "lower", "type": "string"}}, ds.D_SCHEMA_TITLE)

    def test_a09_references_must_close(self):
        self.bad_schema({"a": {"$ref": "#/$defs/nope"}}, ds.D_SCHEMA_REF)
        self.bad_schema({"a": {"$ref": "../types.schema.json#/$defs/Uuid"}},
                        ds.D_SCHEMA_REF)
        self.bad_schema({"a": {"$ref": "absent.schema.json#/$defs/X"}},
                        ds.D_SCHEMA_JSON)


class CrossFileExamples(Base):
    """B2：跨文件 $ref 的示例校验必须按需加载且与条目顺序无关。"""

    shared = "shared.schema.json"

    @staticmethod
    def shared_schema(minimum=3):
        return {
            "$schema": ds.DIALECT,
            "title": "FixtureSharedSchema",
            "$defs": {
                "Counted": {
                    "title": "FixtureSharedCounted",
                    "type": "object",
                    "properties": {"n": {"type": "integer", "minimum": minimum}},
                    "required": ["n"],
                    "additionalProperties": False,
                },
            },
        }

    def counted_schema(self, example, prefix=None):
        schema = echo_schema(
            extra_ok={"item": {"$ref": self.shared + "#/$defs/Counted"}},
            examples=[{"request": {"text": "hi"},
                       "ok": {"text": "hi", "item": example}}])
        if prefix is not None:
            schema["title"] = "Fixture" + prefix + "Schema"
            schema["$defs"]["request"]["title"] = "Fixture" + prefix + "Request"
            schema["$defs"]["ok"]["title"] = "Fixture" + prefix + "Ok"
        return schema

    def test_b2_cross_file_example_violation_is_reported(self):
        schema = self.counted_schema({"n": 1})
        bundle = self.compile([echo_entry()],
                              {ECHO: schema, self.shared: self.shared_schema()})
        self.assert_invalid(bundle, ds.D_SCHEMA_EXAMPLE)

    def test_b2_entry_order_does_not_change_example_diagnostics(self):
        one = echo_entry(op="fixture.one", schema="one.schema.json")
        two = echo_entry(op="fixture.two", schema="two.schema.json")
        bad = {self.shared: self.shared_schema(),
               "one.schema.json": self.counted_schema({"n": 3}, "One"),
               "two.schema.json": self.counted_schema({"n": 1}, "Two")}
        forward = self.compile([one, two], bad)
        reverse = self.compile([two, one], bad)
        self.assertFalse(forward.valid)
        self.assertFalse(reverse.valid)
        self.assertEqual(forward.diagnostics, reverse.diagnostics)
        self.assertEqual(self.codes(forward), self.codes(reverse))
        self.assertEqual((forward.ready, forward.nodes, forward.named), ((), (), ()))
        self.assertEqual((reverse.ready, reverse.nodes, reverse.named), ((), (), ()))

        clean = {self.shared: self.shared_schema(),
                 "one.schema.json": self.counted_schema({"n": 3}, "One"),
                 "two.schema.json": self.counted_schema({"n": 4}, "Two")}
        forward = self.compile([one, two], clean)
        reverse = self.compile([two, one], clean)
        self.assertTrue(forward.valid)
        self.assertTrue(reverse.valid)
        self.assertEqual(forward.diagnostics, reverse.diagnostics)
        self.assertEqual(forward.nodes, reverse.nodes)
        self.assertEqual(forward.named, reverse.named)

    def test_b2_missing_ref_pointer_is_reported(self):
        schema = echo_schema(
            extra_ok={"item": {"$ref": self.shared + "#/$defs/Missing"}},
            examples=[{"request": {"text": "hi"},
                       "ok": {"text": "hi", "item": {"n": 4}}}])
        bundle = self.compile([echo_entry()],
                              {ECHO: schema, self.shared: self.shared_schema()})
        self.assert_invalid(bundle, ds.D_SCHEMA_REF)
        self.assertTrue(any(item.source == self.shared
                            and item.pointer == "/$defs/Missing"
                            for item in bundle.diagnostics))

    def test_ref_to_non_object_node_is_diagnosed(self):
        shared = self.shared_schema()
        shared["$defs"]["Scalar"] = "not-a-schema"
        schema = echo_schema(
            extra_ok={"item": {"$ref": self.shared + "#/$defs/Scalar"}},
            examples=[{"request": {"text": "hi"}, "ok": {"text": "hi"}}])
        bundle = self.compile([echo_entry()], {ECHO: schema, self.shared: shared})
        self.assert_invalid(bundle, ds.D_SCHEMA_SHAPE)


REAL = DTO / "manifest.json"
SNAPSHOT_OPS = {
    "calc.evaluate", "calc.solvable_targets", "constants.resolve", "derive.rank",
    "derive.run_plan", "derive.substitute", "engine.check", "notation.bind",
    "notation.display", "notation.profiles", "typeset.glyph_outlines",
    "typeset.layout", "units.compatible", "units.convert",
}


@unittest.skipUnless(REAL.is_file(), "contracts/dto/manifest.json 不在工作树内")
class RealManifest(unittest.TestCase):
    """验收 1/2/3/4/6/9：真实清单上的图、nullable 归并与快照一致性。"""

    @classmethod
    def setUpClass(cls):
        cls.bundle = ds.compile_manifest(REAL)

    def node(self, doc, pointer):
        return self.bundle.node(ds.SchemaRef("%s#%s" % (doc, pointer)))

    def ready(self, op):
        for item in self.bundle.ready:
            if item.op == op:
                return item
        raise AssertionError(op)

    def test_a01_real_manifest_is_valid(self):
        self.assertTrue(self.bundle.valid)
        self.assertEqual(self.bundle.diagnostics, ())
        self.assertEqual(len(self.bundle.ready), 36)
        self.assertEqual(len(self.bundle.pending), 107)
        known = {item.ref.id for item in self.bundle.nodes}
        for item in self.bundle.ready:
            self.assertIn(item.request.id, known)
            self.assertIn(item.ok.id, known)

    def test_a02_ref_wrapper_titles_survive(self):
        for doc, title in (("calc.evaluate.schema.json", "CalcEvaluateOk"),
                           ("engine.check.schema.json", "EngineCheckOk"),
                           ("store.integrity_check.schema.json",
                            "StoreIntegrityCheckOk"),
                           ("typeset.layout.schema.json", "TypesetLayoutOk")):
            with self.subTest(doc=doc):
                ok = self.node(doc, "/$defs/ok")
                self.assertEqual((ok.kind, ok.title), ("ref", title))
                self.assertIsNotNone(ok.target)
        self.assertIn(ds.SchemaRef("calc.evaluate.schema.json#/$defs/ok"),
                      self.bundle.named)

    def test_a03_real_nullable_merges(self):
        for doc, pointer in (
            ("engine.parse.schema.json", "/$defs/ok/properties/ast"),
            ("types.schema.json", "/$defs/MathKind/oneOf/1/properties/vector"),
            ("types.schema.json",
             "/$defs/MathKind/oneOf/2/properties/matrix/prefixItems/0"),
            ("types.schema.json",
             "/$defs/MathKind/oneOf/2/properties/matrix/prefixItems/1"),
        ):
            with self.subTest(pointer=pointer):
                item = self.node(doc, pointer)
                self.assertTrue(item.nullable)
                self.assertNotEqual(item.kind, "union")
                self.assertEqual(item.cases, ())
        ast = self.node("engine.parse.schema.json", "/$defs/ok/properties/ast")
        self.assertEqual(ast.kind, "ref")
        self.assertEqual(ast.target.id, "types.schema.json#/$defs/FormulaNode")
        vector = self.node("types.schema.json",
                           "/$defs/MathKind/oneOf/1/properties/vector")
        self.assertEqual(vector.kind, "integer")
        self.assertEqual((vector.limits.minimum, vector.limits.maximum), (0, 65535))
        kinds = {item.kind for item in self.bundle.nodes}
        self.assertNotIn("union-null", kinds)

    def test_a03_real_unions(self):
        formula = self.node("types.schema.json", "/$defs/FormulaNode")
        self.assertEqual(formula.kind, "union")
        self.assertEqual(len(formula.cases), 14)
        self.assertEqual({case.match for case in formula.cases}, {"field_const"})
        self.assertEqual({case.key for case in formula.cases}, {"k"})
        self.assertEqual([case.values[0].value for case in formula.cases],
                         ["symbol", "number", "unit", "binary", "unary", "function",
                          "derivative", "integral", "sum_or_limit", "vector",
                          "matrix", "relation", "piecewise", "hole"])
        math_kind = self.node("types.schema.json", "/$defs/MathKind")
        self.assertEqual([case.match for case in math_kind.cases],
                         ["scalar_enum", "external_key", "external_key",
                          "external_key"])
        self.assertEqual([case.key for case in math_kind.cases],
                         [None, "vector", "matrix", "function"])

    def test_a10_real_typed_map_and_tuple(self):
        args = self.node("types.schema.json", "/$defs/Diagnostic/properties/args")
        self.assertEqual(args.kind, "map")
        self.assertEqual(self.bundle.node(args.item).kind, "string")
        args_value = self.node("types.schema.json",
                               "/$defs/Diagnostic/properties/args/additionalProperties")
        self.assertEqual((args_value.kind, args_value.fields), ("string", ()))
        pseudo = self.node("types.schema.json",
                           "/$defs/DimensionFull/properties/pseudo/items")
        self.assertEqual(pseudo.kind, "tuple")
        self.assertEqual(len(pseudo.prefix), 2)
        self.assertEqual((pseudo.limits.min_items, pseudo.limits.max_items), (2, 2))

    def test_a09_real_recursion_and_single_node(self):
        integrand = self.node("types.schema.json",
                              "/$defs/FormulaNode/oneOf/7/properties/integrand")
        self.assertEqual(integrand.kind, "ref")
        self.assertEqual(integrand.target.id, "types.schema.json#/$defs/FormulaNode")
        ids = [item.ref.id for item in self.bundle.nodes]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, sorted(ids))

    def test_a09_real_ordering_and_stability(self):
        again = ds.compile_manifest(REAL)
        self.assertEqual(again.nodes, self.bundle.nodes)
        self.assertEqual(again.named, self.bundle.named)
        self.assertEqual(again.ready, self.bundle.ready)
        self.assertEqual(again.pending, self.bundle.pending)
        titles = [self.bundle.node(ref).title for ref in self.bundle.named]
        self.assertEqual(titles, sorted(titles))
        ops = [item.op for item in self.bundle.ready]
        self.assertEqual(ops, sorted(ops))
        pending_ops = [item.op for item in self.bundle.pending]
        self.assertEqual(pending_ops, sorted(pending_ops))

    def test_a09_enumeration_order_does_not_matter(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "dto"
            target.mkdir()
            files = sorted(DTO.iterdir(), key=lambda item: item.name, reverse=True)
            for item in files:
                if item.is_file():
                    shutil.copyfile(item, target / item.name)
            reordered = ds.compile_manifest(target / "manifest.json")
        self.assertEqual(reordered.nodes, self.bundle.nodes)
        self.assertEqual(reordered.named, self.bundle.named)
        self.assertEqual(reordered.ready, self.bundle.ready)
        self.assertEqual(reordered.diagnostics, self.bundle.diagnostics)

    def test_a04_real_snapshot_facts(self):
        flagged = {item.op for item in self.bundle.ready
                   if item.reads_engine_snapshot}
        self.assertEqual(flagged, SNAPSHOT_OPS)
        for op in SNAPSHOT_OPS:
            self.assertIn(ds.ENGINE_SNAPSHOT_CODE,
                          self.ready(op).error_codes)
        for op in ("engine.generation", "engine.wait_generation"):
            item = self.ready(op)
            self.assertFalse(item.reads_engine_snapshot)
            self.assertEqual(item.error_codes, ())
        self.assertFalse(self.ready("engine.parse").reads_engine_snapshot)

    def test_a07_real_sensitive_paths(self):
        found = {item.op: item.sensitive_paths for item in self.bundle.ready
                 if item.sensitive_paths}
        self.assertEqual(found, {
            "account.create_guest": ("/ok/db_key",),
            "account.create_registered": ("/ok/db_key",),
            "account.open_profile": ("/body/db_key",),
            "store.open": ("/body/db_key_b64",),
        })

    def test_a07_real_numbers_are_exact(self):
        for item in self.bundle.nodes:
            for value in (item.limits.minimum, item.limits.maximum):
                if value is not None:
                    self.assertNotIsInstance(value, float)
                    self.assertIsInstance(value, (int, Decimal))
            for scalar in item.enum_values or ():
                self.assertNotIsInstance(scalar.value, float)

    def test_a11_real_invalid_stays_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "dto"
            shutil.copytree(DTO, target)
            (target / "engine.parse.schema.json").write_text("{", encoding="utf-8")
            broken = ds.compile_manifest(target / "manifest.json")
        self.assertFalse(broken.valid)
        self.assertEqual((broken.ready, broken.nodes, broken.named), ((), (), ()))
        self.assertEqual(len(broken.pending), 107)
        self.assertTrue(any(item.severity == "error" for item in broken.diagnostics))
        for item in broken.diagnostics:
            self.assertNotIn(":", item.source)
            self.assertFalse(Path(item.source).is_absolute())


SHARED = "types.schema.json"


def shared_types_schema(defs=None):
    """最小共享类型文档：manifest 不引用它，只有 include_shared=True 才进图。"""
    return {
        "$schema": ds.DIALECT,
        "title": "FixtureSharedTypes",
        "$defs": defs if defs is not None else {
            "Counted": {
                "title": "FixtureSharedCounted",
                "type": "object",
                "properties": {"n": {"type": "integer"}},
                "required": ["n"],
                "additionalProperties": False,
            },
            "Holder": {"title": "FixtureSharedHolder", "$ref": "#/$defs/Uuid"},
            "Uuid": {"title": "FixtureSharedUuid", "type": "string",
                     "format": "uuid"},
        },
    }


class SharedTypes(Base):
    """CORE-100：同图共享根增量默认关闭，开启后只补 manifest 不可达的根。"""

    def compile_shared(self, shared=None, entries=None, **kw):
        payload = {ECHO: echo_schema(), SHARED: shared_types_schema()}
        if shared is not None:
            payload[SHARED] = shared
        return self.compile(entries if entries is not None else [echo_entry()],
                            payload, **kw)

    def ids(self, bundle):
        return {item.ref.id for item in bundle.nodes}

    def test_core100_shared_default_off_matches_legacy_call(self):
        schemas = {ECHO: echo_schema(), SHARED: shared_types_schema()}
        default = self.compile([echo_entry()], schemas)
        explicit = self.compile([echo_entry()], schemas, include_shared=False)
        self.assertTrue(default.valid)
        for field in ("valid", "ready", "pending", "nodes", "named",
                      "diagnostics"):
            with self.subTest(field=field):
                self.assertEqual(getattr(default, field),
                                 getattr(explicit, field))
        path = self.write("manifest.json",
                          {"version": 1, "ops": [echo_entry()]})
        legacy = ds.compile_manifest(path, "S0", False)
        self.assertEqual(legacy.pending, default.pending)
        self.assertEqual(legacy.ready, default.ready)
        self.assertEqual(legacy.nodes, default.nodes)
        self.assertEqual(legacy.named, default.named)
        self.assertEqual(legacy.diagnostics, default.diagnostics)
        ids = self.ids(default)
        self.assertNotIn(SHARED + "#/$defs/Uuid", ids)
        self.assertNotIn(SHARED + "#/$defs/Counted", ids)

    def test_core100_shared_on_adds_roots_and_keeps_ops(self):
        off = self.compile_shared()
        on = self.compile_shared(include_shared=True)
        self.assertTrue(on.valid, self.codes(on))
        self.assertEqual(on.diagnostics, ())
        self.assertEqual(on.ready, off.ready)
        self.assertEqual(on.pending, off.pending)
        self.assertEqual(len(on.ready), 1)
        added = self.ids(on) - self.ids(off)
        roots = {SHARED + "#/$defs/Counted", SHARED + "#/$defs/Holder",
                 SHARED + "#/$defs/Uuid"}
        self.assertTrue(roots <= added)
        self.assertTrue(all(rid.startswith(SHARED + "#") for rid in added))
        off_named = {ref.id for ref in off.named}
        self.assertEqual({ref.id for ref in on.named} - off_named, roots)
        for item in off.nodes:
            self.assertEqual(on.node(item.ref), item)

    def test_core100_shared_roots_are_closed_refs(self):
        on = self.compile_shared(include_shared=True)
        known = self.ids(on)
        holder = on.node(ds.SchemaRef(SHARED + "#/$defs/Holder"))
        self.assertEqual(holder.kind, "ref")
        self.assertEqual(holder.target.id, SHARED + "#/$defs/Uuid")
        self.assertEqual(on.node(holder.target).kind, "string")
        for node in on.nodes:
            for field in node.fields:
                self.assertIn(field.value.id, known)
            for edge in (node.item, node.target):
                if edge is not None:
                    self.assertIn(edge.id, known)
            for edge in node.prefix:
                self.assertIn(edge.id, known)
            for case in node.cases:
                self.assertIn(case.branch.id, known)

    def test_core100_shared_empty_defs_is_valid(self):
        on = self.compile_shared(shared_types_schema({}), include_shared=True)
        self.assertTrue(on.valid)
        self.assertEqual(on.diagnostics, ())
        self.assertEqual(on.nodes,
                         self.compile([echo_entry()], {ECHO: echo_schema()}).nodes)

    def test_core100_shared_missing_file_is_diagnostic(self):
        bundle = self.compile([echo_entry()], {ECHO: echo_schema()},
                              include_shared=True)
        self.assert_invalid(bundle, ds.D_SCHEMA_JSON)
        diag = [item for item in bundle.diagnostics
                if item.code == ds.D_SCHEMA_JSON]
        self.assertEqual(len(diag), 1)
        self.assertEqual(diag[0].source, SHARED)
        self.assertEqual(diag[0].pointer, "")
        self.assertIsNone(diag[0].op)
        self.assertTrue(self.compile([echo_entry()], {ECHO: echo_schema()}).valid)

    def test_core100_shared_not_object_is_shape_diagnostic(self):
        for payload in ("null", "[]", '"FixtureSharedTypes"', "3"):
            with self.subTest(payload=payload):
                bundle = self.compile_shared(payload, include_shared=True)
                self.assert_invalid(bundle, ds.D_SCHEMA_SHAPE)
                self.assertEqual(self.codes(bundle), [ds.D_SCHEMA_SHAPE])

    def test_core100_shared_null_after_manifest_ref_is_diagnostic(self):
        # manifest 先按 $ref 读过同一文件，_doc 已把合法 JSON null 缓存成 None；
        # 共享根阶段必须仍判断出「解析成功但根不是对象」，不能因为缓存无新诊断
        # 就静默当成有效文档。
        schema = echo_schema(
            extra_ok={"uuid": {"$ref": SHARED + "#/$defs/Uuid"}})
        schemas = {ECHO: schema, SHARED: "null"}
        on = self.compile([echo_entry()], schemas, include_shared=True)
        self.assert_invalid(on, ds.D_SCHEMA_SHAPE)
        self.assertEqual(self.codes(on), [ds.D_SCHEMA_SHAPE])
        diag = [item for item in on.diagnostics
                if item.code == ds.D_SCHEMA_SHAPE]
        self.assertEqual(diag[0].source, SHARED)
        self.assertEqual(diag[0].pointer, "")
        self.assertIsNone(diag[0].op)
        # 默认关闭时保持既有行为：$ref 解析不到目标只让该字段无节点，不报诊断。
        off = self.compile([echo_entry()], schemas)
        self.assertTrue(off.valid)
        self.assertEqual(off.diagnostics, ())

    def test_core100_shared_broken_json_stays_json_code(self):
        for payload in ("{not json",
                        '{"$defs": {"A": {"type": "number", "default": NaN}}}'):
            with self.subTest(payload=payload):
                bundle = self.compile_shared(payload, include_shared=True)
                self.assert_invalid(bundle, ds.D_SCHEMA_JSON)

    def test_core100_shared_definitions_shape(self):
        cases = [
            (shared_types_schema([]), "/$defs"),
            ({"$schema": ds.DIALECT, "title": "FixtureSharedTypes"}, "/$defs"),
            (shared_types_schema({"Bad": "not-a-schema"}), "/$defs/Bad"),
        ]
        for payload, pointer in cases:
            with self.subTest(pointer=pointer):
                bundle = self.compile_shared(payload, include_shared=True)
                self.assert_invalid(bundle, ds.D_SCHEMA_SHAPE)
                self.assertTrue(any(item.pointer == pointer
                                    for item in bundle.diagnostics))

    def test_core100_shared_child_rules_apply(self):
        cases = [
            ({"Bad": {"type": "email"}}, ds.D_SCHEMA_TYPE),
            ({"Bad": {"type": "string", "patternProperties": {}}},
             ds.D_SCHEMA_KEYWORD),
            ({"Bad": {"$ref": "#/$defs/Absent"}}, ds.D_SCHEMA_REF),
            ({"Bad": {"title": "FixtureEchoOk", "type": "string"}},
             ds.D_SCHEMA_TITLE),
            ({"Bad": {"title": "lower", "type": "string"}}, ds.D_SCHEMA_TITLE),
            ({"Bad": {"type": "integer", "default": "1"}}, ds.D_SCHEMA_EXAMPLE),
        ]
        for defs, code in cases:
            with self.subTest(code=code, defs=defs):
                bundle = self.compile_shared(shared_types_schema(defs),
                                             include_shared=True)
                self.assert_invalid(bundle, code)

    def test_core100_shared_diagnostics_carry_no_op(self):
        bundle = self.compile_shared(shared_types_schema({"Bad": {"type": "email"}}),
                                     include_shared=True)
        self.assertFalse(bundle.valid)
        shared = [item for item in bundle.diagnostics if item.source == SHARED]
        self.assertTrue(shared)
        for item in shared:
            self.assertIsNone(item.op)
            self.assertEqual(item.severity, "error")

    def test_core100_shared_parameter_must_be_bool(self):
        for value in (1, 0, "yes", None, [True]):
            with self.subTest(value=value):
                with self.assertRaises(ds.SchemaToolError):
                    self.compile([echo_entry()], include_shared=value)
        path = self.write("manifest.json",
                          {"version": 1, "ops": [echo_entry()]})
        self.write(ECHO, echo_schema())
        with self.assertRaises(ds.SchemaToolError):
            ds.compile_manifest(path, None, False, "yes")

    def test_core100_shared_oserror_boundary(self):
        with self.assertRaises(OSError):
            ds.compile_manifest(self.dir / "absent" / "manifest.json",
                                include_shared=True)

    def test_core100_shared_ordering_is_stable(self):
        forward = self.compile_shared(include_shared=True)
        defs = shared_types_schema()["$defs"]
        reversed_defs = {key: defs[key] for key in reversed(list(defs))}
        reverse = self.compile_shared(shared_types_schema(reversed_defs),
                                      include_shared=True)
        self.assertTrue(reverse.valid)
        self.assertEqual(reverse.nodes, forward.nodes)
        self.assertEqual(reverse.named, forward.named)
        self.assertEqual(reverse.diagnostics, forward.diagnostics)
        self.assertEqual(self.compile_shared(include_shared=True).nodes,
                         forward.nodes)

    def test_core100_shared_does_not_mask_manifest_errors(self):
        bundle = self.compile_shared(
            entries=[echo_entry(owner="nope")], include_shared=True)
        self.assert_invalid(bundle, ds.D_MANIFEST_OWNER)
        self.assertEqual(self.codes(bundle), [ds.D_MANIFEST_OWNER])


@unittest.skipUnless(REAL.is_file(), "contracts/dto/manifest.json 不在工作树内")
class RealSharedTypes(unittest.TestCase):
    """CORE-100：真实 contracts/dto 数据快照上的共享根增量。"""

    @classmethod
    def setUpClass(cls):
        cls.off = ds.compile_manifest(REAL)
        cls.on = ds.compile_manifest(REAL, include_shared=True)
        cls.roots = sorted(json.loads(
            (DTO / SHARED).read_text(encoding="utf-8"))["$defs"])

    def ids(self, bundle):
        return {item.ref.id for item in bundle.nodes}

    def codes(self, bundle):
        return [item.code for item in bundle.diagnostics
                if item.severity == "error"]

    def test_core100_shared_real_default_is_off(self):
        self.assertTrue(self.off.valid)
        self.assertEqual(len(self.off.ready), 36)
        self.assertEqual(len(self.off.pending), 107)
        self.assertEqual(len(self.off.nodes), 624)
        self.assertEqual(len(self.off.named), 115)
        explicit = ds.compile_manifest(REAL, include_shared=False)
        self.assertEqual(explicit.ready, self.off.ready)
        self.assertEqual(explicit.pending, self.off.pending)
        self.assertEqual(explicit.nodes, self.off.nodes)
        self.assertEqual(explicit.named, self.off.named)
        self.assertEqual(explicit.diagnostics, self.off.diagnostics)
        for key in ("Envelope", "NodePath", "PullResponse", "PushItemResult",
                    "Uuid"):
            self.assertNotIn(SHARED + "#/$defs/" + key, self.ids(self.off))

    def test_core100_shared_real_adds_all_roots(self):
        self.assertTrue(self.on.valid)
        self.assertEqual(self.on.diagnostics, ())
        self.assertEqual(len(self.on.ready), 36)
        self.assertEqual(len(self.on.pending), 107)
        self.assertEqual(len(self.roots), 48)
        added = self.ids(self.on) - self.ids(self.off)
        self.assertEqual(len(added), 33)
        self.assertTrue(all(rid.startswith(SHARED + "#") for rid in added))
        self.assertEqual(len(self.on.nodes), 624 + 33)
        self.assertEqual(len(self.on.named), 115 + 5)
        self.assertTrue({SHARED + "#/$defs/" + key for key in self.roots}
                        <= self.ids(self.on))
        titles = [self.on.node(ref).title for ref in self.on.named]
        self.assertEqual((len(titles), len(set(titles))), (120, 120))

    def test_core100_shared_real_keeps_old_nodes_and_ops(self):
        self.assertEqual(self.on.ready, self.off.ready)
        self.assertEqual(self.on.pending, self.off.pending)
        for item in self.off.nodes:
            self.assertEqual(self.on.node(item.ref), item)

    def test_core100_shared_real_gates_unchanged(self):
        off_s0 = ds.compile_manifest(REAL, "S0")
        on_s0 = ds.compile_manifest(REAL, "S0", include_shared=True)
        self.assertTrue(on_s0.valid)
        self.assertEqual(len(on_s0.ready), 36)
        self.assertEqual(on_s0.diagnostics, off_s0.diagnostics)
        self.assertEqual(len(on_s0.diagnostics), 107)
        self.assertEqual({item.severity for item in on_s0.diagnostics}, {"info"})
        self.assertEqual(len(on_s0.nodes), 624 + 33)
        released = ds.compile_manifest(REAL, release=True, include_shared=True)
        self.assertFalse(released.valid)
        self.assertEqual(len(released.diagnostics), 107)
        self.assertEqual((released.ready, released.nodes, released.named),
                         ((), (), ()))
        self.assertEqual(len(released.pending), 107)

    def test_core100_shared_real_repeat_is_stable(self):
        again = ds.compile_manifest(REAL, include_shared=True)
        self.assertEqual(again.nodes, self.on.nodes)
        self.assertEqual(again.named, self.on.named)
        self.assertEqual(again.diagnostics, self.on.diagnostics)


class InvalidPolicy(Base):
    """验收 11：invalid 不返回半张图、诊断稳定、故障边界与消费方协议。"""

    def test_a11_partial_graph_is_never_returned(self):
        schema = echo_schema()
        schema["$defs"]["ok"]["properties"]["a"] = {"type": "string", "format": "email"}
        bundle = self.compile([echo_entry()], {ECHO: schema})
        self.assertFalse(bundle.valid)
        self.assertEqual(bundle.ready, ())
        self.assertEqual(bundle.nodes, ())
        self.assertEqual(bundle.named, ())
        self.assertTrue(bundle.diagnostics)

    def test_a11_diagnostics_are_sorted_and_locatable(self):
        bundle = self.compile([echo_entry(owner="nope", stage="S9"),
                               pending_entry(status="draft")])
        diags = bundle.diagnostics
        keys = [(item.source, item.pointer, item.op or "", item.code,
                 item.severity, item.message) for item in diags]
        self.assertEqual(keys, sorted(keys))
        self.assertTrue(all(item.message for item in diags))
        self.assertTrue(any(item.pointer.startswith("/ops/") for item in diags))
        self.assertEqual(self.compile([echo_entry(owner="nope", stage="S9"),
                                       pending_entry(status="draft")]).diagnostics,
                         diags)

    def test_a11_manifest_io_and_tool_errors(self):
        with self.assertRaises(OSError):
            ds.compile_manifest(self.dir / "absent" / "manifest.json")
        path = self.write("manifest.json", {"version": 1, "ops": [echo_entry()]})
        self.write(ECHO, echo_schema())
        for value in ("S9", "s0"):
            with self.subTest(stage=value):
                with self.assertRaises(ds.SchemaToolError):
                    ds.compile_manifest(path, required_stage=value)
        with self.assertRaises(ds.SchemaToolError):
            ds.compile_manifest(path, release="yes")

    def test_a11_broken_json_is_a_diagnostic(self):
        bundle = self.compile([echo_entry()], raw_manifest="{not json")
        self.assert_invalid(bundle, ds.D_MANIFEST_JSON)
        schema = echo_schema()
        schema["$defs"]["ok"]["properties"]["a"] = {"type": "number",
                                                    "default": 1.5}
        self.assertTrue(self.compile([echo_entry()], {ECHO: schema}).valid)
        raw = json.dumps(echo_schema()).replace(
            '"text": {"type": "string"}',
            '"text": {"type": "number", "default": NaN}', 1)
        self.assertNotEqual(raw, json.dumps(echo_schema()))
        self.assert_invalid(self.compile([echo_entry()], {ECHO: raw}),
                            ds.D_SCHEMA_JSON)

    def test_a11_consumer_protocol(self):
        def stand_in(path):
            try:
                bundle = ds.compile_manifest(path)
            except (OSError, ds.SchemaToolError):
                return 2, None
            if not bundle.valid:
                return 1, None
            lines = []
            for ref in bundle.named:
                item = bundle.node(ref)
                lines.append("%s=%s" % (item.title, item.kind))
            return 0, lines

        ok_path = self.dir / "manifest.json"
        self.write(ECHO, echo_schema())
        self.write("manifest.json", {"version": 1, "ops": [echo_entry()]})
        self.assertTrue(ds.compile_manifest(ok_path).valid)
        code, lines = stand_in(ok_path)
        self.assertEqual(code, 0)
        self.assertIn("FixtureEchoOk=object", lines)
        self.write(ECHO, echo_schema(examples=[]))
        self.assertEqual(stand_in(ok_path)[0], 1)
        self.assertEqual(stand_in(self.dir / "absent.json")[0], 2)


class ToolchainPremises(unittest.TestCase):
    """验收 7/11：外部前提只来自锁版文件，本库只用标准库。"""

    def test_a07_python_version_comes_from_locked_file(self):
        text = (REPO / "tools" / "toolchain.versions").read_text(encoding="utf-8")
        locked = None
        for line in text.splitlines():
            if line.startswith("python="):
                locked = tuple(int(part) for part in line.split("=", 1)[1].split("."))
        self.assertIsNotNone(locked)
        self.assertEqual(sys.version_info[:len(locked)], locked)

    def test_a07_module_imports_only_stdlib(self):
        tree = ast.parse(Path(ds.__file__).read_text(encoding="utf-8"))
        names = set()
        for item in ast.walk(tree):
            if isinstance(item, ast.Import):
                names.update(alias.name.split(".")[0] for alias in item.names)
            elif isinstance(item, ast.ImportFrom) and item.level == 0 and item.module:
                names.add(item.module.split(".")[0])
        self.assertTrue(names <= set(sys.stdlib_module_names),
                        sorted(names - set(sys.stdlib_module_names)))

    def test_a07_requirements_only_pin_versions(self):
        text = (REPO / "tools" / "requirements.txt").read_text(encoding="utf-8")
        lines = [line.strip() for line in text.splitlines()
                 if line.strip() and not line.strip().startswith("#")]
        import re
        for line in lines:
            self.assertRegex(line, r"^[A-Za-z0-9_.\-]+==[0-9][A-Za-z0-9.\-]*$")


class RepoFixture(unittest.TestCase):
    """验收 8：CORE-67 建好 tools/ci/tests/fixtures/dto 后复用同一份 fixture。"""

    FIXTURE = REPO / "tools" / "ci" / "tests" / "fixtures" / "dto"

    @unittest.skipUnless((REPO / "tools" / "ci" / "tests" / "fixtures" / "dto"
                          / "fixture.manifest.json").is_file(),
                         "CORE-67 尚未创建 fixture.manifest.json")
    def test_a08_repo_fixture_compiles(self):
        bundle = ds.compile_manifest(self.FIXTURE / "fixture.manifest.json")
        self.assertTrue(bundle.valid)
        op = bundle.ready[0]
        self.assertEqual(bundle.node(op.request).title, "FixtureEchoRequest")
        self.assertEqual(bundle.node(op.ok).title, "FixtureEchoOk")
        self.assertEqual([field.dart_name for field in bundle.node(op.request).fields],
                         ["text"])


if __name__ == "__main__":
    unittest.main()
