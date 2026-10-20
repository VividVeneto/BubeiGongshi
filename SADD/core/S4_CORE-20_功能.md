### CORE-20 学习统计、掌握度与本地提醒

**目标**：从作答与复习事件派生学习统计与掌握度，并按到期数量安排每日本地提醒。

**范围**
- 包含：日/周/月学习量与时长、连续天数、客观正确率、平均用时、题型与章节掌握分布、章节完成率、复习积压、到期预测、易错公式榜；掌握度判据；统计缓存与全量重算；每日提醒用例。
- 不包含：统计界面（CORE-49）；通知的平台实现（AND-08、WIN-09）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-13、CORE-17、CORE-19

**接口契约**

```rust
// crates/fml-study/src/stats/mod.rs
// MasteryState 定义见 CORE-14（mastery_cache 表也在 CORE-14），本卡负责判定与写入
pub enum Granularity { Day, Week /* 周一起 */, Month }
pub struct StatsQuery { pub from_day: String /* YYYY-MM-DD，学习日 */, pub to_day: String /* 含，跨度 ≤ 366 天 */, pub book: Option<Uuid>, pub granularity: Granularity }
pub struct DayStat { pub day: String /* 区间首个学习日 */, pub new_learned: u32, pub reviewed: u32, pub duration_ms: u64,
                     pub objective_correct: u32, pub objective_total: u32 }
pub struct MasteryDistribution { pub not_learned: u32, pub learning: u32, pub mastered: u32, pub needs_reinforce: u32 }
pub struct StatsCache { pub schema: u32, pub generation: u64 /* 档案 stats_generation */, pub days: Vec<DayStat>, pub mastery: Vec<(FormulaItemId, MasteryState)> }   // 序列化后存 stats_cache
pub struct StatsReport { pub series: Vec<DayStat>, pub streak_days: u32, pub objective_accuracy: f32,
                         pub avg_duration_ms: u32, pub mastery_by_chapter: Vec<(String, MasteryDistribution)>,
                         pub chapter_completion: Vec<(String, f32)>, pub backlog: u32,
                         pub due_forecast: Vec<(String, u32)>, pub error_prone: Vec<FormulaItemId> }
pub fn mastery(attempts: &[Attempt], events: &[ReviewEvent], n_required: u8 /* 默认 3 */) -> MasteryState;
pub struct StatsInput { pub books: Vec<Book>, pub cards: Vec<CardSchedule>, pub plans: Vec<StudyPlan>,
 pub today: String, pub study_day: StudyDay, pub now_ms: i64 }
pub fn compute(q: &StatsQuery, attempts: &[Attempt], events: &[ReviewEvent], input: &StatsInput) -> StatsReport;  // 全量
pub fn invalidate(cache: &mut Option<StatsCache>); // 不按事件序号截断，失效后全量重算
```

```dart
// app/lib/study/reminder_service.dart
class ReminderService {
  ReminderService(this._scheduler, this._core);   // NotificationScheduler 见 CORE-04
  Future<void> reschedule({required LocalTime at}); // 先成功申请权限/安排，再写设置
  Future<void> resume(); // 从已有device.reminder_time恢复，缺失则取消
  Future<void> cancel(); // 取消并将device.reminder_time置null // 正文只含待复习数量，不含公式内容
  // 内部调用 FFI op stats.due_count（→ {"due": u32}）取数量；due = 0 时取消当日提醒；正文消息键 reminder.body（参数 n）
}

// 提醒可靠性自检：平台卡（AND-08）可经 PlatformPorts.platformInstallers 登记实现；未登记的平台（Windows）不显示自检入口
final class ReminderCheckItem {
  const ReminderCheckItem({required this.id, required this.state, required this.title, this.detail, required this.canFix});
  final String id;          // 平台自定，如 'permission'、'battery_optimization'
  final ReminderCheckState state; final String title; final String? detail;   // 文案由平台实现给出（简体中文）
  final bool canFix;        // true 时界面显示“去设置”
}
abstract interface class ReminderSelfCheck {
  Future<List<ReminderCheckItem>> run();
  Future<void> openFix(String id);   // 打开对应系统设置页；返回后界面重新 run()
}
```

- 掌握判据：跨 ≥ 2 个学习日、间隔 ≥ 1 天、连续 N 次（默认 3）客观判对且最近一次默写正确（`Attempt.dictation = true` 的最近一条 verdict 为 Correct；从未默写视为不满足）→ Mastered；之后任一次判错 → NeedsReinforce；自评结果不能单独使公式进入 Mastered。
- FFI op：`stats.report`（`{query: StatsQuery, now_ms}` → StatsReport）、`stats.mastery`（`{item_ids}` → `[[id, state]]`）、`stats.rebuild_cache`（长任务，`{now_ms}`）、`stats.due_count`（`{now_ms}` → `{due}`）。
- 指标口径：连续天数 = 截至今天（今天未学则截至昨天）连续有 ≥ 1 次有效作答的学习日数；章节完成率 = 章节内 Mastered 条目 ÷ 章节唯一条目数（细则与向量 STATS-X1 见下）；复习积压 = 到期未复习的卡数；到期预测为未来 14 个学习日每日到期数；易错榜取最近 30 天客观错误次数前 20 的条目。
- 表（本卡 `migrations/0020_stats.sql`）：`stats_cache`（`book_key TEXT PK`（书 ID 或 `all`），`cache_json TEXT NOT NULL`，`updated_at_ms INTEGER NOT NULL`）；本地缓存，不进 outbox。
- 错误码（本卡唯一定义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `STUDY_STATS_RANGE_INVALID` | error | 否 | 日期格式错误、from_day > to_day、跨度超过 366 天或 today 与 StudyDay 不一致 |

