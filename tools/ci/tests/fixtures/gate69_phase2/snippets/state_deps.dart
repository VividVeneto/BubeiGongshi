/// 正例：AppDeps.http 不是 PlatformPorts 字段，不报 error。
class DepsState {
  /// 创建状态。
  DepsState(this.deps);

  /// 应用依赖。
  final AppDeps deps;

  /// 读取 http 依赖。
  Object? client() => deps.http;
}
