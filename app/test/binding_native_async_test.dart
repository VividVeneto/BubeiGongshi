// Real Rust ABI ownership probes, not the supplemental C fault library.
import 'dart:async';
import 'dart:convert';
import 'dart:ffi';
import 'dart:io';
import 'dart:isolate';

import 'package:bubeigongshi/binding/fmlcore.g.dart';
import 'package:ffi/ffi.dart';
import 'package:flutter_test/flutter_test.dart';

int _cancel(String path, int id) =>
    FmlCoreBindings(DynamicLibrary.open(path)).fml_cancel(id);
Future<int> _cancelOffThread(String path, int id) =>
    Isolate.run(() => _cancel(path, id));

int _submit(FmlCoreBindings native, String op, Map<String, Object?> body) {
  final name = op.toNativeUtf8();
  final bytes = utf8.encode(
    jsonEncode({
      'v': 1,
      'trace_id': '1234567890abcdef1234567890abcdef',
      'body': body,
    }),
  );
  final request = calloc<Uint8>(bytes.length)
    ..asTypedList(bytes.length).setAll(0, bytes);
  final id = calloc<Uint64>();
  try {
    expect(native.fml_submit(name.cast(), request, bytes.length, id), 0);
    return id.value;
  } finally {
    request.asTypedList(bytes.length).fillRange(0, bytes.length, 0);
    bytes.fillRange(0, bytes.length, 0);
    calloc.free(request);
    calloc.free(name);
    calloc.free(id);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final path = Platform.environment['FML_ASYNC_LIBRARY'];
  test('real cancel 0 suppresses callback; 1 retains allocation; free retires to -4', () async {
    final native = FmlCoreBindings(DynamicLibrary.open(path!));
    final held = calloc<FmlBuf>();
    final received = Completer<int>();
    var callbacks = 0;
    final listener = NativeCallable<FmlCompletionFunction>.listener((
      int id,
      FmlBuf buffer,
      Pointer<Void> user,
    ) {
      callbacks++;
      held.ref
        ..ptr = buffer.ptr
        ..len = buffer.len
        ..allocation_id = buffer.allocation_id;
      received.complete(id);
    });
    expect(native.fml_register_completion(listener.nativeFunction, nullptr), 0);
    var registered = true;
    try {
      final waiting = _submit(native, 'fake.wait', {'wait_ms': 5000});
      expect(await _cancelOffThread(path, waiting), 0);
      expect(native.fml_cancel(waiting), -4);
      expect(native.fml_register_completion(nullptr, nullptr), 0);
      registered = false;
      // Cancellation's return and successful unregister are synchronization,
      // not an arbitrary sleep claiming no future callback.
      await Future<void>.delayed(Duration.zero);
      expect(callbacks, 0);
      expect(
        native.fml_register_completion(listener.nativeFunction, nullptr),
        0,
      );
      registered = true;
      final completed = _submit(native, 'fake.async', {'value': 42});
      expect(
        await received.future.timeout(const Duration(seconds: 10)),
        completed,
      );
      expect(native.fml_cancel(completed), 1);
      expect(native.fml_register_completion(nullptr, nullptr), -6);
      final reply = jsonDecode(
        utf8.decode(held.ref.ptr.asTypedList(held.ref.len)),
      ) as Map;
      expect(reply['trace_id'], '1234567890abcdef1234567890abcdef');
      expect((reply['ok'] as Map)['echo'], {'value': 42});
      expect(native.fml_free_buffer(held.ref), 0);
      expect(native.fml_free_buffer(held.ref), -1);
      held.ref.ptr = nullptr;
      // The native callback may still be unwinding after posting to Dart.
      final deadline = Stopwatch()..start();
      while (true) {
        final status = native.fml_register_completion(nullptr, nullptr);
        if (status == 0) break;
        expect(status, -6);
        expect(deadline.elapsed, lessThan(const Duration(seconds: 10)));
        await Future<void>.delayed(Duration.zero);
      }
      registered = false;
      expect(native.fml_cancel(completed), -4);
      expect(callbacks, 1);
    } finally {
      if (held.ref.ptr != nullptr) native.fml_free_buffer(held.ref);
      // Keep the listener alive if unregister fails; never unload a live DLL.
      if (registered) {
        final status = native.fml_register_completion(nullptr, nullptr);
        expect(status, 0);
        registered = status != 0;
      }
      if (!registered) listener.close();
      calloc.free(held);
    }
  }, skip: path == null ? 'Real Rust test_ops DLL not configured' : false);
}
