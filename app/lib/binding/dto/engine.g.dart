// GENERATED CODE - DO NOT MODIFY BY HAND.
// generator: CORE-67 v1
// source: manifest=manifest.json; schemas=engine.check.schema.json, engine.export.schema.json, engine.generation.schema.json, engine.parse.schema.json, engine.wait_generation.schema.json
// dart format off

import 'types.g.dart';

/// 共享别名 EngineCheckOk：wire 形状与 CheckResponse 相同。
typedef EngineCheckOk = CheckResponse;

/// EngineCheckRequest：不可变值对象；wire 键见各字段。
final class EngineCheckRequest {
  /// 由 wire 字段构造。
  const EngineCheckRequest({
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
  factory EngineCheckRequest.fromJson(Map<String, Object?> json) {
    return EngineCheckRequest(
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
    return 'EngineCheckRequest(empirical: $empirical, notationProfileId: $notationProfileId, source: $source, userDecls: $userDecls)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is EngineCheckRequest &&
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

/// EngineExportOk：不可变值对象；wire 键见各字段。
final class EngineExportOk {
  /// 由 wire 字段构造。
  const EngineExportOk({
    required this.text,
  });

  /// wire 键 text。
  final String text;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory EngineExportOk.fromJson(Map<String, Object?> json) {
    return EngineExportOk(
      text: readString(json, 'text'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'text': text,
    };
  }

  @override
  String toString() {
    return 'EngineExportOk(text: $text)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is EngineExportOk &&
        dtoEquals(text, other.text);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(text),
  ]);
}

/// EngineExportRequest：不可变值对象；wire 键见各字段。
final class EngineExportRequest {
  /// 由 wire 字段构造。
  const EngineExportRequest({
    required this.format,
    required this.revisionAst,
    required this.symbols,
  });

  /// wire 键 format。
  final EngineExportRequestFormat format;

  /// wire 键 revision_ast。
  final FormulaNode revisionAst;

  /// wire 键 symbols。
  final SymbolEnv symbols;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory EngineExportRequest.fromJson(Map<String, Object?> json) {
    return EngineExportRequest(
      format: readEnum(json, 'format', EngineExportRequestFormat.fromWire),
      revisionAst: readValue(json, 'revision_ast', FormulaNode.fromJson),
      symbols: readObject(json, 'symbols', SymbolEnv.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'format': format.wire,
      'revision_ast': revisionAst.toJson(),
      'symbols': symbols.toJson(),
    };
  }

  @override
  String toString() {
    return 'EngineExportRequest(format: $format, revisionAst: $revisionAst, symbols: $symbols)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is EngineExportRequest &&
        dtoEquals(format, other.format) &&
        dtoEquals(revisionAst, other.revisionAst) &&
        dtoEquals(symbols, other.symbols);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(format),
    dtoHash(revisionAst),
    dtoHash(symbols),
  ]);
}

/// 枚举 EngineExportRequestFormat：wire 取值为 [wire]。
enum EngineExportRequestFormat {
  /// wire 取值 latex。
  latex('latex'),
  /// wire 取值 unicode。
  unicode('unicode');

  const EngineExportRequestFormat(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, EngineExportRequestFormat> byWire = <String, EngineExportRequestFormat>{
    'latex': EngineExportRequestFormat.latex,
    'unicode': EngineExportRequestFormat.unicode,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static EngineExportRequestFormat fromWire(String wire) {
    final EngineExportRequestFormat? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 EngineExportRequestFormat wire 取值: $wire');
    }
    return found;
  }
}

/// EngineGenerationOk：不可变值对象；wire 键见各字段。
final class EngineGenerationOk {
  /// 由 wire 字段构造。
  const EngineGenerationOk({
    required this.available,
    required this.generation,
  });

  /// wire 键 available。
  final bool available;

  /// wire 键 generation。
  final String generation;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory EngineGenerationOk.fromJson(Map<String, Object?> json) {
    return EngineGenerationOk(
      available: readBool(json, 'available'),
      generation: readString(json, 'generation'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'available': available,
      'generation': generation,
    };
  }

  @override
  String toString() {
    return 'EngineGenerationOk(available: $available, generation: $generation)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is EngineGenerationOk &&
        dtoEquals(available, other.available) &&
        dtoEquals(generation, other.generation);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(available),
    dtoHash(generation),
  ]);
}

/// EngineGenerationRequest：不可变值对象；wire 键见各字段。
final class EngineGenerationRequest {
  /// 无 wire 字段的空对象。
  const EngineGenerationRequest();

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory EngineGenerationRequest.fromJson(Map<String, Object?> json) {
    return const EngineGenerationRequest();
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
    };
  }

  @override
  String toString() {
    return 'EngineGenerationRequest()';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is EngineGenerationRequest;
  }

  @override
  int get hashCode => 0;
}

/// EngineParseOk：不可变值对象；wire 键见各字段。
final class EngineParseOk {
  /// 由 wire 字段构造。
  const EngineParseOk({
    required this.ast,
    required this.diagnostics,
    required this.rawSymbols,
    required this.sourceMap,
  });

  /// wire 键 ast。
  final FormulaNode? ast;

  /// wire 键 diagnostics。
  final List<Diagnostic> diagnostics;

  /// wire 键 raw_symbols。
  final List<RawSymbol> rawSymbols;

  /// wire 键 source_map。
  final SourceMap sourceMap;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory EngineParseOk.fromJson(Map<String, Object?> json) {
    return EngineParseOk(
      ast: readValuePresent(json, 'ast', FormulaNode.fromJson),
      diagnostics: readList(json, 'diagnostics', (Object? value) => Diagnostic.fromJson(asObject(value))),
      rawSymbols: readList(json, 'raw_symbols', (Object? value) => RawSymbol.fromJson(asObject(value))),
      sourceMap: readList(json, 'source_map', (Object? value) => SourceSpan.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'ast': ast?.toJson(),
      'diagnostics': encodeList(diagnostics, (Diagnostic item) => item.toJson()),
      'raw_symbols': encodeList(rawSymbols, (RawSymbol item) => item.toJson()),
      'source_map': encodeList(sourceMap, (SourceSpan item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'EngineParseOk(ast: $ast, diagnostics: $diagnostics, rawSymbols: $rawSymbols, sourceMap: $sourceMap)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is EngineParseOk &&
        dtoEquals(ast, other.ast) &&
        dtoEquals(diagnostics, other.diagnostics) &&
        dtoEquals(rawSymbols, other.rawSymbols) &&
        dtoEquals(sourceMap, other.sourceMap);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(ast),
    dtoHash(diagnostics),
    dtoHash(rawSymbols),
    dtoHash(sourceMap),
  ]);
}

/// EngineParseRequest：不可变值对象；wire 键见各字段。
final class EngineParseRequest {
  /// 由 wire 字段构造。
  const EngineParseRequest({
    this.allowUnicode,
    required this.source,
  });

  /// wire 键 allow_unicode。
  final bool? allowUnicode;

  /// wire 键 source。
  final String source;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory EngineParseRequest.fromJson(Map<String, Object?> json) {
    return EngineParseRequest(
      allowUnicode: readBoolOrNull(json, 'allow_unicode'),
      source: readString(json, 'source'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'allow_unicode': allowUnicode,
      'source': source,
    };
  }

  @override
  String toString() {
    return 'EngineParseRequest(allowUnicode: $allowUnicode, source: $source)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is EngineParseRequest &&
        dtoEquals(allowUnicode, other.allowUnicode) &&
        dtoEquals(source, other.source);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(allowUnicode),
    dtoHash(source),
  ]);
}

/// EngineWaitGenerationOk：不可变值对象；wire 键见各字段。
final class EngineWaitGenerationOk {
  /// 由 wire 字段构造。
  const EngineWaitGenerationOk({
    required this.available,
    required this.changed,
    required this.generation,
  });

  /// wire 键 available。
  final bool available;

  /// wire 键 changed。
  final bool changed;

  /// wire 键 generation。
  final String generation;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory EngineWaitGenerationOk.fromJson(Map<String, Object?> json) {
    return EngineWaitGenerationOk(
      available: readBool(json, 'available'),
      changed: readBool(json, 'changed'),
      generation: readString(json, 'generation'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'available': available,
      'changed': changed,
      'generation': generation,
    };
  }

  @override
  String toString() {
    return 'EngineWaitGenerationOk(available: $available, changed: $changed, generation: $generation)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is EngineWaitGenerationOk &&
        dtoEquals(available, other.available) &&
        dtoEquals(changed, other.changed) &&
        dtoEquals(generation, other.generation);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(available),
    dtoHash(changed),
    dtoHash(generation),
  ]);
}

/// EngineWaitGenerationRequest：不可变值对象；wire 键见各字段。
final class EngineWaitGenerationRequest {
  /// 由 wire 字段构造。
  const EngineWaitGenerationRequest({
    required this.after,
    required this.waitMs,
  });

  /// wire 键 after。
  final String after;

  /// wire 键 wait_ms。
  final int waitMs;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory EngineWaitGenerationRequest.fromJson(Map<String, Object?> json) {
    return EngineWaitGenerationRequest(
      after: readString(json, 'after'),
      waitMs: readInt(json, 'wait_ms'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'after': after,
      'wait_ms': waitMs,
    };
  }

  @override
  String toString() {
    return 'EngineWaitGenerationRequest(after: $after, waitMs: $waitMs)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is EngineWaitGenerationRequest &&
        dtoEquals(after, other.after) &&
        dtoEquals(waitMs, other.waitMs);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(after),
    dtoHash(waitMs),
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

/// 严格读取 bool 字段。
bool readBool(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is bool) return value;
  throw FormatException('字段 ' + key + ' 应为 bool');
}

/// 读取可空 bool 字段。
bool? readBoolOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is bool) return value;
  throw FormatException('字段 ' + key + ' 应为 bool 或 null');
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

/// 读取可空键并交给 [decode]；缺键或显式 null 返回 null。
T? readValueOrNull<T>(
    Map<String, Object?> json, String key, T Function(Object?) decode) {
  final Object? value = json[key];
  return value == null ? null : decode(value);
}

/// 必填且可空：缺键抛 [FormatException]，显式 null 通过。
T? readValuePresent<T>(
    Map<String, Object?> json, String key, T Function(Object?) decode) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填键: $key');
  }
  return readValueOrNull<T>(json, key, decode);
}
