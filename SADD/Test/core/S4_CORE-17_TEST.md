# CORE-17 测试方案

> 来源卡：[S4_CORE-17_功能.md](../../core/S4_CORE-17_功能.md)（卡片生成与 FSRS 排程）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R04][R04.h] 重放测试：FS-01～FS-08 与 FS-X1、FS-X2 全部通过（fixtures/fs.yaml 一份，Windows 与 Android 两端 CI 均运行）；同一事件序列在两端、乱序到达后重放得到相同排程；重复事件只计一次。
- [R04][R04.h] 排程：复习优先于新学；每日新学上限 10 生效；积压降低新学；同胞卡同学习日最多一张；切换时刻与时区变更后学习日计算正确。
- [R28] 卡片状态不进同步，只同步事件；相同参数下从合并后的完整事件重算状态一致（由 CORE-26 集成测试复用）。
- [R03] 性能：10000 条公式 / 50000 张卡下 `due_queue` 满足 CORE-01 全局资源预算表“排程取下一题”行；测量方法：criterion 基准 1000 次取 P95。

- [R04.h] reset_card将Card.reset_epoch从0增至1后，即使epoch1尚无事件，replay也忽略epoch0的全部历史并返回新卡调度；序列化/仓储往返保留epoch。

- [R04][R19] 同一事务写两个ReviewEvent：device_seq相同、tx_index=0/1，均可插入并稳定重放；相同UUID重放只保留一次；整库回退后不同UUID即使同三元也保留，不因唯一索引静默丢失；同日仅一次有效排程是派生调度判定，不删除原事件。
- [R04] 参数采用expected_version校验、原子更新与上一版本回退，取消/写失败不部分提交，保留率边界拒绝。
- [R28] study_card/review_event两个owner codec/applier用FakeRegistry独立验证；参数不注册，card派生state/due不上传；重复UUID同负载零写、同UUID异负载拒绝，乱序新事件全部保留且完整重放一致，无本地stamp/outbox；Delete旧Upsert不复活。
- [R04][R28] card.reset_epoch按字段时钟同步，不取远端事件max；无now_ms/StudyDay上下文只标缓存失效，读取再按注入上下文重算，不写伪造now=0排程；stats hook不重复实现。
- [R27] `load_params_tx`：无 srs_params 行时返回默认参数；adopt_params 后在同一写事务内读到新参数；rollback 后读到上一版本；调用不改变任何行。
- [R04] 积压与新学（new_limit=10、review_limit=backlog_threshold=200）：backlog 0/200 → new_limit_effective 10；300 → 5；399 → 0；400 → 0；new_limit=300、review_limit=200 无积压 → 200；backlog_threshold=0 按 1 计；reviews 按 overdue_days 降序、due_ms、id 排序截取 review_limit，未入队者次日仍在队首；暂停/搁置/待选择卡不计入 backlog。
- [R04] 学习日：Asia/Shanghai 切换 04:00 的 03:59 与 04:00 分属两日；America/New_York 2026-03-08（春令跳变）switch_hour=2 的学习日起点为本地 03:00、该学习日 23 小时；Europe/Berlin 2026-10-25（秋令重复）switch_hour=2 取较早一次、学习日 25 小时；“下一学习日起点”跨夏令时按本地日期；switch_hour=24 与 tz="Mars/Base" 报 STUDY_DAY_INVALID（args.field 分别为 switch_hour、tz）；at_ms > now_ms 的事件不参与重放，now_ms 追上后计入。
- [R04] 参数表：无行时 load/params_state 为默认（version 0、has_previous=false、last_optimized_ms=None）；adopt 两次得 version 1、2（previous_version 0、1）；expected_version 不符报 STUDY_PARAMS_VERSION_STALE 且不写；rollback 两次依次回到 1 与默认，第三次报 STUDY_PARAMS_NO_PREVIOUS；回退后 last_optimized_ms 不变；行只追加。
- [R04] 修订变化：head 变为 Verified/VerifiedPolymorphic 新修订后 mark_revision_changes 置 pending_choice 并只写一次（重复调用零写）；head 为未校验修订时不标记；待选择卡列入 DueQueue.pending_choice、不进 reviews/new_cards、不参与同胞隐藏；record_event 报 STUDY_CARD_PENDING_CHOICE 且不写；keep 后 revision_id=head、事件与 epoch 不变；rebuild 后 reset_epoch+1、按新卡排程；对非待选择卡 resolve 报 STUDY_CARD_PENDING_CHOICE；card.id 不变。
- [R04][R19] op 形状与错误逐码：六个 srs.* op 的方式（均 submit）与请求/响应字段按卡内表；desired_retention 0.79/0.96 报 STUDY_RETENTION_OUT_OF_RANGE、0.80/0.95 通过；rating_map_version=0 报 FFI_BAD_ARG；不存在的 card_id 报 STUDY_CARD_NOT_FOUND；CardType 序列化为 snake_case 线名并与 study_card.card_type 列一致；suspend 后卡不入队，取消暂停恢复；reset_card 返回新 reset_epoch。
- [R04] 改判与重置：correction_of 指向不存在或其他卡事件的改判事件不参与调度；reset 与改判乱序到达时，只计当前 reset_epoch 内事件，结果与按排序键顺序到达相同。
