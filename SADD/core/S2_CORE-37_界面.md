### CORE-37 公式渲染组件与编辑器

**目标**：提供两端共用的公式显示组件与结构化/LaTeX 双模式编辑器；编辑状态只有一份 LaTeX 源码，排版全部来自 Rust DisplayList，校验错误在编辑器内即时标注。

**范围**
- 包含：EditorWorker、EditorRequest/Result、FormulaView、MathText、FormulaDecorations 与共享绘制函数。
- 不包含：编辑控制器、输入组件、复制按钮与声明面板，迁至 CORE-59（下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-08、CORE-09、CORE-12、CORE-55、CORE-56、CORE-58、CORE-73

**接口契约**

```dart
// app/lib/editor/editor_worker.dart
final class EditorWorker {
  static Future<EditorWorker> start(CoreLibrarySpec spec);   // 常驻 isolate，内部 CoreBinding.open(spec)
  Future<EditorResult> run(EditorRequest req);   // 新请求到达时丢弃尚未开始的旧请求，其 Future 以 EditorSuperseded 结束
  Future<DisplayListDto> layoutStatic(String latex, {LayoutOptionsDto? layout});   // 只读公式；独立 FIFO 队列，不被 run 取代；(latex, layout, engineGeneration) 256 项 LRU；按CORE-73查询/通知失效
  Future<void> close();
}
final class EditorRequest { final String source; final String notationProfileId;
  final List<SymbolDeclDto> userDecls; final bool empirical; final LayoutOptionsDto layout; }
final class EditorResult { final CheckResponseDto check; final DisplayListDto? display; }
final class EditorSuperseded implements Exception {}

// app/lib/ui/editor/formula_view.dart
final class FormulaDecorations {
  final Rect? caret; final List<Rect> selection; final List<(Rect, String /* severity */)> underlines;
  static const none = FormulaDecorations();
}
class FormulaView extends StatelessWidget {
  const FormulaView({super.key, required this.display, this.decorations = FormulaDecorations.none,
                     this.onTap, this.scale = 1.0});
  final DisplayListDto display; final FormulaDecorations decorations;
  final void Function(NodePathDto? path, Offset local)? onTap; final double scale;
}

// app/lib/ui/editor/math_text.dart：只读公式显示（题干、选项、列表项），排版失败时显示等宽源码
class MathText extends StatelessWidget {
  const MathText(this.latex, {super.key, required this.worker, this.scale = 1.0});
  final String latex; final EditorWorker worker; final double scale;
}

// app/lib/render/display_list_painter.dart（本卡所有，依赖dart:ui与生成DTO，不依赖Widget/ui目录）
void paintDisplayList(Canvas canvas, DisplayListDto display, {double scale = 1.0});   // FormulaView 内部同样调用；供离屏渲染（CORE-52 复制图片）
// app/lib/editor/install.dart
Future<void> installEditor(CompositionContext ctx);   // EditorWorker.start(ctx.core.spec) 后注册到 ctx.features
```

- Dart DTO（`app/lib/binding/dto/`，按 CORE-67 schema 生成）：`DisplayListDto`、`DrawCmdDto`、`NodePathDto`、`LayoutOptionsDto`、`SourceSpanDto`、`CheckResponseDto`（`ast, source_map, symbols, check_result`）、`SymbolDeclDto`（CORE-05 `SymbolDecl` 镜像）。
- 调用的 op：`engine.check`（CORE-56 登记，语义见 CORE-09，`budget_ms = 100`）、`typeset.layout` 与 `typeset.glyph_outlines`（CORE-56 登记，DTO 为 CORE-12 类型）、`units.compatible`（CORE-08）。
Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/editor/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/editor/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `TYPESET_NO_FONT` | CORE-12 | 显示“数学字体未安装”占位，源码仍可编辑 |
| `PARSE_HOLE_UNFILLED` | CORE-06 | 源码仍有空位；不画下划线，空位框高亮，`canSave` 为 false |
| `PARSE_LIMIT_EXCEEDED` | CORE-05 | 粘贴或输入后源码超过 64 KiB：拒绝本次修改，提示条显示原因 |
| `PARSE_TIMEOUT` | CORE-06 | worker 自动以同一请求重试 1 次，仍超时则保留 stale 排版并提示 |

产品约束追踪：见README §6 Q12、Q13、Q16；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 后台计算：`engine.check` 与 `typeset.layout` 只在 `EditorWorker` 的 isolate 中调用，UI 线程不调用这两个 op；每次修改发出一个请求，worker 只执行最新请求；结果按 `(source, userDecls, notationProfileId, empirical, layout, engineGeneration)` 哈希做 64 项 LRU 缓存；`layout.highlight` 填入 Error 级诊断的 NodePath。
- 结果/字形缓存启用CORE-73协议：worker命中前调用engine.generation，以返回值作为整条check/layout链的expectedGeneration；CORE-03信封代数回传用于校验，通知清空旧代数分区；绘制路径只从匹配代数的结果快照读取。query失败/unavailable时清空且不用缓存；迟到旧代数结果丢弃重试一次。layoutStatic键另含默认方案cn-default、空声明、empirical=false；run键必须额外含empirical，避免相同源码使用不同经验标记误命中。
- 绘制：`Glyph` 用 `typeset.glyph_outlines` 得到的路径绘制（按 `size / units_per_em` 缩放并翻转 y 轴），`Glyph.font` 先经 `DisplayList.font_ids` 换成字体 ID 再请求，路径按 `(engineGeneration, font_id, glyph_id)` 缓存（上限 4096 条）；`Rule` 画矩形，`Path` 按描边或填充绘制；不使用平台字体渲染公式字形。语义标签用 `semantic_text`。
- 外部前提：只用 Flutter SDK 自带库（`dart:isolate`、`dart:ui` 的 `Path`）；不引入第三方编辑器或数学渲染包（附录 A ADR-V5-04）。空位记法 `\fmlhole` 见 ADR-V5-17。

**验收标准**
- [R01] 黄金图测试：固定Linux CI镜像/Flutter/字体/缩放对同一DisplayList主机黄金图像素差≤1%；两端真机布局和截图对照归AND-12/WIN-13 checklist，不承诺跨栅格器像素相等。
- [R03] 自动化只验证连续输入100字符的请求去重、最新结果上屏与帧时间样本导出，Fake计时不判预算；S7由两平台性能卡在参考设备运行benchmark，worker按 CORE-01“公式解析（≤256 节点）”“量纲校验”“单式排版”三行分别判定，界面按“点击到可见反馈”行判定。预算按已采纳 ADR-V5-25，不把M0实测写成另一次采纳。

- [R19] worker缓存填满后同ID替换字体，下一次query/通知清旧分区，结果和glyph轮廓来自新代数；通知丢失仍因命中前query失效。check后layout前更新时丢弃整链并重试，不组合不同快照。

**规模**：约 300 行；主包 `app/lib/editor/editor_worker.dart`、`app/lib/ui/editor/formula_view.dart`、`app/lib/ui/editor/math_text.dart`、`app/lib/render/`。

