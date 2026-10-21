### CORE-79 公式检索、差异与导入

**目标**：在CORE-14条目/修订仓储上提供确定性检索、源码/AST差异、代入候选与逐行批量导入，并提供可复用的分析/重解析注入接缝。

**范围**
- 包含：LibraryQueryRepo、搜索与筛选、修订diff、候选池、LaTeX/CSV导入、行级诊断；分析注入trait与本卡fml-ffi薄适配。
- 不包含：条目/修订写入与表迁移（CORE-14）；解析/绑定/校验算法；界面；第三方diff crate。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-09、CORE-11、CORE-13、CORE-14、CORE-56

**接口契约**

```rust
// crates/fml-store/src/library/query.rs；SourceFilter/ValidationFilter/MasteryState/ItemSummary/NewRevision仍由CORE-14定义
pub struct RevisionDiff { pub source: Vec<TextHunk> /* 行级 unified diff */, pub ast: Vec<AstChange> }
pub struct TextHunk { pub old_start: u32, pub old_len: u32, pub new_start: u32, pub new_len: u32, pub lines: Vec<String> /* 前缀 ' ' '-' '+' */ }
pub enum AstChange { Added { path: NodePath }, Removed { path: NodePath }, Changed { path: NodePath, before: String, after: String } }
pub enum ImportSource { Latex(String) /* 每行一个公式，空行与 % 开头行忽略 */, Csv(String) }
pub struct SearchQuery { pub text: Option<String>, pub subject: Option<String>, pub course: Option<String>,
                         pub tags: Vec<String>, pub source: Option<SourceFilter>, pub dimension: Option<DimensionFull>,
                         pub role: Option<SymbolRole>, pub mastery: Option<MasteryState>, pub validation: Option<ValidationFilter>,
                         pub trashed: bool /* 默认 false；true 时只返回回收站条目 */,
                         pub page: u32, pub page_size: u32 /* ≤ 100 */ }
pub trait LibraryQueryRepo {
    fn search(&self, q: &SearchQuery) -> Result<Page<ItemSummary>, FmlError>;
    fn diff(&self, a: RevisionId, b: RevisionId) -> Result<RevisionDiff, FmlError>;   // 源码差异 + AST 节点差异
    fn candidate_rows(&self, slot: &SlotRef, limit: u32) -> Result<Vec<CandidateRow>, FmlError>; // CO-28：Store 只给原始行，output_type 由适配层补

    fn import_batch(&self, rows: ImportSource /* Latex(String) | Csv(String) */) -> Result<ImportReport, FmlError>;
}
pub struct CandidateRow { pub revision: RevisionId, pub output: SymbolId, pub subject: String,
                          pub ast: FormulaNode, pub symbols: SymbolEnv }   // 每个 Verified/VerifiedPolymorphic 修订中单独构成等式一侧的符号各一行
pub struct ImportReport { pub accepted: u32, pub rejected: Vec<(u32 /* 行号，从 1 起，含表头 */, Vec<Diagnostic>)> }
// crates/fml-store/src/library/analysis.rs：只含纯数据与注入接口，不依赖fml-ffi
pub struct RevisionAnalysis { pub ast: FormulaNode, pub symbols: SymbolEnv, pub conditions: Vec<FormulaNode>,
                            pub validation: Validation, pub diagnostics: Vec<Diagnostic> }
pub trait RevisionAnalyzer {
    fn analyze_revision(&self, source_latex: &str, user_decls: &[SymbolDecl], notation_profile_id: &str) -> Result<RevisionAnalysis, FmlError>;
}
```

- 搜索语义：`text` 走 FTS5（标题、标签、LaTeX 源码、符号名，`trigram case_sensitive 0` 分词，连续子串匹配；SQLCipher 的 SQLite 必须≥3.34.0 且启用 FTS5）；多个筛选条件为“与”；`tags` 为“全部包含”；输入先 NFC，英文按SQLite同一折叠规则；查询≥3个Unicode标量时用参数化 MATCH（双引号内原样短语，双引号转义），1～2个标量时对相同投影列作参数化 LIKE，显式 ESCAPE 转义 %/_/反斜杠，空串等同无text；两路径排序统一为 updated_at_ms 降序、id 升序，FTS相关度只作后续优化，无 `text` 时按 `updated_at_ms` 降序；`page` 从 0 起，`page_size` 默认 50、上限 100，越界返回空页；`trashed = false`（默认）时回收站条目不出现，`trashed = true` 时只返回回收站条目、无 `text` 时按 `trashed_at_ms` 降序。
- CSV 列：`title,subject,latex,tags,symbol_decls_json`，UTF-8（可带 BOM），首行为表头，RFC 4180 引号规则；`tags` 以分号分隔；`symbol_decls_json` 可空，非空时为 `[SymbolDecl]` JSON；单次导入 ≤ 5000 行、≤ 8 MiB，超出整批拒绝（`LIB_IMPORT_TOO_LARGE`）。
- FTS 能力依据 SQLite 官方 https://sqlite.org/fts5.html#the_trigram_tokenizer：少于3个标量的 MATCH 不命中，故必须有上述 LIKE 路径；两路径都参数化，不能把用户文本直接拼成 SQL。

