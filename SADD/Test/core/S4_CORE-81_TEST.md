# CORE-81 测试方案

> 来源卡：[S4_CORE-81_功能.md](../../core/S4_CORE-81_功能.md)。

**验收标准**
- [R04] 个性化边界：有效复习 399 与 400 次、log-loss 劣于默认、同月第二次优化、回退、目标保留率 0.79/0.80/0.95/0.96 均按规则处理。
- [R04] 突击/跳过/自评不进训练集；TooSoon/Insufficient返回OptimizeOutcome而非错误；取消/Rejected不采用参数，Adopted经CORE-17写入并能回退。
- [R04] 同一自然月第二次返回 TooSoon，断言 next_allowed_ms 等于下月 1 日学习日起点；覆盖跨年与学习日起点边界。
