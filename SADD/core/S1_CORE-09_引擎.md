### CORE-09 类型推断与量纲校验

**目标**：对绑定后的 AST 推导量纲、QuantityKind 与数学结构，给出带定位的诊断和修订的校验状态，支持数学公式的量纲多态。

**范围**
- 包含：运算规则表、`Validation` 判定、经验公式处理、纯函数 check（infer → 调用 CORE-77 `unify` → 诊断）；FFI 编排由 CORE-56（下游说明，非契约）交付。
- 已拆出：`DimVar`、`DimExpr`、`TypeExpr` 与合一（unification）由 CORE-77 交付（本卡原规模约 500 行另计规则表 150 行，超出先拆卡约定）。
- 不包含：数值计算（CORE-10（下游说明，非契约））；代入（CORE-11（下游说明，非契约））；新 RevisionId 与“待重校”标记（CORE-14（下游说明，非契约））。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-06、CORE-07、CORE-08、CORE-77

**接口契约**

```rust
// crates/fml-type/src/rules.rs、infer.rs（crate 骨架归 CORE-77，本卡追加 mod 声明）
// DimVar、DimExpr、TypeExpr 与 unify/Subst 定义见 CORE-77（crates/fml-type/src/dim.rs），本卡 use 之，不重复定义
// MathKind、Validation、TypeDecl 定义见 CORE-05
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)] // serde：{types:[[NodePath 文本, TypeExpr],…]}，deny_unknown_fields
pub struct TypedAst { pub types: Vec<(NodePath, TypeExpr)> }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)] // serde：typed 为 None 时省略；validation/diagnostics 按 CORE-05/CORE-02 约定
pub struct CheckResult { pub typed: Option<TypedAst>, pub validation: Validation, pub diagnostics: Vec<Diagnostic> }

pub fn check(ast: &FormulaNode, env: &SymbolEnv, units: &dyn UnitRegistry, empirical: bool,
             cancel: &CancelFlag) -> CheckResult;
pub fn infer_slot(ast: &FormulaNode, typed: &TypedAst, slot: &NodePath) -> Option<TypeExpr>; // 供 CORE-11（下游说明，非契约）；slot 不存在或 typed 无该条目返回 None
```

