### CORE-08 量纲与单位

**目标**：提供七个 SI 基本量纲的有理指数代数、可直接构造的内存注册表、有理换算、仿射温度与角度语义，以及用户单位定义图。

**范围**
- 包含：Rational、Dimension/DimensionFull、Unit/QuantityKind、UnitRegistry/UnitRegistryMut、MemRegistry、有理换算、伪量纲 Angle/Count、用户单位定义及环检测。
- 不包含：表达式类型推断与温度点算术（CORE-09（下游说明，非契约），下游说明，非契约）、文件/数据库/引擎快照 I/O。

**依赖**：CORE-01、CORE-02、CORE-05

**接口契约**

```rust
// crates/fml-units/src/lib.rs
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)] // 不 derive PartialOrd/Ord：分子/分母字典序不代表数值大小
pub struct Rational { pub num: i128, pub den: i128 } // 已约分、den>0、零唯一0/1
impl Rational {
    pub fn new(num: i128, den: i128) -> Result<Self, FmlError>;
    pub fn checked_add(self, o: Self) -> Result<Self, FmlError>;
    pub fn checked_mul(self, o: Self) -> Result<Self, FmlError>;
    pub fn checked_neg(self) -> Result<Self, FmlError>;
    pub fn checked_recip(self) -> Result<Self, FmlError>;
    pub fn is_zero(self) -> bool;
    pub fn is_one(self) -> bool;
}
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct Dimension { pub exps: [Rational; 7] } // L M T I Θ N J
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum PseudoDim { Angle, Count } // 固定顺序 Angle < Count，serde为angle/count
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct DimensionFull { pub base: Dimension, pub pseudo: Vec<(PseudoDim, Rational)> }
impl DimensionFull {
    pub fn one() -> Self;
    pub fn checked_mul(&self, o: &Self) -> Result<Self, FmlError>;
    pub fn inverse(&self) -> Result<Self, FmlError>;
    pub fn pow(&self, q: Rational) -> Result<Self, FmlError>;
    pub fn is_dimensionless(&self) -> bool;
    pub fn parse(text: &str) -> Result<Self, FmlError>;
    pub fn to_text(&self) -> String;
}
pub enum UnitKind { Absolute, AffinePoint, Difference }
pub struct Unit { pub id: String, pub namespace: String, pub dimension: DimensionFull,
                  pub scale: Rational, pub offset: Option<Rational>, pub kind: UnitKind, pub version: u32 }
pub struct QuantityKind { pub id: String, pub dimension: DimensionFull, pub compatible_with: Vec<String> }
pub struct UnitDefinition { pub id: String, pub symbol: String, pub expr: String,
                            pub offset: Option<String>, pub kind: UnitKind }
pub trait UnitRegistry {
    fn lookup(&self, id: &str) -> Option<&Unit>;
    fn compatible_units(&self, dim: &DimensionFull) -> Vec<&Unit>;
    fn convert(&self, value: &Rational, from: &str, to: &str) -> Result<Rational, FmlError>;
    fn quantity_kind(&self, id: &str) -> Option<&QuantityKind>;
}
pub trait UnitRegistryMut: UnitRegistry {
    fn insert(&mut self, unit: Unit) -> Result<(), FmlError>;
    fn remove(&mut self, id: &str) -> Result<(), FmlError>;
    fn insert_definition(&mut self, def: UnitDefinition) -> Result<(), FmlError>; // 新增，原子保留定义与依赖图
}
#[derive(Clone)]
pub struct MemRegistry<'a> { /* 私有 owned units/kinds/definitions/dependencies；可选只读 borrowed base */ }
impl MemRegistry<'static> {
    pub fn from_parts(units: Vec<Unit>, kinds: Vec<QuantityKind>) -> Result<Self, FmlError>;
}
impl<'a> MemRegistry<'a> {
    pub fn with_user_definitions(base: &'a dyn UnitRegistry, defs: &[UnitDefinition]) -> Result<Self, FmlError>;
}
// MemRegistry<'a> 实现 UnitRegistry、UnitRegistryMut；不要求 dyn UnitRegistry 可 Clone 或可枚举
pub fn define_user_unit(reg: &mut dyn UnitRegistryMut, def: UnitDefinition) -> Result<(), FmlError>;
```

公共能力与 serde（类型声明中未重复写 derives 不代表可省略）：

