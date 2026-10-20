### CORE-05 公式 AST 与修订模型

**目标**：定义公式的唯一权威数据结构——不可变 AST、公式条目与修订、推导与来源记录，以及规范序列化和哈希。

**范围**
- 包含：`fml-ast` crate 的类型、NodePath、规范 JSON 序列化与 BLAKE3 规范哈希、全局复杂度上限常量、取消标志 `CancelFlag`、AST JSON schema；各引擎卡共用的存储形数据类型（`SymbolEnv`、`SymbolDecl`、`TypeDecl`、`MathKind`、`Validation`、`ConfirmRecord`）只在本卡定义，由 CORE-07、CORE-09 填充与判定。
- 不包含：解析（CORE-06）、符号绑定（CORE-07）、类型推断（CORE-09）、持久化（CORE-13/14）。渲染树不作为权威数据保存。

**依赖**：CORE-01、CORE-02、CORE-03

**接口契约**

```rust
// crates/fml-ast/src/lib.rs
pub struct FormulaItemId(pub Uuid);   // 用户条目随机 UUIDv7；资源包条目调用下述 pack_item_id，跨设备确定（禁止自行拼接）
pub struct RevisionId(pub Uuid);
pub enum ConstantSource { Exact /* 2019 SI 定义值 + CODATA 2022 */, Textbook /* 教材取值，如 g = 9.8 */, Given /* 题目给定 */ }
pub struct ConstantValue { pub key: String, pub value: String, pub unit: String,
                           pub source: ConstantSource, pub source_ref: String, pub set_version: String }

pub struct SymbolId(pub u32);          // 在修订的符号环境内唯一
pub struct NodePath(pub Vec<u16>);     // 自根起的子节点下标；文本形式 "0.2.1"

pub enum FormulaNode {
    Symbol(SymbolId),
    Number(NumberLiteral),              // 十进制文本原样保留 + 有效数字位数
    Unit(UnitRef),                     // 单位符号，不得当作普通变量
    Binary { op: BinaryOp, left: Box<FormulaNode>, right: Box<FormulaNode> },
    Unary { op: UnaryOp, operand: Box<FormulaNode> },
    Function { id: FunctionId, args: Vec<FormulaNode> },   // 函数符号与普通符号区分
    Derivative { kind: DerivKind /* Ordinary|Partial|Dot */, target: Box<FormulaNode>, var: SymbolId, order: u8 },
    Integral { kind: IntegralKind /* Indefinite|Definite|Multiple(n)|Line|Surface|Closed */,
               integrand: Box<FormulaNode>, differentials: Vec<SymbolId>,
               lower: Option<Box<FormulaNode>>, upper: Option<Box<FormulaNode>> },
    SumOrLimit { kind: LimitKind /* Sum|Product|Limit */, index: Option<SymbolId>,
                 lower: Option<Box<FormulaNode>>, upper: Option<Box<FormulaNode>>, body: Box<FormulaNode> },
    Vector { items: Vec<FormulaNode> },
    Matrix { rows: Vec<Vec<FormulaNode>> },
    Relation { op: RelOp /* Eq|Ne|Lt|Le|Gt|Ge|Approx|Equiv */, left: Box<FormulaNode>, right: Box<FormulaNode> },
    Piecewise { branches: Vec<(FormulaNode, Option<FormulaNode>)> },  // (值, 条件)；条件为 None 表示“其他情况”，只能是最后一支
    Hole(u16),                          // 编辑器空位 `\fmlhole`，按出现顺序从 0 编号；只存在于草稿，含 Hole 的 AST 不得写入正式修订（ADR-V5-17）
}
pub struct NumberLiteral { pub text: String /* 十进制原文，如 "6.674e-11"、"9.8" */, pub sig_digits: Option<u8> }
pub struct UnitRef(pub String);         // CORE-08 单位 ID，如 "si:m"、"common:km"、"user:<uuid>"
pub enum BinaryOp { Add, Sub, Mul, Div, Pow, Dot, Cross }  // \frac 与 / 同为 Div，隐式乘与 \cdot 同为 Mul（写法不进 AST）
pub enum UnaryOp { Neg, Plus, Factorial, Transpose, Conjugate, Adjugate }
pub struct FunctionId(pub String);      // 规范名：sin cos tan cot sec csc arcsin arccos arctan sinh cosh tanh exp ln lg log
                                        // （log 的底数为第 2 个参数）sqrt root（参数：被开方式、次数）abs norm floor ceil det tr
                                        // binom P E Var Cov max min gcd；用户函数为 "user:<名称>"
pub enum DerivKind { Ordinary, Partial, Dot }
pub enum IntegralKind { Indefinite, Definite, Multiple(u8), Line, Surface, Closed }
pub enum LimitKind { Sum, Product, Limit }
pub enum RelOp { Eq, Ne, Lt, Le, Gt, Ge, Approx, Equiv }

// 符号环境：由 CORE-06 分配 SymbolId，CORE-07 填充含义，CORE-09 读取 declared_type
pub enum SymbolRole { Variable, Constant, Function, Unit, BoundVar /* 积分/求和变量 */, Parameter }
#[derive(Clone, Debug, PartialEq, Eq, Hash)]   // serde：蛇形外部标签，无载荷为字符串（"scalar"），有载荷为单键对象（{"vector": null|n}、{"matrix": [a, b]}、{"function": n}），与 types.schema.json MathKind 一致
pub enum MathKind { Scalar, Complex, Vector(Option<u16>), Matrix(Option<u16>, Option<u16>), ScalarField,
                    VectorField, Function(u8), Sequence, Series, Operator, Distribution, Density, Unknown }
pub struct TypeDecl { pub dimension: Option<String> /* 量纲式文本，语法见 CORE-08 */, pub quantity_kind: Option<String>,
                      pub math_kind: Option<MathKind> }
pub struct SymbolDecl {
    pub id: SymbolId, pub glyph: String,             // 显示字形，如 "ν"
    pub role: SymbolRole, pub meaning_key: String,   // 如 "phys.amount_of_substance"；未绑定为 ""
    pub declared_type: Option<TypeDecl>, pub domain: Option<String>,
}
pub struct SymbolEnv { pub decls: Vec<SymbolDecl> }   // 按 id 升序，id 唯一
pub enum Validation { Draft, Unresolved, Invalid, Verified,
                      VerifiedPolymorphic { vars: Vec<u32> /* 该修订多态的 DimVar 编号，只作标识；跨修订使用前必须经 CORE-77 Subst::instantiate 换成新变量 */, constraints: Vec<String> } }
pub struct ConfirmRecord { pub confirmed_at_ms: i64, pub from_kind: String, pub to_kind: String, pub reason_key: String }

pub enum Provenance { UserInput, Handwriting { session: Uuid }, Photo { session: Uuid },
                      Pack { pack_id: String, pack_version: String, entry_key: String }, Import { batch: Uuid } }

pub struct FormulaRevision {
    pub id: RevisionId, pub item: FormulaItemId, pub parents: Vec<RevisionId>,
    pub ast_schema: u16, pub source_latex: String,      // 原文按字节保留
    pub ast: FormulaNode, pub symbols: SymbolEnv,        // SymbolEnv 由 CORE-07 填充
    pub notation_profile_id: String, pub conditions: Vec<FormulaNode>,
    pub validation: Validation,                          // CORE-09 写入
    pub derived_from: Option<Derivation>, pub detached: bool,
    pub provenance: Provenance, pub created_at_ms: i64,
    pub draft: bool,                                     // 未通过校验时只能存为草稿（CORE-14）
}
pub struct FormulaItem {
    pub id: FormulaItemId, pub title: String, pub subject: String, pub course: Option<String>, pub tags: Vec<String>,
    pub head: RevisionId, pub read_only: bool /* 预置条目为 true */, pub trashed_at_ms: Option<i64>,
}
pub struct Derivation {
    pub source_revisions: Vec<RevisionId>, pub target_slot: NodePath,
    pub var_map: Vec<(SymbolId, SymbolId)>, pub conditions: Vec<FormulaNode>, pub branch: Option<u8>,
    pub cross_kind_confirmation: Option<ConfirmRecord>, pub depth: u8,
}

pub struct CancelFlag(pub Arc<AtomicBool>);   // CORE-03 的 fml_cancel 置位；长计算每 CHECKPOINT_MS 检查一次
impl CancelFlag { pub fn new() -> Self; pub fn is_cancelled(&self) -> bool; pub fn cancel(&self); }

pub mod limits {   // 全部模块共用的硬上限
    pub const MAX_SOURCE_BYTES: usize = 64 * 1024;
    pub const MAX_NODES: usize = 4096;
    pub const MAX_DEPTH: usize = 64;
    pub const MAX_MATRIX_DIM: usize = 64;         // 且元素总数 ≤ MAX_MATRIX_ELEMS
    pub const MAX_MATRIX_ELEMS: usize = 1024;
    pub const MAX_NORMALIZE_STEPS: u32 = 100_000;
    pub const CHECKPOINT_MS: u32 = 100;           // 长计算每 100 ms 检查一次取消
    pub const MAX_DERIVATION_DEPTH: u8 = 8;
}

pub enum LimitViolation { SourceBytes(usize), Nodes(usize), Depth(usize), MatrixDim(usize, usize), MatrixElems(usize) }
pub fn check_limits(node: &FormulaNode) -> Result<(), LimitViolation>;   // 调用方映射为 PARSE_LIMIT_EXCEEDED
pub fn canonical_json(node: &FormulaNode) -> String;     // 键序固定、无多余空白
pub fn from_canonical_json(s: &str) -> Result<FormulaNode, FmlError>;  // 不合 schema 返回 AST_JSON_INVALID
pub fn canonical_hash(node: &FormulaNode) -> [u8; 32];   // BLAKE3(canonical_json)
pub fn node_at(node: &FormulaNode, path: &NodePath) -> Option<&FormulaNode>;
pub fn walk(node: &FormulaNode, f: &mut dyn FnMut(&NodePath, &FormulaNode));
```

