// CORE-02 阶段2：错误信封桥（手写文件，非生成物）。
//
// 本文件只负责两件事：
// 1. 用 CORE-67 生成的诊断 DTO 承载诊断，并导出契约要求的 `DiagnosticDto` 别名
//    （ADR-V5-58 ⑧：别名指向生成类，不另建第二个类）；
// 2. 按 CORE-03 把根错误信封 `{error: {...}}` 校验后投影为 [FmlException]。
//
// 诊断元素的字段解析、未声明键忽略与 JSON 编码全部由
// `app/lib/binding/dto/types.g.dart` 的生成类 `Diagnostic` 完成；本文件只补
// 生成 schema 不承诺的 u32 区间与 recovery 派生校验，不复制、不改名、不收紧
// 诊断内部字段的未知键规则（ADR-V5-58 ②⑧）。

import 'dart:math';

import 'dto/types.g.dart';
import 'error_codes.g.dart';

/// CORE-67 生成的诊断 DTO 的类型别名。
///
/// 指向 `app/lib/binding/dto/types.g.dart` 中的生成类 `Diagnostic`，字段与 CORE-02
/// 契约中的诊断对象一一对应；本卡不再复制第二个诊断类，也不改其类名。
typedef DiagnosticDto = Diagnostic;

/// 公式核心错误的 Dart 侧表示（CORE-02 阶段2）。
///
/// 由 CORE-03 的错误信封经 [FmlException.fromJson] 投影而来，或由调用方用已登记的
/// 错误码直接构造。[retryable] 只取自 `error_codes.g.dart` 的生成表，不接受外部覆盖。
class FmlException implements Exception {
  /// 用已登记的错误码 [code] 构造异常。
  ///
  /// [diagnostics] 按给定顺序保留，并复制为不可修改列表；[traceId] 省略时用
  /// [Random.secure] 生成 32 位小写十六进制且非全零的值。
  ///
  /// [code] 未在 `error_codes.g.dart` 登记、[traceId] 不是 32 位小写十六进制
  /// 或全零、[diagnostics] 含非 [DiagnosticDto] 元素时抛 [ArgumentError]。
  FmlException(
    String code, {
    List<DiagnosticDto> diagnostics = const <DiagnosticDto>[],
    String? traceId,
  }) : code = _checkedCode(code),
       diagnostics = _checkedDiagnostics(diagnostics),
       traceId = traceId == null ? _newTraceId() : _checkedTraceId(traceId),
       retryable = _metaOf(code).retryable;

  /// 从 CORE-03 的根错误信封 `{error: {...}}` 构造异常。
  ///
  /// 以下载荷问题抛 [FormatException]，且异常消息不显示原始载荷：缺少 `error`
  /// 对象或它不是对象、`error` 对象层出现未声明字段、必填字段缺失或类型不符、
  /// 错误码未登记、`domain` 或 `retryable` 与生成表不一致、`trace_id` 不是
  /// 32 位小写十六进制或全零、诊断元素不是对象、诊断自身 `code` 未登记或
  /// `severity` 与生成表不一致、`input_range` 越界或倒序、`recovery` 未按
  /// `message_key + ".fix"` 派生或该码未声明 `fix_hint`。
  ///
  /// 诊断对象内部的未声明键由生成类 `Diagnostic.fromJson` 忽略（CORE-67 规则）。
  factory FmlException.fromJson(Map<String, Object?> json) {
    final Map<String, Object?> error = _errorEnvelope(json);
    final String code = _requiredString(error, 'code');
    final String domain = _requiredString(error, 'domain');
    final bool retryable = _requiredBool(error, 'retryable');
    final String traceId = _requiredString(error, 'trace_id');
    final List<Object?> rawDiagnostics = _requiredList(error, 'diagnostics');
    final ErrorCodeMeta meta = _payloadMeta(code);
    if (domain != meta.domain) {
      throw const FormatException('error.domain 与生成表不一致');
    }
    if (retryable != meta.retryable) {
      throw const FormatException('error.retryable 与生成表不一致');
    }
    if (!_isValidTraceId(traceId)) {
      throw const FormatException('error.trace_id 必须是 32 位小写十六进制且非全零');
    }
    return FmlException(
      code,
      diagnostics: _parsedDiagnostics(rawDiagnostics),
      traceId: traceId,
    );
  }

