### WIN-15 Windows 桌面交互与窗口适配

**目标**：让共享界面在 Windows 上按键鼠优先优化：经 CORE-55 接缝注入输入方式、动画开关、设备偏好存储与键位提示；学习流程每一步都可用键盘完成；最小窗口与断点、跨显示器 DPI 变化、标题栏深浅色、系统高对比度与二合一触摸密度在 Windows 上表现正确（README §6 Q11、Q19）。

**范围**
- 包含：CORE-55 接缝的 Windows 实现（`WindowsInputModalitySource`、`WindowsMotionScale`、`WindowsDevicePrefStore`、`WindowsShortcutLabels`）；全应用唯一的 `ShellKeyHandler` 实现 `WindowsKeyRouter`；组合键模型 `KeyChord`（自 WIN-08 移入）；学习流程键盘命令表 `StudyCommand`、默认键位 `defaultStudyBindings` 与持有者 `StudyKeymapHolder`；跟随 `AppearanceController.resolvedChanges` 的标题栏 `WindowsTitleBar`；最小窗口尺寸；原生 `interaction_channel.cpp`（顶层窗口消息委托）；安装点 `installWindowsInteraction` 及其在 `ports_windows.dart` 中的登记行；焦点、悬停、右键菜单、滚轮与触摸板滚动的 Windows 行为对照表及其真机验收。
- 不包含：宽度分档、矮高度、密度、组件、焦点环样式、悬停提示时长、动效与“减少动效”、高对比度令牌（CORE-55 §接口契约，本卡不重定义）；学习各状态的命令声明与动作（CORE-39 动作绑定与 CORE-58 `FmlCommandScope`）；窗口位置恢复、PerMonitorV2 与 DPI 重绘、单实例（WIN-06）；编辑器与全局快捷键、保留键规则（WIN-08）；快捷键设置界面与 `keymap.v1` 持久化（WIN-14）；`UiFeedbackSink`（Windows 不登记，桌面无触感，外观页“触感反馈”开关因此不显示）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-36、CORE-55、WIN-01、WIN-06、CORE-58、CORE-28、WIN-17

**接口契约**

实现与使用的接缝（逐字摘录，定义见 CORE-55 §接口契约、CORE-36 §接口契约、WIN-06）：

```dart
abstract interface class InputModalitySource {       // 平台登记（AND-13：touch；WIN-15：pointer，平板模式或触摸时 touch）；未登记时 initial = touch
  InputModality get initial; Stream<InputModality> get changes;
}
abstract interface class MotionScaleSource { double get scale; Stream<double> get changes; }   // 可选（AND-13 系统动画时长缩放），取值 0～10
abstract interface class DevicePrefStore {           // 设备级偏好：不进档案库、不同步、不进备份
  Future<String?> read(String key); Future<void> write(String key, String value);   // key 匹配 ^[a-z0-9_.]{1,64}$
}
abstract interface class ShortcutLabelSource { String? labelOf(String commandId); Listenable get changes; }   // 可选（WIN-15 登记，键位变化时通知）；未登记时 ShortcutHint 不显示
abstract interface class ShellKeyHandler {                           // 可选；AppShell 用 FocusManager.addEarlyKeyEventHandler 先交给它，返回 ignored 再走焦点链；AppShell 只取一个（同类型重复登记抛StateError），平台若有多组按键规则须自行合并为一个处理器（Windows 为 WIN-15 WindowsKeyRouter）
  KeyEventResult handle(KeyEvent event, AppNavigator nav); }
// 只读使用：AppearanceController.resolved / resolvedChanges（ResolvedAppearance.brightness、colors）；
//           FmlCommands.invoke / isAvailable（CORE-55）；WindowsPrefs.get / set（WIN-06）
```

本卡定义与实现（`app/lib/platform/windows/interaction/`）：

