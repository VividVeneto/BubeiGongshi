### CORE-19 学习会话与组学习循环

**目标**：实现“以不背单词为原型、功能近似”的背诵闭环：选书定计划、分组多轮、错题重现、组后默写、客观结果映射评分、跳过暂停与改判。

**范围**
- 包含：`Book`、`StudyPlan`、`StudySession`、`Attempt` 实体与仓储；组循环状态机（sans-I/O）；出题（含干扰项与易混组）；评分映射；续学；多设备同组；“记错了”申诉。
- 不包含：卡片排程（CORE-17）；判分（CORE-18）；统计（CORE-20）；界面（CORE-39）。不做组队打卡与社交功能。

**依赖**：CORE-01、CORE-02、CORE-13、CORE-14、CORE-17、CORE-18、CORE-16

**接口契约**

```rust
// crates/fml-study/src/lib.rs
pub enum BookSource { Pack { pack_id: String, book_key: String }, User }
pub struct Chapter { pub key: String, pub title: String, pub children: Vec<Chapter>,
                     pub items: Vec<(FormulaItemId, RequirementLevel)> }   // 深度 ≤ 4；用户书只引用条目 ID
pub struct Book { pub id: Uuid, pub title: String /* 1–100 字符 */, pub source: BookSource, pub chapters: Vec<Chapter> }
pub struct StudyPlan { pub book: Uuid, pub daily_new: u16 /* 默认 10 */, pub daily_review_cap: u16,
                       pub group_size: u8 /* 默认 10 */, pub k_new: u8 /* 默认 3，1..=5 */, pub k_review: u8 /* 默认 1 */,
                       pub target_retention: f32, pub enabled_types: Vec<CardType>, pub day: StudyDay,
                       pub exam_date: Option<String> /* YYYY-MM-DD */, pub exam_subject: Option<String> /* shu1|shu2|shu3，同 CORE-16 */ }
// daily_new 0..=200；daily_review_cap 10..=2000（默认 200）；group_size 5..=30；k_review 1..=3；target_retention 0.80..=0.95（默认 0.90）
pub enum SessionKind { New, Review, Dictation, Mistakes, Cram }   // Cram 事件带 cram 标记，不进参数优化
pub enum AnswerMode { Choice, Input, Handwriting, SelfRate }
pub struct QuestionDto { pub card: Uuid, pub card_type: CardType, pub prompt_latex: Option<String>, pub prompt_text: Option<String>,
                         pub options: Vec<String> /* 选择题选项 LaTeX，2–6 个；其他题型为空 */, pub answer_mode: AnswerMode,
                         pub expected: GradeTarget /* 不下发到界面展示，只用于判分 */, pub required_form: Option<RequiredForm>, pub seed: u64 }
pub struct QuestionSource { pub revision: FormulaRevision, pub distractors: Vec<Distractor>, pub confusable: Vec<FormulaRevision>, pub reviewed_by: String, pub reviewed_at_ms: i64 }
pub struct Distractor { pub reviewed_by: String, pub reviewed_at: String, pub latex: String, pub error_type: String /* 漏系数|正负号|指数|分子分母颠倒|量纲不一致，同 CORE-16 */ }
pub struct RatingMap { pub version: u32 /* 初值 1 */, pub easy_ratio: f32 /* 0.5 */, pub easy_min_samples: u8 /* 10 */, pub easy_window: u8 /* 30 */ }
pub struct GroupSummary { pub cards: u32, pub first_try_correct: u32, pub reappeared: u32, pub dictation_wrong: Vec<Uuid>, pub duration_ms: u64 }
pub struct Attempt { pub id: Uuid, pub card: Uuid, pub card_revision: RevisionId, pub answer_mode: AnswerMode /* Choice|Input|Handwriting|SelfRate */,
                     pub raw_answer: String, pub canonical_answer: Option<String>, pub verdict: Verdict,
                     pub hint_used: bool, pub self_knew: Option<bool> /* 仅 Undetermined 后自评时有值 */,
                     pub duration_ms: u32, pub dictation: bool /* 组后默写中的作答为 true */,
                     pub device_id: Uuid, pub device_seq: u64, pub tx_index: u16 /* 同一事务内第几条事件，0 起；device_seq 由同事务共用（CORE-13） */, pub at_ms: i64 }

pub enum GroupEvent { Start { cards: Vec<Uuid> }, Answered(Attempt), Skip(Uuid), Pause, Resume { now_ms: i64 }, DictationDone(Vec<Attempt>), Appeal { attempt: Uuid } }
pub enum GroupCommand { Ask(QuestionDto), PersistAttempt(Attempt), EmitReview(ReviewEvent), StartDictation(Vec<Uuid>), Finished(GroupSummary) }
pub struct GroupState { pub queue: Vec<Uuid>, pub cursor: u32, pub streak: Vec<(Uuid, u8)>, pub done: Vec<Uuid>,
                        pub failed: Vec<Uuid>, pub phase: GroupPhase, pub paused: bool }   // 可序列化，作为会话游标持久化
pub enum GroupPhase { Learning, Dictation, Finished }

// 界面边界 DTO（op 入参与出参）。界面不构造 Attempt：判分、verdict、device_seq、id 均由 Rust 侧 op 处理函数生成
pub enum UiAnswer { Graded(GradeAnswer), SelfRate { knew: bool } /* 只用于 AnswerMode::SelfRate 题型 */ }
pub struct AnswerSubmission { pub card: Uuid, pub answer_mode: AnswerMode, pub raw_answer: String /* 原样作答文本或选项下标串 */,
                              pub answer: UiAnswer, pub hint_used: bool, pub duration_ms: u32 }
pub enum SessionInput { Answer(AnswerSubmission), Skip { card: Uuid }, Pause, Resume,
                        SelfRated { attempt_id: Uuid, knew: bool }, DictationDone(Vec<AnswerSubmission>) }
pub struct QuestionView { pub card: Uuid, pub card_type: CardType, pub prompt_latex: Option<String>, pub prompt_text: Option<String>,
                          pub options: Vec<String>, pub answer_mode: AnswerMode, pub hint_latex: Option<String>,
                          pub required_form: Option<RequiredForm>, pub exam_tags: Vec<String> /* 如 "数二·常考" */ }   // QuestionDto 去掉 expected 后下发
pub enum UiCommand {
    Ask(QuestionView),
    Feedback { attempt_id: Uuid, card: Uuid, verdict: Verdict, expected_latex: String, will_reappear: bool,
               related: Vec<RelatedFormula> /* 易混组成员与派生上下游，最多 6 条 */ },
    NeedSelfRate { attempt_id: Uuid, card: Uuid, expected_latex: String, reason: String },   // 判分为 Undetermined
    StartDictation(Vec<QuestionView>),
    Finished(GroupSummary),
}
pub enum Relation { Confusable { note: Option<String> }, DerivedFrom, DerivesTo }
pub struct RelatedFormula { pub item_id: FormulaItemId, pub title: String, pub latex: String, pub relation: Relation }
pub struct TodayInfo { pub plan_id: Option<Uuid>, pub book_title: Option<String>, pub new_available: u32, pub review_due: u32,
                       pub mistakes_due: u32, pub resumable_session: Option<Uuid>, pub exam_days_left: Option<i32> }
pub struct RecentStats { pub median_ms: Option<u32>, pub samples: u8 }
pub fn step(state: GroupState, ev: GroupEvent, plan: &StudyPlan, rating_map: &RatingMap, recent: &RecentStats, now_ms: i64) -> (GroupState, Vec<GroupCommand>);
pub fn build_question(card: &Card, content: &QuestionSource, seed: u64) -> Result<QuestionDto, FmlError>; // 选项只取 content.distractors（已审校错误变体）；content.confusable 只填反馈 related
```

