### CORE-14 公式库仓储

**目标**：提供公式条目、修订、推导与计算计划的持久化与检索，支持修订历史、差异、恢复、回收站和 LaTeX/CSV 批量导入。

**范围**
- 包含：`LibraryRepo`、搜索与筛选、修订历史与差异、恢复为新修订、回收站（30 天）、量纲声明变更后的“待重校”标记、母修订删除后的派生转独立、批量导入与校验报告。
- 不包含：界面（CORE-38）；卡片重建（CORE-17 读取本卡标记）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-09、CORE-11、CORE-13、CORE-56

**接口契约**

```rust
// crates/fml-store/src/library/mod.rs
// FormulaItemId、RevisionId、FormulaItem、FormulaRevision、Provenance、Derivation 定义见 CORE-05
pub enum SourceFilter { Preset /* Provenance::Pack */, User /* UserInput、Handwriting、Photo */, Imported /* Import */, Derived /* derived_from 非空 */ }
pub enum ValidationFilter { Verified, Warning, Error, Unchecked, NeedsRecheck }   // 由 Validation 与待重校标记映射
pub enum MasteryState { NotLearned, Learning, Mastered, NeedsReinforce }   // 判据见 CORE-20；本卡定义 mastery_cache 表，CORE-20 写入
pub struct ItemMeta { pub title: String /* 1–200 字符 */, pub subject: String, pub course: Option<String>,
                     pub tags: Vec<String> /* 去首尾空白、按字面去重后每个 1–32 字符，≤ 20 个 */ }
pub struct NewRevision {
    pub source_latex: String,                // ≤ 64 KiB
    pub ast: FormulaNode, pub symbols: SymbolEnv, pub notation_profile_id: String,
    pub conditions: Vec<FormulaNode>,
    pub validation: Validation,              // CORE-09 结果；Invalid/Draft 时只能 draft = true
    pub confirm: Option<ConfirmRecord>,      // Unresolved 正式保存时必填
    pub derived_from: Option<Derivation>, pub provenance: Provenance,
    pub draft: bool,
}
pub struct RevisionSummary { pub id: RevisionId, pub created_at_ms: i64, pub provenance: Provenance,
                             pub draft: bool, pub validation: ValidationFilter }
pub struct ItemView { pub item: FormulaItem, pub head: FormulaRevision, pub needs_recheck: bool, pub revision_count: u32 }
pub struct ItemSummary { pub id: FormulaItemId, pub title: String, pub subject: String, pub source_latex: String,
                         pub validation: ValidationFilter, pub mastery: Option<MasteryState>, pub updated_at_ms: i64 }
// Page<T> 唯一定义见 CORE-05，import fml_ast::Page;
pub struct RevisionDiff { pub source: Vec<TextHunk> /* 行级 unified diff */, pub ast: Vec<AstChange> }
pub struct TextHunk { pub old_start: u32, pub old_len: u32, pub new_start: u32, pub new_len: u32, pub lines: Vec<String> /* 前缀 ' ' '-' '+' */ }
pub enum AstChange { Added { path: NodePath }, Removed { path: NodePath }, Changed { path: NodePath, before: String, after: String } }
pub enum ImportSource { Latex(String) /* 每行一个公式，空行与 % 开头行忽略 */, Csv(String) }
pub struct SearchQuery { pub text: Option<String>, pub subject: Option<String>, pub course: Option<String>,
                         pub tags: Vec<String>, pub source: Option<SourceFilter>, pub dimension: Option<DimensionFull>,
                         pub role: Option<SymbolRole>, pub mastery: Option<MasteryState>, pub validation: Option<ValidationFilter>,
                         pub trashed: bool /* 默认 false；true 时只返回回收站条目 */,
                         pub page: u32, pub page_size: u32 /* ≤ 100 */ }
pub trait LibraryRepo {
    fn create_item(&self, meta: &ItemMeta, rev: NewRevision) -> Result<(FormulaItemId, RevisionId), FmlError>;
    fn update_meta(&self, item: FormulaItemId, meta: &ItemMeta) -> Result<(), FmlError>;   // 只改条目元数据，不生成修订；预置条目同样允许
    fn add_revision(&self, item: FormulaItemId, rev: NewRevision) -> Result<RevisionId, FmlError>; // 预置条目生成用户修订
    fn get(&self, item: FormulaItemId) -> Result<ItemView, FmlError>;
    fn search(&self, q: &SearchQuery) -> Result<Page<ItemSummary>, FmlError>;
    fn history(&self, item: FormulaItemId) -> Result<Vec<RevisionSummary>, FmlError>;
    fn diff(&self, a: RevisionId, b: RevisionId) -> Result<RevisionDiff, FmlError>;   // 源码差异 + AST 节点差异
    fn restore(&self, item: FormulaItemId, from: RevisionId) -> Result<RevisionId, FmlError>; // 生成新修订，不改历史
    fn trash(&self, item: FormulaItemId) -> Result<(), FmlError>;
    fn untrash(&self, item: FormulaItemId) -> Result<(), FmlError>;
    fn purge_expired(&self, now_ms: i64) -> Result<u32, FmlError>;    // 30 天后物理删除并写 tombstone
    fn mark_recheck_dependents(&self, rev: RevisionId) -> Result<Vec<RevisionId>, FmlError>;
    fn candidates_for(&self, slot: &SlotRef, limit: u32) -> Result<Vec<Candidate>, FmlError>; // 交给 CORE-11 排序
    fn import_batch(&self, rows: ImportSource /* Latex(String) | Csv(String) */) -> Result<ImportReport, FmlError>;
}
pub struct ImportReport { pub accepted: u32, pub rejected: Vec<(u32 /* 行号，从 1 起，含表头 */, Vec<Diagnostic>)> }
```

