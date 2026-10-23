// GENERATED CODE - DO NOT MODIFY BY HAND.
// generator: CORE-67 v1
// source: manifest=manifest.json; schemas=derive.rank.schema.json, derive.run_plan.schema.json, derive.substitute.schema.json
// dart format off

import 'types.g.dart';

/// DeriveRankOk：不可变值对象；wire 键见各字段。
final class DeriveRankOk {
  /// 由 wire 字段构造。
  const DeriveRankOk({
    required this.candidates,
  });

  /// wire 键 candidates。
  final List<(Candidate, DeriveRankOkCandidatesItem1)> candidates;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DeriveRankOk.fromJson(Map<String, Object?> json) {
    return DeriveRankOk(
      candidates: readList(json, 'candidates', (Object? value) => readDeriveRankOkCandidatesValue(value)),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'candidates': encodeList(candidates, encodeDeriveRankOkCandidates),
    };
  }

  @override
  String toString() {
    return 'DeriveRankOk(candidates: $candidates)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DeriveRankOk &&
        dtoEquals(candidates, other.candidates);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(candidates),
  ]);
}

/// DeriveRankOkCandidates：定长元组；wire 为 JSON 数组。
typedef DeriveRankOkCandidates = (Candidate, DeriveRankOkCandidatesItem1);

/// 严格解码 DeriveRankOkCandidates：元素个数或类型不符抛 [FormatException]。
(Candidate, DeriveRankOkCandidatesItem1) readDeriveRankOkCandidatesValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 DeriveRankOkCandidates 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    Candidate.fromJson(asObject(items[0])),
    DeriveRankOkCandidatesItem1.fromWire(asString(items[1])),
  );
}

/// 编码 DeriveRankOkCandidates。
List<Object?> encodeDeriveRankOkCandidates((Candidate, DeriveRankOkCandidatesItem1) value) {
  final (Candidate item0, DeriveRankOkCandidatesItem1 item1) = value;
  return <Object?>[
    item0.toJson(),
    item1.wire,
  ];
}

/// 枚举 DeriveRankOkCandidatesItem1：wire 取值为 [wire]。
enum DeriveRankOkCandidatesItem1 {
  /// wire 取值 quantity_kind_exact。
  quantityKindExact('quantity_kind_exact'),
  /// wire 取值 dimension_unified。
  dimensionUnified('dimension_unified'),
  /// wire 取值 cross_kind。
  crossKind('cross_kind');

  const DeriveRankOkCandidatesItem1(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, DeriveRankOkCandidatesItem1> byWire = <String, DeriveRankOkCandidatesItem1>{
    'quantity_kind_exact': DeriveRankOkCandidatesItem1.quantityKindExact,
    'dimension_unified': DeriveRankOkCandidatesItem1.dimensionUnified,
    'cross_kind': DeriveRankOkCandidatesItem1.crossKind,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static DeriveRankOkCandidatesItem1 fromWire(String wire) {
    final DeriveRankOkCandidatesItem1? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 DeriveRankOkCandidatesItem1 wire 取值: $wire');
    }
    return found;
  }
}

/// DeriveRankRequest：不可变值对象；wire 键见各字段。
final class DeriveRankRequest {
  /// 由 wire 字段构造。
  const DeriveRankRequest({
    required this.includeCrossKind,
    required this.pool,
    required this.slot,
  });

  /// wire 键 include_cross_kind。
  final bool includeCrossKind;

  /// wire 键 pool。
  final List<Candidate> pool;

  /// wire 键 slot。
  final SlotRef slot;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DeriveRankRequest.fromJson(Map<String, Object?> json) {
    return DeriveRankRequest(
      includeCrossKind: readBool(json, 'include_cross_kind'),
      pool: readList(json, 'pool', (Object? value) => Candidate.fromJson(asObject(value))),
      slot: readObject(json, 'slot', SlotRef.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'include_cross_kind': includeCrossKind,
      'pool': encodeList(pool, (Candidate item) => item.toJson()),
      'slot': slot.toJson(),
    };
  }

  @override
  String toString() {
    return 'DeriveRankRequest(includeCrossKind: $includeCrossKind, pool: $pool, slot: $slot)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DeriveRankRequest &&
        dtoEquals(includeCrossKind, other.includeCrossKind) &&
        dtoEquals(pool, other.pool) &&
        dtoEquals(slot, other.slot);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(includeCrossKind),
    dtoHash(pool),
    dtoHash(slot),
  ]);
}

/// DeriveRunPlanOk：不可变值对象；wire 键见各字段。
final class DeriveRunPlanOk {
  /// 由 wire 字段构造。
  const DeriveRunPlanOk({
    required this.results,
  });

