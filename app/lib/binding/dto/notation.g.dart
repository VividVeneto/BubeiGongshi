// GENERATED CODE - DO NOT MODIFY BY HAND.
// generator: CORE-67 v1
// source: manifest=manifest.json; schemas=notation.bind.schema.json, notation.display.schema.json, notation.profiles.schema.json
// dart format off

import 'types.g.dart';

/// NotationBindOk：不可变值对象；wire 键见各字段。
final class NotationBindOk {
  /// 由 wire 字段构造。
  const NotationBindOk({
    required this.diagnostics,
    required this.symbols,
  });

  /// wire 键 diagnostics。
  final List<Diagnostic> diagnostics;

  /// wire 键 symbols。
  final SymbolEnv symbols;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory NotationBindOk.fromJson(Map<String, Object?> json) {
    return NotationBindOk(
      diagnostics: readList(json, 'diagnostics', (Object? value) => Diagnostic.fromJson(asObject(value))),
      symbols: readObject(json, 'symbols', SymbolEnv.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'diagnostics': encodeList(diagnostics, (Diagnostic item) => item.toJson()),
      'symbols': symbols.toJson(),
    };
  }

  @override
  String toString() {
    return 'NotationBindOk(diagnostics: $diagnostics, symbols: $symbols)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is NotationBindOk &&
        dtoEquals(diagnostics, other.diagnostics) &&
        dtoEquals(symbols, other.symbols);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(diagnostics),
    dtoHash(symbols),
  ]);
}

/// NotationBindRequest：不可变值对象；wire 键见各字段。
final class NotationBindRequest {
  /// 由 wire 字段构造。
  const NotationBindRequest({
    required this.ast,
    required this.notationProfileId,
    required this.raw,
    required this.userDecls,
  });

  /// wire 键 ast。
  final FormulaNode ast;

  /// wire 键 notation_profile_id。
  final String notationProfileId;

  /// wire 键 raw。
  final List<RawSymbol> raw;

  /// wire 键 user_decls。
  final List<SymbolDecl> userDecls;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory NotationBindRequest.fromJson(Map<String, Object?> json) {
    return NotationBindRequest(
      ast: readValue(json, 'ast', FormulaNode.fromJson),
      notationProfileId: readString(json, 'notation_profile_id'),
      raw: readList(json, 'raw', (Object? value) => RawSymbol.fromJson(asObject(value))),
      userDecls: readList(json, 'user_decls', (Object? value) => SymbolDecl.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'ast': ast.toJson(),
      'notation_profile_id': notationProfileId,
      'raw': encodeList(raw, (RawSymbol item) => item.toJson()),
      'user_decls': encodeList(userDecls, (SymbolDecl item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'NotationBindRequest(ast: $ast, notationProfileId: $notationProfileId, raw: $raw, userDecls: $userDecls)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is NotationBindRequest &&
        dtoEquals(ast, other.ast) &&
        dtoEquals(notationProfileId, other.notationProfileId) &&
        dtoEquals(raw, other.raw) &&
        dtoEquals(userDecls, other.userDecls);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(ast),
    dtoHash(notationProfileId),
    dtoHash(raw),
    dtoHash(userDecls),
  ]);
}

/// NotationDisplayOk：不可变值对象；wire 键见各字段。
final class NotationDisplayOk {
  /// 由 wire 字段构造。
  const NotationDisplayOk({
    required this.glyph,
  });

  /// wire 键 glyph。
  final String glyph;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory NotationDisplayOk.fromJson(Map<String, Object?> json) {
    return NotationDisplayOk(
      glyph: readString(json, 'glyph'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'glyph': glyph,
    };
  }

  @override
  String toString() {
    return 'NotationDisplayOk(glyph: $glyph)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is NotationDisplayOk &&
        dtoEquals(glyph, other.glyph);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(glyph),
  ]);
}

/// NotationDisplayRequest：不可变值对象；wire 键见各字段。
final class NotationDisplayRequest {
  /// 由 wire 字段构造。
  const NotationDisplayRequest({
    required this.decl,
    required this.notationProfileId,
  });

  /// wire 键 decl。
  final SymbolDecl decl;

  /// wire 键 notation_profile_id。
  final String notationProfileId;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory NotationDisplayRequest.fromJson(Map<String, Object?> json) {
    return NotationDisplayRequest(
      decl: readObject(json, 'decl', SymbolDecl.fromJson),
      notationProfileId: readString(json, 'notation_profile_id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'decl': decl.toJson(),
      'notation_profile_id': notationProfileId,
    };
  }

  @override
  String toString() {
    return 'NotationDisplayRequest(decl: $decl, notationProfileId: $notationProfileId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is NotationDisplayRequest &&
        dtoEquals(decl, other.decl) &&
        dtoEquals(notationProfileId, other.notationProfileId);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(decl),
    dtoHash(notationProfileId),
  ]);
}

/// NotationProfilesOk：不可变值对象；wire 键见各字段。
final class NotationProfilesOk {
  /// 由 wire 字段构造。
  const NotationProfilesOk({
    required this.profiles,
  });

  /// wire 键 profiles。
  final List<NotationProfile> profiles;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory NotationProfilesOk.fromJson(Map<String, Object?> json) {
    return NotationProfilesOk(
      profiles: readList(json, 'profiles', (Object? value) => NotationProfile.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'profiles': encodeList(profiles, (NotationProfile item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'NotationProfilesOk(profiles: $profiles)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is NotationProfilesOk &&
        dtoEquals(profiles, other.profiles);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(profiles),
  ]);
}

/// NotationProfilesRequest：不可变值对象；wire 键见各字段。
final class NotationProfilesRequest {
  /// 无 wire 字段的空对象。
  const NotationProfilesRequest();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory NotationProfilesRequest.fromJson(Map<String, Object?> json) {
    return const NotationProfilesRequest();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'NotationProfilesRequest()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is NotationProfilesRequest;
  }

  @override
  int get hashCode => 0;
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

/// 读取必填键并交给 [decode]；缺键抛 [FormatException]。
T readValue<T>(Map<String, Object?> json, String key, T Function(Object?) decode) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填键: $key');
  }
  return decode(json[key]);
}
