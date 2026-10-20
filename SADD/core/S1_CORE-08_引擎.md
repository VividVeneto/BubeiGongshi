### CORE-08 量纲与单位

**目标**：提供七个 SI 基本量纲的有理指数代数、单位注册表、精确换算、仿射温度与角度语义，以及用户自定义单位。

**范围**
- 包含：`Dimension`、`Unit`、`UnitRegistry`、`QuantityKind` 注册表、精确有理换算、仿射单位、伪量纲 Angle/Count、自定义单位的定义与环检测。
- 不包含：表达式类型推断（CORE-09）。

**依赖**：CORE-01、CORE-02、CORE-05

**接口契约**

```rust
// crates/fml-units/src/lib.rs
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct Rational { pub num: i128, pub den: i128 }        // 已约分，den > 0；零唯一为 0/1；溢出返回 UNIT_OVERFLOW
impl Rational { pub fn new(num: i128, den: i128) -> Result<Self, FmlError>;   // 约分并规范符号；den = 0 或 i128::MIN 取反溢出 → UNIT_OVERFLOW（不引入新错误码）
                pub fn checked_add(self, o: Self) -> Result<Self, FmlError>; pub fn checked_mul(self, o: Self) -> Result<Self, FmlError>; // 先交叉约分再 checked 运算
                pub fn checked_neg(self) -> Result<Self, FmlError>; pub fn checked_recip(self) -> Result<Self, FmlError>; // 零的倒数 → UNIT_OVERFLOW
                pub fn is_zero(self) -> bool; pub fn is_one(self) -> bool; }   // CORE-77 等下游只经这些函数做指数运算（T1-F02）
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct Dimension { pub exps: [Rational; 7] }           // 顺序 [L, M, T, I, Θ, N, J]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]   // serde 蛇形："angle"、"count"；排序 Angle < Count
pub enum PseudoDim { Angle, Count }                         // 库级固定策略，不做用户开关
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct DimensionFull { pub base: Dimension, pub pseudo: Vec<(PseudoDim, Rational)> }   // 规范形：pseudo 去掉零指数、按 Angle < Count 排序；所有构造与运算结果都是规范形
impl DimensionFull { pub fn one() -> Self;                                     // 单位元（全零指数、pseudo 为空）
                     pub fn checked_mul(&self, o: &Self) -> Result<Self, FmlError>;   // 指数逐项相加，溢出 UNIT_OVERFLOW（取代原无溢出通道的 mul）
                     pub fn inverse(&self) -> Result<Self, FmlError>;                  // 指数取负
                     pub fn pow(&self, q: Rational) -> Result<Self, FmlError>;
                     pub fn is_dimensionless(&self) -> bool;   // 仅当 base 全零且 pseudo 为空；Angle、Count 不等价于无量纲（CORE-09 的“Angle 或无量纲”规则对应两个判断）
                     pub fn parse(text: &str) -> Result<Self, FmlError>;   // CORE-05 TypeDecl.dimension 的文本形式
                     pub fn to_text(&self) -> String; }                    // 规范文本，parse(to_text(d)) == d

pub enum UnitKind { Absolute, AffinePoint /* ℃ 温度点 */, Difference /* 温差 */ }
pub struct Unit { pub id: String, pub namespace: String /* "si" | "common" | "user" | 扩展名 */,
                  pub dimension: DimensionFull, pub scale: Rational, pub offset: Option<Rational>,
                  pub kind: UnitKind, pub version: u32 }
pub struct QuantityKind { pub id: String /* "Energy" */, pub dimension: DimensionFull,
                          pub compatible_with: Vec<String> /* Energy ↔ Heat */ }

pub trait UnitRegistry {
    fn lookup(&self, id: &str) -> Option<&Unit>;
    fn compatible_units(&self, dim: &DimensionFull) -> Vec<&Unit>;
    fn convert(&self, value: &Rational, from: &str, to: &str) -> Result<Rational, FmlError>;
    fn quantity_kind(&self, id: &str) -> Option<&QuantityKind>;
}
pub trait UnitRegistryMut: UnitRegistry {
    fn insert(&mut self, unit: Unit) -> Result<(), FmlError>;
    fn remove(&mut self, id: &str) -> Result<(), FmlError>;     // 被其他用户单位引用时返回 UNIT_IN_USE
}
pub struct UnitDefinition {
    pub id: String,                 // "user:<名称>"，名称匹配 ^[A-Za-z][A-Za-z0-9_]{0,31}$
    pub symbol: String,             // 显示符号，≤ 16 字符
    pub expr: String,               // 以已有单位表示的定义，如 "1000 si:m"、"1/60 si:s"、"si:kg si:m^2 si:s^-2"
    pub offset: Option<String>,     // 仅 AffinePoint；有理数文本
    pub kind: UnitKind,
}
pub fn define_user_unit(reg: &mut dyn UnitRegistryMut, def: UnitDefinition) -> Result<(), FmlError>;
```

