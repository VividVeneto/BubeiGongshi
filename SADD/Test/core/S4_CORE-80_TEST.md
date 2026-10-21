# CORE-80 测试方案

> 来源卡：[S4_CORE-80_功能.md](../../core/S4_CORE-80_功能.md)。

**验收标准**
- [R04] 十种CardType逐一生成，未Verified拒绝STUDY_REVISION_NOT_VERIFIED；缺省要求层级取条目值，用户条目空值按掌握；了解/理解与掌握/会用题型映射符合Q35。
- [R04][R28] 固定修订/题型的card_id稳定，重复调用不重复插入；同事务outbox与卡片一致，生成不另改已有事件/调度。
- [R04] 题型表逐行：每个 CardType 构造满足/不满足前置的修订各一例（无变量、无 meaning_key、仅无量纲、多态修订 simple_numeric、无 conditions、无 derived_from），断言出卡与否；输出按 CardType 声明顺序；enabled 为空切片不出卡、op 省略 enabled_types 取全部。
- [R04] 校验状态：Verified 与 VerifiedPolymorphic 出卡（后者无 simple_numeric），Draft/Unresolved/Invalid 及 draft=true 纯函数返回空、srs.generate 报 STUDY_REVISION_NOT_VERIFIED。
- [R28] 卡 ID：card_id 使用 snake_case 线名与空 template_id，与 contracts/vectors/ids-v1.json 的 card_id 空模板向量一致；Card 新卡字段 reset_epoch=0、state=New、due_ms=None、pending_choice=false。
