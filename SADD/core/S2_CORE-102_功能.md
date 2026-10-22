### CORE-102 同步读取入口与写门

**目标**：为 CORE-13 的本地库补齐消费方已依赖、但原卡只有 DDL 的读取入口与写门——按实体读回规范化负载与字段时钟、查询未过期墓碑、读写同步游标、按业务门暂停/恢复写入，使 CORE-24、CORE-26、CORE-66 在禁止自拼 SQL 的前提下闭合。

**范围**
- 包含：`crates/fml-store/src/sync_read.rs` 的 `EntityRegistry::read_entity`、`read_field_clocks`、`list_tombstones`、`read_sync_cursor`、`WriteTx::set_sync_cursor`/`clear_sync_cursor`、`CursorOrder` 与四个行类型；`crates/fml-store/src/write_gate.rs` 的 `WriteGateState`、`WriteGate`、`Store::write_gated`/`write_gate`/`pause_writes`。
- 不包含：基础设施表 DDL 与迁移（CORE-13）；字段时钟分配、`stamp`、outbox 写入与墓碑生成（CORE-13）；远端合并与 enqueue 时机（CORE-26、CORE-66）；游标文本格式与有序性判定（格式属 CORE-25，本卡只经 `CursorOrder` 注入）；写门的触发时机与错误码定义（CORE-24）；FFI op 与 DTO（本卡不新增 op，消费卡在各自 S6 接线）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-13

**接口契约**

```rust
// crates/fml-store/src/sync_read.rs
pub struct StoredEntity { pub entity: serde_json::Value, pub clocks: BTreeMap<String, FieldClock> }
pub struct TombstoneRow { pub entity_type: String, pub entity_id: String, pub deleted_at_ms: i64, pub clocks: BTreeMap<String, FieldClock> }
pub struct SyncCursorValue { pub cursor: String, pub epoch: u32, pub seq: u64 }
pub struct SyncCursorRow { pub cursor: String, pub epoch: u32, pub updated_at_ms: i64 }
pub struct SyncCursorWrite { pub written: bool, pub row: SyncCursorRow }
pub const TOMBSTONE_TTL_MS: i64 = 15_552_000_000;   // 180 天，与 CORE-26 的清理口径同一常量

pub trait CursorOrder: Send + Sync {
    fn compare(&self, local: &str, next: &SyncCursorValue) -> Result<std::cmp::Ordering, FmlError>;
}

impl EntityRegistry {
    pub fn read_entity(&self, conn: &rusqlite::Connection, entity_type: &str, entity_id: &str) -> Result<Option<StoredEntity>, FmlError>;
}

pub fn read_field_clocks(conn: &rusqlite::Connection, entity_type: &str, entity_id: &str) -> Result<BTreeMap<String, FieldClock>, FmlError>;
pub fn list_tombstones(conn: &rusqlite::Connection, now_ms: i64) -> Result<Vec<TombstoneRow>, FmlError>;
pub fn read_sync_cursor(conn: &rusqlite::Connection, stream: &str) -> Result<Option<SyncCursorRow>, FmlError>;

impl WriteTx<'_> {
    pub fn set_sync_cursor(&mut self, stream: &str, next: &SyncCursorValue, order: &dyn CursorOrder, now_ms: i64) -> Result<SyncCursorWrite, FmlError>;
    pub fn clear_sync_cursor(&mut self, stream: &str) -> Result<bool, FmlError>;
}

// crates/fml-store/src/write_gate.rs
pub enum WriteGateState { Open, Paused }
pub struct WriteGate { /* 计数句柄；resume 或 Drop 释放一次，不可克隆 */ }

impl Store {
    pub fn write_gate(&self) -> WriteGateState;
    pub fn pause_writes(&self, reject: FmlError) -> Result<WriteGate, FmlError>;
}

impl WriteGate {
    pub fn resume(self) -> Result<(), FmlError>;
}
```

