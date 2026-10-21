### CORE-11 公式间代入、推导链与计算链

**目标**：在两条已校验公式之间做类型安全的符号代入，生成带溯源的派生修订；并支持不生成修订的数值计算链。

**范围**
- 包含：代入候选排序、符号代入（变量换名防捕获、条件与分支）、推导链记录、脱离溯源、循环与深度检测、`CalculationPlan` 计算链与重放。
- 不包含：候选的全文检索与持久化（CORE-79 提供候选集合；下游说明，非契约；本卡纯函数只接收调用方传入的 pool）；界面（CORE-38（下游说明，非契约））；派生修订的写入、脱离与 `DERIVE_READ_ONLY` 的编辑拦截（CORE-14（下游说明，非契约））；符号反解算法（CORE-93 `isolate`，本卡只调用）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-09、CORE-10、CORE-56、CORE-77、CORE-93

**接口契约**

```rust
// crates/fml-derive/src/lib.rs（依赖 fml-ast、fml-type、fml-eval、fml-units、fml-error；不依赖 fml-store/fml-ffi）
// 以下全部 pub struct/enum：#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]，字段蛇形，枚举为蛇形字符串（MatchLevel 为 "quantity_kind_exact"|"dimension_unified"|"cross_kind"），形状以 contracts/dto/types.schema.json 为准
pub struct SlotRef { pub revision: RevisionId, pub path: NodePath, pub slot_type: TypeExpr }
pub struct Candidate { pub revision: RevisionId, pub output: SymbolId, pub output_type: TypeExpr, pub subject: String }
pub enum MatchLevel { QuantityKindExact, DimensionUnified, CrossKind /* 仅 include_cross_kind 时出现 */ }
pub fn rank_candidates(slot: &SlotRef, pool: &[Candidate], include_cross_kind: bool) -> Vec<(Candidate, MatchLevel)>;
// 排序：QuantityKind 匹配 > 量纲合一 > Candidate.subject按UTF-8字节序 > Candidate.output的SymbolId字节序 > Candidate.revision字节序；同一候选revision/output组合去重，排序不读取目标学科或未传入的显示符号名；跨 QuantityKind 的候选默认不列出，仅在 include_cross_kind = true 时列出并标记

pub struct RevisionSnapshot { pub revision: FormulaRevision, pub typed: TypedAst }
pub trait AncestryLookup { fn derivation_depth(&self, rev: &RevisionId) -> u8; fn ancestors(&self, rev: &RevisionId) -> Vec<RevisionId>; }
pub trait RevisionLookup { fn get(&self, id: &RevisionId) -> Option<RevisionSnapshot>; }   // 由本卡 derive.rs 以请求数组实现（不是 CORE-14 仓储）
pub struct SubstituteRequest { pub target: RevisionSnapshot, pub slot: NodePath, pub source: RevisionSnapshot,
                               pub source_output: SymbolId, pub var_map: Vec<(SymbolId, SymbolId)>,
                               pub branch: Option<u8>, pub confirm_cross_kind: Option<ConfirmRecord> }
pub struct SubstituteResult { pub new_ast: FormulaNode, pub symbols: SymbolEnv, pub derivation: Derivation,
                              pub check: CheckResult }   // 新修订必须重新完整校验
pub fn substitute(req: &SubstituteRequest, ancestry: &dyn AncestryLookup, units: &dyn UnitRegistry, cancel: &CancelFlag) -> Result<SubstituteResult, FmlError>;

pub struct CalculationPlan { pub steps: Vec<PlanStep> }   // 上一步输出 → 下一步输入
pub struct PlanStep { pub revision: RevisionId, pub inputs: Vec<Assignment>, pub output: SymbolId, pub feeds: Option<SymbolId> }
// feeds 方向：本步 output 的结果喂给**下一步**修订中的符号 feeds；最后一步 feeds 必须为 None，否则 FFI_BAD_ARG
pub fn run_plan(plan: &CalculationPlan, revs: &dyn RevisionLookup, units: &dyn UnitRegistry, cancel: &CancelFlag) -> Result<Vec<CalcResult>, FmlError>;
```

- FFI op：`derive.rank`、`derive.substitute`、`derive.run_plan`（同步；DTO 按 CORE-03 映射规则，`derive.rank` 的候选池由 CORE-79 `library.substitution_pool` 提供）。
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


