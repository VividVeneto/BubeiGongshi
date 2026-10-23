// GENERATED CODE - DO NOT MODIFY BY HAND.
// generator: CORE-67 v1
// source: manifest=manifest.json; schemas=constants.resolve.schema.json
// dart format off

import 'types.g.dart';

/// ConstantsResolveOk：不可变值对象；wire 键见各字段。
final class ConstantsResolveOk {
  /// 由 wire 字段构造。
  const ConstantsResolveOk({
    this.value,
  });

  /// wire 键 value。
  final ConstantValue? value;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ConstantsResolveOk.fromJson(Map<String, Object?> json) {
    return ConstantsResolveOk(
      value: readObjectOrNull(json, 'value', ConstantValue.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'value': value?.toJson(),
    };
  }

  @override
  String toString() {
    return 'ConstantsResolveOk(value: $value)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ConstantsResolveOk &&
        dtoEquals(value, other.value);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(value),
  ]);
}

/// ConstantsResolveRequest：不可变值对象；wire 键见各字段。
final class ConstantsResolveRequest {
  /// 由 wire 字段构造。
  const ConstantsResolveRequest({
    required this.given,
    required this.key,
    required this.textbookSetId,
  });

  /// wire 键 given。
  final List<ConstantValue> given;

  /// wire 键 key。
  final String key;

  /// wire 键 textbook_set_id。
  final String textbookSetId;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ConstantsResolveRequest.fromJson(Map<String, Object?> json) {
    return ConstantsResolveRequest(
      given: readList(json, 'given', (Object? value) => ConstantValue.fromJson(asObject(value))),
      key: readString(json, 'key'),
      textbookSetId: readString(json, 'textbook_set_id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'given': encodeList(given, (ConstantValue item) => item.toJson()),
      'key': key,
      'textbook_set_id': textbookSetId,
    };
  }

  @override
  String toString() {
    return 'ConstantsResolveRequest(given: $given, key: $key, textbookSetId: $textbookSetId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ConstantsResolveRequest &&
        dtoEquals(given, other.given) &&
        dtoEquals(key, other.key) &&
        dtoEquals(textbookSetId, other.textbookSetId);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(given),
    dtoHash(key),
    dtoHash(textbookSetId),
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

/// 读取可空对象字段并解码。
T? readObjectOrNull<T>(
  Map<String, Object?> json,
  String key,
  T Function(Map<String, Object?>) decode,
) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is Map<String, Object?>) return decode(value);
  throw FormatException('字段 ' + key + ' 应为 object 或 null');
}

/// 严格读取 string 字段。
String readString(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is String) return value;
  throw FormatException('字段 ' + key + ' 应为 string');
}