  /// 已登记的稳定错误码。
  final String code;

  /// 按 wire 顺序保留的诊断列表；构造后不可修改。
  final List<DiagnosticDto> diagnostics;

  /// 出错链路的 trace id：32 位小写十六进制，永不全零。
  final String traceId;

  /// 是否可重试，只由生成表 `error_codes.g.dart` 决定。
  final bool retryable;

  @override
  String toString() =>
      'FmlException(code: $code, retryable: $retryable, '
      'traceId: $traceId, diagnostics: ${diagnostics.length})';
}

/// CORE-03 错误信封 `error` 对象允许出现的字段（ADR-V5-58 ②）。
const Set<String> _errorKeys = <String>{
  'code',
  'domain',
  'retryable',
  'trace_id',
  'diagnostics',
};

/// u32 上界（2^32 - 1），`input_range` 两端都不得超过。
const int _maxInputRange = 4294967295;

/// 全零 trace id 的规范写法：任何出边界输出都不得使用。
const String _zeroTraceId = '00000000000000000000000000000000';

/// trace id 的唯一合法形状。
final RegExp _traceIdPattern = RegExp(r'^[0-9a-f]{32}$');

/// 生成表的按码索引；生成物只提供有序列表，不提供查找函数。
final Map<String, ErrorCodeMeta> _registryByCode = <String, ErrorCodeMeta>{
  for (final ErrorCodeMeta meta in errorCodeRegistry) meta.code: meta,
};

/// 生成 trace id 的随机源；只用于填充调用方未给出的 trace id。
final Random _random = Random.secure();

/// 构造器路径：未登记的 [code] 属于调用方编程错误，抛 [ArgumentError]。
String _checkedCode(String code) {
  if (!_registryByCode.containsKey(code)) {
    throw ArgumentError('错误码未在 error_codes.g.dart 登记');
  }
  return code;
}

/// 取生成表中登记的错误码元数据；未登记时抛 [ArgumentError]。
ErrorCodeMeta _metaOf(String code) {
  final ErrorCodeMeta? meta = _registryByCode[code];
  if (meta == null) {
    throw ArgumentError('错误码未在 error_codes.g.dart 登记');
  }
  return meta;
}

/// 工厂路径：载荷里的错误码未登记属于载荷问题，抛 [FormatException]。
ErrorCodeMeta _payloadMeta(String code) {
  final ErrorCodeMeta? meta = _registryByCode[code];
  if (meta == null) {
    throw const FormatException('error.code 未在生成表中登记');
  }
  return meta;
}

/// 复制并冻结诊断列表；元素类型不符转 [ArgumentError]。
List<DiagnosticDto> _checkedDiagnostics(List<DiagnosticDto> diagnostics) {
  final List<DiagnosticDto> copy = <DiagnosticDto>[];
  try {
    for (final DiagnosticDto diagnostic in diagnostics) {
      copy.add(diagnostic);
    }
  } on TypeError {
    throw ArgumentError('diagnostics 的元素必须是 DiagnosticDto');
  }
  return List<DiagnosticDto>.unmodifiable(copy);
}

/// 校验调用方给出的 trace id。
String _checkedTraceId(String traceId) {
  if (!_isValidTraceId(traceId)) {
    throw ArgumentError('traceId 必须是 32 位小写十六进制且非全零');
  }
  return traceId;
}

/// 生成一个新的非零 trace id。
String _newTraceId() {
  final StringBuffer buffer = StringBuffer();
  do {
    buffer.clear();
    for (int i = 0; i < 16; i++) {
      buffer.write(_random.nextInt(256).toRadixString(16).padLeft(2, '0'));
    }
  } while (buffer.toString() == _zeroTraceId);
  return buffer.toString();
}

