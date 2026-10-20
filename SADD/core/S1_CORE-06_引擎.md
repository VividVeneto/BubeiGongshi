### CORE-06 LaTeX 子集解析与导出

**目标**：把 LaTeX 子集与 Unicode/ISO 数学符号输入安全地解析为 AST，并能从 AST 导出 LaTeX 与 Unicode 文本。

**范围**
- 包含：词法与语法分析、命令白名单、Unicode 词法别名表、源码映射（AST 节点 → 字符区间）、错误定位与修复建议、LaTeX/Unicode 导出、ISO 80000-2 符号能力清单。
- 不包含：符号含义绑定与记号方案（CORE-07）；量纲（CORE-09）；排版（CORE-12）。

**依赖**：CORE-01、CORE-02、CORE-05

**接口契约**

```rust
// crates/fml-latex/src/lib.rs
pub struct ParseOptions { pub budget_ms: u32 /* 默认 100 */, pub allow_unicode: bool /* 默认 true */ }
pub struct SourceMap { pub spans: Vec<(NodePath, (u32, u32))> }   // UTF-8 字节区间 [start, end)
pub enum RawHint { Plain, FunctionHead /* 后接括号或函数参数 */, Differential /* d 或 ∂ 之后 */, BoundIndex /* 求和/积分/极限下标变量 */, UnitPosition /* 数字之后的单位位置 */ }
pub struct RawSymbol {
    pub id: SymbolId,                   // 解析时按“字形 + 下标”首次出现顺序从 0 分配，AST 中的 Symbol 引用此 id
    pub glyph: String, pub subscript: Option<String>,
    pub occurrences: Vec<NodePath>, pub hint: RawHint,
}
pub struct ParseResult {
    pub ast: Option<FormulaNode>,       // 有 Error 级诊断时可为 None，草稿原文仍保留
    pub source_map: SourceMap,
    pub raw_symbols: Vec<RawSymbol>,    // 未绑定的字形与位置，交给 CORE-07
    pub diagnostics: Vec<Diagnostic>,
}
pub fn parse(source: &str, opts: &ParseOptions, cancel: &CancelFlag) -> ParseResult;
pub fn export_latex(ast: &FormulaNode, symbols: &SymbolEnv) -> String;
pub fn export_unicode(ast: &FormulaNode, symbols: &SymbolEnv) -> Result<String, Vec<Diagnostic>>; // 无法无损导出的节点列出诊断
```

- FFI op（DTO 主版本 1，同步调用）：

| op | 请求 | 响应 |
| --- | --- | --- |
| `engine.parse` | `{"source": string（≤ 64 KiB）, "allow_unicode": bool（默认 true）}` | `{"ast": AST 规范 JSON &#124; null, "source_map": [{"path": "0.1", "start": int, "end": int}], "raw_symbols": [{"id", "glyph", "subscript"?, "occurrences": ["0.1"], "hint": "plain"&#124;…}], "diagnostics": [DiagnosticDto]}`。 |
| `engine.export` | `{"revision_ast": AST 规范 JSON, "symbols": SymbolEnv JSON, "format": "latex"&#124;"unicode"}` | `{"text": string}`，Unicode 无法无损导出时返回业务错误 `PARSE_UNICODE_NOT_EXPORTABLE`，诊断列出节点。 |


- `engine.parse` 预算只取 CORE-03 信封 `budget_ms`（u32，1–1000，缺省100），处理层传入 ParseOptions；body 不接受该字段，出现时按 DTO 非法字段拒绝，不存在双值优先级。
- 语法白名单（冻结，扩展需走附录 A ADR）：分数 `\frac\dfrac\tfrac`；上下标；根式 `\sqrt[n]{}`；三角/反三角/指数/对数（含国内写法 tg、arctg、lg）；关系符；向量 `\vec\boldsymbol`、矩阵环境 pmatrix/bmatrix/vmatrix/matrix；导数 `\mathrm{d}`、`\partial`、`\dot`、`\ddot`、撇号；积分 `\int\iint\iiint\oint` 与上下限；`\sum\prod\lim`；`\nabla`、`\cdot`、`\times`；分段 cases 环境；概率统计 P(·)、E、D/Var、组合数；括号 `\left\right`；编辑器空位 `\fmlhole`（ADR-V5-17，可出现在任何表达式位置，不能出现在积分变量、求和与极限指标等要求单个符号的位置，否则报 `PARSE_SYNTAX`）。
- 禁止命令：宏定义（def、newcommand 等）、文件引入（input、include）、写文件（write）、网址与超链接、宏包加载、任意 shell 转义。遇到时返回 `PARSE_FORBIDDEN_COMMAND`，不执行、不展开。
- 错误码（每条诊断带 `input_range`、片段与修复建议键）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `PARSE_SYNTAX` | error | 否 | 括号不配对、缺参数、环境未闭合、意外记号 |
| `PARSE_UNSUPPORTED_COMMAND` | error | 否 | 不在白名单、也不在禁止清单中的命令（如 `\overbrace`），保留为草稿 |
| `PARSE_FORBIDDEN_COMMAND` | error | 否 | 禁止清单中的命令 |
| `PARSE_TIMEOUT` | error | 是 | 超过 `budget_ms` 或被取消 |
| `PARSE_UNICODE_NOT_EXPORTABLE` | warning | 否 | 节点无对应 Unicode 写法（如矩阵、多重上下限） |
| `PARSE_HOLE_UNFILLED` | error | 否 | 源码含 `\fmlhole`；每个空位一条诊断，`ast` 仍返回（含 `Hole` 节点）供编辑器排版 |

