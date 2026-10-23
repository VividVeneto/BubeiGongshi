// CORE-02 阶段2 行为测试（T-11 / T-12）。
//
// 覆盖构造器与工厂的异常类型边界、生成表投影、诊断 u32 区间与 recovery 派生、
// `DiagnosticDto` 别名的来源，以及 contracts/vectors/errors-v1.json 的共享向量。

import 'dart:convert';
import 'dart:io';

import 'package:bubeigongshi/binding/dto/types.g.dart';
import 'package:bubeigongshi/binding/error_codes.g.dart';
import 'package:bubeigongshi/binding/errors.dart';
import 'package:flutter_test/flutter_test.dart';

/// 合法 trace id 样例（共享向量使用的值）。
const String _validTraceId = '3f8b2c1d4e5f60718293a4b5c6d7e8f9';

/// 全零 trace id：Rust 领域正例，跨出边界必须被 Dart 侧拒绝。
const String _zeroTraceId = '00000000000000000000000000000000';

/// trace id 唯一合法形状。
final RegExp _traceIdPattern = RegExp(r'^[0-9a-f]{32}$');

/// 读取 app 包内文件（测试进程工作目录是 `app/`）。
String _readAppFile(String relativePath) =>
    File(relativePath).readAsStringSync();

/// 取生成表中登记的错误码元数据。
ErrorCodeMeta _meta(String code) =>
    errorCodeRegistry.firstWhere((ErrorCodeMeta meta) => meta.code == code);

/// 构造一条字段齐全的诊断 wire 对象。
Map<String, Object?> _diagnostic({
  String code = 'TYPE_DIM_CONFLICT',
  String severity = 'error',
  Map<String, Object?> args = const <String, Object?>{},
  List<Object?>? inputRange,
  String? nodePath = '0.2.1',
  String? recovery,
  bool needsConfirm = false,
  Map<String, Object?> extra = const <String, Object?>{},
}) {
  return <String, Object?>{
    'code': code,
    'severity': severity,
    'args': args,
    'needs_confirm': needsConfirm,
    if (inputRange != null) 'input_range': inputRange,
    if (nodePath != null) 'node_path': nodePath,
    if (recovery != null) 'recovery': recovery,
    ...extra,
  };
}

/// 构造规范错误对象的 wire 数据。
Map<String, Object?> _errorObject({
  String code = 'TYPE_DIM_CONFLICT',
  String? domain,
  bool? retryable,
  String traceId = _validTraceId,
  List<Object?> diagnostics = const <Object?>[],
  Map<String, Object?> extra = const <String, Object?>{},
}) {
  final ErrorCodeMeta meta = _meta(code);
  return <String, Object?>{
    'code': code,
    'domain': domain ?? meta.domain,
    'retryable': retryable ?? meta.retryable,
    'trace_id': traceId,
    'diagnostics': diagnostics,
    ...extra,
  };
}

/// 把错误对象包进根信封。
Map<String, Object?> _envelope(Map<String, Object?> error) => <String, Object?>{
  'error': error,
};

/// 断言 `input_range` 被拒绝，并确认拒绝理由是区间校验而非必填键。
void _expectRangeRejected(List<Object?> range) {
  Object? caught;
  try {
    FmlException.fromJson(
      _envelope(
        _errorObject(diagnostics: <Object?>[_diagnostic(inputRange: range)]),
      ),
    );
  } catch (error) {
    caught = error;
  }
  expect(caught, isA<FormatException>(), reason: '$range');
  expect(
    (caught! as FormatException).message,
    contains('input_range'),
    reason: '$range',
  );
}