- `Store::write_gated`：签名与 CORE-13 的 `Store::write` 逐字相同（同一泛型 `T`、同一命令闭包参数 `impl FnOnce(&mut WriteTx) -> Result<T, FmlError>`，一个命令一个事务），差异只有一处——在进入写队列之前先判定写门：`Paused` 时直接返回 `pause_writes` 注入的拒绝错误（CORE-24 用 `SYNC_UPGRADE_IN_PROGRESS`），不入队、不占写者、不产生 `STORE_BUSY`。签名不在本卡代码块内重复书写，避免与 CORE-13 两处漂移；如需核对以 CORE-13 :21 为准。
- `conn` 一律是**合同只读**同事务视图（与 CORE-13 :94 analyzer 的口径相同）：调用方已在自己的 `Store.read` 或 `Store.write` 事务内，用 `tx.conn()` 取得；本卡内部不嵌套 `Store.read`/`Store.write`、不另开连接、不提交事务。`WriteTx::set_sync_cursor`/`clear_sync_cursor` 只接受写事务，保证单写者。
- `read_entity`：用该类型已登记的 `OutboxEntityCodec` 回读规范化 body（`C::read_entity`），并以同一事务读该 `(entity_type, entity_id)` 的全部 `field_clock` 行；与 outbox 明文 `{"entity":…,"clocks":…}` 同口径。未登记类型或存活实体没有任何 `field_clock` 行 → `STORE_CORRUPT`（不得临时新建注册项或补写时钟）。不返回 outbox、隔离区与批次状态。
- `read_field_clocks`：返回该实体全部字段时钟（含 `__deleted`、`__entity`）；无行返回空映射，不报错。本函数只读，只由 `ReadTx::conn()`/`WriteTx::conn()` 的同一事务视图调用。
- `list_tombstones`：只返回 `deleted_at_ms >= now_ms - TOMBSTONE_TTL_MS` 的墓碑，按 `(entity_type, entity_id)` 的 UTF-8 升序稳定排序，每行附该实体的全部字段时钟（含 `__deleted`）；`now_ms` 非正 → `FFI_BAD_ARG`。不清理、不写库，清理仍走 CORE-13 的 `purge_tombstones`。
- `read_sync_cursor`：无行返回 `None`；有行时 `cursor`/`epoch`/`updated_at_ms` 一一映射。只读快照：已开始的读事务看不到其后提交的游标行。
- `set_sync_cursor`：只前进不回退。无行 → 插入；有行且 `epoch` 不同 → `STORE_CORRUPT` 且不写（纪元切换须先由 CORE-26 的 `on_epoch_changed` 调 `clear_sync_cursor`）；`epoch` 相同 → 以注入的 `order.compare(现有 cursor, next)` 判定：`Less` 写入并返回 `written=true`，`Equal`/`Greater` 不改行并返回 `written=false` 与现有行（`updated_at_ms` 不前移）。`order` 返回 `Err` 时原样上抛、行不变，由调用方回滚整个事务。写入只更新 `sync_cursor` 一行的 `cursor/epoch/updated_at_ms`（= 调用方 `now_ms`），**不写 outbox、不分配时钟、不改 `local_clock`、不触发 stats 失效**。
- `clear_sync_cursor`：删除该 `stream` 行，返回是否确有一行；供 CORE-26 的 `on_epoch_changed` 清游标，不写 outbox 与其他表。
- 写门：`pause_writes` 计数 +1 并登记拒绝模板；已暂停时再次暂停且错误码不同 → `STORE_CORRUPT`（不允许两个不同原因互相覆盖），错误码相同则只计数。暂停期间 `write_gated` **在进入写队列之前**直接返回该模板的克隆，不排队、不占 5 s 超时、不产生 `STORE_BUSY`；门打开时 `write_gated` 与 CORE-13 的 `Store::write` 逐字同义（同一 actor、同一事务、同一回滚语义）。`resume` 或 `Drop` 释放一次，计数归零才回到 `Open`。门状态只存在于进程内、不持久化：`Store` 打开时为 `Open`，重启后由 CORE-24 依据未完成 journal 重新暂停。
- 门的作用面：只拦 `write_gated`。`Store::write` 不受门约束，供 CORE-13 的 `store.*`、CORE-24 的升级步骤与基础设施写入使用；**其余卡不得用 `Store::write` 绕过门**。读（`Store.read` 与本卡全部读取）、`integrity_check`、`close` 不受门影响；已进入 actor 的写命令照常完成，门只影响其后进入的命令。
- 表与事务规则仍唯一：`field_clock`、`sync_cursor`、`tombstone` 的 DDL、写入与时钟规则只在 CORE-13；本卡不新增迁移文件、不改 `SCHEMA_VERSION`、不改任何列。**禁止消费方自拼 SQL**：不得直接 `SELECT`/`INSERT`/`UPDATE` 这三张表（含自行 `UPSERT sync_cursor` 或自行判游标单调），也不得复制本卡的列读取逻辑；需要新读取面时按 README §8.4 提契约变更单给本卡。

错误码（全部复用他卡定义，本卡不新增代码）：

| 错误码（引用） | 定义卡 | 本卡触发条件 |
| --- | --- | --- |
| `STORE_CORRUPT` | CORE-13 | 未登记类型读取、存活实体缺字段时钟、游标 `epoch` 不符、行内持久化格式不符、暂停时以不同错误码再次暂停 |
| `FFI_BAD_ARG` | CORE-03 | `list_tombstones` 的 `now_ms` 非正；`stream` 为空串 |
| `SYNC_UPGRADE_IN_PROGRESS` | CORE-24 | 非本卡触发：门暂停时原样返回 CORE-24 在 `pause_writes` 登记的模板，本卡不定义也不硬编码该码 |

**实现约束**
- 单一来源：读装载路径只在本卡一处，消费卡只能用上述符号；本卡不导出 `Connection` 之外的写入口，写游标只能经 `WriteTx`。
- 事务纪律：全部读取在调用方已开启的事务内完成，函数内不 BEGIN/COMMIT/ROLLBACK、不重试、不吞错；错误原样上抛，回滚由持有事务的调用方负责。
- 不缓存：每次调用都从当前事务视图读数，不在 `Store` 或注册表里保留副本；游标与时钟的任何缓存化视为契约破坏。
- `CursorOrder` 是唯一注入点：本卡不解析 `cursor` 文本、不认识 `v1:<epoch>:<seq>`；S2 验收用 `FakeCursorOrder`，S6 由格式所有者（CORE-25 的游标格式、CORE-26/66 的接线）提供同一实现，保证两卡共用一次单调判定。
- 写门不参与持久化与恢复：本卡不写任何表、不读 journal；"暂停中"不得由 SQL 或文件推断，只由 `pause_writes` 的句柄计数决定。
- 时间与随机：`now_ms` 全部由调用方传入，本卡不读系统时钟；本卡不取随机数、不消耗 `IdSource`。
- 外部前提：`rusqlite`、`serde_json`、`blake3` 随 CORE-13 锁定，本卡不引入新依赖；`fml-store` 保持 `#![forbid(unsafe_code)]`。
- 测试接缝（crate 内部，非公共契约）：`FakeCursorOrder` 与门状态的观察句柄经 `#[cfg(test)]` 注入，生产不使用。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-102_TEST.md](../Test/core/S2_CORE-102_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 130 行；单包 `crates/fml-store/`（`src/sync_read.rs` 约 85、`src/write_gate.rs` 约 45）。不新增 FFI op、迁移文件、DTO 与错误码；消费卡的接线计入各自 S6 规模。
