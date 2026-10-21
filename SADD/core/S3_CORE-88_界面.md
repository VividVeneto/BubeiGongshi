### CORE-88 公式编辑与草稿界面

**目标**：提供公式新建/编辑、草稿恢复与保存确认界面，消费公式库与编辑器的稳定契约。

**范围**
- 包含：新建与编辑页面、FormulaEditVm、SaveOutcome、NewFormulaArgs、草稿恢复/去抖/后台落盘，保存校验与警告确认，编辑路由接入。
- 不包含：浏览/详情/修订diff与LibraryListDecorator（CORE-38）；草稿仓储（CORE-61）；源码控制器（CORE-59）；公式编辑器/复制按钮（CORE-87）；核心校验与存储（CORE-09、CORE-14）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-09、CORE-13、CORE-14、CORE-36、CORE-37、CORE-38、CORE-55、CORE-58、CORE-59、CORE-61、CORE-87

**接口契约**

```dart
// app/lib/library/edit_routes.dart；页面在app/lib/ui/library/，只收VM与deps.ui。
List<GoRoute> libraryEditRoutes(AppDeps deps); // /library/new、/library/:itemId/edit
final class NewFormulaArgs { const NewFormulaArgs(this.latex); final String latex; }
// /library/new接受extra: NewFormulaArgs；保存成功后以Saved为页面返回值pop。
// app/lib/library/formula_edit_vm.dart
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
```

- 调用的 op：CORE-14 library.create/revise/update_meta及读取现有条目；CORE-61 library.draft_get/draft_put/draft_delete等草稿op（具体命名/形状严格以CORE-61为准）；engine.check经CORE-37 worker。只消费底层定义，不变更存储/草稿契约。
- 路由的静态/library/new在CORE-38的/library/:itemId之前登记；composition并列聚合libraryEditRoutes与libraryRoutes。CORE-38不依赖本卡，只发出已约定路径导航。本卡不新增Installer；登记片段由聚合维护者单写合入。
- SaveOutcome及其子类、FormulaEditVm、NewFormulaArgs只由本卡定义；浏览VM/装饰接口只由CORE-38定义，互不复制。调用新建并等待Saved返回的消费者直接依赖本卡。

Dart文件归属：本卡VM/用例/DTO在app/lib/library/，Widget和编辑页面在app/lib/ui/library/；沿用既有路径以免纯拆卡导致不必要导入迁移。Widget不接收CoreBinding或HttpTransport，只接VM与回调。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| LIB_NOT_FOUND | CORE-14 | 编辑目标已删除：提示后退出 |
| `LIB_TRASHED` | CORE-14 | 对回收站条目编辑：提示先恢复 |
| `LIB_READ_ONLY` | CORE-14 | 不应出现（预置条目一律走 `library.revise`）；出现时提示并上报日志 |
| `LIB_NOT_VERIFIED` | CORE-14 | 保存时核心仍判定未通过：返回 `Blocked`，草稿保留 |

产品约束追踪：见README §6 Q10、Q11、Q16、Q32、Q35；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 编辑页：标题 1–200 字符、学科必填；`editor.canSave` 为 false 时保存按钮禁用；Warning 弹确认框，确认后带 `ConfirmRecord` 保存；保存成功后删除对应草稿。
- 草稿：订阅 `editor.draftChanges`（500 ms 去抖）与标题等表单变化，写 `library.draft_put`；新建公式只保留一份 `"new"` 草稿。应用转入后台时立即写一次。
- 预置条目（`read_only`）可编辑，保存走 `library.revise` 生成用户修订；派生条目在脱离前只读，编辑按钮显示为“脱离后编辑”。
- 页面按CORE-55关键布局自适应，旋转与textScaler变化不重建VM、编辑器或草稿会话；不得因旋转额外保存或发出library调用；保存为唯一primary操作。
- 开草稿时先询问“继续编辑草稿/放弃草稿”；源码、声明、标题及编辑器光标/焦点按原有约定恢复。后台立即落盘不替代500ms去抖。
- 新建初始LaTeX只来自NewFormulaArgs/initialLatex，保存成功删除对应草稿后返回Saved；警告确认复用ConfirmRecordDto，不自行放宽核心判定。
- 外部前提：`go_router`（CORE-36 已引入）；不新增第三方包。

**验收标准**：测试方案全文见 [Test/core/S3_CORE-88_TEST.md](../Test/core/S3_CORE-88_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约380行；app/lib/library/、app/lib/ui/library/中本卡编辑/草稿VM及页面、编辑路由和本卡编写的composition接入行（VM190、界面155、接入35）；不计自测、夹具、草稿/schema数据与生成物。