void main() {
  group('构造器', () {
    test('SYNC_NOT_AVAILABLE 的 retryable 取生成表，traceId 非零且两次不同', () {
      final FmlException first = FmlException('SYNC_NOT_AVAILABLE');
      final FmlException second = FmlException('SYNC_NOT_AVAILABLE');
      expect(_meta('SYNC_NOT_AVAILABLE').retryable, isFalse);
      expect(first.retryable, isFalse);
      expect(first.retryable, _meta('SYNC_NOT_AVAILABLE').retryable);
      expect(first.traceId, matches(_traceIdPattern));
      expect(first.traceId, isNot(_zeroTraceId));
      expect(second.traceId, isNot(first.traceId));
      expect(first.diagnostics, isEmpty);
    });

    test('每个登记错误码的 retryable 都与生成表一致', () {
      expect(errorCodeRegistry.length, greaterThanOrEqualTo(200));
      for (final ErrorCodeMeta meta in errorCodeRegistry) {
        expect(
          FmlException(meta.code).retryable,
          meta.retryable,
          reason: meta.code,
        );
      }
      expect(_meta('FFI_BUSY').retryable, isTrue);
      expect(FmlException('FFI_BUSY').retryable, isTrue);
    });

    test('显式 traceId 保留，诊断保序、复制且不可修改', () {
      const DiagnosticDto firstDiagnostic = Diagnostic(
        args: <String, String>{'left': 'm'},
        code: 'TYPE_DIM_CONFLICT',
        needsConfirm: false,
        severity: DiagnosticSeverity.error,
      );
      const DiagnosticDto secondDiagnostic = Diagnostic(
        args: <String, String>{},
        code: 'TYPE_DIM_CONFLICT',
        needsConfirm: true,
        severity: DiagnosticSeverity.warning,
      );
      final List<DiagnosticDto> source = <DiagnosticDto>[
        firstDiagnostic,
        secondDiagnostic,
      ];
      final FmlException error = FmlException(
        'TYPE_DIM_CONFLICT',
        diagnostics: source,
        traceId: _validTraceId,
      );
      expect(error.traceId, _validTraceId);
      expect(error.diagnostics, hasLength(2));
      expect(error.diagnostics.first.needsConfirm, isFalse);
      expect(error.diagnostics.last.needsConfirm, isTrue);
      expect(error.diagnostics.last.severity, DiagnosticSeverity.warning);
      source.clear();
      expect(error.diagnostics, hasLength(2));
      expect(
        () => error.diagnostics.add(firstDiagnostic),
        throwsUnsupportedError,
      );
    });

    test('构造器非法参数抛 ArgumentError', () {
      expect(() => FmlException('NO_SUCH_CODE'), throwsArgumentError);
      expect(
        () => FmlException(
          'AST_JSON_INVALID',
          traceId: '3F8B2C1D4E5F60718293A4B5C6D7E8F9',
        ),
        throwsArgumentError,
      );
      expect(
        () => FmlException('AST_JSON_INVALID', traceId: _zeroTraceId),
        throwsArgumentError,
      );
      expect(
        () => FmlException('AST_JSON_INVALID', traceId: '3f8b2c1d'),
        throwsArgumentError,
      );
      expect(
        () => FmlException('AST_JSON_INVALID', traceId: '${_validTraceId}0'),
        throwsArgumentError,
      );
      final List<DiagnosticDto> mixed = <Object?>['not-a-diagnostic']
          .cast<DiagnosticDto>();
      expect(
        () => FmlException('AST_JSON_INVALID', diagnostics: mixed),
        throwsArgumentError,
      );
    });
  });

  group('fromJson 正例', () {
    test('根信封解析成功并与生成表一致', () {
      final FmlException error = FmlException.fromJson(
        _envelope(
          _errorObject(
            diagnostics: <Object?>[
              _diagnostic(
                inputRange: <Object?>[4, 9],
                args: <String, Object?>{'left': 'L', 'right': 'L T^-1'},
                recovery: 'err.type.dim_conflict.fix',
                needsConfirm: true,
              ),
            ],
          ),
        ),
      );
      expect(error.code, 'TYPE_DIM_CONFLICT');
      expect(error.retryable, _meta('TYPE_DIM_CONFLICT').retryable);
      expect(error.retryable, isFalse);
      expect(error.traceId, _validTraceId);
      expect(error.diagnostics, hasLength(1));
      final DiagnosticDto diagnostic = error.diagnostics.single;
      expect(diagnostic.code, 'TYPE_DIM_CONFLICT');
      expect(diagnostic.severity, DiagnosticSeverity.error);
      expect(diagnostic.nodePath, '0.2.1');
      expect(diagnostic.inputRange, (4, 9));
      expect(diagnostic.args, <String, String>{'left': 'L', 'right': 'L T^-1'});
      expect(diagnostic.recovery, 'err.type.dim_conflict.fix');
      expect(diagnostic.needsConfirm, isTrue);
      expect(() => error.diagnostics.add(diagnostic), throwsUnsupportedError);
    });

    test('空诊断与缺省可选字段可解析', () {
      final FmlException empty = FmlException.fromJson(
        _envelope(_errorObject(code: 'PARSE_SYNTAX')),
      );
      expect(empty.diagnostics, isEmpty);
      final FmlException error = FmlException.fromJson(
        _envelope(
          _errorObject(
            code: 'PARSE_SYNTAX',
            diagnostics: <Object?>[
              _diagnostic(code: 'PARSE_SYNTAX', nodePath: null),
            ],
          ),
        ),
      );
      final DiagnosticDto diagnostic = error.diagnostics.single;
      expect(diagnostic.nodePath, isNull);
      expect(diagnostic.inputRange, isNull);
      expect(diagnostic.recovery, isNull);
      expect(diagnostic.args, isEmpty);
    });
  });

  group('fromJson 载荷问题抛 FormatException', () {
    test('缺少 error 对象或类型不符', () {
      expect(
        () => FmlException.fromJson(<String, Object?>{}),
        throwsFormatException,
      );
      expect(
        () => FmlException.fromJson(<String, Object?>{'error': null}),
        throwsFormatException,
      );
      expect(
        () => FmlException.fromJson(<String, Object?>{'error': 'error'}),
        throwsFormatException,
      );
      expect(
        () => FmlException.fromJson(<String, Object?>{'error': <Object?>[]}),
        throwsFormatException,
      );
    });

    test('error 对象缺必填字段', () {
      for (final String key in <String>[
        'code',
        'domain',
        'retryable',
        'trace_id',
        'diagnostics',
      ]) {
        final Map<String, Object?> error = _errorObject();
        error.remove(key);
        expect(
          () => FmlException.fromJson(_envelope(error)),
          throwsFormatException,
          reason: key,
        );
      }
    });

    test('error 对象字段类型不符', () {
      final Map<String, Object?> overrides = <String, Object?>{
        'code': 1,
        'domain': 1,
        'retryable': 'false',
        'trace_id': 1,
        'diagnostics': <String, Object?>{},
      };
      for (final MapEntry<String, Object?> entry in overrides.entries) {
        final Map<String, Object?> error = _errorObject();
        error[entry.key] = entry.value;
        expect(
          () => FmlException.fromJson(_envelope(error)),
          throwsFormatException,
          reason: entry.key,
        );
      }
    });

    test('未登记 code 或 domain / retryable 与生成表不一致', () {
      expect(
        () => FmlException.fromJson(
          _envelope(<String, Object?>{
            'code': 'NO_SUCH_CODE',
            'domain': 'ast',
            'retryable': false,
            'trace_id': _validTraceId,
            'diagnostics': <Object?>[],
          }),
        ),
        throwsFormatException,
      );
      expect(
        () => FmlException.fromJson(_envelope(_errorObject(domain: 'eval'))),
        throwsFormatException,
      );
      expect(
        () => FmlException.fromJson(
          _envelope(_errorObject(code: 'FFI_BUSY', retryable: false)),
        ),
        throwsFormatException,
      );
    });

    test('error 对象层出现未声明字段', () {
      expect(
        () => FmlException.fromJson(
          _envelope(
            _errorObject(
              extra: <String, Object?>{'condition': 'type_mismatch'},
            ),
          ),
        ),
        throwsFormatException,
      );
    });

    test('trace_id 形状不符或全零', () {
      final List<String> broken = <String>[
        '3F8B2C1D4E5F60718293A4B5C6D7E8F9',
        '3f8b2c1d',
        '${_validTraceId}0',
        '${_validTraceId.substring(1)}g',
        _zeroTraceId,
      ];
      for (final String traceId in broken) {
        expect(
          () =>
              FmlException.fromJson(_envelope(_errorObject(traceId: traceId))),
          throwsFormatException,
          reason: traceId,
        );
      }
    });

    test('诊断 severity 与自身错误码不一致', () {
      expect(
        () => FmlException.fromJson(
          _envelope(
            _errorObject(
              code: 'AST_JSON_INVALID',
              diagnostics: <Object?>[
                _diagnostic(code: 'AST_JSON_INVALID', severity: 'warning'),
              ],
            ),
          ),
        ),
        throwsFormatException,
      );
      expect(
        () => FmlException.fromJson(
          _envelope(
            _errorObject(
              code: 'AST_JSON_INVALID',
              diagnostics: <Object?>[
                _diagnostic(code: 'AST_JSON_INVALID', severity: 'bogus'),
              ],
            ),
          ),
        ),
        throwsFormatException,
      );
    });

    test('诊断 code 未在生成表登记', () {
      expect(
        () => FmlException.fromJson(
          _envelope(
            _errorObject(
              diagnostics: <Object?>[_diagnostic(code: 'NO_SUCH_CODE')],
            ),
          ),
        ),
        throwsFormatException,
      );
    });

    test('input_range 倒序、越界或负端点一律拒绝（含 B1 负端点）', () {
      for (final List<Object?> range in <List<Object?>>[
        <Object?>[10, 5],
        <Object?>[0, 4294967296],
        <Object?>[4294967296, 4294967296],
        <Object?>[-1, 5],
        <Object?>[-5, -2],
        <Object?>[-1, -5],
        <Object?>[0, -7],
      ]) {
        _expectRangeRejected(range);
      }
      for (final List<Object?> range in <List<Object?>>[
        <Object?>[0, 0],
        <Object?>[2, 5],
        <Object?>[0, 4294967295],
        <Object?>[4294967295, 4294967295],
      ]) {
        final FmlException error = FmlException.fromJson(
          _envelope(
            _errorObject(
              diagnostics: <Object?>[_diagnostic(inputRange: range)],
            ),
          ),
        );
        expect(error.diagnostics.single.inputRange, (
          range.first,
          range.last,
        ), reason: '$range');
      }
    });

    test('input_range 元素类型或长度不符', () {
      for (final List<Object?> range in <List<Object?>>[
        <Object?>[1],
        <Object?>[1, 2, 3],
        <Object?>['1', '2'],
        <Object?>[1.5, 2],
      ]) {
        expect(
          () => FmlException.fromJson(
            _envelope(
              _errorObject(
                diagnostics: <Object?>[_diagnostic(inputRange: range)],
              ),
            ),
          ),
          throwsFormatException,
          reason: '$range',
        );
      }
    });

    test('recovery 必须按 message_key 派生且该码声明 fix_hint', () {
      expect(
        () => FmlException.fromJson(
          _envelope(
            _errorObject(
              code: 'PARSE_SYNTAX',
              diagnostics: <Object?>[
                _diagnostic(
                  code: 'PARSE_SYNTAX',
                  recovery: 'err.parse.other.fix',
                ),
              ],
            ),
          ),
        ),
        throwsFormatException,
      );
      expect(
        () => FmlException.fromJson(
          _envelope(
            _errorObject(
              code: 'AST_JSON_INVALID',
              diagnostics: <Object?>[
                _diagnostic(
                  code: 'AST_JSON_INVALID',
                  recovery: 'err.ast.json_invalid.fix',
                ),
              ],
            ),
          ),
        ),
        throwsFormatException,
      );
      final FmlException accepted = FmlException.fromJson(
        _envelope(
          _errorObject(
            code: 'PARSE_SYNTAX',
            diagnostics: <Object?>[
              _diagnostic(
                code: 'PARSE_SYNTAX',
                recovery: 'err.parse.syntax.fix',
              ),
            ],
          ),
        ),
      );
      expect(accepted.diagnostics.single.recovery, 'err.parse.syntax.fix');
    });

    test('诊断元素不是对象或缺必填键', () {
      expect(
        () => FmlException.fromJson(
          _envelope(_errorObject(diagnostics: <Object?>['not-an-object'])),
        ),
        throwsFormatException,
      );
      final Map<String, Object?> withoutArgs = _diagnostic()..remove('args');
      expect(
        () => FmlException.fromJson(
          _envelope(_errorObject(diagnostics: <Object?>[withoutArgs])),
        ),
        throwsFormatException,
      );
    });

    test('诊断对象内部未声明键由生成类忽略', () {
      final FmlException error = FmlException.fromJson(
        _envelope(
          _errorObject(
            diagnostics: <Object?>[
              _diagnostic(
                extra: <String, Object?>{'future_field': 'x', 'condition': 'y'},
              ),
            ],
          ),
        ),
      );
      expect(error.diagnostics, hasLength(1));
      expect(error.diagnostics.single.code, 'TYPE_DIM_CONFLICT');
    });

    test('两类异常不混用', () {
      Object? constructorError;
      try {
        FmlException('NO_SUCH_CODE');
      } catch (error) {
        constructorError = error;
      }
      expect(constructorError, isA<ArgumentError>());
      expect(constructorError, isNot(isA<FormatException>()));

      Object? payloadError;
      try {
        FmlException.fromJson(<String, Object?>{});
      } catch (error) {
        payloadError = error;
      }
      expect(payloadError, isA<FormatException>());
      expect(payloadError, isNot(isA<ArgumentError>()));
    });

    test('异常消息不含原始载荷', () {
      const String marker = 'payload-marker-8f3a1c';
      final Map<String, Object?> wrongType = _errorObject();
      wrongType['retryable'] = marker;
      Object? caught;
      try {
        FmlException.fromJson(_envelope(wrongType));
      } catch (error) {
        caught = error;
      }
      expect(caught, isA<FormatException>());
      expect(caught.toString(), isNot(contains(marker)));
      expect((caught! as FormatException).message, isNot(contains(marker)));

      Object? unknownFieldError;
      try {
        FmlException.fromJson(
          _envelope(
            _errorObject(extra: <String, Object?>{'condition': marker}),
          ),
        );
      } catch (error) {
        unknownFieldError = error;
      }
      expect(unknownFieldError, isA<FormatException>());
      expect(unknownFieldError.toString(), isNot(contains(marker)));

      Object? argumentError;
      try {
        FmlException('AST_JSON_INVALID', traceId: marker);
      } catch (error) {
        argumentError = error;
      }
      expect(argumentError, isA<ArgumentError>());
      expect(argumentError.toString(), isNot(contains(marker)));
    });
  });

  group('源码断言（T-12）', () {
    test('DiagnosticDto 是生成类的 typedef 别名，不复制诊断类', () {
      final String source = _readAppFile('lib/binding/errors.dart');
      expect(source, contains('typedef DiagnosticDto = Diagnostic;'));
      expect(source, isNot(contains('class DiagnosticDto')));
      expect(source, isNot(contains('class Diagnostic ')));
      expect(source, contains("import 'dto/types.g.dart';"));
    });

    test('诊断类来自 CORE-67 生成文件并带生成头', () {
      final String generated = _readAppFile('lib/binding/dto/types.g.dart');
      expect(generated, contains('// GENERATED CODE - DO NOT MODIFY BY HAND.'));
      expect(generated, contains('generator: CORE-67'));
      expect(generated, contains('final class Diagnostic'));
      expect(generated, contains('typedef DiagnosticInputRange = (int, int);'));
    });

    test('构造器与工厂都没有 retryable / domain 形参', () {
      final String source = _readAppFile('lib/binding/errors.dart');
      final RegExpMatch? constructor = RegExp(
        r'FmlException\(\s*String code,\s*\{[^}]*\}',
      ).firstMatch(source);
      expect(constructor, isNotNull);
      expect(constructor!.group(0), isNot(contains('retryable')));
      expect(constructor.group(0), isNot(contains('domain')));
      final RegExpMatch? factory = RegExp(
        r'factory FmlException\.fromJson\([^)]*\)',
      ).firstMatch(source);
      expect(factory, isNotNull);
      expect(factory!.group(0), isNot(contains('retryable')));
      expect(factory.group(0), isNot(contains('domain')));
    });
  });

  group('共享向量 contracts/vectors/errors-v1.json（N2 ERR-NEG-12/13）', () {
    late List<Map<String, Object?>> cases;

    setUpAll(() {
      final String raw = _readAppFile('../contracts/vectors/errors-v1.json');
      final Map<String, Object?> decoded =
          jsonDecode(raw) as Map<String, Object?>;
      cases = (decoded['cases']! as List<Object?>)
          .cast<Map<String, Object?>>()
          .toList();
    });

    test('向量齐备且负端点负例在册', () {
      expect(cases, hasLength(22));
      final Set<Object?> ids = cases
          .map((Map<String, Object?> item) => item['id'])
          .toSet();
      expect(
        ids,
        containsAll(<String>['ERR-01', 'ERR-09', 'ERR-NEG-12', 'ERR-NEG-13']),
      );
    });

    test('正例按 canonical 投影（ERR-09 的零 trace 由 Dart 侧拒绝）', () {
      final List<Map<String, Object?>> positives = cases
          .where((Map<String, Object?> item) => item.containsKey('canonical'))
          .toList();
      expect(positives, hasLength(9));
      for (final Map<String, Object?> item in positives) {
        final String id = item['id']! as String;
        final Map<String, Object?> error =
            jsonDecode(item['canonical']! as String) as Map<String, Object?>;
        if (id == 'ERR-09') {
          expect(
            () => FmlException.fromJson(<String, Object?>{'error': error}),
            throwsFormatException,
            reason: 'ERR-09 是 Rust 领域正例，零 trace 在 Dart 边界必须拒绝',
          );
          continue;
        }
        final FmlException parsed = FmlException.fromJson(<String, Object?>{
          'error': error,
        });
        final ErrorCodeMeta meta = _meta(error['code']! as String);
        expect(parsed.code, error['code'], reason: id);
        expect(parsed.retryable, meta.retryable, reason: id);
        expect(parsed.traceId, error['trace_id'], reason: id);
        expect(
          parsed.diagnostics.length,
          (error['diagnostics']! as List<Object?>).length,
          reason: id,
        );
      }
    });

    test('13 条负例全部被拒绝', () {
      final List<Map<String, Object?>> negatives = cases
          .where((Map<String, Object?> item) => item['valid'] == false)
          .toList();
      expect(negatives, hasLength(13));
      for (final Map<String, Object?> item in negatives) {
        final String id = item['id']! as String;
        expect(
          () => FmlException.fromJson(item['input']! as Map<String, Object?>),
          throwsFormatException,
          reason: '$id (${item['why']})',
        );
      }
    });

    test('ERR-NEG-12/13 补全必填键后仍由 u32 下界拒绝', () {
      for (final String id in <String>['ERR-NEG-12', 'ERR-NEG-13']) {
        final Map<String, Object?> item = cases.firstWhere(
          (Map<String, Object?> candidate) => candidate['id'] == id,
        );
        final Map<String, Object?> input =
            item['input']! as Map<String, Object?>;
        final Map<String, Object?> error =
            input['error']! as Map<String, Object?>;
        final List<Object?> diagnostics = <Object?>[];
        for (final Object? element in error['diagnostics']! as List<Object?>) {
          final Map<String, Object?> diagnostic = Map<String, Object?>.of(
            element as Map<String, Object?>,
          );
          diagnostic['args'] = <String, Object?>{};
          diagnostic['needs_confirm'] = false;
          diagnostics.add(diagnostic);
        }
        final Map<String, Object?> range =
            diagnostics.single! as Map<String, Object?>;
        expect(
          (range['input_range']! as List<Object?>).first,
          lessThan(0),
          reason: id,
        );
        Object? caught;
        try {
          FmlException.fromJson(
            _envelope(<String, Object?>{...error, 'diagnostics': diagnostics}),
          );
        } catch (error) {
          caught = error;
        }
        expect(caught, isA<FormatException>(), reason: id);
        expect(
          (caught! as FormatException).message,
          contains('input_range'),
          reason: id,
        );
      }
    });
  });
}
