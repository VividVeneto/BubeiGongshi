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

- 表 `formula_draft`（迁移 `crates/fml-store/migrations/0061_formula_draft.sql`）：`draft_key TEXT PK`，`item_id TEXT`，`title TEXT NOT NULL`，`subject TEXT NOT NULL`，`source_latex TEXT NOT NULL`（≤ 64 KiB），`user_decls_json TEXT NOT NULL`，`notation_profile_id TEXT NOT NULL`，`updated_at_ms INTEGER NOT NULL`；只在本机，不进 outbox、不导出。
- 本卡登记的 op：`library.draft_put`、`library.draft_get`（`{draft_key}` → `{draft?: FormulaDraft}`，缺失省略draft）、`library.draft_delete`（同步）。


library.draft_put body=FormulaDraft，ok={}；get body={draft_key}、ok={draft?:FormulaDraft}（不存在省略draft）；delete body={draft_key}、ok={}（不存在幂等成功），均call；错误沿用CORE-14输入校验/CORE-13存储错误。例get new不存在：body={"draft_key":"new"}，ok={}；put后get返回同一draft字段。Dart FormulaDraftDto只引用CORE-67生成文件，不另定义。

**实现约束**
- 草稿仅本地，不进 outbox/备份；写入使用 CORE-13 单写者事务。
- FFI 处理函数归 fml-ffi，作为跨语言薄适配附属约30行；Rust 仓储不能依赖 Flutter。
- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**：测试方案全文见 [Test/core/S3_CORE-61_TEST.md](../Test/core/S3_CORE-61_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 160 行；主包 `crates/fml-store/src/library/draft.rs`、`crates/fml-store/migrations/0061_formula_draft.sql`（含测试与必要的同构建单元接缝）；附属 `crates/fml-ffi/src/ops/library_draft.rs`（FFI 薄适配，约 30 行）。

