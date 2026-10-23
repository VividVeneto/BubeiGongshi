// GENERATED CODE - DO NOT MODIFY BY HAND.
// generator: CORE-67 v1
// source: manifest=manifest.json; schemas=store.close.schema.json, store.integrity_check.schema.json, store.open.schema.json
// dart format off

import 'dart:convert';
import 'dart:typed_data';
import 'types.g.dart';

/// StoreCloseOk：不可变值对象；wire 键见各字段。
final class StoreCloseOk {
  /// 无 wire 字段的空对象。
  const StoreCloseOk();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory StoreCloseOk.fromJson(Map<String, Object?> json) {
    return const StoreCloseOk();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'StoreCloseOk()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is StoreCloseOk;
  }

  @override
  int get hashCode => 0;
}

/// StoreCloseRequest：不可变值对象；wire 键见各字段。
final class StoreCloseRequest {
  /// 由 wire 字段构造。
  const StoreCloseRequest({
    required this.handle,
  });

  /// wire 键 handle。
  final String handle;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory StoreCloseRequest.fromJson(Map<String, Object?> json) {
    return StoreCloseRequest(
      handle: readString(json, 'handle'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'handle': handle,
    };
  }

  @override
  String toString() {
    return 'StoreCloseRequest(handle: $handle)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is StoreCloseRequest &&
        dtoEquals(handle, other.handle);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(handle),
  ]);
}

/// 共享别名 StoreIntegrityCheckOk：wire 形状与 IntegrityReport 相同。
typedef StoreIntegrityCheckOk = IntegrityReport;

/// StoreIntegrityCheckRequest：不可变值对象；wire 键见各字段。
final class StoreIntegrityCheckRequest {
  /// 由 wire 字段构造。
  const StoreIntegrityCheckRequest({
    required this.handle,
  });

  /// wire 键 handle。
  final String handle;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory StoreIntegrityCheckRequest.fromJson(Map<String, Object?> json) {
    return StoreIntegrityCheckRequest(
      handle: readString(json, 'handle'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'handle': handle,
    };
  }

  @override
  String toString() {
    return 'StoreIntegrityCheckRequest(handle: $handle)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is StoreIntegrityCheckRequest &&
        dtoEquals(handle, other.handle);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(handle),
  ]);
}

/// StoreOpenOk：不可变值对象；wire 键见各字段。
final class StoreOpenOk {
  /// 由 wire 字段构造。
  const StoreOpenOk({
    required this.handle,
    required this.schemaVersion,
  });

  /// wire 键 handle。
  final String handle;

  /// wire 键 schema_version。
  final int schemaVersion;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory StoreOpenOk.fromJson(Map<String, Object?> json) {
    return StoreOpenOk(
      handle: readString(json, 'handle'),
      schemaVersion: readInt(json, 'schema_version'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'handle': handle,
      'schema_version': schemaVersion,
    };
  }

  @override
  String toString() {
    return 'StoreOpenOk(handle: $handle, schemaVersion: $schemaVersion)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is StoreOpenOk &&
        dtoEquals(handle, other.handle) &&
        dtoEquals(schemaVersion, other.schemaVersion);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(handle),
    dtoHash(schemaVersion),
  ]);
}

/// StoreOpenRequest：不可变值对象；wire 键见各字段。
final class StoreOpenRequest {
  /// 由 wire 字段构造。
  const StoreOpenRequest({
    required this.config,
    required this.dbKeyB64,
  });

  /// wire 键 config。
  final StoreConfig config;

  /// wire 键 db_key_b64。
  final Uint8List dbKeyB64;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory StoreOpenRequest.fromJson(Map<String, Object?> json) {
    return StoreOpenRequest(
      config: readObject(json, 'config', StoreConfig.fromJson),
      dbKeyB64: readBytes(json, 'db_key_b64'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'config': config.toJson(),
      'db_key_b64': base64Encode(dbKeyB64),
    };
  }

  @override
  String toString() {
    return 'StoreOpenRequest(config: $config, dbKeyB64: <redacted>)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is StoreOpenRequest &&
        dtoEquals(config, other.config) &&
        dtoEquals(dbKeyB64, other.dbKeyB64);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(config),
    dtoHash(dbKeyB64),
  ]);
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

/// 严格读取 base64 字节字段。
Uint8List readBytes(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  final String? text = value is String ? value : null;
  if (text != null) return base64Decode(text);
  throw FormatException('字段 ' + key + ' 应为 base64 字符串');
}

/// 严格读取 int 字段。
int readInt(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is int) return value;
  throw FormatException('字段 ' + key + ' 应为 int');
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