- 往返测试向量（`contracts/vectors/latex-roundtrip.yaml`；“等价”指 `canonical_hash` 相同）：

| 编号 | 输入 | 期望 |
| --- | --- | --- |
| LX-01 | `\frac{a}{b}` | 与 `a/b` 等价；`export_latex` 输出 `\frac{a}{b}` |
| LX-02 | `\mathrm{tg}\,x` 与 `\tan x` | 两者等价，`FunctionId("tan")` |
| LX-03 | `\sqrt[3]{x}` | `root(x, 3)`，导出后再解析等价 |
| LX-04 | `\int_0^1 x^2\,\mathrm{d}x` | `Integral{Definite}`，积分变量 hint 为 `bound_index` |
| LX-05 | `\begin{pmatrix}1&2\\3&4\end{pmatrix}` | 2×2 `Matrix`；Unicode 导出返回 `PARSE_UNICODE_NOT_EXPORTABLE` |
| LX-06 | `F = ma` 与 Unicode `F＝ma`（全角等号经别名表） | 两者等价 |
| LX-07 | `\frac{a}{` | `PARSE_SYNTAX`，`input_range` 为 [8, 9)（未闭合的 `{`） |
| LX-08 | `\input{x}` | `PARSE_FORBIDDEN_COMMAND`，`input_range` 为 [0, 6)，`ast` 为 null |
| LX-09 | `\overbrace{a}` | `PARSE_UNSUPPORTED_COMMAND`，原文保留 |
| LX-10 | `E = mc^2` | `raw_symbols` 依次为 E(0)、m(1)、c(2) |
| LX-11 | `\frac{\fmlhole}{b}` | `ast` 非 null，分子为 `Hole(0)`；一条 `PARSE_HOLE_UNFILLED`，`input_range` 为 [6, 14) |
- 符号能力清单：`contracts/vectors/iso80000-2.yaml`，每个符号标注 `input / render / compute` 三项能力，与实际能力一致。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `PARSE_LIMIT_EXCEEDED` | CORE-05 | 超过 CORE-05 `limits` 任一上限 |

FFI错误镜像（不重定义代码；通用信封错误见CORE-03）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| engine.export | AST_JSON_INVALID、PARSE_LIMIT_EXCEEDED、PARSE_HOLE_UNFILLED、PARSE_UNICODE_NOT_EXPORTABLE |
| engine.parse | PARSE_SYNTAX、PARSE_FORBIDDEN_COMMAND、PARSE_UNSUPPORTED_COMMAND、PARSE_TIMEOUT、PARSE_HOLE_UNFILLED、PARSE_LIMIT_EXCEEDED |

**实现约束**
- 原文按字节保留；Unicode 只经显式别名表映射，不做全局兼容规范化（NFKC）。中文输入法组合期间（composition）不触发解析。
- 往返要求是“语义往返”：parse(export(ast)) 的规范哈希与原 AST 相同；不承诺 LaTeX 与 Unicode 文本逐字双射，无法无损导出的符号在编辑器显式提示。
- 不支持的结构保留为草稿并定位，不得静默丢弃。
- 手写递归下降或 PEG 解析器；禁止正则拼接解析、动态代码执行；输入长度、深度、节点数、时间四重预算（CORE-05 `limits`），每 100 ms 检查取消。
- 外部前提：模糊测试用 `cargo-fuzz`，需要 nightly 工具链（仅 CI 模糊测试任务使用，nightly 日期与 cargo-fuzz 版本见 `tools/toolchain.versions` 的 `fuzz_nightly=`、`cargo_fuzz=`，ADR-V5-15）。

**验收标准**
- [R10] 往返向量 LX-01～LX-11 全部满足期望。
- [R10] 语料测试 `tests/fixtures/formulas/`：每条含 LaTeX、Unicode、AST JSON、期望诊断与来源，覆盖高中数学、高中物理、高等数学、大学物理；≥100 条冻结语法代表式（分数、矩阵、重积分、曲线积分、∇、级数、分段）全部通过。
- [R09] ISO 80000-2 清单逐项做 Unicode↔LaTeX 语义往返，规范哈希不变；清单能力标注与实际行为一致。
- [R19] 错误定位：语法错误、未支持命令的诊断区间精确到字符；禁用命令不执行；64 KiB、4096 节点、深度 64、矩阵32×32（1024元素）通过、33×32因元素数超限拒绝、65×1因单边超限拒绝、越界返回 `PARSE_LIMIT_EXCEEDED`，100 ms 内可取消。
- [R19] 模糊测试（cargo-fuzz）24 小时无 panic、无越界、无无限递归。
- [R03] 性能：≤256 节点的公式解析满足 CORE-01 全局资源预算表“公式解析（≤256 节点）”行；测量方法：criterion 基准在两端参考机上取 P95。

**规模**：约 500 行（不含语料）；`crates/fml-latex/`。语料文件随卡提交但不计行数。