- schema：`contracts/dto/ast.schema.json`（AST JSON），版本号 `ast_schema = 1`；读到更高主版本时返回 `STORE_SCHEMA_TOO_NEW`（由 CORE-13 使用）。
- 规范 JSON 规则：每个节点是对象，变体名放在键 `"k"`（snake_case，如 `"binary"`、`"sum_or_limit"`）；字段名 snake_case；枚举值 snake_case 字符串（`Multiple(n)` 写作 `{"multiple":n}`）；对象键按 UTF-8 字节序升序；`None` 字段省略，空数组保留；`SymbolId`、`order` 为 JSON 整数，数值字面量只存 `text` 字符串；无空白、无尾随换行；字符串按 RFC 8259 最短转义。
- 规范 JSON 测试向量（`contracts/vectors/ast-canonical.yaml`，哈希值由首次实现生成后冻结）：

| 编号 | 输入（AST 描述） | 规范 JSON |
| --- | --- | --- |
| AST-01 | `x + 1`（x 为 SymbolId 0，1 的有效数字 1 位） | `{"k":"binary","left":{"id":0,"k":"symbol"},"op":"add","right":{"k":"number","sig_digits":1,"text":"1"}}` |
| AST-02 | `-a`（a 为 0） | `{"k":"unary","op":"neg","operand":{"id":0,"k":"symbol"}}` |
| AST-03 | `sin(θ)`（θ 为 0） | `{"args":[{"id":0,"k":"symbol"}],"id":"sin","k":"function"}` |
| AST-04 | `dy/dx`（y 为 0，x 为 1） | `{"k":"derivative","kind":"ordinary","order":1,"target":{"id":0,"k":"symbol"},"var":1}` |
| AST-05 | `\frac{a}{b}` 与 `a/b` | 两者规范 JSON 相同：`{"k":"binary","left":{"id":0,"k":"symbol"},"op":"div","right":{"id":1,"k":"symbol"}}` |

