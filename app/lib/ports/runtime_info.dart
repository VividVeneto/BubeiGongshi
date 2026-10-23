import 'port_dtos.dart';
export 'port_dtos.dart';

/// 平台运行环境快照，不猜测未知GPU能力。
abstract interface class RuntimeInfo {
  /// 获取快照；未实现抛PLATFORM_UNSUPPORTED。
  Future<RuntimeSnapshot> snapshot();
}
