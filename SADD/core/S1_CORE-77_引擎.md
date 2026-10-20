### CORE-77 量纲变量与合一

**目标**：提供公式量纲多态所需的量纲变量表达式、类型表达式与合一算法，使 CORE-09（下游说明，非契约）只负责运算规则与诊断，不与合一实现耦合。本卡自 CORE-09（下游说明，非契约）拆出。类型三层见附录A A4（Dimension 决定合法性、QuantityKind 决定物理语义、MathKind 决定结构约束），本卡只实现 Dimension 层的量纲变量与合一，`TypeExpr` 只承载另两层的值。

**范围**
- 包含：`fml-type` crate 骨架（`Cargo.toml`、最小 `lib.rs`、crate README；CORE-09（下游说明，非契约）在其上追加模块）、`DimVar`、`DimExpr`、`TypeExpr`、代换 `Subst`、`unify`、跨来源实例化（`instantiate`/`instantiate_all`/`instantiate_types`）、乘/幂/逆与规范化、文本化与内省、确定性变量选取。
- 不包含：运算规则表、诊断、`Validation` 判定、经验公式与 MathKind 相容判定（CORE-09（下游说明，非契约））；基础量纲、`Rational` 与 `DimensionFull` 运算（CORE-08）；`MathKind`（CORE-05）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-08

**接口契约**

```rust
// crates/fml-type/src/dim.rs（crate 根 lib.rs：#![forbid(unsafe_code)] #![deny(missing_docs)]，pub mod dim; pub use dim::*;）
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]   // serde transparent：JSON 为裸 u32
pub struct DimVar(pub u32);                      // 量纲变量 D_f、D_x ……
#[derive(Clone, Debug, PartialEq, Eq)]           // serde：{base, vars:[[u32,Rational],…]}
pub struct DimExpr { pub base: DimensionFull, pub vars: Vec<(DimVar, Rational)> }  // Π base^q · Π D_j^r；规范形：vars 按 DimVar 升序、无零指数
#[derive(Clone, Debug, PartialEq, Eq)]           // serde：dimension?/quantity_kind? 缺省省略
pub struct TypeExpr { pub dimension: Option<DimExpr> /* None = Unknown */, pub quantity_kind: Option<String>,
                      pub math_kind: MathKind, pub assumptions: Vec<String> }
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Subst { /* 内部合一工作表：不可序列化，不进 DTO；Clone 用于试探合一 */ }
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum UnifyError { DimConflict { left: DimExpr, right: DimExpr }, Overflow(FmlError) }   // Overflow 恒为 UNIT_OVERFLOW；DimConflict 对应 CORE-09（下游说明，非契约）的 TYPE_DIM_CONFLICT
impl DimExpr {
    pub fn new(base: DimensionFull, vars: Vec<(DimVar, Rational)>) -> Result<DimExpr, FmlError>;   // 规范化：合并同号、去零指数、排序
    pub fn one() -> Self;  pub fn from_base(b: DimensionFull) -> Self;  pub fn var(v: DimVar) -> Self;
    pub fn mul(&self, o: &DimExpr) -> Result<DimExpr, FmlError>;       // 指数相加，返回规范形
    pub fn pow(&self, q: &Rational) -> Result<DimExpr, FmlError>;      // 指数相乘
    pub fn inverse(&self) -> Result<DimExpr, FmlError>;
    pub fn is_one(&self) -> bool;  pub fn is_ground(&self) -> bool;    // is_ground：vars 为空
    pub fn free_vars(&self) -> Vec<DimVar>;                            // 升序
    pub fn to_text(&self) -> String;                                   // 规范文本，文法见下“文本化”；`impl Display` 同
}
impl Subst {
    pub fn new() -> Self;  pub fn fresh(&mut self) -> DimVar;           // 编号从 0 单调递增（u32 计数器）；分配总数上界见下“变量作用域”，远小于 u32::MAX，故不设错误返回（计数器耗尽才 panic，任何合法输入不可达）
    pub fn resolve(&self, e: &DimExpr) -> Result<DimExpr, FmlError>;    // 应用全部代换后返回规范形
    pub fn bindings(&self) -> Vec<(DimVar, DimExpr)>;                   // 按变量升序
    pub fn instantiate_all(&mut self, es: &[&DimExpr]) -> Vec<DimExpr>;      // 把 es 中全部变量换成本 Subst 新分配的变量：同一次调用内同号映射同一新变量，映射只在本次调用内有效；按 es 顺序、每个表达式内变量升序首次出现的次序分配；单射改名，指数不变，不会失败；输出与 es 一一对应且为规范形
    pub fn instantiate(&mut self, e: &DimExpr) -> DimExpr;                    // 等价于 instantiate_all(&[e])[0]
    pub fn instantiate_types(&mut self, ts: &[TypeExpr]) -> Vec<TypeExpr>;    // ts 中全部 dimension 共用一次 instantiate_all 的映射，其余字段原样；None 维度保持 None
}
pub fn unify(a: &DimExpr, b: &DimExpr, s: &mut Subst) -> Result<(), UnifyError>;
```