- 搜索语义：`text` 走 FTS5（标题、标签、LaTeX 源码、符号名，`trigram case_sensitive 0` 分词，连续子串匹配；SQLCipher 的 SQLite 必须≥3.34.0 且启用 FTS5）；多个筛选条件为“与”；`tags` 为“全部包含”；输入先 NFC，英文按SQLite同一折叠规则；查询≥3个Unicode标量时用参数化 MATCH（双引号内原样短语，双引号转义），1～2个标量时对相同投影列作参数化 LIKE，显式 ESCAPE 转义 %/_/反斜杠，空串等同无text；两路径排序统一为 updated_at_ms 降序、id 升序，FTS相关度只作后续优化，无 `text` 时按 `updated_at_ms` 降序；`page` 从 0 起，`page_size` 默认 50、上限 100，越界返回空页；`trashed = false`（默认）时回收站条目不出现，`trashed = true` 时只返回回收站条目、无 `text` 时按 `trashed_at_ms` 降序。
- 脱离：对派生条目调用 `add_revision` 且 `derived_from = None` 即为脱离，新修订 `detached = true`，此后可正常编辑；脱离前的其他修改返回 CORE-11 的 `DERIVE_READ_ONLY`。
- 表（本卡 `migrations/0014_library.sql`；通用列约定见 CORE-13）：

| 表 | 主要列（类型，约束） | 索引 |
| --- | --- | --- |
| `formula_item` | `id TEXT PK`，`title TEXT NOT NULL`（1–200 字符），`subject TEXT NOT NULL`，`course TEXT`，`tags_json TEXT NOT NULL`（每个 ≤ 32 字符，≤ 20 个），`read_only INTEGER NOT NULL`，`head TEXT NOT NULL`（当前修订），`source_pack_id TEXT`，`source_content_hash TEXT`，`source_entry_key TEXT`，`requirement_level TEXT`（CORE-16 取值原样），`pack_extras_json TEXT`（包条目的 templates 与 distractors 原文 JSON），`projection_generation INTEGER NOT NULL DEFAULT 0`（三项 source 与这两列同时为空或非空；用户条目全为空），`created_at_ms`，`updated_at_ms`，`trashed_at_ms INTEGER` | `(subject, updated_at_ms)`，`(trashed_at_ms)` |
| `formula_revision` | `id TEXT PK`，`item_id TEXT NOT NULL REFERENCES formula_item(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED`，`parents_json TEXT NOT NULL`，`ast_schema INTEGER NOT NULL`，`source_latex TEXT NOT NULL`，`ast_json TEXT NOT NULL`（CORE-05 规范 JSON），`ast_hash TEXT NOT NULL`，`symbols_json TEXT NOT NULL`，`notation_profile_id TEXT NOT NULL`，`conditions_json TEXT NOT NULL`，`validation_json TEXT NOT NULL`，`validation TEXT NOT NULL`（ValidationFilter 蛇形小写，冗余列供筛选），`confirm_json TEXT`，`derived_from_json TEXT`，`detached INTEGER NOT NULL`，`provenance_json TEXT NOT NULL`，`draft INTEGER NOT NULL`，`is_pack_cache INTEGER NOT NULL DEFAULT 0 CHECK (is_pack_cache IN (0,1))`，`needs_recheck INTEGER NOT NULL DEFAULT 0`，`created_at_ms` | `(item_id, created_at_ms)`，`(validation)` |
| `symbol_binding` | `revision_id TEXT NOT NULL`，`symbol_id INTEGER NOT NULL`，`glyph TEXT NOT NULL`，`role TEXT NOT NULL`，`dimension TEXT`，`decl_json TEXT NOT NULL`，PK `(revision_id, symbol_id)` | `(dimension)`，`(role)` |
| `user_unit` | `id TEXT PK`（`user:<name>`），`definition_json TEXT NOT NULL`（CORE-08 UnitDefinition），`updated_at_ms` | — |
| `notation_profile` | `id TEXT PK`，`name TEXT NOT NULL`，`profile_json TEXT NOT NULL`，`updated_at_ms` | — |
| `constant_set` | `id TEXT PK`，`name TEXT NOT NULL`，`constants_json TEXT NOT NULL`，`updated_at_ms` | — |
| `derivation` | `id TEXT PK`，`source_revision TEXT NOT NULL`，`result_revision TEXT NOT NULL`（派生关系索引，一个派生修订的每个母修订一行；内容在 `formula_revision.derived_from_json`），`created_at_ms` | `(source_revision)`，`(result_revision)` |
| `mastery_cache` | `item_id TEXT PK`，`state TEXT NOT NULL`（MasteryState 蛇形小写），`updated_at_ms INTEGER NOT NULL`；本地缓存，不进 outbox | `(state)` |
| `formula_fts` | FTS5 虚表：`title`，`tags`，`latex`，`symbols`；`content_rowid` 关联 `formula_item`；由本卡迁移中 `formula_item` 的 AFTER INSERT/UPDATE/DELETE 触发器维护（`head` 变化时取新修订的 LaTeX 与符号），因此同步写入（CORE-26）与备份恢复（CORE-27）无需另行重建 | — |

