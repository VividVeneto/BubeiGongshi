// ignore_for_file: public_member_api_docs
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';
import 'package:bubeigongshi/binding/errors.dart';

void runCameraControllerContract(CameraController Function() create) {
  test('CameraController batch replaced independently', () async {
    final p = create();
    final first = await p.capture();
    expect(first, isNotNull);
    final adopted = await first!.readBytes();
    expect(await first.readBytes(), adopted);
    await p.capture();
    await expectLater(
      first.readBytes(),
      throwsA(isA<FmlException>().having((e) => e.code, 'code', 'PLATFORM_IO')),
    );
    expect(adopted, isNotEmpty);
  });
}
