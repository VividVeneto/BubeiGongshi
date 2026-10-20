### AND-08 本地通知与提醒自检

**目标**：不依赖厂商推送与网络，按 CORE-20 安排的时刻每日本地提醒复习；提供提醒可靠性自检与国产 ROM 设置跳转。

**范围**
- 包含：`NotificationScheduler` 端口实现（AlarmManager 非精确闹钟、通知渠道、点击回调、开机与时区变化后重排）；`ReminderSelfCheck` 实现（CORE-20 定义）与按厂商的设置跳转表；Kotlin 侧 `ReminderBridge.kt`、`ReminderReceiver.kt`、`RomSettings.kt`。
- 不包含：提醒时刻与正文的生成、重排时机（CORE-20 `ReminderService`）；提醒设置页与自检页界面（CORE-49）；通知权限对话框（AND-02 `PermissionService`）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-20、AND-02、AND-15

**接口契约**

实现的端口与接缝（逐字摘录，定义见 CORE-04、CORE-20）：

```dart
abstract interface class NotificationScheduler {
  Future<bool> requestPermission();                           // 已授权或无需授权返回 true
  Future<void> scheduleDailyReminder(LocalTime time, String body); // 只保留一个每日提醒，重复调用替换；body 只含待复习数量
  Future<void> cancelAll();
  Stream<void> taps();                                        // 用户点击提醒通知；应用由通知冷启动时，首个订阅者也收到这一次
}
abstract interface class ReminderSelfCheck {
  Future<List<ReminderCheckItem>> run();
  Future<void> openFix(String id);   // 打开对应系统设置页；返回后界面重新 run()
}
```

本卡实现（`app/lib/platform/android/notify/`）：

```dart
final class AndroidNotificationScheduler implements NotificationScheduler {
  AndroidNotificationScheduler(this.permissions);   // AND-02；requestPermission：API 33+ 请求 postNotifications，以下版本查询通知是否被关闭
  final PermissionService permissions;
}
final class AndroidReminderSelfCheck implements ReminderSelfCheck { const AndroidReminderSelfCheck(); }
void installAndroidReminders(CompositionContext ctx) =>
    ctx.features.register<ReminderSelfCheck>(const AndroidReminderSelfCheck());   // 追加到 ports_android.dart 的 platformInstallers（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
```

```text
MethodChannel "fml/android/reminder"（ReminderBridge.kt）
  schedule {hour, minute, body}  → null   存入 SharedPreferences（fml_reminder：hour、minute、body、last_shown_day），
                                          以 AlarmManager.setAndAllowWhileIdle(RTC_WAKEUP) 安排下一次该时刻（已过则明天）
  cancel                         → null   取消闹钟并清空存储
  consumeLaunchTap               → bool   本次启动是否由提醒通知打开（读取后清除）
  selfCheck                      → [{id, state:"ok"|"warn"|"unknown", can_fix, detail?}]
  openFix {id}                   → null
EventChannel "fml/android/reminder/taps"  应用运行中点击通知时发送一次
ReminderReceiver：
  闹钟到达 → 若 last_shown_day ≠ 今天：在渠道 "study_reminder"（重要性 DEFAULT）发通知 id 1001，正文 = 存储的 body，
             点击打开MainActivity（singleTop，PendingIntent.FLAG_IMMUTABLE | FLAG_UPDATE_CURRENT；extra fml_reminder_tap=true，唯一tap_id）；AND-01转发onNewIntent到本模块，核验/消费tap_id后推taps事件，移除已消费extra，冷启动同样只投递一次，记录 last_shown_day；然后安排明天同一时刻
  BOOT_COMPLETED、TIMEZONE_CHANGED、TIME_SET、MY_PACKAGE_REPLACED → 按存储重新安排（无存储则不动作）
taps()：订阅时先调用 consumeLaunchTap，为 true 则先发一次；之后转发 EventChannel 事件
selfCheck 项（id → 判定，标题文案在 Dart 侧）：
  permission              NotificationManagerCompat.areNotificationsEnabled()           can_fix：打开应用通知设置
  scheduled               存储中有提醒且下一次闹钟已安排（未开启提醒时 state = ok）        can_fix = false
  battery_optimization    PowerManager.isIgnoringBatteryOptimizations()                can_fix：ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS
  background_restriction  API 28+ ActivityManager.isBackgroundRestricted() 为 false     can_fix：应用详情页
  autostart               无法检测，恒 state = unknown 且 detail 说明“部分手机需允许自启动”     can_fix：RomSettings 表中的厂商页面
  RomSettings：不内置未经核实的OEM私有ComponentName。所有厂商统一ACTION_APPLICATION_DETAILS_SETTINGS(package:本应用)，异常时ACTION_SETTINGS；只有锁定ROM实测并记D后才允许将候选列入版本化资源表，resolveActivity成功才尝试，失败继续公共兜底。
```

- 错误码：`PLATFORM_PERMISSION_DENIED`（`scheduleDailyReminder` 时通知被关闭，CORE-04 登记）；本卡不新增错误码。

notify/strings.dart映射：permission标题“通知权限”，detail拒绝时“请在系统设置中允许通知”；scheduled标题“每日提醒”，未开启detail“尚未开启提醒”；battery_optimization标题“电池优化”，detail“系统可能延迟提醒”；autostart标题“自启动设置”，detail“无法自动检测，请在应用详情中检查厂商设置”。通道只提供id/state/can_fix/detail?，Dart映射为CORE-20必填title，未知id显示未知检查项并记日志；autostart按说明信息呈现，不能将不可检测写成确定配置错误。

ReminderCheck稳定ID集合固定为本卡自检表全部项；background_restriction标题“后台运行限制”，detail说明当前后台限制状态，can_fix仅对应应用详情页。文案映射测试枚举全覆盖，未知ID作为协议失败显式显示“未知检查项”，不静默丢弃。

selfCheck可确定布尔判定true→state=ok、false→warn；仅autostart与不支持的系统探测返回unknown。对unknown不读取OEM私有设置键，不把未检测状态计为错误。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

**实现约束**
- 不使用厂商推送或 FCM，不申请 `SCHEDULE_EXACT_ALARM` / `USE_EXACT_ALARM`，不使用 WorkManager 或前台服务；非精确闹钟允许系统推迟（通常数分钟）。
- 应用多日未打开时，后续每天沿用最近一次 `scheduleDailyReminder` 给出的正文（CORE-20 无法在后台计算到期数）；正文只含数量，不含公式内容；通知只有点击动作，不提供“记得/忘了”快捷评分（评分须来自客观判定，CORE-19）。
- `RECEIVE_BOOT_COMPLETED` 权限与 Receiver 声明在 AND-02 清单白名单内登记（本卡提交时同步更新 `check_android_manifest.py` 白名单的这一项）。
- 同一天最多显示一次提醒（`last_shown_day` 判断），时区变化后按新时区的本地时刻重排。

**验收标准**：测试方案全文见 [Test/and/S4_AND-08_TEST.md](../Test/and/S4_AND-08_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 380 行；`app/lib/platform/android/notify/` 与 `app/android/.../` 下的 ReminderBridge、ReminderReceiver、RomSettings 三个 Kotlin 文件（同属 `app/` 构建单元）。

---

