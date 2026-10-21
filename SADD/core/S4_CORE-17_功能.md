### CORE-17 FSRS排程、复习事件与参数仓储

**目标**：封装确定性FSRS排程、追加式复习事件、卡片与参数仓储；生成与优化算法由CORE-80/81单向调用。

**范围**
- 包含：Card等基础类型、study_card/review_event/srs_params仓储、FSRS确定性重放、同胞隐藏、积压平滑、学习日、修订保持/重建、参数采用/回退事务。
- 不包含：组学习循环（CORE-19）；判分（CORE-18）；统计（CORE-20）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-09、CORE-13、CORE-14

**接口契约**

```rust
// crates/fml-srs/src/lib.rs
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)] #[serde(rename_all = "snake_case")]
pub enum CardType { NameToFormula, FormulaToName, SymbolCloze, VariableMeaning, UnitDimension, SimpleNumeric,
                    ConditionRecall, ConfusableChoice, DerivationOrder, ContextChoice }
pub enum CardState { New, Learning, Review, Relearning, Suspended, Buried }
pub struct Card { pub id: Uuid, pub item: FormulaItemId, pub revision: RevisionId, pub card_type: CardType,
                  pub siblings_key: FormulaItemId, pub reset_epoch: u32 /* 仓储当前epoch，新卡0 */, pub state: CardState, pub due_ms: Option<i64>,
                  pub pending_choice: bool /* 修订变化待选择，新卡 false */ }
pub enum Rating { Again, Hard, Good, Easy }
pub struct ReviewEvent { pub id: Uuid, pub card: Uuid, pub rating: Rating, pub source_attempt: Uuid,
                         pub algo_version: String, pub params_version: u32, pub rating_map_version: u32,
                         pub reset_epoch: u32, pub device_id: Uuid, pub device_seq: u64, pub tx_index: u16 /* 同事务内0起，配合CORE-13序号 */, pub at_ms: i64,
                         pub flags: EventFlags /* self_rated | cram | skipped | correction_of；写入后不可变 */ }
pub struct EventFlags { pub self_rated: bool, pub cram: bool, pub skipped: bool,
                        pub correction_of: Option<Uuid> /* 被改判的事件 ID（CORE-19 申诉） */ }
pub enum RequirementLevel { Liaojie, Lijie, Zhangwo, Huiyong }   // 了解、理解、掌握、会用（CORE-16 字段同名）
pub struct FsrsParams { pub weights: Vec<f32> /* 长度与锁定的 fsrs crate 一致，默认取该 crate 默认值 */,
                        pub desired_retention: f32 /* 0.80–0.95，默认 0.90 */, pub version: u32 /* 0 = 默认参数 */ }
pub struct CardSchedule { pub card: Card, pub stability: f32, pub difficulty: f32, pub due_ms: Option<i64>,
                          pub last_review_ms: Option<i64>, pub reps: u32, pub lapses: u32, pub overdue_days: i32,
                          pub duplicate_events: Vec<Uuid> /* 重放派生：同卡同学习日非首条事件 ID，不回写事件 */ }
pub struct DailyCaps { pub new_limit: u32 /* 默认 10 */, pub review_limit: u32 /* 默认 200 */, pub backlog_threshold: u32 /* 默认 = review_limit */ }
pub struct DueQueue { pub reviews: Vec<Uuid>, pub new_cards: Vec<Uuid>, pub hidden_siblings: Vec<Uuid>,
                      pub new_limit_effective: u32 /* 积压降级后的新学上限 */, pub backlog: u32,
                      pub pending_choice: Vec<Uuid> /* 待选择“保持/重建”的卡，不入 reviews/new_cards */ }
pub fn replay(card: &Card, events: &[ReviewEvent], params: &FsrsParams, now_ms: i64, day: &StudyDay) -> CardSchedule; // 纯函数，确定性
pub fn due_queue(cards: &[CardSchedule], day: &StudyDay, caps: &DailyCaps, now_ms: i64) -> DueQueue;     // 复习优先，同胞卡同日最多一张
pub struct StudyDay { pub switch_hour: u8 /* 0..=23，默认 4 */, pub tz: String /* IANA 时区名 */ }
impl StudyDay {
    pub fn validate(&self) -> Result<(), FmlError>;      // switch_hour > 23 或 tz 不在内置时区库 → STUDY_DAY_INVALID
    pub fn day_start_ms(&self, at_ms: i64) -> i64;       // at_ms 所在学习日起点（UTC 毫秒），规则见“学习日”
}
pub struct ParamsState { pub current: FsrsParams, pub has_previous: bool, pub last_optimized_ms: Option<i64> }
```

