// ignore_for_file: public_member_api_docs
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';
import 'package:bubeigongshi/binding/errors.dart';

void runSecureKeyValueStoreContract(SecureKeyValueStore Function() create) {
  group('SecureKeyValueStore contract', () {
    test('roundtrip, copies, delete, tamper and missing aliases', () async {
      final p = create();
      final input = Uint8List.fromList([0, 1, 255]);
      final wrapped = await p.wrap('contract.key', input);
      input[0] = 99;
      expect(await p.unwrap('contract.key', wrapped), [0, 1, 255]);
      final copy = await p.unwrap('contract.key', wrapped);
      copy[0] = 88;
      expect(await p.unwrap('contract.key', wrapped), [0, 1, 255]);
      expect(await p.securityLevel('contract.key'), isA<KeySecurityLevel>());
      final bad = Uint8List.fromList(wrapped);
      bad[0] ^= 1;
      await expectLater(
        p.unwrap('contract.key', bad),
        throwsA(
          isA<FmlException>().having(
            (e) => e.code,
            'code',
            'PLATFORM_KEY_UNAVAILABLE',
          ),
        ),
      );
      await p.delete('contract.key');
      await p.delete('contract.key');
      await expectLater(
        p.unwrap('contract.key', wrapped),
        throwsA(isA<FmlException>()),
      );
    });
    test('invalid alias is programming error', () async {
      final p = create();
      for (final alias in ['', 'Upper', 'a/b', 'x' * 65]) {
        await expectLater(p.wrap(alias, Uint8List(0)), throwsArgumentError);
      }
    });
  });
}
