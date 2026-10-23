// Real phase-two Rust DLL integration, never substituted by the C fault DLL.
import 'dart:convert';
import 'dart:io';

import 'package:bubeigongshi/binding/core_binding.dart';
import 'package:bubeigongshi/binding/errors.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final library = Platform.environment['FML_ASYNC_LIBRARY'];
  final configuration = Platform.environment['FML_ASYNC_CASES'];
  const pending = 'Real Rust test_ops DLL not configured for this invocation';
  group('real Rust asynchronous integration', () {
    late CoreBinding binding;
    late Map<String, dynamic> cases;
    setUp(() {
      if (configuration == null) {
        throw StateError('FML_ASYNC_CASES is required with FML_ASYNC_LIBRARY');
      }
      cases = jsonDecode(configuration) as Map<String, dynamic>;
      binding = CoreBinding.open(CoreLibrarySpec(library!));
    });
    tearDown(() async => binding.dispose());
    Future<Map<String, Object?>> run(String key, {CancelToken? cancel}) {
      final spec = cases[key] as Map<String, dynamic>;
      return binding.submit(
        spec['op'] as String,
        Map<String, Object?>.from(spec['body'] as Map),
        cancel: cancel,
      );
    }

    test('success returns only the expected business body', () async {
      expect(await run('success'), cases['success']['expected']);
    });
    test('domain error and panic traverse the real callback', () async {
      await expectLater(
        run('domain'),
        throwsA(
          isA<FmlException>()
              .having((e) => e.code, 'code', cases['domain']['code'])
              .having(
                (e) => e.traceId,
                'nonzero trace',
                matches(r'^(?!0{32}$)[0-9a-f]{32}$'),
              ),
        ),
      );
      await expectLater(
        run('panic'),
        throwsA(
          isA<FfiException>()
              .having((e) => e.status, 'status', -5)
              .having((e) => e.traceId, 'trace', matches(r'^[0-9a-f]{32}$')),
        ),
      );
    });
    test(
      'existing trace survives and invalid handler becomes FFI panic',
      () async {
        await expectLater(
          binding.submit('fake.async_traced', {}),
          throwsA(
            isA<FmlException>().having((e) => e.traceId, 'trace', '07' * 16),
          ),
        );
        await expectLater(
          binding.submit('fake.async_invalid', {}),
          throwsA(
            isA<FfiException>().having((e) => e.code, 'code', 'FFI_PANIC'),
          ),
        );
      },
    );
    test('long cooperative task cancels without blocking listener', () async {
      final token = CancelToken();
      final result = run('long', cancel: token);
      final checked = expectLater(result, throwsA(isA<FfiCancelled>()));
      token.cancel();
      await checked.timeout(const Duration(seconds: 10));
    });
    test('dispose cancels three jobs and rejects new work', () async {
      final checked = List.generate(
        3,
        (_) => expectLater(run('long'), throwsA(isA<FfiCancelled>())),
      );
      final disposal = binding.dispose();
      expect(() => binding.call('unused', {}), throwsStateError);
      expect(() => binding.submit('unused', {}), throwsStateError);
      await Future.wait(checked).timeout(const Duration(seconds: 10));
      await disposal.timeout(const Duration(seconds: 10));
      final next = CoreBinding.open(CoreLibrarySpec(library!));
      await next.dispose();
    });
  }, skip: library == null ? pending : false);
}
