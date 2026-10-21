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