```dart
// keys.dart
final class KeyChord {                              // 自 WIN-08 移入，签名与语义不变；WIN-08、WIN-14 引用本定义
  const KeyChord(this.key, {this.ctrl = false, this.shift = false, this.alt = false});
  final LogicalKeyboardKey key; final bool ctrl, shift, alt;     // key 不为修饰键；不支持 Win 键组合
  static KeyChord? fromEvent(KeyEvent e);           // 修饰状态取 HardwareKeyboard.instance；纯修饰键返回 null
  String get label;                                 // 显示用，如 "Ctrl+Enter"
  String encode();                                  // 持久化：按ctrl、alt、shift顺序仅输出已置位修饰，各后接+；末尾0x加11位小写十六进制keyId（不足补0），如ctrl+0x0010000000d
  static KeyChord? decode(String s);                // 非规范键序、大小写、位宽、重复修饰或非法keyId返回null
  @override bool operator ==(Object other);          // key.keyId和ctrl/alt/shift逐字段相等
  @override int get hashCode;                        // 与值相等一致
}
// StudyCommand 从 CORE-58 app/lib/design/commands.dart 导入；不得复制枚举或字符串表。
const Map<StudyCommand, List<KeyChord>> defaultStudyBindings;    // 见下表 a“默认按键”列；每个命令 0–2 个组合键
final class StudyKeymapHolder extends ValueNotifier<Map<StudyCommand, List<KeyChord>>> {
  StudyKeymapHolder() : super(defaultStudyBindings);
  StudyCommand? lookup(KeyChord chord);
}
// router.dart
final class WindowsKeyRouter implements ShellKeyHandler {
  WindowsKeyRouter(this.study);
  final StudyKeymapHolder study;
  bool suspended = false;                           // 为 true 时一律返回 ignored（WIN-14 录制组合键期间使用）
  void attach(ShellKeyHandler inner);               // WIN-08 挂入 WindowsShellKeys；至多一个，重复attach抛StateError
}
final class WindowsShortcutLabels implements ShortcutLabelSource {
  WindowsShortcutLabels(this.study);                // labelOf：study.* → 该命令首个组合键的 label，无键位为 null；其他 ID → null
  final StudyKeymapHolder study;                    // changes 即 study（键位变化时通知）
}
// platform_sources.dart
final class WindowsInputModalitySource implements InputModalitySource {
  WindowsInputModalitySource(this._channel);
  Future<void> start();                             // 读一次 interactionMode 作 initial（读取前或失败为 pointer），再订阅事件流；与当前值不同才发出
}
final class WindowsMotionScale implements MotionScaleSource {
  WindowsMotionScale(this._channel);
  Future<void> start();                             // clientAreaAnimation 为 false → 0.0，否则 1.0；读取失败为 1.0
}
final class WindowsDevicePrefStore implements DevicePrefStore {
  const WindowsDevicePrefStore(this.prefs);         // read → prefs.get(key)；write → prefs.set(key, value)；键规则相同（^[a-z0-9_.]{1,64}$）
  final WindowsPrefs prefs;
}
final class WindowsTitleBar {
  WindowsTitleBar(this.appearance, this._channel);
  Future<void> attach();                            // 首帧回调中按 appearance.resolved 设一次，并订阅 resolvedChanges；与上次参数相同则不调用
}
abstract final class WindowsWindowLimits { static const Size minLogical = Size(600, 500); }   // README §6 Q24
// install.dart
void installWindowsInteraction(CompositionContext ctx);
// 登记 StudyKeymapHolder、WindowsKeyRouter（作为 ShellKeyHandler 与自身类型各登记一次）、WindowsShortcutLabels、
// InputModalitySource、MotionScaleSource、DevicePrefStore（WindowsDevicePrefStore，WindowsPrefs 用 ctx.features.require 取得）；
// 调用 minSize、创建 WindowsTitleBar 并 attach、两个 source 的 start（均不 await）；不登记 UiFeedbackSink
// ports_windows.dart：向 platformInstallers 追加 installWindowsInteraction，位于 installWindowsShell（WIN-06）之后、installWindowsEditing（WIN-08）之前（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
```