- 组循环：出题 → 作答 → 判定（CORE-18 `grade`，`seed` 调 CORE-05 question_seed，包含session/card/question_index）；判错、或 Undetermined 后自评“不会”插回本组靠后（当前位置之后第 3 个位置，不足则末尾）并清零连续计数；正确则计数 +1，达到 K 次即该卡完成；全组完成后进入组后默写（可选只默写错题）；默写错误使该卡本组判失败，次日进入错题复习。
- 评分映射（`RatingMap`，带版本，初值）：判错或放弃 → Again；用提示或经组内重现后判对 → Hard；首次判对且无提示 → Good；首次判对、无提示且用时 ≤ 本人该题型最近 30 次判对用时中位数的 50%（判对少于 10 次时不判 Easy）→ Easy；Undetermined → 先返回 `NeedSelfRate`，界面显示标准答案请用户自评，收到 `SelfRated` 后才生成 Attempt（`self_knew` 有值）并推进状态机：自评“会” → Hard 且计入连续计数，自评“不会” → Again；自评不能单独使公式进入 Mastered（CORE-20）。
- 申诉“记错了”：生成引用原 Attempt 的纠正事件并重算排程，原事件保留。
- FFI op（DTO 按 CORE-03 映射规则）：

| op | 入参 → 出参 | 说明 |
| --- | --- | --- |
| `study.books.list` | `{}` → `[BookSummary]` | 不含章节条目以减小体积 |
| `study.books.get` | `{id}` → `Book` | 含章节与条目 |
| `study.books.create` | `BookDraft` → `{id}` | 只允许 `BookSource::User` |
| `study.books.update` | `Book` → `{id}` | id 必须存在，且为用户书 |
| `study.books.delete` | `{id}` → `{}` | 只删书，不删条目；有计划引用时一并停用计划 |
| `study.plan.get` | `{}` → `{plan_id, plan: StudyPlan}` 或 `null` | 当前 active 计划 |
| `study.plan.set` | `StudyPlan` → `{plan_id}` | 新建并设为 active，旧计划 active = 0 |
| `study.today` | `{now_ms}` → `TodayInfo` | 首页数字；复习优先于新学 |
| `study.session.start` | `{plan_id, kind: SessionKind, source_session_id?: Uuid}` → `{session_id, commands: [UiCommand]}` | |
| `study.session.step` | `{session_id, input: SessionInput}` → `{commands: [UiCommand]}` | 处理函数：判分 → 组装 Attempt → 纯函数 `step` → 执行 `PersistAttempt`、`EmitReview` → 映射为 `UiCommand` |
| `study.session.resume` | `{session_id, now_ms}` → `{commands}` | 重发当前题 |
| `study.appeal` | `{attempt_id}` → `{}` | “记错了” |

