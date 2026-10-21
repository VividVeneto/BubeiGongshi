### CORE-82 学习会话仓储、同步投影与op处理

**目标**：消费CORE-19纯组循环，提供书/计划/会话/作答的幂等持久化、续学、多设备重放、codec/applier及统一FFI处理。

**范围**
- 包含：fml-store study仓储、codec/applier（含删除分支）、12个study.* op的fml-ffi处理、判分/Attempt组装、UI命令投影、申诉与续学。
- 不包含：step/build_question/select_cards和所有纯模型/边界DTO（CORE-19）；调度/判分算法（CORE-17/18）；统计与UI。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-13、CORE-14、CORE-16、CORE-17、CORE-18、CORE-19

**接口契约**

- CORE-19唯一拥有Book、Chapter、StudyPlan、StudySession相关纯DTO、Attempt、SessionSelectionInput、QuestionView、UiCommand等模型与纯函数，本卡import不复制定义；BookSummary/BookDraft仍在CORE-19，id由本卡仓储生成。
- 仓储位于`crates/fml-store/src/study/sessions.rs`及同目录codec/applier；处理函数全部位于本卡编写的`crates/fml-ffi/src/ops/study.rs`，禁止把op处理塞进fml-study。每个业务写命令均用Store.write/enqueue_outbox和显式changed_fields，不自行分配Lamport或直接写outbox；重放/缓存更新不当用户编辑。
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

- 申诉“记错了”：生成引用原 Attempt 的纠正事件并重算排程，原事件保留。
study.session.start 读取候选排程前先调用 CORE-17 `mark_revision_changes`，待选择卡（Card.pending_choice）由 select_cards 过滤；select_cards 的 Dictation 输入由处理层用来源组成员裁剪 schedules/book，kind与source_session_id均校验；session.start DTO附 source_session_id?（只在dictation必填），既有未结束同计划同kind会话优先续接，不能重开绕过额度。

RecentStats 由op层在提交前查询本人同题型最近30条客观Correct、未跳过/自评/改判作答的duration，按(at_ms,device_id,seq)逆序截30，再按duration排序；偶数中位取两中间均值向下取整，samples是实际条数。step不查库，samples<10或median=None不判Easy；当前题不算历史。

BookSummary `{id:Uuid,title:string,source:BookSource,chapter_count:u32,item_count:u32}`；BookDraft `{title:string,chapters:[Chapter]}`，source固定User、id由仓储生成。QuestionSource由CORE-16包读取适配提供revision/distractors/confusable和审校信息；exam_tags/hint_latex来自条目templates字段；RelatedFormula的派生关系从CORE-14 derivation表读取，反馈不依赖CORE-48界面。seed只调用CORE-05 question_seed(session_id,card_id,question_index)，禁止另写“卡片+作答序号”拼接。

- 执行GroupCommand::PersistAttempt/EmitReview时按一次作答同一事务提交游标、Attempt与review事件，device_seq由CORE-13事务共用、tx_index从0递增；Undetermined先返回NeedSelfRate且不写Attempt，SelfRated后才生成带self_knew的Attempt并推进纯循环。对外QuestionView剔除expected，标准答案只在规定反馈/自评结果展示。
- 同计划同kind未结束会话优先续接，不能重开绕过配额；24h内续学，超过24h结束并保留完成部分；暂停必须手动恢复。两台设备同组保留全部Attempt，按(device_id,device_seq)与时间确定性重放，每次作答/评分只落库一次。
- 用户书只引用条目ID；删除书不删除条目，有计划引用则停用；只准User来源创建/更新/删除。组循环、选卡稳定排序/同胞过滤/每日去重与Cram/Dictation规则原样消费CORE-19，不重写算法。
- 表DDL继续在CORE-19迁移元数据的`0019_study.sql`，代码所有权在本卡；不新建重复迁移、不把DDL计450行。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| STUDY_SESSION_EXPIRED | CORE-19 | resume超24h，结束并保留已完成部分 |
| STUDY_K_OUT_OF_RANGE、STUDY_PLAN_INVALID | CORE-19 | 拒绝非法计划/K，不写入 |
| STUDY_NO_CARDS | CORE-19 | 无卡返回info，不创建伪题 |
| STUDY_BOOK_READ_ONLY | CORE-19 | 拒绝内容包书写/删除 |
| STUDY_INPUT_INVALID | CORE-19 | 当前题/待自评/答题模式或题源不匹配时拒绝 |

**实体应用与删除（CORE-13 接缝）**

- 注册 book、study_plan、attempt、confusable_group 四类 codec/applier；study_session 仅本机续学，不注册/不入outbox。book只枚举User来源，预置书不复制上传；按ID UTF-8排序。各类型read_entity返回权威字段与既有完整时钟，排除当前游标/派生统计。
- book/study_plan/confusable_group按字段时钟合并，数组值作为单字段整体决胜，非匿名增删集合。收到两份active计划时不额外生成用户编辑：active候选按其active字段时钟、同钟按计划ID字节最大者作为本机有效计划投影，保留各原权威值，下次plan.set才产生用户字段写。删除书同事务停用引用计划的本机有效投影，不删公式条目；Delete保存原类型墓碑防旧版本复活。
- attempt不可变：相同ID/相同权威值Duplicate，异值Invalid；保留所有不同ID的远端作答，不能用到达顺序覆盖。与review_event关联的更新经CORE17本卡接缝而非直接重写排程算法；完整Attempt用于确定性投影，study_session.cursor仍是本机续学状态，不从他设备覆盖。所有applier在传入WriteTx内完成，Invalid回滚该实体，存储故障Err整页回滚；不stamp/enqueue，不产生同步回声。统计失效hook归CORE20，不双计。

**实现约束**
- fml-study保持sans-I/O；处理层组合grade→Attempt→step→事务效果→UiCommand，所有引擎与Store依赖只在允许层持有。
- Book章节深度/计划范围与exam_subject等校验沿用CORE-19/16；产品Q33/Q34保持确认值/暂行默认，不增减范围。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-82_TEST.md](../Test/core/S4_CORE-82_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约450行；crates/fml-store/src/study/的仓储/codec/applier及本卡编写的crates/fml-ffi/src/ops/study.rs（12op含薄适配）；DDL仍在0019_study.sql，不计数据/schema/生成物、自测与夹具；不重复计CORE-19纯算法。
