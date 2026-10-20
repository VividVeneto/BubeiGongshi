### AND-13 Android 触摸交互与横竖屏适配

**目标**：让共享界面在 Android 手机与平板上按触摸操作优化：经 CORE-55 接缝注入输入方式、触感与系统动画缩放；系统栏、刘海与软键盘为内容让位；横竖屏跟随系统旋转设置，旋转、分屏与窗口尺寸变化时界面状态不丢（README §6 Q17、Q18）。

**范围**
- 包含：CORE-55 接缝的 Android 实现（`AndroidInputModalitySource`、`AndroidHaptics`、`AndroidMotionScale`）；跟随 `AppearanceController.resolvedChanges` 的系统栏样式 `AndroidSystemBars`；安装点 `installAndroidInteraction` 及其在 `ports_android.dart` 中的登记行；引用AND-02唯一的MainActivity窗口属性表（本卡不维护清单属性）；启动主题、edge-to-edge 与 displayCutout 模式（`styles.xml`）；Kotlin 侧 `InteractionHandler.kt`（触感、动画缩放、窗口度量）；系统返回、内边距与屏幕方向的行为对照表及其真机验收。
- 不包含：`DevicePrefStore`（使用 CORE-55 默认实现，见实现约束）；宽度分档、矮高度、密度、组件、动效时长与“减少动效”处理（CORE-55）；返回处理逻辑（CORE-36 路由与各页面 `PopScope`，本卡只给对照表并做真机验收）；生命周期与进程恢复（AND-05）；权限与清单审计脚本（AND-02，按AND-02唯一属性表审计）；相机界面的方向处理（AND-04）；软键盘快捷栏与触控笔策略（AND-07）；动态取色（ADR-V5-24 不做）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-36、CORE-55、AND-01、AND-02、AND-05、CORE-58、AND-15

**接口契约**

实现的接缝（逐字摘录，定义见 CORE-55 §接口契约）：

```dart
abstract interface class InputModalitySource {       // 平台登记（AND-13：touch；WIN-15：pointer，平板模式或触摸时 touch）；未登记时 initial = touch
  InputModality get initial; Stream<InputModality> get changes;
}
abstract interface class UiFeedbackSink { void emit(UiFeedbackKind kind); }   // 可选（AND-13 触感）；未登记为空操作；共享界面统一经 FmlFeedback.emit(context, kind) 调用，pref.haptics 为 false 时不转发
abstract interface class MotionScaleSource { double get scale; Stream<double> get changes; }   // 可选（AND-13 系统动画时长缩放），取值 0～10
// 只读使用：AppearanceController 的 pref（AppearancePref.haptics）、resolved、resolvedChanges（ResolvedAppearance.brightness）
```

本卡实现：

```dart
// app/lib/platform/android/interaction/android_modality.dart
final class AndroidInputModalitySource implements InputModalitySource {
  const AndroidInputModalitySource();   // initial = InputModality.touch；changes 为空流
                                        // 外接鼠标与触控笔由 CORE-55 InputModalityScope 根部 Listener 按 PointerDeviceKind 切换
}
// app/lib/platform/android/interaction/android_haptics.dart
final class AndroidHaptics implements UiFeedbackSink {
  AndroidHaptics(this.appearance, {this.minInterval = const Duration(milliseconds: 80)});
  final AppearanceController appearance;
  final Duration minInterval;            // 同一 kind 在 minInterval 内只触发一次
  // emit：appearance.pref.haptics 为 false → 直接返回；否则调用通道 haptic {kind}，不等待结果、吞掉通道异常
}
// app/lib/platform/android/interaction/android_motion_scale.dart
final class AndroidMotionScale implements MotionScaleSource {
  AndroidMotionScale();                  // scale 初值 1.0
  Future<void> start();                  // 读一次 animatorScale，再订阅事件流；值截到 0～10，与当前值不同才发出
}
// app/lib/platform/android/interaction/android_system_bars.dart
final class AndroidSystemBars {
  AndroidSystemBars(this.appearance, this.runtime);   // runtime：CORE-04 RuntimeInfo（取 API 级别）
  final AppearanceController appearance;
  final RuntimeInfo runtime;
  Future<void> attach();   // setEnabledSystemUIMode(edgeToEdge)；首帧回调中按 appearance.resolved 设一次样式，并订阅 resolvedChanges
}
// app/lib/platform/android/interaction/install.dart
void installAndroidInteraction(CompositionContext ctx);
// 登记 InputModalitySource、UiFeedbackSink、MotionScaleSource与唯一ShellKeyHandler(AndroidShellKeys)；AppearanceController 用 ctx.features.require 取得；
// 创建 AndroidSystemBars 并 attach、AndroidMotionScale.start（均不 await）；不登记 DevicePrefStore
// ports_android.dart：向 platformInstallers 列表追加 installAndroidInteraction（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
```