/// trace id 是否合法：32 位小写十六进制且非全零。
bool _isValidTraceId(String traceId) =>
    _traceIdPattern.hasMatch(traceId) && traceId != _zeroTraceId;

/// 取根信封中的 `error` 对象并拒绝未声明字段。
Map<String, Object?> _errorEnvelope(Map<String, Object?> json) {
  final Object? raw = json['error'];
  final Map<String, Object?> error;
  if (raw is Map<String, Object?>) {
    error = raw;
  } else if (raw is Map<Object?, Object?>) {
    final Map<String, Object?> converted = <String, Object?>{};
    for (final MapEntry<Object?, Object?> entry in raw.entries) {
      final Object? key = entry.key;
      if (key is! String) {
        throw const FormatException('error 对象的键必须是字符串');
      }
      converted[key] = entry.value;
    }
    error = converted;
  } else {
    throw const FormatException('载荷缺少 error 对象');
  }
  for (final String key in error.keys) {
    if (!_errorKeys.contains(key)) {
      throw FormatException('error 对象包含未声明字段: $key');
    }
  }
  return error;
}

/// 读取必填字符串字段。
String _requiredString(Map<String, Object?> map, String key) {
  final Object? value = map[key];
  if (value is! String) {
    throw FormatException('error.$key 缺失或不是字符串');
  }
  return value;
}

/// 读取必填布尔字段。
bool _requiredBool(Map<String, Object?> map, String key) {
  final Object? value = map[key];
  if (value is! bool) {
    throw FormatException('error.$key 缺失或不是布尔值');
  }
  return value;
}

/// 读取必填数组字段。
List<Object?> _requiredList(Map<String, Object?> map, String key) {
  final Object? value = map[key];
  if (value is! List<Object?>) {
    throw FormatException('error.$key 缺失或不是数组');
  }
  return value;
}

/// 逐条解析并校验诊断；诊断内部字段交给生成类。
List<DiagnosticDto> _parsedDiagnostics(List<Object?> rawDiagnostics) {
  final List<DiagnosticDto> parsed = <DiagnosticDto>[];
  for (final Object? element in rawDiagnostics) {
    if (element is! Map<String, Object?>) {
      throw const FormatException('error.diagnostics 的元素必须是对象');
    }
    final DiagnosticDto diagnostic = Diagnostic.fromJson(element);
    _checkDiagnostic(diagnostic);
    parsed.add(diagnostic);
  }
  return List<DiagnosticDto>.unmodifiable(parsed);
}

/// 校验诊断自身的错误码、severity、区间与 recovery 派生。
void _checkDiagnostic(DiagnosticDto diagnostic) {
  final ErrorCodeMeta? meta = _registryByCode[diagnostic.code];
  if (meta == null) {
    throw const FormatException('诊断 code 未在生成表中登记');
  }
  if (diagnostic.severity.wire != meta.severity) {
    throw const FormatException('诊断 severity 与生成表不一致');
  }
  final DiagnosticInputRange? range = diagnostic.inputRange;
  if (range != null && !_isValidRange(range)) {
    throw const FormatException('input_range 越界或倒序');
  }
  final String? recovery = diagnostic.recovery;
  if (recovery != null) {
    if (!meta.fixHint) {
      throw const FormatException('该错误码未声明 fix_hint，诊断不得给出 recovery');
    }
    if (recovery != '${meta.messageKey}.fix') {
      throw const FormatException('recovery 必须等于 message_key + ".fix"');
    }
  }
}

/// `input_range` 必须是 u32 闭区间：0 <= start <= end <= 4294967295。
bool _isValidRange(DiagnosticInputRange range) {
  final int start = range.$1;
  final int end = range.$2;
  return start >= 0 && start <= end && end <= _maxInputRange;
}
