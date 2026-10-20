### CORE-11 公式间代入、推导链与计算链

**目标**：在两条已校验公式之间做类型安全的符号代入，生成带溯源的派生修订；并支持不生成修订的数值计算链。

**范围**
- 包含：代入候选排序、符号代入（变量换名防捕获、条件与分支）、推导链记录、脱离溯源、循环与深度检测、`CalculationPlan` 计算链与重放。
- 不包含：候选的全文检索与持久化（CORE-14 提供候选集合）；界面（CORE-38）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-09、CORE-10、CORE-56、CORE-77

**接口契约**

```rust
// crates/fml-derive/src/lib.rs
pub struct SlotRef { pub revision: RevisionId, pub path: NodePath, pub slot_type: TypeExpr }
pub struct Candidate { pub revision: RevisionId, pub output: SymbolId, pub output_type: TypeExpr, pub subject: String }
pub enum MatchLevel { QuantityKindExact, DimensionUnified, CrossKind /* 仅 include_cross_kind 时出现 */ }
pub fn rank_candidates(slot: &SlotRef, pool: &[Candidate], include_cross_kind: bool) -> Vec<(Candidate, MatchLevel)>;
// 排序：QuantityKind 匹配 > 量纲合一 > Candidate.subject按UTF-8字节序 > Candidate.output的SymbolId字节序 > Candidate.revision字节序；同一候选revision/output组合去重，排序不读取目标学科或未传入的显示符号名；跨 QuantityKind 的候选默认不列出，仅在 include_cross_kind = true 时列出并标记

pub struct RevisionSnapshot { pub revision: FormulaRevision, pub typed: TypedAst }
pub trait AncestryLookup { fn derivation_depth(&self, rev: &RevisionId) -> u8; fn ancestors(&self, rev: &RevisionId) -> Vec<RevisionId>; }
pub trait RevisionLookup { fn get(&self, id: &RevisionId) -> Option<RevisionSnapshot>; }   // CORE-14 实现
pub struct SubstituteRequest { pub target: RevisionSnapshot, pub slot: NodePath, pub source: RevisionSnapshot,
                               pub source_output: SymbolId, pub var_map: Vec<(SymbolId, SymbolId)>,
                               pub branch: Option<u8>, pub confirm_cross_kind: Option<ConfirmRecord> }
pub struct SubstituteResult { pub new_ast: FormulaNode, pub symbols: SymbolEnv, pub derivation: Derivation,
                              pub check: CheckResult }   // 新修订必须重新完整校验
pub fn substitute(req: &SubstituteRequest, ancestry: &dyn AncestryLookup, units: &dyn UnitRegistry, cancel: &CancelFlag) -> Result<SubstituteResult, FmlError>;

pub struct CalculationPlan { pub steps: Vec<PlanStep> }   // 上一步输出 → 下一步输入
pub struct PlanStep { pub revision: RevisionId, pub inputs: Vec<Assignment>, pub output: SymbolId, pub feeds: Option<SymbolId> }
pub fn run_plan(plan: &CalculationPlan, revs: &dyn RevisionLookup, units: &dyn UnitRegistry, cancel: &CancelFlag) -> Result<Vec<CalcResult>, FmlError>;
```

- FFI op：`derive.rank`、`derive.substitute`、`derive.run_plan`（同步；DTO 按 CORE-03 映射规则，`derive.rank` 的候选池由 CORE-14 `library.substitution_pool` 提供）。
- 错误码（唯一定义；沿用原触发语义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `DERIVE_NOT_VERIFIED` | error | 否 | 目标或来源修订不是Verified/VerifiedPolymorphic |
| `DERIVE_TYPE_MISMATCH` | error | 否 | 槽位与来源输出量纲或MathKind不能合一（按 CORE-77 跨来源协议：新建 `Subst`，目标侧与来源侧 typed 各调一次 `Subst::instantiate_types`（各自把本次用到的全部类型一次传入）后再 `unify`，避免同号变量误合一；`unify` 返回 `Overflow` 时报 `UNIT_OVERFLOW`；MathKind 相容用 CORE-09 `math_kind_compatible`） |
| `DERIVE_CROSS_KIND_UNCONFIRMED` | error | 否 | QuantityKind不同且未带确认记录 |
| `DERIVE_DEPTH_EXCEEDED` | error | 否 | 推导深度大于8 |
| `DERIVE_CYCLE` | error | 否 | 来源修订的祖先含目标修订 |
| `DERIVE_NODE_LIMIT` | error | 否 | 节点数大于4096 |
| `DERIVE_READ_ONLY` | error | 否 | 编辑未脱离的派生修订 |

