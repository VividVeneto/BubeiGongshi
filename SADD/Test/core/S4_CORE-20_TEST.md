# CORE-20 测试方案

> 来源卡：[S4_CORE-20_功能.md](../../core/S4_CORE-20_功能.md)（学习统计、掌握度与本地提醒）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**

- [R04][R25] 用 FakeProfileSessionSource 驱动 null→A→closing/null→B，B 再取与 A 同 profileId、不同 handle。无档案时 resume/reschedule/cancel 均无 FFI/权限/平台调度；ProfileHooks order80 对每新 handle 恰好 resume 一次，进程钩子/首帧钩子不重跑，重复 paused 订阅不存在。A/B 分别恢复各自 device.reminder_time。
- [R04][R25] 在设置读取、权限、due_count、schedule、设置写入每个 await 前后设置屏障，发起 A close 后 current 必须同步为 null，后续无新 A 副作用，A 迟到数量不安排成 B 通知；stats.due_count 只携带同一次边界 UTC now_ms。无法取消的 schedule 先完成再 cancelAll，完成补偿取消前不允许 B order80 安排。
- [R04][R25] 并发 reschedule/cancel/paused 按 handle 串行；关闭路径 cancelAll 不写 device.reminder_time=null（与用户公开 cancel 区分），切回 A 原时刻仍在。注入 cancelAll/在途设置排空失败，所有 beforeClose 停止前缀仍执行，A handle 未 close、B 未 open；显式重试只补未完成清理。
- [R04][R04.i] T-STATS：随机生成 1000 组事件序列，命中缓存的结果与丢弃缓存后全量重算的结果 100% 一致；同步合并、卡片重置、学习日边界与时区变更后统计正确；自评不计入正确率。
- [R04][R04.d][R04.i] 掌握判据单元测试：仅自评达标不进入 Mastered；跨日与间隔不足不进入 Mastered；判错转 NeedsReinforce。
- [R04][R04.i] 提醒：`resume()` 调用 Fake `NotificationScheduler` 时正文只含数量，到期为 0 时不安排；游客与注册用户行为一致且不发网络请求。
- [R04] 学习效果试点（手动，M3 前）：≥ 30 名目标用户连续 ≥ 30 天，记录 7 天与 30 天保留率（目标 ≥ 80% 与 ≥ 70%）、Undetermined 比例（≤ 5%）与申诉改判比例（≤ 1%）；未达标须调整组大小、K 或评分映射后复测，结果写入附录 A 评审记录。

- [R04.i] 先缓存设备A seq=100，再同步设备B seq=1 且 at_ms更早的事件，下一次统计必须失效并重算计入B；重复拉取B不再增加数量。

- [R04] at写入后重启读取相同时刻，None不调schedule；calibration样本/偏差验收迁CORE-97。