```text
MethodChannel "fml/windows/interaction"（app/windows/runner/interaction_channel.cpp；经 FlutterEngine::RegisterTopLevelWindowProcDelegate 挂接，
                                         flutter_window.cpp 的 OnCreate 只追加一行注册调用，不改 WIN-06 的消息处理）
  titleBar {dark: bool, caption: int?, text: int?} → null
        DwmSetWindowAttribute(DWMWA_USE_IMMERSIVE_DARK_MODE)：build ≥ 18985 用属性 20，17763～18984 用 19；
        build ≥ 22000 且 caption、text 非空时另设 DWMWA_CAPTION_COLOR（35）、DWMWA_TEXT_COLOR（36），值为 COLORREF；
        系统高对比度开启时不设颜色，两色恢复 DWMWA_COLOR_DEFAULT，由系统绘制
  minSize {width: double, height: double} → null
        逻辑像素；runner 保存，WM_GETMINMAXINFO 时乘 GetDpiForWindow/96 写入 ptMinTrackSize，且不超过窗口所在显示器的工作区；
        WM_WINDOWPOSCHANGING 中非最大化、非最小化且未带 SWP_NOSIZE 时把 cx/cy 放大到同一下限（覆盖启动时恢复的过小位置）
  interactionMode → "touch" | "pointer"
        先GetSystemMetrics(SM_MAXIMUMTOUCHES)>0，否则pointer；有触屏才检测以下touch条件：HKCU\Software\Microsoft\Windows\CurrentVersion\ImmersiveShell 的 TabletMode = 1（仅Windows 10读取；Windows 11不使用该注册值），
               或 GetSystemMetrics(SM_CONVERTIBLESLATEMODE) = 0（二合一键盘拆下或翻折为平板姿态）；否则 pointer
  clientAreaAnimation → bool（SystemParametersInfo(SPI_GETCLIENTAREAANIMATION)；“设置 → 辅助功能 → 视觉效果 → 动画效果”）
  windowMetrics → {dpi, work_area_px: {w, h}, min_track_px: {w, h}, high_contrast: bool, slate: bool}
        只供集成测试与诊断，界面布局不读（布局只按 MediaQuery，CORE-55）
EventChannel  "fml/windows/interaction/events"
  WM_SETTINGCHANGE（lParam 为 "UserInteractionMode" 或 "ConvertibleSlateMode"）→ {"interactionMode": "touch" | "pointer"}
  WM_SETTINGCHANGE（wParam 为 SPI_SETCLIENTAREAANIMATION）→ {"clientAreaAnimation": bool}
  窗口过程委托对上述消息只观察、返回 std::nullopt，不拦截
```

a. 学习流程键盘命令（S2～S4 由本卡按默认键处理；S5 起 WIN-14 把本表并入 `keymap.v1` 可自定义列表“学习”组）

| 命令 ID（CORE-58） | `StudyCommand` | 默认按键 | 作用 | 分发条件 |
| --- | --- | --- | --- | --- |
| `study.primary` | `primary` | Ctrl+Enter | 当前状态的唯一主操作：首页开始或续学、公式输入题提交、反馈页下一题、默写末题提交、暂停后继续、小结继续、过期页返回首页 | 任意焦点（含公式编辑器与文本框） |
| `study.option1`～`study.option4` | `option1`～`option4` | 1 / 2 / 3 / 4，另 A / B / C / D | 选择 A～D 并提交 | 不带修饰；焦点不在可编辑文本内 |
| `study.rateKnew` | `rateKnew` | Y | 自评“会” | 同上 |
| `study.rateForgot` | `rateForgot` | N | 自评“不会” | 同上 |
| `study.skip` | `skip` | Ctrl+Shift+S | 跳过本题 | 任意焦点 |
| `study.pause` | `pause` | Ctrl+Shift+P | 暂停（与顶栏“暂停”同一动作） | 任意焦点 |
| `study.appeal` | `appeal` | Ctrl+Shift+M | “记错了”申诉 | 任意焦点 |
| `study.prevQuestion` / `study.nextQuestion` | `prevQuestion` / `nextQuestion` | Ctrl+PageUp / Ctrl+PageDown | 默写上一题 / 下一题 | 任意焦点 |

