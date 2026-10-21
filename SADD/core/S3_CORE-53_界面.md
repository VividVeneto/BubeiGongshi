### CORE-53 LaTeX 命令补全

**目标**：LaTeX 源码模式下键入 `\` 加字母或 `\begin{` 时弹出候选命令列表，用键盘或点按插入白名单命令与带空位的模板；按键与 TeXstudio、Overleaf 等 LaTeX 编辑器一致，但不占用输入法切换键 Ctrl+Space（README §6 Q16）。

**范围**
- 包含：补全数据 `app/assets/editor/latex_commands.json`；前缀识别与候选排序（纯函数）；候选弹层与按键处理；接受候选后的源码替换与空位选中；安装点 `installLatexCompletion`（登记 CORE-87 `LatexSourceAssist`）。
- 不包含：结构化模式的输入（符号面板与模板，CORE-37）；命令白名单本身（CORE-06，本卡数据只能是其子集）；语法诊断与排版（CORE-37 `EditorWorker`）；用户自定义宏与片段（CORE-06 禁止宏定义）；补全按键自定义（键位固定，WIN-08 列为保留键）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-06、CORE-37、CORE-55、CORE-59、CORE-58、CORE-28、CORE-87

**接口契约**

```dart
// app/lib/editor/completion/latex_completion.dart
enum LatexEntryKind { command, environment }
final class LatexCommandEntry {               // latex_commands.json 的一项
  final String name;                          // 不含反斜杠，如 "frac"；环境项为环境名，如 "pmatrix"
  final LatexEntryKind kind;
  final String insert;                        // 接受后写入的源码，如 "\\frac{\\fmlhole}{\\fmlhole}"
  final String labelKey;                      // 中文说明的本地化键，如 "latex.frac" → “分式”
  final int rank;                             // 0–100，常用度，数据文件给定
}
sealed class CompletionContext { int get start; String get typed; }   // UTF-16 下标
final class CommandPrefix extends CompletionContext {}       // start 指向 '\'，typed 为其后已键入的字母（可为空）
final class EnvironmentPrefix extends CompletionContext {}   // start 指向 '\begin{' 的 '\'，typed 为环境名前缀
CompletionContext? contextAt(String source, int caret);
List<LatexCommandEntry> rankCandidates(List<LatexCommandEntry> all, CompletionContext ctx,
                                       {Map<String, int> recent = const {}, int limit = 50});
final class CompletionEdit { final String source; final int selStart, selEnd; }
CompletionEdit applyCandidate(String source, int caret, CompletionContext ctx, LatexCommandEntry e);

final class LatexCompletionController extends ChangeNotifier {
  LatexCompletionController(List<LatexCommandEntry> entries, LatexSourceSession session);
  bool get visible; List<LatexCommandEntry> get items; int get highlighted;
  void onValueChanged(TextEditingValue v);    // 重新计算 contextAt 与候选；组合输入期间隐藏
  void move(int delta); bool accept(); void dismiss();
}
final class LatexCompletionAssist implements LatexSourceAssist { const LatexCompletionAssist(this.entries); final List<LatexCommandEntry> entries; }

// app/lib/editor/completion/install.dart
Future<void> installLatexCompletion(CompositionContext ctx);   // 读取资产并登记 LatexSourceAssist
```

- 前缀识别（`contextAt`）：光标前紧邻 `\` 加 0 个或多个 ASCII 字母，且该 `\` 前连续反斜杠个数为偶数（`\\` 换行不触发）→ `CommandPrefix`；光标位于 `\begin{` 之后、尚无 `}` 且其间只有字母 → `EnvironmentPrefix`；其余返回 null。光标位于单词中间时，`typed` 只取光标前部分，替换时连同光标后紧邻的字母一并替换。
- 排序（`rankCandidates`）：只取与上下文同类的项；分三档——区分大小写的前缀匹配、不区分大小写的前缀匹配、按字母顺序的子序列匹配；同档内依次按本次运行的使用次数 `recent`、`rank` 降序，再按名称长度与字典序升序；最多 `limit` 项。`typed` 为空时按 `rank` 取前 50 项。
- 接受（`applyCandidate`）：命令项用 `insert` 替换 `[start, 光标后单词末尾)`；环境项替换 `\begin{typed` 及其后紧邻的 `}`（如有），`insert` 为完整环境（如 `\begin{pmatrix}\fmlhole & \fmlhole \\ \fmlhole & \fmlhole\end{pmatrix}`）。插入内容含 `\fmlhole` 时选中第一个空位的整段文字，否则光标置于插入内容末尾。
- 补全数据：覆盖 CORE-06 白名单中的全部命令与环境、希腊字母、关系符与常用运算符；CORE-87 `palette.json` 中出现的每个命令都必须有对应项；不得出现禁止清单中的名称（`def`、`newcommand`、`input`、`include`、`write` 等）。
- 按键（弹层可见时；不可见时一律交回源码框）：

| 按键 | 动作 | 依据 |
| --- | --- | --- |
| ↑ / ↓ | 移动高亮（循环） | TeXstudio、Overleaf |
| PageUp / PageDown | 高亮移动 8 项 | 通用列表 |
| Tab、Enter | 插入高亮项 | TeXstudio、Overleaf |
| Esc | 关闭弹层；此后在同一前缀内继续键入字母不再弹出，键入新的 `\` 后恢复 | 通用 |
| 字母 | 继续过滤 | 通用 |
| 其他字符、空格、←/→ 移出前缀 | 关闭弹层，字符照常输入 | 通用 |

- 本卡不新增错误码；资产文件缺失或解析失败时不登记 `LatexSourceAssist`，记 AppLog warning（不含公式内容），源码框照常可用。

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/editor/completion/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/editor/completion/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 补全弹层用 CORE-55 `surfaceRaised` 与 `FmlElevation`，行高取 `FmlDensity`（`pointer` 32、`touch` 48）；`pointer` 下显示选中行快捷键提示，`touch` 下只点按。
- 弹层不获取焦点：源码框保持焦点，软键盘不收起；弹层锚定在光标矩形下方（经 `LatexSourceSession.fieldKey` 取 `RenderEditable` 的光标矩形），下方空间不足时显示在上方；最多同时显示 8 行，右侧以 CORE-37 `MathText` 显示 `insert` 的排版预览（空位显示为虚线框）。
- 按键拦截用 `Shortcuts` 与 `Actions` 包裹源码框，只在 `visible` 为 true 时覆盖表中按键；不判断运行平台，触屏点按候选即插入。
- 组合输入（`TextEditingValue.composing` 非空）期间不弹出、已弹出则隐藏；组合结束后按新值重新判断。
- 接受候选经 `LatexSourceSession.commitEdit` 写入，作为一次独立的撤销步（撤销一次回到接受前的源码与光标）。
- `recent` 只保存在内存中，进程退出即清空；不写偏好、不写日志。
- 每次按键的前缀识别与排序在 UI 线程同步完成，不调用核心 op。
- 组装：`installLatexCompletion` 追加到 CORE-36 `installers.dart` 的 `featureInstallers`，紧随 `installFormulaCopy`。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
- 外部前提：只用 Flutter SDK；不新增第三方包。

**验收标准**：测试方案全文见 [Test/core/S3_CORE-53_TEST.md](../Test/core/S3_CORE-53_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约470行；app/lib/editor/completion/、app/lib/ui/editor/completion/及本卡编写的编辑器/composition接入行；不计自测、夹具、候选/模板JSON资源数据与生成物。

