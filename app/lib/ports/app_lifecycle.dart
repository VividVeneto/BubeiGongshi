import 'port_dtos.dart';
export 'port_dtos.dart';

/// 共享生命周期接缝。
abstract interface class AppLifecycle {
  /// 广播生命周期事件。
  Stream<LifecycleEvent> events();
}