- 所需输入：已解析 AST、已绑定 SymbolEnv、UnitRegistry、empirical 与 CancelFlag；本 crate 不依赖解析器。FFI 管线契约由 CORE-56 定义。
- 校验状态规则：存在 Error → Invalid；有未绑定符号、Unknown 量纲或未确认的 Warning → Unresolved；全部通过 → Verified 或 VerifiedPolymorphic。只有 Verified 与 VerifiedPolymorphic 的修订可计算、可代入、可出卡。Unknown 不等于多态。
- 诊断分级与 UI 行为：Error（量纲不匹配、向量结构错误、温度点乘除）阻止保存并高亮节点；Warning（同量纲不同 QuantityKind、经验公式未设系数）允许保存但须确认（`needs_confirm`）；Info（建议单位、有效数字、可简化）只提示。
- 运算规则：规则表在 `crates/fml-type/src/rules.rs`，逐节点/函数见下“运算规则表”；表外的 FunctionId 不存在（CORE-05 已穷举），表中未列的组合按 `TYPE_MATHKIND_MISMATCH` 拒绝，不静默放行。
- 与 CORE-77 的衔接（T1-F03/F05/F08）：①DimVar 分配顺序固定——检查开始时用 `Subst::fresh` 按 `SymbolId` 升序为未声明量纲的符号各分配一个，再在 AST 先序遍历中为需要的子式补分配；②`unify` 返回 `DimConflict` 时诊断为 `TYPE_DIM_CONFLICT`，参数 left/right 用 `DimExpr::to_text()`，定位首个不可合一子式后继续检查其余子式（Subst 在 Err 后保持不变）；返回 `Overflow` 时诊断为 `UNIT_OVERFLOW`（error，结果 Invalid）；③“须无量纲”一律指在 Angle 软约束下与 `DimExpr::one()` 合一（见下）；参数是未声明量纲的符号时合一把其变量绑定为无量纲，结果可为 Verified，不报 `TYPE_UNKNOWN_DIM`；④`VerifiedPolymorphic.vars` 取最终 typed 中出现的 `free_vars()` 编号（升序去重）；`constraints` 只用自由变量表述：按 `SymbolId` 升序，对步骤①分配了变量的每个符号输出 `<glyph> : <Subst::resolve(D_sym).to_text()>`（glyph 为 SymbolDecl.glyph），不输出已绑定变量作左侧的绑定；⑤MathKind 相容判定归本卡 `rules.rs` 的 `pub fn math_kind_compatible(a: &MathKind, b: &MathKind) -> bool`：同种相容；`Vector(None)` 与 `Vector(Some(n))`、`Matrix` 的 `None` 维与具体维相容，具体维数不同则不相容；`TYPE_MATHKIND_MISMATCH` 与 CORE-11 的 `DERIVE_TYPE_MISMATCH` 共用它；⑥输出 `TypedAst` 前对每个 `TypeExpr.dimension` 调 `Subst::resolve`，typed 中的量纲只含自由变量（`Subst` 不持久化，未 resolve 的绑定变量在跨修订使用时会被 CORE-77 的 `instantiate*` 当作独立自由变量），且 typed 中出现的全部变量 ⊆ `VerifiedPolymorphic.vars`；⑦`fresh` 分配总数 ≤ 符号数 + 节点数（各 ≤ 4096），与 CORE-77 的上界说明一致。
- Angle 软约束（本卡规则，CORE-77 的 unify 不变）：加减、关系、Piecewise 值与“须无量纲”的合一若返回 `DimConflict`，且 `resolve(a)·resolve(b)⁻¹` 为 ground、基础量纲与 Count 指数均为 0、仅 Angle 指数 k≠0，则改为 `unify(a, b·Angle^k)` 并接受，不报 `TYPE_DIM_CONFLICT`；Count 与基础量纲始终是硬约束。故 sin(ωt)、θ = arcsin x、e^{iθ}、ω = 2πf 均通过；ω = f 仅在两侧都声明且不相容的 QuantityKind 时由下述 QK 规则给 `TYPE_QK_MISMATCH`。
- 默认类型：Number 为无量纲 Scalar、kind None；Symbol 取声明的量纲（经 `DimensionFull::parse`）、quantity_kind 与 math_kind，未声明量纲引入步骤①的变量，未声明 math_kind 视为 Scalar；Unit(UnitRef) 取 `UnitRegistry::lookup` 的 dimension（未找到报 CORE-08 的 `UNIT_UNKNOWN`，error），kind None；Hole 取新变量、Unknown math_kind；积分/求和变量（differentials、index）未在 env 声明时按 BoundVar 分配新变量。
- QuantityKind 传播：只有声明符号带 kind；Neg/Plus/Conjugate/Transpose、abs、max/min 与 Piecewise 保留操作数 kind；其余运算与函数结果 kind 为 None。加减、关系与 Piecewise 值两侧均有 kind 且既不相同也不在任一方的 `compatible_with` 中（经 `UnitRegistry::quantity_kind` 查询，未知 id 视为不相容）→ `TYPE_QK_MISMATCH`（warning，needs_confirm），结果 kind None；一侧 None 不警告、结果取另一侧。
- MathKind 推断：Unknown 操作数按所需种类取用、不报错；加减与关系两侧须 `math_kind_compatible`，结果取更具体者；Mul：Scalar/Complex×X→X，Matrix(m,k)×Matrix(k,n)→Matrix(m,n)，Matrix(m,k)×Vector(k)→Vector(m)，Vector×Vector 与维数不符→`TYPE_MATHKIND_MISMATCH`；Div 分母须 Scalar/Complex；Dot 两侧同维 Vector→Scalar，被用作向量处→`TYPE_MATHKIND_MISMATCH`；Cross 两侧为 Vector(3) 或 Vector(None)→Vector(3)，已知维数≠3→`TYPE_CROSS_DIM`；None 维与具体维按 `math_kind_compatible`。

运算规则表（D_x 表示 x 的量纲表达式，结果均经 `Subst::resolve`；“同”表示与操作数相同）：

