### CORE-87 公式输入组件与平台编辑接缝

**目标**：消费CORE-59控制器，交付完整公式编辑器、符号/声明面板、复制按钮与平台输入接缝。

**范围**
- 包含：FormulaEditor、Palette、DeclarationPanel、UnitOptions、FormulaCopyButton/FormulaCopier低层接口、EditorPlatformBindings/DefaultEditorBindings、LatexSourceAssist与安装。
- 不包含：源码编辑状态算法（CORE-59）；后台worker与字形缓存（CORE-37）；完整复制实现（CORE-91，下游说明）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-08、CORE-12、CORE-37、CORE-55、CORE-58、CORE-59

**接口契约**

```dart
// app/lib/ui/editor/palette.dart 与 declaration_panel.dart
class SymbolPalette extends StatelessWidget {
  const SymbolPalette({super.key, required this.onInsert});   // 数据为本卡资产 app/assets/editor/palette.json：[{group, items: [{latex, label, iso}]}]
  final void Function(String latex) onInsert;
}
class DeclarationPanel extends StatelessWidget {
  const DeclarationPanel({super.key, required this.controller, required this.units});  // UnitOptions用例只暴露compatible
  final FormulaEditorController controller; final UnitOptions units;
}

// app/lib/ui/editor/formula_editor.dart：页面统一使用的完整编辑器
class FormulaEditor extends StatefulWidget {
  const FormulaEditor({super.key, required this.controller, required this.features,
                       this.showPalette = true, this.autofocus = false});
  final FormulaEditorController controller; final FeatureRegistry features;   // features 只用于取 EditorPlatformBindings 与 LatexSourceAssist
  final bool showPalette, autofocus;
}
enum FormulaCopyFormat { auto, latex, unicode, mathml, image }
abstract interface class FormulaCopier {           // CORE-91 实现并登记；未登记时 FormulaCopyButton 只复制 LaTeX 文本
  Future<Set<FormulaCopyFormat>> formatsFor(String latex, {String notationProfileId = 'cn-default', List<SymbolDeclDto> userDecls = const []});   // 供“复制为”菜单置灰
  Future<bool> copy(String latex, {FormulaCopyFormat format = FormulaCopyFormat.auto, String notationProfileId = 'cn-default', List<SymbolDeclDto> userDecls = const []});   // true = 系统已显示复制反馈
}
class FormulaCopyButton extends StatelessWidget {  // 各页面的统一复制入口（CORE-38、CORE-50）
  const FormulaCopyButton({super.key, required this.latex, required this.features, required this.clipboard,
                           this.notationProfileId = 'cn-default', this.userDecls = const [], this.compact = false});
  final String latex; final FeatureRegistry features; final ClipboardAdapter clipboard; final String notationProfileId;
  final List<SymbolDeclDto> userDecls;               // 当前修订/编辑会话的声明快照，透传formatsFor与copy
  final bool compact;                              // true = 只显示图标
}
abstract interface class EditorPlatformBindings {   // 平台卡经 PlatformPorts.platformInstallers 登记；未登记时用 DefaultEditorBindings
  KeyEventResult handleKey(FormulaEditorController c, KeyEvent e);        // 结构化模式下公式区持有焦点时调用
  Widget? accessoryBar(BuildContext context, FormulaEditorController c);  // 显示在公式区与符号面板之间；null 表示无
}
final class DefaultEditorBindings implements EditorPlatformBindings {
  const DefaultEditorBindings();
  // handleKey：←/→/↑/↓（Shift 扩选）、Home/End、Tab/Shift+Tab → nextHole/prevHole、Backspace/Delete、
  //            Ctrl+Z/Ctrl+Y → undo/redo；其余返回 ignored；accessoryBar 返回 null
}

abstract interface class LatexSourceAssist {        // CORE-53 登记；未登记时 LaTeX 源码框不加修饰
  Widget wrapSourceField(BuildContext context, LatexSourceSession session, Widget field);
}
final class LatexSourceSession {                    // FormulaEditor 在 LaTeX 模式下为源码框创建
  final TextEditingController text; final FocusNode focus; final GlobalKey fieldKey;   // fieldKey 用于取光标矩形
  final void Function(TextEditingValue value) commitEdit;   // 作为一次独立撤销步写入源码
}
```

