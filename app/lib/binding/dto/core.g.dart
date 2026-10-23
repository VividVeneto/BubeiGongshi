// GENERATED CODE - DO NOT MODIFY BY HAND.
// generator: CORE-67 v1
// source: manifest=manifest.json; schemas=core.log_init.schema.json
// dart format off

/// CoreLogInitOk：不可变值对象；wire 键见各字段。
final class CoreLogInitOk {
  /// 无 wire 字段的空对象。
  const CoreLogInitOk();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CoreLogInitOk.fromJson(Map<String, Object?> json) {
    return const CoreLogInitOk();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'CoreLogInitOk()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is CoreLogInitOk;
  }

  @override
  int get hashCode => 0;
}

/// CoreLogInitRequest：不可变值对象；wire 键见各字段。
final class CoreLogInitRequest {
  /// 由 wire 字段构造。
  const CoreLogInitRequest({
    required this.dir,
    required this.level,
  });

  /// wire 键 dir。
  final String dir;

  /// wire 键 level。
  final CoreLogInitRequestLevel level;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CoreLogInitRequest.fromJson(Map<String, Object?> json) {
    return CoreLogInitRequest(
      dir: readString(json, 'dir'),
      level: readEnum(json, 'level', CoreLogInitRequestLevel.fromWire),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'dir': dir,
      'level': level.wire,
    };
  }

  @override
  String toString() {
    return 'CoreLogInitRequest(dir: $dir, level: $level)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CoreLogInitRequest &&
        dtoEquals(dir, other.dir) &&
        dtoEquals(level, other.level);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(dir),
    dtoHash(level),
  ]);
}

/// 枚举 CoreLogInitRequestLevel：wire 取值为 [wire]。
enum CoreLogInitRequestLevel {
  /// wire 取值 debug。
  debug('debug'),
  /// wire 取值 info。
  info('info'),
  /// wire 取值 warning。
  warning('warning'),
  /// wire 取值 error。
  error('error');

  const CoreLogInitRequestLevel(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, CoreLogInitRequestLevel> byWire = <String, CoreLogInitRequestLevel>{
    'debug': CoreLogInitRequestLevel.debug,
    'info': CoreLogInitRequestLevel.info,
    'warning': CoreLogInitRequestLevel.warning,
    'error': CoreLogInitRequestLevel.error,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static CoreLogInitRequestLevel fromWire(String wire) {
    final CoreLogInitRequestLevel? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 CoreLogInitRequestLevel wire 取值: $wire');
    }
    return found;
  }
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

/// 严格读取枚举字段（wire 字符串）。
T readEnum<T>(
  Map<String, Object?> json,
  String key,
  T Function(String) fromWire,
) {
  final Object? value = json[key];
  if (value is String) return fromWire(value);
  throw FormatException('字段 ' + key + ' 应为字符串枚举');
}

/// 严格读取 string 字段。
String readString(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is String) return value;
  throw FormatException('字段 ' + key + ' 应为 string');
}
