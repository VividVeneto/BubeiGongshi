### CORE-10 计算器与数值求解

**目标**：对已校验的公式做带单位的直接求值、受限符号反解与区间数值求根，输出值、单位、有效数字与来源说明。

**范围**
- 包含：直接求值、可逆运算链的符号反解、Brent 法求根、有效数字修约、不确定度区间传播、常数自动填入、相容单位列表、计算限额。
- 不包含：公式间代入与计算链（CORE-11）；计算器界面（CORE-38）。积分、极限等 V1 不计算的结构只返回“不可计算”原因。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-07、CORE-08、CORE-09

**接口契约**

```rust
// crates/fml-eval/src/lib.rs
pub struct Assignment { pub symbol: SymbolId, pub value: String /* 十进制文本 */, pub unit: String,
                        pub uncertainty: Option<String> /* 同单位的绝对不确定度 */ }
pub enum SolveMethod { Direct, Symbolic, Numeric { lower: String, upper: String } }
pub struct CalcRequest { pub revision_ast: FormulaNode, pub symbols: SymbolEnv, pub typed: TypedAst,
                         pub assignments: Vec<Assignment>, pub target: SymbolId, pub output_unit: Option<String>,
                         pub interval: Option<(String, String)>, pub given_constants: Vec<ConstantValue>,
                         pub display: DisplayPrecision /* LeastSigFigs | Full | Fixed(3..=10) */ }
pub struct CalcResult { pub value: String, pub unit: String, pub sig_figs: u8,
                        pub uncertainty_interval: Option<(String, String)>,
                        pub method: SolveMethod, pub residual: Option<String>,
                        pub branches: Vec<FormulaNode> /* 多值反解时的各支 */,
                        pub constants_used: Vec<ConstantValue>, pub diagnostics: Vec<Diagnostic> }
pub fn evaluate(req: &CalcRequest, units: &dyn UnitRegistry, cancel: &CancelFlag) -> Result<CalcResult, FmlError>;
pub fn solvable_targets(ast: &FormulaNode, typed: &TypedAst) -> Vec<(SymbolId, SolveCapability)>;
pub enum DisplayPrecision { LeastSigFigs /* 默认 */, Full, Fixed(u8) /* 3..=10 位有效数字 */ }
pub enum SolveCapability { Direct /* 目标在等号左侧单独出现 */, Symbolic, NumericOnly, NotComputable(String /* 原因消息键 */) }
```

- FFI op：`calc.evaluate`（同步，支持 `budget_ms`，默认 200）、`calc.solvable_targets`（同步）的 DTO 与处理编排由 CORE-56 登记：请求携带源码，处理层在同一引擎快照上重跑 parse → bind → check 后构造 `CalcRequest`；本卡只提供上面的纯函数。
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

- 错误码（唯一定义；沿用原触发语义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `EVAL_DIV_ZERO` | error | 否 | 除数为0 |
| `EVAL_DOMAIN` | error | 否 | 实数域外：负数开偶次方、非正数取对数、反三角越界 |
| `EVAL_NAN_OR_INF` | error | 否 | 中间或结果非有限值 |
| `EVAL_OVERFLOW` | error | 否 | 绝对值大于1e308 |
| `EVAL_NO_CONVERGE` | error | 否 | Brent迭代200次未收敛 |
| `EVAL_NEEDS_INTERVAL` | error | 否 | 自动bracket未找到变号区间 |
| `EVAL_NOT_COMPUTABLE` | error | 否 | 含积分/极限、未Verified或MathKind不支持 |
| `EVAL_LIMIT_EXCEEDED` | error | 否 | 超过CORE-05 limits |
| `EVAL_TIMEOUT` | error | 是 | 超过budget_ms或取消 |
| `EVAL_MULTI_BRANCH` | info | 否 | 返回各个数值分支 |

**实现约束**
- 只计算 Verified/VerifiedPolymorphic（实例化后）的修订；V1 可计算 MathKind 为 Scalar、基础 Complex、Vector、Matrix。
- 不使用 eval、动态语言、反射；函数白名单固定；节点数、递归深度、步数受 CORE-05 `limits` 约束，每 100 ms 检查取消。
- 求根流程：先尝试符号反解；失败时要求物理合理区间；未给区间时自动 bracket；仍失败返回明确错误，不静默给可疑数值；结果标注“数值解”并给出区间与残差。
- 输出默认按最少有效数字修约，可切换全精度或固定 3–10 位；中间计算不修约。带不确定度的输入按一阶误差传播显示区间；不做统计推断。
- 常数由 CORE-56 在 FFI 处理层按 CORE-07 resolve_constant 解析后注入 given_constants（已解析的完整常数集合）；fml-eval 只消费 CORE-05 的 ConstantValue，不调用记号层。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-10_TEST.md](../Test/core/S1_CORE-10_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 500 行；`crates/fml-eval/`。