| 类型 | 必须能力/唯一线表示 |
| --- | --- |
| Rational | 上列能力 + Serialize/Deserialize；`{"num":"<i128十进制>","den":"<正i128十进制>"}`，规范整数拼写，无+、前导零、-0；必须已约分，零0/1；不经JSON number/f64 |
| Dimension、DimensionFull、PseudoDim | 上列能力 + Serialize/Deserialize；Dimension对象exps恰7项；Full为base与pseudo，pseudo为恰两项数组[蛇形PseudoDim,Rational]的数组，Angle<Count，无重复、无零项；反序/重复/零项输入拒绝而非静默合并 |
| UnitKind | Clone + Copy + Debug + PartialEq + Eq + Hash + Serialize + Deserialize；absolute/affine_point/difference |
| Unit、QuantityKind、UnitDefinition | Clone + Debug + PartialEq + Eq + Serialize + Deserialize；同名snake_case struct字段，拒绝未知/重复字段；offset=None省略，显式null拒绝；QuantityKind兼容ID数组无重复、按UTF-8字节序 |
| MemRegistry | Clone；拥有的集合/定义图深拷贝，base只拷贝借用引用；不提供serde，不冒充持久化模型 |

所有 serde 结构匹配现有 contracts/dto/types.schema.json、units.compatible/convert.schema.json；本次不新增机器字段。坏 wire 在 FFI 进入领域前返回 CORE-03 的 FFI_BAD_ARG；serde 自身返回解码错误，不在 Deserialize 中 panic。公开字段的直接构造者也必须满足规范形，注册表构造与插入再次验证，不能把无效 Rational 传给算法。

**数值与量纲文本**
- Rational::new 先按无符号幅值求gcd、约分再规范符号；den=0、规范后不能放入i128、零取倒数或checked中间值溢出均 UNIT_OVERFLOW。乘法先交叉约分，加法先用分母gcd减少中间值；不靠 f64 或 lexicographic Ord 比较大小。MIN/MIN 应可约成1/1，MIN/-1不可表示。
- DimensionFull运算只作用于指数：checked_mul逐项加，inverse取负，pow乘有理指数，不对Unit.scale开方；结果去零、排序。one为七个0/1且pseudo=[]；Angle/Count不是无量纲。pow(1/2)对L得到L^1/2，不因不能整除而失败。
- DimensionFull::parse文本：输入仅以ASCII空格分隔因子 `基[^有符号整数或p/q]`；基为 L M T I Θ N J Angle Count，q为正整数。允许无序/重复因子并合并指数，指数0消去、1省略；单独`1`为无量纲，不和其他因子混写。to_text按上述基顺序，以单个空格连接；L^x、空文本、未知基、零分母、尾随垃圾为UNIT_DIM_SYNTAX；词法合法但指数超i128或运算溢出为UNIT_OVERFLOW。parse(to_text(d))==d。

**具体注册表与接线**
- from_parts拥有给定Unit/QuantityKind，按ID建索引；只接受可验证的原子单位：id为NFC的`namespace:local`，namespace匹配`[a-z][a-z0-9_-]*`且与字段一致，local非空、无空白/控制字符或`:^*/`；scale规范且num>0，dimension规范；AffinePoint仅允许纯Θ一阶、可有offset，其余kind不得有offset。QuantityKind.id非空，compatible_with必须指向现有kind且互相声明。重复ID UNIT_DUPLICATE，坏结构 UNIT_DIM_SYNTAX，未知kind引用 UNIT_UNKNOWN，offset误用 UNIT_INVALID_OFFSET，数值不可表示 UNIT_OVERFLOW。它不从Unit.scale猜测UnitDefinition、来源引用或恢复User依赖图。
- lookup与quantity_kind精确匹配ID，不存在返回None。compatible_units只按完整量纲相等筛选、按ID UTF-8字节序、每ID一次；与量的种类/点差算术不是同一判定。with_user_definitions先查自己拥有的用户结果再回落base；compatible_units合并自己与base.compatible_units结果并排序，quantity_kind回落base，不需要枚举任意trait对象。
- with_user_definitions借用“不含User层”的稳定base快照，拥有defs副本与用户引用图；只接收user:单位定义。先解析完整集合，建立边（定义→被引用user ID），检查自环/间接环，再拓扑求值；允许集合内前向引用，非环未知引用UNIT_UNKNOWN。base借用不得超出该快照，Clone不延长生命周期。CORE-56（下游说明，非契约）将快照已合成units/kinds传from_parts；CORE-14（下游说明，非契约）用base+全部已持久化UnitDefinition构造临时用户registry，在同一Store事务完成候选检查/写入，之后才发布引擎层，不能依赖dyn trait可clone。
- insert(Unit)只加入独立原子单位，不能伪造定义依赖；ID冲突拒绝、不覆盖。insert_definition先在副本解析、闭包/环/offset/数值检查，成功才同时写Unit、UnitDefinition及引用图；define_user_unit仅调用该原子入口。remove不存在返回UNIT_UNKNOWN，已有其他owned定义引用时UNIT_IN_USE；失败时所有索引/定义图不变。借用base只读，remove只操作owned条目，只有base中存在的ID视为无owned条目而返回UNIT_UNKNOWN。普通from_parts/insert不能代替以定义图为依据的User删除安全检查。
- 引用图是用户定义的事实来源，不能从Unit的扁平量纲/比例反推。删除/重定义由CORE-14（下游说明，非契约）在事务内以持久化全集构造候选图，先校验再替换；调用者保存原定义记录，不从Unit回造symbol/expr。