- FFI op：`units.compatible`（给量纲返回可选单位，供计算器下拉）、`units.convert`（同步；DTO 按 CORE-03 映射规则，处理适配在 CORE-56 的 `crates/fml-ffi/src/ops/units.rs`，读取引擎快照的合成单位表）；`units.define_user`、`units.list_user`（返回全部用户单位定义）、`units.delete_user`（仍被引用时 `UNIT_IN_USE`）的持久化与处理归 CORE-14，本卡只提供定义校验纯函数与 `UNIT_*` 错误码。
- 量纲文本语法：以空格分隔的因子 `<基>^<指数>`，基为 `L M T I Θ N J` 与伪量纲 `Angle Count`，指数为整数或 `p/q`，指数 1 省略；无量纲写 `1`。规范文本按 `L M T I Θ N J Angle Count` 顺序、省略零指数，如力为 `L M T^-2`，频率为 `T^-1`。
- 内置 QuantityKind（最少）：Energy/Heat（可显式兼容）、Torque、Frequency、AngularFrequency（与 Frequency 换算含 2π）、Temperature、TemperatureDifference、SpecificHeat、SpecificEntropy、Probability、Correlation、Count、Angle。
- 错误码（唯一定义；沿用原触发语义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `UNIT_UNKNOWN` | error | 否 | 单位ID不存在 |
| `UNIT_INCOMPATIBLE` | error | 否 | 换算两端量纲不同 |
| `UNIT_AFFINE_MISUSE` | error | 否 | 温度点相加、乘除或取幂 |
| `UNIT_CYCLE` | error | 否 | 用户单位定义相互引用 |
| `UNIT_INVALID_OFFSET` | error | 否 | 非AffinePoint带offset或offset非有理数 |
| `UNIT_OVERFLOW` | error | 否 | 有理数约分后分子、分母或checked中间值超i128；分母为0或对零取倒数（不可表示） |
| `UNIT_DIM_SYNTAX` | error | 否 | 量纲文本不合语法 |
| `UNIT_IN_USE` | error | 否 | 删除仍被引用的用户单位 |
| `UNIT_DUPLICATE` | error | 否 | 单位ID已存在 |

Rational 的跨语言 JSON 为 {"num":"<i128十进制>","den":"<正i128十进制>"}，数值必须为已约分形式，零唯一为 0/1；不能作为 JSON number 传给 Dart。CORE-03 通用整数规则对本类型以此为准。乘除先交叉约分再 checked_mul；不能用 f64 掩盖溢出。

| 向量 | 输入 | 期望 |
| --- | --- | --- |
| UNIT-X1 | 1 eV → J | 精确 801088317 / 5000000000000000000000000000 |
| UNIT-X2 | N_A | 精确整数 602214076000000000000000 mol^-1 |
| UNIT-X3 | 原子质量单位 u → kg | CODATA 2022 近似值 1.66053906892e-27，对记录的十进制值精确保存为有理数；不得标 SI 定义精确值 |

