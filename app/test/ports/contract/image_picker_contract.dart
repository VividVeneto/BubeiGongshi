// ignore_for_file: public_member_api_docs
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';
import 'package:bubeigongshi/binding/errors.dart';

void runImagePickerContract(ImagePicker Function() create) {
  test('ImagePicker boundaries and batch ownership', () async {
    final p = create();
    await expectLater(p.pick(maxCount: 0), throwsArgumentError);
    await expectLater(p.pick(maxCount: 11), throwsArgumentError);
    // Host driver selects at least one small PNG/JPEG/WebP for this case.
    final images = await p.pick(maxCount: 1);
    expect(images, hasLength(1));
    final image = images.single;
    final adopted = await image.readBytes();
    expect(await image.readBytes(), adopted);
    expect(image.byteLength, adopted.length);
    expect(['image/png', 'image/jpeg', 'image/webp'], contains(image.mimeType));
    await p.pick(maxCount: 1);
    await expectLater(
      image.readBytes(),
      throwsA(isA<FmlException>().having((e) => e.code, 'code', 'PLATFORM_IO')),
    );
    expect(adopted, isNotEmpty);
  });
}
