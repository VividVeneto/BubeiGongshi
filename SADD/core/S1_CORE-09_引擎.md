### CORE-09 类型推断与量纲校验

**目标**：对绑定后的 AST 推导量纲、QuantityKind 与数学结构，给出带定位的诊断和修订的校验状态，支持数学公式的量纲多态。

**范围**
- 包含：运算规则表、`Validation` 判定、经验公式处理、纯函数 check（infer → 调用 CORE-77 `unify` → 诊断）；FFI 编排由 CORE-56 交付。
- 已拆出：`DimVar`、`DimExpr`、`TypeExpr` 与合一（unification）由 CORE-77 交付（本卡原规模约 500 行另计规则表 150 行，超出先拆卡约定）。
- 不包含：数值计算（CORE-10）；代入（CORE-11）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-06、CORE-07、CORE-08、CORE-77

**接口契约**

```rust
// crates/fml-type/src/rules.rs、infer.rs（crate 骨架归 CORE-77，本卡追加 mod 声明）
// DimVar、DimExpr、TypeExpr 与 unify/Subst 定义见 CORE-77（crates/fml-type/src/dim.rs），本卡 use 之，不重复定义
// MathKind、Validation、TypeDecl 定义见 CORE-05
pub struct TypedAst { pub types: Vec<(NodePath, TypeExpr)> }
pub struct CheckResult { pub typed: Option<TypedAst>, pub validation: Validation, pub diagnostics: Vec<Diagnostic> }

pub fn check(ast: &FormulaNode, env: &SymbolEnv, units: &dyn UnitRegistry, empirical: bool,
             cancel: &CancelFlag) -> CheckResult;
pub fn infer_slot(ast: &FormulaNode, typed: &TypedAst, slot: &NodePath) -> Option<TypeExpr>; // 供 CORE-11
```

- 所需输入：已解析 AST、已绑定 SymbolEnv、UnitRegistry、empirical 与 CancelFlag；本 crate 不依赖解析器。FFI 管线契约由 CORE-56 定义。
- 校验状态规则：存在 Error → Invalid；有未绑定符号、Unknown 量纲或未确认的 Warning → Unresolved；全部通过 → Verified 或 VerifiedPolymorphic。只有 Verified 与 VerifiedPolymorphic 的修订可计算、可代入、可出卡。Unknown 不等于多态。
- 诊断分级与 UI 行为：Error（量纲不匹配、向量结构错误、温度点乘除）阻止保存并高亮节点；Warning（同量纲不同 QuantityKind、经验公式未设系数）允许保存但须确认（`needs_confirm`）；Info（建议单位、有效数字、可简化）只提示。
- 运算规则（规则表在 `crates/fml-type/src/rules.rs`）：加减与关系两侧合一；乘除相乘/相除；幂与根有理指数；导数 D_f·D_x^-k；积分 D_f·D_x；det(A) 为 D_Aⁿ、伴随元素 D_Aⁿ⁻¹；极限、∇/散度/旋度按场类型；sin/cos 参数须为 Angle 或无量纲；exp/log 参数须无量纲；概率无量纲，密度为 D_X⁻¹；点积输出标量，叉积要求三维。
- 与 CORE-77 的衔接（T1-F03/F05/F08）：①DimVar 分配顺序固定——检查开始时用 `Subst::fresh` 按 `SymbolId` 升序为未声明量纲的符号各分配一个，再在 AST 先序遍历中为需要的子式补分配；②`unify` 返回 `DimConflict` 时诊断为 `TYPE_DIM_CONFLICT`，参数 left/right 用 `DimExpr::to_text()`，定位首个不可合一子式后继续检查其余子式（Subst 在 Err 后保持不变）；返回 `Overflow` 时诊断为 `UNIT_OVERFLOW`（error，结果 Invalid）；③“sin/cos 参数须为 Angle 或无量纲”先对 `Subst` 的克隆试探合一 Angle，失败再试无量纲，都失败才报 `TYPE_FUNC_ARG_DIMENSIONED`；④`VerifiedPolymorphic.vars` 取最终结果中 `free_vars()` 的编号（升序），`constraints` 取 `Subst::bindings()` 中涉及这些变量的绑定的文本（`变量 = 表达式`，按变量升序）；⑤MathKind 相容判定归本卡 `rules.rs` 的 `pub fn math_kind_compatible(a: &MathKind, b: &MathKind) -> bool`：同种相容；`Vector(None)` 与 `Vector(Some(n))`、`Matrix` 的 `None` 维与具体维相容，具体维数不同则不相容；`TYPE_MATHKIND_MISMATCH` 与 CORE-11 的 `DERIVE_TYPE_MISMATCH` 共用它；⑥输出 `TypedAst` 前对每个 `TypeExpr.dimension` 调 `Subst::resolve`，typed 中的量纲只含自由变量（`Subst` 不持久化，未 resolve 的绑定变量在跨修订使用时会被 CORE-77 的 `instantiate*` 当作独立自由变量），且 typed 中出现的全部变量 ⊆ `VerifiedPolymorphic.vars`；⑦`fresh` 分配总数 ≤ 符号数 + 节点数（各 ≤ 4096），与 CORE-77 的上界说明一致。
- 符号声明读取：`SymbolDecl.declared_type.dimension` 经 CORE-08 `DimensionFull::parse` 解析，失败按 `UNIT_DIM_SYNTAX` 诊断并使修订为 Unresolved；未声明量纲的符号引入量纲变量。
- `Hole` 节点按未知类型与量纲变量处理，不另报诊断（空位已由 `PARSE_HOLE_UNFILLED` 报告）；含 Hole 的结果状态至多为 Unresolved。
- 经验公式：标记 `empirical = true` 时系统推导使等式配平所需的系数量纲作为建议，用户接受或手工指定前状态为 Unresolved；未标记的经验公式不得跳过校验。
- 错误码（唯一定义；沿用原触发语义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `TYPE_DIM_CONFLICT` | error | 否 | 两侧量纲不可合一 |
| `TYPE_LOG_DIMENSIONED` | error | 否 | 对数参数带不允许的量纲 |
| `TYPE_FUNC_ARG_DIMENSIONED` | error | 否 | 函数参数不满足本卡运算规则的量纲约束 |
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
- 录入时可调整符号的量纲声明；入库后修改量纲声明生成新修订，依赖它的派生修订与卡片标记“待重校”（由 CORE-14 执行），旧修订保留。
- 解析 + 量纲校验总耗时计入 CORE-01 预算。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-09_TEST.md](../Test/core/S1_CORE-09_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约590行，分阶段：①类型/声明、基础规则及递归推断320行；②扩展规则与多态/经验公式判定270行；主包crates/fml-type/src/{rules,infer,check}.rs及lib.rs接入；合一引擎与FFI编排分别归CORE-77/56，不计本卡。 阶段独立构建/测试：①基础推断（320行）：复用CORE-77，对基础表达式产生typed/诊断；扩展节点明确未实现，crate与基础用例可独立构建测试。；②完整规则与校验状态（270行）：补齐复杂节点、状态/经验建议，验证所有已声明规则和resolve自由变量不泄漏。

