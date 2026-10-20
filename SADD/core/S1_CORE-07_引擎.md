### CORE-07 符号表、记号方案与常数集

**目标**：把解析出的字形绑定为有含义的符号（变量、常数、函数、单位），支持国内默认与 ISO 两套记号方案互切，并提供分来源的物理常数集。

**范围**
- 包含：`SymbolEnv`、`NotationProfile`（`cn-default`、`iso`）、`SymbolAlias`、`ConstantSet`（exact / textbook / given）、绑定与歧义诊断、显示切换。
- 不包含：量纲推导（CORE-09）；单位定义（CORE-08）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-06

**接口契约**

```rust
// crates/fml-notation/src/lib.rs
// SymbolEnv、SymbolDecl、SymbolRole、TypeDecl 定义见 CORE-05；RawSymbol 见 CORE-06
pub struct NotationProfile { pub id: String, pub aliases: Vec<SymbolAlias>, pub defaults: Vec<(String, String)> }
pub struct SymbolAlias { pub glyph: String, pub meaning_key: String, pub context: Option<String> }

pub fn bind(raw: &[RawSymbol], ast: &FormulaNode, profile: &NotationProfile,
            user_decls: &[SymbolDecl]) -> (SymbolEnv, Vec<Diagnostic>);
pub fn display_glyph(decl: &SymbolDecl, profile: &NotationProfile) -> String; // 只改显示，不改 SymbolId 与 AST

// ConstantSource、ConstantValue 唯一定义见 CORE-05
pub struct ConstantSet { pub id: String, pub values: Vec<ConstantValue> }
pub fn resolve_constant(key: &str, given: &[ConstantValue], textbook: &ConstantSet, exact: &ConstantSet)
    -> Option<ConstantValue>;   // 优先级 given → textbook → exact
```

- FFI op：`notation.profiles`、`notation.bind`、`notation.display`、`constants.resolve`（读取引擎快照的处理适配在 CORE-56 的 `ops/notation.rs`）。
- 国内默认方案要点：ν 为物质的量、n 为分子数密度、k 为玻尔兹曼常数、V 为体积；tg/arctg 与 tan/arctan 等价；lg 为常用对数；A* 在线性代数语境为伴随矩阵、在 ISO 方案为共轭转置；D(X) 与 Var(X) 等价；组合数 C_n^k。S1 的方案与常数由 CORE-56 编译期注入，S4 内容包只补充和更新（下游说明，非契约）。
- 错误码（本卡唯一定义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `NOTATION_AMBIGUOUS` | warning | 否 | 同一方案内同字形多义；该符号保持 Unresolved，待用户声明 |
| `NOTATION_LOG_BASE` | warning | 否 | 未写底数的 log；保持 Unresolved |
| `NOTATION_UNBOUND` | error | 否 | 请求的 notation_profile_id 不在当前引擎快照中 |
| `NOTATION_CONSTANT_CONFLICT` | info | 否 | 给定常数值与教材值不一致；按 given 计算并显示所用值 |


**op 字段约定（ok 负载，外层信封见 CORE-03）**
| op（均call） | body | ok |
| --- | --- | --- |
| notation.profiles | `{}` | `{profiles: [NotationProfile]}` |
| notation.bind | `{raw: [RawSymbol], ast: FormulaNode, notation_profile_id: string, user_decls: [SymbolDecl]}` | `{symbols: SymbolEnv, diagnostics: [Diagnostic]}` |
| notation.display | `{decl: SymbolDecl, notation_profile_id: string}` | `{glyph: string}` |
| constants.resolve | `{key: string, given: [ConstantValue], textbook_set_id: string}` | `{value?: ConstantValue}` |
字段均必填，value省略表示未找到；错误复用本卡 NOTATION_*。CORE-56 在同一 EngineSnapshot 按 id 查方案/常数集，不由纯 bind 自行查全局。例：`notation.profiles` 的 body=`{}`，ok=`{"profiles":[{"id":"cn-default","aliases":[],"defaults":[]}]}`；`notation.display` 的 decl按CORE-05、profile=cn-default，成功glyph="x"；bind空raw/空声明与Number节点得空symbols/diagnostics；constants不存在的key得`{}`。复杂 AST/声明的具体schema由其所有者供给，不能以这些空样例冒充完整闭合。

FFI错误镜像（不重定义代码；通用信封错误见CORE-03；读取快照的适配另由CORE-56（下游说明，非契约）统一返回ENGINE_UNAVAILABLE）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| constants.resolve | NOTATION_CONSTANT_CONFLICT |
| notation.bind | NOTATION_UNBOUND、NOTATION_AMBIGUOUS、NOTATION_LOG_BASE、AST_JSON_INVALID、PARSE_LIMIT_EXCEEDED |
| notation.display | 无业务错误；通用信封错误仍适用 |
| notation.profiles | 无业务错误；通用信封错误仍适用 |

**实现约束**
- 一个字形在一个方案内最多映射到一个 SymbolId；记号能力分三级（可输入、可渲染、可计算），不宣称字形与含义一一对应。
- 绑定不改 AST 结构；切换方案只改显示，规范 AST 哈希与 SymbolId 不变。
- 常数集带版本；界面显示所用值、来源与版本；中间计算不修约。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-07_TEST.md](../Test/core/S1_CORE-07_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 400 行（不含方案数据）；`crates/fml-notation/`。

