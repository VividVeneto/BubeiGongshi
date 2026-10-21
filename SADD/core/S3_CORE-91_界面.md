### CORE-91 多格式公式复制用例

**目标**：一次组装多种常用剪贴板格式供粘贴目标选择，并提供“复制为”的单格式复制用例；只消费稳定导出内核和平台负载端口。

**范围**
- 包含：DefaultFormulaCopier实现CORE-87 FormulaCopier；formatsFor/copy、声明快照和generation一致性、PNG生成、HTML片段、16项缓存、无平台写入器时降级纯文本、installFormulaCopy。
- 不包含：MathML/SVG/Unicode导出算法与export.formula（CORE-52）；FormulaClipboardPayload/Writer低层端口（CORE-52）；平台系统剪贴板实现（WIN-05、AND-14，下游说明，非契约）；复制按钮/菜单（CORE-87）；绘制函数本身（CORE-37）；粘贴/图片识别（CORE-87、CORE-50，下游说明，非契约）；私有格式与自动清空（Q12不采用）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-28、CORE-36、CORE-37、CORE-52、CORE-55、CORE-58、CORE-87、CORE-73

**接口契约**

```dart
// app/lib/export/default_formula_copier.dart；负载/写入端口从CORE-52 formula_copy.dart导入
// FormulaCopyFormat、FormulaCopier 定义见 CORE-87
final class DefaultFormulaCopier implements FormulaCopier {
  DefaultFormulaCopier({required CoreBinding core, required FeatureRegistry features, required ClipboardAdapter clipboard});
}
String formulaHtmlFragment({required String latex, required Uint8List png, required double width, required double height});
// app/lib/export/install.dart
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

- 调用op：CORE-52 export.formula（CORE-03 submit长任务）。请求声明、方案与formats按底层契约原样发送；本卡不重复实现parse/bind/layout或登记export.formula。
- 错误引用：EXPORT_NOT_RENDERABLE、EXPORT_TOO_LARGE的定义/级别/触发条件唯一在CORE-52；本卡执行PNG边长保护时引用EXPORT_TOO_LARGE，不另定义码。
- 界面行为：由 CORE-87 `FormulaCopyButton` 呈现；本卡以 `formatsFor` 告知不可用格式（`EXPORT_NOT_RENDERABLE` → 只有 auto 与 latex；Unicode 导出失败 → 无 unicode；`EXPORT_TOO_LARGE` → 无对应格式）。

paintDisplayList从CORE-37所有的app/lib/render/display_list_painter.dart导入，不从ui/editor导入；它只依赖dart:ui及生成DTO。

DefaultFormulaCopier的formatsFor/copy完整实现CORE-87声明：userDecls是当前修订/会话的不可变声明快照，逐次原样传给export.formula；缓存键用其规范序列化内容，不用对象identity。formatsFor与copy使用同一声明输入，不读取隐式当前公式。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 本卡出现的界面元素（复制结果提示、导出预览与错误提示）用 CORE-55 `showFmlToast` 与组件，不新增颜色与动效。
- PNG 在 Dart 侧生成：以 `display` 调用 CORE-37 `paintDisplayList`（`scale = 3`，四周 8 逻辑像素留白，透明背景）→ `toImage` → PNG；任一边超过 8192 像素时依次降到 2、1 倍，仍超过则省略图片并记 `EXPORT_TOO_LARGE`。与界面同一绘制函数，两端图片与屏幕显示一致。
- HTML 片段：`<span class="fml-formula"><img src="data:image/png;base64,…" alt="<转义后的 LaTeX>" style="width:Wpx;height:Hpx;vertical-align:middle"></span>`（W、H 为逻辑尺寸），不含脚本、样式表与外部链接；富文本编辑器、邮件与网页编辑框据此粘贴为图片。
- `DefaultFormulaCopier`：每次复制时才从 `features` 取 `FormulaClipboardWriter`（平台安装点在功能安装点之后执行）；取不到时任何选择都退化为 `clipboard.writeText(text)`（“复制为图片”置灰）。导出结果按 `(latex, notationProfileId, engineGeneration)` 做 16 项 LRU 缓存；按CORE-73命中前refresh与expectedGeneration校验；键还必须含userDecls、formats，通知清旧代数；失败不缓存，复制过程中代数改变丢弃旧结果并至多重试一次；`EXPORT_NOT_RENDERABLE` 时“自动”只写 text 与 latex。
- 只在用户点击复制时调用；公式源码与导出内容不写日志（CORE-28）。
- 组装：`installFormulaCopy` 追加到 CORE-36 `installers.dart` 的 `featureInstallers`，紧随 `installEditorInput`；各页面的复制入口为 CORE-87 `FormulaCopyButton`，本卡不提供界面。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
- 外部前提：Rust 侧无新增第三方库（XML 转义自写，测试用 dev-dependency `roxmltree` 解析输出，版本按 ADR-V5-15 锁入 `Cargo.lock`）；Dart 侧只用 Flutter SDK。
- FormulaClipboardPayload/Writer从CORE-52导入；本卡不重声明低层端口，不使CORE-52反向依赖本卡。平台安装可以晚于功能安装，writer每次复制时才取。
- DefaultFormulaCopier、formulaHtmlFragment、installFormulaCopy唯一归本卡；CORE-87只声明FormulaCopier/FormulaCopyFormat与展示按钮，不构造本实现。composition按安装顺序聚合，不把复制服务注入领域crate。

**验收标准**：测试方案全文见 [Test/core/S3_CORE-91_TEST.md](../Test/core/S3_CORE-91_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约255行；app/lib/export/default_formula_copier.dart、HTML/PNG辅助、install.dart及本卡编写的composition复制服务安装行（Copier160、PNG/HTML80、安装15）；纯负载/写入端口35行留CORE-52，不重复计；不计自测、夹具、schema/图片资源数据与生成物。
