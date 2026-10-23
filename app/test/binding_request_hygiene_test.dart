// Source-level ownership guard; not proof of VM/String erasure.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
    'request retains encoder buffer and wipes owned allocations in finally',
    () {
      final source = File('lib/binding/wire.dart').readAsStringSync();
      final request = source.substring(source.indexOf('T _request<T>('));
      expect(request, isNot(contains('Uint8List.fromList')));
      expect(request, contains('final bytes = utf8.encode('));
      final cleanup = request.substring(request.indexOf('} finally {'));
      expect(cleanup, contains('bytes.fillRange(0, bytes.length, 0)'));
      expect(
        cleanup,
        contains(
          'request.asTypedList(bytes.length).fillRange(0, bytes.length, 0)',
        ),
      );
      expect(
        cleanup.indexOf('fillRange'),
        lessThan(cleanup.indexOf('calloc.free(request)')),
      );
    },
  );
}
