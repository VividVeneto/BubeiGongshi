# CORE-80 测试方案

> 来源卡：[S4_CORE-80_功能.md](../../core/S4_CORE-80_功能.md)。

**验收标准**
- [R04] 十种CardType逐一生成，未Verified拒绝STUDY_REVISION_NOT_VERIFIED；缺省要求层级取条目值，用户条目空值按掌握；了解/理解与掌握/会用题型映射符合Q35。
- [R04][R28] 固定修订/题型的card_id稳定，重复调用不重复插入；同事务outbox与卡片一致，生成不另改已有事件/调度。
