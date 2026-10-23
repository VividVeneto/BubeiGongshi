import 'dart:async';

import '../binding/core_binding.dart';
import '../ports/platform_ports.dart';

/// 按显式类型保存服务，禁止静默替换。
final class FeatureRegistry {
  final _services = <Type, Object>{};

  /// 同类型重复登记抛StateError；接口实现需显式指定T。
  void register<T extends Object>(T impl) {
    if (_services.containsKey(T)) throw StateError('Duplicate feature type');
    _services[T] = impl;
  }

  /// 未登记时null，不做子类型搜索。
  T? get<T extends Object>() => _services[T] as T?;

  /// 仅组装期使用；缺服务抛StateError。
  T require<T extends Object>() =>
      get<T>() ?? (throw StateError('Missing feature type'));
}

/// 一项需要等待完成的启动任务。
typedef StartupHook = Future<void> Function(FeatureRegistry features);

/// 同步安装点兼容；组装者必须逐项await，失败不得发布依赖对象。
typedef Installer = FutureOr<void> Function(CompositionContext ctx);

/// 组装原语，不运行CORE-36业务安装流程。
final class CompositionContext {
  /// 地址由CORE-28策略的同源配置传入，本层不另建网络策略。
  CompositionContext({
    required this.core,
    required this.ports,
    required this.apiBase,
    required this.packBase,
  });

  /// 已通过入口ABI检查的核心绑定。
  final CoreBinding core;

  /// 平台端口。
  final PlatformPorts ports;

  /// API服务根地址。
  final Uri apiBase;

  /// 资源包根地址。
  final Uri packBase;

  /// 初始传输端口，允许隐私安装点替换为NetworkGuard。
  late HttpTransport http = ports.http;

  /// 已安装的特性服务。
  final FeatureRegistry features = FeatureRegistry();
  final _startup = <int, (int, String, StartupHook)>{};
  final _firstFrame = <int, (int, String, StartupHook)>{};

  /// 登记进程启动任务；同序列重复order抛StateError。
  void addStartupHook(int order, String name, StartupHook hook) =>
      _add(_startup, order, name, hook);

  /// 升序只读快照，读取不执行任务。
  List<(int, String, StartupHook)> get startupHooks => _sorted(_startup);

  /// 登记本地短首帧任务，与启动序列独立。
  void addFirstFrameHook(int order, String name, StartupHook hook) =>
      _add(_firstFrame, order, name, hook);

  /// 首帧升序只读快照。
  List<(int, String, StartupHook)> get firstFrameHooks => _sorted(_firstFrame);
}

void _add(
  Map<int, (int, String, StartupHook)> hooks,
  int order,
  String name,
  StartupHook hook,
) {
  if (hooks.containsKey(order)) throw StateError('Duplicate hook order');
  hooks[order] = (order, name, hook);
}

List<(int, String, StartupHook)> _sorted(
  Map<int, (int, String, StartupHook)> hooks,
) => List.unmodifiable(
  hooks.values.toList()..sort((a, b) => a.$1.compareTo(b.$1)),
);