- FFI op（DTO按CORE-03，profile scope）：

| op | 方式 | 请求体 → 响应 | 说明 |
| --- | --- | --- | --- |
| `srs.due_queue` | submit | `{now_ms, day, caps, desired_retention}` → DueQueue | 先在一个写事务内执行“修订变化”标记，再读全部卡排程计算队列；无 plan_id |
| `srs.record_event` | submit | `{event, day, desired_retention, now_ms}` → CardSchedule | 同一写事务插入事件、按该卡当前 reset_epoch 的全部事件重放并更新缓存列；卡 pending_choice = 1 时报 STUDY_CARD_PENDING_CHOICE 且不写 |
| `srs.reset_card` | submit | `{card_id}` → `{reset_epoch}` | reset_epoch + 1，缓存列置为新卡 |
| `srs.suspend` | submit | `{card_id, suspended}` → `{}` | 只改 suspended |
| `srs.rollback_params` | submit | `{}` → FsrsParams | 规则见“参数表” |
| `srs.resolve_revision_change` | submit | `{card_id, choice}`（choice 为 keep 或 rebuild）→ Card | 规则见“修订变化” |

  srs.generate 唯一迁 CORE-80，srs.optimize 唯一迁 CORE-81。`day` 先经 `StudyDay::validate`；`desired_retention` 取调用方学习计划的目标保留率（CORE-19 StudyPlan.target_retention，下游说明，非契约），不在 [0.80, 0.95] 报 STUDY_RETENTION_OUT_OF_RANGE；处理层以“srs_params 当前权重 + 请求的 desired_retention + 当前 version”组成 FsrsParams。
- 评分由调用方的映射策略产生，`rating_map_version` 的唯一来源是 CORE-19 `RatingMap.version`（下游说明，非契约；初值 1）；本卡只接收 `Rating` 与该版本号原样存储，不做映射，只校验 ≥ 1（否则 FFI_BAD_ARG）。
- 表（本卡 `migrations/0017_srs.sql`）：

| 表 | 主要列（类型，约束） | 索引 |
| --- | --- | --- |
| `study_card` | `id TEXT PK`，`item_id TEXT NOT NULL`，`revision_id TEXT NOT NULL`，`card_type TEXT NOT NULL`，`siblings_key TEXT NOT NULL`，`suspended INTEGER NOT NULL`，`pending_choice INTEGER NOT NULL`（修订变化待选择），`reset_epoch INTEGER NOT NULL`，`created_at_ms`；派生列 `state TEXT`、`due_ms INTEGER` 为本地缓存，可由事件重算 | `(due_ms)`，`(siblings_key)`，`(revision_id)` |
| `srs_params` | `version INTEGER PK`（≥ 1，按采用次序递增），`weights_json TEXT NOT NULL`（f32 数组，长度与锁定 fsrs 默认参数一致），`previous_version INTEGER NOT NULL`（0 = 默认参数），`is_current INTEGER NOT NULL`，`adopted_ms INTEGER NOT NULL`，`optimized_ms INTEGER NOT NULL`（触发采用的优化时刻） | `UNIQUE(is_current) WHERE is_current = 1` |
| `review_event` | `id TEXT PK`，`card_id TEXT NOT NULL`，`rating TEXT NOT NULL`，`source_attempt TEXT NOT NULL`，`algo_version TEXT NOT NULL`，`params_version INTEGER NOT NULL`，`rating_map_version INTEGER NOT NULL`，`reset_epoch INTEGER NOT NULL`，`device_id TEXT NOT NULL`，`device_seq INTEGER NOT NULL`，`tx_index INTEGER NOT NULL`，`at_ms INTEGER NOT NULL`，`flags_json TEXT NOT NULL`；只插入不更新（id唯一；三元仅重放索引，整库回退后的不同事件可能同三元） | `(card_id, at_ms)`，`(device_id, device_seq, tx_index)` 非唯一 |

