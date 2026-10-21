### CORE-13 本地库 Schema、单写者与迁移

**目标**：为每个本地账户提供一个加密 SQLite 库，统一表结构、单写者事务模型、迁移链与完整性检查。

**范围**
- 包含：`fml-store` crate 的打开/关闭、SQLCipher 加密、单写者 actor、只读连接池、迁移执行器与迁移前备份、基础设施表（`schema_migration`、`local_setting`、`sync_outbox`、`sync_cursor`、`tombstone`）的 DDL、`sync_outbox` 写入钩子（与业务同事务）、业务表归属清单。
- 不包含：业务表的 DDL 与仓储逻辑（由下表的归属卡在各自迁移文件中定义）；数据库密钥的生成与平台包装（CORE-21、CORE-23）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-05

**接口契约**

```rust
// crates/fml-store/src/lib.rs
pub struct DbKey(pub Zeroizing<[u8; 32]>);              // 随机生成，由 CORE-23 经平台密钥解包后传入
pub struct StoreConfig { pub db_path: PathBuf, pub backup_dir: PathBuf, pub read_pool: usize /* 默认 2 */ }
pub trait IdSource: Send { fn new_uuid(&mut self) -> Result<Uuid, FmlError>; } // 调用方注入，生产适配见 CORE-23；本卡无 OS 随机实现
pub struct Store { /* 单写者 actor + 只读池 + 注入的 IdSource */ }
impl Store {
    pub fn open(cfg: &StoreConfig, key: DbKey, ids: Box<dyn IdSource>) -> Result<Store, FmlError>;   // 校验 user_version 与密钥
    pub fn write<T>(&self, cmd: impl FnOnce(&mut WriteTx) -> Result<T, FmlError>) -> Result<T, FmlError>; // 一个用例命令 = 一个事务
    pub fn read<T>(&self, q: impl FnOnce(&ReadTx) -> Result<T, FmlError>) -> Result<T, FmlError>;          // WAL 快照读
    pub fn integrity_check(&self) -> Result<IntegrityReport, FmlError>;
    pub fn close(self) -> Result<(), FmlError>;
}
pub struct WriteTx<'a> { /* 包装 rusqlite::Transaction */ }
pub struct ReadTx<'a>  { /* 包装只读连接上的快照事务 */ }
impl WriteTx<'_> {
    pub fn conn(&self) -> &rusqlite::Connection;
    pub fn stamp(&mut self) -> Result<TxStamp, FmlError>;   // 本事务首次调用时分配，之后返回同一值
    pub fn enqueue_outbox<C: OutboxEntityCodec>(&mut self, op: OutboxOp) -> Result<(), FmlError>;   // 业务写与 outbox 同事务；op.entity_type 必须等于 C::ENTITY_TYPE
    pub fn tombstone(&mut self, entity_type: &str, entity_id: &str, at_ms: i64) -> Result<(), FmlError>;
    pub fn rotate_device_id(&mut self, min_lamport: u64) -> Result<Uuid, FmlError>; // 仅 CORE-26 在检测到整库回退时调用：新随机 device_id、device_seq=0、lamport=max(当前, min_lamport)；已有 field_clock 与 outbox 行不改
}
impl ReadTx<'_> { pub fn conn(&self) -> &rusqlite::Connection; }
pub struct TxStamp { pub lamport: u64, pub device_id: Uuid, pub device_seq: u64 }   // 取自 local_clock，事务回滚则作废
pub trait OutboxEntityCodec {                          // 由业务表归属卡为每个同步实体实现
    const ENTITY_TYPE: &'static str;
    fn read_entity(conn: &rusqlite::Connection, entity_id: &str) -> Result<Option<serde_json::Value>, FmlError>; // 本事务内回读最终实体；None 表示已删除
    fn list_entity_ids(conn: &rusqlite::Connection) -> Result<Vec<String>, FmlError>; // 只列本 codec 可同步的存活实体，按 ID UTF-8 字节升序去重
}
pub enum OutboxKind { Upsert, Delete }
pub struct OutboxOp { pub entity_type: String /* 表名，如 "formula_revision" */, pub entity_id: String,
                      pub kind: OutboxKind, pub changed_fields: Vec<String> /* 真正变化的顶层字段名；去重排序 */, pub created_at_ms: i64 }
pub struct IntegrityReport { pub ok: bool, pub sqlite_messages: Vec<String> /* PRAGMA integrity_check 输出，最多 100 行 */,
                             pub foreign_key_violations: u32, pub schema_version: u32 }
pub const SCHEMA_VERSION: u32;   // 仅取 migrations/ 直接子文件的最大序号；registry/ 属设备小库，不递归收录
```