- 唯一登记op：`library.search`（SearchQuery→Page<ItemSummary>）、`library.diff`（两RevisionId→RevisionDiff）、`library.substitution_pool`（`{slot,limit}`，默认50、上限200，返回 `Vec<Candidate>` 供CORE-11排序：本卡 `library_analysis.rs` 适配在 Store.read 内取 `candidate_rows` 后释放读锁，再用同一 CORE-56 快照的单位对每行调用 CORE-09 `check(ast, symbols, units, false, cancel)`，`output_type` 取 typed 中该 output 符号按 walk 先序首个 Symbol 节点的类型（已 resolve）；重算结果不是 Verified/VerifiedPolymorphic 的行省略。Store 不运行 check，fml-store 不依赖 fml-type 的 check 函数）、`library.import`（ImportSource→ImportReport，长任务）。DTO字段与原结构同名，CORE-03映射；条目/历史/恢复op仍归CORE-14。
- 导入与重解析只经RevisionAnalyzer。trait定义在本卡；实现位于本卡编写的`crates/fml-ffi/src/ops/library_analysis.rs`，取得CORE-56同一Arc快照后复用其parse→bind→check分析函数；snapshot()?、unavailable与expected_generation检查均在领域调用前。本适配在 Store.read 闭包中取得导入所需用户声明/方案/单位只读副本后释放读锁，再调用 CORE-56 的纯 analyze_source；不接收 WriteTx/Connection，不得在同步写事务内调用。CORE-26/66 的同步重解析改用 CORE-13 RemoteRevisionAnalyzer 接缝及各自 S6 事务适配；只共享 CORE-56 纯函数，不复用本 Store.read 适配，也不形成本卡对同步卡的依赖（下游说明，非契约）。fml-store只收trait对象，禁止依赖fml-ffi或全局EngineContext；本卡依赖字段写CORE-56而不直列CORE-06/07/09。
- 导入把成功分析结果交CORE-14写入；失败行不写，rejected保留原行号/Diagnostic；Validation保存映射、标签校验、changed_fields/Store.write/enqueue_outbox全部复用CORE-14/13。重放与缓存不冒充用户编辑。源码/AST diff由本卡自行实现，未经锁版不引入第三方diff crate。
- SQL触发器、FTS投影表与其他DDL继续留0014_library.sql，检索和导入代码归本卡，不重复预算DDL或CORE-14写仓储。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| LIB_IMPORT_ROW_INVALID | CORE-14 | 仅放入rejected的行级诊断，不中断整批 |
| LIB_IMPORT_TOO_LARGE | CORE-14 | 超5000行/8MiB整批拒绝 |
| LIB_NOT_FOUND、LIB_NOT_VERIFIED、LIB_META_INVALID、LIB_TAGS_LIMIT | CORE-14 | 透传仓储拒绝，失败行不入库 |
| ENGINE_UNAVAILABLE | CORE-56 | 不调用分析算法，向调用者返回可重试失败 |

**实现约束**
- 列表查询分页并使用按字节计量LRU，不同账户不共享明文缓存；参数化查询与稳定排序不可因拆卡改变。
- 外部前提：SQLCipher必须启用FTS5且SQLite≥3.34.0；开工运行sqlite_version()、compile_options及CREATE VIRTUAL TABLE tokenize=trigram探针，不凭bundled名假定能力。
- 产品约束仍见README §6 Q10/Q16；暂行默认不由编码会话改变。

**验收标准**：测试方案全文见 [Test/core/S3_CORE-79_TEST.md](../Test/core/S3_CORE-79_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约405行（CO-28 增 CandidateRow 与 output_type 补全约15行）；crates/fml-store/src/library/{query,diff,import,analysis}.rs及本卡编写的crates/fml-ffi/src/ops/{library_query,library_analysis}.rs；含分析注入trait/薄适配与四op接入，不计CORE-14实现、DDL/schema、生成物、自测及夹具。