  /// wire 键 results。
  final List<CalcResult> results;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DeriveRunPlanOk.fromJson(Map<String, Object?> json) {
    return DeriveRunPlanOk(
      results: readList(json, 'results', (Object? value) => CalcResult.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'results': encodeList(results, (CalcResult item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'DeriveRunPlanOk(results: $results)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DeriveRunPlanOk &&
        dtoEquals(results, other.results);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(results),
  ]);
}

/// DeriveRunPlanRequest：不可变值对象；wire 键见各字段。
final class DeriveRunPlanRequest {
  /// 由 wire 字段构造。
  const DeriveRunPlanRequest({
    required this.plan,
    required this.revisions,
  });

  /// wire 键 plan。
  final CalculationPlan plan;

  /// wire 键 revisions。
  final List<RevisionSnapshot> revisions;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DeriveRunPlanRequest.fromJson(Map<String, Object?> json) {
    return DeriveRunPlanRequest(
      plan: readObject(json, 'plan', CalculationPlan.fromJson),
      revisions: readList(json, 'revisions', (Object? value) => RevisionSnapshot.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'plan': plan.toJson(),
      'revisions': encodeList(revisions, (RevisionSnapshot item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'DeriveRunPlanRequest(plan: $plan, revisions: $revisions)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DeriveRunPlanRequest &&
        dtoEquals(plan, other.plan) &&
        dtoEquals(revisions, other.revisions);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(plan),
    dtoHash(revisions),
  ]);
}

/// DeriveSubstituteOk：不可变值对象；wire 键见各字段。
final class DeriveSubstituteOk {
  /// 由 wire 字段构造。
  const DeriveSubstituteOk({
    required this.check,
    required this.derivation,
    required this.newAst,
    required this.symbols,
  });

  /// wire 键 check。
  final CheckResult check;

  /// wire 键 derivation。
  final Derivation derivation;

  /// wire 键 new_ast。
  final FormulaNode newAst;

  /// wire 键 symbols。
  final SymbolEnv symbols;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DeriveSubstituteOk.fromJson(Map<String, Object?> json) {
    return DeriveSubstituteOk(
      check: readObject(json, 'check', CheckResult.fromJson),
      derivation: readObject(json, 'derivation', Derivation.fromJson),
      newAst: readValue(json, 'new_ast', FormulaNode.fromJson),
      symbols: readObject(json, 'symbols', SymbolEnv.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'check': check.toJson(),
      'derivation': derivation.toJson(),
      'new_ast': newAst.toJson(),
      'symbols': symbols.toJson(),
    };
  }

  @override
  String toString() {
    return 'DeriveSubstituteOk(check: $check, derivation: $derivation, newAst: $newAst, symbols: $symbols)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DeriveSubstituteOk &&
        dtoEquals(check, other.check) &&
        dtoEquals(derivation, other.derivation) &&
        dtoEquals(newAst, other.newAst) &&
        dtoEquals(symbols, other.symbols);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(check),
    dtoHash(derivation),
    dtoHash(newAst),
    dtoHash(symbols),
  ]);
}

/// DeriveSubstituteRequest：不可变值对象；wire 键见各字段。
final class DeriveSubstituteRequest {
  /// 由 wire 字段构造。
  const DeriveSubstituteRequest({
    required this.ancestry,
    required this.request,
  });

  /// wire 键 ancestry。
  final List<DeriveSubstituteRequestAncestry> ancestry;

  /// wire 键 request。
  final SubstituteRequest request;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DeriveSubstituteRequest.fromJson(Map<String, Object?> json) {
    return DeriveSubstituteRequest(
      ancestry: readList(json, 'ancestry', (Object? value) => DeriveSubstituteRequestAncestry.fromJson(asObject(value))),
      request: readObject(json, 'request', SubstituteRequest.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'ancestry': encodeList(ancestry, (DeriveSubstituteRequestAncestry item) => item.toJson()),
      'request': request.toJson(),
    };
  }

  @override
  String toString() {
    return 'DeriveSubstituteRequest(ancestry: $ancestry, request: $request)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DeriveSubstituteRequest &&
        dtoEquals(ancestry, other.ancestry) &&
        dtoEquals(request, other.request);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(ancestry),
    dtoHash(request),
  ]);
}

/// DeriveSubstituteRequestAncestry：不可变值对象；wire 键见各字段。
final class DeriveSubstituteRequestAncestry {
  /// 由 wire 字段构造。
  const DeriveSubstituteRequestAncestry({
    required this.ancestors,
    required this.depth,
    required this.revision,
  });

  /// wire 键 ancestors。
  final List<String> ancestors;

  /// wire 键 depth。
  final int depth;

  /// wire 键 revision。
  final String revision;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DeriveSubstituteRequestAncestry.fromJson(Map<String, Object?> json) {
    return DeriveSubstituteRequestAncestry(
      ancestors: readList(json, 'ancestors', (Object? value) => asString(value)),
      depth: readInt(json, 'depth'),
      revision: readString(json, 'revision'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'ancestors': ancestors,
      'depth': depth,
      'revision': revision,
    };
  }

  @override
  String toString() {
    return 'DeriveSubstituteRequestAncestry(ancestors: $ancestors, depth: $depth, revision: $revision)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DeriveSubstituteRequestAncestry &&
        dtoEquals(ancestors, other.ancestors) &&
        dtoEquals(depth, other.depth) &&
        dtoEquals(revision, other.revision);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(ancestors),
    dtoHash(depth),
    dtoHash(revision),
  ]);
}

/// 断言 JSON 数组并返回元素列表。
List<Object?> asList(Object? value) {
  if (value is! List) {
    throw FormatException('期望 JSON 数组: $value');
  }
  return value;
}

/// 把 JSON 值收成对象。
Map<String, Object?> asObject(Object? value) {
  if (value is Map<String, Object?>) return value;
  throw const FormatException('元素应为 object');
}

/// 把 JSON 值收成 string。
String asString(Object? value) {
  if (value is String) return value;
  throw const FormatException('元素应为 string');
}

/// 递归值相等：列表逐项、映射逐键，其余用 ==。
bool dtoEquals(Object? a, Object? b) {
  if (identical(a, b)) {
    return true;
  }
  if (a is List && b is List) {
    if (a.length != b.length) {
      return false;
    }
    for (int index = 0; index < a.length; index++) {
      if (!dtoEquals(a[index], b[index])) {
        return false;
      }
    }
    return true;
  }
  if (a is Map && b is Map) {
    if (a.length != b.length) {
      return false;
    }
    for (final Object? key in a.keys) {
      if (!b.containsKey(key) || !dtoEquals(a[key], b[key])) {
        return false;
      }
    }
    return true;
  }
  return a == b;
}

/// 与 [dtoEquals] 一致的递归哈希：列表有序、映射无序。
int dtoHash(Object? value) {
  if (value is List) {
    final List<int> hashes = <int>[];
    for (final Object? item in value) {
      hashes.add(dtoHash(item));
    }
    return Object.hashAll(hashes);
  }
  if (value is Map) {
    final List<int> hashes = <int>[];
    for (final Object? key in value.keys) {
      hashes.add(Object.hash(dtoHash(key), dtoHash(value[key])));
    }
    return Object.hashAllUnordered(hashes);
  }
  return value.hashCode;
}

/// 把列表逐项编码成 JSON 值。
List<Object?> encodeList<T>(List<T> values, Object? Function(T) encode) {
  return values.map<Object?>(encode).toList(growable: false);
}

/// 严格读取 bool 字段。
bool readBool(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is bool) return value;
  throw FormatException('字段 ' + key + ' 应为 bool');
}

/// 严格读取 int 字段。
int readInt(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is int) return value;
  throw FormatException('字段 ' + key + ' 应为 int');
}

/// 严格读取数组字段并逐个解码。
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
}

/// 严格读取对象字段并解码。
T readObject<T>(
  Map<String, Object?> json,
  String key,
  T Function(Map<String, Object?>) decode,
) {
  final Object? value = json[key];
  if (value is Map<String, Object?>) return decode(value);
  throw FormatException('字段 ' + key + ' 应为 object');
}

/// 严格读取 string 字段。
String readString(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is String) return value;
  throw FormatException('字段 ' + key + ' 应为 string');
}

/// 读取必填键并交给 [decode]；缺键抛 [FormatException]。
T readValue<T>(Map<String, Object?> json, String key, T Function(Object?) decode) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填键: $key');
  }
  return decode(json[key]);
}