- 错误码（本卡登记）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `AST_JSON_INVALID` | error | 否 | `from_canonical_json` 输入不合 schema、未知变体或字段类型错误 |
| `PARSE_LIMIT_EXCEEDED` | error | 否 | `check_limits` 返回违例（由 CORE-06 及其他构造方返回） |

AST schema=1 的穷举字段表（每行额外必含 k；未标 ? 的必填；不允许 null、额外字段、重复对象键或未知枚举；递归 Node 是本表联合）：

| Rust 变体 | k | 其余字段 |
| --- | --- | --- |
| Symbol | symbol | id: u32 |
| Number | number | text: string, sig_digits?: u8 |
| Unit | unit | id: string |
| Binary | binary | op, left: Node, right: Node |
| Unary | unary | op, operand: Node |
| Function | function | id: string, args: Node[] |
| Derivative | derivative | kind, target: Node, var: u32, order: u8 |
| Integral | integral | kind, integrand: Node, differentials: u32[], lower?: Node, upper?: Node |
| SumOrLimit | sum_or_limit | kind, index?: u32, lower?: Node, upper?: Node, body: Node |
| Vector | vector | items: Node[] |
| Matrix | matrix | rows: Node[][]（非空矩形） |
| Relation | relation | op, left: Node, right: Node |
| Piecewise | piecewise | branches: {value: Node, condition?: Node}[] |
| Hole | hole | id: u16 |