- 运算全部经 CORE-08 的 `Rational::checked_*` 与 `DimensionFull::{one, checked_mul, inverse, pow}`（本卡不重复实现指数算术；CORE-08 已补这些函数与规范形）。
- 语义：`DimExpr` 是有理指数下的交换群元素。`unify(a, b)` 先 `resolve` 两侧，再化为 `c = a·b⁻¹ = 1`：无变量时 `c.base` 必须等于 `DimensionFull::one()`（Angle、Count 不等价于无量纲），否则 `DimConflict`；有变量时取编号最小且指数 `r ≠ 0` 的变量 `D`，令 `D = (其余因子)^(−1/r)`，写入绑定并对已有绑定做代入以保持 `Subst` 幂等（任何绑定的右侧都不含已绑定变量；右侧变量编号必大于被绑定变量，天然无环，无需 occurs 检查）。选取规则固定为最小编号，使结果与参数顺序和运行次数无关。
- 失败原子性：`unify` 先在副本上完成全部计算，成功才提交；任何 `Err`（冲突或中途溢出）都不改变 `Subst`。`DimConflict` 携带 `resolve` 后的 `a`、`b`（调用时的两侧，不是约去共同因子后的值）。
- 变量作用域与跨来源协议：`DimVar` 编号只在产生它的 `Subst` 内有意义。持久化在修订中的 `vars`（CORE-05 `Validation::VerifiedPolymorphic`）只表示“该修订多态”；持久化或传入的 typed 不携带 `Subst`，其中每个 `TypeExpr.dimension` 都是 `resolve` 后的规范形、只含自由变量（由 CORE-09（下游说明，非契约）输出时保证；`instantiate*` 的输入应为这种表达式）。把来自不同修订或不同 `check` 的 typed 放在一起合一时（CORE-11（下游说明，非契约）的槽位合一、候选排序），必须：① 新建 `Subst::new()`；② 对**每一份**来源各调用一次 `instantiate_types`（或 `instantiate_all`），把该来源本次要用到的全部类型一次传入，使同一来源内同号变量映射到同一新变量、不同来源的变量互不相交；③ 之后只用实例化结果调用 `unify`。不得只实例化其中一侧：各来源编号都从 0 起，未实例化一侧的变量会与新分配的变量重号而被误合一。`fresh` 分配总数上界：CORE-09 单次 `check` ≤ 符号数（≤ 4096）+ 节点数（≤ 4096）；一次跨来源合一 ≤ 各来源自由变量数之和；均远小于 `u32::MAX`。
- 文本化（`to_text`/`Display`，供 CORE-09（下游说明，非契约）的诊断参数与 constraints）：因子以单个空格分隔，与 CORE-08 量纲文本语法一致。先写基础部分 `DimensionFull::to_text()`（CORE-08 规范文本），基础部分为 `1` 且 `vars` 非空时省略；再按 `DimVar` 升序写变量因子 `D<n>`（n 为 `DimVar` 原值的十进制），指数 1 省略，否则写 `^<p>` 或 `^<p>/<q>`（与 CORE-08 指数写法相同，负号紧随 `^`）；整体为单位元时写 `1`。黄金文本：base = `L`、vars = [(D1, −1)] → `L D1^-1`；base = `1`、vars = [(D0, 1), (D2, 1/2)] → `D0 D2^1/2`；base = `L M T^-2`、vars 为空 → `L M T^-2`；单位元 → `1`。该文本只用于显示与诊断，不作为可解析格式。
- 溢出：任何指数运算溢出返回 `UNIT_OVERFLOW`（`FmlError`），不 panic、不回绕；`unify` 中以 `Overflow` 返回。本卡不新增错误码；`TypeExpr`/`DimExpr` 的 JSON 形状由本卡 serde 派生给出，`types.schema.json` 为其机器镜像，CORE-09（下游说明，非契约）的 CheckResult DTO 段引用之。反序列化经 `DimExpr::new` 规范化：非规范但可表示的输入（乱序、零指数、同号重复）规范化后接受；同号合并溢出时反序列化失败（serde 自定义错误，FFI 适配按 CORE-03 映射为 `FFI_BAD_ARG`）。`TypeExpr`、`UnifyError` 的 derive 依赖 CORE-05 `MathKind`、CORE-08 `PseudoDim`/`DimensionFull`、CORE-02 `FmlError` 已声明的 derive 与 serde 约定；`UNIT_OVERFLOW` 的 `FmlError` 用 CORE-02 `FmlError::new(ErrorCode::UnitOverflow)` 构造（trace_id 为零值，由调用用例填入）。

**实现约束**
- 纯函数，无 I/O、无浮点；`#![forbid(unsafe_code)]`；依赖仅 `fml-ast`（`MathKind`）、`fml-units`（`Rational`、`DimensionFull`）与 `fml-error`（通用例外，CORE-01 规则 1）。
- 代换内部结构不得出现在公共 API 或 DTO；`bindings()` 只读视图。
- 外部前提：`serde`（derive 特性）；dev-dependency：属性测试库 `proptest`、`serde_json`、JSON Schema 2020-12 校验库（须能注册 CORE-67 的 `int128`/`positive-int128` 自定义 format）；版本均由首张使用卡按 ADR-V5-15 锁入 `Cargo.lock`；`rust-toolchain.toml` 由 CORE-01 锁定。

