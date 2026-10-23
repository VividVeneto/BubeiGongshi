/// 反例：ui 构造参数与字段出现 AppDeps、CoreBinding、PlatformPorts。
class HoldsPage extends Object {
  /// 创建页面。
  const HoldsPage(this.deps, this.binding, this.ports);

  /// 应用依赖。
  final AppDeps deps;

  /// 核心绑定。
  final CoreBinding binding;

  /// 平台端口。
  final PlatformPorts ports;
}
