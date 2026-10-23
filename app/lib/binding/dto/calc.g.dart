// GENERATED CODE - DO NOT MODIFY BY HAND.
// generator: CORE-67 v1
// source: manifest=manifest.json; schemas=calc.evaluate.schema.json, calc.solvable_targets.schema.json
// dart format off

import 'types.g.dart';

/// 共享别名 CalcEvaluateOk：wire 形状与 CalcResult 相同。
typedef CalcEvaluateOk = CalcResult;

/// CalcEvaluateRequest：不可变值对象；wire 键见各字段。
final class CalcEvaluateRequest {
  /// 由 wire 字段构造。
  const CalcEvaluateRequest({
    required this.assignments,
    required this.display,
    required this.empirical,
    required this.givenConstants,
    this.interval,
    required this.notationProfileId,
    this.outputUnit,
    required this.source,
    required this.target,
    required this.userDecls,
  });

  /// wire 键 assignments。
  final List<Assignment> assignments;

  /// wire 键 display。
  final DisplayPrecision display;

  /// wire 键 empirical。
  final bool empirical;

  /// wire 键 given_constants。
  final List<ConstantValue> givenConstants;

  /// wire 键 interval。
  final (String, String)? interval;

  /// wire 键 notation_profile_id。
  final String notationProfileId;

  /// wire 键 output_unit。
  final String? outputUnit;

  /// wire 键 source。
  final String source;

  /// wire 键 target。
  final int target;

  /// wire 键 user_decls。
  final List<SymbolDecl> userDecls;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CalcEvaluateRequest.fromJson(Map<String, Object?> json) {
    return CalcEvaluateRequest(
      assignments: readList(json, 'assignments', (Object? value) => Assignment.fromJson(asObject(value))),
      display: readValue(json, 'display', DisplayPrecision.fromJson),
      empirical: readBool(json, 'empirical'),
      givenConstants: readList(json, 'given_constants', (Object? value) => ConstantValue.fromJson(asObject(value))),
      interval: readValueOrNull(json, 'interval', readCalcEvaluateRequestIntervalValue),
      notationProfileId: readString(json, 'notation_profile_id'),
      outputUnit: readStringOrNull(json, 'output_unit'),
      source: readString(json, 'source'),
      target: readInt(json, 'target'),
      userDecls: readList(json, 'user_decls', (Object? value) => SymbolDecl.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'assignments': encodeList(assignments, (Assignment item) => item.toJson()),
      'display': display.toJson(),
      'empirical': empirical,
      'given_constants': encodeList(givenConstants, (ConstantValue item) => item.toJson()),
      'interval': interval == null ? null : encodeCalcEvaluateRequestInterval(interval!),
      'notation_profile_id': notationProfileId,
      'output_unit': outputUnit,
      'source': source,
      'target': target,
      'user_decls': encodeList(userDecls, (SymbolDecl item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'CalcEvaluateRequest(assignments: $assignments, display: $display, empirical: $empirical, givenConstants: $givenConstants, interval: $interval, notationProfileId: $notationProfileId, outputUnit: $outputUnit, source: $source, target: $target, userDecls: $userDecls)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CalcEvaluateRequest &&
        dtoEquals(assignments, other.assignments) &&
        dtoEquals(display, other.display) &&
        dtoEquals(empirical, other.empirical) &&
        dtoEquals(givenConstants, other.givenConstants) &&
        dtoEquals(interval, other.interval) &&
        dtoEquals(notationProfileId, other.notationProfileId) &&
        dtoEquals(outputUnit, other.outputUnit) &&
        dtoEquals(source, other.source) &&
        dtoEquals(target, other.target) &&
        dtoEquals(userDecls, other.userDecls);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(assignments),
    dtoHash(display),
    dtoHash(empirical),
    dtoHash(givenConstants),
    dtoHash(interval),
    dtoHash(notationProfileId),
    dtoHash(outputUnit),
    dtoHash(source),
    dtoHash(target),
    dtoHash(userDecls),
  ]);
}

/// CalcEvaluateRequestInterval：定长元组；wire 为 JSON 数组。
typedef CalcEvaluateRequestInterval = (String, String);

/// 严格解码 CalcEvaluateRequestInterval：元素个数或类型不符抛 [FormatException]。
(String, String) readCalcEvaluateRequestIntervalValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 CalcEvaluateRequestInterval 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asString(items[0]),
    asString(items[1]),
  );
}

/// 编码 CalcEvaluateRequestInterval。
List<Object?> encodeCalcEvaluateRequestInterval((String, String) value) {
  final (String item0, String item1) = value;
  return <Object?>[
    item0,
    item1,
  ];
}

/// CalcSolvableTargetsOk：不可变值对象；wire 键见各字段。
final class CalcSolvableTargetsOk {
  /// 由 wire 字段构造。
  const CalcSolvableTargetsOk({
    required this.targets,
  });