- 表（本卡 `migrations/0019_study.sql`）：

| 表 | 主要列（类型，约束） | 索引 |
| --- | --- | --- |
| `book` | `id TEXT PK`，`title TEXT NOT NULL`，`source_json TEXT NOT NULL`，`chapters_json TEXT NOT NULL`，`updated_at_ms` | — |
| `study_plan` | `id TEXT PK`，`book_id TEXT NOT NULL REFERENCES book(id)`，`plan_json TEXT NOT NULL`，`active INTEGER NOT NULL`，`updated_at_ms` | `(active)` |
| `study_session` | `id TEXT PK`，`plan_id TEXT NOT NULL`，`kind TEXT NOT NULL`，`state_json TEXT NOT NULL`（GroupState），`started_at_ms`，`last_active_at_ms`，`finished_at_ms INTEGER` | `(plan_id, last_active_at_ms)` |
| `attempt` | Attempt 各字段一列（`verdict_json TEXT`），`session_id TEXT NOT NULL`，`UNIQUE (device_id, device_seq, tx_index)`；只插入不更新 | `(card, at_ms)`，`(session_id)` |
| `confusable_group` | `id TEXT PK`，`source TEXT NOT NULL`（pack 或 user），`items_json TEXT NOT NULL`（2–8 个条目 ID），`note TEXT` | — |