**同步接缝（ADR-V5-47；S2 只依赖本卡 trait/Fake，S6 消费）**

```rust
// crates/fml-store/src/sync_contract.rs；不依赖 fml-ffi 或 fml-sync
pub struct FieldClock { pub counter: u64, pub device_id: Uuid }
pub struct RemoteEntity { pub entity_type: String, pub entity_id: String, pub kind: OutboxKind,
    pub entity: Option<serde_json::Value>, pub clocks: BTreeMap<String, FieldClock> }
pub struct RemoteRevisionAnalysisInput { pub source_latex: String, pub notation_profile_id: String,
    pub user_decls: Vec<SymbolDecl>, pub conditions: Vec<FormulaNode>, pub empirical: bool }
pub struct RemoteRevisionAnalysis { pub ast: Option<FormulaNode>, pub symbols: SymbolEnv,
    pub conditions: Vec<FormulaNode>, pub validation: Validation, pub diagnostics: Vec<Diagnostic> }
pub trait RemoteRevisionAnalyzer {
    fn analyze_revision(&self, conn: &rusqlite::Connection, input: &RemoteRevisionAnalysisInput,
                        cancel: &CancelFlag) -> Result<RemoteRevisionAnalysis, FmlError>;
}
pub struct ApplyContext<'a> { pub analyzer: &'a dyn RemoteRevisionAnalyzer, pub cancel: &'a CancelFlag }
pub enum ApplyOutcome {
    Applied,
    Duplicate,
    Invalid(FmlError),
}
pub trait EntityApplier {
    fn apply(&self, tx: &mut WriteTx, remote: &RemoteEntity, ctx: &ApplyContext) -> Result<ApplyOutcome, FmlError>;
}
pub struct EntityRegistry { /* 按 ENTITY_TYPE 保存 applier 与擦除后的 codec 回调 */ }
impl EntityRegistry {
    pub fn new() -> Self;
    pub fn register<C: OutboxEntityCodec + 'static>(&mut self, applier: Box<dyn EntityApplier>) -> Result<(), FmlError>;
    pub fn entity_types(&self) -> Vec<&str>; // UTF-8 字节升序
    pub fn list_entity_ids(&self, conn: &rusqlite::Connection, entity_type: &str) -> Result<Vec<String>, FmlError>;
    pub fn apply(&self, tx: &mut WriteTx, remote: &RemoteEntity, ctx: &ApplyContext) -> Result<ApplyOutcome, FmlError>;
}
impl WriteTx<'_> {
    pub fn requeue_outbox(&mut self, registry: &EntityRegistry, entity_type: &str, entity_id: &str, created_at_ms: i64) -> Result<(), FmlError>;
}
```

