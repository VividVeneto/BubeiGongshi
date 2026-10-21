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
// 纯函数：按下表过滤并按 CardType 声明顺序输出；未通过校验的修订返回空
```

- 出卡判定：修订 `validation` 为 Verified 或 VerifiedPolymorphic 且 `draft == false` 才出卡；其余（Draft、Unresolved、Invalid）`generate_cards` 返回空，`srs.generate` 报 STUDY_REVISION_NOT_VERIFIED。题型集合 = enabled ∩ 层级允许 ∩ 前置满足；enabled 为空切片时不出卡（op 省略 enabled_types 时取全部十种）。
- 每张卡：`id = card_id(rev.id, card_type 的 snake_case 线名, "")`（CORE-05；本版本不按模板实例出卡，template_id 恒为空串，见 ADR-V5-54）、item = rev.item、revision = rev.id、siblings_key = rev.item、reset_epoch = 0、state = New、due_ms = None、pending_choice = false。

| CardType（线名） | 类别 | 前置（不满足则不出该卡） |
| --- | --- | --- |
| name_to_formula | 回忆 | 无 |
| formula_to_name | 辨识 | 无 |
| symbol_cloze | 回忆 | SymbolEnv 中 role 为 Variable 或 Parameter 的符号 ≥ 1 |
| variable_meaning | 回忆 | 至少一个 Variable/Parameter 符号的 meaning_key 非空 |
| unit_dimension | 应用 | 至少一个 Variable/Parameter 符号的 declared_type.dimension 为 Some 且不是无量纲 |
| simple_numeric | 应用 | validation 为 Verified（多态修订不出）、ast 根为等式且一侧为单个 Variable 符号 |
| condition_recall | 回忆 | conditions 非空 |
| confusable_choice | 辨识 | 无（干扰项不足时的降级由组学习出题处理，下游说明，非契约） |
| derivation_order | 应用 | derived_from 为 Some |
| context_choice | 辨识 | 无 |

- 层级允许：了解、理解 → 仅辨识类；掌握、会用 → 辨识、回忆、应用全部类别（Q35）。
- FFI op：srs.generate（submit，{revision_id,requirement_level?,enabled_types?}→[Card]，返回该修订按表应有的全部卡；已存在的卡 ID 由 CORE-17 insert_generated 跳过不重复插入）。requirement_level缺省取CORE-14 formula_item.requirement_level；空值（用户自建）按掌握；Q35已确认。CardType/RequirementLevel/Card类型唯一见CORE-17；id调用CORE-05 card_id。

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `STUDY_REVISION_NOT_VERIFIED` | error | 否 | 对非 Verified 修订调用 `srs.generate` |

**实现约束**
- 出卡判定与题型表见接口契约；通过CORE-17 insert_generated与CORE-13单写者事务持久化，不重写排程/表。
- profile scope，使用CORE-03信封handle，切换档案不复用旧Store；取消不写半成品；不复制FSRS调度状态机。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-80_TEST.md](../Test/core/S4_CORE-80_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约160行；主包`crates/fml-srs/src/generate.rs`，附属`crates/fml-ffi/src/ops/srs.rs`的srs.generate处理/登记；DDL/自测不计。
