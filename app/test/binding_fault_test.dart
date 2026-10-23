// Supplemental C fault injection, NOT Rust pool acceptance.
import 'dart:async';
import 'dart:convert';
import 'dart:ffi';
import 'dart:io';

import 'package:ffi/ffi.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/binding/core_binding.dart';
import 'package:bubeigongshi/binding/errors.dart';
import 'package:bubeigongshi/binding/error_codes.g.dart';
import 'package:bubeigongshi/binding/fmlcore.g.dart';

const _trace = '1234567890abcdef1234567890abcdef';
final _spec = CoreLibrarySpec(
  Platform.environment['FML_FAULT_LIBRARY'] ??
      File('../build/binding-fixture/fixture.dll').absolute.path,
);
final _lib = DynamicLibrary.open(_spec.path);
final _config = _lib
    .lookupFunction<
      Void Function(Pointer<Utf8>, Int32, Int32),
      void Function(Pointer<Utf8>, int, int)
    >('fixture_configure');
final _metric = _lib.lookupFunction<Int32 Function(Int32), int Function(int)>(
  'fixture_metric',
);
final _lastRequest = _lib
    .lookupFunction<Pointer<Utf8> Function(), Pointer<Utf8> Function()>(
      'fixture_request',
    );
final _release = _lib.lookupFunction<Void Function(), void Function()>(
  'fixture_release',
);
final _complete = _lib
    .lookupFunction<Void Function(Uint64), void Function(int)>(
      'fixture_complete',
    );