S1复合op的可序列化输入：derive.rank body={slot:SlotRef,pool:Candidate[],include_cross_kind:bool}，ok={candidates:[[Candidate,MatchLevel]]}；derive.substitute body={request:SubstituteRequest,ancestry:[{revision:UUID,depth:u8,ancestors:UUID[]}]}，ok=SubstituteResult；derive.run_plan body={plan:CalculationPlan,revisions:RevisionSnapshot[]}，ok={results:CalcResult[]}。三者均call/none scope，不能访问隐式Store。substitute的AncestryLookup只读该数组、run_plan的RevisionLookup只读revisions，缺被引用修订/重复ID为FFI_BAD_ARG；单位快照由CORE-56处理层注入（新依赖），不由领域crate读全局。线上形状及正反例见contracts/dto/对应schema的examples；JSON结构校验通过不等同算法语义向量通过。

三个derive op的唯一适配所有者为本卡附属crates/fml-ffi/src/ops/derive.rs：从CORE-56公开snapshot()取得同一Arc并注入units；expected_generation校验及响应代数遵CORE-03。CORE-56不登记这三个op，也不依赖本卡。

FFI错误镜像（不重定义代码；通用信封错误见CORE-03；读取快照的适配另由CORE-56（下游说明，非契约）统一返回ENGINE_UNAVAILABLE）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| derive.rank | 无业务错误；通用信封错误仍适用 |
| derive.run_plan | DERIVE_NOT_VERIFIED、DERIVE_TYPE_MISMATCH、DERIVE_CROSS_KIND_UNCONFIRMED、DERIVE_DEPTH_EXCEEDED、DERIVE_CYCLE、DERIVE_NODE_LIMIT、DERIVE_READ_ONLY、TYPE_DIM_CONFLICT、TYPE_LOG_DIMENSIONED、TYPE_FUNC_ARG_DIMENSIONED、TYPE_MATHKIND_MISMATCH、TYPE_CROSS_DIM、TYPE_QK_MISMATCH、TYPE_UNKNOWN_DIM、TYPE_EMPIRICAL_COEFF、TYPE_AFFINE_MISUSE、UNIT_DIM_SYNTAX、EVAL_DIV_ZERO、EVAL_DOMAIN、EVAL_NAN_OR_INF、EVAL_OVERFLOW、EVAL_NO_CONVERGE、EVAL_NEEDS_INTERVAL、EVAL_NOT_COMPUTABLE、EVAL_LIMIT_EXCEEDED、EVAL_TIMEOUT、EVAL_MULTI_BRANCH、UNIT_UNKNOWN、UNIT_INCOMPATIBLE、UNIT_AFFINE_MISUSE、UNIT_OVERFLOW、NOTATION_CONSTANT_CONFLICT |
| derive.substitute | DERIVE_NOT_VERIFIED、DERIVE_TYPE_MISMATCH、DERIVE_CROSS_KIND_UNCONFIRMED、DERIVE_DEPTH_EXCEEDED、DERIVE_CYCLE、DERIVE_NODE_LIMIT、DERIVE_READ_ONLY、TYPE_DIM_CONFLICT、TYPE_LOG_DIMENSIONED、TYPE_FUNC_ARG_DIMENSIONED、TYPE_MATHKIND_MISMATCH、TYPE_CROSS_DIM、TYPE_QK_MISMATCH、TYPE_UNKNOWN_DIM、TYPE_EMPIRICAL_COEFF、TYPE_AFFINE_MISUSE、UNIT_DIM_SYNTAX、AST_JSON_INVALID、PARSE_LIMIT_EXCEEDED、UNIT_OVERFLOW |

EngineContext.snapshot返回Result；FFI适配先用snapshot()?取得Arc再检查unavailable/expected_generation，任一失败不调用领域算法。层提交后mark_unavailable的Err向调用方传播，不忽略。

rank_candidates不返回业务Err；对每个候选新建 `Subst`，按 CORE-77 跨来源协议分别实例化槽位类型与候选输出类型后合一；`unify` 返回 `DimConflict` 或 `Overflow`、或 MathKind 不相容的候选均视为不匹配而省略，无候选返回空数组；仅FFI参数/快照失败走通用错误。substitute/run_plan保留本卡及依赖诊断集合。

**实现约束**
- 代入同时检查量纲、MathKind 与 QuantityKind，不能只看量纲；约束变量（积分变量、求和指标）自动换名，不发生变量捕获；多值反解的分支显式选择。
- 跨 QuantityKind 代入只有用户显式确认后才允许，确认记录写入 `Derivation.cross_kind_confirmation`。
- 派生修订默认只读；编辑前须“脱离溯源”，脱离后生成独立修订并标“已脱离”。被引用的母修订删除时，派生修订转为独立修订并记录提示（由 CORE-14 执行）。
- 计算链要求相邻步量纲合一且 QuantityKind 匹配，单位自动换算，不生成修订；计划可保存与重放。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-11_TEST.md](../Test/core/S1_CORE-11_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 360 行；主包 `crates/fml-derive/`（算法/纯查询300；不含测试约120），附属 `crates/fml-ffi/src/ops/derive.rs`（快照注入及三个op60）；不含计划持久化。

