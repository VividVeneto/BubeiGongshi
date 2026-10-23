// GENERATED CODE - DO NOT MODIFY BY HAND.
// generator: CORE-67 v1
// source: manifest=manifest.json; schemas=typeset.glyph_outlines.schema.json, typeset.layout.schema.json
// dart format off

import 'types.g.dart';

/// TypesetGlyphOutlinesOk：不可变值对象；wire 键见各字段。
final class TypesetGlyphOutlinesOk {
  /// 由 wire 字段构造。
  const TypesetGlyphOutlinesOk({
    required this.outlines,
    required this.unitsPerEm,
  });

  /// wire 键 outlines。
  final List<TypesetGlyphOutlinesOkOutlines> outlines;

  /// wire 键 units_per_em。
  final int unitsPerEm;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory TypesetGlyphOutlinesOk.fromJson(Map<String, Object?> json) {
    return TypesetGlyphOutlinesOk(
      outlines: readList(json, 'outlines', (Object? value) => TypesetGlyphOutlinesOkOutlines.fromJson(asObject(value))),
      unitsPerEm: readInt(json, 'units_per_em'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'outlines': encodeList(outlines, (TypesetGlyphOutlinesOkOutlines item) => item.toJson()),
      'units_per_em': unitsPerEm,
    };
  }

  @override
  String toString() {
    return 'TypesetGlyphOutlinesOk(outlines: $outlines, unitsPerEm: $unitsPerEm)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is TypesetGlyphOutlinesOk &&
        dtoEquals(outlines, other.outlines) &&
        dtoEquals(unitsPerEm, other.unitsPerEm);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(outlines),
    dtoHash(unitsPerEm),
  ]);
}

/// TypesetGlyphOutlinesOkOutlines：不可变值对象；wire 键见各字段。
final class TypesetGlyphOutlinesOkOutlines {
  /// 由 wire 字段构造。
  const TypesetGlyphOutlinesOkOutlines({
    required this.glyphId,
    required this.segs,
  });

  /// wire 键 glyph_id。
  final int glyphId;

  /// wire 键 segs。
  final List<PathSeg> segs;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory TypesetGlyphOutlinesOkOutlines.fromJson(Map<String, Object?> json) {
    return TypesetGlyphOutlinesOkOutlines(
      glyphId: readInt(json, 'glyph_id'),
      segs: readList(json, 'segs', (Object? value) => PathSeg.fromJson(value)),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'glyph_id': glyphId,
      'segs': encodeList(segs, (PathSeg item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'TypesetGlyphOutlinesOkOutlines(glyphId: $glyphId, segs: $segs)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is TypesetGlyphOutlinesOkOutlines &&
        dtoEquals(glyphId, other.glyphId) &&
        dtoEquals(segs, other.segs);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(glyphId),
    dtoHash(segs),
  ]);
}

/// TypesetGlyphOutlinesRequest：不可变值对象；wire 键见各字段。
final class TypesetGlyphOutlinesRequest {
  /// 由 wire 字段构造。
  const TypesetGlyphOutlinesRequest({
    required this.fontId,
    required this.glyphIds,
  });

  /// wire 键 font_id。
  final String fontId;

  /// wire 键 glyph_ids。
  final List<int> glyphIds;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory TypesetGlyphOutlinesRequest.fromJson(Map<String, Object?> json) {
    return TypesetGlyphOutlinesRequest(
      fontId: readString(json, 'font_id'),
      glyphIds: readList(json, 'glyph_ids', (Object? value) => asInt(value)),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'font_id': fontId,
      'glyph_ids': glyphIds,
    };
  }

  @override
  String toString() {
    return 'TypesetGlyphOutlinesRequest(fontId: $fontId, glyphIds: $glyphIds)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is TypesetGlyphOutlinesRequest &&
        dtoEquals(fontId, other.fontId) &&
        dtoEquals(glyphIds, other.glyphIds);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(fontId),
    dtoHash(glyphIds),
  ]);
}

/// 共享别名 TypesetLayoutOk：wire 形状与 DisplayList 相同。
typedef TypesetLayoutOk = DisplayList;

/// TypesetLayoutRequest：不可变值对象；wire 键见各字段。
final class TypesetLayoutRequest {
  /// 由 wire 字段构造。
  const TypesetLayoutRequest({
    required this.ast,
    required this.options,
    required this.symbols,
  });

  /// wire 键 ast。
  final FormulaNode ast;

  /// wire 键 options。
  final LayoutOptions options;

  /// wire 键 symbols。
  final SymbolEnv symbols;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory TypesetLayoutRequest.fromJson(Map<String, Object?> json) {
    return TypesetLayoutRequest(
      ast: readValue(json, 'ast', FormulaNode.fromJson),
      options: readObject(json, 'options', LayoutOptions.fromJson),
      symbols: readObject(json, 'symbols', SymbolEnv.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'ast': ast.toJson(),
      'options': options.toJson(),
      'symbols': symbols.toJson(),
    };
  }

  @override
  String toString() {
    return 'TypesetLayoutRequest(ast: $ast, options: $options, symbols: $symbols)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is TypesetLayoutRequest &&
        dtoEquals(ast, other.ast) &&
        dtoEquals(options, other.options) &&
        dtoEquals(symbols, other.symbols);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(ast),
    dtoHash(options),
    dtoHash(symbols),
  ]);
}

/// 把 JSON 值收成 int。
int asInt(Object? value) {
  if (value is int) return value;
  throw const FormatException('元素应为 int');
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