- 错误码（本卡唯一定义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `STUDY_SESSION_EXPIRED` | warning | 否 | last_active_at_ms 距 now_ms 超过 24 h 仍 resume，结束会话并保留完成部分 |
| `STUDY_K_OUT_OF_RANGE` | error | 否 | k_new 不在 1..=5 或 k_review 不在 1..=3 |
| `STUDY_PLAN_INVALID` | error | 否 | 计划其他字段越界、书不存在、exam_subject 非法 |
| `STUDY_NO_CARDS` | info | 否 | 按计划过滤后无可出卡片 |
| `STUDY_BOOK_READ_ONLY` | error | 否 | 更新或删除内容包书 |
| `STUDY_INPUT_INVALID` | error | 否 | 卡片非当前题、attempt_id 不待自评、UiAnswer 不匹配 answer_mode 或题源审校字段无效 |

- 每个业务写命令必须使用 CORE-13 Store.write/enqueue_outbox，显式 changed_fields；不得自行分配 Lamport 或直接写 outbox。重放与缓存更新不当成用户编辑。

选卡纯函数所需输入与算法（见 README §6 Q33（待确认），暂行默认）：

```rust
pub struct SessionSelectionInput { pub schedules: Vec<CardSchedule>, pub book: Book,
 pub effective_new_limit: u32 /* op 层用 CORE-17 due_queue(…, DailyCaps { new_limit: plan.daily_new, review_limit: plan.daily_review_cap, backlog_threshold: plan.daily_review_cap }, now_ms).new_limit_effective 求得 */,
 pub today_new_ids: Vec<Uuid>, pub today_review_ids: Vec<Uuid>, pub mistake_ids: Vec<Uuid>, pub now_ms: i64, pub day: StudyDay }
pub fn select_cards(input: &SessionSelectionInput, plan: &StudyPlan, kind: SessionKind) -> Vec<Uuid>;
```

共同过滤：当前书章节深度优先次序内的条目、启用题型、已校验、未挂起/回收/待修订选择；同胞同学习日只取首张（card_type枚举顺序、UUID字节破同序）。DailyCaps按CORE-17积压降级，group_size是本组最多数而非日配额；今日计数按StudyDay边界、去重Card ID，新学指当日首个进入Learning/Review，复习指非New的有效完成事件。

| kind | 来源与稳定排序 | 配额 |
| --- | --- | --- |
| New | 若仍有到期Review/Learning/Relearning先返回空并提示先复习；否则New按书章节/条目顺序、题型顺序、ID | min(group_size,max(0,effective_new_limit-today_new_ids数量)) |
| Review | due_ms≤now_ms，due_ms升序、ID字节升序 | min(group_size,max(0,daily_review_cap-today_review_ids数量)) |
| Mistakes | 昨学习日组后默写错/最近一次客观作答错且尚未随后答对的本书卡；最近错at_ms降序、ID升序 | 与Review共享当日上限，重复卡只计一次 |
| Cram | 需要exam_date，否则STUDY_INPUT_INVALID；本书符合exam_subject大纲的全部卡，先due_ms升序，再书顺序/ID | 每组group_size，不扣常规new/review配额，事件标cram |
| Dictation | 只取指定已结束组的成员次序，不重新从全书抽取；start入参须带source_session_id | 不额外生成常规复习事件，不重复扣日配额 |

select_cards 的 Dictation 输入由处理层用来源组成员裁剪 schedules/book，kind与source_session_id均校验；session.start DTO附 source_session_id?（只在dictation必填），既有未结束同计划同kind会话优先续接，不能重开绕过额度。

RecentStats 由op层在提交前查询本人同题型最近30条客观Correct、未跳过/自评/改判作答的duration，按(at_ms,device_id,seq)逆序截30，再按duration排序；偶数中位取两中间均值向下取整，samples是实际条数。step不查库，samples<10或median=None不判Easy；当前题不算历史。

