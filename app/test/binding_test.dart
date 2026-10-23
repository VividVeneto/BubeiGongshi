// CORE-03: real Rust DLL tests; missing artifacts fail instead of silently skipping.
import 'dart:convert';
import 'dart:ffi';
import 'dart:io';
import 'dart:isolate';

import 'package:ffi/ffi.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/binding/core_binding.dart';
import 'package:bubeigongshi/binding/errors.dart';
import 'package:bubeigongshi/binding/fmlcore.g.dart';

final _spec = CoreLibrarySpec(
  Platform.environment['FML_TEST_LIBRARY'] ??
      File('../build/binding-test/debug/fmlcore.dll').absolute.path,
);
final _bump = CoreLibrarySpec(
  Platform.environment['FML_BUMP_LIBRARY'] ??
      File('../build/binding-bump/debug/fmlcore.dll').absolute.path,
);
const _trace = '1234567890abcdef1234567890abcdef';
Map<String, dynamic> _take(FmlCoreBindings native, FmlBuf buf) {
  try {
    return jsonDecode(utf8.decode(buf.ptr.asTypedList(buf.len)))
        as Map<String, dynamic>;
  } finally {
    expect(native.fml_free_buffer(buf), 0);
  }
}

(int, Map<String, dynamic>) _raw(
  FmlCoreBindings native,
  String op,
  Map<String, Object?> env,
) {
  final name = op.toNativeUtf8();
  final bytes = utf8.encode(jsonEncode(env));
  final req = calloc<Uint8>(bytes.length)
    ..asTypedList(bytes.length).setAll(0, bytes);
  final out = calloc<FmlBuf>();
  try {
    final status = native.fml_call(name.cast(), req, bytes.length, out);
    return (status, _take(native, out.ref));
  } finally {
    calloc.free(name);
    calloc.free(req);
    calloc.free(out);
  }
}

Matcher _ffi(int status) =>
    isA<FfiException>().having((e) => e.status, 'status', status);
