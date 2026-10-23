import 'dart:io';
import 'dart:convert';

import 'package:bubeigongshi/binding/error_codes.g.dart';

import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/binding/errors.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';

import '../../fakes/composition_fakes.dart';

void main() {
  test(
    'all unsupported operations fail closed except documented empty values',
    () async {
      final p = portsWith();
      final bytes = Uint8List(0);
      var consumed = false;
      Stream<List<int>> source() async* {
        consumed = true;
        yield [1];
      }

      final operations = <Future<Object?> Function()>[
        () => p.keys.wrap('a', bytes),
        () => p.keys.unwrap('a', bytes),
        () => p.keys.delete('a'),
        () => p.keys.securityLevel('a'),
        () => p.files.root(StoreArea.staging),
        () => p.files.freeBytes(),
        () => p.files.excludeFromSystemBackup(Directory('unaccessed')),
        () => p.picker.pick(maxCount: 1),
        p.camera.capture,
        p.notifications.requestPermission,
        () => p.notifications.scheduleDailyReminder(LocalTime(1, 2), 'body'),
        p.notifications.cancelAll,
        p.clipboard.readText,
        () => p.clipboard.writeText('text'),
        p.runtime.snapshot,
        () => p.http.send(
          HttpRequestDto(
            method: HttpMethod.get,
            url: Uri.parse('https://unused.invalid'),
            purpose: RequestPurpose.auth,
          ),
        ),
        () => p.exporter.saveAs('name', source()),
        () => p.documents.pick(extensions: ['txt'], maxBytes: 1),
      ];
      for (final operation in operations) {
        await expectLater(
          operation(),
          throwsA(
            isA<FmlException>().having(
              (e) => e.code,
              'code',
              'PLATFORM_UNSUPPORTED',
            ),
          ),
        );
      }
      expect(consumed, isFalse);
      expect(await p.clipboard.readImage(), isNull);
      expect(await p.notifications.taps().toList(), isEmpty);
      expect(await p.lifecycle.events().toList(), isEmpty);
      expect(await p.lifecycle.events().toList(), isEmpty);
      for (final n in [0, 11]) {
        await expectLater(p.picker.pick(maxCount: n), throwsArgumentError);
      }
    },
  );
  test('all owned error codes are registered and have Chinese fallback', () {
    for (final code in [
      'PLATFORM_UNSUPPORTED',
      'PLATFORM_PERMISSION_DENIED',
      'PLATFORM_KEY_UNAVAILABLE',
      'PLATFORM_IO',
      'PLATFORM_FILE_TOO_LARGE',
      'PLATFORM_FILE_TYPE_MISMATCH',
      'PLATFORM_CANCELLED',
      'PLATFORM_UPDATE_SIG_INVALID',
      'PLATFORM_UPDATE_HASH_MISMATCH',
      'PLATFORM_UPDATE_DISK_FULL',
      'PLATFORM_UPDATE_ROLLED_BACK',
      'NET_OFFLINE',
      'NET_TLS',
      'NET_TIMEOUT',
      'NET_HOST_NOT_ALLOWED',
    ]) {
      final error = FmlException(code);
      expect(error.code, code);
      final meta = errorCodeRegistry.singleWhere((m) => m.code == code);
      final messages = jsonDecode(
        File('lib/l10n/errors_zh.arb').readAsStringSync(),
      ) as Map<String, dynamic>;
      expect(meta.messageKey, startsWith('err.'));
      expect(messages[meta.messageKey], matches(RegExp(r'[\u4e00-\u9fff]')));
    }
  });
}