来源：[BIPM SI Brochure](https://www.bipm.org/en/publications/si-brochure)、[NIST atomic mass constant](https://physics.nist.gov/cgi-bin/cuu/Value?u)。

DimensionFull跨语言JSON唯一采用结构体映射：base.exps恰7项，顺序L/M/T/I/Θ/N/J；每项Rational的num/den为十进制字符串，pseudo是[伪量纲蛇形枚举,Rational]数组，无重复且按angle/count顺序、省略零指数。无量纲例base.exps全为{"num":"0","den":"1"}且pseudo=[]；L量纲仅首项为1/1，其余0/1。文本parse/to_text仅用于TypeDecl声明和展示，不是DimensionFull线类型。

units.compatible的body={dimension:DimensionFull}、ok={units:Unit[]}；units.convert的body={value:Rational,from:string,to:string}、ok={value:Rational}，均call/none scope。字段全部必填，units按id字节序。例convert 1 si:m→si:m返回1/1；compatible允许无匹配时units=[]。持久化用户单位仍归CORE-14。

FFI错误镜像（不重定义代码；通用信封错误见CORE-03；读取快照的适配另由CORE-56（下游说明，非契约）统一返回ENGINE_UNAVAILABLE）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| units.compatible | 无业务错误；通用信封错误仍适用 |
| units.convert | UNIT_UNKNOWN、UNIT_INCOMPATIBLE、UNIT_AFFINE_MISUSE、UNIT_OVERFLOW |

**实现约束**
- 换算用精确有理系数，只在输出阶段转浮点；π 相关换算给出精度说明。
- 温度：20 ℃ 存储为 293.15 K 的温度点；Δ20 ℃ 存储为 20 K 温差；点 − 点 = 差，点 + 差 = 点，点 + 点拒绝；温度点不得参与乘除、指数与约分，热力学公式（如 pV = νRT）中的绝对温度以开尔文参与。
- 角度在三角函数内按库策略转弧度，外部显示保留用户单位。
- `pow(q)` 的失败条件只有数值溢出或超出策略限制，不因“不能整除”失败。
- 自定义单位位于 `user` 命名空间，定义集合闭合、无环；非 SI 量纲只能经带版本的扩展命名空间引入。

**验收标准**
- [R13] T-UNIT：20 ℃ → 293.15 K、Δ20 ℃ → 20 K、温度点相加被拒；rad 与 deg 换算；ω = 2πf 显式；ω = f 报 QuantityKind 不一致（由 CORE-09 使用本卡数据）。
- [R15] 自定义单位：等价换算成功；循环定义与非法 offset 被拒（`UNIT_CYCLE`、`UNIT_INVALID_OFFSET`）。
- [R13] 属性测试：换算满足结合性与往返一致（a→b→a 精确相等）。
- [R14] 单元测试：`compatible_units` 对力的量纲只返回 N、kN、dyn 等相容单位。
- [R13] 量纲文本：`L M T^-2`、`L^1/2`、`1`、`T^-1 Angle` 解析后 `to_text` 原样返回；`M L T^-2` 规范化为 `L M T^-2`；`L^x` 返回 `UNIT_DIM_SYNTAX`。

- [R13] 指数运算单测：`Rational::new(1, 0)`、`Rational::new(i128::MIN, 1).checked_neg()`、零的 `checked_recip`、先交叉约分后仍溢出的 `checked_mul`、`checked_add` 溢出均返回 `UNIT_OVERFLOW`；`new(2, -4)` 规范为 `-1/2`、`new(0, 5)` 规范为 `0/1`；`DimensionFull::one()` 为单位元，`checked_mul` 与 `inverse` 结果去零指数且 pseudo 按 Angle < Count 排序，`pow(1/2)` 后 `L^2` 得 `L`，`d.checked_mul(&d.inverse()?)? == one()`；`is_dimensionless` 对 `Angle` 为 false。
- [R13] UNIT-X1～X3 可无溢出表示；eV 往返为精确有理数，i128 边界外返回 UNIT_OVERFLOW，JSON 往返无 Dart 浮点损失。

**规模**：约 500 行（不含单位数据表；含 Rational/DimensionFull 的 checked 运算与规范形及其单测约 40 行）；`crates/fml-units/`。