Future<List<Object?>> _workerProbe(String path) => Isolate.run(() async {
  final worker = CoreBinding.open(CoreLibrarySpec(path));
  final reply = worker.call('fake.echo', {'worker': true});
  var rejected = false;
  try {
    await worker.submit('fake.echo', {});
  } on StateError {
    rejected = true;
  }
  await worker.dispose();
  return [reply['echo'], rejected];
});
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('missing dynamic library is not swallowed', () {
    expect(
      () => CoreBinding.open(const CoreLibrarySpec('absent-core03-library')),
      throwsArgumentError,
    );
  });
  group('real Rust transport', () {
    late CoreBinding binding;
    setUp(() {
      binding = CoreBinding.open(_spec);
    });
    tearDown(() async {
      await binding.dispose();
    });
    test('ABI constants, actual echo and CORE67-free transport', () {
      expect(binding.abiVersion(), FML_ABI_MAJOR << 16 | FML_ABI_MINOR);
      final body = {'v': 987, 'formula': 'α+β', 'value': 'secret-not-logged'};
      final reply = binding.call(
        'fake.echo',
        body,
        expectedGeneration: '18446744073709551615',
      );
      expect(reply['echo'], body);
      expect(reply['dto'], 1);
      expect(reply.keys, isNot(contains('trace_id')));
      expect(reply.keys, isNot(contains('engine_generation')));
    });
    test('domain zero trace filled and existing trace preserved', () {
      expect(
        () => binding.call('fake.error', {}),
        throwsA(
          isA<FmlException>()
              .having((e) => e.code, 'code', 'EVAL_TIMEOUT')
              .having(
                (e) => e.traceId,
                'trace',
                matches(RegExp(r'^[0-9a-f]{32}$')),
              )
              .having((e) => e.traceId, 'nonzero', isNot('0' * 32)),
        ),
      );
      expect(
        () => binding.call('fake.traced', {}),
        throwsA(
          isA<FmlException>().having(
            (e) => e.traceId,
            'existing trace',
            '07' * 16,
          ),
        ),
      );
    });
    test('native unknown op, panic, malformed handler, profile statuses', () {
      expect(() => binding.call('missing.operation', {}), throwsA(_ffi(-2)));
      expect(() => binding.call('fake.panic', {}), throwsA(_ffi(-5)));
      expect(() => binding.call('fake.invalid', {}), throwsA(_ffi(-5)));
      expect(
        () => binding.call('fake.profile', {}),
        throwsA(
          isA<FmlException>().having(
            (e) => e.code,
            'profile required',
            'AUTH_NO_PROFILE',
          ),
        ),
      );
      expect(
        () => binding.scopedTo('1').call('fake.profile', {}),
        throwsA(_ffi(-4)),
      );
      expect(
        () => binding.scopedTo('1').call('fake.echo', {}),
        throwsA(_ffi(-1)),
      );
    });
    test('three budgets and non-budget op ignoring it', () {
      for (final op in ['engine.parse', 'calc.evaluate', 'grade.answer']) {
        expect(
          () => binding.call(op, {}, budget: const Duration(milliseconds: 1)),
          throwsA(
            isA<FmlException>().having(
              (e) => e.code,
              'timeout',
              'EVAL_TIMEOUT',
            ),
          ),
        );
      }
      expect(
        binding.call('fake.echo', {}, budget: Duration.zero)['budget_ms'],
        null,
      );
      expect(
        () => binding.call(
          'fake.echo',
          {},
          budget: const Duration(microseconds: -1),
        ),
        throwsArgumentError,
      );
      expect(
        () => binding.call(
          'fake.echo',
          {},
          budget: const Duration(milliseconds: 4294967296),
        ),
        throwsArgumentError,
      );
    });
    test(
      'bound view immutable, dispose nonowning and input decimals strict',
      () async {
        final view = binding.scopedTo('18446744073709551615');
        expect(() => view.scopedTo('2'), throwsStateError);
        for (final value in ['-1', '+1', '', '1.0', '18446744073709551616']) {
          expect(() => binding.scopedTo(value), throwsArgumentError);
          expect(
            () => binding.call('fake.echo', {}, expectedGeneration: value),
            throwsArgumentError,
          );
        }
        await view.dispose();
        expect(() => view.call('fake.echo', {}), throwsStateError);
        expect(binding.call('fake.echo', {})['dto'], 1);
        expect(
          () => binding.call('fake.echo\u0000suffix', {}),
          throwsArgumentError,
        );
      },
    );
    test('single owner, idempotent disposal rejects new call/submit', () async {
      expect(() => CoreBinding.open(_spec), throwsStateError);
      final first = binding.dispose();
      expect(identical(first, binding.dispose()), isTrue);
      expect(() => binding.call('fake.echo', {}), throwsStateError);
      expect(() => binding.submit('fake.echo', {}), throwsStateError);
      await first;
      final replacement = CoreBinding.open(_spec);
      await replacement.dispose();
    });
    test(
      'pre-cancel idempotent and phase1 unsupported submit is not fake success',
      () async {
        final token = CancelToken()
          ..cancel()
          ..cancel();
        expect(token.isCancelled, isTrue);
        await expectLater(
          binding.submit('fake.echo', {}, cancel: token),
          throwsA(isA<FfiCancelled>()),
        );
        await expectLater(binding.submit('fake.echo', {}), throwsA(_ffi(-2)));
      },
    );
    test('worker isolate sync allowed, submit rejected and dispose does not unregister', () async {
      final path = _spec.path;
      final value = await _workerProbe(path);
      expect(value, [
        {'worker': true},
        true,
      ]);
      await expectLater(binding.submit('fake.echo', {}), throwsA(_ffi(-2)));
    });
  });
  test(
    'real ABI bump not silently normalized; platform comparison can reject',
    () async {
      final binding = CoreBinding.open(_bump);
      expect(binding.abiVersion() >> 16, FML_ABI_MAJOR + 1);
      await binding.dispose();
    },
  );
  test(
    'generated raw bindings: capability projection and trace/version vectors',
    () {
      final native = FmlCoreBindings(DynamicLibrary.open(_spec.path));
      final caps = _take(native, native.fml_capabilities());
      expect(caps['abi'], '1.0');
      expect((caps['build'] as Map)['test_build'], true);
      final ops = (caps['ops'] as List).cast<Map<String, dynamic>>();
      expect(ops.length, greaterThanOrEqualTo(9));
      for (final op in ops) {
        expect(op['dto'], 1);
      }
      expect(
        ops.where((o) => o['budget'] == true).map((o) => o['op']).toSet(),
        {'engine.parse', 'calc.evaluate', 'grade.answer'},
      );
      for (final trace in ['', '0' * 32, 'A' * 32, 'f' * 31, 'g' * 32, null]) {
        final (status, reply) = _raw(native, 'fake.echo', {
          'v': 1,
          'body': {},
          'trace_id': trace,
        });
        expect(status, -1);
        expect(reply['trace_id'], matches(RegExp(r'^[0-9a-f]{32}$')));
        expect(reply['trace_id'], isNot('0' * 32));
        expect((reply['error'] as Map)['trace_id'], reply['trace_id']);
      }
      final (status, reply) = _raw(native, 'fake.echo', {
        'v': 2,
        'body': {},
        'trace_id': _trace,
      });
      expect(status, -3);
      expect(reply['trace_id'], _trace);
    },
  );
  test('shared errors-v1 consumed by the actual CORE02 bridge', () {
    final vectors = jsonDecode(
      File('../contracts/vectors/errors-v1.json').readAsStringSync(),
    ) as Map;
    expect(vectors['version'], 1);
    for (final item in vectors['cases'] as List) {
      final row = item as Map;
      final input = Map<String, Object?>.from(row['input'] as Map);
      if (row['valid'] == false || row['id'] == 'ERR-09') {
        expect(
          () => FmlException.fromJson(input),
          throwsFormatException,
          reason: row['id'] as String,
        );
      } else {
        final canonical = jsonDecode(row['canonical'] as String) as Map;
        final error = FmlException.fromJson({'error': canonical});
        expect(error.code, canonical['code']);
        expect(error.traceId, canonical['trace_id']);
        expect(
          error.diagnostics.length,
          (canonical['diagnostics'] as List).length,
        );
      }
    }
  });
}