- `register` 的泛型只负责擦除静态 codec，`EntityApplier` / `RemoteRevisionAnalyzer` 均 object-safe；重复注册视为构建错误，返回 STORE_CORRUPT。未知实体由分派方先查 `entity_types` 并隔离，不把未登记类型当成成功。所有者只注册自己的类型；CORE-13 提供 `setting` 的 codec/applier，键为实体 ID，仅 `syncable=1` 且非 `device.*` 可枚举/读写；CORE-14/17/82/86 与 CORE-26 的 merge_choice 实现由各自卡交付，S2 不加载未交付模块。
- owner applier 仅在传入 WriteTx 内更新自己的表、field_clock、派生投影与缓存失效，不调用 enqueue_outbox/stamp、不另开 Store.read/write、不提交事务；非法远端业务内容返回 Invalid（由分派方保存点回滚该条并隔离），SQLite/I/O 故障返回 Err（整页回滚）。Duplicate 不改任何行。墓碑仍按被删实体类型分派，不设第二个可同步 tombstone 实体。
- `requeue_outbox` 从同一事务回读 codec 与完整现有 field_clock，保留全部字段值/时钟；已删实体从 tombstone 与 __deleted 时钟生成 Delete。既无存活实体又无墓碑时幂等不入队；存活实体缺时钟是 STORE_CORRUPT，不偷偷 stamp 字段。新队列 op 使用新事务序号，但绝不改业务字段或 field_clock；调用方重建全队列前先作废批次、清旧 outbox，再按类型/ID 稳定顺序枚举，追加未过期墓碑；全部在同一写事务。游客仍不入队，升级先在同一事务改注册资格再重排。
- analyzer 的 conn 为**合同只读**同事务视图，不嵌套 Store.read/write；本卡只拥有输入/输出与 trait，返回结果只供所有者重建派生缓存。具体 FFI 适配归 CORE-26/66 的 S6 附属接线，读取当前事务 user_unit/notation_profile 并调用 CORE-56 的 S1 纯 helper；CORE-56 不依赖 CORE-13、不读库，fml-store 不依赖 fml-ffi。输出保留解析失败的 ast=None，不造 Hole 或信任上传 AST；validation/diagnostics 从纯 helper 的 check_result 投影，S2 不依赖 fml-type 的 CheckResult。S2 用 FakeAnalyzer 验收，不以未来引擎/同步实现为前提。

- 迁移文件：`crates/fml-store/migrations/<4 位序号>_<域>.sql`，按序号升序执行，本次升级全部待执行文件在同一个事务中执行，每文件在 `schema_migration` 记一行（连同最终 user_version 一起提交）。待执行文件 = `migrations/` 中未记入 `schema_migration` 的文件（不以 user_version 比较判定）；`PRAGMA user_version` 等于已执行文件的最大序号（= `SCHEMA_VERSION`），不因补执行低序号文件而降低。V1 发布前依赖关系可使高序号文件先于低序号文件合入（如 CORE-78 的 0078 先于 CORE-26 的 0026），开发与测试库在下次打开时按上述规则补执行；发布后新增文件序号必须大于已发布的最大序号，不允许乱序。V1 发布前序号取归属卡编号（如 `0013_core.sql`、`0014_library.sql`），发布后新增迁移从 `0100` 起递增，已发布的迁移文件不得修改。
- 打开时先比对所有已执行记录：已记录 version 的文件缺失、或记录最大版本/user_version 高于本构建可识别版本 → STORE_SCHEMA_TOO_NEW；文件仍在但 checksum/name 不符 → STORE_MIGRATION_FAILED。二者均在迁移前拒绝写打开、保留原库；不得以待执行集合为空跳过校验。build.rs 只枚举 migrations/ 直接子文件，排除 registry/，嵌入按序号排序的文件名/字节/checksum 并拒绝重复序号，运行时不从任意工作目录找迁移。迁移失败只返回错误，保留旧库与备份；“旧库可打开”须由旧兼容构建重开验证，不向新构建伪装成功 Store。迁移时间由存储边界一次采样并记录，不在领域层读取时钟。
- 基础设施表（本卡 `0013_core.sql`）：

