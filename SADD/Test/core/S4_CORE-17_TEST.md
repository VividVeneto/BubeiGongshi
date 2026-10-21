# CORE-17 测试方案

> 来源卡：[S4_CORE-17_功能.md](../../core/S4_CORE-17_功能.md)（卡片生成与 FSRS 排程）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R04][R04.h] 重放测试：FS-01～FS-08 全部通过；同一事件序列在两端、乱序到达后重放得到相同排程；重复事件只计一次。
- [R04][R04.h] 排程：复习优先于新学；每日新学上限 10 生效；积压降低新学；同胞卡同学习日最多一张；切换时刻与时区变更后学习日计算正确。
- [R28] 卡片状态不进同步，只同步事件；从合并后的完整事件重算状态一致（由 CORE-26 集成测试复用）。
- [R03] 性能：10000 条公式 / 50000 张卡下 `due_queue` 满足 CORE-01 全局资源预算表“排程取下一题”行；测量方法：criterion 基准 1000 次取 P95。

- [R04.h] reset_card将Card.reset_epoch从0增至1后，即使epoch1尚无事件，replay也忽略epoch0的全部历史并返回新卡调度；序列化/仓储往返保留epoch。

- [R04][R19] 同一事务写两个ReviewEvent：device_seq相同、tx_index=0/1，均可插入并稳定重放；相同UUID重放只保留一次；整库回退后不同UUID即使同三元也保留，不因唯一索引静默丢失；同日仅一次有效排程是派生调度判定，不删除原事件。
- [R04] 参数采用expected_version校验、原子更新与上一版本回退，取消/写失败不部分提交，保留率边界拒绝。
- [R28] study_card/review_event两个owner codec/applier用FakeRegistry独立验证；参数不注册，card派生state/due不上传；重复UUID同负载零写、同UUID异负载拒绝，乱序新事件全部保留且完整重放一致，无本地stamp/outbox；Delete旧Upsert不复活。
- [R04][R28] card.reset_epoch按字段时钟同步，不取远端事件max；无now_ms/StudyDay上下文只标缓存失效，读取再按注入上下文重算，不写伪造now=0排程；stats hook不重复实现。
- [R27] `load_params_tx`：无 srs_params 行时返回默认参数；adopt_params 后在同一写事务内读到新参数；rollback 后读到上一版本；调用不改变任何行。
