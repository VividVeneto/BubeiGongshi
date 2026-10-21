# CORE-32 测试方案

> 来源卡：[S5_CORE-32_扩展.md](../../core/S5_CORE-32_扩展.md)。

**验收标准**
- [R33][R40] 状态合法表逐边通过、其余转换RECOG_TRANSITION_INVALID；networked=false时不能Authorized。未知远端保留只查询，不重新提交的状态语义。
- [R27][R35] Fake CoreBinding/平台密钥验证HistoryKeyUnlocker：loaded直接false，version0轮换clear=false；失效/不匹配轮换clear=true返回true；ensure前后ProfileSession变化丢弃/清零，重试最多一次。
- [R27] 解锁器wrap后/commit前失败不改已提交版本；锁定后不提供旧密钥；真实SQL/WAL/GC/崩溃恢复集成验收迁CORE-85。
