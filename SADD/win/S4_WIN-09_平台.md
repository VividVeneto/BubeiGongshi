### WIN-09 应用内提醒、托盘与开机自启

**目标**：在应用运行或驻留托盘时按时提醒复习（托盘通知与任务栏闪烁），提供托盘菜单、关闭到托盘与可选开机自启。

**范围**
- 包含：`NotificationScheduler` 端口实现（应用内定时）；托盘图标、菜单与通知（`Shell_NotifyIconW`）；任务栏闪烁；`TrayPresence`（WIN-06 定义）实现与登记；开机自启（HKCU Run）；设置页“提醒与托盘”区。
- 不包含：提醒时刻、正文与重排时机（CORE-20）；提醒设置页（CORE-49）；通知点击后的导航（CORE-36 订阅 `taps()`）；窗口隐藏与退出流程（WIN-06）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-20、CORE-36、WIN-06、WIN-17

**接口契约**

实现的端口与接缝（逐字摘录，定义见 CORE-04、WIN-06）：

```dart
abstract interface class NotificationScheduler {
  Future<bool> requestPermission();                           // 已授权或无需授权返回 true
  Future<void> scheduleDailyReminder(LocalTime time, String body); // 只保留一个每日提醒，重复调用替换；body 只含待复习数量
  Future<void> cancelAll();
  Stream<void> taps();                                        // 用户点击提醒通知；应用由通知冷启动时，首个订阅者也收到这一次
}
abstract interface class TrayPresence {          // WIN-09 登记；未登记时关闭即退出
  bool get iconReady;                            // 托盘图标已创建成功
  Future<void> hideToTray();
  Future<void> destroy();                        // 幂等，停止定时并移除托盘图标
}
```

本卡实现（`app/lib/platform/windows/notify/`）：

```dart
final class WindowsNotificationScheduler implements NotificationScheduler {
  WindowsNotificationScheduler(this.prefs);    // WIN-06 WindowsPrefs；requestPermission 恒返回 true
  final WindowsPrefs prefs;
}
final class WindowsTray implements TrayPresence { WindowsTray(this.nav, this.shell); final AppNavigator nav; final WindowsShell shell; }
void installWindowsTray(CompositionContext ctx);
// 登记 TrayPresence；向 SettingsSections 加入 order 75 的“提醒与托盘”区；firstFrameHooks order 10：创建托盘图标，成功后置 iconReady（--minimized 时窗口自始未显示，失败由 WIN-06 order 15 兜底显示）；不经顺序启动钩子，不等待档案打开；
// 追加到 ports_windows.dart 的 platformInstallers（须位于 installWindowsShell 之后）（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
```

```text
MethodChannel "fml/windows/tray"（app/windows/runner/tray_channel.cpp）
  create {tooltip}                 → null   NOTIFYICONDATAW（uVersion NOTIFYICON_VERSION_4，图标取 exe 资源）
  notify {title, body}             → null   NIF_INFO 通知（Windows 10/11 显示为系统通知）；窗口可见时另调 FlashWindowEx(FLASHW_TRAY | FLASHW_TIMERNOFG)
  destroy                          → null   NIM_DELETE，重复调用成功；取消Timer/订阅并清iconReady
  autostart.get → bool；autostart.set {enabled, command} → null   HKCU\Software\Microsoft\Windows\CurrentVersion\Run 值 "BubeiGongshi"
  Dart 收到的调用：trayClick（左键单击）、menu {id: "open"|"study"|"recognize"|"exit"}（右键菜单）、notifyClick（NIN_BALLOONUSERCLICK）、
                  timeChanged（WM_TIMECHANGE）、resumed（WM_POWERBROADCAST PBT_APMRESUMEAUTOMATIC）
定时：scheduleDailyReminder 写 prefs reminder.time = "HH:MM"、reminder.body，并以 Timer 安排到下一次该时刻；cancelAll 删除两项并取消 Timer；
      Timer 到时：prefs reminder.last_shown_day ≠ 今天 → notify("背公式", body)，写 last_shown_day，安排明天；
      timeChanged 或 resumed：重新计算 Timer；若当天时刻已在过去 2 h 内且今天未提醒 → 立即提醒一次；
      应用启动时只安排，不补发
taps()：notifyClick 时发送一次；同时 show 主窗口（WIN-06 通道 show）
托盘菜单：open → 显示主窗口；study → 显示并 nav.go('/study')；recognize → 显示并 nav.go('/recognize')；exit → shell.exitApp()
开机自启命令："<installRoot>\BubeiGongshi.exe" --minimized；installRoot 下无 BubeiGongshi.exe（开发构建）时开关禁用并说明
“提醒与托盘”区：链接WIN-06“关闭行为”控件；开关“开机自启并驻留托盘”（默认关）、
               说明“应用完全退出后不会提醒；需要每日提醒请开启开机自启并驻留托盘”
```

- 错误码：通道失败映射为 `PLATFORM_IO`；本卡不新增错误码。

Explorer恢复：注册`RegisterWindowMessageW(L"TaskbarCreated")`，WIN-01平台线程delegate收到时重新NIM_ADD并NIM_SETVERSION，成功才置iconReady；失败置false并显示主窗口（含--minimized）。退出先取消重建标志/委托再NIM_DELETE，不能退出后重添。图标重建不补发提醒；WIN-06只经TrayPresence.destroy统一销毁，原生窗口最终清理也须幂等兜底。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

产品约束追踪：见README §6 Q15、Q41；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 不安装服务、计划任务或常驻后台进程；应用完全退出时不保证提醒（在设置区说明）。
- 提醒正文只含待复习数量（CORE-20 给出），不含公式内容；提醒全流程不发网络请求。
- 托盘图标在应用运行期间常驻；退出流程（WIN-06 `exitApp`）前调用 `destroy`，避免残留图标。
- 不使用 Toast COM 激活与 AppUserModelId 注册（系统通知由 `NIF_INFO` 呈现）；专注助手开启时系统可能隐藏通知，任务栏闪烁仍生效。
- 卸载时自启值由 WIN-02 删除。

**验收标准**：测试方案全文见 [Test/win/S4_WIN-09_TEST.md](../Test/win/S4_WIN-09_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 380 行；`app/lib/platform/windows/notify/` 与 `app/windows/runner/tray_channel.cpp`（同属 `app/` 构建单元）。

---

