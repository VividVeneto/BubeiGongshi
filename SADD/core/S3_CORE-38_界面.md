### CORE-38 公式库界面

**目标**：提供公式库的浏览、检索、详情、修订历史与恢复、新建与编辑、回收站界面。

**范围**
- 包含：列表、详情、修订差异/恢复、编辑与回收站，消费 CORE-61 草稿 op。
- 不包含：导入与单位页（CORE-60）、草稿仓储（CORE-61）、计算（CORE-48，下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-08、CORE-09、CORE-13、CORE-14、CORE-36、CORE-37、CORE-55、CORE-59、CORE-61、CORE-58

**接口契约**

```dart
// app/lib/library/routes.dart —— 在 CORE-36 `app/lib/composition/routes.dart` 追加一行；静态路径先于 :itemId 声明；页面只收 VM 与 `deps.ui`（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
// /library  /library/new  /library/trash  /library/:itemId  /library/:itemId/edit
// /library 接受查询参数 search=1：进入后搜索框获得焦点（WIN-08 的“查找”快捷键使用；无平台判断）
List<GoRoute> libraryRoutes(AppDeps deps);

// app/lib/library/library_vm.dart
final class LibraryQuery {            // 字段对应 CORE-14 SearchQuery（page 由 VM 管理）
  final String? text, subject, course, source /* preset|user|imported|derived */, role, mastery, validation;
  final DimensionFullDto? dimension;   // CORE-67 由 CORE-08 DimensionFull schema 生成，与 CORE-14 SearchQuery.dimension 同形
  final List<String> tags;
  final bool trashed;                 // 回收站页为 true
}
final class LibraryVm extends ChangeNotifier {
  LibraryVm(CoreBinding core);
  LibraryQuery get query; void setQuery(LibraryQuery q);   // text 变化去抖 200 ms，其余立即生效
  int get total; ItemSummaryDto? itemAt(int index);        // 每页 50 条懒加载；未加载返回 null 并触发加载
  Future<void> refresh();
}
final class FormulaDetailVm extends ChangeNotifier {
  FormulaDetailVm(CoreBinding core, String itemId);
  ItemViewDto? get item; DisplayListDto? get display; List<RevisionSummaryDto> get history;
  Future<RevisionDiffDto> diff(String fromRevision, String toRevision);
  Future<void> restore(String revisionId);   // library.restore：生成新修订，不改历史
  Future<void> detach();                     // 派生条目：提交 derived_from = null 的新修订（CORE-14 脱离规则）
  Future<void> trash();
}
sealed class SaveOutcome {}
final class Saved extends SaveOutcome { final String itemId, revisionId; }
final class NeedsConfirm extends SaveOutcome { final List<DiagnosticDto> warnings; }   // 带 confirm 再调 save
final class Blocked extends SaveOutcome { final List<DiagnosticDto> errors; }          // 含 Error 或空位
final class FormulaEditVm extends ChangeNotifier {
  static Future<FormulaEditVm> open(AppDeps deps, {String? itemId, String? initialLatex});  // 有草稿时先问“继续编辑草稿 / 放弃草稿”；initialLatex 只用于新建
  FormulaEditorController get editor;
  String title; String subject; String? course; List<String> tags;
  Future<SaveOutcome> save({ConfirmRecordDto? confirm});   // 新建：library.create（meta + revision）；已有条目：library.revise，元数据有变化时再调 library.update_meta；draft = false
  Future<void> discardDraft();
}
enum LibraryScope { library, trash }
abstract interface class LibraryListDecorator {   // CORE-54 登记；未登记时列表无多选
  Widget wrapList(BuildContext context, LibraryScope scope, LibraryVm vm, Widget list);
  Widget decorateItem(BuildContext context, LibraryScope scope, LibraryVm vm, int index, ItemSummaryDto item, Widget tile);
}
```

- 调用的 op：`library.*`（CORE-14；草稿 op 归 CORE-61）、`engine.check`（经 CORE-37 worker）、`typeset.layout`（详情页显示）。

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/library/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/library/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `LIB_NOT_FOUND` | CORE-14 | 打开的条目不存在或已物理删除：提示后返回列表 |
| `LIB_TRASHED` | CORE-14 | 对回收站条目编辑：提示先恢复 |
| `LIB_READ_ONLY` | CORE-14 | 不应出现（预置条目一律走 `library.revise`）；出现时提示并上报日志 |
| `LIB_NOT_VERIFIED` | CORE-14 | 保存时核心仍判定未通过：返回 `Blocked`，草稿保留 |