- FFI op（DTO 按 CORE-03 映射规则，字段与上面结构体同名）：`library.create`（请求 `{meta, revision}`）、`library.revise`（对应 `add_revision`）、`library.update_meta`（请求 `{item_id, meta}`）、`library.get`、`library.search`、`library.history`、`library.diff`、`library.restore`、`library.trash`、`library.untrash`、`library.substitution_pool`（请求 `{slot, limit}`，`limit` 默认 50、上限 200，返回 `candidates_for` 结果供 CORE-11 排序）、`library.import`（长任务）。
- CSV 列：`title,subject,latex,tags,symbol_decls_json`，UTF-8（可带 BOM），首行为表头，RFC 4180 引号规则；`tags` 以分号分隔；`symbol_decls_json` 可空，非空时为 `[SymbolDecl]` JSON；单次导入 ≤ 5000 行、≤ 8 MiB，超出整批拒绝（`LIB_IMPORT_TOO_LARGE`）。
- 错误码：见本节末“错误码唯一定义”表，7 个 `LIB_*` 码均由本卡登记；CORE-38、CORE-54 只引用。

Validation → 保存与筛选的穷举映射（见 README §6 Q32（待确认），暂行默认）：

| Validation | draft=false | confirm | ValidationFilter |
| --- | --- | --- | --- |
| Draft | 拒绝 | 无效 | Unchecked |
| Invalid | 拒绝，只存草稿 | 不能解除拒绝 | Error |
| Unresolved | 允许，但仍不可计算/代入/出卡 | 正式保存必填 | Warning |
| Verified | 允许 | 不要求 | Verified |
| VerifiedPolymorphic | 允许 | 不要求 | Verified |

draft=true 的可编辑草稿均可保存，筛选仍按 Validation 映射；needs_recheck=true 优先映射 NeedsRecheck，清除后恢复原映射；任何含 Hole 的修订只能 draft=true，confirm 不可越过。

- 每个业务写命令必须使用 CORE-13 Store.write/enqueue_outbox，显式 changed_fields；不得自行分配 Lamport 或直接写 outbox。重放与缓存更新不当成用户编辑。

