// GENERATED CODE - DO NOT MODIFY BY HAND.
// generator: CORE-67 v1
// source: manifest=manifest.json; schemas=units.compatible.schema.json, units.convert.schema.json
// dart format off

import 'types.g.dart';

/// UnitsCompatibleOk：不可变值对象；wire 键见各字段。
final class UnitsCompatibleOk {
  /// 由 wire 字段构造。
  const UnitsCompatibleOk({
    required this.units,
  });

  /// wire 键 units。
  final List<Unit> units;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory UnitsCompatibleOk.fromJson(Map<String, Object?> json) {
    return UnitsCompatibleOk(
      units: readList(json, 'units', (Object? value) => Unit.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'units': encodeList(units, (Unit item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'UnitsCompatibleOk(units: $units)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is UnitsCompatibleOk &&
        dtoEquals(units, other.units);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(units),
  ]);
}

/// UnitsCompatibleRequest：不可变值对象；wire 键见各字段。
final class UnitsCompatibleRequest {
  /// 由 wire 字段构造。
  const UnitsCompatibleRequest({
    required this.dimension,
  });

  /// wire 键 dimension。
  final DimensionFull dimension;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory UnitsCompatibleRequest.fromJson(Map<String, Object?> json) {
    return UnitsCompatibleRequest(
      dimension: readObject(json, 'dimension', DimensionFull.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'dimension': dimension.toJson(),
    };
  }

  @override
  String toString() {
    return 'UnitsCompatibleRequest(dimension: $dimension)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is UnitsCompatibleRequest &&
        dtoEquals(dimension, other.dimension);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(dimension),
  ]);
}

/// UnitsConvertOk：不可变值对象；wire 键见各字段。
final class UnitsConvertOk {
  /// 由 wire 字段构造。
  const UnitsConvertOk({
    required this.value,
  });

  /// wire 键 value。
  final Rational value;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory UnitsConvertOk.fromJson(Map<String, Object?> json) {
    return UnitsConvertOk(
      value: readObject(json, 'value', Rational.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'value': value.toJson(),
    };
  }

  @override
  String toString() {
    return 'UnitsConvertOk(value: $value)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is UnitsConvertOk &&
        dtoEquals(value, other.value);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(value),
  ]);
}

/// UnitsConvertRequest：不可变值对象；wire 键见各字段。
final class UnitsConvertRequest {
  /// 由 wire 字段构造。
  const UnitsConvertRequest({
    required this.from,
    required this.to,
    required this.value,
  });

  /// wire 键 from。
  final String from;

  /// wire 键 to。
  final String to;

  /// wire 键 value。
  final Rational value;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory UnitsConvertRequest.fromJson(Map<String, Object?> json) {
    return UnitsConvertRequest(
      from: readString(json, 'from'),
      to: readString(json, 'to'),
      value: readObject(json, 'value', Rational.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'from': from,
      'to': to,
      'value': value.toJson(),
    };
  }

  @override
  String toString() {
    return 'UnitsConvertRequest(from: $from, to: $to, value: $value)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is UnitsConvertRequest &&
        dtoEquals(from, other.from) &&
        dtoEquals(to, other.to) &&
        dtoEquals(value, other.value);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(from),
    dtoHash(to),
    dtoHash(value),
  ]);
}

/// 把 JSON 值收成对象。
Map<String, Object?> asObject(Object? value) {
  if (value is Map<String, Object?>) return value;
  throw const FormatException('元素应为 object');
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