键位核对（与 WIN-08 默认键位、保留键逐一比对，无重复）：WIN-08 的编辑器与全局命令都带 Ctrl 或 Alt，且不含 Enter、PageUp/PageDown 与 Ctrl+Shift+S/P/M；本表无修饰键只用数字 1～4 与字母 A～D、Y、N，不在 WIN-08 保留表中（保留的 Space、Enter、Esc、Tab、方向键、Delete 均不使用；Ctrl+Enter、Ctrl+PageUp/PageDown 带修饰，不等同于保留的 Enter 与补全弹层 PageUp/PageDown）；不使用 Alt+字母（无菜单栏的 Win32 窗口按 Alt+字母会响提示音）、Ctrl+Alt 与 Win 组合。新增或修改默认键时须重跑 WIN-14 验收中的键位冲突测试（WIN-14 同时依赖本卡与 WIN-08）。

b. 分发规则（`WindowsKeyRouter.handle`）

| 步骤 | 规则 |
| --- | --- |
| 1 | `suspended` 为 true，或事件既不是 `KeyDownEvent` 也不是 `KeyRepeatEvent` → ignored |
| 2 | 已 `attach` 的内层处理器（WIN-08 `WindowsShellKeys`）先处理，返回 handled 即结束 |
| 3 | 文本/IME焦点时库批量分支ignored；否则若库列表scope声明对应CORE-58 library.batch命令且可用，invoke后handled；repeat只允许move/extend，删除/撤销/打开等非方向命令的repeat直接ignored |
| 4 | 库分支未处理且为KeyRepeatEvent → ignored；否则查StudyKeymap，未命中ignored。学习无修饰命令遇EditableText或有效composing时ignored，不带入文本输入 |
| 5 | 学习命令FmlCommands.isAvailable(id)为true才invoke并handled，否则ignored；各分支消费后不再交给后续分支或页面 |

c. 窗口尺寸与断点（分档规则见 CORE-55 d，本表只列 Windows 典型窗口）

| 情形 | 逻辑尺寸（约） | CORE-55 分档 | 说明 |
| --- | --- | --- | --- |
| 最小窗口 | 600 × 500 | 中等，rail | 拖动缩放不能更小；更小工作区按CORE-55通用断点处理 |
| 默认窗口（WIN-06） | 1280 × 800 | 宽，常驻侧栏 | 双栏 |
| Windows 11 贴靠三分之一（1920×1080 @100%） | 640 × 1032 | 中等，rail | 单列 |
| 半屏贴靠（1920×1080 @100%） | 960 × 1032 | 宽 | 双栏（列表 360） |
| 小屏高缩放（1366×768 @200%） | 683 × 364（工作区） | 中等 + 矮高度 | 最小尺寸被工作区截断，学习页按矮高度左右排列 |
| 最大化（1920×1080 @150%） | 1280 × 693 | 宽 | 内容总宽 ≤ `contentMax` 居中 |
| 二合一平板姿态 | 按当前窗口 | 按上表 | 只改密度为 `touch`（控件 48），不改分档 |

d. 桌面交互对照（规范见 CORE-55 e、f、i；本表为 Windows 真机验收清单）