- 本卡处理的错误码与界面行为：

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `PARSE_SYNTAX` 等 `PARSE_*` | CORE-06 | 按 `inputRange` 画波浪下划线，点击显示诊断气泡与修复建议；排版置 stale |
| `TYPE_*`、`UNIT_*`、`NOTATION_*` | CORE-09/08/07 | 按 NodePath 区域画下划线；Error 阻止保存，Warning 保存时须确认 |

```dart
// app/lib/editor/unit_options.dart：应用层实现经CoreBinding调用units.compatible
abstract interface class UnitOptions {
  Future<List<UnitDto>> compatible(DimensionFullDto dimension);   // units.compatible 入参按 CORE-08 DimensionFull 结构
}
```
DeclarationPanel 只消费 UnitOptions，不能直接 import binding。


`installEditorInput(CompositionContext ctx)` 登记输入默认值和平台绑定；后台 worker 仍由 CORE-37 installEditor 构造。
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 编辑器工具栏、模板栏、补全入口与“复制为”菜单的控件尺寸取 `FmlDensity`（`pointer` 32、`touch` 48）；公式渲染颜色取 `FmlColors.onSurface`，深浅色切换后重绘不重新排版。`defaultEditorMode` 仅在composition构造默认值时读取RuntimeSnapshot.os（README §6 Q13），共享Widget只消费已注入EditorMode。
- 绘制复用CORE-37的FormulaView与render绘制器，不复制字形获取或缓存逻辑。
- `FormulaEditor` 布局：工具栏（模式切换、撤销、重做、模板菜单）→ 结构化模式为 `FormulaView`（含光标与选区装饰），LaTeX 模式为等宽源码 `TextField`（`features` 中有 `LatexSourceAssist` 时经其 `wrapSourceField` 包裹）加其下的 `FormulaView` 预览 → 诊断提示条 → `bindings.accessoryBar` → `SymbolPalette`（`showPalette` 时）。CORE-88、39、40、48、50 的公式输入一律使用 `FormulaEditor`，不自行组合 `FormulaView` 与源码文本框。
- 结构化模式的文字输入：公式区获得焦点时打开 `TextInputConnection`（`enableDeltaModel: true`、`autocorrect: false`、`enableSuggestions: false`）；`TextEditingDeltaInsertion` → `insertText`，`TextEditingDeltaDeletion` → `deleteBackward`；组合输入（composing 区间非空）期间不提交，组合结束后整体插入；硬件按键先交 `bindings.handleKey`。
- `FormulaCopyButton`：点击执行 `copy(format: auto)`；长按、右键或按钮旁下拉箭头打开“复制为”菜单（LaTeX、Unicode 文本、MathML、图片），按 `formatsFor` 结果把不可用项置灰并显示原因（“公式未完成，只能复制 LaTeX”“含无法用 Unicode 表示的结构”“公式过大”）；`copy` 返回 false 时显示“已复制”，抛错时显示“复制失败，请重试”；`features` 中无 `FormulaCopier` 时点击即 `clipboard.writeText(latex)`，菜单只有 LaTeX 一项。
- 组装：`installEditorInput` 在 `app/lib/composition/installers.dart` 的功能安装段追加一行；`DeclarationPanel` 的量的种类为自由文本，合法性由 `engine.check` 诊断给出。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）

**实现约束**
- 控制器与模板语义唯一见CORE-59，Widget只使用UTF-16下标；本卡不另建worker/结果/字形缓存；复用CORE-37 FormulaView并消费其失效。
- FormulaCopier与EditorPlatformBindings低层接口唯一归本卡，不依赖CORE-91复制实现或平台实现；缺省仅复制LaTeX，已有方法签名与接缝路径不变。FormulaCopier实现说明中原CORE-52改为CORE-91。
- installEditorInput构造默认绑定/UnitOptions并追加安装片段，聚合维护者单写合入，本卡计接入行；共享Widget不import binding。
- 仅Flutter SDK；锁版/设备前提沿用CORE-59，未获得能力不写通过。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-87_TEST.md](../Test/core/S2_CORE-87_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约520行；`app/lib/ui/editor/`、`app/lib/editor/unit_options.dart`及附属`app/lib/composition/editor_input.dart`。分阶段：① 完整编辑器/绑定/符号面板340行；② 声明面板/UnitOptions/复制按钮180行；用Fake worker/复制端口分别独立构建验证。静态palette与自测不计。