```text
MethodChannel "fml/android/interaction"（InteractionHandler.kt，挂在 MainActivity）
  haptic {kind: "tap" | "selection" | "correct" | "wrong" | "warning"} → null
        window.decorView.performHapticFeedback(下表常量)，不带 FLAG_IGNORE_GLOBAL_SETTING；不用 Vibrator，不申请 VIBRATE
  animatorScale → double（Settings.Global.ANIMATOR_DURATION_SCALE；读取失败为 1.0）
  windowMetrics → {smallest_width_dp, orientation: "portrait" | "landscape", in_multi_window: bool,
                   cutout_dp: {left, top, right, bottom}, nav_mode: "gesture" | "three_button" | "unknown", create_count: int /* 转发 AND-05 lifecycle.createCount */}
                   只供集成测试与诊断使用，界面布局不读（布局只按 MediaQuery，CORE-55）
EventChannel  "fml/android/interaction/events"
  ContentObserver 监听 ANIMATOR_DURATION_SCALE → {"animatorScale": double}
```

a. 触感映射

| UiFeedbackKind | 含义（CORE-55） | API 30 及以上 | API 26～29 |
| --- | --- | --- | --- |
| `tap` | 主按钮、作答选项按下 | `VIRTUAL_KEY` | `VIRTUAL_KEY` |
| `selection` | 开关、分段选择、档位切换 | `CLOCK_TICK` | `CLOCK_TICK` |
| `correct` | 判对 | `CONFIRM` | `VIRTUAL_KEY` |
| `wrong` | 判错 | `REJECT` | `LONG_PRESS` |
| `warning` | 破坏性操作确认、校验失败 | `LONG_PRESS` | `LONG_PRESS` |

触发需同时满足两项：应用内“触感反馈”开关（`AppearancePref.haptics`，CORE-58 外观页，默认开）为开；系统“触摸振动”为开（由 `performHapticFeedback` 不带忽略标志自然保证）。

b. MainActivity 窗口属性：只引用 AND-02 的唯一属性表。

c. 启动主题与系统栏

| 项 | 取值或规则 |
| --- | --- |
| `values/styles.xml` 的 LaunchTheme、NormalTheme 背景 | `#F7F7FB`（群青预设浅色 surface，CORE-55） |
| `values-night/styles.xml` 同上 | `#121318`（群青深色 surface） |
| `values-v31`、`values-night-v31` 的 `windowSplashScreenBackground` | 与上两行相同 |
| 状态栏、导航栏底色 | 透明（edge-to-edge），内容绘制到系统栏之后，由内边距让位 |
| `values-v28` 的 `windowLayoutInDisplayCutoutMode` | `shortEdges` |
| 状态栏与导航栏对比度强制（API 29+） | 关闭（`systemStatusBarContrastEnforced`、`systemNavigationBarContrastEnforced` 为 false） |
| 图标明暗 | `resolved.brightness` 为 light → 深色图标；dark → 浅色图标 |
| 更新时机 | 首帧后设一次；`resolvedChanges` 每次发出时更新；与上次样式相同则不调用 |

启动背景不读偏好（避免拖慢启动），用户选了其他预设时由首帧切换。

d. 内边距与软键盘

