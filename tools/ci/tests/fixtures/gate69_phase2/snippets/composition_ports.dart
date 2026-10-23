/// 正例：composition 内读取 PlatformPorts.http 不报。
class CompositionPorts {
  /// 创建组合根。
  CompositionPorts(this.ports);

  /// 平台端口。
  final PlatformPorts ports;

  /// 读取 http 端口。
  Object? client() => ports.http;
}
