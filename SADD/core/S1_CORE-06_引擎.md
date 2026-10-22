### CORE-06 LaTeX 子集解析

**目标**：把 LaTeX 子集与 Unicode/ISO 数学符号输入安全地解析为 AST；语义导出由 CORE-92 提供。

**范围**
- 包含：词法与语法分析、命令白名单、Unicode 词法别名表、源码映射（AST 节点 → 字符区间）、错误定位与修复建议、ISO 80000-2 符号能力清单。
- 不包含：LaTeX/Unicode 导出与 engine.export（CORE-92）；符号含义绑定与记号方案（CORE-07）；量纲（CORE-09）；排版（CORE-12）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05

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
```

- FFI op（DTO 主版本 1，同步调用）：

| op | 请求 | 响应 |
| --- | --- | --- |
| `engine.parse` | `{"source": string（≤ 64 KiB）, "allow_unicode": bool（默认 true）}` | `{"ast": AST 规范 JSON &#124; null, "source_map": [{"path": "0.1", "start": int, "end": int}], "raw_symbols": [{"id", "glyph", "subscript"?, "occurrences": ["0.1"], "hint": "plain"&#124;…}], "diagnostics": [DiagnosticDto]}`。 |


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
| `PARSE_HOLE_UNFILLED` | error | 否 | 源码含 `\fmlhole`；每个空位一条诊断，`ast` 仍返回（含 `Hole` 节点）供编辑器排版 |

- LX-01～LX-11 的完整往返向量与导出期望迁 CORE-92；本卡负责其解析侧 AST、RawSymbol、SourceMap 与诊断。
- 符号能力清单：`contracts/vectors/iso80000-2.yaml`，每个符号标注 `input / render / compute` 三项能力，与实际能力一致。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `PARSE_LIMIT_EXCEEDED` | CORE-05 | 超过 CORE-05 `limits` 任一上限 |

FFI错误镜像（不重定义代码；通用信封错误见CORE-03）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| engine.parse | PARSE_SYNTAX、PARSE_FORBIDDEN_COMMAND、PARSE_UNSUPPORTED_COMMAND、PARSE_TIMEOUT、PARSE_HOLE_UNFILLED、PARSE_LIMIT_EXCEEDED |

**实现约束**
- 原文按字节保留；Unicode 只经显式别名表映射，不做全局兼容规范化（NFKC）。中文输入法组合期间（composition）不触发解析。
- 解析不依赖 CORE-92；由 CORE-92 消费 parse 进行规范哈希语义往返验收。不支持的导出不会改变本卡 AST。
- 不支持的结构保留为草稿并定位，不得静默丢弃。
- 手写递归下降或 PEG 解析器；禁止正则拼接解析、动态代码执行；输入长度、深度、节点数、时间四重预算（CORE-05 `limits`），每 100 ms 检查取消。
- 外部前提：模糊测试用 `cargo-fuzz`，需要 nightly 工具链（仅 CI 模糊测试任务使用，nightly 日期与 cargo-fuzz 版本见 `tools/toolchain.versions` 的 `fuzz_nightly=`、`cargo_fuzz=`，ADR-V5-15）。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-06_TEST.md](../Test/core/S1_CORE-06_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约780行，分阶段：①词法140、核心表达式190、SourceMap/诊断/预算100及 engine.parse 附属适配20，共450行；②结构语法330行。主包 `crates/fml-latex/src/{lexer,parser,structures,diagnostics}.rs` 760行；附属 `crates/fml-ffi/src/ops/latex.rs` 的 engine.parse 20行。每阶段独立构建/测试：①核心语法及拒绝尚未交付结构；②完整冻结白名单与限额；语料、数据、生成物、自测不计。原1080行另300行归CORE-92。

