### CORE-93 受限反解与区间数值求根

**目标**：在CORE-10纯直接求值内核上完成可逆链反解、Brent求根与完整计算门面。

**范围**
- 包含：目标能力分析、多值符号反解、自动bracket/区间Brent、残差/分支与方法标记；完整evaluate/solvable_targets分派接入。
- 不包含：共享计算模型、直接Scalar/Complex/Vector/Matrix、单位/修约/不确定度内核（CORE-10）；FFI parse→bind→check（CORE-56）；计算链（CORE-11）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-09、CORE-10

**接口契约**

```rust
// crates/fml-eval/src/lib.rs；共享CalcRequest/CalcResult/SolveCapability等仍定义在CORE-10
pub fn evaluate(req: &CalcRequest, units: &dyn UnitRegistry, cancel: &CancelFlag) -> Result<CalcResult, FmlError>;
pub fn solvable_targets(ast: &FormulaNode, typed: &TypedAst) -> Vec<(SymbolId, SolveCapability)>;
// CO-28 新增（CORE-11 R11-01 变更单）：公开 evaluate 内部的同一符号反解步骤，不含数值
pub fn isolate(ast: &FormulaNode, typed: &TypedAst, target: SymbolId, cancel: &CancelFlag) -> Result<Vec<FormulaNode>, FmlError>;
```

`isolate`：ast 须为根 `Relation{op: Eq}`；target 单独构成一侧时返回 `[另一侧]`；否则沿与 evaluate 相同的可逆运算链（Add/Sub/Neg/Mul/Div、整数字面量指数的 Pow、sqrt/root、exp↔ln）把 target 化为单独一侧，返回各分支表达式：偶次幂/偶次根产生两支，顺序固定为“正支（主值）在前、负支（外包一层 Neg）在后”，与 `CalcResult.branches` 次序一致；结果只做构造、不做代数化简，target 不出现在返回式中。target 在等式两侧都出现、不在可逆链上或 `solvable_targets` 对它不是 Symbolic 时返回 `EVAL_NOT_COMPUTABLE`；取消返回 `EVAL_TIMEOUT`；节点超限返回 `EVAL_LIMIT_EXCEEDED`。evaluate 的符号步骤必须调用同一函数，不得两套实现。

本卡单向调用CORE-10 evaluate_direct/direct_targets。完整门面供CORE-56 calc.evaluate/calc.solvable_targets和CORE-11消费；CORE-10不得反向调用本卡。calc.*的DTO与FFI处理仍属CORE-56，不在此重复登记。

- 数值约定：求值用 f64，单位系数用 CORE-08 精确有理数，只在输出时修约；有效数字按输入中最少者（整数末尾 0 视为有效）；Brent 法相对容差 1e-12、最多 200 次迭代；自动 bracket 先正侧、后负侧，每侧按绝对值从小到大扫描 x_i = ±10^(-12 + 24*i/199)，i=0..199（每侧200点，含端点）；仅比较同侧相邻有限函数值，跳过非有限点且不跨越该点连区间，精确零立即返回，首个异号相邻对按数值升序作为区间；两侧之间不跨零连区间，未发现则 EVAL_NEEDS_INTERVAL；不确定度用一阶偏导绝对值和（最坏情况）传播。
- 计算向量（`tests/fixtures/calc/cx.yaml`）：

| 编号 | 公式与输入 | 期望 |
| --- | --- | --- |
| CX-01 | F = ma，m = 2 kg，a = 3 m/s² | F = 6 N，sig_figs 1，method Direct |
| CX-02 | v = s/t，s = 100.0 m，t = 9.58 s，输出 km/h | 37.6 km/h，sig_figs 3 |
| CX-03 | v = s/t，求 t，v = 10.0 m/s，s = 100. m | t = 10.0 s，method Symbolic |
| CX-04 | x² = a，求 x，a = 4 | 两支 ±2，返回 `EVAL_MULTI_BRANCH`（Info） |
| CX-05 | x² = a，求 x，a = −1（Scalar 实数） | `EVAL_DOMAIN` |
| CX-06 | y = 1/x，x = 0 | `EVAL_DIV_ZERO` |
| CX-07 | E = mc²，m = 1 g，输出 J（c 取 exact） | 9e13 J，`constants_used` 含 c 的 exact 来源与版本 |
| CX-08 | v = s/t，s = 100.0 ± 0.1 m，t = 10.00 ± 0.01 s | v = 10.00 m/s，区间 [9.98, 10.02] |
| CX-09 | x·eˣ = 1，求 x，无区间 | 数值解 0.567143…，残差 < 1e-12，method Numeric |
| CX-10 | ∫₀¹ x dx 求值 | `EVAL_NOT_COMPUTABLE`，原因“含积分” |


| 错误码（本卡唯一定义） | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `EVAL_NO_CONVERGE` | error | 否 | Brent迭代200次未收敛 |
| `EVAL_NEEDS_INTERVAL` | error | 否 | 自动bracket未找到变号区间 |
| `EVAL_MULTI_BRANCH` | info | 否 | 返回各个数值分支 |

直接求值错误EVAL_DIV_ZERO/EVAL_DOMAIN/EVAL_NAN_OR_INF/EVAL_OVERFLOW/EVAL_NOT_COMPUTABLE/EVAL_LIMIT_EXCEEDED/EVAL_TIMEOUT唯一归CORE-10，本卡透传，不重复定义。

**实现约束**
- 先尝试符号反解；失败时使用用户给定物理合理区间；未给区间按上述固定次序自动bracket；失败明确报错，不静默给可疑值；数值结果标注method Numeric、区间和残差。
- 只计算Verified/VerifiedPolymorphic实例化后修订，支持范围沿CORE-10；每100ms检查取消，节点/深度/步数受CORE-05 limits约束；禁止eval/动态语言/反射。
- 多值根返回全部分支；Scalar实数域外拒绝。中间不修约，输出精度与最坏情况不确定度复用CORE-10，不另定口径。
- 常数已由CORE-56按CORE-07解析并注入given_constants；本卡不调用记号层。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-93_TEST.md](../Test/core/S1_CORE-93_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约345行；主包 `crates/fml-eval/src/{symbolic,solve}.rs`（反解/能力180、公开 isolate 封装15、bracket/Brent150，含完整分派接入）；无本卡FFI附属。向量/生成物/自测不计；单阶段以直接内核+求解层独立构建、全部CX集成测试交付。