| 表 | 列（类型，约束） | 索引 |
| --- | --- | --- |
| `schema_migration` | `version INTEGER PRIMARY KEY`，`name TEXT NOT NULL`，`applied_at_ms INTEGER NOT NULL`，`checksum TEXT NOT NULL`（迁移文件原始 UTF-8 字节的 BLAKE3 小写 64 位十六进制，不规范化换行） | — |
| `local_setting` | `key TEXT PRIMARY KEY`（匹配 `^[a-z0-9_.]+$`），`value TEXT NOT NULL`（JSON），`syncable INTEGER NOT NULL DEFAULT 0 CHECK (syncable IN (0,1))`，`updated_at_ms INTEGER NOT NULL` | — |
| `sync_outbox` | `seq INTEGER PRIMARY KEY AUTOINCREMENT`，`entity_type TEXT NOT NULL`，`entity_id TEXT NOT NULL`，`kind TEXT NOT NULL CHECK (kind IN ('upsert','delete'))`，`payload BLOB NOT NULL`，`created_at_ms INTEGER NOT NULL`，`attempts INTEGER NOT NULL DEFAULT 0` | `(entity_type, entity_id)` |
| `sync_cursor` | `stream TEXT PRIMARY KEY`，`cursor TEXT NOT NULL`，`epoch INTEGER NOT NULL`，`updated_at_ms INTEGER NOT NULL` | — |
| `tombstone` | `entity_type TEXT NOT NULL`，`entity_id TEXT NOT NULL`，`deleted_at_ms INTEGER NOT NULL`，`PRIMARY KEY (entity_type, entity_id)` | `(deleted_at_ms)` |

- 业务表归属（列、约束与索引在归属卡中定义，迁移文件由归属卡提交）：`formula_item`、`formula_revision`、`symbol_binding`、`user_unit`、`notation_profile`、`constant_set`、`derivation`、`mastery_cache`、`formula_fts` → CORE-14；`formula_draft` → CORE-61；`calculation_plan` → CORE-86（`0086_calculation_plan.sql`）；设备级 `pack_meta.db` 的 `installed_pack` → CORE-95（不在档案库）；`study_card`、`review_event`、`srs_params` → CORE-17；`book`、`study_plan`、`study_session`、`attempt`、`confusable_group` → CORE-19 定义纯模型与 `0019_study.sql` DDL，CORE-82 实现仓储、codec/applier；`stats_cache` → CORE-20；`account_state` → CORE-23（设备级 `device_registry.db` 是独立小库，不在本库内）；`upgrade_journal`、`account_key_wrap`、`account_key` → CORE-24；`local_clock`、`field_clock` → CORE-13；`sync_quarantine`、`merge_choice` → CORE-26；`push_batch` → CORE-78（CO-08拆出）；`recognition_counter`、`recognition_session`、`recognition_asset`、`cleanup_job`、`pending_cloud_job` → CORE-85（五表 DDL 与仓储；CORE-32 保留纯模型与历史协议）。

**表所有权与备份策略（ADR-V5-50；本卡清单唯一，表列/外键运行时经 PRAGMA 读取）**

```rust
// crates/fml-store/src/schema_policy.rs；只读静态元数据，不引用后续备份模块
pub enum BackupScope { Formulas, Units, Study, Plans, Settings, Never }
pub enum TableMutability { Mutable, Immutable, Derived, LocalMutable, LocalInfrastructure, RebuildableCache,
    LocalDraft, LocalParameters, LocalSecret, LocalSyncMetadata, LocalHistorySecret, DeviceMetadata }
pub enum RowFilter { AllRows, UserFormulaItems, NonPackRevisions, UserRevisionBindings,
    UserRevisionDerivations, SyncableNonDeviceSettings, NoRows }
pub struct TablePolicy { pub table: &'static str, pub ddl_owner: &'static str, pub logical_owner: &'static str,
    pub scope: BackupScope, pub mutability: TableMutability, pub row_filter: RowFilter }
pub fn table_policies() -> &'static [TablePolicy];
```

