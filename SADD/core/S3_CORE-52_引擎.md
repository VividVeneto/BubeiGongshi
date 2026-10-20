### CORE-52 公式复制格式与富格式导出

**目标**：复制公式时一次写入多种常见剪贴板格式，由粘贴目标自动选用（纯文本编辑器得到 LaTeX，Office 得到可编辑公式，绘图与聊天软件得到图片）；另提供“复制为”菜单单独复制某一种格式。

**范围**
- 包含：Rust 导出 crate `fml-export`（MathML、SVG；Unicode 文本复用 CORE-06）；FFI op `export.formula`；Dart 用例 `DefaultFormulaCopier`（实现 CORE-59 `FormulaCopier`：按格式组装剪贴板负载、渲染 PNG、生成 HTML 片段、缓存、无平台写入器时降级为纯文本）；平台接缝 `FormulaClipboardWriter`；安装点 `installFormulaCopy`。
- 不包含：各平台把负载写入系统剪贴板（WIN-05、AND-14）；复制按钮与“复制为”菜单（CORE-59 `FormulaCopyButton`）；公式绘制函数本身（CORE-37 `paintDisplayList`）；粘贴与粘贴图片（CORE-59、CORE-50）；应用私有剪贴板格式与复制后自动清空（README §6 Q12 不采用）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-05、CORE-06、CORE-07、CORE-12、CORE-37、CORE-55、CORE-59、CORE-58、CORE-73

**接口契约**

```rust
// crates/fml-export/src/lib.rs
pub struct MathMlOptions { pub display_block: bool /* true → <math display="block"> */, pub annotate_latex: bool /* 附 LaTeX 原文注释 */ }
pub fn export_mathml(ast: &FormulaNode, symbols: &SymbolEnv, profile: &NotationProfile,
                     source: &str, source_map: &SourceMap, opts: &MathMlOptions) -> Result<String, FmlError>;
pub struct SvgOptions { pub padding_px: f32 /* 默认 8 */, pub title: Option<String> /* 写入 <title>，用 LaTeX 原文 */ }
pub fn export_svg(dl: &DisplayList, fonts: &[FontData], opts: &SvgOptions) -> Result<String, FmlError>;
```

- FFI op（长任务，经 CORE-03 `submit` 调用）：`export.formula`
  - 请求 `{"source": string（≤ 64 KiB）, "notation_profile_id": string（默认 "cn-default"）, "user_decls": [SymbolDecl]（默认 []）, "formats": ["unicode"|"mathml"|"svg"|"display"]}`。
  - 处理：CORE-06 `parse`（`budget_ms = 200`）→ CORE-07 `bind`（与 `engine.check` 相同的方案与声明规则，不做量纲校验）→ CORE-12 `layout`（`font_size_px = 20`、`display_style = true`、`WrapMode::Scroll`）→ 按 `formats` 导出。
  - 响应 `{"unicode"?: string, "mathml"?: string, "svg"?: string, "display"?: DisplayList, "omitted": [{"format": string, "code": string}]}`；某一格式失败只记入 `omitted`，不影响其他格式。

```dart
// app/lib/export/formula_copy.dart
final class FormulaClipboardPayload {             // null 字段不写入剪贴板
  const FormulaClipboardPayload({this.text, this.latex, this.mathml, this.html, this.svg, this.png, this.pngWidth = 0, this.pngHeight = 0});
  final String? text;                              // 纯文本（auto 与 latex 时为 LaTeX 源码；unicode / mathml 时为对应文本）
  final String? latex, mathml, html, svg;          // 专用格式：text/x-latex、MathML、HTML 片段、SVG
  final Uint8List? png; final int pngWidth, pngHeight;   // 透明背景 PNG 与像素尺寸
}
abstract interface class FormulaClipboardWriter {  // 平台卡经 PlatformPorts.platformInstallers 登记（WIN-05、AND-14）
  Future<bool> write(FormulaClipboardPayload payload);   // 平台不支持的字段忽略；返回 true 表示系统已显示复制反馈（如 Android 13+）
}
// FormulaCopyFormat、FormulaCopier 定义见 CORE-59
final class DefaultFormulaCopier implements FormulaCopier {
  DefaultFormulaCopier({required CoreBinding core, required FeatureRegistry features, required ClipboardAdapter clipboard});
}
String formulaHtmlFragment({required String latex, required Uint8List png, required double width, required double height});
void installFormulaCopy(CompositionContext ctx);   // ctx.features.register<FormulaCopier>(DefaultFormulaCopier(...))
```

