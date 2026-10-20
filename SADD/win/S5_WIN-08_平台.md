### WIN-08 编辑器快捷键、输入法与笔输入

**目标**：通过 CORE-36、CORE-59、CORE-64 预留的接缝，为 Windows 提供编辑器快捷键、全局快捷键与触控笔、外接数位板、触屏的手写输入策略；默认键位尽量贴近 Word 与常见 LaTeX 编辑器，键位表可由 WIN-14 自定义（README §6 Q11）。

**范围**
- 包含：快捷键模型 `ShortcutCommand`、`Keymap`（组合键 `KeyChord` 定义见 WIN-15），默认键位表 `defaultKeymap`，保留键判定 `isReservedChord`，当前键位持有者 `KeymapHolder`；`WindowsEditorBindings`（实现 CORE-59 `EditorPlatformBindings`）；`WindowsShellKeys`（实现 CORE-36 `ShellKeyHandler`，挂入 WIN-15 `WindowsKeyRouter`，不直接登记）；`WindowsInkPolicy`（实现 CORE-64 `InkInputPolicy`）；笔设备检测 `WindowsPenStatus` 与设置区“笔与数位板”（order 65）；runner 侧通道 `fml/windows/pen`（笔设备枚举、关闭系统长按右键与笔势）；安装点 `installWindowsEditing`。
- 不包含：编辑器逻辑、撤销与模板（CORE-59）；画布与笔画模型（CORE-64）；快捷键设置界面、录制、冲突处理与持久化（WIN-14）；学习流程键盘命令与全应用按键入口（WIN-15）；LaTeX 命令补全（CORE-53）与公式库批量操作（CORE-54）的按键，二者在共享界面实现，键位固定，本卡只把 Ctrl+T、Shift+F10 列为保留键，避免被自定义占用（README §6 Q16）；数位板快捷键按钮、触控环、压感曲线与板面映射区域（由厂商驱动设置）；WinTab 接口（见 README §6 Q31）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-36、CORE-37、CORE-40、WIN-15、CORE-59、CORE-64、CORE-28、WIN-17

**接口契约**

实现的接缝（逐字摘录，定义见 CORE-36、CORE-59、CORE-64）：

```dart
abstract interface class EditorPlatformBindings {   // 平台卡经 PlatformPorts.platformInstallers 登记；未登记时用 DefaultEditorBindings
  KeyEventResult handleKey(FormulaEditorController c, KeyEvent e);        // 结构化模式下公式区持有焦点时调用
  Widget? accessoryBar(BuildContext context, FormulaEditorController c);  // 显示在公式区与符号面板之间；null 表示无
}
abstract interface class ShellKeyHandler {                           // 可选；AppShell 用 FocusManager.addEarlyKeyEventHandler 先交给它，返回 ignored 再走焦点链；AppShell 只取一个（同类型重复登记抛StateError），平台若有多组按键规则须自行合并为一个处理器（Windows 为 WIN-15 WindowsKeyRouter）
  KeyEventResult handle(KeyEvent event, AppNavigator nav); }
abstract interface class InkInputPolicy {          // 平台卡经 PlatformPorts.platformInstallers 登记（AND-07、WIN-08）
  bool accept(PointerDownEvent e, {required bool stylusSeen});   // false = 整笔丢弃（防手掌误触）；stylusSeen = 本画布清空后出现过触控笔
  double? pressureOf(PointerEvent e);                            // 0..1；null = 不记录压力
  bool isEraser(PointerEvent e);                                 // true = 该笔为擦除（触及的笔画整笔删除）
}
```

本卡定义与实现（`app/lib/platform/windows/editing/`）：

