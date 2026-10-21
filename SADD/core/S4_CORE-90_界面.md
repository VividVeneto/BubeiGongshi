### CORE-90 提醒设置与自建书编辑界面

**目标**：提供每日提醒设置、提醒自检与自建公式书编辑界面。

**范围**
- 包含：提醒开关/时刻/权限请求与被拒说明、ReminderSelfCheck展示与设置入口；自建书新建/改名/删除，章节树增删改名排序（深度≤4），公式库多选加入章节与要求层级、保存/放弃保护。
- 不包含：统计图表与页面（CORE-49，下游说明，非契约）；统计/提醒调度（CORE-20）；通知平台实现（AND-08、WIN-09，下游说明，非契约）；书架/计划设置（CORE-89，下游说明，非契约）；书存储（CORE-19）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-14、CORE-19、CORE-20、CORE-23、CORE-36、CORE-37、CORE-55、CORE-58、CORE-28、CORE-82

**接口契约**

```dart
// app/lib/study_stats/book_reminder_routes.dart（页面在app/lib/ui/study_stats/与app/lib/ui/books/）
List<GoRoute> bookReminderRoutes(AppDeps deps); // /study/reminder、/study/books/new、/study/books/:bookId/edit
// app/lib/study_stats/reminder_vm.dart
final class ReminderSettingsVm extends ChangeNotifier {
  ReminderSettingsVm(this._core, this._reminders);          // ReminderService 见 CORE-20
  bool get enabled; LocalTime? get at; String? get permissionMessageKey;
  Future<void> load();                                      // account.local_setting 读 device.reminder_time
  Future<void> setEnabled(bool on, {LocalTime? at});        // 开启调用 ReminderService.reschedule(at:)，关闭调用 cancel()；device.reminder_time 只由 ReminderService 写
}

// app/lib/study_stats/book_editor_vm.dart（页面在 app/lib/ui/books/）
final class BookEditorVm extends ChangeNotifier {
  BookEditorVm(this._core, {String? bookId});               // null = 新建
  BookDto get draft; bool get dirty; Map<String, String> get errors;
  void rename(String title);                                // 1–100 字符
  void addChapter(List<int> parentPath, String title);      // 深度 > 4 时记 errors['chapters']
  void renameChapter(List<int> path, String title);
  void moveChapter(List<int> path, int newIndex);
  void removeChapter(List<int> path);                       // 只移除引用
  void addItems(List<int> path, List<String> itemIds, RequirementLevelDto level);   // 重复引用忽略
  void removeItem(List<int> path, String itemId);
  Future<String?> save();                                   // study.books.create / update → id
  Future<bool> delete();                                    // study.books.delete；二次确认后调用
}
```

- ReminderSettingsVm、BookEditorVm只由本卡定义，保留既有文件位置和签名。BookDto、ChapterDto、RequirementLevelDto直接复用CORE-19等领域schema经CORE-67生成的DTO，不从CORE-39/CORE-89的UI导入wire模型。
- 调用op：account.local_setting（CORE-23，只读device.reminder_time）；study.books.get/create/update/delete（CORE-82）；library.list（CORE-14，条目多选）。提醒写入仅经CORE-20 ReminderService，本卡不另写device.reminder_time。
- 组装：bookReminderRoutes由聚合维护者追加到composition/routes.dart；静态/study/books/new在动态/study/books/:bookId之前登记。ReminderService取自features，由CORE-20 installReminders注册；本卡不新增Installer，不让统计/首页反向导入本卡。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `STUDY_PLAN_INVALID` / `STUDY_BOOK_READ_ONLY` | CORE-19 | 自建书页显示错误；内容包书不显示编辑入口 |
| `PLATFORM_PERMISSION_DENIED` | CORE-04 | 提醒开关回到关闭，显示“到系统设置开启通知”说明 |

ReminderSelfCheck结果读取CORE-20 ReminderCheckItem.state：ok显示正常，warn计入需处理项，unknown用中性信息样式、提供detail和可选设置入口但不标红。状态未知不等于配置错误。

Dart文件归属：VM/用例在app/lib/study_stats/；提醒Widget在app/lib/ui/study_stats/，书编辑Widget在app/lib/ui/books/。Widget只收VM/状态与回调，不接裸CoreBinding/HttpTransport。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 提醒自检：提醒设置页在 `features.get<ReminderSelfCheck>()` 非空时显示“提醒不准时？检查设置”入口，进入后逐项列出 `ReminderCheckItem`（仅state=warn项标红，unknown显示中性信息，`canFix` 时显示“去设置”，返回前台后重新检查）；为空时不显示入口。
- 提醒：打开开关时先调用 `ReminderService.reschedule(at:)`，失败（权限被拒）则不写设置；默认时刻 20:00；正文只含待复习数量。
- 自建书：离开页面时 `dirty` 为真弹出“保存 / 放弃”；章节树操作在内存完成，保存时一次提交整本书。
- 外部前提：无新增第三方库。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-90_TEST.md](../Test/core/S4_CORE-90_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约425行；app/lib/study_stats/中提醒/书编辑VM、app/lib/ui/study_stats/提醒页面、app/lib/ui/books/书编辑页面及本卡编写的路由/composition接入行（提醒155、书编辑260、接入10）；不计自测、夹具、配置/DTO/schema数据与生成物。
