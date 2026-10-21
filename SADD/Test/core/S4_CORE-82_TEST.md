# CORE-82 测试方案

> 来源卡：[S4_CORE-82_功能.md](../../core/S4_CORE-82_功能.md)（学习会话仓储、同步投影与op处理）。本文件是该卡验收标准全文；修改范围时同步修改，工具从下方验收标准行起拼回。

**验收标准**
- [R04][R04.a][R04.b][R04.d][R04.e] 持久化T-SESSION：K=0/6返回STUDY_K_OUT_OF_RANGE；23h59min续学成功，24h01min返回STUDY_SESSION_EXPIRED并保留完成部分；两台设备同组完成保留全部Attempt并重放一致；每次作答/评分只落库一次，暂停只手动恢复。
- [R04][R04.j] 自建公式书：创建含 3 章、20 个条目引用的用户书并按其定计划出卡；删除书不删除条目。
- [R04][R04.h] 申诉生成纠正事件（`correction_of` 指向原事件）、原事件保留，排程按纠正后重算。
- [R04] 边界 op：Undetermined 作答返回 `NeedSelfRate` 且未写 Attempt；`SelfRated` 后写入一条 `self_knew` 有值的 Attempt；`QuestionView` 序列化结果不含标准答案；对内容包书调用 `study.books.delete` 返回 `STUDY_BOOK_READ_ONLY`。
- [R04] 端到端（集成测试，Fake 端口）：选书 → 定计划 → 组学习 → 组后默写 → 次日复习全流程离线可完成。
- [R04] 12个study.* op处理只在fml-ffi；书/计划/会话/Attempt codec/applier含删除分支，事务共用device_seq、tx_index稳定，changed_fields/outbox正确；纯模型/DTO唯一来自CORE-19。
- [R04] RecentStats过滤本人/同题型/客观Correct且非跳过自评改判；按(at_ms,device_id,seq)逆序截30后计算中位数，偶数向下取整，当前题不入历史；同kind未结束组优先续接防绕配额，dictation来源组校验。
- [R28] 注册且只注册book/study_plan/attempt/confusable_group；User书稳定枚举，study_session/游标不进同步，预置书不上传。Delete书保留条目且停用计划有效投影；旧数据不复活；同ID同Attempt零写，异值拒绝；不同ID作答保留并确定性投影，无回声outbox。
- [R28] 两设备离线各设active计划，交换顺序任意均由active字段时钟/ID选出同一本机有效计划，原权威值不被隐式改写；下一次显式plan.set才写字段时钟/outbox。保存点失败不漏统计失效/派生更新。
- [R04] 修订变化：条目 head 换为新的 Verified 修订后 study.session.start 先标记待选择，该卡不进入本组；head 为未校验修订时照常出卡。