op/kind 取上方对应枚举的 snake_case 值；IntegralKind::Multiple(n) 唯一例外为 {"multiple":n}，n=1..3。Piecewise 的 condition 缺省只允许最后一支。空数组在语法允许处保留；整数使用无前导零的十进制，SymbolId ≤u32::MAX，负数不允许；u16/u8 各守自身范围。Number.text 匹配 ^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$，拒绝 NaN/Inf，保留原拼写与 sig_digits，不转 f64 或约分；无有理数 JSON number，分数用 binary/div。字符串先 NFC，再按 Unicode 标量排序所得 UTF-8 键序编码；引号与反斜杠写 \" 与 \\，U+0008/0009/000A/000C/000D 写 \b、\t、\n、\f、\r，其余 U+0000–U+001F 写 \u00xx（小写十六进制），其他 Unicode 直接 UTF-8，不转义 /。sig_digits 由解析器从 text 计算后写入：尾数去掉符号、小数点与前导 0 后的数字个数（整数末尾 0 计入，全为 0 时取 1）；from_canonical_json 接受缺省（如 AST-14），缺省与显式值是不同 AST、哈希不同，不推断补齐。canonical_hash 只覆盖规范 AST 字节，不含绑定；绑定需另存独立哈希，不能改变本函数输入。

确定性 ID 与 seed（唯一所有者；UUID 全部按 RFC 网络序 16 字节，文本为小写连字符；字符串 NFC UTF-8，禁止 NUL）：

- NS_PACK = UUIDv5(NAMESPACE_URL, "urn:fml:pack")；条目 ID = UUIDv5(NS_PACK, pack_id + NUL + entry_key)，无尾 NUL，不含版本或 template。模板实例 ID 使用相同 namespace，name 追加 NUL+template_id，供升级去重，不能代替条目 ID。
- NS_CARD = UUIDv5(NAMESPACE_URL, "urn:fml:card")；卡 ID = UUIDv5(NS_CARD, revision_id 的16字节 + card_type 的 snake_case UTF-8 + NUL + template_id UTF-8)。同修订同题型同模板仅一张卡；不来自模板的题型 template_id 取空串（NUL 仍写入）。
- 包缓存修订 ID = UUIDv5(条目 ID 作 namespace, content_hash 的小写十六进制 ASCII)；content_hash 为CORE-16明确排除content_hash及派生revision.id后的条目规范JSON投影的BLAKE3，按条目而非整包计算。CORE-14 投影只调用本函数。
- NS_MERGE = UUIDv5(NAMESPACE_URL, "urn:fml:merge")；merge_choice ID = UUIDv5(NS_MERGE, item_id16 + 按16字节升序去重的 head UUID 拼接)。至少两头，无字符串分隔。
- seed = SHA-256(ASCII "fml/seed/v1" + NUL + session_id16 + card_id16 + question_index u32 大端) 的首8字节按小端 u64 解释；ChaCha8Rng::seed_from_u64 用锁定 rand_chacha 版本。其他用途必须另取 domain，不能复用本 seed。