| 节点/函数 | 输入约束（违反时诊断） | 结果量纲 | 结果 MathKind |
| --- | --- | --- | --- |
| Binary Add/Sub、Relation（全部 RelOp） | 两侧合一（Angle 软约束；`TYPE_DIM_CONFLICT`） | Add/Sub 为合一结果；Relation 为 1 | Add/Sub 按上；Relation 为 Scalar |
| Binary Mul/Dot/Cross | Dot/Cross 见 MathKind | D_l·D_r | 见 MathKind |
| Binary Div | 分母 Scalar/Complex | D_l·D_r⁻¹ | 同分子 |
| Binary Pow | 指数须无量纲（`TYPE_FUNC_ARG_DIMENSIONED`）；指数为有理字面量 q（Number、其 Neg、或两个整数 Number 的 Div）时 | D_b^q；否则底数须无量纲，结果 1 | 方阵底数须整数字面量指数，否则同 Scalar |
| Unary Neg/Plus/Conjugate | — | 同 | 同 |
| Unary Transpose | Vector/Matrix | 同 | Matrix(m,n)→Matrix(n,m)；Vector(n)→Matrix(1,n) |
| Unary Factorial、floor、ceil、gcd、binom | 参数无量纲（`TYPE_FUNC_ARG_DIMENSIONED`） | 1 | Scalar |
| Unary Adjugate | 方阵（`TYPE_MATHKIND_MISMATCH`） | 阶 n 已知：D_A^(n−1)；未知：P_A·D_A⁻¹（P_A 见 det） | 同 |
| det(A)、\|A\|（方阵） | 方阵 | 阶 n 已知：D_A^n；未知：参数为矩阵符号与标量因子的乘积 Π f_i 时为 Π P_{f_i}，P_f 为每个因子符号首次出现时分配、同一检查内复用的变量；其他形状分配新变量 | Scalar |
| tr(A) | 方阵 | D_A | Scalar |
| sin cos tan cot sec csc、sinh cosh tanh | 参数无量纲（Angle 软约束；`TYPE_FUNC_ARG_DIMENSIONED`） | 1 | 同参数（Scalar/Complex） |
| arcsin arccos arctan | 参数无量纲（`TYPE_FUNC_ARG_DIMENSIONED`） | Angle | Scalar |
| exp | 参数无量纲（Angle 软约束；`TYPE_FUNC_ARG_DIMENSIONED`） | 1 | 同参数 |
| ln lg log(x[,b]) | x、b 无量纲（`TYPE_LOG_DIMENSIONED`） | 1 | Scalar |
| sqrt(x)、root(x,n) | n 须为正整数字面量，否则 x 须无量纲（`TYPE_FUNC_ARG_DIMENSIONED`） | D_x^(1/2)、D_x^(1/n) | 同 |
| abs、norm | — | D_x | Scalar（norm 接受 Vector/Matrix） |
| max、min（≥2 参数） | 各参数合一（`TYPE_DIM_CONFLICT`） | 合一结果 | 同 |
| P(event) | 参数为 Relation 或其逻辑组合 | 1 | Scalar |
| E(X)、Var(X)、Cov(X,Y) | — | D_X、D_X²、D_X·D_Y | Scalar |
| user:<名称>(args) | 参数不约束 | 同名函数在本次检查内共用一个新变量 D_f（与参数无关）；声明了量纲则取声明 | 声明或 Scalar |
| Derivative Ordinary/Partial | var 量纲（未声明则新变量） | D_target·D_var^(−order) | 同 target |
| Derivative Dot | — | D_target·T^(−order) | 同 target |
| Integral（各 kind） | 定积分上下限与唯一积分变量合一 | D_integrand·Π D_differential | 同 integrand |
| SumOrLimit Sum | 指标与上下限无量纲 | D_body | 同 body |
| SumOrLimit Product | 指标与上下限无量纲；body 须无量纲（`TYPE_FUNC_ARG_DIMENSIONED`） | 1 | 同 body |
| SumOrLimit Limit | 极限点（lower）与指标合一 | D_body | 同 body |
| Vector / Matrix | 全部元素合一（V1 不支持混合量纲矩阵） | 元素量纲 | Vector(Some(len)) / Matrix(Some(r),Some(c)) |
| Piecewise | 各值合一；条件按 Relation 检查 | 值的合一结果 | 各值 `math_kind_compatible` |

