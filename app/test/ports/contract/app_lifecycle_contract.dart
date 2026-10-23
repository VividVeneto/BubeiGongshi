// ignore_for_file: public_member_api_docs
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';

void runAppLifecycleContract(AppLifecycle Function() create) {
  test('AppLifecycle concurrent subscribers', () async {
    final stream = create().events();
    expect(stream.isBroadcast, isTrue);
    final a = stream.listen((_) {});
    final b = stream.listen((_) {});
    await a.cancel();
    await b.cancel();
  });
}