| 项 | Windows 行为 | 实现位置 |
| --- | --- | --- |
| 焦点顺序 | Tab / Shift+Tab 按阅读顺序：导航（rail 或侧栏）→ 顶栏 → 内容 → 操作栏；宽档双栏为列表 → 详情 | 共享界面默认 `ReadingOrderTraversalPolicy`；本卡验收 |
| 焦点可见 | 键盘操作时焦点环可见，鼠标点击后不显示；保持 Flutter 默认 `FocusHighlightStrategy.automatic`，平台层不改 | CORE-55 焦点环 |
| 激活 | 焦点在按钮或选项上按 Enter 或 Space 激活（Flutter 默认 `ActivateIntent`），与 a 表命令并存 | 共享组件 |
| 悬停与提示 | `pointer` 下显示悬停态，悬停 500 ms 出提示；`ShortcutHint` 与选项徽标经 `WindowsShortcutLabels` 显示 a 表键位 | CORE-55 + 本卡标签源 |
| 右键菜单 | 鼠标右键与触控笔侧键点按（书写区外）打开共享组件的上下文菜单（如“复制为”）；书写区内按住侧键为擦除（WIN-08 侧键规则）；键盘等价为 Shift+F10 或菜单键；文本框沿用 Flutter 默认复制粘贴菜单 | 共享组件；本卡验收 |
| 滚轮 | 一格滚动距离随系统“一次滚动的行数”；Shift+滚轮横向滚动（`FormulaStage` 过宽时）；鼠标拖动不滚动列表 | Flutter Windows 嵌入层与默认 `ScrollBehavior`；本卡验收 |
| 精确式触摸板 | 双指平滑滚动带惯性（`PointerPanZoom` 事件）；不做双指缩放 | 同上 |
| 触屏 | 触摸按下即切到 `touch` 密度（CORE-55 根部 `Listener`），平板姿态或平板模式由本卡事件切换；鼠标或触摸板移动后回到 `pointer` | CORE-55 + 本卡 |
| 触控笔与数位板 | 屏上笔与开启 Windows Ink 的外接数位板上报为 `stylus`，悬停或落笔即切到触控笔密度；未开启 Windows Ink 的数位板上报为鼠标，按 `pointer` 处理；驱动设置提示在设置区“笔与数位板”（WIN-08）；支持方式见 README §6 Q31 | CORE-55 + WIN-08 |
| 深浅色 | 外观模式“跟随系统”时随 Windows“应用模式”切换；标题栏随 `resolvedChanges` 改深浅色，Windows 11 标题栏底色取 `colors.surface`、文字取 `colors.onSurface` | CORE-55 + 本卡 |
| 高对比度 | 开启系统对比度主题时 `MediaQuery.highContrast` 为真，CORE-55 改用高对比度令牌；标题栏交还系统绘制 | Flutter 嵌入层 + CORE-55 |
| 文本大小 | “辅助功能 → 文本大小”经嵌入层映射为 `textScaler`，按 CORE-55 大字号降档 | Flutter 嵌入层 |
| DPI | 100%～200% 与跨显示器移动由 WIN-06 重绘；本卡只保证最小尺寸随 DPI 换算、分档按新逻辑尺寸重算且页面状态不丢 | WIN-06 + 本卡 |

- 错误码：无（通道失败时输入方式取 `pointer`、动画取 1.0、标题栏保持系统默认，记 AppLog warning，不向用户报错）。


LibraryBatchCommands（CORE-58）只在库列表scope生效、编辑文本焦点ignored：↑/↓/Home/End/PageUp/PageDown分别→library.batch.move.up/down/home/end/pageUp/pageDown，Shift组合对应library.batch.extend.up/down/home/end/pageUp/pageDown（每项均独立无参ID），Space→toggle，Ctrl+A→selectAll，Esc→clear，Enter→open，Delete→trash，Ctrl+T→editTags，Shift+F10/菜单键→menu，Ctrl+Z→undo；handled后不再执行页面默认动作，命令不可用返回ignored。Android同样由early handler安装点路由，不另加第二个ShellKeyHandler。


主题变化时在平台UI线程设置DWM属性后，调用SetWindowPos(topHwnd,null,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOZORDER|SWP_NOACTIVATE|SWP_FRAMECHANGED)请求边框重算，并RedrawWindow(...,RDW_FRAME|RDW_INVALIDATE)请求非客户区重绘；不激活/移动窗口。对属性不支持/设置失败记warning并使用系统默认标题栏，不将调用成功当视觉实测通过。Windows 10 1809/11、高对比度切换仍由WIN-13在M0/S7实测。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