- typed 来源（R11-03）：typed 不持久化。derive.* 适配（本卡 derive.rs）对请求中的每个 `RevisionSnapshot` 用同一快照单位重跑 CORE-09 `check(revision.ast, revision.symbols, units, false, cancel)`，传入的 typed 须与重算结果的 serde JSON 逐字节相等，否则 `FFI_BAD_ARG`；重算不是 Verified/VerifiedPolymorphic 报 `DERIVE_NOT_VERIFIED`。调用方的 typed 取自同一 generation 的 CORE-56 `engine.check` 结果；rank 池的 `Candidate.output_type` 由 CORE-79 `library.substitution_pool` 适配以同一方式补全。
- 来源反解（R11-01）：substitute 先以 CORE-93 `isolate(source.ast, source.typed, source_output, cancel)` 得到各支 E_i（来源须为根 Eq 关系）；只有一支时 `branch` 须为 None 或 Some(0)；多支时 `branch` 必填且 < 支数，否则 `DERIVE_TYPE_MISMATCH`（参数 reason="branch"）；isolate 的 `EVAL_NOT_COMPUTABLE` 原样返回。不自写反解。
- substitute 确定性规则（R11-02）：① `var_map` 为 (来源 SymbolId → 目标 SymbolId)：E 中出现的来源符号按表改写为目标符号，两者 QuantityKind 与量纲按 `DERIVE_TYPE_MISMATCH` 同规则检查；② 未映射的来源自由符号与来源 BoundVar 一律视为新符号：按来源 SymbolId 升序，从“目标 env 最大 id + 1”起连续分配新 SymbolId，复制来源 SymbolDecl（id 改新值）；③ 新符号 glyph 与目标 env 已有 glyph 相同时（防捕获/防混淆），依次尝试追加 `'`、`''`、`_1`、`_2`……取第一个不冲突者；④ 新 env = 目标 env（不变）+ 新符号，按 id 升序；⑤ 把目标 AST 中 `slot` 处子树替换为改写后的 E_branch，再对新 AST 做 `check_limits`（超 4096 节点报 `DERIVE_NODE_LIMIT`）；⑥ `Derivation`：source_revisions=[source.id]，target_slot=slot，var_map=原样，conditions = 目标 conditions 后接改写后的来源 conditions（去掉逐字节相同的重复），branch=请求值，depth = max(目标深度, 来源深度) + 1（深度由 AncestryLookup 给出，>8 报 `DERIVE_DEPTH_EXCEEDED`），cross_kind_confirmation=请求值；⑦ 对新 AST 运行 CORE-09 `check` 放入 `SubstituteResult.check`，其中的 Error 诊断不转为 Err（是否可保存由 CORE-14（下游说明，非契约）按 validation 判定）；⑧ 目标或来源为未脱离派生修订本身不阻止代入（代入生成新修订）；`DERIVE_READ_ONLY` 只由 CORE-14 编辑路径返回，本卡只定义该码。同一输入的 `canonical_hash(new_ast)` 必须可复现。
- rank 判定（R11-06）：每候选先按跨来源协议做量纲合一（失败或 MathKind 不相容 → 省略）；再比较 QuantityKind：两侧均为 Some 且字符串相等 → `QuantityKindExact`；任一侧为 None → `DimensionUnified`；两侧 Some 且不等 → `CrossKind`（include_cross_kind=false 时省略）。rank 不读 UnitRegistry，CORE-08 的 `compatible_with` 只在 substitute 的确认流程使用：兼容的 kind 仍要求 `confirm_cross_kind`，确认界面提示“兼容”。槽位或候选 dimension 为 None（Unknown）时该候选省略。
- run_plan（R11-05）：逐步构造 CORE-10 `CalcRequest`：revision_ast/symbols/typed 取该步快照；assignments = 本步 inputs，加上上一步 `feeds` 指定的符号 = 上一步结果（value 与 unit 用上一步 `CalcResult` 的未修约值与单位、uncertainty 取上一步区间半宽，若有）；target=output；output_unit = 下一步 feeds 符号的声明单位（无声明或最后一步为 None，按 CORE-10 默认）；interval=None；given_constants 由 CORE-56 处理层注入同一快照的常数；display：中间步 `Full`，最后一步 `LeastSigFigs`。相邻步要求 feeds 两侧量纲合一且 QuantityKind 按上述 rank 规则不为 CrossKind，否则 `DERIVE_TYPE_MISMATCH`。

**实现约束**
- 代入同时检查量纲、MathKind 与 QuantityKind，不能只看量纲；约束变量（积分变量、求和指标）自动换名，不发生变量捕获；多值反解的分支显式选择。
- 跨 QuantityKind 代入只有用户显式确认后才允许，确认记录写入 `Derivation.cross_kind_confirmation`。
- 派生修订默认只读；编辑前须“脱离溯源”，脱离后生成独立修订并标“已脱离”。被引用的母修订删除时，派生修订转为独立修订并记录提示（由 CORE-14（下游说明，非契约）执行）。
- 计算链要求相邻步量纲合一且 QuantityKind 匹配，单位自动换算，不生成修订；计划可保存与重放。
- 性能：本卡无独立预算行；`derive.rank` 若用于交互，由 CORE-48（下游说明，非契约）引用 CORE-01“点击到可见反馈”行验收；`rank_candidates` 纯函数对 10000 候选应在单线程 1 s 内完成（基准测试记录，不作阻断）。
- 外部前提：运行依赖 `serde`（derive）；开发依赖 `serde_json`、YAML 夹具解析库（读取 sx.yaml）、JSON Schema 2020-12 校验库，版本由首张使用卡按 ADR-V5-15 锁入 `Cargo.lock`。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-11_TEST.md](../Test/core/S1_CORE-11_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约725行（反解由 CORE-93 `isolate` 实现、计入 CORE-93 规模；typed 重算校验计入② FFI 110 行内），分阶段：①本卡类型、候选排序、代入/防捕获/重校验和安全检查485行；②CalculationPlan重放130行及三个FFI op/数组Lookup110行，共240行；主包crates/fml-derive/615行，附属crates/fml-ffi/src/ops/derive.rs 110行；持久化与自测不计。 阶段独立构建/测试：①纯候选与代入（485行）：纯算法入口可直接构造Lookup验证，crate独立构建；不注册尚未交付op。；②计划与FFI（240行）：补计划重放并注册全部op，验证缺/重复ID、快照失败和透传诊断。