- 重放顺序：按 `(at_ms, device_id, device_seq, tx_index)` 升序；只取`event.reset_epoch == card.reset_epoch`的事件，不从事件max推导当前epoch；重放派生为重复的事件与 `skipped` 事件不进入调度；`correction_of` 事件替换被改判事件的评分。
- 错误码（本卡唯一定义；级别与可重试为本次补全，待所有者确认）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `STUDY_CARD_NOT_FOUND` | error | 否 | 卡片 ID 不存在 |
| `STUDY_RETENTION_OUT_OF_RANGE` | error | 否 | 目标保留率不在 [0.80, 0.95] |
| `STUDY_CARD_PENDING_CHOICE` | warning | 否 | 对待选择“保持/重建”的卡片记录事件，或对未处于待选择的卡调用 `srs.resolve_revision_change` |
| `STUDY_PARAMS_VERSION_STALE` | error | 否 | `adopt_params` 的 expected_version 不等于当前参数 version（优化期间参数已被采用或回退；调用方重新优化） |
| `STUDY_PARAMS_NO_PREVIOUS` | error | 否 | `rollback_params` 时当前已是默认参数（无 is_current 行） |
| `STUDY_DAY_INVALID` | error | 否 | `StudyDay.switch_hour` > 23 或 `tz` 不是内置时区库中的 IANA 名（args.field 为 `switch_hour` 或 `tz`） |

FSRS 样例（crates/fml-srs/tests/fixtures/fs.yaml）：仅 stability/difficulty/next_states 的算法输出直接取 fsrs=6.6.2；CardState/due_ms/lapses 用本卡显式状态表的独立参照组合，不能宣称 fsrs 自带学习状态机；默认 weights 与 API 固定见 ADR-V5-29。

| 编号 | 事件序列（学习日） | 期望 |
| --- | --- | --- |
| FS-01 | 新卡 Good（第 0 天） | 状态离开 New，`due_ms` 晚于事件时刻 |
| FS-02 | Good、Good、Good（每次在到期日） | 间隔均为正，memory_state与锁定API逐字段一致，不假定任意参数严格增大 |
| FS-03 | Good、Good、Again（每次在到期日） | 状态为 Relearning，`lapses = 1` |
| FS-04 | 同一学习日两条 Good | 第二条列入 `CardSchedule.duplicate_events`，排程与只有一条时相同 |
| FS-05 | FS-02 的事件乱序到达 | 排程与 FS-02 相同 |
| FS-06 | Good、重置、Good | 只计重置后的事件，与 FS-01 结果相同 |
| FS-07 | Again 后经 `correction_of` 改判为 Good | 与直接 Good 结果相同，原事件保留 |
| FS-08 | 自评兜底事件 Good | 参与调度，但不进入 `optimize_params` 的训练集 |

- 每个业务写命令必须使用 CORE-13 Store.write/enqueue_outbox，显式 changed_fields；不得自行分配 Lamport 或直接写 outbox。重放与缓存更新不当成用户编辑。

所需输入：revision+enabled_types+requirement_level 决定出卡，Card.id调用 CORE-05 card_id；replay 需初始卡、完整事件、参数、now_ms、StudyDay；due_queue 需全部卡排程、caps、now_ms、StudyDay。时间差由相邻有效 at_ms 算，不由事件到达时间算；未来事件不参与 now_ms 前的重放。同学习日重复标记只在重放结果中派生，不回写不可变事件。

学习状态包装表（见 README §6 Q34（已确认））：同卡同学习日只接受首个完成事件；学习/重学仅一个跨学习日步长，不做分钟内重复；day_start 是传入 StudyDay 对 next日期计算的 UTC 边界。

| 当前 | Again / Hard | Good | Easy |
| --- | --- | --- | --- |
| New | Learning，下一学习日起点 | Learning，下一学习日起点 | Review，用next_states.easy.interval |
| Learning | Learning，下一学习日起点 | Review，用next_states.good.interval | Review，用next_states.easy.interval |
| Review | Again→Relearning且lapses+1；Hard→Review用hard.interval | Review，用good.interval | Review，用easy.interval |
| Relearning | Relearning，下一学习日起点 | Review，用good.interval | Review，用easy.interval |
| Suspended / Buried | 不调度 | 不调度 | 不调度 |

FSRS 构造从 params.weights 注入；首次 next_states(None, retention,0)，后续传上一 memory state 与 floor((事件时刻-上次有效事件时刻)/86400000) 的非负 elapsed_days。interval单位天，取 round（0.5向上）且至少1天后加到事件时刻；Learning/Relearning 的上述 next_day 覆盖间隔但保留 FSRS 新记忆状态。Review Again 即使记忆库建议长间隔也按重学规则覆盖。只到期的 due_ms≤now_ms 入队，overdue_days=floor(max(0,now_ms-due_ms)/86400000)。不以 due_queue day 代替 now。

| 向量 | 输入 | 期望 |
| --- | --- | --- |
| FS-X1 | due_ms=1000/1001，now_ms=1000，均Review，无同胞 | 只含due=1000；overdue_days=0 |
| FS-X2 | New 卡于同学习日先Good后Again，day切换04:00 | 第二事件派生duplicate；次日04:00到期Learning，lapses=0 |

