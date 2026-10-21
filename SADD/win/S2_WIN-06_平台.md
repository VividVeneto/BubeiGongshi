### WIN-06 窗口、DPI、生命周期与单实例

**目标**：提供高 DPI 清晰、多显示器位置正确、单实例运行的桌面窗口，实现 `AppLifecycle` 与 `RuntimeInfo` 端口，并提供 Windows 偏好存储与退出流程。

**范围**
- 包含：`AppLifecycle`、`RuntimeInfo` 端口实现；窗口位置与最大化状态记忆及离屏纠正；单实例；关闭与退出流程；低内存通知；`WindowsPrefs`（HKCU 偏好）；`TrayPresence` 接缝；设置页“窗口”区。
- 不包含：托盘图标与菜单（WIN-09，经 `TrayPresence` 接入）；快捷键（WIN-08）；布局断点、深色模式、高对比度与字体缩放（CORE-55 共享界面按 `MediaQuery` 处理）；最小窗口、标题栏深浅色、输入方式与设备偏好接缝（WIN-15）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-36、WIN-01、WIN-17

**接口契约**

实现的端口（CORE-04，逐字摘录）：

```dart
abstract interface class RuntimeInfo {
  Future<RuntimeSnapshot> snapshot();
}
abstract interface class AppLifecycle {
  Stream<LifecycleEvent> events();                            // 广播流
}
```

本卡实现（`app/lib/platform/windows/window/`）：

```dart
final class WindowsRuntimeInfo implements RuntimeInfo { const WindowsRuntimeInfo(); }
final class WindowsLifecycle implements AppLifecycle { WindowsLifecycle(); }
final class WindowsPrefs {                       // HKCU\Software\BubeiGongshi\Prefs 下的字符串值；只存设备偏好，不存用户内容
  Future<String?> get(String key); Future<void> set(String key, String? value);   // key 匹配 ^[a-z0-9_.]{1,64}$；null 删除
}
abstract interface class TrayPresence {          // WIN-09 登记；未登记时关闭即退出
  bool get iconReady;                            // 托盘图标已创建成功
  Future<void> hideToTray();
  Future<void> destroy();                        // 幂等，停止定时并移除托盘图标
}
final class WindowsShell {
  WindowsShell(this.lifecycle, this.prefs, this.features);
  Future<void> exitApp();                        // 发 paused、detached → TrayPresence.destroy（至多200 ms）→ 总等待上限800 ms → 通道 destroy
}
void installWindowsShell(CompositionContext ctx, WindowsPrefs prefs);  // 登记ports_windows构造并共享的prefs、WindowsShell；向 SettingsSections 加入 order 80 的“窗口”区；订阅关闭请求；
// firstFrameHooks order 15（最小化兜底）：有 --minimized 且 TrayPresence 未登记或 iconReady 为 false → 通道 show
```