```dart
enum ShortcutScope { editor, global }
enum ShortcutCommand {                              // 顺序即设置页显示顺序；name 用作持久化键（WIN-14），不得改名
  superscript, subscript, fraction, sqrt, parentheses, toggleMode,          // editor
  newFormula, findInLibrary, goStudy, goLibrary, goRecognize, goSettings;          // global（导航顺序同 CORE-36；计算页无全局命令）
  ShortcutScope get scope;
  String get titleKey;                              // 本地化键 shortcut.<name>
}
// KeyChord：定义见 WIN-15（app/lib/platform/windows/interaction/keys.dart），本卡 import 使用，不重复定义
final class Keymap {                                // 不可变；每个命令 0–2 个组合键
  const Keymap(this.bindings);
  final Map<ShortcutCommand, List<KeyChord>> bindings;
  ShortcutCommand? lookup(KeyChord chord, ShortcutScope scope);
}
const Keymap defaultKeymap;                         // 见下表“默认按键”列
bool isReservedChord(KeyChord c);                   // 下表“保留”各行；为 true 的组合键不能分配给命令
final class KeymapHolder extends ValueNotifier<Keymap> {
  KeymapHolder() : super(defaultKeymap);
  bool suspended = false;                           // 为 true 时两个按键处理器一律返回 ignored（WIN-14 录制组合键期间使用）
}
final class WindowsEditorBindings implements EditorPlatformBindings { const WindowsEditorBindings(this.holder); final KeymapHolder holder; }   // accessoryBar 恒返回 null
final class WindowsShellKeys implements ShellKeyHandler { const WindowsShellKeys(this.holder); final KeymapHolder holder; }
final class WindowsInkPolicy implements InkInputPolicy { const WindowsInkPolicy(); }
final class PenDevice { const PenDevice(this.name, {required this.integrated}); final String name; final bool integrated; }  // integrated = 屏上笔；false = 外接数位板或数位屏
final class PenStatus {
  const PenStatus({this.devices = const [], this.wintabDriver = false});
  final List<PenDevice> devices; final bool wintabDriver;
  bool get needsInkHint => wintabDriver && devices.every((d) => d.integrated);   // 装有数位板驱动但系统未登记外接笔 → 提示开启 Windows Ink
}
final class WindowsPenStatus {                      // 通道 fml/windows/pen 的 Dart 侧
  Future<PenStatus> read();                         // 通道失败返回 const PenStatus()，记 AppLog warning，不向用户报错
  Stream<void> get changes;                         // devicesChanged 事件
}
void installWindowsEditing(CompositionContext ctx);
// 登记 KeymapHolder、WindowsEditorBindings、WindowsInkPolicy、WindowsPenStatus；向 SettingsSections 加入 order 65 的“笔与数位板”区；WindowsShellKeys 经 ctx.features.require<WindowsKeyRouter>().attach 挂入，
// 不作为 ShellKeyHandler 登记；追加到 ports_windows.dart 的 platformInstallers（在 installWindowsInteraction 之后）（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
```

默认键位（只处理 `KeyDownEvent` 与 `KeyRepeatEvent`；未命中的按键交给 `const DefaultEditorBindings()`，其行为见 CORE-59）：

