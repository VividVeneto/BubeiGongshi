### CORE-49 学习统计、提醒设置与自建书界面

**目标**：提供学习统计页、每日提醒设置页与自建公式书编辑界面。

**范围**
- 包含：统计页（日 / 周 / 月切换的学习量与时长曲线、日历热力图、连续天数、客观正确率与平均用时、章节完成率与掌握分布、复习积压、到期预测、易错公式榜，点击跳转 CORE-38 详情）；提醒设置页（开关、时刻、权限请求与被拒说明）；自建书编辑（新建、改名、删除；章节树增删、改名、排序，深度 ≤ 4；从公式库多选条目加入章节并设要求层级）。
- 不包含：统计与掌握度计算（CORE-20）；通知的平台实现（AND-08、WIN-09）；学习会话（CORE-39）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-14、CORE-19、CORE-20、CORE-23、CORE-36、CORE-37、CORE-39、CORE-55、CORE-58、CORE-28

**接口契约**

```dart
// app/lib/study_stats/routes.dart（页面在 app/lib/ui/study_stats/ 与 app/lib/ui/books/，只收 VM 与 deps.ui）
List<GoRoute> statsRoutes(AppDeps deps);   // /study/stats、/study/reminder、/study/books/new、/study/books/:bookId/edit

// app/lib/study_stats/stats_vm.dart
enum GranularityDto { day, week, month }   // 时间窗：day 近 30 天、week 近 26 周、month 近 12 个月（均 ≤ 366 天）
final class StatsVm extends ChangeNotifier {
  StatsVm(this._core, {String? bookId, int Function()? nowMs});
  GranularityDto get granularity; Future<void> setGranularity(GranularityDto g);
  StatsReportDto? get report; Object? get error;
  Future<void> refresh();                                   // stats.report
}
// app/lib/ui/study_stats/calendar_heatmap.dart
class CalendarHeatmap extends StatelessWidget {            // 近 26 周；5 档颜色（CORE-55 heat）按当日学习量（新学 + 复习）分档：0、1–9、10–29、30–59、≥ 60
  const CalendarHeatmap({super.key, required this.days, this.onTapDay});
  final List<DayStatDto> days; final void Function(String day)? onTapDay;
}

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

- Dart wire DTO（统一由CORE-67生成到`app/lib/binding/dto/`；特性dto.dart只允许re-export或页面状态）：`StatsReportDto`、`DayStatDto`、`MasteryDistributionDto`、`RequirementLevelDto`；`BookDto`、`ChapterDto` 复用 CORE-39。
- 调用的 op：`stats.report`（CORE-20）；`account.local_setting`（CORE-23，只读键 `device.reminder_time` 用于显示；写入只经 CORE-20 ReminderService）；`study.books.get / create / update / delete`（CORE-19）；`library.list`（CORE-14，条目多选）。
- 组装：`statsRoutes` 追加到 `app/lib/composition/routes.dart`；`ReminderService` 从 `ctx.features` 取（CORE-20 `installReminders` 注册）；本卡不新增 Installer。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
- 错误码与界面行为：

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `STUDY_STATS_RANGE_INVALID` | CORE-20 | 不应出现（时间窗由本卡计算）；出现即记 AppLog 并显示通用错误 |
| `STUDY_PLAN_INVALID` / `STUDY_BOOK_READ_ONLY` | CORE-19 | 自建书页显示错误；内容包书不显示编辑入口 |

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/study_stats/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/study_stats/` 与 `app/lib/ui/books/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `PLATFORM_PERMISSION_DENIED` | CORE-04 | 提醒开关回到关闭，显示“到系统设置开启通知”说明 |

ReminderSelfCheck结果读取CORE-20 ReminderCheckItem.state：ok显示正常，warn计入需处理项，unknown用中性信息样式、提供detail和可选设置入口但不标红。状态未知不等于配置错误。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 统计图、掌握分布与热力图颜色只取 CORE-55 `FmlSemanticColors`（掌握度四色、`heat` 五档），切换主题色时不变；每档另有图例文字，不只靠颜色表意。
- 提醒自检：提醒设置页在 `features.get<ReminderSelfCheck>()` 非空时显示“提醒不准时？检查设置”入口，进入后逐项列出 `ReminderCheckItem`（仅state=warn项标红，unknown显示中性信息，`canFix` 时显示“去设置”，返回前台后重新检查）；为空时不显示入口。
- 图表用 Flutter `CustomPaint` 自绘，不引入图表库；曲线与柱状图共用一个坐标轴组件；空数据显示“还没有学习记录”。
- 统计页正确率只显示客观判定（CORE-20 口径），标注“不含自评”；连续天数与积压直接取 `StatsReport`，界面不重算。
- 掌握分布四段（未学、学习中、已掌握、需巩固）用 CORE-55 `FmlSemanticColors` 的掌握度四色，与公式库掌握度标记一致；易错榜每行用 CORE-37 `MathText` 显示公式，点击跳转 `/library/:itemId`。
- 提醒：打开开关时先调用 `ReminderService.reschedule(at:)`，失败（权限被拒）则不写设置；默认时刻 20:00；正文只含待复习数量。
- 自建书：离开页面时 `dirty` 为真弹出“保存 / 放弃”；章节树操作在内存完成，保存时一次提交整本书。
- 外部前提：无新增第三方库。

**验收标准**
- [R04][R04.i] Widget 测试（Fake 核心）：预置 30 天 `StatsReport`，统计页显示连续天数、正确率、平均用时、章节完成率与积压；切到“周”后以 Dart `GranularityDto.week`（wire `"week"`）重新请求，跨度 ≤ 366 天。
- [R04][R04.i] 热力图分档：学习量 0、5、20、45、80 分别落入 5 档颜色。
- [R04][R04.i] 提醒：开启并选 21:30 后 `FakeNotificationScheduler` 记录 21:30 的提醒且 `device.reminder_time` 为 21:30；权限被拒时开关回到关闭、设置未写入。
- [R04][R04.j] 自建书：新建 3 章（含一个二级章）、加入 20 个条目后保存，`study.books.create` 收到的章节树与条目一致；第 5 层章节被拒；删除书后条目仍在公式库。
- [R04][R04.i] Widget 测试：登记返回两项（一项未通过且 `canFix`）的测试用 `ReminderSelfCheck` 时入口出现，点“去设置”调用 `openFix`；未登记时入口不出现。
- [R42.f] Widget 测试：切换 5 套预设主题后掌握分布四色与热力图五档颜色不变，均等于 `FmlSemanticColors` 对应值。

**规模**：约 450 行；用例/状态目录 `app/lib/study_stats/`；`app/lib/ui/study_stats/` 与 `app/lib/ui/books/`（同属 Flutter `app/` 构建单元）。