- 温度点（UnitKind::AffinePoint 的 Unit 或声明 kind 为 Temperature 的量）参与 Mul/Div/Pow 或两个点相加 → `TYPE_AFFINE_MISUSE`；点 − 点 = 差、点 + 差 = 点不报。
- typed 覆盖与取消：未取消时 typed 恒为 Some，按 `walk` 为每个节点给出一条（含 Invalid/Unresolved，冲突节点也给出 resolve 后的当前类型），按 NodePath 整数分量词典序。每处理 `CHECKPOINT_MS` 检查取消；已取消时返回 typed None、validation Unresolved、diagnostics 仅一条复用 CORE-06 的 `PARSE_TIMEOUT`（此时不按“存在 Error → Invalid”判定），CORE-56（下游说明，非契约）将其映射为 op 错误。
- 符号声明读取：`SymbolDecl.declared_type.dimension` 经 CORE-08 `DimensionFull::parse` 解析，失败按 `UNIT_DIM_SYNTAX` 诊断并使修订为 Unresolved；未声明量纲的符号引入量纲变量。
- `Hole` 节点按未知类型与量纲变量处理，不另报诊断（空位已由 `PARSE_HOLE_UNFILLED` 报告）；含 Hole 的结果状态至多为 Unresolved。
- 经验公式：标记 `empirical = true` 时系统推导使等式配平所需的系数量纲作为建议，用户接受或手工指定前状态为 Unresolved；未标记的经验公式不得跳过校验。
- 错误码（唯一定义；沿用原触发语义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `TYPE_DIM_CONFLICT` | error | 否 | 两侧量纲不可合一 |
| `TYPE_LOG_DIMENSIONED` | error | 否 | 对数参数带不允许的量纲 |
| `TYPE_FUNC_ARG_DIMENSIONED` | error | 否 | 函数、幂指数、开方次数或连乘 body 不满足本卡运算规则表的量纲约束 |
| `TYPE_MATHKIND_MISMATCH` | error | 否 | 运算的MathKind不兼容 |
| `TYPE_CROSS_DIM` | error | 否 | 叉积输入不是三维向量 |
| `TYPE_QK_MISMATCH` | warning | 否 | 量纲可合一而QuantityKind不匹配 |
| `TYPE_UNKNOWN_DIM` | warning | 否 | 未声明且合一后仍无法确定量纲，结果Unresolved |
| `TYPE_EMPIRICAL_COEFF` | warning | 否 | 经验公式系数或经验标记不足 |
| `TYPE_AFFINE_MISUSE` | error | 否 | 温度点用于本卡规则不允许的运算 |

CheckResult DTO 唯一形状为 `{typed?: {types:[[NodePath,TypeExpr],...]}, validation, diagnostics:Diagnostic[]}`。NodePath是CORE-05字符串；TypeExpr字段dimension?/quantity_kind?/math_kind/assumptions；DimExpr `{base: DimensionFull, vars:[[u32,Rational],...]}`；Rational统一为CORE-08的{num:string,den:string}已约分对象；DimensionFull统一为{base:{exps:[Rational×7]},pseudo:[["angle"或"count",Rational],...]}结构，不用量纲文本替代。TypeDecl.dimension的文本是单独输入字段，经parse转换后才进入此DTO。types按NodePath的整数分量词典序；不输出内部合一变量工作表。例：未绑定 x 的结果 `{"typed":{"types":[["",{"math_kind":"scalar","assumptions":[]}]]},"validation":"unresolved","diagnostics":[]}`（具体未绑定诊断在真实fixture补齐，不当已通过向量）。
`engine.check` 入参/编排归CORE-56；单位取同一EngineSnapshot（包含已打开档案User层），不另收用户单位数组；无档案使用Embedded+Pack。这样同一请求不会混用不同generation的单位与方案。

**实现约束**
- 量纲冲突以 `TYPE_DIM_CONFLICT` 定位到首个不可合一的子式；数学量不一律当作无量纲，未指定物理量的函数与变量引入量纲变量。
- 录入时可调整符号的量纲声明；入库后修改量纲声明生成新修订，依赖它的派生修订与卡片标记“待重校”（由 CORE-14（下游说明，非契约）执行，本卡只保证声明变化使诊断变化），旧修订保留。
- `check` 对 ≤256 节点 AST 的耗时计入 CORE-01 预算“量纲校验”行；解析另计“公式解析”行，两者合计由 CORE-56（下游说明，非契约）集成验收。
- 外部前提：运行依赖 `serde`（derive）；开发依赖 `proptest`、`serde_json`、YAML 夹具解析库（读取 dx.yaml）与支持 2020-12 的 JSON Schema 校验库，版本由首张使用卡按 ADR-V5-15 锁入 `Cargo.lock`。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-09_TEST.md](../Test/core/S1_CORE-09_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约590行，分阶段：①类型/声明、基础规则及递归推断320行；②扩展规则与多态/经验公式判定270行；主包crates/fml-type/src/{rules,infer,check}.rs及lib.rs接入；合一引擎与FFI编排分别归CORE-77/56，不计本卡。 阶段独立构建/测试：①基础推断（320行）：复用CORE-77，对基础表达式产生typed/诊断；扩展节点明确未实现，crate与基础用例可独立构建测试。；②完整规则与校验状态（270行）：补齐复杂节点、状态/经验建议，验证所有已声明规则和resolve自由变量不泄漏。

