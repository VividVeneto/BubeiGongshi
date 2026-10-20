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
pub struct Store { /* 单写者 actor + 只读池 */ }
impl Store {
    pub fn open(cfg: &StoreConfig, key: DbKey) -> Result<Store, FmlError>;   // 校验 user_version 与密钥
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
}
pub enum OutboxKind { Upsert, Delete }
pub struct OutboxOp { pub entity_type: String /* 表名，如 "formula_revision" */, pub entity_id: String,
                      pub kind: OutboxKind, pub changed_fields: Vec<String> /* 真正变化的顶层字段名；去重排序 */, pub created_at_ms: i64 }
pub struct IntegrityReport { pub ok: bool, pub sqlite_messages: Vec<String> /* PRAGMA integrity_check 输出，最多 100 行 */,
                             pub foreign_key_violations: u32, pub schema_version: u32 }
pub const SCHEMA_VERSION: u32;   // 由 build.rs 取 migrations/ 中最大序号生成
```

- 迁移文件：`crates/fml-store/migrations/<4 位序号>_<域>.sql`，按序号升序执行，本次升级全部待执行文件在同一个事务中执行，每文件在 `schema_migration` 记一行（连同最终 user_version 一起提交）。待执行文件 = `migrations/` 中未记入 `schema_migration` 的文件（不以 user_version 比较判定）；`PRAGMA user_version` 等于已执行文件的最大序号（= `SCHEMA_VERSION`），不因补执行低序号文件而降低。V1 发布前依赖关系可使高序号文件先于低序号文件合入（如 CORE-78 的 0078 先于 CORE-26 的 0026），开发与测试库在下次打开时按上述规则补执行；发布后新增文件序号必须大于已发布的最大序号，不允许乱序。V1 发布前序号取归属卡编号（如 `0013_core.sql`、`0014_library.sql`），发布后新增迁移从 `0100` 起递增，已发布的迁移文件不得修改。
- 基础设施表（本卡 `0013_core.sql`）：

| 表 | 列（类型，约束） | 索引 |
| --- | --- | --- |
| `schema_migration` | `version INTEGER PRIMARY KEY`，`name TEXT NOT NULL`，`applied_at_ms INTEGER NOT NULL`，`checksum TEXT NOT NULL`（迁移文件 BLAKE3 十六进制） | — |
| `local_setting` | `key TEXT PRIMARY KEY`（匹配 `^[a-z0-9_.]+$`），`value TEXT NOT NULL`（JSON），`syncable INTEGER NOT NULL DEFAULT 0 CHECK (syncable IN (0,1))`，`updated_at_ms INTEGER NOT NULL` | — |
| `sync_outbox` | `seq INTEGER PRIMARY KEY AUTOINCREMENT`，`entity_type TEXT NOT NULL`，`entity_id TEXT NOT NULL`，`kind TEXT NOT NULL CHECK (kind IN ('upsert','delete'))`，`payload BLOB NOT NULL`，`created_at_ms INTEGER NOT NULL`，`attempts INTEGER NOT NULL DEFAULT 0` | `(entity_type, entity_id)` |
| `sync_cursor` | `stream TEXT PRIMARY KEY`，`cursor TEXT NOT NULL`，`epoch INTEGER NOT NULL`，`updated_at_ms INTEGER NOT NULL` | — |
| `tombstone` | `entity_type TEXT NOT NULL`，`entity_id TEXT NOT NULL`，`deleted_at_ms INTEGER NOT NULL`，`PRIMARY KEY (entity_type, entity_id)` | `(deleted_at_ms)` |

- 业务表归属（列、约束与索引在归属卡中定义，迁移文件由归属卡提交）：`formula_item`、`formula_revision`、`symbol_binding`、`user_unit`、`notation_profile`、`constant_set`、`derivation`、`mastery_cache` → CORE-14；`formula_draft` → CORE-61；`calculation_plan` → CORE-48；设备级 `pack_meta.db` 的 `installed_pack` → CORE-15（不在档案库）；`study_card`、`review_event` → CORE-17；`book`、`study_plan`、`study_session`、`attempt`、`confusable_group` → CORE-19；`stats_cache` → CORE-20；`account_state` → CORE-23（设备级 `device_registry.db` 是独立小库，不在本库内）；`upgrade_journal`、`account_key_wrap`、`account_key` → CORE-24；`local_clock`、`field_clock` → CORE-13；`sync_quarantine`、`merge_choice` → CORE-26；`push_batch` → CORE-78（CO-08拆出）；`recognition_counter`、`recognition_session`、`recognition_asset`、`cleanup_job`、`pending_cloud_job` → CORE-32。
- 通用列约定：主键为 UUID 文本（小写带连字符）或整数；时间列为 `*_at_ms INTEGER`；布尔为 `INTEGER CHECK (x IN (0,1))`；JSON 列为 `TEXT` 且以 `_json` 结尾；所有外键 `ON DELETE RESTRICT`，启用 `PRAGMA foreign_keys = ON`。
- 不进 outbox 的数据：识别历史、各类 cache、诊断、本机密钥、本地路径。
- 资源包权威内容只存 `(pack_id, content_hash, entry_key)` 引用；CORE-14 可保存可重建的只读查询投影与全文索引，不作为用户修订、不进 outbox。长期保留或编辑时复制成用户修订。
- FFI op：`store.open`、`store.close`、`store.integrity_check`（长任务走 `fml_submit`）。
- 错误码：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `STORE_KEY_INVALID` | error | 否 | 密钥无法解密库头 |
| `STORE_SCHEMA_TOO_NEW` | error | 否 | `user_version` 大于本程序 `SCHEMA_VERSION` |
| `STORE_MIGRATION_FAILED` | error | 否 | 迁移事务失败，已回滚 |
| `STORE_CORRUPT` | error | 否 | `integrity_check` 非 ok、文件头损坏或时钟计数溢出 |
| `STORE_DISK_FULL` | error | 是 | `SQLITE_FULL` 或迁移前剩余空间小于库文件 2 倍 |
| `STORE_BUSY` | warning | 是 | 写命令排队超过 5 s |

- 外部前提：`rusqlite`（`bundled-sqlcipher` 特性）与 `zeroize` crate，版本按 ADR-V5-15 由首张使用卡开工时锁入 `Cargo.lock`；SQLCipher 以 BSD 风格许可随包分发，需在关于页列出。

本地写入与字段时钟（S2 即交付，不等同步模块）：

- local_clock(singleton INTEGER PK CHECK=1, device_id TEXT NOT NULL, lamport INTEGER NOT NULL, device_seq INTEGER NOT NULL)；field_clock(entity_type TEXT, entity_id TEXT, field TEXT, counter INTEGER NOT NULL, device_id TEXT NOT NULL, PRIMARY KEY(entity_type,entity_id,field))，0013_core.sql 创建。counter/device_seq 限 0..i64::MAX，溢出 STORE_CORRUPT，不回绕。
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
例：open body=`{"config":{"db_path":"/fixture/profile.db","backup_dir":"/fixture/backup","read_pool":2},"db_key_b64":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}`，ok=`{"handle":"281474976710657","schema_version":13}`；close body=`{"handle":"281474976710657"}`，ok=`{}`；integrity同body，ok=`{"ok":true,"sqlite_messages":["ok"],"foreign_key_violations":0,"schema_version":13}`。零密钥仅fixture，生产由调用方生成；错误见本卡表及 CORE-03 句柄错误。store.open为device scope，close/integrity为profile scope（body.handle保留，信封profile_handle同值）；其他仓储op统一继承CORE-03信封路由。Store::close先等待租约和actor队列排空；不能同时保留account.open_profile和store.open产生的两个同库写者。交互档案只由CORE-23的open_profile入口打开，store.open供无账户仓储fixture/工具使用；进程内以规范路径去重，重复打开返回STORE_BUSY。

FFI错误镜像（不重定义代码；通用信封错误见CORE-03）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| store.close | STORE_BUSY、STORE_CORRUPT |
| store.integrity_check | STORE_BUSY、STORE_CORRUPT |
| store.open | STORE_KEY_INVALID、STORE_SCHEMA_TOO_NEW、STORE_MIGRATION_FAILED、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |

**实现约束**
- 单用户单库：每个本地账户一个库文件与一个私有资产目录（库文件为 `root(StoreArea.database)/<profile_id>.db`；档案私有资产位于其他 StoreArea 根目录下的 `<profile_id>/` 子目录）。
- SQLCipher（rusqlite 的 bundled-sqlcipher 特性）使用 32 字节原始密钥；数据库文件、WAL 与临时文件均加密；`temp_store = MEMORY`。密钥材料不得写入任何普通表。
- WAL 模式；写入只经单写者 actor；长任务分批提交并让出写锁。
- 迁移：先检查剩余空间，再做受平台密钥保护的本地备份，迁移在单个事务中完成；失败时保留并打开旧库，或以只读模式打开；禁止破坏性迁移与不受控的降级迁移。
- 完整性检查在迁移后、异常关闭后与用户主动诊断时执行，不做周期性 VACUUM。

**验收标准**
- [R27] 离线读取测试：用 sqlite3 或任意未带密钥的工具打开库文件、WAL 与临时文件均失败；对库目录做明文关键字扫描（样例公式与笔记文本）零命中。
- [R18] 迁移链测试：`tests/fixtures/db/` 中每个历史版本的样例库逐级迁移到最新版本，数据与校验和一致；注入迁移中途失败后旧库可打开。
- [R18] 乱序到达：样例库已执行 0013、0078，随后加入 0026 后打开，0026 被补执行并记入 `schema_migration`，`user_version` 保持 78；全部已记录文件不重复执行。
- [R19] 故障注入：写事务中途杀进程，重启后库可打开且无半条记录；磁盘满时返回 `STORE_DISK_FULL`，原数据不变。
- [R28] 单元测试：业务写与 `enqueue_outbox` 同事务，回滚时两者都不落库。
- [R28] 同一事务内写 2 个实体的 outbox 与 1 条事件行：三者共用同一 lamport 与 device_seq，local_clock 只前进 1；回滚后 local_clock 不变；payload 等于 `read_entity` 回读结果与字段时钟。

**规模**：约 450 行（不含 DDL）；`crates/fml-store/`（本卡只写 crate 核心代码与 0013_core.sql 迁移；业务仓储子模块由归属卡编写）。