复用 CORE-04 `PLATFORM_PERMISSION_DENIED`：提醒权限拒绝时保持关闭并提示系统设置。

缓存只采用全量重算策略：档案 local_setting 键 stats_generation 是 u64 字符串，初始0；任一 attempt/review_event/study_card/book/study_plan 的本地或远端变更同事务 +1；读取 cache.generation≠当前值、查询范围/学习日/时区/schema 改变时丢缓存，读取同一快照全部输入重算，发布结果附该快照 generation。在计算期间新写入则下次读再次失效，不能把旧报告标成新水位；不再使用 through_event_seq。

compute所需输入为StatsQuery、完整Attempts/ReviewEvents及StatsInput；处理层在同一数据库快照读取书章节、卡片到期/状态、计划、StudyDay；now_ms 由 Dart 用例在调用边界取一次 UTC 毫秒，经请求体 `now_ms` 传入（CORE-01 时间注入规则），处理层据此计算 today，不读系统时钟。today必须等于study_day覆盖now_ms的日期，不一致返回处理层STUDY_STATS_RANGE_INVALID，不偷偷读系统时钟。章节完成率分母=过滤后章节唯一条目数，分子=Mastered条目数，空章节为0；积压=未挂起且due_ms≤now的唯一卡数；预测按卡due_ms所属学习日计数，跨天再分桶；连续天数从today（今天未学习则从昨日）逐日回溯至少一条有效学习事件的天数，自评/突击是否计时沿用本卡既有规则。

| 向量 | 输入 | 期望 |
| --- | --- | --- |
| STATS-X1 | 一章2条目，仅1条Mastered；2张卡due=now-1/now+1 | 完成率0.5，backlog=1，今日预测含前者 |
| STATS-X2 | StudyDay04:00，today=10-20，事件10-20 03:59与04:00 | 分到10-19与10-20，streak_days=2 |


ReminderService.reschedule(at:)先成功申请权限并重排，再写device.reminder_time（HH:MM，syncable=0），失败保留原设置；resume()读取该键，有值则重排、None则取消；cancel()取消并写null。None不启用通知（界面默认展示20:00但需用户开启）。预测偏差口径：最近30×24h内非self_rated/非skipped的首个每日复习，按复习前memory state与elapsed_days算预测回忆概率p，actual=rating!=Again；样本≥200且abs(mean(p)-mean(actual))>0.05才建议回退；不自动回退。stats.calibration body={now_ms}，ok={samples,mean_predicted?,mean_observed?,suggest_rollback}，不足样本两均值省略、false；call。输入来自同一快照的历史重放，不用复习后状态预测自身。

ReminderCheckState为本卡公共枚举{ok,warn,unknown}（Dart同名；通道wire为ok/warn/unknown）；可确定正常=ok，可确定问题=warn，不可检测=unknown。CORE-49（下游说明，非契约）按正常/警示/中性信息图标显示，unknown不计入问题数；不再用bool ok制造红项。

**实现约束**
- 安装点：`app/lib/study/install.dart` 的 `installReminders(CompositionContext ctx)` 登记 `ReminderService` 并以 order 80 登记“提醒重排”启动钩子；在 CORE-36 `installers.dart` 的 `featureInstallers` 追加一行。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
- 重排时机：启动钩子、应用每次进入后台（`installReminders` 订阅 `ports.lifecycle.events()` 的 `paused`，与上次重排间隔 ≥ 1 分钟）与提醒时刻修改后各一次，因此学完一组后退出即按新的到期数安排；应用长期未打开时平台按 AND-08、WIN-09 的规则沿用上次正文。
- 正确率只计客观判定，自评与 Undetermined 不计。掌握度与统计缓存不同步，各端从同步后的事件重算。
- 提醒：每日一次，本地调度，不依赖网络；不做组队打卡。
- 最近 30 天有效复习 ≥ 200 次时，若预测回忆率与实际回忆率之差超过 5 个百分点，提示用户回退个性化参数（调用 CORE-17 `srs.rollback_params`）。

**验收标准**
- [R04][R04.i] T-STATS：随机生成 1000 组事件序列，命中缓存的结果与丢弃缓存后全量重算的结果 100% 一致；同步合并、卡片重置、学习日边界与时区变更后统计正确；自评不计入正确率。
- [R04][R04.d][R04.i] 掌握判据单元测试：仅自评达标不进入 Mastered；跨日与间隔不足不进入 Mastered；判错转 NeedsReinforce。
- [R04][R04.i] 提醒：`resume()` 调用 Fake `NotificationScheduler` 时正文只含数量，到期为 0 时不安排；游客与注册用户行为一致且不发网络请求。
- [R04] 学习效果试点（手动，M3 前）：≥ 30 名目标用户连续 ≥ 30 天，记录 7 天与 30 天保留率（目标 ≥ 80% 与 ≥ 70%）、Undetermined 比例（≤ 5%）与申诉改判比例（≤ 1%）；未达标须调整组大小、K 或评分映射后复测，结果写入附录 A 评审记录。

- [R04.i] 先缓存设备A seq=100，再同步设备B seq=1 且 at_ms更早的事件，下一次统计必须失效并重算计入B；重复拉取B不再增加数量。

- [R04] calibration 199/200样本、偏差0.05/0.0501边界符合规则；at写入后重启读取相同时刻，None不调schedule。

**规模**：约 450 行；主包 `crates/fml-study/src/stats/`（约 380 行，另含迁移 `0020_stats.sql`），附属：跨语言另一侧 `app/lib/study/reminder_service.dart`（约 70 行）。

---