| 来源 | Flutter 侧 | 处理 |
| --- | --- | --- |
| 状态栏、导航栏、手势条 | `MediaQuery.viewPadding`/`padding` | CORE-55 `AdaptiveScaffold` 的安全区；底部操作栏与底部导航下方留出导航栏高度，背景延伸到屏幕底边 |
| 刘海与挖孔 | 计入 `padding` 对应边（横屏时为左或右） | rail、侧栏与内容避开挖孔，背景仍铺满 |
| 系统手势区 | `MediaQuery.systemGestureInsets` | 不设手势排除区；从左右边缘手势区内起始的拖动交给系统返回 |
| 软键盘 | `MediaQuery.viewInsets.bottom`（API 30+ 随 `WindowInsetsAnimation` 逐帧变化） | 输入区与主操作上移到键盘之上；AND-07 快捷栏紧贴键盘 |

e. 系统返回（手势或返回键）

| 场景 | 系统返回的结果 | 界面上的可见等价按钮 |
| --- | --- | --- |
| 推入的二级页（详情、编辑、设置子页） | 回到上一页；编辑草稿已由 CORE-37 去抖保存 | 顶栏返回按钮 |
| 主导航中“学习”以外的根页 | 切到“学习”（`/study`） | 底部导航或 rail 的“学习” |
| “学习”根页 | 交给系统退到后台（Android 13+ 显示回到桌面的预测性动画）；不弹“再按一次退出” | 系统 Home |
| 学习会话中 | 进入暂停（与会话内“暂停”按钮同一动作，CORE-39），不直接离开 | 会话顶栏“暂停” |
| 底部面板、对话框、菜单 | 关闭它 | “关闭”按钮或点遮罩 |
| 公式库多选模式（CORE-54） | 退出多选 | 顶栏“取消” |

f. 屏幕方向与窗口变化

| 情形 | 行为 |
| --- | --- |
| 系统自动旋转开启 | 随设备方向在竖屏、横屏（含反向横屏）间切换，手机与平板相同 |
| 系统旋转锁定 | 保持当前方向；系统在旋转设备时显示的“旋转建议”按钮可用 |
| 平板判定 | 平台层不判定；共享界面只按窗口尺寸断点布局，`LayoutInfo.largeScreen`（最短边 ≥ 600 dp，Q18）由 CORE-55 计算 |
| 分屏、自由窗口、折叠屏展开或折叠 | 不重建 Activity，按新窗口尺寸重排 |
| 相机取景 | 见 AND-04 方向处理 |

- 错误码：无（通道失败时触感静默跳过、动画缩放取 1.0，不抛异常）。


LibraryBatchCommands（CORE-58）只在库列表scope生效、编辑文本焦点ignored：↑/↓/Home/End/PageUp/PageDown分别→library.batch.move.up/down/home/end/pageUp/pageDown，Shift组合对应library.batch.extend.up/down/home/end/pageUp/pageDown（每项均独立无参ID），Space→toggle，Ctrl+A→selectAll，Esc→clear，Enter→open，Delete→trash，Ctrl+T→editTags，Shift+F10/菜单键→menu，Ctrl+Z→undo；handled后不再执行页面默认动作，命令不可用返回ignored。Android由本卡AndroidShellKeys经early handler路由，不另加第二个ShellKeyHandler。


nav_mode默认unknown；不读取Settings.Secure的非公开navigation_mode键，不从insets高度猜导航模式。仅未来通过锁定SDK公开接口并有设备证据才填写gesture/three_button，变更先修此契约。unknown不阻碍按真实insets布局；M0分别手势/三键设备验证安全区。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

产品约束追踪：见README §6 Q41；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

实体库键唯一实现：app/lib/platform/android/interaction/android_shell_keys.dart 的AndroidShellKeys implements CORE-36 ShellKeyHandler，构造参数FeatureRegistry；handle(KeyEvent event,AppNavigator nav)从当前primaryFocus的FmlCommandScope读取命令，不直接依赖CORE-54（下游说明，非契约）。installAndroidInteraction登记一次ShellKeyHandler，在AppShell挂early handler前完成；后续AND-07不重复登记。输入焦点属于EditableText或存在composing区间时全部ignored；KeyUp ignored；KeyRepeat只允许move/extend方向，其他重复ignored；KeyDown按本卡LibraryBatchCommands映射，作用域不含命令/不可用则ignored，调用一次invoke成功返回handled。任何事件只能由外壳回调消费一次，不在页面再处理实体键。

