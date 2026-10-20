### AND-07 手写与编辑器的 Android 适配

**目标**：通过 CORE-37、CORE-40 预留的接缝，为 Android 提供手写输入策略（触控笔优先、防手掌误触、压力、橡皮擦）与软键盘上方的模板快捷栏。

**范围**
- 包含：`AndroidInkPolicy`（实现 CORE-64 `InkInputPolicy`）；`AndroidEditorBindings`（实现 CORE-59 `EditorPlatformBindings`，含软键盘快捷栏）；安装点 `installAndroidEditing` 及其在 `ports_android.dart` 中的登记行。
- 不包含：画布、笔画模型与撤销（CORE-40）；编辑器逻辑、模板与符号面板（CORE-37）；笔迹渲染为识别图（CORE-29 `render_ink`）；原生 `MotionEvent` 采集（不做，笔迹点来自 Flutter 指针事件）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-37、CORE-40、CORE-59、CORE-64、AND-15

**接口契约**

实现的接缝（逐字摘录，定义见 CORE-37、CORE-40）：

```dart
abstract interface class EditorPlatformBindings {   // 平台卡经 PlatformPorts.platformInstallers 登记；未登记时用 DefaultEditorBindings
  KeyEventResult handleKey(FormulaEditorController c, KeyEvent e);        // 结构化模式下公式区持有焦点时调用
  Widget? accessoryBar(BuildContext context, FormulaEditorController c);  // 显示在公式区与符号面板之间；null 表示无
}
abstract interface class InkInputPolicy {          // 平台卡经 PlatformPorts.platformInstallers 登记（AND-07、WIN-08）
  bool accept(PointerDownEvent e, {required bool stylusSeen});   // false = 整笔丢弃（防手掌误触）；stylusSeen = 本画布清空后出现过触控笔
  double? pressureOf(PointerEvent e);                            // 0..1；null = 不记录压力
  bool isEraser(PointerEvent e);                                 // true = 该笔为擦除（触及的笔画整笔删除）
}
```

本卡实现：

```dart
// app/lib/platform/android/editing/android_ink_policy.dart
final class AndroidInkPolicy implements InkInputPolicy {
  const AndroidInkPolicy({this.palmRadiusPx = 24});
  final double palmRadiusPx;      // 逻辑像素；e.radiusMajor 超过即视为手掌
  // accept：kind 为 stylus 或 invertedStylus → true；
  //         kind 为 touch：stylusSeen → false（本画布出现过触控笔后忽略手指）；radiusMajor > palmRadiusPx → false；否则 true；
  //         其余 kind（mouse、trackpad）→ true
  // pressureOf：stylus 与 invertedStylus 且 pressureMax > pressureMin 时取 (pressure − pressureMin) / (pressureMax − pressureMin) 并截到 0..1；否则 null
  // isEraser：kind == invertedStylus，或 buttons 含 kSecondaryStylusButton
}

// app/lib/platform/android/editing/android_editor_bindings.dart
final class AndroidEditorBindings implements EditorPlatformBindings {
  const AndroidEditorBindings();
  // handleKey：委托 const DefaultEditorBindings()（外接键盘与平板键盘）
  // accessoryBar：MediaQuery.viewInsetsOf(context).bottom > 0（软键盘显示）时返回 TemplateBar，否则 null
}
// TemplateBar：高 48 dp（CORE-55 触摸密度最小触控目标）、横向可滚动的一行按钮，顺序固定：
//   分式 fraction、上标 superscript、下标 subscript、根号 sqrt、括号 parentheses、积分 integral、求和 sum、
//   极限 limit、下一空位（CursorMove.nextHole）、收起键盘
//   模板按钮调用 controller.insertTemplate(TemplateId.<名>)；按钮文字与无障碍标签来自 app/lib/platform/android/editing/strings.dart

// app/lib/platform/android/editing/install.dart
void installAndroidEditing(CompositionContext ctx) {
  ctx.features.register<EditorPlatformBindings>(const AndroidEditorBindings());
  ctx.features.register<InkInputPolicy>(const AndroidInkPolicy());
}
// ports_android.dart：向 platformInstallers 列表追加 installAndroidEditing（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
```

- 错误码：无（只实现策略与界面接缝）。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

**实现约束**
- 只读 Flutter `PointerEvent` 字段（`kind`、`pressure`、`pressureMin/Max`、`radiusMajor`、`buttons`），不新增 MethodChannel，不写 Kotlin。
- 手掌判定阈值 `palmRadiusPx` 为常量默认值，AND-12 真机矩阵标定后可调整；V1 不提供“仅触控笔”开关（出现触控笔后自动忽略手指，清空画布后恢复）。
- 快捷栏不遮挡输入：其高度计入 `FormulaEditor` 布局，不使用 Overlay；横竖屏切换后随 `viewInsets` 重新判断；横屏（矮高度）时仍为单行并紧贴键盘上方（内边距与软键盘避让见 AND-13 表 d）。
- 触控笔悬停与书写时由 CORE-55 `InputModalityScope` 按 `PointerDeviceKind.stylus` 切换输入方式，本卡不另行登记（AND-13 只登记 `touch`）；画布不设系统手势排除区，从屏幕左右边缘手势区起笔交给系统返回，已写笔画由 CORE-40 保留。
- 墨迹上屏延迟预算见 CORE-01 预算表“手写墨迹上屏”（Android ≤ 50 ms），由 AND-12 测量。

**验收标准**：测试方案全文见 [Test/and/S5_AND-07_TEST.md](../Test/and/S5_AND-07_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 220 行；`app/lib/platform/android/editing/`。