```text
MethodChannel "fml/windows/window"（app/windows/runner/window_channel.cpp）
  runtime                  → {os_version: "10.0.22631", avail_mem: int, gpu: bool}   RtlGetVersion、GlobalMemoryStatusEx、DXGI 枚举到非软件适配器
  destroy                  → null   DestroyWindow → PostQuitMessage
  hide / show              → null   show 时 SW_RESTORE + SetForegroundWindow
  prefs.get {key} / prefs.set {key, value?}
  Dart 收到的调用：lifecycle {event: "resumed"|"paused"|"lowMemory"}、closeRequested
事件来源：WM_SIZE SIZE_MINIMIZED 或窗口隐藏 → paused；还原、显示 → resumed（失去焦点不算 paused）；
          CreateMemoryResourceNotification(LowMemoryResourceNotification) + RegisterWaitForSingleObject（一次性，60 s 后重新登记）→ lowMemory
关闭：WM_CLOSE 不直接销毁，改发 closeRequested；Dart 按偏好 window.close_action（"exit" 默认，见 README §6 Q15；或 "tray"，后者仅 TrayPresence 已登记时生效）
      调 TrayPresence.hideToTray() 或 WindowsShell.exitApp()
单实例：main.cpp 在创建窗口前 CreateMutexW(L"Local\\BubeiGongshi.SingleInstance")；已存在 → 每100 ms调用FindWindowW(L"BubeiGongshiMainWindow", nullptr)，最多10次；
        超时提示“应用正在启动，请稍后重试”，退出10且不创建第二窗口、不打开库；找到后，
        GetWindowThreadProcessId 后 AllowSetForegroundWindow(该 PID)，SendMessageTimeoutW(WM_COPYDATA, SMTO_ABORTIFHUNG, 5000 ms) 发送
        COPYDATASTRUCT{dwData = 0x464D4C31（"FML1"），lpData = argv[1..] 的 UTF-16LE 串，每个参数以 NUL 结束、末尾再加一个 NUL，
        cbData ≤ 32 KiB（超出时截到最后一个完整参数）}，然后以退出码 10（仅转发，非启动失败）退出；
        已运行实例只接受 dwData 匹配的消息，V1 只做 SW_RESTORE + SetForegroundWindow（参数暂不处理）；WIN-16 启动器激活时使用同一格式
窗口位置：WM_EXITSIZEMOVE 与关闭时 GetWindowPlacement 写入 HKCU\Software\BubeiGongshi\Window\Placement（REG_BINARY）；
          启动时读取，MonitorFromRect(rcNormalPosition, MONITOR_DEFAULTTONULL) 为空则在主显示器工作区居中 1280×800（不超过工作区）
启动参数：--minimized → runner 首帧回调不调用 Show()（模板默认首帧后 Show；窗口保持创建时的隐藏状态，避免闪现），首帧照常渲染；
          firstFrameHooks order 10 由 WIN-09 创建托盘图标并置 iconReady，order 15 由本卡兜底显示，不能留下不可进入的隐藏窗口；
          无 --minimized 时首帧后 Show。启动器透传验证 nonce，不改变是否渲染首帧。
```

- `RuntimeSnapshot` 取值：`os = 'windows'`，`abi = 'x64'`，`locale` 取 `PlatformDispatcher.instance.locale`，`dpiScale` 取当前视图的 `devicePixelRatio`，其余来自通道 `runtime`。
- 错误码：通道失败映射为 `PLATFORM_IO`；本卡不新增错误码。

窗口设置区order80的唯一控件：关闭行为单选`window.close_action`（exit默认/tray；无iconReady时按exit并说明托盘尚未可用）；“记住窗口位置”开关`window.remember_position`（字符串true默认/false）。false时启动使用默认居中1280×800且不读写Placement；true时Placement的WINDOWPLACEMENT同时保存正常位置/最大化状态，按离屏规则纠正。损坏或未知偏好回退默认。WIN-09只链接此关闭行为控件，不另造第二份；自启仍归WIN-09。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

**实现约束**
- runner 窗口类名改为 `BubeiGongshiMainWindow`；清单 PerMonitorV2 由 WIN-01 设置；DPI 变化由 Flutter 重新布局，公式按 DisplayList 重新绘制，不缩放位图。
- 单实例保证同一数据库只有一个写者进程（CORE-13 单写者）。
- 退出流程不做数据保存逻辑：学习进度由 CORE-39 每步写库，其他功能在 `paused/detached` 时自行收尾；800 ms 后无论如何退出。
- 偏好键只允许设备级设置（窗口、托盘、自启、快捷键、外观 `appearance.v1`），由各 WIN 卡在本卡登记的 `WindowsPrefs` 上读写；卸载时整键删除（WIN-02）。

**验收标准**：测试方案全文见 [Test/win/S2_WIN-06_TEST.md](../Test/win/S2_WIN-06_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 680 行；`app/lib/platform/windows/window/`、`app/windows/runner/`、`app/windows/runner/window_channel.cpp`、`app/`。组件估算：原生窗口位置与离屏纠正约 85 行，runtime/注册表偏好约 105 行，低内存与生命周期/消息清理约 130 行，单实例与COPYDATA约 110 行，Dart端口/WindowsShell/退出约 200 行，设置区与聚合接入约 50 行。分阶段：① runner生命周期与单实例约 430 行；② Dart状态与设置约 250 行；各阶段以替身隔离后续能力，分别可构建、验收与提交，未交付阶段不声明通过。只计本卡交付实现及附属接入代码；验证测试、夹具与静态配置/资源数据不计。

