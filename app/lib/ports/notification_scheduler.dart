import 'port_dtos.dart';
export 'port_dtos.dart';

/// 每日提醒与点击接缝。
abstract interface class NotificationScheduler {
  /// 已授权或无需授权返回true。
  Future<bool> requestPermission();

  /// 替换唯一每日提醒，body只含待复习数量。
  Future<void> scheduleDailyReminder(LocalTime time, String body);

  /// 取消全部提醒。
  Future<void> cancelAll();

  /// 广播点击；冷启动事件重放给首个订阅者。
  Stream<void> taps();
}
