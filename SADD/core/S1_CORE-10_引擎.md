### CORE-10 直接求值与数值内核

**目标**：对已校验的公式做带单位的直接求值（完整反解/求根门面迁CORE-93），输出值、单位、有效数字与来源说明。

**范围**
- 包含：直接求值、有效数字修约、不确定度区间传播、常数自动填入、相容单位列表、计算限额。
- 不包含：受限符号反解、Brent求根、完整evaluate/solvable_targets（CORE-93）；公式间代入与计算链（CORE-11）；计算器界面（CORE-38）。积分、极限等 V1 不计算的结构只返回“不可计算”原因。

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
pub fn evaluate_direct(req: &CalcRequest, units: &dyn UnitRegistry, cancel: &CancelFlag) -> Result<CalcResult, FmlError>;
pub fn direct_targets(ast: &FormulaNode, typed: &TypedAst) -> Vec<(SymbolId, SolveCapability)>;
pub enum DisplayPrecision { LeastSigFigs /* 默认 */, Full, Fixed(u8) /* 3..=10 位有效数字 */ }
pub enum SolveCapability { Direct /* 目标在等号左侧单独出现 */, Symbolic, NumericOnly, NotComputable(String /* 原因消息键 */) }
```

- 完整evaluate/solvable_targets唯一实现迁CORE-93；本卡evaluate_direct只接受直接可解目标，其余返回EVAL_NOT_COMPUTABLE并给原因；direct_targets只报告Direct/NotComputable，不调用求解层。共享请求/结果/枚举仍由本卡定义。
- FFI op：`calc.evaluate`（同步，支持 `budget_ms`，默认 200）、`calc.solvable_targets`（同步）的 DTO 与处理编排由 CORE-56 登记：请求携带源码，处理层在同一引擎快照上重跑 parse → bind → check 后构造 `CalcRequest`；本卡只提供上面的纯函数。
- 数值约定：直接求值用f64，单位系数用CORE-08精确有理数，只在输出修约；有效数字取输入最少者（整数末尾0有效）；不确定度按一阶偏导绝对值和（最坏情况）传播。CORE-93单向消费本卡内核，其Brent/自动bracket参数与分支规则见该卡。
- 直接计算向量：CX-01、02、06、07、08、10保留原期望；全部CX-01～10原始表移CORE-93，供集成与两层边界对照；本卡不负责反解/求根期望。

- 错误码（唯一定义；沿用原触发语义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `EVAL_DIV_ZERO` | error | 否 | 除数为0 |
| `EVAL_DOMAIN` | error | 否 | 实数域外：负数开偶次方、非正数取对数、反三角越界 |
| `EVAL_NAN_OR_INF` | error | 否 | 中间或结果非有限值 |
| `EVAL_OVERFLOW` | error | 否 | 绝对值大于1e308 |
| `EVAL_NOT_COMPUTABLE` | error | 否 | 含积分/极限、未Verified或MathKind不支持 |
| `EVAL_LIMIT_EXCEEDED` | error | 否 | 超过CORE-05 limits |
| `EVAL_TIMEOUT` | error | 是 | 超过budget_ms或取消 |

**实现约束**
- 只计算 Verified/VerifiedPolymorphic（实例化后）的修订；V1 可计算 MathKind 为 Scalar、基础 Complex、Vector、Matrix。
- 不使用 eval、动态语言、反射；函数白名单固定；节点数、递归深度、步数受 CORE-05 `limits` 约束，每 100 ms 检查取消。
- 只计算直接目标；完整求根与多值反解由CORE-93调用本卡内核，不在本卡分派或反向依赖。
- 输出默认按最少有效数字修约，可切换全精度或固定 3–10 位；中间计算不修约。带不确定度的输入按一阶误差传播显示区间；不做统计推断。
- 常数由 CORE-56 在 FFI 处理层按 CORE-07 resolve_constant 解析后注入 given_constants（已解析的完整常数集合）；fml-eval 只消费 CORE-05 的 ConstantValue，不调用记号层。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-10_TEST.md](../Test/core/S1_CORE-10_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约730行，分阶段：①共享模型50、Scalar180、赋值/单位消费90、修约60、限额编排50，共430行；②基础Complex/Vector/Matrix200及最坏不确定度传播100，共300行。主包 `crates/fml-eval/` 的直接求值内核；FFI归CORE-56不计；向量/数据/生成物/自测不计。①验证Scalar独立构建与错误边界，②验证全部V1 MathKind/不确定度独立构建。原1060行另330行归CORE-93。

