### CORE-52 公式导出内核与剪贴板负载契约

**目标**：提供Rust MathML/SVG导出、export.formula处理和跨平台剪贴板负载/写入端口的低层稳定契约。

**范围**
- 包含：fml-export MathML/SVG，Unicode复用CORE-92；FFI长任务export.formula；纯Dart FormulaClipboardPayload与FormulaClipboardWriter端口，供平台实现与上层复制用例共同消费；EXPORT_*错误唯一定义。
- 不包含：DefaultFormulaCopier、多格式负载编排、PNG/HTML/缓存与安装（CORE-91，下游说明，非契约）；平台剪贴板实现（WIN-05、AND-14，下游说明，非契约）；复制按钮/菜单（CORE-87，下游说明，非契约）；粘贴/识别（CORE-59、CORE-50，下游说明，非契约）；私有格式与自动清空（Q12不采用）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-05、CORE-06、CORE-07、CORE-12、CORE-73、CORE-92、CORE-94

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
  - 处理：CORE-06 `parse`（`budget_ms = 200`）→ CORE-07 `bind`（与 `engine.check` 相同的方案与声明规则，不做量纲校验）→ CORE-94 `layout`（`font_size_px = 20`、`display_style = true`、`WrapMode::Scroll`）→ 按 `formats` 导出。
  - 响应 `{"unicode"?: string, "mathml"?: string, "svg"?: string, "display"?: DisplayList, "omitted": [{"format": string, "code": string}]}`；某一格式失败只记入 `omitted`，不影响其他格式。

```dart
// app/lib/export/formula_copy.dart —— 纯负载/端口，无Widget、复制用例或安装依赖
final class FormulaClipboardPayload {             // null 字段不写入剪贴板
  const FormulaClipboardPayload({this.text, this.latex, this.mathml, this.html, this.svg, this.png, this.pngWidth = 0, this.pngHeight = 0});
  final String? text;                              // 纯文本（auto 与 latex 时为 LaTeX 源码；unicode / mathml 时为对应文本）
  final String? latex, mathml, html, svg;          // 专用格式：text/x-latex、MathML、HTML 片段、SVG
  final Uint8List? png; final int pngWidth, pngHeight;   // 透明背景 PNG 与像素尺寸
}
abstract interface class FormulaClipboardWriter {  // 平台卡经 PlatformPorts.platformInstallers 登记（WIN-05、AND-14）
  Future<bool> write(FormulaClipboardPayload payload);   // 平台不支持的字段忽略；返回 true 表示系统已显示复制反馈（如 Android 13+）
}
```

- FormulaClipboardPayload与FormulaClipboardWriter只由本卡定义；平台写入器继续直接依赖本卡，在PlatformPorts.platformInstallers登记。上层复制服务只消费端口，不把平台接缝搬到UI子卡。

- 错误码（本卡登记）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `EXPORT_NOT_RENDERABLE` | warning | 否 | 源码无法解析（`ast` 为 null）或含空位 `\fmlhole`；此时只能复制 LaTeX |
| `EXPORT_TOO_LARGE` | warning | 否 | MathML 超过 1 MiB、SVG 超过 4 MiB，或 PNG 在 1 倍缩放下仍超过 8192 像素边长；该格式被省略 |

- EXPORT_TOO_LARGE的PNG边长条件由上层复制用例执行时引用同一错误码；错误语义/级别/可重试性仍只在本卡定义，不因发生位置而再登记。

EngineContext.snapshot返回Result；FFI适配先用snapshot()?取得Arc再检查unavailable/expected_generation，任一失败不调用领域算法。层提交后mark_unavailable的Err向调用方传播，不忽略。

**实现约束**
- MathML：输出 MathML Core（`<math xmlns="http://www.w3.org/1998/Math/MathML">`），`annotate_latex` 时外包 `<semantics>` 并附 `<annotation encoding="application/x-tex">`。映射：Symbol → `mi`（正体或斜体按 CORE-07 `display_glyph` 与方案），Number → `mn`，Unit → `mi mathvariant="normal"`，分式 → `mfrac`，根式 → `msqrt/mroot`，上下标 → `msup/msub/msubsup`，求和与极限 → `munderover`，矩阵与向量 → `mtable`，分段 → 左大括号加 `mtable`。AST 不记写法时按 `source_map` 取运算符所在源码片段决定显示：`\cdot` → ·，`\times` → ×，并列 → `<mo>&#x2062;</mo>`（不可见乘号）；`\frac` → `mfrac`，`/` → `<mo>/</mo>`；函数名后加 `<mo>&#x2061;</mo>`。含 `Hole` 时不导出。
- SVG：`viewBox` 取 DisplayList `bounds` 外扩 `padding_px`；`Glyph` 用 CORE-12 `glyph_outline` 取轮廓、按 `size / units_per_em` 缩放并翻转 y 轴后写成 `<path>`；`Rule` → `<rect>`；`Path` 按描边或填充写出；填充 `#000000`、背景透明；只含 `svg/title/g/path/rect` 元素，不含 `text`、字体、脚本、样式表、外部引用与 `foreignObject`。
- FFI处理仅按请求formats执行导出，每种失败进入omitted，不令其他格式丢失；使用同一EngineContext快照，绑定规则与engine.check一致；不做量纲校验。
- 本卡纯负载/端口不依赖Flutter Widget、CORE-59编辑器或CORE-91复制实现；领域crate无I/O，导出源码和结果不得写日志。
- 外部前提：Rust侧无新增第三方库，XML转义自写；测试dev-dependency roxmltree按ADR-V5-15锁入Cargo.lock。Dart负载仅用SDK Uint8List类型。

**验收标准**：测试方案全文见 [Test/core/S3_CORE-52_TEST.md](../Test/core/S3_CORE-52_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约645行，分阶段（Ⅰ MathML全AST导出约360行；Ⅱ SVG、FFI/op处理绑定与纯负载/写入端口约285行；各阶段可独立构建与测试）；crates/fml-export/、crates/fml-ffi/src/ops/export.rs、本卡编写的dispatch/binding接入行及app/lib/export/formula_copy.dart的低层负载/端口；不计自测、夹具、schema/资源数据与生成物；完整复制服务归CORE-91，不重复计。