```rust
pub trait UnitRepo {   // base 为调用方传入的引擎快照单位表（不含将被替换的 User 层）
 fn list_user(&self) -> Result<Vec<UnitDefinition>,FmlError>;
 fn define_user(&self, base: &dyn UnitRegistry, def: UnitDefinition) -> Result<Vec<UnitDefinition> /* 提交后的全部用户单位 */,FmlError>;
 fn delete_user(&self, base: &dyn UnitRegistry, id: &str) -> Result<Vec<UnitDefinition>,FmlError>;
}
pub struct PackFormulaEntry { pub pack_id: String, pub content_hash: String /* 条目级，见 CORE-05 */, pub entry_key: String,
  pub meta: ItemMeta, pub requirement_level: String, pub extras_json: String /* templates 与 distractors */, pub revision: FormulaRevision }
pub trait PackCatalog {
 fn generation(&self) -> u64;
 fn formula_entries(&self) -> Result<Vec<PackFormulaEntry>,FmlError>;
}
```
- units.define_user/list_user/delete_user 的有 I/O 处理归本卡 fml-store/src/library/units.rs；CORE-08 只有定义校验纯函数。UnitRepo 只接收调用方传入的 `base` 快照，不依赖 fml-ffi；本卡附属的 `crates/fml-ffi/src/ops/units_user.rs` 适配负责 EngineContext 访问。修改先用 `base` 校验，再在单事务持久化 user_unit、标记待重校并 enqueue_outbox；提交后适配以返回的全部用户单位调用 CORE-56 `set_layer(User)`，失败时调用 `mark_unavailable`（此后引擎 op 返回 `ENGINE_UNAVAILABLE`，重试成功前拒绝求值），不回滚已提交数据。打开/切换档案先加载全部 user_unit，注销清除；启动加载失败不静默忽略非法定义。
- 只读投影：公式的 pack_id/content_hash/entry_key 写 formula_item 的 source_pack_id/source_content_hash/source_entry_key 三列（可空），缓存来源 revision ID = CORE-05 `pack_cache_revision_id(条目 ID, content_hash)`，content_hash 为条目级哈希；item 带 read_only=1/projection_generation=catalog generation，revision 带 is_pack_cache=1，保存 AST/符号/LaTeX 仅作可重建缓存。安装后按 catalog generation 懒刷新；借助延迟外键，先插 revision 再 upsert item/head（含 requirement_level 与 pack_extras_json），FTS 由 formula_item 触发器同事务维护；新增 item 的延迟外键在事务提交时满足；整个投影事务不发 outbox。更新不删除用户派生修订，旧引用依然钉住其内容哈希，包卸载前有引用则拒绝；用户确认长期保留时复制成普通用户修订。S3 用本卡 PackCatalog Fake 验收，S4 安装器只实现适配。


- FTS 能力依据 SQLite 官方 https://sqlite.org/fts5.html#the_trigram_tokenizer：少于3个标量的 MATCH 不命中，故必须有上述 LIKE 路径；两路径都参数化，不能把用户文本直接拼成 SQL。

错误码唯一定义（业务保存规则以上方 Validation 映射为准；界面只解释结果）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `LIB_NOT_FOUND` | error | 否 | ID 不存在或已物理删除 |
| `LIB_READ_ONLY` | error | 否 | 直接修改预置条目或其预置修订（应改走 `add_revision` 生成用户修订） |
| `LIB_NOT_VERIFIED` | error | 否 | Invalid/Draft 正式保存，或 Unresolved 正式保存缺 confirm |
| `LIB_IMPORT_ROW_INVALID` | error | 否 | 导入行校验失败；只出现在 `ImportReport.rejected` 的行级诊断中，不中断整批 |
| `LIB_IMPORT_TOO_LARGE` | error | 否 | 单次导入超过 5000 行或 8 MiB，整批拒绝 |
| `LIB_TRASHED` | error | 否 | 对回收站条目执行修订、恢复以外的写操作 |
| `LIB_META_INVALID` | error | 否 | `ItemMeta` 不满足长度或数量约束：标题为空或超 200 字符、学科为空、规范化后有空标签；标签长度/数量超限专用LIB_TAGS_LIMIT |


标签约束唯一定义：去首尾空白、非空、每标签≤32个Unicode标量，区分大小写按字面去重、每条目≤20；单条create/update与批量复用同一校验。LIB_TAGS_LIMIT（warning/不可重试）：超数量或长度；单条拒绝整个写事务，批量该条跳过，其余继续；本卡单条错误由批量消费方决定跳过并汇总，不反向引用后卡类型。

产品约束追踪：见README §6 Q10、Q16；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

EngineContext.snapshot返回Result；FFI适配先用snapshot()?取得Arc再检查unavailable/expected_generation，任一失败不调用领域算法。层提交后mark_unavailable的Err向调用方传播，不忽略。

**实现约束**
- 每次写入都是 CORE-13 的单个写事务，并同时 `enqueue_outbox`（修订、条目元数据、tombstone）。
- 保存前调用 CORE-09 校验：严格按本卡 Validation 映射表保存；诊断 Severity 与 Validation 是不同类型。
- 预置条目只读；编辑生成用户修订并保留卡片来源。单位定义变更后受影响修订标记待重校。
- 列表使用虚拟列表分页与按字节计量的 LRU 缓存；不同账户之间不共享明文缓存。
- 搜索使用 SQLite FTS5 与必要索引。
- 外部前提：SQLCipher 构建须启用 FTS5（开工实际运行 sqlite_version()、compile_options 和 CREATE VIRTUAL TABLE ... tokenize=trigram 探针，不依据 bundled 名称假定能力）。

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `LIB_TAGS_LIMIT` | warning | 否 | 标签超过20个或单标签超过32个Unicode标量 |

**验收标准**：测试方案全文见 [Test/core/S3_CORE-14_TEST.md](../Test/core/S3_CORE-14_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 500 行；主包 `crates/fml-store/src/library/` 与 `crates/fml-store/migrations/0014_library.sql`（约480行）；附属 `crates/fml-ffi/src/ops/units_user.rs`（约20行，持上下文并调用UnitRepo，不把fml-ffi反向引入fml-store）。

