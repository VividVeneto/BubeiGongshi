### CORE-18 三层判分器

**目标**：判定用户作答与标准式是否数学等价，结果只有正确、错误、无法判定三种，绝不猜测。

**范围**
- 包含：第一层规范 AST 比较、第二层数值抽样、第三层 Undetermined、必须形式检查、选择题与顺序题判定、单位按量纲等价判定。
- 不包含：识别转写（CORE-31，判分只接收用户确认后的文本）；评分映射（CORE-19）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-06、CORE-07、CORE-09、CORE-10

**接口契约**

```rust
// crates/fml-grade/src/lib.rs
pub enum Verdict { Correct, Incorrect { reason: IncorrectReason }, Undetermined { reason: String } }
pub enum IncorrectReason { NotEquivalent { witness: Option<SamplePoint> }, RequiredFormMissing, WrongChoice, WrongOrder, SigFigs }
pub enum GradeTarget {                       // 标准答案
    Expression { ast: FormulaNode, symbols: SymbolEnv },   // 表达式或方程（Relation 节点）
    Numeric { value: String /* 十进制字符串 */, unit: Option<UnitRef>, sig_figs: u8 },
    Choice { correct: Vec<u16> /* 选项下标，多选时升序 */ },
    Order { sequence: Vec<u16> },
}
pub enum GradeAnswer {                       // 用户作答；文本由 CORE-06 解析，失败返回 GRADE_PARSE_FAILED
    Latex(String), Numeric { text: String, unit: Option<String> }, Choice(Vec<u16>), Order(Vec<u16>),
}
pub enum RequiredForm { IntegrationConstant /* 不定积分须带 +C */, InTermsOf { functions: Vec<FunctionId> } /* 只允许出现这些函数 */,
                        NoNegativeExponent, Factored, Expanded }
pub struct SamplePoint { pub values: Vec<(SymbolId, f64)>, pub expected: f64, pub actual: f64 }
pub struct GradeRequest { pub expected: GradeTarget, pub answer: GradeAnswer,
                          pub notation_profile_id: String, pub required_form: Option<RequiredForm>,
                          pub seed: u64, pub budget_ms: u32 /* 默认 50 */ }
pub struct GradeResult { pub verdict: Verdict, pub layer: u8 /* 1|2|3 */, pub diagnostics: Vec<Diagnostic> }
pub fn grade(req: &GradeRequest, profile: &NotationProfile, units: &dyn UnitRegistry, cancel: &CancelFlag) -> GradeResult;
```

- FFI op：`grade.answer`。
- 层次：① 规范化后比较 AST（交换律/结合律排序只用于满足交换律的类型、常数折叠、移项、按记号方案的别名）；② 数值抽样（固定种子、在定义域内取点、避开奇点、相对容差；方程比较残差 lhs − rhs，常数倍视为等价；任一点不符即 Incorrect；无法抽样转第三层）；③ Undetermined：显示答案由用户自评，事件标记自评兜底，不计客观正确率。
- 必须形式（如不定积分须带 +C、指定用 sin x 表示）在等价判定之后检查。
- 抽样参数：每个自由变量按声明类型取值（实数默认在 [-10, 10]，正量或量纲量在 [0.1, 10]），用 `seed` 初始化的 ChaCha8 生成 16 个点；取值域以期望式为准：先在显式声明域内求期望式，期望式非有限或域非法的点丢弃重取；期望式有限而作答式非有限或域非法时立即 Incorrect（附域反例，如 GX-11 的 x<0）；因此 ln(ab) 与 ln a + ln b 这类只在未声明域上分歧的恒等式按期望式的域判定，不因作答侧多出的定义域误判；可求奇点时距离不足1e-6也重取，有效点少于 8 个转第三层；比较用相对容差 1e-9（期望绝对值 < 1e-12 时用绝对容差 1e-12）；方程以残差 lhs − rhs 比较，两边残差之比在全部点上为同一非零常数视为等价。
- 选择题与顺序题直接比较下标序列；数值题按 `sig_figs` 修约后比较，单位经 CORE-08 换算到标准单位后比较。
- 错误码（触发条件）：`GRADE_PARSE_FAILED`（作答文本无法解析，GradeResult为Undetermined(parse_failed)，先提示用户修改，不记事件）、`GRADE_TIMEOUT`（超过 `budget_ms`，结果转 Undetermined）、`GRADE_UNSUPPORTED`（`GradeTarget` 与 `GradeAnswer` 种类不匹配，或包含本判分器不支持的节点，如极限、无穷级数，转 Undetermined）。
- 外部前提：随机数 `rand_chacha` crate，版本按 ADR-V5-15 由首张使用卡开工时锁入 `Cargo.lock`。

所需输入为 GradeRequest、标准符号环境与记号方案（由处理层解析）、UnitRegistry、CancelFlag；数值样本和形式要求由req决定。GX-11/12 在随机采样前固定注入允许域中的 -2,-1,1,2 四点（仍受声明域筛选），保证不会因固定 seed 恰好全正而漏反例；x>0声明域时两式等价可判Correct。

模糊 GX 项的具体参照输入：GX-02 a*x+b=0 对 x=-b/a（a≠0）；GX-04 Var=E2-E1²（中文方案绑定其定义，ISO 未绑定保留歧义）；GX-05 0.5*m*v² 对 m*v²；GX-06 a+b 对 a-b；GX-07 a/(b+c) 对 a/b+c；GX-08 a/b 对 b/a；GX-09 ∫x dx 的答案 x²/2 缺+C；GX-10 要求含sin时给cos(π/2-x)，等价但RequiredFormMissing；GX-13 A=[[1,1],[0,1]],B=[[1,0],[1,1]] 的乘积转置；GX-14 含未在白名单的Gamma，不调用CAS代答，返回Undetermined。输入域按上述明确条件设定，不能拿复数域NaN去冒充实数答案。

作答符号绑定：LaTeX解析后用期望 SymbolEnv 的符号名与请求 notation_profile_id 的别名映射到既有 SymbolId，不按作答出现顺序重编号；未知符号只产生诊断并返回 Undetermined，不擅自新建量纲。纯grade还需调用方显式传入 `profile: &NotationProfile`，FFI从同一引擎快照解析ID。
`grade.answer` body=GradeRequest、ok=GradeResult（call）；GradeTarget/Answer/RequiredForm采用CORE-03外部tag蛇形；例 body=`{"expected":{"choice":{"correct":[1]}},"answer":{"choice":[1]},"notation_profile_id":"cn-default","seed":1,"budget_ms":50}`，ok=`{"verdict":"correct","layer":1,"diagnostics":[]}`。解析失败在GradeResult返回 `Undetermined{reason:"parse_failed"}`、diagnostics含GRADE_PARSE_FAILED，界面提示修正且不记录事件；不是先返回Incorrect再提示。超时同样成功返回Undetermined且带GRADE_TIMEOUT。

**实现约束**
- 判分不得读取识别置信度、量纲检查结果或识别成功与否；“识别成功”与“量纲通过”都不等于答对。
- 矩阵等不满足交换律的 MathKind 不得使用交换律规范化。
- 数值作答按题目要求的有效数字与标准值修约一致即正确，有效数字不足判错并提示。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-18_TEST.md](../Test/core/S4_CORE-18_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 480 行；主包 `crates/fml-grade/`（约 460：类型、分派与预算、作答绑定、规范化比较、数值抽样、必须形式、数值与单位判定），附属 `crates/fml-ffi/src/ops/grade.rs`（grade.answer 处理约 20）。二级分界：数值有效数字与单位换算（约 45），编码超出时移出。