每个已合入迁移的 profile 表恰一条 TablePolicy；table 是原始表名而非 SQL，owner 为卡号字符串。下表定义所有权与闭集策略；构建仅收录已合入表，未来表不凭空创建。静态 slice 无可写入口，不带任意 SQL 字符串；未登记表/不满足 row_filter 的行均隐式 Never，不能因 PRAGMA/FK 发现而导出。独立 pack_meta.db 的 installed_pack、device_registry.db 的 profile/profile_blob 永不属于该 slice/档案备份。

| 表 | ddl_owner | logical_owner | scope | mutability | row_filter |
| --- | --- | --- | --- | --- | --- |
| formula_item | CORE-14 | CORE-14 | Formulas | Mutable | UserFormulaItems |
| formula_revision | CORE-14 | CORE-14 | Formulas | Immutable | NonPackRevisions |
| symbol_binding | CORE-14 | CORE-14 | Formulas | Derived | UserRevisionBindings |
| derivation | CORE-14 | CORE-14 | Formulas | Derived | UserRevisionDerivations |
| notation_profile | CORE-14 | CORE-14 | Formulas | Mutable | AllRows |
| constant_set | CORE-14 | CORE-14 | Formulas | Mutable | AllRows |
| user_unit | CORE-14 | CORE-14 | Units | Mutable | AllRows |
| calculation_plan | CORE-86 | CORE-86 | Formulas | Mutable | AllRows |
| study_card | CORE-17 | CORE-17 | Study | Mutable | AllRows |
| review_event | CORE-17 | CORE-17 | Study | Immutable | AllRows |
| book | CORE-19 | CORE-82 | Study | Mutable | AllRows |
| confusable_group | CORE-19 | CORE-82 | Study | Mutable | AllRows |
| attempt | CORE-19 | CORE-82 | Study | Immutable | AllRows |
| study_session | CORE-19 | CORE-82 | Study | LocalMutable | AllRows |
| study_plan | CORE-19 | CORE-82 | Plans | Mutable | AllRows |
| local_setting | CORE-13 | CORE-13 | Settings | Mutable | SyncableNonDeviceSettings |
| schema_migration | CORE-13 | CORE-13 | Never | LocalInfrastructure | NoRows |
| local_clock | CORE-13 | CORE-13 | Never | LocalInfrastructure | NoRows |
| field_clock | CORE-13 | CORE-13 | Never | LocalInfrastructure | NoRows |
| sync_outbox | CORE-13 | CORE-13 | Never | LocalInfrastructure | NoRows |
| sync_cursor | CORE-13 | CORE-13 | Never | LocalInfrastructure | NoRows |
| tombstone | CORE-13 | CORE-13 | Never | LocalInfrastructure | NoRows |
| formula_fts | CORE-14 | CORE-14 | Never | RebuildableCache | NoRows |
| mastery_cache | CORE-14 | CORE-14 | Never | RebuildableCache | NoRows |
| formula_draft | CORE-61 | CORE-61 | Never | LocalDraft | NoRows |
| srs_params | CORE-17 | CORE-17 | Never | LocalParameters | NoRows |
| stats_cache | CORE-20 | CORE-20 | Never | RebuildableCache | NoRows |
| account_state | CORE-23 | CORE-23 | Never | LocalInfrastructure | NoRows |
| upgrade_journal | CORE-24 | CORE-24 | Never | LocalSecret | NoRows |
| account_key_wrap | CORE-24 | CORE-24 | Never | LocalSecret | NoRows |
| account_key | CORE-24 | CORE-24 | Never | LocalSecret | NoRows |
| sync_quarantine | CORE-26 | CORE-26 | Never | LocalSyncMetadata | NoRows |
| merge_choice | CORE-26 | CORE-26 | Never | LocalSyncMetadata | NoRows |
| push_batch | CORE-78 | CORE-78 | Never | LocalSyncMetadata | NoRows |
| recognition_counter | CORE-85 | CORE-85 | Never | LocalHistorySecret | NoRows |
| recognition_session | CORE-85 | CORE-85 | Never | LocalHistorySecret | NoRows |
| recognition_asset | CORE-85 | CORE-85 | Never | LocalHistorySecret | NoRows |
| cleanup_job | CORE-85 | CORE-85 | Never | LocalHistorySecret | NoRows |
| pending_cloud_job | CORE-85 | CORE-85 | Never | LocalHistorySecret | NoRows |

