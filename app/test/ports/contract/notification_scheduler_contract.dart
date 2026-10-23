// ignore_for_file: public_member_api_docs
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';

void runNotificationSchedulerContract(NotificationScheduler Function() create) {
  test(
    'NotificationScheduler permission, replacement and cancellation',
    () async {
      final p = create();
      expect(await p.requestPermission(), isTrue);
      await p.scheduleDailyReminder(LocalTime(8, 0), '3');
      await p.scheduleDailyReminder(LocalTime(9, 30), '4');
      await p.cancelAll();
      await p.cancelAll();
      final one = p.taps().listen((_) {});
      final two = p.taps().listen((_) {});
      await one.cancel();
      await two.cancel();
    },
  );
}