上述规范化与编码依据 [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259) 与 [RFC 9562 UUIDv5](https://www.rfc-editor.org/rfc/rfc9562#section-5.5)。

补充黄金向量（与 AST-01～05 合起来覆盖全部 FormulaNode 变体；表中 JSON 就是期望字节，不得由被测实现生成）：

| 编号 | 规范 JSON |
| --- | --- |
| AST-06 | `{"id":"si:m","k":"unit"}` |
| AST-07 | `{"id":0,"k":"hole"}` |
| AST-08 | `{"branches":[{"condition":{"k":"relation","left":{"id":0,"k":"symbol"},"op":"gt","right":{"k":"number","sig_digits":1,"text":"1"}},"value":{"k":"number","sig_digits":1,"text":"1"}},{"value":{"id":0,"k":"symbol"}}],"k":"piecewise"}` |
| AST-09 | `{"differentials":[0],"integrand":{"id":0,"k":"symbol"},"k":"integral","kind":"indefinite"}` |
| AST-10 | `{"body":{"id":0,"k":"symbol"},"index":0,"k":"sum_or_limit","kind":"sum","lower":{"k":"number","sig_digits":1,"text":"1"},"upper":{"k":"number","sig_digits":1,"text":"1"}}` |
| AST-11 | `{"items":[{"id":0,"k":"symbol"},{"k":"number","sig_digits":1,"text":"1"}],"k":"vector"}` |
| AST-12 | `{"k":"matrix","rows":[[{"k":"number","sig_digits":1,"text":"1"}]]}` |
| AST-13 | `{"k":"relation","left":{"id":0,"k":"symbol"},"op":"eq","right":{"k":"number","sig_digits":1,"text":"1"}}` |
| AST-14 | `{"k":"number","text":"1.00e+0"}` |
| AST-15 | `{"id":0,"k":"symbol"}` |

```rust
pub fn pack_item_id(pack_id: &str, entry_key: &str) -> FormulaItemId;
pub fn pack_template_id(pack_id: &str, entry_key: &str, template_id: &str) -> Uuid;
pub fn card_id(revision: RevisionId, card_type: &str, template_id: &str /* 无模板为 "" */) -> Uuid;
pub fn pack_cache_revision_id(item: FormulaItemId, content_hash_hex: &str) -> RevisionId;
pub fn merge_choice_id(item: FormulaItemId, heads: &[RevisionId]) -> Uuid;
pub fn question_seed(session: Uuid, card: Uuid, question_index: u32) -> u64;
```

```rust
// crates/fml-ast/src/page.rs，纯数据，无I/O；page从0起，page_size 1..=200
pub struct Page<T> { pub items: Vec<T>, pub total: u32, pub page: u32, pub page_size: u32 }
```

**实现约束**
- 修订不可变：任何内容变化生成新 `FormulaRevision`，旧修订保留；条目只移动 `head`。
- 规范哈希只依赖 AST 语义（不含符号绑定，见上方规范 JSON 规则），不依赖源码空白与 LaTeX 写法，用于“语义往返不变”的判定。
- 纯数据 crate：无 I/O、无时钟（时间戳由调用方传入）。
- 外部前提：`uuid`、`blake3`、`serde`、`serde_json`、`proptest`（开发依赖）crate，版本按 ADR-V5-15 由首张使用卡开工时锁入 `Cargo.lock`。

**验收标准**
- [R10] 属性测试（proptest）：随机 AST 经 `canonical_json` → `from_canonical_json` → 再序列化逐字节一致；规范哈希稳定；AST-01～15 向量逐字节一致；含 U+0001 与换行的字符串分别规范化为 `\u0001` 与 `\n`；`pack_cache_revision_id` 与 `card_id`（空 template_id）写入 ids-v1.json 向量。
- [R19] 属性测试：每个节点的 NodePath 唯一，`node_at` 能取回该节点；`check_limits` 对 4096 节点、深度 64、64×16 矩阵通过，对 4097 节点、深度 65、65×1 矩阵、33×32（1056 元素）矩阵分别返回对应 `LimitViolation` 且不 panic。
- [R11] 单元测试：修改一条修订生成新 RevisionId，父修订字段指向旧修订，旧修订内容不变。

- [R19] AST-01～15的规范JSON逐条通过共享schema；AST08的对象分支通过，tuple分支拒绝；multiple的1/3通过、0/4拒绝，空矩阵及空行拒绝；Number.text的+.5、100.保留合法原文；i64的精确上下界通过、上下界外1拒绝。矩形一致性、节点总数/深度和Piecewise缺省条件仅末支等跨字段语义仍由本卡校验。

**规模**：约 450 行；`crates/fml-ast/`。