Map<String, Object?> _ok() => {
  'v': 1,
  'trace_id': _trace,
  'ok': {'value': 42},
  'diagnostics': [],
};
Map<String, Object?> _error() => {
  'v': 1,
  'trace_id': _trace,
  'error': {
    'code': 'EVAL_TIMEOUT',
    'domain': 'eval',
    'trace_id': _trace,
    'diagnostics': [],
    'retryable': true,
  },
};
void _set(Object value, {int status = 0, int mode = 0}) {
  final text = (value is String ? value : jsonEncode(value)).toNativeUtf8();
  try {
    _config(text, status, mode);
  } finally {
    calloc.free(text);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late CoreBinding binding;
  setUp(() {
    _set(_ok());
    binding = CoreBinding.open(_spec);
  });
  tearDown(() async {
    _release();
    await binding.dispose();
    expect(_metric(0), 0);
    expect(_metric(2), 0);
  });
  test(
    'copy/free once even when decoding fails; strict malformed envelopes',
    () {
      final cases = <Object>[
        'not json',
        [],
        {},
        {..._ok(), 'v': 2},
        {..._ok(), 'v': 1.0},
        {..._ok(), 'trace_id': '0' * 32},
        {..._ok(), 'trace_id': 'F' * 32},
        {..._ok(), 'trace_id': null},
        {..._ok(), 'trace_id': 'g' * 32},
        {..._ok(), 'trace_id': 'a' * 31},
        {..._ok(), 'ok': []},
        {..._ok(), 'error': {}},
        {..._ok(), 'diagnostics': null},
        {..._ok(), 'engine_generation': -1},
        {..._ok(), 'engine_generation': null},
        {..._ok(), 'engine_generation': '18446744073709551616'},
        {..._error(), 'trace_id': 'f' * 32},
      ];
      for (final value in cases) {
        _set(value);
        final before = _metric(1);
        expect(() => binding.call('fault', {}), throwsFormatException);
        expect(_metric(1), before + 1);
        expect(_metric(0), 0);
      }
    },
  );
  test('six FFI statuses match registry retryability and severity', () {
    const codes = [
      'FFI_BAD_ARG',
      'FFI_UNKNOWN_OP',
      'FFI_VERSION_MISMATCH',
      'FFI_STALE_HANDLE',
      'FFI_PANIC',
      'FFI_BUSY',
    ];
    for (var index = 0; index < codes.length; index++) {
      final meta = errorCodeRegistry.singleWhere((m) => m.code == codes[index]);
      final error = {
        'code': meta.code,
        'domain': meta.domain,
        'retryable': meta.retryable,
        'trace_id': _trace,
        'diagnostics': [
          {
            'code': meta.code,
            'severity': meta.severity,
            'needs_confirm': false,
            'args': <String, String>{},
          },
        ],
      };
      final envelope = {'v': 1, 'trace_id': _trace, 'error': error};
      _set(envelope, status: -index - 1);
      expect(
        () => binding.call('fault', {}),
        throwsA(
          isA<FfiException>()
              .having((e) => e.status, 'status', -index - 1)
              .having((e) => e.code, 'code', meta.code)
              .having((e) => e.traceId, 'trace', _trace),
        ),
      );
      _set({
        ...envelope,
        'error': {...error, 'retryable': !meta.retryable},
      }, status: -index - 1);
      expect(() => binding.call('fault', {}), throwsFormatException);
    }
  });
  test('unknown -99 maps null code and trace when no buffer', () {
    _set('', status: -99, mode: 9);
    expect(
      () => binding.call('fault', {}),
      throwsA(
        isA<FfiException>()
            .having((e) => e.status, 'status', -99)
            .having((e) => e.code, 'code', null)
            .having((e) => e.traceId, 'trace', null),
      ),
    );
  });
  test(
    'generation reaches subscribers before both result and domain error',
    () async {
      final events = <String>[];
      final sub = binding.engineGenerations.listen(events.add);
      _set({..._ok(), 'engine_generation': '18446744073709551615'});
      expect(binding.call('fault', {}), {'value': 42});
      expect(events, ['18446744073709551615']);
      _set({..._error(), 'engine_generation': '0'}, status: 1);
      expect(() => binding.call('fault', {}), throwsA(isA<FmlException>()));
      expect(events.last, '0');
      await sub.cancel();
    },
  );
  test('invalid status/code does not publish a generation', () async {
    final events = <String>[];
    final sub = binding.engineGenerations.listen(events.add);
    _set({
      ..._error(),
      'engine_generation': '5',
      'error': {
        'code': 'FFI_BAD_ARG',
        'domain': 'ffi',
        'retryable': false,
        'trace_id': _trace,
        'diagnostics': [],
      },
    }, status: -2);
    expect(() => binding.call('fault', {}), throwsFormatException);
    expect(events, isEmpty);
    await sub.cancel();
  });
  test(
    'all inconsistent status families suppress generation and free once',
    () async {
      final events = <String>[];
      final sub = binding.engineGenerations.listen(events.add);
      for (final status in [0, 1, -2, -3, -4, -5, -6, -99, 2]) {
        _set({
          'v': 1,
          'trace_id': _trace,
          'engine_generation': '6',
          'error': {
            'code': 'FFI_BAD_ARG',
            'domain': 'ffi',
            'retryable': false,
            'trace_id': _trace,
            'diagnostics': [],
          },
        }, status: status);
        final before = _metric(1);
        expect(() => binding.call('fault', {}), throwsFormatException);
        expect(_metric(1), before + 1);
      }
      for (final status in [-1, -2, -3, -4, -5, -6]) {
        _set({..._error(), 'engine_generation': '7'}, status: status);
        expect(() => binding.call('fault', {}), throwsFormatException);
      }
      expect(events, isEmpty);
      await sub.cancel();
    },
  );
  test(
    'invalid async envelopes free once without publishing generation',
    () async {
      final events = <String>[];
      final sub = binding.engineGenerations.listen(events.add);
      for (final value in [
        {..._ok(), 'v': 1.0},
        {..._ok(), 'diagnostics': null},
        {..._error(), 'trace_id': 'f' * 32},
      ]) {
        _set({...value, 'engine_generation': '8'});
        final before = _metric(1);
        await expectLater(binding.submit('fault', {}), throwsFormatException);
        expect(_metric(1), before + 1);
        expect(_metric(0), 0);
      }
      expect(events, isEmpty);
      await sub.cancel();
    },
  );
  test(
    'request fields copied once, profiles independent and trace unique',
    () async {
      final traces = <String>{};
      for (final profile in ['1', '18446744073709551615']) {
        final view = binding.scopedTo(profile);
        view.call(
          'fault',
          {'email': 'not-logged'},
          budget: const Duration(milliseconds: 2),
          expectedGeneration: '0',
        );
        final req = jsonDecode(_lastRequest().toDartString()) as Map;
        expect(req['profile_handle'], profile);
        expect(req['expected_generation'], '0');
        expect(req['budget_ms'], 2);
        expect(req['body'], {'email': 'not-logged'});
        expect(req['trace_id'], matches(RegExp(r'^[0-9a-f]{32}$')));
        traces.add(req['trace_id'] as String);
        await view.dispose();
      }
      expect(traces.length, 2);
    },
  );
  test('actual by-value completion and cancellation after posting', () async {
    final before = _metric(1);
    expect(await binding.submit('fault', {}), {'value': 42});
    final token = CancelToken();
    final result = binding.submit('fault', {}, cancel: token);
    final checked = expectLater(result, throwsA(isA<FfiCancelled>()));
    token.cancel();
    await checked;
    expect(_metric(1), before + 2);
  });
  test(
    'busy unregister yields to late callback and frees before listener close',
    () async {
      final raw = FmlCoreBindings(_lib);
      final held = raw.fml_capabilities();
      _complete(400);
      final attempts = _metric(4);
      final disposal = binding.dispose();
      final freed = Future<void>.delayed(Duration.zero, () {
        expect(raw.fml_free_buffer(held), 0);
      });
      await Future.wait([freed, disposal]);
      expect(_metric(4), greaterThan(attempts + 1));
      final reopened = CoreBinding.open(_spec);
      await reopened.dispose();
    },
  );
  test(
    'blocking cancel runs off listener isolate with finite barrier',
    () async {
      _set(_ok(), mode: 2);
      final prior = _metric(3);
      final token = CancelToken();
      final future = binding.submit('fault', {}, cancel: token);
      final id = _metric(5);
      final checked = expectLater(future, throwsA(isA<FfiCancelled>()));
      token.cancel();
      var ticks = 0;
      final timer = Timer.periodic(const Duration(milliseconds: 1), (_) {
        ticks++;
        _release();
      });
      try {
        await checked.timeout(const Duration(seconds: 5));
      } finally {
        timer.cancel();
        _release();
        if (_metric(3) == prior) _complete(id);
      }
      expect(ticks, greaterThan(0));
      expect(_metric(3), prior + 1);
    },
  );
  test('dispose three jobs drains late results exactly once', () async {
    _set(_ok(), mode: 3);
    final before = _metric(1);
    final ids = <int>[];
    final checked = <Future<void>>[];
    for (var i = 0; i < 3; i++) {
      checked.add(
        expectLater(binding.submit('fault', {}), throwsA(isA<FfiCancelled>())),
      );
      ids.add(_metric(5));
    }
    final prior = _metric(3);
    final disposal = binding.dispose();
    await Future.wait(checked).timeout(const Duration(seconds: 5));
    if (_metric(3) == prior) {
      for (final id in ids) {
        _complete(id);
      }
    }
    await disposal.timeout(const Duration(seconds: 5));
    expect(_metric(3), prior + 3);
    expect(_metric(1), before + 3);
  });
}