| 向量 | 输入 | 期望 |
| --- | --- | --- |
| SELECT-01 | 本书A(due=10)、B(due=9)、C(New)，now=10、group=10、review_cap=10，今日已复习9张 | Review=[B]，New=[] |
| SELECT-02 | New章节次序C,D,E，同胞各异；无到期；effective_new_limit=10、今日9 | New=[C]；Cram单独组不扣此配额 |
| SELECT-03 | 同 SELECT-02，但积压降级使 effective_new_limit=0 | New=[] |
| EASY-01 | 无提示首次判对duration=500，median=1000，samples=10 / 9 | Easy / Good |

build_question 的输入包括已人工审校的QuestionSource（reviewed_by,reviewed_at来自CORE-16，非空）；干扰项只能取其中Distractor并带error_type，不现场合成未审校选项；reviewed_by 空或 reviewed_at_ms≤0 返回 STUDY_INPUT_INVALID（复用本卡错误），不抛无定义异常；用seed洗牌去重，同seed复现，干扰项不足时改Input，不伪造干扰项。`QuestionSource.confusable`（内容包易混组与用户自建易混组，后者未经审校）只用于反馈 `related`，不进入 options；因此用户建组不影响 [R04.c] 的审校要求。

BookSummary `{id:Uuid,title:string,source:BookSource,chapter_count:u32,item_count:u32}`；BookDraft `{title:string,chapters:[Chapter]}`，source固定User、id由仓储生成。QuestionSource由CORE-16包读取适配提供revision/distractors/confusable和审校信息；exam_tags/hint_latex来自条目templates字段；RelatedFormula的派生关系从CORE-14 derivation表读取，反馈不依赖CORE-48界面。seed只调用CORE-05 question_seed(session_id,card_id,question_index)，禁止另写“卡片+作答序号”拼接。

产品约束追踪：见README §6 Q34；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 状态机是纯函数，组内顺序与重现位置由事件确定性重放；每次作答与评分只落库一次。
- 跳过当次不计；暂停挂起到手动恢复；关闭的题型不再出卡；会话游标持久化，24 h 内可续学。
- 两台设备同学一组时保留全部 Attempt，按 `(device_id, device_seq)` 与时间重放。
- 用户可自建公式书，书中只引用公式条目 ID。

**验收标准**
- [R04][R04.a][R04.b][R04.d][R04.e] T-SESSION：默认组 10 条、K = 3 与 K = 1、5 通过，K = 0、6 返回 `STUDY_K_OUT_OF_RANGE`；复习卡 K = 1；答错插回本组靠后第 3 位；组后默写全部或只默写错题；默写错误进入次日错题复习；跳过、暂停、关闭题型；23 h 59 min 续学成功、24 h 01 min 返回 `STUDY_SESSION_EXPIRED`；同一组在两台设备完成后结果一致。
- [R04][R04.j] 自建公式书：创建含 3 章、20 个条目引用的用户书并按其定计划出卡；删除书不删除条目。
- [R04] 评分映射单元测试覆盖表中每一行，含“判对少于 10 次不判 Easy”。
- [R04][R04.h] 申诉生成纠正事件（`correction_of` 指向原事件）、原事件保留，排程按纠正后重算。
- [R04] 边界 op：Undetermined 作答返回 `NeedSelfRate` 且未写 Attempt；`SelfRated` 后写入一条 `self_knew` 有值的 Attempt；`QuestionView` 序列化结果不含标准答案；对内容包书调用 `study.books.delete` 返回 `STUDY_BOOK_READ_ONLY`。
- [R04] 端到端（集成测试，Fake 端口）：选书 → 定计划 → 组学习 → 组后默写 → 次日复习全流程离线可完成。

- [R04.c] 固定QuestionSource+seed连跑两次options完全相同，所有非正确项均能回溯已审校Distractor及error_type；少于所需项改输入题，未审校源拒绝出题。

**规模**：约 500 行；主包 `crates/fml-study/`（约 400 行，含边界 DTO 与 op 处理函数），附属：领域表仓储 `crates/fml-store/src/study/sessions.rs` 与迁移 `0019_study.sql`（约 100 行，DDL 不计）。

