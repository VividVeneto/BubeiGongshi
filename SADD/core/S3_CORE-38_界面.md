### CORE-38 公式库界面

**目标**：提供公式库的浏览、检索、详情、修订历史与恢复、回收站界面。

**范围**
- 包含：列表、详情、修订差异/恢复与回收站；定义供多选功能消费的 LibraryListDecorator。
- 不包含：新建/编辑与草稿界面（CORE-88，下游说明，非契约）；导入与单位页（CORE-60，下游说明，非契约）；草稿仓储（CORE-61，下游说明，非契约）；计算（CORE-48，下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-08、CORE-14、CORE-36、CORE-37、CORE-55、CORE-58、CORE-87、CORE-79

**接口契约**

```dart
// app/lib/library/routes.dart —— 页面只收 VM 与 deps.ui；聚合维护者登记片段，消费卡不直接写共享文件。
// /library /library/trash /library/:itemId；/library 接受 search=1，进入后搜索框获得焦点。
// /library/new 与 /library/:itemId/edit 由 CORE-88 的 libraryEditRoutes 提供（下游说明，非契约），静态路径由composition先登记。
List<GoRoute> libraryRoutes(AppDeps deps);

// app/lib/library/library_vm.dart
final class LibraryQuery {            // 字段对应 CORE-79 SearchQuery（page 由 VM 管理）
  final String? text, subject, course, source /* preset|user|imported|derived */, role, mastery, validation;
  final DimensionFullDto? dimension;   // CORE-67 由 CORE-08 DimensionFull schema 生成，与 CORE-79 SearchQuery.dimension 同形
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
enum LibraryScope { library, trash }
abstract interface class LibraryListDecorator {   // CORE-54 登记；未登记时列表无多选
  Widget wrapList(BuildContext context, LibraryScope scope, LibraryVm vm, Widget list);
  Widget decorateItem(BuildContext context, LibraryScope scope, LibraryVm vm, int index, ItemSummaryDto item, Widget tile);
}
```

- 调用的 op：library.list/get、修订历史/restore、回收站相关 library.*（CORE-14），检索与diff（CORE-79）；详情显示消费 CORE-37 worker 的排版与高亮结果。本卡不调用草稿 op，不导入编辑页VM。

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/library/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/library/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `LIB_NOT_FOUND` | CORE-14 | 打开的条目不存在或已物理删除：提示后返回列表 |

产品约束追踪：见README §6 Q10、Q11、Q16、Q32、Q35；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 宽度为 `expanded` 时列表与详情用 CORE-58 `TwoPane` 并排（列表宽 360），点击列表项在右栏打开详情、路由仍为 `/library/:itemId`；`compact` 与 `medium` 推入详情页。列表首屏未就绪超过 150 ms 显示 `Skeleton`。
- 列表只按 `total` 与页懒加载，不一次取全量；筛选条件组合为“与”，与 CORE-79 搜索语义一致。
- 预置条目（read_only）显示可编辑入口；派生条目在detach前只读，按钮显示“脱离后编辑”。详情VM按CORE-14脱离规则提交新修订；编辑/保存实现由独立上层编辑页承担，本卡只导航，不导入其VM。
- 差异页：源码按 `TextHunk` 行级显示；AST 差异在两侧 DisplayList 上用 `layout.highlight` 标出变更节点。
- 导入与单位入口导航到 CORE-60 提供的静态路由（下游说明，非契约）。
- 组装：libraryRoutes 追加到 app/lib/composition/routes.dart；本卡不新增 Installer。新建/编辑按钮只按静态路由导航，不导入 CORE-88；composition 将编辑路由与浏览路由并列安装，先登记静态 /library/new、/library/trash，再登记 :itemId。本卡不以聚合函数导入编辑路由。
- 外部前提：`go_router`（CORE-36 已引入）；不新增第三方包。
- 列表修饰：公式库页与回收站页（`LibraryQuery.trashed = true`）在 `features` 中有 `LibraryListDecorator` 时用 `wrapList` 包裹列表、用 `decorateItem` 包裹每个列表项；本卡不实现多选。
- 复制公式：详情页标题栏与列表项菜单放置 CORE-87 `FormulaCopyButton`（`latex` 为当前修订的 `source_latex`，`notationProfileId` 为该公式的记号方案，`userDecls` 为当前修订的symbols声明快照），本卡不直接访问剪贴板。

**验收标准**：测试方案全文见 [Test/core/S3_CORE-38_TEST.md](../Test/core/S3_CORE-38_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约600行，分阶段（Ⅰ 列表/筛选与路由、装饰/复制入口接入约300行；Ⅱ 详情/修订diff与恢复约300行；各阶段可独立构建与测试）；app/lib/library/、app/lib/ui/library/中本卡浏览/详情实现及本卡编写的composition接入行；编辑/草稿实现归CORE-88，不重复计；不计自测、夹具、数据与生成物。
