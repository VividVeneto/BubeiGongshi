/// 反例：composition 外读取 PlatformPorts 的 http 字段。
class PortsState {
  /// 创建状态。
  PortsState(this.ports);

  /// 平台端口。
  final PlatformPorts ports;

  /// 读取 http 端口。
  Object? client() => ports.http;
}
