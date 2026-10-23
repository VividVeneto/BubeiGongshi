// ignore_for_file: public_member_api_docs
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';

void runRuntimeInfoContract(RuntimeInfo Function() create) {
  test('RuntimeInfo well-formed platform data', () async {
    final s = await create().snapshot();
    expect(['android', 'windows'], contains(s.os));
    expect(s.osVersion, isNotEmpty);
    expect(s.locale, matches(RegExp(r'^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$')));
    expect(s.availMemBytes, greaterThanOrEqualTo(0));
    expect(s.dpiScale, greaterThan(0));
    expect(s.dpiScale.isFinite, isTrue);
    expect(['arm64-v8a', 'armeabi-v7a', 'x86_64', 'x64'], contains(s.abi));
  });
}
