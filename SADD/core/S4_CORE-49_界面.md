### CORE-49 学习统计界面

**目标**：提供学习统计页与可复用统计图表/热力图。

**范围**
- 包含：日/周/月切换的学习量与时长曲线、日历热力图、连续天数、客观正确率与平均用时、章节完成率/掌握分布、复习积压/到期预测、易错公式榜及详情导航。
- 不包含：提醒设置与自建书编辑（CORE-90，下游说明，非契约）；统计/掌握度计算（CORE-20）；通知平台实现（AND-08、WIN-09，下游说明，非契约）；学习会话（CORE-39，下游说明，非契约）；学习首页（CORE-89，下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-20、CORE-36、CORE-37、CORE-38、CORE-55、CORE-58、CORE-28

**接口契约**

```dart
// app/lib/study_stats/routes.dart（页面在app/lib/ui/study_stats/，只收VM与deps.ui）
List<GoRoute> statsRoutes(AppDeps deps); // 仅 /study/stats

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
```

- Dart wire DTO由CORE-67按CORE-20领域schema生成到binding/dto：StatsReportDto、DayStatDto、MasteryDistributionDto；特性dto.dart只re-export或定义页面状态。
- 调用op：stats.report（CORE-20）；本卡不调用提醒设置或study.books写op。
- 组装：statsRoutes追加到composition/routes.dart，不新增Installer；独立提醒/书编辑路由由其所有者登记，本卡不导入其实现。共享登记由聚合维护者单写合入。

- 错误码与界面行为：

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `STUDY_STATS_RANGE_INVALID` | CORE-20 | 不应出现（时间窗由本卡计算）；出现即记 AppLog 并显示通用错误 |

Dart文件归属：VM/用例在app/lib/study_stats/；Widget、绘制与页面在app/lib/ui/study_stats/。Widget只接收状态/抽象与回调，不接收CoreBinding/HttpTransport，不从FeatureRegistry取裸绑定。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 统计图、掌握分布与热力图颜色只取 CORE-55 `FmlSemanticColors`（掌握度四色、`heat` 五档），切换主题色时不变；每档另有图例文字，不只靠颜色表意。
- 图表用 Flutter `CustomPaint` 自绘，不引入图表库；曲线与柱状图共用一个坐标轴组件；空数据显示“还没有学习记录”。
- 统计页正确率只显示客观判定（CORE-20 口径），标注“不含自评”；连续天数与积压直接取 `StatsReport`，界面不重算。
- 掌握分布四段（未学、学习中、已掌握、需巩固）用 CORE-55 `FmlSemanticColors` 的掌握度四色，与公式库掌握度标记一致；易错榜每行用 CORE-37 `MathText` 显示公式，点击跳转 `/library/:itemId`。
- 外部前提：无新增第三方库。
- 统计接口可被学习首页单向复用，不导入首页VM或自建书/提醒UI；BookDto/ChapterDto若需要必须从CORE-19领域schema的CORE-67生成DTO获取，不从学习UI定义。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-49_TEST.md](../Test/core/S4_CORE-49_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约515行，分阶段（Ⅰ 统计VM与共用坐标/曲线柱图约290行；Ⅱ 热力日历、统计页及接入约225行；各阶段可独立构建与测试）；app/lib/study_stats/、app/lib/ui/study_stats/中本卡统计实现及本卡编写的composition接入行；提醒/自建书编辑归CORE-90，不重复计；不计自测、夹具、DTO/schema数据与生成物。
