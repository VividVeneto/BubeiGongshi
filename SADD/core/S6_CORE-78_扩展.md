### CORE-78 同步推送批次持久化

**目标**：把已加密、待推送的批次连同密文字节持久化，使崩溃、超时或重启后重发的始终是同一批字节，并以原子方式结算与作废。本卡自 CORE-26 拆出（CORE-26 估算超 500 行）。

**范围**
- 包含：`push_batch` 表与迁移、`StoredBatch`、批次保存/读取/结算/作废函数（均在调用方的同一写事务内执行）、结算时对 `sync_outbox` 行的同事务删除。
- 不包含：加密、Envelope 构造与元素字节编码（CORE-26（下游说明，非契约），编码见 CORE-68）、推送请求、请求体计量与重试（CORE-26/CORE-46（下游说明，非契约））、合并与隔离（CORE-26（下游说明，非契约））。

**依赖**：CORE-01、CORE-02、CORE-13

**接口契约**

```rust
// crates/fml-store/src/sync/batch.rs
pub struct StoredBatch { pub batch_id: Uuid, pub account_epoch: u32 /* ≥ 1 */, pub key_version: u32 /* ≥ 1 */, pub op_ids: Vec<Uuid>,
                         pub envelopes: Vec<Vec<u8>> /* 与 op_ids 一一对应、顺序相同的元素字节，由调用方编码，本卡不解析 */,
                         pub created_at_ms: i64 /* 调用方提供，仅作诊断，不参与排序 */ }
pub enum InvalidateReason { EpochChanged, KeyRotated, Stale /* 批次的 account_epoch/key_version 与当前密钥不一致 */ }
pub struct SettleReport { pub removed_ops: u32, pub remaining: u32, pub batch_deleted: bool }
pub const MAX_BATCH_OPS: usize = 200;
pub const MAX_BATCH_ELEMENT_BYTES: usize = 1_048_576;   // 元素字节之和的上限（防御性检查）
pub fn save_batch(tx: &mut WriteTx, batch: &StoredBatch) -> Result<(), FmlError>;
pub fn pending_batch(tx: &WriteTx) -> Result<Option<StoredBatch>, FmlError>;   // 未结算批次；不变量保证至多一个
pub fn settle(tx: &mut WriteTx, batch_id: Uuid, settled: &[Uuid]) -> Result<SettleReport, FmlError>;
pub fn invalidate_all(tx: &mut WriteTx, reason: InvalidateReason) -> Result<u32 /* 删除的批次数 */, FmlError>;
```

- 全部函数接收调用方的 CORE-13 `WriteTx`，使“查—建—存”“结算”“作废”与调用方的其他读写在同一单写者事务内原子完成；本卡不自行开启事务。
- 不变量：同一时刻至多一个未结算批次。构造方只在 `pending_batch` 返回 `None` 时构造新批次；新 outbox 条目等当前批次全部结算或作废后再进入下一批。
- 表（`crates/fml-store/migrations/0078_sync_batch.sql`，序号取本卡编号）：`push_batch`（`batch_id TEXT PK`，`account_epoch INTEGER NOT NULL CHECK (account_epoch >= 1)`，`key_version INTEGER NOT NULL CHECK (key_version >= 1)`，`op_ids_json TEXT NOT NULL`（小写带连字符的 UUID 字符串数组），`envelopes BLOB NOT NULL`，`created_at_ms INTEGER NOT NULL`）。`envelopes` 为各元素依次拼接的 `u32 大端长度 ‖ 元素字节`，元素个数等于 `op_ids` 长度，本卡定义此格式，不依赖 CBOR。
- `save_batch`：拒绝（`SYNC_BATCH_INVALID`）以下任一情况——`op_ids` 与 `envelopes` 不等长或为空、超过 `MAX_BATCH_OPS`、元素字节之和超过 `MAX_BATCH_ELEMENT_BYTES`、批内 `op_id` 重复、某个 `op_id` 不在 `sync_outbox`、`account_epoch` 或 `key_version` 为 0、`batch_id` 已存在或已有未结算批次。请求体上限（CORE-25（下游说明，非契约）的 1 MiB 请求体）由构造方 CORE-26（下游说明，非契约）按其口径保证；请求体必大于元素字节之和，故满足请求体上限的批次必然通过本卡检查。
- `settle`：删除 `settled` 中属于该批次的 op 对应的 `sync_outbox` 行与批次条目（不属于该批次的 op_id 忽略；`settled` 为空时不改动并返回 `SettleReport { removed_ops: 0, remaining: <批内条目数>, batch_deleted: false }`）；全部条目结算则删除批次（`batch_deleted = true`）；部分结算则用**剩余条目的原字节**改写 `op_ids_json` 与 `envelopes`，`batch_id` 不变。`batch_id` 不存在时：若 `settled` 中没有任何 op_id 仍在 `sync_outbox`，视为重复结算，返回 `SettleReport { removed_ops: 0, remaining: 0, batch_deleted: true }`；否则（批次已被作废而条目仍待推送）返回 `SYNC_BATCH_UNKNOWN`，不改动任何行。
- `invalidate_all`：删除全部批次，`sync_outbox` 行保留，回到待构造状态；`reason` 只随删除计数写入诊断日志，不改变行为。
- 错误码（本卡唯一定义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `SYNC_BATCH_UNKNOWN` | error | 否 | `settle` 的 `batch_id` 不存在，且 `settled` 中仍有 op_id 留在 `sync_outbox`（批次已被作废） |
| `SYNC_BATCH_INVALID` | error | 否 | `save_batch` 违反上列任一条件（长度、数量、元素字节和、批内重复、op_id 不在 outbox、epoch/key_version 为 0、batch_id 重复或已有未结算批次） |

**实现约束**
- 只做字节存取，不解密、不重新编码、不取随机数、不读时钟；已保存的元素字节不得被修改，部分结算时剩余条目的字节必须逐字节保持。
- 全部写操作在调用方传入的 CORE-13 `WriteTx` 中完成；`sync_outbox` 的新增仍只能经 CORE-13 事务规则，本卡只删除。
- 无新增 FFI op；`prepare_push`、`ack`、`on_epoch_changed` 由 CORE-26（下游说明，非契约）暴露。
- 外部前提：`rusqlite`（`bundled-sqlcipher`）、`uuid`、`serde_json` 沿用 CORE-13 与首张使用卡按 ADR-V5-15 锁定的版本；不引入 CBOR 等新第三方依赖。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-78_TEST.md](../Test/core/S6_CORE-78_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 120 行；`crates/fml-store/src/sync/batch.rs`（实现约 120 行；测试约 90 行，按 README §8.4 不计入规模；表迁移为数据不计，同属 fml-store 构建单元）。