RowFilter 的 SQL 谓词/必要连接由本卡闭集映射实现，不允许调用方传入或拼接任意过滤 SQL：AllRows 接受全表；NoRows 一律拒绝；UserFormulaItems 为 read_only=0；NonPackRevisions 为 is_pack_cache=0；UserRevisionBindings 按 symbol_binding.revision_id 连接 NonPackRevisions；UserRevisionDerivations 按 derivation.result_revision 连接 NonPackRevisions（source_revision 不被改写为用户修订）；SyncableNonDeviceSettings 为 syncable=1 且 key 不以 device. 开头。后三项的表/列名称是所有者既有过滤契约，不是转录整套列/FK结构。

已合入策略要求存在的表/固定过滤所需列缺失、同表重复策略或策略矛盾均返回 STORE_CORRUPT，不能默默跳过；尚未合入表没有 slice 项，不要求存在、不建占位表。备份范围不等于同步实体列表；Derived 随权威行导出后校验/重建，study_card 的 state/due_ms 等仍是派生列，Never 不因外键闭包放行。新增表由所有者先回填本清单与实现条目，CORE-27/84 共消费本 API，只通过当前事务 PRAGMA 获取实际列/主键/FK，不复制其他所有者 DDL。学习恢复重放仍由 CORE-84 消费 CORE-17。

包稳定 ID 引用与 missing_packs 既有行为保留；RowFilter/PRAGMA 不新增禁止引用预置内容的产品规则，也不把预置缓存提升为用户数据。

- 通用列约定：主键为 UUID 文本（小写带连字符）或整数；时间列为 `*_at_ms INTEGER`；布尔为 `INTEGER CHECK (x IN (0,1))`；JSON 列为 `TEXT` 且以 `_json` 结尾；所有外键 `ON DELETE RESTRICT`，启用 `PRAGMA foreign_keys = ON`。
- 不进 outbox 的数据：识别历史、各类 cache、诊断、本机密钥、本地路径。
- 资源包权威内容只存 `(pack_id, content_hash, entry_key)` 引用；CORE-14 可保存可重建的只读查询投影与全文索引，不作为用户修订、不进 outbox。长期保留或编辑时复制成用户修订。
- FFI op：`store.open`、`store.close`、`store.integrity_check`（长任务走 `fml_submit`）。
- 错误码：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `STORE_KEY_INVALID` | error | 否 | 密钥无法解密库头 |
| `STORE_SCHEMA_TOO_NEW` | error | 否 | user_version/已记录最大序号高于本构建，或任一已执行迁移文件缺失 |
| `STORE_MIGRATION_FAILED` | error | 否 | 已执行迁移的 name/checksum 与嵌入文件不符，或迁移事务失败并回滚 |
| `STORE_CORRUPT` | error | 否 | `integrity_check` 非 ok、文件头损坏、时钟计数溢出，或已合入表策略的必需表/过滤列缺失、重复/矛盾策略 |
| `STORE_DISK_FULL` | error | 是 | `SQLITE_FULL` 或迁移前剩余空间小于库文件 2 倍 |
| `STORE_BUSY` | warning | 是 | 写命令排队超过 5 s |

- 外部前提：`rusqlite`（`bundled-sqlcipher` 特性）、`zeroize`、`uuid`（serde；不启用内部 OS RNG）、`serde`/`serde_json`、`blake3`，build-dependencies 的 `blake3` 同运行时版本；版本按 ADR-V5-15 由首张使用卡开工时锁入 `Cargo.lock`；SQLCipher 以 BSD 风格许可随包分发，需在关于页列出。

