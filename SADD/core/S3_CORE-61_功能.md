### CORE-61 公式草稿仓储

**目标**：公式草稿仓储，与原卡分开实施与验收。

**范围**
- 包含：草稿数据、表与三个 op；接收原 CORE-38 Rust 附属部分。
- 不包含：依赖卡已定义的业务算法、存储与平台能力；不修改其契约。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-13、CORE-14

**接口契约**

```rust
// crates/fml-store/src/library/draft.rs（附属：Rust 侧草稿仓储与 op）
pub struct FormulaDraft { pub draft_key: String /* "item:<uuid>" 或 "new" */, pub item_id: Option<FormulaItemId>,
                          pub title: String, pub subject: String, pub source_latex: String,
                          pub user_decls: Vec<SymbolDecl>, pub notation_profile_id: String, pub updated_at_ms: i64 }
pub fn put_draft(tx: &mut WriteTx, d: &FormulaDraft) -> Result<(), FmlError>;     // 同 key 覆盖
pub fn get_draft(rx: &ReadTx, key: &str) -> Result<Option<FormulaDraft>, FmlError>;
pub fn delete_draft(tx: &mut WriteTx, key: &str) -> Result<(), FmlError>;
```

- 表 `formula_draft`（迁移 `crates/fml-store/migrations/0061_formula_draft.sql`）：`draft_key TEXT PK`，`item_id TEXT`，`title TEXT NOT NULL`，`subject TEXT NOT NULL`，`source_latex TEXT NOT NULL`（≤ 64 KiB），`user_decls_json TEXT NOT NULL`，`notation_profile_id TEXT NOT NULL`，`updated_at_ms INTEGER NOT NULL`；只在本机，不进 outbox、不导出、不进备份（按 CORE-13 表策略 formula_draft 行 Never/LocalDraft/NoRows）。
- 本卡登记的 op：`library.draft_put`、`library.draft_get`（`{draft_key}` → `{draft?: FormulaDraft}`，缺失省略draft）、`library.draft_delete`；get 为 call，put/delete 为 submit（见下）。


library.draft_put body=FormulaDraft，ok={}；get body={draft_key}、ok={draft?:FormulaDraft}（不存在省略draft）；delete body={draft_key}、ok={}（不存在幂等成功）。调用方式：draft_get经只读连接池为call；draft_put与draft_delete进入CORE-13单写者队列，排队可能超过CORE-03 fml_call的P95≤30 ms上限，故为submit，不提供call别名。例get new不存在：body={"draft_key":"new"}，ok={}；put后get返回同一draft字段。Dart FormulaDraftDto只引用CORE-67生成文件，不另定义。

校验（put/get/delete共用，失败不写入）：draft_key只取`new`或`item:`后接小写带连字符UUID（CORE-05 FormulaItemId文本形式）；`new`要求item_id为None，`item:<u>`要求item_id等于u；source_latex按UTF-8字节计≤65536（恰65536通过）；notation_profile_id非空；title/subject可为空且不套用CORE-14的LIB_META_INVALID（草稿允许未完成表单）。仓储不读formula_item、不校验条目是否存在：条目移入回收站或删除后其`item:<uuid>`草稿保留，直到调用方draft_delete或档案库删除，不自动清理。存储层错误沿用CORE-13。

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `LIB_DRAFT_INVALID` | error | 否 | draft_key格式非法、item_id与draft_key不一致、source_latex超过65536字节或notation_profile_id为空；details给出字段路径 |

op schema与登记：contracts/dto/manifest.json中三个library.draft_* 目前为pending（schema/mode为null）；由本卡编码会话提交schema、示例与mode（get=call，put/delete=submit），error_codes填LIB_DRAFT_INVALID后再改ready，消费者在此之前不得注册。

**实现约束**
- 草稿仅本地，不进 outbox/备份；写入使用 CORE-13 单写者事务；同 key 并发 put 按单写者提交顺序最后一次生效。
- FFI 处理函数归 fml-ffi，作为跨语言薄适配附属约30行；Rust 仓储不能依赖 Flutter。
- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**：测试方案全文见 [Test/core/S3_CORE-61_TEST.md](../Test/core/S3_CORE-61_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 140 行；主包 `crates/fml-store/src/library/draft.rs`（含校验，约 105 行），迁移 `crates/fml-store/migrations/0061_formula_draft.sql`（DDL 不计）；附属 `crates/fml-ffi/src/ops/library_draft.rs`（FFI 薄适配，约 35 行）。