- 格式组合（`FormulaCopier.copy` 生成的负载）：

| 选择 | text | latex | mathml | html | svg | png |
| --- | --- | --- | --- | --- | --- | --- |
| 自动（默认点击） | LaTeX 源码 | LaTeX 源码 | MathML | 内嵌 PNG 的 HTML 片段 | SVG | PNG |
| 复制为 LaTeX | LaTeX 源码 | LaTeX 源码 | — | — | — | — |
| 复制为 Unicode 文本 | Unicode 文本 | — | — | — | — | — |
| 复制为 MathML | MathML 文本 | — | — | — | — | — |
| 复制为图片 | — | — | — | — | SVG | PNG |

- 错误码（本卡登记）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `EXPORT_NOT_RENDERABLE` | warning | 否 | 源码无法解析（`ast` 为 null）或含空位 `\fmlhole`；此时只能复制 LaTeX |
| `EXPORT_TOO_LARGE` | warning | 否 | MathML 超过 1 MiB、SVG 超过 4 MiB，或 PNG 在 1 倍缩放下仍超过 8192 像素边长；该格式被省略 |

- 界面行为：由 CORE-59 `FormulaCopyButton` 呈现；本卡以 `formatsFor` 告知不可用格式（`EXPORT_NOT_RENDERABLE` → 只有 auto 与 latex；Unicode 导出失败 → 无 unicode；`EXPORT_TOO_LARGE` → 无对应格式）。

paintDisplayList从CORE-37所有的app/lib/render/display_list_painter.dart导入，不从ui/editor导入；它只依赖dart:ui及生成DTO。

DefaultFormulaCopier的formatsFor/copy完整实现CORE-59声明：userDecls是当前修订/会话的不可变声明快照，逐次原样传给export.formula；缓存键用其规范序列化内容，不用对象identity。formatsFor与copy使用同一声明输入，不读取隐式当前公式。