  /// wire 键 targets。
  final List<CalcSolvableTargetsOkTargets> targets;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CalcSolvableTargetsOk.fromJson(Map<String, Object?> json) {
    return CalcSolvableTargetsOk(
      targets: readList(json, 'targets', (Object? value) => CalcSolvableTargetsOkTargets.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'targets': encodeList(targets, (CalcSolvableTargetsOkTargets item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'CalcSolvableTargetsOk(targets: $targets)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CalcSolvableTargetsOk &&
        dtoEquals(targets, other.targets);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(targets),
  ]);
}

/// CalcSolvableTargetsOkTargets：不可变值对象；wire 键见各字段。
final class CalcSolvableTargetsOkTargets {
  /// 由 wire 字段构造。
  const CalcSolvableTargetsOkTargets({
    required this.capability,
    required this.symbol,
  });

  /// wire 键 capability。
  final SolveCapability capability;

  /// wire 键 symbol。
  final int symbol;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CalcSolvableTargetsOkTargets.fromJson(Map<String, Object?> json) {
    return CalcSolvableTargetsOkTargets(
      capability: readValue(json, 'capability', SolveCapability.fromJson),
      symbol: readInt(json, 'symbol'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'capability': capability.toJson(),
      'symbol': symbol,
    };
  }

  @override
  String toString() {
    return 'CalcSolvableTargetsOkTargets(capability: $capability, symbol: $symbol)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CalcSolvableTargetsOkTargets &&
        dtoEquals(capability, other.capability) &&
        dtoEquals(symbol, other.symbol);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(capability),
    dtoHash(symbol),
  ]);
}

/// CalcSolvableTargetsRequest：不可变值对象；wire 键见各字段。
final class CalcSolvableTargetsRequest {
  /// 由 wire 字段构造。
  const CalcSolvableTargetsRequest({
    required this.empirical,
    required this.notationProfileId,
    required this.source,
    required this.userDecls,
  });

  /// wire 键 empirical。
  final bool empirical;

  /// wire 键 notation_profile_id。
  final String notationProfileId;

  /// wire 键 source。
  final String source;

  /// wire 键 user_decls。
  final List<SymbolDecl> userDecls;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CalcSolvableTargetsRequest.fromJson(Map<String, Object?> json) {
    return CalcSolvableTargetsRequest(
      empirical: readBool(json, 'empirical'),
      notationProfileId: readString(json, 'notation_profile_id'),
      source: readString(json, 'source'),
      userDecls: readList(json, 'user_decls', (Object? value) => SymbolDecl.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'empirical': empirical,
      'notation_profile_id': notationProfileId,
      'source': source,
      'user_decls': encodeList(userDecls, (SymbolDecl item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'CalcSolvableTargetsRequest(empirical: $empirical, notationProfileId: $notationProfileId, source: $source, userDecls: $userDecls)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CalcSolvableTargetsRequest &&
        dtoEquals(empirical, other.empirical) &&
        dtoEquals(notationProfileId, other.notationProfileId) &&
        dtoEquals(source, other.source) &&
        dtoEquals(userDecls, other.userDecls);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(empirical),
    dtoHash(notationProfileId),
    dtoHash(source),
    dtoHash(userDecls),
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

/// 严格读取 string 字段。
String readString(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is String) return value;
  throw FormatException('字段 ' + key + ' 应为 string');
}

/// 读取可空 string 字段。
String? readStringOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is String) return value;
  throw FormatException('字段 ' + key + ' 应为 string 或 null');
}

/// 读取必填键并交给 [decode]；缺键抛 [FormatException]。
T readValue<T>(Map<String, Object?> json, String key, T Function(Object?) decode) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填键: $key');
  }
  return decode(json[key]);
}

/// 读取可空键并交给 [decode]；缺键或显式 null 返回 null。
T? readValueOrNull<T>(
    Map<String, Object?> json, String key, T Function(Object?) decode) {
  final Object? value = json[key];
  return value == null ? null : decode(value);
}
