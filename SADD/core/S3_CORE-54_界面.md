### CORE-54 公式库批量选择与批量操作

**目标**：在公式库列表与回收站中支持多选与批量操作（加标签、去标签、移入回收站、恢复），键盘、鼠标与触控操作沿用文件管理器习惯（README §6 Q16）。

**范围**
- 包含：选择模型（按 ID 选择，或“当前筛选的全部结果减去排除项”）；列表修饰与选择工具栏；键盘、鼠标与触控交互；编辑标签对话框；移入回收站后的撤销提示条；附属的 Rust 批量操作与 op `library.batch`；安装点 `installLibraryBatch`（登记 CORE-38 `LibraryListDecorator`）。
- 不包含：列表、筛选与搜索（CORE-38、CORE-14）；单条编辑与单条元数据修改（CORE-38、CORE-14 `library.update_meta`）；批量导入（CORE-14、CORE-38）；批量导出与批量复制公式（V1 不做）；手动永久删除（回收站条目 30 天后由 CORE-14 清理）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-13、CORE-14、CORE-36、CORE-38、CORE-55、CORE-58

**接口契约**

```dart
// app/lib/library/batch/selection.dart
sealed class LibrarySelection { bool contains(String itemId); int count(int total); }
final class SelectedIds extends LibrarySelection { final Set<String> ids; }                     // ≤ 10000
final class AllMatching extends LibrarySelection { final LibraryQuery query; final Set<String> except; }
final class SelectionController extends ChangeNotifier {
  SelectionController(LibraryVm vm, LibraryScope scope);
  bool get active; LibrarySelection get selection; int? get focusIndex;
  void toggle(int index); void extendTo(int index); void selectAll(); void clear();
  void moveFocus(int delta, {bool extend = false});   // extend：从锚点到新焦点整段选中
}
// app/lib/library/batch/batch_vm.dart
sealed class BatchActionDto {}
final class EditTags extends BatchActionDto { final List<String> add, remove; }
final class TrashItems extends BatchActionDto {}
final class UntrashItems extends BatchActionDto {}
final class BatchResultDto { final int applied, unchanged; final List<String> appliedIds; final List<(String itemId, String code)> skipped; }
final class BatchVm extends ChangeNotifier {
  BatchVm(CoreBinding core);
  bool get running; double? get progress;
  Future<BatchResultDto> run(LibrarySelection s, BatchActionDto a, {CancelToken? cancel});   // library.batch（长任务）
}
final class LibraryBatchDecorator implements LibraryListDecorator { const LibraryBatchDecorator(); }   // wrapList/decorateItem 返回下列 Widget
// app/lib/ui/library/batch/selection_widgets.dart（只收 SelectionController、BatchVm 状态与回调）
class SelectionToolbar extends StatelessWidget { const SelectionToolbar({super.key, required this.selection, required this.total, required this.onAction}); final SelectionController selection; final int total; final void Function(BatchActionDto a) onAction; }
class EditTagsDialog extends StatefulWidget { const EditTagsDialog({super.key, required this.knownTags}); final List<String> knownTags; }   // pop 返回 EditTags 或 null
// app/lib/library/batch/install.dart
Future<void> installLibraryBatch(CompositionContext ctx);
```

```rust
// crates/fml-store/src/library/batch.rs（附属）
pub enum BatchTarget { Ids(Vec<FormulaItemId>) /* ≤ 10000 */, Query { query: SearchQuery, except: Vec<FormulaItemId> } }
pub enum BatchAction { EditTags { add: Vec<String>, remove: Vec<String> }, Trash, Untrash }
pub struct BatchResult { pub applied: u32, pub unchanged: u32, pub applied_ids: Vec<FormulaItemId>,
                         pub skipped: Vec<(FormulaItemId, String /* 错误码 */)> }
pub fn apply_batch(db: &Db, target: &BatchTarget, action: &BatchAction, now_ms: i64,
                   progress: &dyn Fn(u32, u32), cancel: &CancelFlag) -> Result<BatchResult, FmlError>;
```

- FFI op：`library.batch`（长任务，进度为“已处理/总数”）：请求 `{"target": {"ids": [..]} | {"query": SearchQuery, "except": [..]}, "action": {"edit_tags": {"add", "remove"}} | "trash" | "untrash"}`；响应 `BatchResult`。`Query` 目标忽略 `page` 与 `page_size`，按 `SearchQuery` 全部结果（含 `trashed` 取值）展开。
- 语义：整批在一个 CORE-13 写事务中完成，复用 CORE-14 的单条写入逻辑（同 crate 内 `pub(crate)` 函数），每个有变化的条目写 `updated_at_ms` 并 `enqueue_outbox`（条目元数据）；取消或出错时整批回滚。标签先去首尾空白、按字面去重，再对每个条目执行“先加后去”；已有的标签不重复添加，没有的标签移除时计入 `unchanged`。`Trash` 对已在回收站的条目、`Untrash` 对不在回收站的条目计入 `unchanged`。预置条目可改标签、可移入回收站（与单条操作一致）。
- 错误码与界面行为：

