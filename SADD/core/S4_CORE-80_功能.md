### CORE-80 学习卡片生成

**目标**：Verified修订的题型生成、要求层级映射、srs.generate处理与卡片插入调用。

**范围**
- 包含：Verified修订的题型生成、要求层级映射、srs.generate处理与卡片插入调用。
- 不包含：排程与卡片/事件/参数表写入（CORE-17）；组学习（CORE-19，下游说明）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-09、CORE-13、CORE-14、CORE-17

**接口契约**

```rust
// crates/fml-srs/src/generate.rs
pub fn generate_cards(rev: &FormulaRevision, enabled: &[CardType], requirement_level: RequirementLevel) -> Vec<Card>;
// 要求层级“掌握/会用”生成回忆与应用题型；“了解/理解”只生成辨识题型；未 Verified 的修订不出卡
```
- FFI op：srs.generate（{revision_id,requirement_level?,enabled_types?}→[Card]）。requirement_level缺省取CORE-14 formula_item.requirement_level；空值（用户自建）按掌握；Q35已确认。CardType/RequirementLevel/Card类型唯一见CORE-17；id调用CORE-05 card_id。

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `STUDY_REVISION_NOT_VERIFIED` | error | 否 | 对非 Verified 修订调用 `srs.generate` |

**实现约束**
- 未Verified不出卡；掌握/会用生成回忆应用，了解/理解只辨识。通过CORE-17 insert_generated与CORE-13单写者事务持久化，不重写排程/表。
- profile scope，使用CORE-03信封handle，切换档案不复用旧Store；取消不写半成品；不复制FSRS调度状态机。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-80_TEST.md](../Test/core/S4_CORE-80_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约130行；主包`crates/fml-srs/src/generate.rs`，附属`crates/fml-ffi/src/ops/srs.rs`的srs.generate处理/登记；DDL/自测不计。