**用户单位冻结语法**
- id=`user:<名称>`，名称匹配`^[A-Za-z][A-Za-z0-9_]{0,31}$`；symbol为NFC、1..16个Unicode标量、不含空白/控制字符。symbol仅显示元数据，不创建lookup别名。
- expr=`[系数 空格] 单位因子 (空格 单位因子)*`，首系数缺省1；系数为有符号十进制整数、有限小数或`p/q`（q正整数），不支持科学记数法；单位因子为已存在或集合内ID，可追加`^有符号整数`，如`1000 si:m`、`1/60 si:s`、`si:kg si:m^2 si:s^-2`。只以一个或多个ASCII空格分隔，可去首尾空格；不支持括号、乘除运算符、相加、分数幂或把符号别名当ID。因子指数重复相加；scale按整数幂有理运算后乘首系数且最终必须>0；生成Unit的namespace=user、version=1，后续定义版本由持久化消费者管理，不从时钟生成。
- AffinePoint定义必须只含一个非AffinePoint的纯Θ单位、指数1，offset用上述有理文本表示“SI基准加数”：`base_value=value*scale+offset`，缺省0；不得把带offset的点当乘积因子。Difference/Absolute带offset返回UNIT_INVALID_OFFSET；引用AffinePoint作为因子返回UNIT_AFFINE_MISUSE；offset词法错误为UNIT_INVALID_OFFSET、合法数字超i128为UNIT_OVERFLOW。格式/id/symbol/不支持幂/非正scale等为UNIT_DIM_SYNTAX；单个插入不能引用未知ID，完整集合允许前向引用。

**换算、近似π与数据所有权**
- convert先检查from/to存在（UNIT_UNKNOWN），再检查完整量纲相等（UNIT_INCOMPATIBLE），再检查仿射kind。si:K为纯Θ、scale1、无offset的Absolute中性SI基准；允许AffinePoint↔si:K与Difference↔si:K，保证20℃→K和Δ20℃→K均有明确入口。直接AffinePoint↔Difference返回UNIT_AFFINE_MISUSE。其他Absolute温度单位按零offset线性基准处理；普通非温度单位不允许AffinePoint定义。K的中性仅是此单位换算API的桥接，不抹除表达式的温度点/温差QuantityKind，也不授权CORE-09（下游说明，非契约）把点当普通量相加或相乘。点→点与点→温度基准使用`(v*scale_from+offset_from-offset_to)/scale_to`；Difference/普通线性单位用`v*scale_from/scale_to`；全部先约分再checked计算。
- 温度点加法/乘除/指数不由本卡的convert执行：CORE-09（下游说明，非契约）报TYPE_AFFINE_MISUSE；点−点=差、点+差=点，绝对温度进入热力学公式时按开尔文语义参与。本卡不添加不存在的Quantity算术API。
- 固定近似`PI_RAT=245850922/78256779`，不是数学π精确值；common:deg.scale=PI_RAT/180=122925461/7043110110，si:rad.scale=1，均带Angle伪量纲。180deg→rad精确为245850922/78256779，1rad→deg精确为7043110110/122925461，往返精确；数学π误差另验`|PI_RAT-π|<1e-15`，不把浮点π当有理黄金值。Frequency与AngularFrequency之2π因子用491701844/78256779，不把两种QuantityKind隐式标为兼容；显式ω=2πf/错误ω=f的表达式规则在CORE-09（下游说明，非契约）。
- 最少种类：Energy/Heat显式双向兼容、Torque、Frequency、AngularFrequency、Temperature、TemperatureDifference、SpecificHeat、SpecificEntropy、Probability、Correlation、Count、Angle。具体units/kinds数据、版本与来源只由CORE-56（下游说明，非契约）交付`crates/fml-ffi/assets/engine-v1/units.json`、`kinds.json`；本crate不读文件、不自带第二份数据表。测试用最小内存fixture而非偷读未交付资产。

