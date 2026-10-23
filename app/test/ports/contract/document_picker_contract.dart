// ignore_for_file: public_member_api_docs
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';
import 'package:bubeigongshi/binding/errors.dart';

void runDocumentPickerContract(DocumentPicker Function() create) {
  test(
    'DocumentPicker accepts prepared text and rejects mismatched type/size',
    () async {
      final p = create();
      final d = await p.pick(extensions: ['txt'], maxBytes: 3);
      expect(d, isNotNull);
      expect(d!.byteLength, 3);
      expect(await d.file.readAsBytes(), [1, 2, 3]);
      await expectLater(
        p.pick(extensions: ['txt'], maxBytes: 2),
        throwsA(
          isA<FmlException>().having(
            (e) => e.code,
            'code',
            'PLATFORM_FILE_TOO_LARGE',
          ),
        ),
      );
      await expectLater(
        p.pick(extensions: ['csv'], maxBytes: 3),
        throwsA(
          isA<FmlException>().having(
            (e) => e.code,
            'code',
            'PLATFORM_FILE_TYPE_MISMATCH',
          ),
        ),
      );
    },
  );
}