EngineContext.snapshot返回Result；FFI适配先用snapshot()?取得Arc再检查unavailable/expected_generation，任一失败不调用领域算法。层提交后mark_unavailable的Err向调用方传播，不忽略。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 本卡出现的界面元素（复制结果提示、导出预览与错误提示）用 CORE-55 `showFmlToast` 与组件，不新增颜色与动效。
- MathML：输出 MathML Core（`<math xmlns="http://www.w3.org/1998/Math/MathML">`），`annotate_latex` 时外包 `<semantics>` 并附 `<annotation encoding="application/x-tex">`。映射：Symbol → `mi`（正体或斜体按 CORE-07 `display_glyph` 与方案），Number → `mn`，Unit → `mi mathvariant="normal"`，分式 → `mfrac`，根式 → `msqrt/mroot`，上下标 → `msup/msub/msubsup`，求和与极限 → `munderover`，矩阵与向量 → `mtable`，分段 → 左大括号加 `mtable`。AST 不记写法时按 `source_map` 取运算符所在源码片段决定显示：`\cdot` → ·，`\times` → ×，并列 → `<mo>&#x2062;</mo>`（不可见乘号）；`\frac` → `mfrac`，`/` → `<mo>/</mo>`；函数名后加 `<mo>&#x2061;</mo>`。含 `Hole` 时不导出。
- SVG：`viewBox` 取 DisplayList `bounds` 外扩 `padding_px`；`Glyph` 用 CORE-12 `glyph_outline` 取轮廓、按 `size / units_per_em` 缩放并翻转 y 轴后写成 `<path>`；`Rule` → `<rect>`；`Path` 按描边或填充写出；填充 `#000000`、背景透明；只含 `svg/title/g/path/rect` 元素，不含 `text`、字体、脚本、样式表、外部引用与 `foreignObject`。
- PNG 在 Dart 侧生成：以 `display` 调用 CORE-37 `paintDisplayList`（`scale = 3`，四周 8 逻辑像素留白，透明背景）→ `toImage` → PNG；任一边超过 8192 像素时依次降到 2、1 倍，仍超过则省略图片并记 `EXPORT_TOO_LARGE`。与界面同一绘制函数，两端图片与屏幕显示一致。
- HTML 片段：`<span class="fml-formula"><img src="data:image/png;base64,…" alt="<转义后的 LaTeX>" style="width:Wpx;height:Hpx;vertical-align:middle"></span>`（W、H 为逻辑尺寸），不含脚本、样式表与外部链接；富文本编辑器、邮件与网页编辑框据此粘贴为图片。
- `DefaultFormulaCopier`：每次复制时才从 `features` 取 `FormulaClipboardWriter`（平台安装点在功能安装点之后执行）；取不到时任何选择都退化为 `clipboard.writeText(text)`（“复制为图片”置灰）。导出结果按 `(latex, notationProfileId, engineGeneration)` 做 16 项 LRU 缓存；按CORE-73命中前refresh与expectedGeneration校验；键还必须含userDecls、formats，通知清旧代数；失败不缓存，复制过程中代数改变丢弃旧结果并至多重试一次；`EXPORT_NOT_RENDERABLE` 时“自动”只写 text 与 latex。
- 只在用户点击复制时调用；公式源码与导出内容不写日志（CORE-28）。
- 组装：`installFormulaCopy` 追加到 CORE-36 `installers.dart` 的 `featureInstallers`，紧随 `installEditorInput`；各页面的复制入口为 CORE-59 `FormulaCopyButton`，本卡不提供界面。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
- 外部前提：Rust 侧无新增第三方库（XML 转义自写，测试用 dev-dependency `roxmltree` 解析输出，版本按 ADR-V5-15 锁入 `Cargo.lock`）；Dart 侧只用 Flutter SDK。

**验收标准**
- [R08] 语料全部可解析公式导出的 MathML 能被 `roxmltree` 解析，元素只属于 MathML Core；`a\cdot b`、`a\times b`、`ab` 分别得到 ·、×、`&#x2062;`；`\frac{a}{b}` 与 `a/b` 分别得到 `mfrac` 与 `<mo>/</mo>`；附带的 annotation 等于原 LaTeX。
- [R08] SVG 只含允许的元素；`<path>` 数等于 DisplayList 中 Glyph 与 Path 命令数之和，`<rect>` 数等于 Rule 数；`<title>` 为 LaTeX 原文。
- [R08] 单元测试（登记假写入器）：五种选择得到的负载字段与“格式组合”表逐格一致；含 `\fmlhole` 时“自动”只含 text 与 latex，`formatsFor` 只含 auto 与 latex；未登记写入器时调用 `clipboard.writeText`。
- [R10] 源码中的 `<`、`&`、`"` 在 MathML、SVG 与 HTML 中均被转义；HTML 与 SVG 输出中不出现 `<script`、`on*=` 属性与 `http:`/`https:` 链接。
- [R20] 复制后检查日志目录，不含公式源码与导出内容。
- [R03] 性能：按CORE-01预算表“公式复制”行，由AND-12/WIN-13在S7真机测量；本卡Fake只验证负载与时序，不计真机完成条件。

- [R08][R19] 相同源码/方案但不同声明、格式或同ID新字体不能命中旧导出；一次复制的display/SVG/PNG代数一致，更新竞态按CORE-73重试，第二次竞态返回可重试错误且剪贴板未写旧图片。

**规模**：约 450 行；主包 `crates/fml-export/`（约 260 行），附属：FFI 处理函数 `crates/fml-ffi/src/ops/export.rs`（约 30 行）与跨语言另一侧 `app/lib/export/`（约 160 行）。

