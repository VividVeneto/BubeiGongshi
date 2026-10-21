### AND-05 生命周期、进程恢复与运行时信息

**目标**：向共享层提供 Android 生命周期事件与运行时信息，并保证应用被系统回收后能经 Flutter 状态恢复回到原页面。

**范围**
- 包含：`AppLifecycle` 与 `RuntimeInfo` 端口实现；`onTrimMemory` 映射为 `lowMemory`；Activity 重建与 Flutter 状态恢复的平台配置；配置变化（旋转、平板、折叠屏、分屏、深色、字号）时不重建 Activity 的生命周期衔接（清单属性见 AND-02 接口契约窗口属性表）。
- 不包含：收到事件后的业务反应（CORE-46 在 `resumed` 时同步、CORE-40 在 `paused/lowMemory` 时卸载模型、CORE-37 草稿去抖、CORE-19 学习游标）；路由恢复的共享配置（CORE-36 `restorationScopeId`）；双栏布局（共享界面卡）；系统栏、edge-to-edge、启动主题与跟随系统字号、深色、动画缩放的界面处理（AND-13）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-36、AND-01、AND-02、AND-15

**接口契约**

实现的端口（CORE-04，逐字摘录）：

```dart
abstract interface class AppLifecycle {
  Stream<LifecycleEvent> events();                            // 广播流
}
abstract interface class RuntimeInfo {
  Future<RuntimeSnapshot> snapshot();
}
```

本卡实现：

```dart
// app/lib/platform/android/lifecycle/android_lifecycle.dart
final class AndroidAppLifecycle implements AppLifecycle {
  AndroidAppLifecycle();   // WidgetsBindingObserver：resumed → resumed；paused → paused；detached → detached；
                           // inactive、hidden 不转发；通道事件 trimMemory(level为10/15或≥40，排除20 UI_HIDDEN) → lowMemory
}
// app/lib/platform/android/lifecycle/android_runtime.dart
final class AndroidRuntimeInfo implements RuntimeInfo { AndroidRuntimeInfo(); }
```

```text
EventChannel  "fml/android/lifecycle"   Kotlin MainActivity.onTrimMemory(level) → {"trimMemory": level}；同一等级 10 s 内只发一次
MethodChannel "fml/android/runtime"     snapshot → {api_level: int, locale: "zh-CN", avail_mem: int, density: double, abi: string, gpu: bool}
  映射：os='android'；osVersion=api_level 的十进制字符串；availMemBytes=ActivityManager.MemoryInfo.availMem；
        dpiScale=density（DisplayMetrics.density，1.0=160 dpi）；abi=Build.SUPPORTED_ABIS[0]；gpuAvailable=false（V1 不探测）
AndroidManifest 中 MainActivity 的 configChanges、resizeableActivity、windowSoftInputMode 与 enableOnBackInvokedCallback
  以 AND-02 接口契约窗口属性表 为唯一定义，本卡不另列取值
```

- 本卡不新增错误码；通道调用失败时 `snapshot()` 返回 `availMemBytes=0`、`gpuAvailable=false` 的保底值，不抛异常。

- 测试诊断通道 fml/android/lifecycle 的 createCount() → int，由 MainActivity.onCreate 自增；同进程计数起始 1，进程重启重新计数；AND-13 windowMetrics 只转发此值。createCount 只在 debug 与 profile 构建（`BuildConfig.BUILD_TYPE != "release"`）中响应，release 构建返回 notImplemented，trimMemory 事件不受影响。

API34+系统不再承诺发送运行中RUNNING_LOW/CRITICAL；模型回收仍依靠正常paused和显式lowMemory。adb强发仅验证映射，不代表系统真实分发；UI_HIDDEN只由生命周期paused表达，不额外lowMemory。10秒去重按事件等级；fake测试10/15/20/40/60/80逐一断言。杀进程/旋转由AND-12主机驱动，进程内测试只检查存活期间状态。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

产品约束追踪：见README §6 Q17、Q38；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 不使用常驻服务和前台服务；后台不做周期性网络轮询。
- `lowMemory` 只发事件，不在平台层释放任何东西；各模块自行监听释放缓存，不得丢弃未保存草稿。
- 进程被回收后的恢复只依赖 Flutter 状态恢复（CORE-36 已设 `restorationScopeId`）；本卡不额外持久化路由，不写用户内容。
- 系统栏、edge-to-edge 与启动主题由 AND-13 统一实现（`AndroidSystemBars` 订阅 CORE-55 `AppearanceController.resolvedChanges`，`styles.xml` 定义启动主题）；本卡与共享界面不调用 `SystemChrome.setSystemUIOverlayStyle`。
- 与 AND-13 的衔接：AND-13 `configChanges` 列出的变化不重建 Activity，Flutter `State` 原样保留，本卡不发额外事件；清单外的配置变化、“不保留活动”与后台回收导致 Activity 或进程重建时，走本卡的 Flutter 状态恢复回到原路由。

主机作业归AND-12；本卡可用Fake事件/通道完成阶段内自动验收，S7真机证据另记。

**验收标准**：测试方案全文见 [Test/and/S2_AND-05_TEST.md](../Test/and/S2_AND-05_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 190 行；`app/lib/platform/android/lifecycle/`、`app/`。组件估算：Dart生命周期与RuntimeInfo约 80 行，Kotlin事件、内存去重与诊断约 85 行，恢复配置和模块接入约 25 行。只计本卡交付实现及附属接入代码；验证测试、夹具与静态配置/资源数据不计。

