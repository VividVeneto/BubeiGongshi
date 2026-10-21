### CORE-97 复习参数预测偏差监测

**目标**：从复习前状态的历史重放监测预测偏差，只提示回退个性化参数，不自动修改参数。

**范围**
- 包含：30天有效样本筛选、每日首个复习去重、复习前memory state重放、预测/实测聚合、边界判断与stats.calibration处理。
- 不包含：FSRS与重放内核/参数回退执行（CORE-17）；常规统计与提醒（CORE-20）；提示界面（CORE-49）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-13、CORE-17、CORE-20

**接口契约**

预测偏差口径：最近30×24h内非self_rated/非skipped的首个每日复习，按复习前memory state与elapsed_days算预测回忆概率p，actual=rating!=Again；样本≥200且abs(mean(p)-mean(actual))>0.05才建议回退；不自动回退。stats.calibration body={now_ms}，ok={samples,mean_predicted?,mean_observed?,suggest_rollback}，不足样本两均值省略、false；call。输入来自同一快照的历史重放，不用复习后状态预测自身。

- 本卡单向消费CORE-20统计输入/同快照读取约定及CORE-17 replay；CORE-20不调用本卡。now_ms由Dart在调用边界取一次UTC毫秒注入，领域函数不读时钟。
- stats.calibration请求{now_ms}与成功负载/sensitive/error镜像由本卡唯一登记，模式call；沿CORE-03/13/17/20已有校验/存储错误透传，不新增业务码。

**实现约束**
- 样本≥200且绝对偏差严格大于0.05才suggest_rollback=true；不足样本时mean_predicted/mean_observed必须省略，不用null或假零代替。
- 首个每日复习按StudyDay归日，30×24h窗口与日边界分别处理；不计self_rated/skipped。actual为rating!=Again，不用复习后state预测自身。
- 只提示用户通过CORE-17 srs.rollback_params回退，不自动回退；同一数据库快照计算，缓存与stats_generation仍归CORE-20，本卡无表。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-97_TEST.md](../Test/core/S4_CORE-97_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约115行；主包 `crates/fml-study/src/stats/calibration.rs`100行，附属 `crates/fml-ffi/src/ops/stats.rs` 的stats.calibration处理/登记15行；FSRS重放内核、数据、生成物、自测不计。单阶段独立构建测试样本/偏差边界与历史重放。
