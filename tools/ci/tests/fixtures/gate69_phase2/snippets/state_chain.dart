/// 反例：经同文件赋值链追到 PlatformPorts 标注。
class ChainState {
  /// 创建状态。
  ChainState(this.ports);

  /// 平台端口。
  final PlatformPorts ports;

  /// 经赋值链读取 http。
  Object? client() {
    final alias = ports;
    return alias.http;
  }
}
