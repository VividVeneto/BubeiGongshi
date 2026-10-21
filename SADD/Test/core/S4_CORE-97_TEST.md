# CORE-97 测试方案

> 来源卡：[S4_CORE-97_功能.md](../../core/S4_CORE-97_功能.md)（复习参数预测偏差监测）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**
- [R04] calibration 199/200样本、偏差0.05/0.0501边界符合原规则；不足200时省略两均值且false，达到200且偏差严格>0.05才true，不自动回退参数。
- [R04] 最近30×24h只取非self_rated/非skipped的首个每日复习；按复习前memory state与elapsed_days历史重放计算p，actual=rating!=Again；同一快照输入，复习后state不可用于预测自身。
- [R04] stats.calibration call的now_ms只在Dart边界取一次，不读领域系统时钟；提示用户回退经CORE-17执行；CORE-20普通统计/提醒可不依赖本卡独立构建。
