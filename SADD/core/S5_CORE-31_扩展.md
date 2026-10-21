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
// 本卡拥有纯领域数据与object-safe分析端口；不引用fml-ffi::AnalysisResult
pub struct CandidateAnalysis { pub ast: Option<FormulaNode>, pub source_map: SourceMap,
    pub raw_symbols: Vec<RawSymbol>, pub symbols: SymbolEnv, pub check_result: CheckResult }
pub trait CandidateAnalyzer {
    fn analyze(&self, latex: &str, profile: &NotationProfile, user_decls: &[SymbolDecl],
               units: &dyn UnitRegistry, cancel: &CancelFlag) -> CandidateAnalysis;
}
pub struct PostOutput { pub candidates: Vec<Candidate> /* 至多3个 */, pub diagnostics: Vec<Diagnostic> /* 请求级 warning：RECOG_OUTPUT_REJECTED（每个被拒候选一条，args.index = 后端序号）、RECOG_ALL_CANDIDATES_INVALID */ }
pub fn postprocess(raw: &RawOutput, ctx: &RecognitionContext, profile: &NotationProfile, user_decls: &[SymbolDecl],
    units: &dyn UnitRegistry, cancel: &CancelFlag, analyzer: &dyn CandidateAnalyzer) -> Result<PostOutput, FmlError>;
pub fn apply_correction(c: &Candidate, span: &SymbolSpan, replacement: &str, profile: &NotationProfile,
    user_decls: &[SymbolDecl], units: &dyn UnitRegistry, cancel: &CancelFlag, analyzer: &dyn CandidateAnalyzer) -> Result<Candidate, FmlError>;
pub fn final_check(latex: &str, profile: &NotationProfile, user_decls: &[SymbolDecl], units: &dyn UnitRegistry,
    cancel: &CancelFlag, analyzer: &dyn CandidateAnalyzer) -> Result<CheckResult, FmlError>; // 保存前完整重解析/绑定/校验