| 范围 | 命令 | 默认按键 | 动作 | 依据 |
| --- | --- | --- | --- | --- |
| 编辑器 | 上标 `superscript` | Ctrl+Shift+=（Ctrl+加号） | `insertTemplate(TemplateId.superscript)` | Word 上标 |
| 编辑器 | 下标 `subscript` | Ctrl+= | `insertTemplate(TemplateId.subscript)` | Word 下标 |
| 编辑器 | 分式 `fraction` | Ctrl+/ | `insertTemplate(TemplateId.fraction)` | Word 公式线性格式以“/”生成分式 |
| 编辑器 | 根号 `sqrt` | Ctrl+R | `insertTemplate(TemplateId.sqrt)` | 本应用约定（Word 与常见 LaTeX 编辑器无默认键） |
| 编辑器 | 圆括号 `parentheses` | Ctrl+9 | `insertTemplate(TemplateId.parentheses)` | 本应用约定（数字键 9 上为“(”） |
| 编辑器 | 结构化 / LaTeX 切换 `toggleMode` | Ctrl+E | `setMode` 互换；返回 false 时不切换（CORE-59 规则） | 本应用约定 |
| 全局 | 新建公式 `newFormula` | Alt+= | `nav.go('/library/new')` | Word 插入公式 |
| 全局 | 在公式库中查找 `findInLibrary` | Ctrl+F | `nav.go('/library?search=1')`（CORE-38 聚焦搜索框） | Word 与 LaTeX 编辑器的查找 |
| 全局 | 学习 `goStudy` / 公式库 `goLibrary` / 识别 `goRecognize` / 设置 `goSettings` | Ctrl+1 / Ctrl+2 / Ctrl+3 / Ctrl+4 | `nav.go` 到 `/study`、`/library`、`/recognize`、`/settings`（与 CORE-36 导航顺序一致）；计算页从公式详情进入，无全局快捷键，Ctrl+5 默认不分配（可在 WIN-14 自定义给其他命令） | 本应用约定 |
| 保留（固定） | 撤销 / 重做 | Ctrl+Z / Ctrl+Y、Ctrl+Shift+Z | `undo` / `redo`（Ctrl+Z、Ctrl+Y 由 `DefaultEditorBindings` 处理，Ctrl+Shift+Z 由本卡转为 `redo`） | Word；Overleaf 等 LaTeX 编辑器 |
| 保留（固定） | 编辑与导航 | Ctrl+C/X/V/A、方向键、Home/End、Tab/Shift+Tab、Backspace/Delete、Enter、Esc | CORE-59 与文本框 | 系统与 Word 通用 |
| 保留（固定） | LaTeX 补全与公式库批量操作 | 补全弹层的 ↑/↓、PageUp/PageDown、Tab、Enter、Esc；公式库列表的 Space、Shift+方向键、Ctrl+A、Delete、Ctrl+T、Shift+F10 | CORE-53、CORE-54（共享界面处理，本卡不拦截） | 补全按键同 TeXstudio、Overleaf；列表按键同 Windows 资源管理器；Ctrl+T 为本应用约定 |
| 保留（不可分配） | 系统与输入法 | Alt+F4、Alt+Tab、含 Win 键的组合、Ctrl+Space、Shift+Space、Ctrl+.、Ctrl+Alt+任意键 | 不处理，交给系统 | 系统窗口操作；微软拼音等输入法的中英文、全半角与标点切换；Ctrl+Alt 与 AltGr 等价 |

```text
WindowsInkPolicy：
  accept：kind 为 stylus 或 invertedStylus → true；kind 为 touch 且 stylusSeen → false；其余 → true（鼠标可书写；未开启 Windows Ink 的数位板按鼠标上报，同样可书写）
  pressureOf：stylus 与 invertedStylus 且 pressureMax > pressureMin 时归一化到 0..1；否则 null（CORE-40 按 0.5 处理）
  isEraser：kind == invertedStylus（笔尾），或按下时 buttons 含 kPrimaryStylusButton 或 kSecondaryStylusButton（按住笔侧键落笔）

笔侧键规则（屏上笔与外接数位板一致）：
  书写区（InkCanvas）内：按住侧键落笔 = 擦除，触及的笔画整笔删除（上面的 isEraser）
  书写区外：点按侧键 = 右键，打开与鼠标右键相同的上下文菜单（WIN-15 d 表“右键菜单”）
  笔长按：不模拟右键（系统长按右键已由本卡关闭），按 Flutter 长按手势处理，与触摸长按一致

外接数位板（README §6 Q31）：
  开启 Windows Ink（驱动选项，如“使用 Windows Ink”）：与屏上笔相同——压感、笔尾与侧键擦除、悬停、防手掌误触
    多显示器映射、板面区域、压感曲线与快捷键按钮由驱动决定；应用按窗口逻辑坐标接收笔事件，不做换算
  未开启 Windows Ink（只有 WinTab）：按鼠标处理——可书写，pressure 为 null，无笔尾擦除与防误触；设置区给出开启提示

通道 fml/windows/pen（app/windows/runner/pen_channel.cpp）：
  status → {devices: [{name, integrated}], wintab_driver}
    devices：GetPointerDevices 中 type 为 POINTER_DEVICE_TYPE_INTEGRATED_PEN（integrated = true）或 POINTER_DEVICE_TYPE_EXTERNAL_PEN（false）的项，name 取 productString
    wintab_driver：%SystemRoot%\System32\Wintab32.dll 存在（数位板驱动通常会安装；只判断文件存在，不加载）
  事件 devicesChanged：收到 WM_POINTERDEVICECHANGE（插拔数位板、驱动切换 Windows Ink 后）时发出，500 ms 内合并为一次
  窗口初始化：先 RegisterPointerDeviceNotifications(topHwnd, FALSE)，失败记录 PLATFORM_IO、设备枚举仍可手动刷新；对 viewHwnd（Flutter 子视图）及 topHwnd SetProp(L"MicrosoftTabletPenServiceProperty", TABLET_DISABLE_PRESSANDHOLD | TABLET_DISABLE_FLICKS)，
    并在 WM_TABLET_QUERYSYSTEMGESTURESTATUS 返回同值——笔或手指长按不再弹出系统右键圆环，笔势不触发翻页

设置区“笔与数位板”（order 65）：
  列出检测到的设备：“屏上触控笔”或“数位板：<name>”；都没有时显示“未检测到触控笔或数位板，可用鼠标或触屏书写”
  needsInkHint 为 true 时显示提示：“检测到数位板驱动，但系统没有登记 Windows Ink 笔。请在数位板驱动设置中开启“使用 Windows Ink”
    （Wacom：数位板属性 → 映射；其他品牌在驱动的“Windows Ink”或“笔模式”选项中），再重新插拔数位板或重启本应用。
    未开启时数位板按鼠标使用，没有压感与橡皮擦。”
  订阅 changes 刷新；本区只读，不提供压感曲线、映射与按钮设置
```

- 错误码：无（只实现按键与输入策略接缝）。

笔消息子类化使用 WIN-01 runner 协议；在 viewHwnd 处理 WM_TABLET_QUERYSYSTEMGESTURESTATUS，销毁时 RemoveProp/RemoveWindowSubclass。Windows 10 1809、数位板驱动组合为外部前提（M0 实测并记录 D），不可从 API 存在推定设备行为。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

产品约束追踪：见README §6 Q21；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 分发：两个处理器都先以 `KeyChord.fromEvent` 取组合键，再查 `holder.value`（键位修改即时生效，不需重启）。`WindowsShellKeys` 只查 `global` 范围，由 WIN-15 `WindowsKeyRouter` 先行调用（学习命令在其后查找，见 WIN-15 b）；`WindowsEditorBindings` 只查 `editor` 范围，未命中再交给 `DefaultEditorBindings`。`WindowsKeyRouter`（WIN-15，全应用唯一的 `ShellKeyHandler`）先于页面收到按键（CORE-36），WIN-14 保证同一组合键不会同时分配给两个命令（含 WIN-15 学习命令）。
- `defaultKeymap` 是默认键位的唯一来源；WIN-14 的设置区、帮助列表与“恢复默认”都由它与 `KeymapHolder` 渲染，不另行维护表格。
- 键位比较用逻辑键（`LogicalKeyboardKey`），使“=”“/”“9”等按键在中文与英文键盘布局下一致；小键盘的“/”“=”不等同于主键盘按键。
- 不处理无 Ctrl 或 Alt 修饰的字符键（学习页不带修饰的选项与自评键由 WIN-15 处理）；输入法组合期间的按键由 `FormulaEditor` 的文本输入连接先行消费（CORE-59），本卡不另做 IME 处理；不注册系统级热键（`RegisterHotKey`）。
- 手写延迟预算见 CORE-01 预算表“手写墨迹上屏”（Windows ≤ 40 ms），由 WIN-13 测量。
- 外部前提：笔输入依赖 Flutter Windows 嵌入层把笔事件上报为 `PointerDeviceKind.stylus`（含压力、笔尾橡皮擦为 `invertedStylus`、侧键为 `kPrimaryStylusButton`、悬停为 `PointerHoverEvent`）；屏上笔与开启 Windows Ink 的外接数位板走同一路径。M0 在锁定的 Flutter 版本上用二合一设备与外接数位板各验证一次，若不满足则笔按鼠标处理、压力为 null，并记入附录 D。书写区外侧键点按是否上报为次键点击同在 M0 核实；不满足时笔用户经“更多”按钮（CORE-55 f 的可见按钮等价）打开同一菜单，并记入附录 D。
- 不加载 Wintab32.dll、不调用 WinTab API；笔设备检测只用 `GetPointerDevices` 与文件是否存在。关闭系统长按右键与笔势只作用于本应用主窗口。
- 产品取舍（2026-10-19 甲方确认）：外接数位板只支持 Windows Ink、不接入 WinTab，见 README §6 Q31。
- 产品取舍（2026-10-19 甲方确认）：计算页不设全局快捷键（Ctrl+5 默认不分配）见 README §6 Q29。

**验收标准**：测试方案全文见 [Test/win/S5_WIN-08_TEST.md](../Test/win/S5_WIN-08_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 460 行；`app/lib/platform/windows/editing/`（约 380 行，含笔设备检测与设置区）、`app/windows/runner/pen_channel.cpp` 与 `app/windows/runner/flutter_window.cpp` 的一行注册（约 80 行），同属 `app/` 构建单元。