本地写入与字段时钟（S2 即交付，不等同步模块）：

- local_clock(singleton INTEGER PK CHECK=1, device_id TEXT NOT NULL, lamport INTEGER NOT NULL, device_seq INTEGER NOT NULL)；field_clock(entity_type TEXT, entity_id TEXT, field TEXT, counter INTEGER NOT NULL, device_id TEXT NOT NULL, PRIMARY KEY(entity_type,entity_id,field))，0013_core.sql 创建。counter/device_seq 限 0..i64::MAX，溢出 STORE_CORRUPT，不回绕。
- ID 来源：Store 持有调用方 IdSource；新库 device_id、每次新 outbox op_id 与 rotate_device_id 从它取得独立 UUID-v4，重发不重新取 ID。生产由 CORE-23 用 OsRandom 取 16 字节后设置 UUID-v4 version/variant，Fake 提供固定序列；现有库打开沿用原 device_id，不消耗新身份。随机失败原样传播并回滚，不使用全零/时钟伪随机；提供器违反非零/版本约束或给出已存在 ID → STORE_CORRUPT。store.open FFI 的参数仍不新增 JSON 字段，其适配构造同一提供器。
- 一个命令一个 Store.write：先业务更新，再 enqueue_outbox。`stamp()` 每个事务只分配一次：lamport=L+1、device_seq=S+1 并写回 local_clock；同一事务内的多条 outbox、`review_event`/`attempt` 等事件行的 device_seq 与字段时钟都用这一个 TxStamp（同事务多条事件需要区分时由归属卡加事件内序号列，不再另取 device_seq）；enqueue_outbox 内部调用 stamp()，给 changed_fields 每字段写 (L+1,device_id)。device_seq 的唯一来源是 local_clock，别的卡不得另存计数。delete 固定字段 __deleted；不可变修订/事件固定 __entity。OutboxOp 不接收 payload/时钟；payload 由 `C::read_entity` 在本事务回读最终实体，存为本地明文 JSON `{"entity": …, "clocks": {字段: [counter, device_id]}}`（库本身已加密），加密与信封由 CORE-26 在推送时完成；不能信任调用者传来的时钟。业务、时钟、tombstone、outbox 任一失败整体回滚。
- 游客写入也维护字段时钟，但不创建上传队列；注册升级按已有 field_clock 为全部实体生成 outbox，不能重分配实体 ID 或制造虚假字段更改。注册未开启同步仍记 outbox，开关只阻止网络发送。
- 远端合并事务先执行 lamport=max(local,所有验证通过的remote counter)，LWW 按 (counter,device_id网络字节) 词典序比较；两者完全相等而值不同（只会出现在整库回退之后，见 CORE-26）时比较该字段值规范 JSON 的 BLAKE3，大者胜，保证各端收敛；合并不生成本地 outbox，不把旧值写回。本地下一次真实编辑才 +1。
- sync_outbox 附加 op_id TEXT UNIQUE NOT NULL、device_id TEXT、device_seq INTEGER；重试保留同一 op_id 与 payload，不用本地 seq 当跨设备水位。该事务规则供所有业务仓储调用，不允许手工直接 INSERT sync_outbox。归属卡可在同一 WriteTx 内追加派生更新（如 CORE-20 的 `local_setting` `stats_generation` + 1），派生更新不进 outbox、不分配时钟。

| 向量 | 输入 | 期望 |
| --- | --- | --- |
| CLOCK-01 | 本地 L=8，收到远端 counter=12，再改 title | 合并后12，本地 title=(13,本设备)，outbox同事务产生1条 |
| CLOCK-02 | 写业务成功后注入 outbox 磁盘满 | 业务、field_clock、L/S及outbox全部回到原值 |