**实现约束**
- 方向：`app/lib/` 与 `app/android/` 中不得调用 `SystemChrome.setPreferredOrientations` 或设置 `requestedOrientation`，清单中任何 Activity 不声明 `screenOrientation`（扫描测试与 AND-02 审计脚本检查）。
- 状态保持有两条路径：属性表中 `configChanges` 列出的变化不重建 Activity，Flutter 引擎与各页 `State`（输入、选区、滚动位置）原样保留，只按新尺寸重排；其余配置变化、开发者选项“不保留活动”与后台回收导致的重建，走 AND-05 的 Flutter 状态恢复回到原路由。两条路径都不额外持久化界面状态。
- 系统栏：全应用只有 `AndroidSystemBars` 调用 `SystemChrome.setSystemUIOverlayStyle` 与 `setEnabledSystemUIMode`；共享界面与其他平台卡不调用。Flutter `AppBar` 会按其背景亮度经 `AnnotatedRegion` 设置图标明暗，CORE-55 中顶栏背景取 surface，结果与本卡一致。
- 设备偏好：不登记 `DevicePrefStore`；CORE-55 默认 `FileDevicePrefStore` 写在 `root(StoreArea.database)/device_prefs/`，位于 AND-06 的 `noBackupFilesDir` 下且被备份与迁移规则排除，满足 Q19“按设备保存”；不使用 SharedPreferences。
- 跟随系统设置且不重建 Activity：字号（`fontScale` → `textScaler`，平台层不设上限）；深色（`uiMode` → `platformBrightness`，外观模式为“跟随系统”时生效）；动画时长缩放（`MotionScaleSource`，为 0 时 CORE-55 `FmlMotion.scaled` 得 0）；无障碍“移除动画”（Flutter `disableAnimations`）与高对比度文字（`MediaQuery.highContrast`）由 CORE-55 处理，本卡不另读。
- 触控目标：本端平台代码自带的可点击控件（AND-07 快捷栏、AND-04 相机界面）不小于 48 dp，与 CORE-55 触摸密度一致；主操作的拇指可达位置由 CORE-55 布局保证，本卡做真机验收。
- 每个手势操作都有可见按钮等价（返回见上表 e；长按、滑动的等价按钮由各共享卡提供），本卡真机验收逐项核对。
- 性能：通道调用不阻塞 UI 线程；触感不等待结果；系统栏只在样式变化时调用。相关预算为 CORE-01 预算表“点击到可见反馈（按压态出现）”“旋转与窗口尺寸变化（到新布局首帧）”“主题切换（预设或外观模式，到新主题首帧）”，由 AND-12 测量。
- 应用内预测性返回的跟手预览转场 V1 不做：应用内页面转场仍用 CORE-55 的页面转场，只启用系统级（回到桌面、跨应用）预测性返回动画（见 README §6 Q25）。
- 外部前提：横屏下输入法不进入全屏提取编辑界面依赖 Flutter 引擎为文本输入设置 `IME_FLAG_NO_EXTRACT_UI`，在 CORE-01 写入 `app/.flutter-version`（ADR-V5-15）后核实；未生效则登记M0外部前提失败并提交ADR评估引擎修补；Activity不能补设TextInputPlugin生成的EditorInfo，不在本卡假设有补设路径。
- 产品取舍（2026-10-19 甲方确认）：高对比度跟随系统见 README §6 Q22、应用内预测性返回预览 Q25、主导航根页的系统返回 Q26、横屏主操作所在侧 Q27。

**验收标准**：测试方案全文见 [Test/and/S2_AND-13_TEST.md](../Test/and/S2_AND-13_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 330 行；`app/lib/platform/android/interaction/`（约 190 行）、`app/android/.../InteractionHandler.kt`（约 90 行）、`app/android/app/src/main/res/values*/styles.xml`（约 50 行；清单属性归 AND-02，不计入本卡），同属 `app/` 构建单元；不含测试 `app/integration_test/android/interaction_test.dart`（约 50 行）。