| 向量 | 输入 | 固定期望 |
| --- | --- | --- |
| UNIT-X1 | 1eV→J | 801088317/5000000000000000000000000000，SI定义精确 |
| UNIT-X2 | N_A | 602214076000000000000000 mol^-1，SI定义精确 |
| UNIT-X3 | u→kg | 41513476723/25000000000000000000000000000000000000，即记录十进制1.66053906892e-27的精确存储；CODATA2022近似，非SI定义精确值 |

来源：[BIPM SI Brochure](https://www.bipm.org/en/publications/si-brochure)、[NIST atomic mass constant](https://physics.nist.gov/cgi-bin/cuu/Value?u)。

**错误码（本卡唯一定义，均error/不可重试）**

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `UNIT_UNKNOWN` | error | 否 | 单位ID或kind兼容引用不存在；remove无owned目标 |
| `UNIT_INCOMPATIBLE` | error | 否 | convert两端完整量纲不同 |
| `UNIT_AFFINE_MISUSE` | error | 否 | convert直接点↔差；用户定义将AffinePoint作为乘积因子；不是表达式算术错误码 |
| `UNIT_CYCLE` | error | 否 | 用户定义集合含自环或间接引用环 |
| `UNIT_INVALID_OFFSET` | error | 否 | 非AffinePoint携offset、AffinePoint非纯Θ或非法offset词法 |
| `UNIT_OVERFLOW` | error | 否 | 规范/checked中间值超i128、分母0、零取倒数 |
| `UNIT_DIM_SYNTAX` | error | 否 | 量纲/定义语法、ID/symbol、非正scale或注册表结构不满足本卡约束 |
| `UNIT_IN_USE` | error | 否 | 删除仍被其他owned用户定义引用的单位 |
| `UNIT_DUPLICATE` | error | 否 | 单位或种类ID重复；insert/insert_definition冲突 |

**FFI接缝**：units.compatible的body={dimension:DimensionFull}、ok={units:Unit[]}；units.convert的body={value:Rational,from:string,to:string}、ok={value:Rational}，均call/none，body字段全必填；compatible无匹配返回[]。适配由CORE-56（下游说明，非契约）的`crates/fml-ffi/src/ops/units.rs`构造同快照from_parts并调用纯trait；snapshot不可用统一ENGINE_UNAVAILABLE，不混入Unit错误。用户units.define_user/list_user/delete_user持久化由CORE-14（下游说明，非契约）负责，返回原UnitDefinition集合。

| op | 本卡业务/诊断代码及依赖透传（通用信封错误见CORE-03） |
| --- | --- |
| units.compatible | 无业务错误；调用前规范DTO/快照验证，空结果不是错误 |
| units.convert | UNIT_UNKNOWN、UNIT_INCOMPATIBLE、UNIT_AFFINE_MISUSE、UNIT_OVERFLOW |

**实现约束**
- 无I/O/时钟/随机源；不依赖fml-ffi/store/type/parser。serde与用户表达式只做本卡语法，不借解析器。
- 外部前提：serde（derive）、serde_json、unicode-normalization（NFC）；proptest与支持2020-12的jsonschema为开发依赖；按ADR-V5-15开工锁Cargo.lock。整数路径必须精确，测试不能先JSON.parse成Number再验证i128。无num-bigint运行依赖，不以浮点掩盖溢出。
- 所有新增trait能力、借用生命周期与下游接线须非作者复核；测试方案是编码验收计划，不声称尚未实现的Rust测试已通过。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-08_TEST.md](../Test/core/S1_CORE-08_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约620行，分阶段；均`crates/fml-units/`，不计测试/fixture、机器schema与他卡资产/FFI代码。阶段①约310行：lib.rs公开类型/traits、rational.rs、dimension.rs、serde.rs、registry.rs的from_parts/基础lookup/compatible/convert与原子Unit插入删除；可独立构建，最小内存SI/温度/角度fixture验证数值/serde/换算/排序，不依赖尚未交付用户图。新增insert_definition/with_user_definitions只随阶段②发布，①不暴露伪实现。阶段②约310行：user_units.rs及registry.rs的定义图/with_user_definitions/insert_definition与闭包/原子更新；复用①数值和原子基表，独立构建并运行用户前向引用/环/删除/失败回滚测试；不改变①from_parts签名。数据资产与units.*适配由CORE-56（下游说明，非契约）交付，用户持久化由CORE-14（下游说明，非契约）交付，不重复预算。