产品约束追踪：见README §6 Q10、Q11、Q16、Q32、Q35；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 宽度为 `expanded` 时列表与详情用 CORE-58 `TwoPane` 并排（列表宽 360），点击列表项在右栏打开详情、路由仍为 `/library/:itemId`；`compact` 与 `medium` 推入详情页。列表首屏未就绪超过 150 ms 显示 `Skeleton`。
- 列表只按 `total` 与页懒加载，不一次取全量；筛选条件组合为“与”，与 CORE-14 搜索语义一致。
- 编辑页：标题 1–200 字符、学科必填；`editor.canSave` 为 false 时保存按钮禁用；Warning 弹确认框，确认后带 `ConfirmRecord` 保存；保存成功后删除对应草稿。
- 草稿：订阅 `editor.draftChanges`（500 ms 去抖）与标题等表单变化，写 `library.draft_put`；新建公式只保留一份 `"new"` 草稿。应用转入后台时立即写一次。
- 预置条目（`read_only`）可编辑，保存走 `library.revise` 生成用户修订；派生条目在脱离前只读，编辑按钮显示为“脱离后编辑”。
- 差异页：源码按 `TextHunk` 行级显示；AST 差异在两侧 DisplayList 上用 `layout.highlight` 标出变更节点。
- 导入与单位入口导航到 CORE-60 提供的静态路由（下游说明，非契约）。
- 组装：`libraryRoutes` 追加到 `app/lib/composition/routes.dart`；本卡不新增 Installer。 `/library/new` 接受 `extra: NewFormulaArgs { String latex }`（CORE-50 识别结果保存时使用），保存成功后以 `Saved` 作为页面返回值 pop。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
- 外部前提：`go_router`（CORE-36 已引入）；不新增第三方包。
- 列表修饰：公式库页与回收站页（`LibraryQuery.trashed = true`）在 `features` 中有 `LibraryListDecorator` 时用 `wrapList` 包裹列表、用 `decorateItem` 包裹每个列表项；本卡不实现多选。
- 复制公式：详情页标题栏与列表项菜单放置 CORE-59 `FormulaCopyButton`（`latex` 为当前修订的 `source_latex`，`notationProfileId` 为该公式的记号方案，`userDecls` 为当前修订的symbols声明快照），本卡不直接访问剪贴板。

**验收标准**
- [R11] Widget 测试（Fake CoreBinding 回放）与集成测试（真实核心）各一套：搜索、按学科/课程/来源/量纲/掌握度/校验状态筛选、打开详情、查看历史与差异、恢复旧版生成新修订、移入回收站与恢复。
- [R11] Widget 测试：打开 `/library?search=1` 后搜索框持有焦点，键入文字即触发搜索。
- [R08] Widget 测试：详情页点击“复制公式”后登记的假 `FormulaCopier` 收到当前修订的 `source_latex`、声明快照userDecls与 `format: auto`；列表项菜单“复制为 → 图片”收到 `format: image`。
- [R11] 10000 条测试库：列表滚动满足 CORE-01 全局资源预算表“列表滚动”行；首屏满足“公式库搜索首屏（10000 条）”行。
- [R08] 编辑页：含空位或 Error 时保存禁用；Warning 时确认后修订带 `ConfirmRecord`；编辑中杀进程，重开编辑页提示恢复草稿且源码、声明、标题一致。
- [R42.e] Widget 测试：宽 1200 时点击列表项在右栏显示详情且路由为 `/library/:itemId`；宽缩到 800 后详情变为整页，返回回到列表且滚动位置不变。

- [R42.e][R42.b] 页面接入验收（Fake CoreBinding 提供 200 条条目）：`/library` 滚到第 120 条、`/library/:itemId/edit` 标题框输入“动能”且编辑器源码为 `E_k=\frac{1}{2}mv^2`、光标在 `m` 前，分别在 360×800 ↔ 800×360 往返 3 次：页面 `State` 为同一对象，滚动偏移、标题文本、编辑器源码与光标、焦点不变，期间不发出 `library.*` 调用、不另存草稿；`textScaler` 2.0 下列表、详情、编辑页 `tester.takeException()` 为 null；编辑页恰有 1 个 `FmlButtonVariant.primary`（“保存”），列表页 0 个（“新建”为浮动按钮）；宽档（1280×800）为 `TwoPane` 且无选中时右侧为空状态。

**规模**：约 420 行；主包 `app/lib/library/`、`app/lib/ui/library/`（不含 import/、units/）。

