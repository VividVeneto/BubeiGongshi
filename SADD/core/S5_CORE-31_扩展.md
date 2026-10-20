### CORE-31 识别候选后处理与忠实转写

**目标**：把任何后端返回的不可信候选统一转成经过解析、绑定、量纲校验并按上下文排序的候选，供用户逐符号校正后保存或判分。

**范围**
- 包含：8 步统一后处理、Top-3 选择、逐符号校正数据结构、作答模式的忠实转写保护、对识别输出的预算与过滤。
- 不包含：识别会话持久化（CORE-32）；界面（CORE-40）；判分（CORE-18）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-06、CORE-07、CORE-08、CORE-09、CORE-29、CORE-56

**接口契约**

```rust
// crates/fml-recognize/src/post.rs
pub struct Candidate { pub latex: String, pub ast: Option<FormulaNode>, pub validation: Option<Validation>,
                       pub score: f32, pub diagnostics: Vec<Diagnostic>, pub symbol_spans: Vec<SymbolSpan> }
pub struct SymbolSpan { pub node_path: NodePath, pub source_range: (u32, u32), pub alternatives: Vec<String> }
pub fn postprocess(raw: &RawOutput, ctx: &RecognitionContext, env: &SymbolEnv, units: &dyn UnitRegistry) -> Result<Vec<Candidate>, FmlError>; // 至多 3 个
pub fn apply_correction(c: &Candidate, span: &SymbolSpan, replacement: &str, env: &SymbolEnv) -> Result<Candidate, FmlError>;
pub fn final_check(latex: &str, env: &SymbolEnv, units: &dyn UnitRegistry) -> Result<CheckResult, FmlError>; // 保存前完整校验
```

- 评分 `score`（0..=1，仅查找模式用于排序）：可解析 0.4 + 绑定无未知符号 0.2 + 量纲一致 0.2 + 后端置信度 × 0.2（None 计 0.1）；与 `symbol_hints` 每命中一个加 0.02，上限 0.1；总分最后截断到 1.0（各项全满时 0.4+0.2+0.2+0.2+0.1 会达 1.1，须截断以满足 0..=1）；同分保持后端原序。
- FFI op唯一表（上述纯算法不读仓储）：请求体只携带可序列化数据，符号环境与单位注册表由 fml-ffi 处理层按 `notation_profile_id` 与 `user_decls` 从 CORE-56 当前引擎快照构造后传给纯函数，与 `engine.check` 同一规则。recog.postprocess固定submit，body={raw,context,notation_profile_id,user_decls}，ok={candidates}，预算30ms×候选数；recog.correct为call，body={candidate,span_index,replacement,notation_profile_id,user_decls}，ok={candidate}；recog.final_check为call，body={latex,notation_profile_id,user_decls}，ok=CheckResult。Invalid/Unresolved为成功校验结果，仅输入/预算故障为Err；这些Rust快照的完整跨语言schema仍随H6标pending，不以此表冒充已生成DTO。
- 8 步：① 候选 LaTeX 解析（CORE-06 预算）；② 构造 AST；③ 符号表绑定（CORE-07）；④ 类型与量纲推导（CORE-09）；⑤ 按 `RecognitionContext` 重排（仅查找模式）；⑥ 取 Top-3；⑦ 逐符号校正；⑧ 保存前完整校验。
- 作答模式：跳过第 ⑤ 步；候选顺序保持后端原序；不做任何自动替换；量纲诊断只显示，不用于排序或判分。
- 白名单过滤：候选去掉首尾空白与 `$`、`\[` 等定界符后，只允许 CORE-06 子集中的命令与可打印字符；出现 `<script`、`http://`、`https://`、`\href`、`\url`、`\input`、`\include`、函数调用形式的 JSON 或代码围栏即拒绝该候选。
- 错误码：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `RECOG_OUTPUT_TOO_LARGE` | error | 否 | `RawOutput` 全部候选 LaTeX 总长 > 256 KiB，或候选数 > 10 |
| `RECOG_OUTPUT_REJECTED` | warning | 否 | 某候选命中白名单过滤规则（该候选丢弃，其余继续） |
| `RECOG_ALL_CANDIDATES_INVALID` | warning | 否 | 全部候选被拒绝或无法解析（界面仍显示原文供手工修改） |
| `RECOG_SPAN_INVALID` | error | 否 | `apply_correction` 的 span 不属于该候选，或替换文本为空 |

**实现约束**
- 识别输出永远是不可信输入：先做长度检查与白名单过滤，再交给解析器。
- 无可靠置信度时 `confidence` 为 None，界面提示用户确认，不编造分数。
- 不能解析的候选仍显示原文，供用户手工修改。

**验收标准**
- [R06] 后处理单元测试：Fake 后端返回 5 个候选（含非法 LaTeX、量纲错误、正确式），输出 ≤ 3 个，且查找模式下正确式排第一。
- [R13] 量纲错误候选带诊断且保存时被 `final_check` 阻止。
- [R04] 作答模式：返回 `m v^2`（漏 ½）时候选不被纠正为 ½mv²，交给判分后判错（与 CORE-18 GX-05 联测）。
- [R07] 含脚本标签、超长输出与外链的返回被拒绝。

**规模**：约 380 行；主包 `crates/fml-recognize/src/post.rs`；附属 `crates/fml-ffi/src/ops/recog_post.rs`（三个 op 的薄适配，约 40 行）。fml-recognize 不依赖 fml-ffi，对 CORE-56 的依赖只来自这个附属适配。