| 错误码 | 级别 | 可重试 | 触发条件与界面行为 |
| --- | --- | --- | --- |
| `LIB_BATCH_TOO_LARGE` | error | 否 | 展开后的目标超过 10000 条：整批拒绝，提示“一次最多处理 10000 条，请先缩小筛选范围” |
| `LIB_BATCH_CANCELLED` | info | 否 | 用户取消：整批回滚，提示“已取消，未作修改” |

- 列表仅经FmlCommandScope声明CORE-58的LibraryBatchCommands：move.<方向>/extend.<方向>/toggle/selectAll/clear/open/trash/editTags/menu/undo（方向独立ID见58）；不在共享Widget处理实体按键。鼠标点击与触控长按调用同一语义动作，选择模型不变。Windows/Android实体键盘映射由平台安装点提供，S3以Fake命令调用验收。

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/library/batch/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/library/batch/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `LIB_NOT_FOUND` | CORE-14 | ID 不存在或已物理删除：该条目列入 `skipped` |
| `LIB_META_INVALID` | CORE-14 | 标签为空串或超过 32 字符：整批拒绝，对话框内就地提示 |

**实现约束**
- 系统返回：多选模式下以 `PopScope(canPop: false)` 拦截，返回等同顶栏“取消”（退出多选、清空选择）；对照见 AND-13 表 e。
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 除长按与快捷键外，列表顶部提供可见的“选择”按钮进入选择模式（CORE-55 f：长按必须有可见按钮等价）；复选框点击区域取 `FmlDensity`；撤销提示条用 `showFmlToast`（10 s）。
- 选择模式下列表项左侧显示复选框，顶部显示选择工具栏：“已选 n 条”（`AllMatching` 为 `total − except.length`）、全选、取消，以及公式库页的“加/去标签”“移入回收站”或回收站页的“恢复”。
- 筛选或搜索条件变化时清空选择；滚动与分页懒加载不影响选择；`SelectedIds` 超过 10000 条时不再接受新增并提示改用筛选。
- 移入回收站后显示 10 s 撤销提示条，“撤销”或 Ctrl+Z 以 `appliedIds` 执行 `UntrashItems`；标签修改不提供撤销（可再次编辑）。
- 编辑标签对话框：两个标签输入框（“添加”“移除”），每个标签输入后成为一个标签块；确认前在本地校验长度，提交时调用一次 `library.batch`。
- `library.batch` 运行时显示进度与“取消”；运行期间列表只读；完成后调用 `LibraryVm.refresh`。
- 只经 CORE-38 `LibraryListDecorator` 修饰列表，不修改 CORE-38 页面；不判断运行平台。
- 组装：`installLibraryBatch` 追加到 CORE-36 `installers.dart` 的 `featureInstallers`；新增错误码 `LIB_BATCH_TOO_LARGE`、`LIB_BATCH_CANCELLED`（LIB_TAGS_LIMIT复用CORE-14） 先写入 `contracts/errors/registry.yaml`（CORE-02）。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
- 外部前提：只用 Flutter SDK 与已有 Rust 依赖；不新增第三方包。

**验收标准**
- [R11] Rust 单元测试：100 条测试库，`Query` 目标排除 3 条执行“加标签 期末” → `applied = 97`；其中已有 20 个标签的条目列入 `skipped`（`LIB_TAGS_LIMIT`）；已含该标签的条目计入 `unchanged`；每个有变化的条目恰好写入一条 outbox 记录。
- [R11] Rust 单元测试：处理到第 50 条时置位取消 → 返回 `LIB_BATCH_CANCELLED` 且数据库与 outbox 无变化；目标展开为 10001 条时返回 `LIB_BATCH_TOO_LARGE`；`Trash` 后 `search` 不再返回这些条目，`trashed = true` 时返回。
- [R11] Widget 测试（Fake CoreBinding 回放）：Fake分别invoke library.batch.toggle/extend.down/selectAll/clear及鼠标Ctrl/Shift单击的选中结果与选择规则一致；invoke trash后出现撤销提示条，invoke undo发出 `untrash` 且 ID 等于 `appliedIds`；invoke editTags打开编辑标签对话框；触控长按进入选择模式。
- [R11] Widget 测试：未登记 `LibraryListDecorator` 时列表无复选框、上述语义命令不可用；筛选变化后选择被清空。
- [R04] 集成测试（真实核心）：回收站页选中 5 条执行“恢复”，5 条回到公式库列表且修订历史不变。
- [R11] 性能：10000条加一标签按CORE-01“库批量写入”行，期间交互与滚动另按“列表滚动”行；由AND-12/WIN-13在S7分别测量，不以滚动FPS代替事务耗时，本卡只验事务/取消语义。
- [R42.b] Widget 测试：只点列表顶部“选择”按钮（不长按）即可进入选择模式；`touch` 下复选框点击区域 ≥ 48×48。

**规模**：约 460 行；用例/状态目录 `app/lib/library/batch/`（选择模型、BatchVm、修饰器与安装点，约 200）；`app/lib/ui/library/batch/`（选择工具栏、复选框与编辑标签对话框，约 130）；附属 `crates/fml-store/src/library/batch.rs` 与 FFI 处理函数 `crates/fml-ffi/src/ops/library_batch.rs`（约 130）。

