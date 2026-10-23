import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../binding/core_binding.dart';
import '../binding/errors.dart';
import '../binding/fmlcore.g.dart' show FML_ABI_MAJOR;
import '../ports/platform_ports.dart';

/// 平台到共享应用的入口签名。
typedef AppEntry = Future<void> Function(PlatformPorts ports, CoreBinding core);

/// S0冒烟入口；CORE-36完成时唯一替换为mainCommon的接缝。
const AppEntry appEntry = smokeEntry;

/// 先初始化Flutter再加载真实库，ABI失败不构造任何端口。
Future<void> runPlatformApp(
  CoreLibrarySpec spec,
  PlatformPorts Function() buildPorts, {
  CoreBinding Function(CoreLibrarySpec)? open,
}) async {
  WidgetsFlutterBinding.ensureInitialized();
  final CoreBinding core;
  try {
    core = (open ?? CoreBinding.open)(spec);
  } on ArgumentError {
    runApp(
      const CoreUnavailableScreen(reason: CoreUnavailableReason.loadFailed),
    );
    return;
  }
  if (core.abiVersion() >> 16 != FML_ABI_MAJOR) {
    runApp(
      const CoreUnavailableScreen(reason: CoreUnavailableReason.abiMismatch),
    );
    await core.dispose();
    return;
  }
  try {
    await appEntry(buildPorts(), core);
  } catch (_) {
    await core.dispose();
    rethrow;
  }
}

/// 冒烟显示核心ABI及真实端口快照；只将Unsupported转成占位说明。
Future<void> smokeEntry(PlatformPorts ports, CoreBinding core) async {
  final abi = core.abiVersion();
  String runtime;
  try {
    final s = await ports.runtime.snapshot();
    runtime =
        'os: ${s.os}\nosVersion: ${s.osVersion}\nlocale: ${s.locale}\n'
        'availMemBytes: ${s.availMemBytes}\ndpiScale: ${s.dpiScale}\n'
        'abi: ${s.abi}\ngpuAvailable: ${s.gpuAvailable}';
  } on FmlException catch (e) {
    if (e.code != 'PLATFORM_UNSUPPORTED') rethrow;
    runtime = '运行时信息待平台卡实现';
  }
  runApp(
    MaterialApp(
      home: Scaffold(
        body: SafeArea(
          child: SingleChildScrollView(
            child: Column(
              children: [
                Text('ABI ${abi >> 16}.${abi & 0xffff}'),
                Text(runtime),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

/// 核心不可用的固定原因，不携带原始异常文本。
enum CoreUnavailableReason {
  /// 动态库加载失败。
  loadFailed,

  /// ABI主版本不兼容。
  abiMismatch,
}

/// 不进入业务页，仅显示固定中文与退出按钮。
final class CoreUnavailableScreen extends StatelessWidget {
  /// 创建核心不可用页。
  const CoreUnavailableScreen({super.key, required this.reason});

  /// 已归类的失败原因。
  final CoreUnavailableReason reason;
  @override
  Widget build(BuildContext context) => MaterialApp(
    home: Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              reason == CoreUnavailableReason.loadFailed
                  ? '核心组件加载失败，请重新安装'
                  : '核心版本不匹配，请重新安装',
            ),
            TextButton(onPressed: SystemNavigator.pop, child: const Text('退出')),
          ],
        ),
      ),
    ),
  );
}