**验收标准**
- [R13] 单元：`unify(D_f·D_x, L²)`（`D_f` 编号小于 `D_x`）解得 `D_f = L²·D_x⁻¹`；`unify(D_f², L)` 解得 `D_f = L^(1/2)`；`unify(L, T)` 报 `DimConflict`；先 `unify(D_f, L)` 再 `unify(D_f, T)` 报 `DimConflict`；`unify(Angle, 无量纲)` 报 `DimConflict`；冲突后 `Subst` 与调用前 `==`。
- [R13] 溢出：`L^(i128::MAX)` 与 `L^1` 的 `mul`、`pow` 指数 `i128::MAX` 再乘 2、`unify(D, L^(i128::MIN))` 的取负倒数，分别返回 `UNIT_OVERFLOW`（unify 路径为 `Overflow`），且 `Subst` 不变。
- [R13] 属性（`proptest`，每项 ≥ 1000 例，固定种子可复现；生成：变量个数 0–4，指数分子 −6..6、分母 1..4，base 为 7 个基本维度的小整数指数）：`unify` 成功则 `resolve(a) == resolve(b)`；`unify(a, b)` 成功当且仅当 `unify(b, a)` 成功；重复 `unify` 后 `Subst ==` 不变（幂等）；同输入重复 100 次得到彼此 `==` 的 `Subst`；`bindings()` 右侧均不含已绑定变量；任何输入不 panic。
- [R13] 多态合一序列（本卡独立运行、字面输入，对应 CORE-09（下游说明，非契约）DX-05～DX-11 的规则展开）：变量按列出顺序用同一 `Subst` 的 `fresh` 分配，依次执行所列 `unify`；期望为全部调用成功、所列等式在 `resolve` 后成立、自由变量个数相符，判定与具体编号无关。DX-05 变量 f,x,F,C：`unify(f·x, F)`、`unify(F, C)` → `resolve(F) = resolve(f·x)`、`resolve(C) = resolve(F)`，自由变量 2；DX-06 变量 f,x,a,R：`unify(x, a)`、`unify(f, f·x^-1·x)`、`unify(f, f·x^-2·x^2)`、`unify(f, R)` → `resolve(a) = resolve(x)`、`resolve(R) = resolve(f)`，自由变量 2；DX-07 变量 f,x,a,b,ξ：`unify(a, x)`、`unify(b, x)`、`unify(ξ, x)`、`unify(b, a)`、`unify(f, f·x^-1·b)` → a、b、ξ、x 四者 `resolve` 相等，自由变量 2；DX-08（n = 3）变量 A,B：`unify((A·B)^3, A^3·B^3)` → 成功且 `bindings()` 为空，自由变量 2；DX-09（n = 3）变量 A：`unify(A·A^2, A^3)` → 成功且 `bindings()` 为空，自由变量 1；DX-10 变量 X,μ,σ,p：`unify(μ, X)`、`unify(X^2·σ^-2, 1)`、`unify(p, X^-1)`、`unify(p, σ^-1)` → `resolve(σ) = resolve(X)`、`resolve(p) = resolve(X)^-1`，自由变量 1；DX-11 变量 X,E,ε,V：`unify(E, X)`、`unify(ε, X)`、`unify(V, X^2)`、`unify(V·ε^-2, 1)` → `resolve(E) = resolve(ε) = resolve(X)`、`resolve(V) = resolve(X)^2`，自由变量 1。
- [R13] 跨来源协议：目标槽位类型 `L·D0` 与来源输出 `T·D0`（两份都自 D0 编号）不实例化直接 `unify` 报 `DimConflict`（伪冲突），按协议新建 `Subst` 并对两侧各调一次 `instantiate_types` 后 `unify` 成功；目标 `D0·D1^-1` 与来源 `D0` 不实例化时 `unify` 使 `resolve(D1)` 成为单位元（伪约束），按协议实例化后 D1 的对应新变量仍为自由变量；同一来源中 `D0` 出现在两个 `TypeExpr` 里，一次 `instantiate_types` 后映射到同一新变量，分两次调用则映射到两个不同变量；`instantiate*` 不改变指数、输出为规范形。
- [R13] 序列化与文本：`DimVar`、`DimExpr`（含 `vars` 非空）、`TypeExpr` 的 JSON 往返等价且与 `types.schema.json` 校验通过；乱序、零指数、同号重复的 `DimExpr` JSON 反序列化后等于规范形，同号合并溢出的 JSON 反序列化失败；`to_text` 对“文本化”所列四个黄金输入逐字节等于黄金文本。

**规模**：约 400 行（实现 230、测试 170）；`crates/fml-type/src/dim.rs`（含 crate 骨架与测试，及必要的同构建单元接缝）。

