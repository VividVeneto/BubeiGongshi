### CORE-92 LaTeX 与 Unicode 语义导出

**目标**：把已构造的 AST 无损导出为冻结 LaTeX 子集或 Unicode 文本，并验证语义往返。

**范围**
- 包含：全 AST 导出、优先级括号、规范函数名、矩阵/微积分/分段与 Hole；Unicode 不能无损表示时逐节点诊断；engine.export 处理与登记。
- 不包含：词法/解析/SourceMap（CORE-06）；符号绑定（CORE-07）；排版（CORE-12、CORE-94）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-06

**接口契约**

```rust
// crates/fml-latex/src/lib.rs；本卡唯一实现，CORE-06 不调用导出函数
pub fn export_latex(ast: &FormulaNode, symbols: &SymbolEnv) -> String;
pub fn export_unicode(ast: &FormulaNode, symbols: &SymbolEnv) -> Result<String, Vec<Diagnostic>>;
```

| op | 请求 | 响应 |
| --- | --- | --- |
| engine.export | {revision_ast: AST规范JSON, symbols: SymbolEnv JSON, format: latex或unicode} | {text: string}；Unicode无法无损导出返回PARSE_UNICODE_NOT_EXPORTABLE，并列出对应节点诊断。 |

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `PARSE_UNICODE_NOT_EXPORTABLE` | warning | 否 | 节点无对应Unicode写法（如矩阵、多重上下限） |

FFI错误镜像（不重定义）：engine.export = AST_JSON_INVALID、PARSE_LIMIT_EXCEEDED（CORE-05），PARSE_HOLE_UNFILLED（CORE-06），PARSE_UNICODE_NOT_EXPORTABLE（本卡）；信封/句柄/取消复用CORE-03。

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

**实现约束**
- 导出覆盖CORE-06冻结白名单对应全AST；parse(export(ast))的canonical_hash与原AST相同，不承诺原文逐字双射。
- Unicode无法无损导出的节点必须列出诊断，不得静默丢弃或有损降级；编辑器提示由消费者负责。
- Hole规范导出为`\fmlhole`；语法与符号位禁用规则仍由CORE-06定义。规范名遵循CORE-06，不引入未冻结宏。
- ISO80000-2能力清单仍由CORE-06管输入能力数据；本卡核对导出实际能力，不重复生成资源。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-92_TEST.md](../Test/core/S1_CORE-92_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约300行；主包 `crates/fml-latex/src/export_{latex,unicode}.rs` 280行（LaTeX170、Unicode110），附属 `crates/fml-ffi/src/ops/latex.rs` 的engine.export处理/登记20行；语料/能力表/生成物与自测不计。单阶段以导出模块及解析内核独立构建、语义往返测试为交付。
