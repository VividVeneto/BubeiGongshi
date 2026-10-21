### CORE-81 个性化FSRS参数优化

**目标**：训练集筛选、月限额、留出集比较、srs.optimize处理及调用CORE-17采用参数。

**范围**
- 包含：训练集筛选、月限额、留出集比较、srs.optimize处理及调用CORE-17采用参数。
- 不包含：排程与卡片/事件/参数表写入（CORE-17）；组学习（CORE-19，下游说明）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-09、CORE-13、CORE-14、CORE-17

**接口契约**

```rust
// crates/fml-srs/src/optimize.rs
pub enum OptimizeOutcome { Adopted { params: FsrsParams, holdout_logloss: f64, default_logloss: f64 },
                           Rejected { holdout_logloss: f64, default_logloss: f64 }, TooSoon { next_allowed_ms: i64 },
                           Insufficient { valid_reviews: u32 } }
pub fn optimize_params(events: &[ReviewEvent], current: &FsrsParams, last_opt_ms: Option<i64>, now_ms: i64) -> OptimizeOutcome;
```
- FFI op：srs.optimize（长任务→OptimizeOutcome）；srs.rollback_params及所有srs_params写入/回退归CORE-17。TooSoon/Insufficient是成功业务结果，不再为这两个业务分支登记错误码（CO-23）。

**实现约束**
- 个性化：有效复习少于 400 次使用默认参数；只有留出集 log-loss 优于默认时启用，每个自然月最多一次；TooSoon.next_allowed_ms 为下月 1 日学习日起点，可一键回退；突击、跳过与自评兜底事件不进优化集；目标保留率限定 0.80–0.95，默认 0.90。
- 调用fsrs=6.6.2 compute_parameters与evaluate，版本/包体约束沿CORE-17；得到Adopted后通过CORE-17 adopt_params原子写入，算法不直接写表；保留默认/当前/上一参数与版本/优化时间供回退和月限额。
- profile scope，使用CORE-03信封handle，切换档案不复用旧Store；取消不写半成品；不复制FSRS调度状态机。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-81_TEST.md](../Test/core/S4_CORE-81_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约165行；主包`crates/fml-srs/src/optimize.rs`，附属`crates/fml-ffi/src/ops/srs.rs`的srs.optimize处理/登记；DDL/自测不计。
