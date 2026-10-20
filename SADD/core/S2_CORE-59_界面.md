### CORE-59 公式编辑控制器与输入组件

**目标**：公式编辑控制器与输入组件，与原卡分开实施与验收。

**范围**
- 包含：结构化/LaTeX 编辑、模板、撤销、IME、声明面板、复制接缝与平台绑定。
- 不包含：依赖卡已定义的业务算法、存储与平台能力；不修改其契约。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-08、CORE-09、CORE-12、CORE-37、CORE-55、CORE-58

**接口契约**

```dart
// app/lib/editor/editor_types.dart
enum EditorMode { structured, latex }
enum CursorMove { left, right, up, down, lineStart, lineEnd, nextHole, prevHole }
enum TemplateId { fraction, sqrt, nthRoot, superscript, subscript, parentheses, abs,
                  integral, definiteIntegral, sum, product, limit, vector, matrix2x2, cases }
final class EditorContext {
  final String notationProfileId; final bool empirical; final LayoutOptionsDto layout;  // LayoutOptions 见 CORE-12
}
final class EditorSnapshot {
  final String source; final TextSelection selection;     // 下标一律为 UTF-16 code unit
  final EditorMode mode;
  final DisplayListDto? display; final bool stale;          // 源码无法解析时保留上一次排版并置 stale
  final List<DiagnosticDto> diagnostics;                    // inputRange 已由 UTF-8 字节换算为 UTF-16
  final String validation;                                  // CORE-05 Validation 的 snake_case 名
  final int holeCount;
  bool get canSave;   // 无 Error 级诊断 && holeCount == 0 && !stale
}
final class EditorDraft { final String source; final List<SymbolDeclDto> userDecls; }
// 此默认值函数归 app/lib/composition/editor_defaults.dart，结果注入Widget
EditorMode defaultEditorMode(RuntimeSnapshot rt) =>
    rt.os == 'windows' ? EditorMode.latex : EditorMode.structured;   // 工具栏可临时切换，不保存偏好（README §6 Q13）

// app/lib/editor/editor_controller.dart
final class FormulaEditorController extends ValueNotifier<EditorSnapshot> {
  FormulaEditorController({required EditorWorker worker, required EditorContext context,
      required EditorMode initialMode, String initialSource = '', List<SymbolDeclDto> initialDecls = const []});
  void insertText(String text);            // 键入字符或符号面板片段；光标选中空位时替换该空位
  void insertTemplate(TemplateId id);      // 有选区时选区内容放入第一个空位
  void deleteBackward(); void deleteForward();
  void moveCursor(CursorMove m, {bool extend = false});
  void tapAt(Offset local);                // 命中区域 → 最近停靠点（结构化）或源码下标（LaTeX）
  void setSelection(TextSelection s);      // LaTeX 模式源码文本框回写
  bool get canUndo; bool get canRedo; void undo(); void redo();
  String copySelection();                  // 返回选区对应源码；结构化模式先扩到完整节点
  void paste(String text);
  bool setMode(EditorMode m);              // false = 被拒（见实现约束）
  List<SymbolDeclDto> get userDecls;
  void declareSymbol(SymbolDeclDto decl);  // 按 glyph 覆盖
  void removeDeclaration(String glyph);
  Stream<EditorDraft> get draftChanges;    // 去抖 500 ms
}

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
abstract interface class FormulaCopier {           // CORE-52 实现并登记；未登记时 FormulaCopyButton 只复制 LaTeX 文本
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

- 模板片段（`app/lib/editor/templates.dart`；插入后光标落在第一个空位）：

| TemplateId | 插入的源码 | 空位数 |
| --- | --- | --- |
| fraction | `\frac{\fmlhole}{\fmlhole}` | 2 |
| sqrt / nthRoot | `\sqrt{\fmlhole}` / `\sqrt[\fmlhole]{\fmlhole}` | 1 / 2 |
| superscript / subscript | `^{\fmlhole}` / `_{\fmlhole}` | 1 / 1 |
| parentheses / abs | `\left(\fmlhole\right)` / `\left|\fmlhole\right|` | 1 / 1 |
| integral | `\int \fmlhole \,\mathrm{d}x` | 1 |
| definiteIntegral | `\int_{\fmlhole}^{\fmlhole} \fmlhole \,\mathrm{d}x` | 3 |
| sum / product | `\sum_{i=\fmlhole}^{\fmlhole} \fmlhole` / `\prod_{i=\fmlhole}^{\fmlhole} \fmlhole` | 3 / 3 |
| limit | `\lim_{x \to \fmlhole} \fmlhole` | 2 |
| vector | `\vec{\fmlhole}` | 1 |
| matrix2x2 | `\begin{pmatrix}\fmlhole & \fmlhole \\ \fmlhole & \fmlhole\end{pmatrix}` | 4 |
| cases | `\begin{cases}\fmlhole & \fmlhole \\ \fmlhole & \fmlhole\end{cases}` | 4 |

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

**实现约束**

- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 编辑器工具栏、模板栏、补全入口与“复制为”菜单的控件尺寸取 `FmlDensity`（`pointer` 32、`touch` 48）；公式渲染颜色取 `FmlColors.onSurface`，深浅色切换后重绘不重新排版。`defaultEditorMode` 仅在composition构造默认值时读取RuntimeSnapshot.os（README §6 Q13），共享Widget只消费已注入EditorMode。
- 源码是唯一事实：结构化与 LaTeX 两种模式编辑同一字符串，切换模式不改写源码；不维护独立的结构化文档树。
- 字节与 UTF-16 换算：Rust 的 `input_range` 与 `source_map` 是 UTF-8 字节区间，controller 对每个源码版本建一次换算表，界面层只使用 UTF-16 下标。
- 停靠点（结构化模式）：取 `source_map` 中的叶节点（Symbol、Number、Unit、Hole，以及没有子节点的 Function 名），每个叶节点的起止下标为停靠点，去重后排序；空位以整段为一个停靠点（选中状态）。left/right 走相邻停靠点；up/down 取当前叶节点 `node_bounds` 正上/正下方水平重叠最多的叶节点；nextHole/prevHole 循环遍历空位（键盘 Tab / Shift+Tab 由平台卡映射）。光标矩形取叶节点矩形的左/右边，高为该矩形高。光标不会落在命令名内部。
- 键入（结构化模式）：在光标处插入原文；光标选中空位时用键入内容替换该空位。LaTeX 模式下 `\fmlhole` 作为普通文本可编辑。
- 删除（结构化模式）：退格删除以光标为终点的叶节点源码；若删除后其所在组为空（前一字符为 `{` 且后一字符为 `}`），补入 `\fmlhole`。光标在空位上退格时：若该空位所属模板的所有槽位都是空位，删除整个模板；否则移到前一个停靠点。LaTeX 模式按字符删除。
- 撤销：快照 `(source, selection)`，上限 200 步；1 s 内同一位置连续 `insertText` 合并为一步；模式切换不是撤销步。
- 模式切换：结构化 → LaTeX 总是允许；LaTeX → 结构化要求最近一次 `engine.check` 的 `ast` 非 null，否则返回 false 并提示“源码有语法错误，修正后才能切换”。
- 粘贴：超过 64 KiB 拒绝；结构化模式下粘贴后若 `ast` 为 null，自动切到 LaTeX 模式并保留粘贴内容与诊断。
- 后台计算与缓存完全遵守CORE-37；本卡不另建worker、结果或字形缓存；由CORE-37统一消费CORE-73的query/通知失效，不在本卡另建缓存。
- 绘制复用CORE-37的FormulaView与render绘制器，不复制字形获取或缓存逻辑。
- `canSave` 为 false 时调用方不得保存正式修订；Warning 由调用方在保存时确认并记录；Info 只提示。
- 外部前提：只用 Flutter SDK 自带库（`dart:isolate`、`dart:ui` 的 `Path`）；不引入第三方编辑器或数学渲染包（附录 A ADR-V5-04）。空位记法 `\fmlhole` 见 ADR-V5-17。
- `FormulaEditor` 布局：工具栏（模式切换、撤销、重做、模板菜单）→ 结构化模式为 `FormulaView`（含光标与选区装饰），LaTeX 模式为等宽源码 `TextField`（`features` 中有 `LatexSourceAssist` 时经其 `wrapSourceField` 包裹）加其下的 `FormulaView` 预览 → 诊断提示条 → `bindings.accessoryBar` → `SymbolPalette`（`showPalette` 时）。CORE-38、39、40、48、50 的公式输入一律使用 `FormulaEditor`，不自行组合 `FormulaView` 与源码文本框。
- 结构化模式的文字输入：公式区获得焦点时打开 `TextInputConnection`（`enableDeltaModel: true`、`autocorrect: false`、`enableSuggestions: false`）；`TextEditingDeltaInsertion` → `insertText`，`TextEditingDeltaDeletion` → `deleteBackward`；组合输入（composing 区间非空）期间不提交，组合结束后整体插入；硬件按键先交 `bindings.handleKey`。
- `FormulaCopyButton`：点击执行 `copy(format: auto)`；长按、右键或按钮旁下拉箭头打开“复制为”菜单（LaTeX、Unicode 文本、MathML、图片），按 `formatsFor` 结果把不可用项置灰并显示原因（“公式未完成，只能复制 LaTeX”“含无法用 Unicode 表示的结构”“公式过大”）；`copy` 返回 false 时显示“已复制”，抛错时显示“复制失败，请重试”；`features` 中无 `FormulaCopier` 时点击即 `clipboard.writeText(latex)`，菜单只有 LaTeX 一项。
- 组装：`installEditorInput` 在 `app/lib/composition/installers.dart` 的功能安装段追加一行；`DeclarationPanel` 的量的种类为自由文本，合法性由 `engine.check` 诊断给出。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）


- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**
- [R08] Widget 测试：15 种模板逐一插入后 `engine.check` 返回非空 `ast`，空位数与模板表一致；nextHole 依次经过全部空位；在空位键入后该空位被替换。
- [R08] 结构化导航：语料抽样 50 条公式，left/right 遍历的停靠点集合与叶节点起止下标去重集合相同，光标从不落在命令名内部。
- [R08] 删除：`\frac{a}{b}` 光标在 b 后连续退格依次得到 `\frac{a}{\fmlhole}` → 光标移到 a 后 → `\frac{\fmlhole}{\fmlhole}` → 空串。
- [R08] 撤销/重做 50 步后源码与选区逐步复原；1 s 内连续键入合并为一步；结构化 → LaTeX → 结构化后源码逐字相同；LaTeX 模式源码含 `PARSE_SYNTAX` 时切换返回 false。
- [R10] 结构化模式粘贴 `\input{x}`：自动切到 LaTeX 模式，`PARSE_FORBIDDEN_COMMAND` 下划线覆盖 UTF-16 [0, 6)；源码前有中文与全角字符时下划线位置仍正确（字节换算单元测试）。
- [R09] 符号面板每一项单独 `engine.check` 无 Error；标为 ISO 的项在 `contracts/vectors/iso80000-2.yaml` 中 `input` 能力为真；国内方案与 ISO 方案下 `\mathrm{tg}\,x` 均能排版且无 Error。
- [R14] 在声明面板修改量纲后，下一个 worker 结果即更新诊断；冲突时 `TYPE_DIM_CONFLICT` 的 NodePath 区域出现 Error 下划线。
- [R08] Widget 测试：`FormulaCopyButton` 点击调用一次 `copy(format: auto)`，返回 false 时显示“已复制”；右键与长按打开“复制为”菜单，`formatsFor` 不含的项置灰；未登记 `FormulaCopier` 时点击写入 LaTeX 文本。
- [R08] Widget 测试：`FeatureRegistry` 中登记测试用 `EditorPlatformBindings` 时其 `accessoryBar` 出现在公式区下方且按键先交给它；未登记时 Tab 依次选中空位；模拟 IME 组合输入“α”期间源码不变，组合结束后插入一次。
- [R42.d] Widget 测试：`InputModalityScope` 为 `pointer` 与 `touch` 时编辑器工具栏按钮最小尺寸分别为 32 与 48；切换深色主题后公式颜色变为 `onSurface` 且未重新调用排版。

- [R08][R14] Fake FormulaCopier记录formatsFor/copy的userDecls：按钮透传当前声明且不修改；相同latex/方案而声明不同不复用旧导出，编辑器声明修改后菜单与复制均取新快照。

**规模**：约 440 行；主包 `app/lib/editor/`、`app/lib/ui/editor/`（controller、templates、palette、declaration、formula_editor、copy）（含测试与必要的同构建单元接缝）。