产品约束追踪：见README §6 Q41；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 唯一按键入口：全应用只有 `WindowsKeyRouter` 登记为 `ShellKeyHandler`（CORE-36 只取一个）；WIN-08 不再直接登记，改为 `attach`。学习命令只经 `FmlCommands` 调用，本卡不 import `app/lib/ui/study/`，命令 ID 直接引用 CORE-58 `StudyCommand.id`（本卡单元测试与 a 表比对；本卡在 S2，不依赖 S4 的 CORE-39）。
- `defaultStudyBindings` 是学习键位默认值的唯一来源；WIN-14 设置区、`ShortcutHint` 文本与“恢复默认”都由它与 `StudyKeymapHolder` 渲染。
- 设备偏好：登记 `WindowsDevicePrefStore`，`appearance.v1`（含 `haptics` 字段，Windows 上无意义但原样保存）写入 WIN-06 的 `HKCU\Software\BubeiGongshi\Prefs`；不写 `%LOCALAPPDATA%` 下的 `device_prefs/`，卸载时随整键删除（WIN-02），不进同步与备份（README §6 Q19）。
- 标题栏：全应用只有 `WindowsTitleBar` 调用 `titleBar`；Windows 10 只切深浅色，Windows 11 另设底色与文字色；不自绘标题栏、不扩展客户区（保留系统贴靠布局与窗口按钮）。
- 最小窗口：600 × 500 逻辑像素（见 README §6 Q24），在启动首帧前设置；拖动缩放与跨 DPI 移动时由 runner 按当前 DPI 换算；工作区更小时以工作区为限，此时 CORE-55 的矮高度档生效。
- 输入方式：初值取 `interactionMode`，之后以本卡事件与 CORE-55 根部 `Listener` 的指针种类共同决定（平台源事件优先，CORE-55 e）；切换只改密度与提示，不改分档、不移动焦点。
- 不调用 `SystemChrome`、不判断 `Platform.isWindows` 于共享界面；所有 Windows 判断限于 `app/lib/platform/windows/` 与 `app/windows/`。
- 性能：通道调用不阻塞 UI 线程；标题栏只在参数变化时调用；相关预算为 CORE-01 预算表“点击到可见反馈（按压态出现）”“作答到判定反馈（提交到判定条出现，含判分）”“转场与动效”“旋转与窗口尺寸变化（到新布局首帧）”“主题切换（预设或外观模式，到新主题首帧）”Windows 列，由 WIN-13 测量。
- 外部前提：系统高对比度与“文本大小”经 Flutter Windows 嵌入层上报为 `MediaQuery.highContrast` 与 `textScaler`、精确式触摸板上报为 `PointerPanZoom`、滚轮距离随系统滚动行数，均在 CORE-01 写入 `app/.flutter-version`（ADR-V5-15）后核实；不满足的项记入附录 D，需要时按 README §8.4 先修订 CORE-55 增加接缝。
- 产品取舍（2026-10-19 甲方确认）：高对比度跟随系统见 README §6 Q22、最小窗口 600×500 Q24、学习流程默认按键 Q28、Windows 11 标题栏着色 Q30。