```

- 评分 `score`（0..=1，仅查找模式用于排序）：原始分 = 可解析 0.4 + 绑定项 + 量纲项 + 后端置信度 × 0.2（None 计 0.1）+ 提示项；`score = 原始分 ÷ 1.1`（归一化而非截断，满分各项与提示加分仍可区分，结果落在 0..=1）。绑定项与量纲项按 `Candidate.validation`（= `CandidateAnalysis.check_result.validation`，ast 为 None 时 validation 为 None、两项均 0）：Verified / VerifiedPolymorphic → 0.2 + 0.2；Invalid → 0.2 + 0；Unresolved、Draft → 0 + 0。置信度为 NaN 或非有限按 None 处理，其余夹到 [0, 1]。提示项 = `symbol_hints` 中在该候选 SymbolEnv 字形里出现的不同项数 × 0.02，上限 0.1。排序按 score 降序，同分保持后端原序；分数比较用原始分的整数千分值，避免浮点误差改变顺序。
- 输入上限：`RawOutput` 候选数 > 10 时只按后端顺序处理前 10 个，其余忽略（不报错）；`RecognitionContext.symbol_hints` 多于 50 项、`user_corrections` 多于 20 项时纯函数只取前 50/20 项，FFI 适配对超限请求返回 `FFI_BAD_ARG`。
- 符号跨度：`symbol_spans` 每个 RawSymbol 出现一条，按源文本位置升序；`node_path` 与 `source_range`（候选 latex 的 UTF-8 字节区间 [start, end)）取自 CandidateAnalysis.source_map 中该符号节点的 CORE-06 SourceSpan；`alternatives` 只来自本卡内置形近字表（同组其余成员按表序，最多 5 个，不含原字形）：{v, ν}、{0, O, o, θ}、{l, 1, I, |}、{x, ×, χ}、{w, ω}、{p, ρ}、{a, α}、{B, β}、{u, μ}、{t, τ}、{n, η}、{e, ε}、{k, κ}、{S, 5}、{Z, 2}、{P, Ρ}，表外字形 alternatives 为空；表在 `post.rs` 内为常量，修改须同步测试向量。
- FFI op唯一表（上述纯算法不读仓储）：请求体只携带可序列化数据；fml-ffi处理层捕获一次CORE-56可用引擎Arc，从该Arc查notation_profile_id得到具体NotationProfile，并取同一快照units，把user_decls原样传入三个纯函数；未知方案返回NOTATION_UNBOUND，不回退默认方案。每个候选/校正后新文本各自解析取得AST和raw_symbols，再按profile/user_decls绑定为各自SymbolEnv，禁止解析前构造跨候选共用env或沿用旧SymbolId。recog.postprocess固定submit，body={raw,context,notation_profile_id,user_decls}，ok={candidates, diagnostics}（PostOutput），每个候选的分析受 ParseOptions.budget_ms 与 CORE-01 预算表“公式解析（≤256 节点）”“量纲校验”行约束，本卡不另设数字；recog.correct为call，body={candidate,span_index,replacement,notation_profile_id,user_decls}，ok={candidate}；recog.final_check为call，body={latex,notation_profile_id,user_decls}，ok=CheckResult。Invalid/Unresolved为成功校验结果，仅输入/预算故障为Err；这些Rust快照的完整跨语言schema仍随H6标pending，不以此表冒充已生成DTO。
- 分析适配唯一归本卡附属 `crates/fml-ffi/src/ops/recog_post.rs`：实现CandidateAnalyzer，调用CORE-56的analyze_source(latex, &ParseOptions { budget_ms: 100, allow_unicode: true }, profile, user_decls, units, false, cancel)，将其拥有的AnalysisResult逐字段搬入本卡CandidateAnalysis；不在fml-recognize复制parse→bind→check，也不令领域crate依赖fml-ffi。固定empirical=false，不从识别置信度放宽量纲校验。ast=None的解析诊断与原文仍保留，不伪造AST；校正重跑完整链路后用新source_map/AST生成跨度，不复用旧raw_symbols/symbols。CandidateAnalysis为Rust临时数据，不向既有持久化Candidate或H6 pending wire偷偷加字段；CORE-32无需迁移候选记录。
- 三个函数都在入口、逐候选/校正/终检前后检查同一CancelFlag，置位返回CORE-29的RECOG_CANCELLED；submit用任务旗标，call适配传本次调用旗标。Invalid/Unresolved/Draft及其全部诊断作为CheckResult成功返回，final_check不做“保存决定”，消费者按Q32确认；不是解析Error就丢失原文。输入过滤/大小故障仍按本卡码处理。
- 8 步：① 候选 LaTeX 解析（CORE-06 预算）；② 构造 AST；③ 符号表绑定（CORE-07）；④ 类型与量纲推导（CORE-09）；⑤ 按 `RecognitionContext` 重排（仅查找模式）；⑥ 取 Top-3；⑦ 逐符号校正；⑧ 保存前完整校验。
- 结果语义：被白名单拒绝的候选丢弃且不进入候选列表，并在 `PostOutput.diagnostics` 记一条 `RECOG_OUTPUT_REJECTED`；未被拒的候选即使无法解析也保留（原文、ast = None、validation = None、带解析诊断）；全部候选被拒或无一可解析时仍返回 Ok，diagnostics 追加一条 `RECOG_ALL_CANDIDATES_INVALID`（全部被拒时 candidates 为空，界面回到手工输入）；只有 `RECOG_OUTPUT_TOO_LARGE`、取消与输入/预算故障为 Err。
- 作答模式：跳过第 ⑤ 步；候选顺序保持后端原序；不做任何自动替换；量纲诊断只显示，不用于排序或判分。
- 白名单过滤：候选去掉首尾空白与 `$`、`\[` 等定界符后，只允许 CORE-06 子集中的命令与可打印字符；出现 `<script`、`http://`、`https://`、`\href`、`\url`、`\input`、`\include`、函数调用形式的 JSON 或代码围栏即拒绝该候选。
- 错误码：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `RECOG_OUTPUT_TOO_LARGE` | error | 否 | `RawOutput` 全部候选 LaTeX 的 UTF-8 总长 > 262 144 字节（候选数超过 10 不报错，见“输入上限”） |
| `RECOG_OUTPUT_REJECTED` | warning | 否 | 某候选命中白名单过滤规则（该候选丢弃，其余继续；作为 `PostOutput.diagnostics` 项返回，不是 Err） |
| `RECOG_ALL_CANDIDATES_INVALID` | warning | 否 | 全部候选被拒绝或无法解析（作为 `PostOutput.diagnostics` 项返回；未被拒的原文仍在 candidates 中供手工修改） |
| `RECOG_SPAN_INVALID` | error | 否 | `apply_correction` 的 span 不属于该候选，或替换文本为空 |

**实现约束**
- 识别输出永远是不可信输入：先做长度检查与白名单过滤，再交给解析器。
- 无可靠置信度时 `confidence` 为 None，界面提示用户确认，不编造分数。
- 不能解析的候选仍显示原文，供用户手工修改。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-31_TEST.md](../Test/core/S5_CORE-31_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 400 行；主包 `crates/fml-recognize/src/post.rs`（类型与逐候选分析 trait、过滤与预算、8 步编排、评分排序、符号跨度与形近字表、校正与终检，约 310），附属 `crates/fml-ffi/src/ops/recog_post.rs`（三个 op 处理、分析上下文构造与 CandidateAnalyzer 薄适配，约 90；parse→bind→check 共用函数由 CORE-56 拆出的引擎编排卡实现，不计）。fml-recognize 不依赖 fml-ffi，对 CORE-56 的依赖只来自这个附属适配。