官方 API：[fsrs 6.6.2](https://docs.rs/fsrs/6.6.2/fsrs/struct.FSRS.html)、[依赖](https://docs.rs/crate/fsrs/6.6.2)、[rs-fsrs 1.2.1 Scheduler对照](https://docs.rs/rs-fsrs/1.2.1/rs_fsrs/struct.Scheduler.html)。

参数表：当前参数 = is_current = 1 的行；无此行时为默认参数（weights 取锁定 fsrs 默认值，version = 0）。`adopt_params` 在单写者事务中校验 expected_version 等于当前 version（否则 STUDY_PARAMS_VERSION_STALE，不写），插入 version = max(version)+1、previous_version = 当前 version、is_current = 1 的行并清除旧行 is_current；`rollback_params` 把当前行 is_current 清零，并把 previous_version 对应行（> 0 时）置为当前，返回新的当前参数；当前已是默认参数报 STUDY_PARAMS_NO_PREVIOUS。行只追加不删除。`params_state(store)` 返回当前参数、has_previous（存在当前行）与 last_optimized_ms = 全部行 optimized_ms 的最大值（回退不撤销月限额；无行为 None），供 CORE-81 计算月限额。desired_retention 不存于本表，见 op 表说明。参数只在本机（ADR-V5-54），同一事件集在两端重放一致以两端参数相同为前提；参数不同时两端各自按本机参数重算缓存，事件仍为唯一权威（R28）。

修订变化：条目 `formula_item.head`（CORE-14）不等于卡片 `revision_id`，且 head 修订的 validation 为 Verified 或 VerifiedPolymorphic 时，该卡视为待选择；head 未通过校验时卡片继续按原修订排程。标记由 `mark_revision_changes` 在一个写事务内完成（`srs.due_queue` 处理开始时调用）：对上述卡置 pending_choice = 1（changed_fields 只含 pending_choice，经 CORE-13 写命令），已置位者不重复写；同步合并或其他设备产生的新 head 也在下一次 due_queue 被发现，CORE-14 不反向调用本卡。待选择卡列入 `DueQueue.pending_choice`，不进入 reviews/new_cards，也不参与同胞隐藏。`resolve_revision_change`：keep → revision_id 改为当前 head、pending_choice = 0，事件与 reset_epoch 不变；rebuild → revision_id 改为当前 head、pending_choice = 0、reset_epoch + 1（等同重置）；card.id 与 card_type 不变（ID 只在生成时由 CORE-05 card_id 决定）。卡不处于待选择时报 STUDY_CARD_PENDING_CHOICE 且不写。界面入口与文案属调用方（下游说明，非契约）。

学习日：`day_start_ms(at)` 取 at 在 tz 下的本地时间减去 switch_hour 小时后所得本地日期 D，返回 D 当天本地 switch_hour:00 对应的 UTC 毫秒；该本地时刻因夏令时不存在时取间隙后第一个有效时刻，重复时取较早一次。“下一学习日起点”是 day_start_ms(at) 之后的下一个学习日起点（夏令时切换日的学习日可为 23 或 25 小时，按本地日期计，不按 86 400 000 ms 平移）。同学习日判定比较 day_start_ms。时钟异常：at_ms 晚于 now_ms 的事件本次不重放、不改写、不报错，now_ms 追上后自然计入；事件到达先后不影响结果（按排序键重放）。

积压与新学：backlog = due_ms ≤ now_ms 且未暂停、未搁置、未待选择的复习卡数（同胞隐藏前）。reviews 按 overdue_days 降序、due_ms 升序、id 升序排序后做同胞隐藏，取前 review_limit 张；其余仍到期，留到后续学习日（自然分摊，不改写 due_ms）。新学上限：backlog ≤ backlog_threshold 时 new_limit_effective = min(new_limit, review_limit)；backlog > backlog_threshold 时 new_limit_effective = floor(new_limit × max(0, 2·backlog_threshold − backlog) ÷ backlog_threshold)，backlog ≥ 2·backlog_threshold 时为 0（暂停新学）；backlog_threshold = 0 时按 1 计。new_cards 取 state = New 的卡按 created_at_ms、id 升序，同胞隐藏后取前 new_limit_effective 张。

**本卡实体 codec/applier（CORE-13 接缝）**

- study_card、review_event 的 codec/applier 位于 fml-store/src/study/cards.rs；srs_params 为本地参数，不注册同步实体。study_card 只同步权威字段（绑定修订/类型/同胞键/suspended/pending_choice/reset_epoch/created_at_ms），不把 state/due_ms/stability 等缓存上传；事件完整不可变，时钟仅 __entity。枚举按ID UTF-8稳定顺序，只列存活权威行；Delete 仍分派原类型。
- applier 仅使用传入 WriteTx/ApplyContext：同事件ID同权威值 Duplicate，异值 Invalid；新事件追加后以当前 card.reset_epoch 的完整事件调用本卡 replay，按既有顺序和 now_ms/StudyDay 输入重建排程。时间/学习日上下文由调用方既有运行时上下文提供，不在纯crate读时钟；不在无上下文时伪造 now=0 缓存（只标失效，读取端按当前参数重算）。card reset_epoch 按字段时钟决胜，不取事件max。
- study_card 字段按CORE13时钟合并，派生state/due只重算不当用户编辑；删除保留墓碑且不物理改写不可变事件。所有远端路径不调用 stamp/enqueue、不重写ReviewEvent原device信息，stats_generation失效hook唯一归CORE-20。S4测试注入Fake分派，S6只集成，不反向依赖26。

**实现约束**
- 参数写入/回退唯一归本卡；`srs_params` 列见表，本卡0017_srs.sql同时定义数据DDL，不迁给优化算法卡。目标保留率[0.80,0.95]，默认0.90，随请求传入不入表。
- 低层仓储接缝由本卡拥有：`insert_generated(tx: &mut WriteTx, cards: &[Card]) -> Result<(), FmlError>`仅插入新卡；`adopt_params(store: &Store, params: &FsrsParams, expected_version: u32, optimized_ms: i64) -> Result<(), FmlError>`在单写者事务校验版本、保存上一版本并采用，更新月优化标记；`rollback_params(store: &Store) -> Result<FsrsParams, FmlError>`恢复上一参数版本；`params_state(store: &Store) -> Result<ParamsState, FmlError>`只读当前参数与月限额依据；`mark_revision_changes(store: &Store) -> Result<Vec<Uuid>, FmlError>`执行“修订变化”标记并返回当前全部待选择卡 ID（srs.due_queue 处理与组学习开课前调用，下游说明，非契约）；`load_params_tx(tx: &WriteTx) -> Result<FsrsParams, FmlError>`在调用方写事务内只读当前采用的参数（无行时返回默认参数，供 CORE-84（下游说明，非契约）恢复重放与同事务重算使用，不写入）。均遵循CORE-13写命令/changed_fields/outbox规则，本卡不调用CORE-80/81。
- 使用 crates.io fsrs=6.6.2（ADR-V5-29）；只调用 `FSRS::new(&[f32])`（空切片为默认参数）、`FSRS::next_states`、`FSRS::memory_state`、自由函数 `fsrs::compute_parameters(ComputeParametersInput)` 与 `FSRS::evaluate`（留出集 log-loss）。该版本正常依赖为 itertools、log、ndarray、priority-queue、rand、rayon、serde、snafu、strum，burn 只是开发依赖；仍须在真实产物过包体门禁；不引入 rs-fsrs 的另套状态机。
- 复习事件追加不可变；卡片状态只由事件重算，不直接合并状态；重置生成新 `reset_epoch`。
- 同卡同学习日多条事件只取先完成的一次，其余在重放结果 `duplicate_events` 中列出；事件原样保留供审计，不改写。
- 新学上限不超过当日复习上限；积压时按“积压与新学”公式降低新学直至暂停，未进入当日队列的复习按逾期程度排在后续学习日。
- 学习日按计划的切换时刻（默认 04:00）与时区计算，规则见“学习日”；时钟异常的事件不改写。
- 公式修订变化时，卡片按“修订变化”暂停到用户选择“保持进度”或“重建”。
- 外部前提：时区规则使用 crates.io `jiff` 并启用内置 tzdb（`tzdb-bundle-always`，编译期嵌入，运行时不读系统时区文件，满足领域 crate 无 I/O）；版本与内置 tzdb 版本按 CORE-01 开工规则在本卡编码会话锁定并回填 ADR-V5-15，未锁定前不能报告通过；须过包体门禁。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-17_TEST.md](../Test/core/S4_CORE-17_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约575行；主包`crates/fml-srs/`，附属`crates/fml-store/src/study/cards.rs`、`params.rs`与`crates/fml-ffi/src/ops/srs.rs`本卡op处理/登记。分阶段：① 纯排程/重放/队列/学习日/积压405行；② 卡片/事件/参数写入及回退、修订变化标记、codec/applier与 6 个 op 适配170行；依赖替身分别独立构建验证。DDL/自测与CORE-80/81实现不计。