**Store op 字段表**（均 submit；隐式全局Store禁止）
| op | body（必填） | ok |
| --- | --- | --- |
| store.open | `{config: StoreConfig, db_key_b64: string}`（解码恰32字节） | `{handle: string, schema_version: u32}` |
| store.close | `{handle: string}` | `{}` |
| store.integrity_check | `{handle: string}` | `IntegrityReport` |
例：open body=`{"config":{"db_path":"/fixture/profile.db","backup_dir":"/fixture/backup","read_pool":2},"db_key_b64":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}`，ok=`{"handle":"281474976710657","schema_version":13}`（13 是仅含 0013 迁移的夹具值；完整构建返回当时最新的迁移序号，契约测试对该字段只断言 ≥ 13）；close body=`{"handle":"281474976710657"}`，ok=`{}`；integrity同body，ok=`{"ok":true,"sqlite_messages":["ok"],"foreign_key_violations":0,"schema_version":13}`。零密钥仅fixture，生产由调用方生成；错误见本卡表及 CORE-03 句柄错误。store.open为device scope，close/integrity为profile scope（body.handle保留，信封profile_handle同值）；其他仓储op统一继承CORE-03信封路由。Store::close先等待租约和actor队列排空；不能同时保留account.open_profile和store.open产生的两个同库写者。交互档案只由CORE-23的open_profile入口打开，store.open供无账户仓储fixture/工具使用；进程内以规范路径去重，重复打开返回STORE_BUSY。

FFI错误镜像（不重定义代码；通用信封错误见CORE-03）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| store.close | STORE_BUSY、STORE_CORRUPT |
| store.integrity_check | STORE_BUSY、STORE_CORRUPT |
| store.open | STORE_KEY_INVALID、STORE_SCHEMA_TOO_NEW、STORE_MIGRATION_FAILED、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY、CRYPTO_RNG_FAILED |

**实现约束**
- 单用户单库：每个本地账户一个库文件与一个私有资产目录（库文件为 `root(StoreArea.database)/<profile_id>.db`；档案私有资产位于其他 StoreArea 根目录下的 `<profile_id>/` 子目录）。
- SQLCipher（rusqlite 的 bundled-sqlcipher 特性）使用 32 字节原始密钥；数据库文件、WAL 与临时文件均加密；`temp_store = MEMORY`。密钥材料不得写入任何普通表。
- WAL 模式；写入只经单写者 actor；长任务分批提交并让出写锁。
- 迁移：先检查剩余空间，再做受平台密钥保护的本地备份，迁移在单个事务中完成；失败返回错误并保留原库与备份，不返回未完成迁移的正常 Store；禁止破坏性迁移与不受控的降级迁移。
- 完整性检查在迁移后、异常关闭后与用户主动诊断时执行，不做周期性 VACUUM。
- 测试接缝（crate 内部，非公共契约）：剩余空间探针与写队列超时（默认 5 s）经 `#[cfg(test)]` 可替换/可调，生产固定取平台剩余空间与 5 s；迁移文件经测试专用嵌入入口注入合成序号文件（`tests/fixtures/db/migrations-synthetic/`），生产只用 build.rs 嵌入集合。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-13_TEST.md](../Test/core/S2_CORE-13_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 705 行；主包 `crates/fml-store/`（crate 核心代码，约 665；`0013_core.sql` 等 DDL 为数据不计，业务仓储子模块由归属卡编写），附属 `crates/fml-ffi/src/ops/store.rs`（store.open/close/integrity_check 处理，约 40）。分阶段：① 存储内核（打开与 SQLCipher、单写者、只读池、迁移执行器与 checksum 规则、build.rs、完整性检查、错误映射、表所有权元数据骨架、store.* 三个 op，约 405）；② 写事务、字段时钟与同步接缝（WriteTx/stamp、enqueue_outbox、tombstone、rotate_device_id、OutboxEntityCodec 含 list_entity_ids、requeue_outbox、EntityApplier 与注册表、合并时钟辅助、setting codec/applier、完整 table_policies 静态元数据/固定 RowFilter 映射约45，约 300）。

