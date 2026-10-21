### CORE-59 公式编辑控制器

**目标**：以源码为唯一事实实现编辑控制器、模板、光标、撤销与声明状态；完整Widget与平台绑定接缝由CORE-87实现。

**范围**
- 包含：编辑数据模型、结构化/LaTeX控制器、模板、撤销与声明状态、UTF-8/UTF-16换算及模式默认值。
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


**实现约束**

- 源码是唯一事实：结构化与 LaTeX 两种模式编辑同一字符串，切换模式不改写源码；不维护独立的结构化文档树。
- 字节与 UTF-16 换算：Rust 的 `input_range` 与 `source_map` 是 UTF-8 字节区间，controller 对每个源码版本建一次换算表，界面层只使用 UTF-16 下标。
- 停靠点（结构化模式）：取 `source_map` 中的叶节点（Symbol、Number、Unit、Hole，以及没有子节点的 Function 名），每个叶节点的起止下标为停靠点，去重后排序；空位以整段为一个停靠点（选中状态）。left/right 走相邻停靠点；up/down 取当前叶节点 `node_bounds` 正上/正下方水平重叠最多的叶节点；nextHole/prevHole 循环遍历空位（键盘 Tab / Shift+Tab 由平台卡映射）。光标矩形取叶节点矩形的左/右边，高为该矩形高。光标不会落在命令名内部。
- 键入（结构化模式）：在光标处插入原文；光标选中空位时用键入内容替换该空位。LaTeX 模式下 `\fmlhole` 作为普通文本可编辑。
- 删除（结构化模式）：退格删除以光标为终点的叶节点源码；若删除后其所在组为空（前一字符为 `{` 且后一字符为 `}`），补入 `\fmlhole`。光标在空位上退格时：若该空位所属模板的所有槽位都是空位，删除整个模板；否则移到前一个停靠点。LaTeX 模式按字符删除。
- 撤销：快照 `(source, selection)`，上限 200 步；1 s 内同一位置连续 `insertText` 合并为一步；模式切换不是撤销步。
- 模式切换：结构化 → LaTeX 总是允许；LaTeX → 结构化要求最近一次 `engine.check` 的 `ast` 非 null，否则返回 false 并提示“源码有语法错误，修正后才能切换”。
- 粘贴：超过 64 KiB 拒绝；结构化模式下粘贴后若 `ast` 为 null，自动切到 LaTeX 模式并保留粘贴内容与诊断。
- 后台计算与缓存完全遵守CORE-37；本卡不另建worker、结果或字形缓存；由CORE-37统一消费CORE-73的query/通知失效，不在本卡另建缓存。
- `canSave` 为 false 时调用方不得保存正式修订；Warning 由调用方在保存时确认并记录；Info 只提示。
- 外部前提：只用 Flutter SDK 自带库（`dart:isolate`、`dart:ui` 的 `Path`）；不引入第三方编辑器或数学渲染包（附录 A ADR-V5-04）。空位记法 `\fmlhole` 见 ADR-V5-17。


- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-59_TEST.md](../Test/core/S2_CORE-59_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约465行；`app/lib/editor/editor_types.dart`、`editor_controller.dart`、`templates.dart`与附属`app/lib/composition/editor_defaults.dart`。不计CORE-87 Widget/IME接缝、自测与模板数据。