**验收标准**
- [R42.d] Widget 测试（假通道）：`interactionMode` 返回 touch 时 `InputModalityScope.of` 为 `touch`、控件高 48；事件发出 pointer 后为 `pointer`、控件高 36，布局档与焦点不变；通道失败时为 `pointer`。
- [R42.c] 单元测试（假通道）：`clientAreaAnimation` 为 false 时 `WindowsMotionScale.scale` 为 0 并发出一次，事件改为 true 后为 1.0；通道失败为 1.0。
- [R42.f] Widget 测试：执行 `installWindowsInteraction` 后 `AppearanceController.load` 经 `WindowsDevicePrefStore` 读写，Fake `WindowsPrefs` 收到键 `appearance.v1` 与 `{"v":1,…,"haptics":true}`；`features.get<UiFeedbackSink>()` 为 null，外观页不显示“触感反馈”开关。
- [R42.f] Widget 测试（假通道）：`resolvedChanges` 发出 dark 时通道收到 `titleBar {dark: true, caption: <surface>, text: <onSurface>}`，相同参数连续发出只调用一次；扫描测试：`app/lib/` 中 `"titleBar"` 只出现在 `windows_title_bar.dart`。
- [R42.b] 单元测试：`StudyCommand` 的全部 `id` 与 a 表命令 ID 逐字相等且无重复；`defaultStudyBindings` 内部无重复组合键，带修饰的组合键均含 Ctrl，不带修饰的只属于 `unmodifiedAllowed` 命令；`KeyChord.encode` 与 `decode` 往返一致。
- [R42.b] Widget 测试（Fake 学习页挂 `FmlCommandScope`）：按 2 调用 `study.option2` 回调；焦点在 `TextField` 中按 2 不调用且文本框收到“2”；公式编辑器获得焦点时按 Ctrl+Enter 调用 `study.primary`；命令值为 null 时按键返回 ignored 并交给页面；`suspended = true` 时任何键返回 ignored；按住 Ctrl+Enter 重复只调用一次；挂入的内层处理器返回 handled 时不再查学习命令。
- [R42.b] Widget 测试：登记 `WindowsShortcutLabels` 后指针密度下 `ShortcutHint('study.primary')` 显示“Ctrl+Enter”；把 `StudyKeymapHolder.value` 中 `pause` 改为 Ctrl+Shift+Q 后 `changes` 通知、`labelOf('study.pause')` 为“Ctrl+Shift+Q”，按 Ctrl+Shift+Q 触发暂停、Ctrl+Shift+P 不再触发。
- [R42.e] 集成测试（`app/integration_test/windows/interaction_test.dart`，真机）：以 `SetWindowPos` 设为 400 × 300 逻辑像素后 `windowMetrics.min_track_px` 等于 600 × 500 × DPI/96（工作区更小时等于工作区），窗口实际不小于该值；在学习页输入未提交文本后于 1280 × 800、600 × 500、最大化之间切换各 2 次，路由、文本、光标与滚动偏移不变。
- [R42.e] 手动（100% + 200% 双显示器）：在 100%、125%、150%、175%、200% 下最小窗口均可用且无截断；把窗口从 100% 显示器拖到 200% 显示器后最小尺寸按新 DPI 生效、分档按新逻辑尺寸重算、正在输入的公式与焦点不丢。
- [R42.b] 手动（键盘，不用鼠标）：从学习首页按 Ctrl+Enter 开始，选择题按 1～4 或 A～D、自评按 Y / N、公式输入题按 Ctrl+Enter 提交、反馈页 Ctrl+Enter 下一题、Ctrl+Shift+M 记错了、Ctrl+Shift+S 跳过、Ctrl+Shift+P 暂停后 Ctrl+Enter 继续、默写用 Ctrl+PageUp/PageDown 换题并提交，完成一组到小结；全程焦点环可见，Tab 顺序与 d 表一致；开启微软拼音输入法时以上按键行为不变。
- [R42.d] 手动（鼠标与精确式触摸板）：按 d 表逐行核对悬停提示、右键菜单（含 Shift+F10）、滚轮行数与 Shift+滚轮横滚、触摸板双指惯性滚动。
- [R42.d] 手动（外接数位板，驱动开启 Windows Ink）：笔悬停或落笔后切到触控笔密度，移动鼠标后回到指针密度，布局档与焦点不变；书写区外点按笔侧键打开与鼠标右键相同的上下文菜单（M0 不满足时按 WIN-08 外部前提处理）。
- [R42.d] 手动（Windows 11 二合一触屏 + 触控笔）：拆下键盘或翻折为平板姿态后控件变为触摸密度、快捷键提示隐藏；接回键盘并移动触摸板后恢复指针密度；全过程不改布局档、不丢输入。
- [R42.f] 手动：Windows 10 1809 与 Windows 11 上切换系统深浅色（外观模式“跟随系统”）及应用内深浅色，标题栏随之切换；开启对比度主题（如“夜空”“沙漠”）后应用改用高对比度令牌、标题栏为系统颜色，关闭后恢复。
- [R42.c] WIN-13 在基线机型与二合一机型上测量 CORE-01 预算表 a 段所列五行，P95 在 Windows 列预算内。

- [R11][R42.d] Fake库scope按↓/Shift+↓分别只invoke move.down/extend.down一次；文本焦点不调用，方向repeat可调用，Delete repeat不调用；WIN-08内层handled时库/学习均不调用，未声明命令继续焦点链。

- [R42.d] 主机切换深浅色及高对比度，截取标题栏确认更新；切换前后位置/尺寸/前台窗口不变，DWM失败夹具回退系统默认且不崩溃。

**规模**：约 440 行；`app/lib/platform/windows/interaction/`（约 260 行）、`app/windows/runner/interaction_channel.cpp` 与 `app/windows/runner/flutter_window.cpp` 的一行注册（约 120 行）、`app/integration_test/windows/interaction_test.dart`（约 60 行），同属 `app/` 构建单元。

