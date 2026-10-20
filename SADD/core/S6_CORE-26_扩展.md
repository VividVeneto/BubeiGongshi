### CORE-26 同步引擎（加密、合并与隔离）

**目标**：在核心内把本地变更加密成 envelope、解密并合并远端变更，保证幂等、可中断、无“最后写入胜出”；网络收发由 CORE-46 完成。

**范围**
- 包含：outbox 取批与 ACK 处理、实体负载编码、加密与 AAD、拉取结果的校验与按实体合并、隔离区、待选择记录、字段逻辑时钟、纪元变化处理；快照与轮换已迁至CORE-66（下游说明，非契约）；对应 FFI op。
- 不包含：HTTP 收发、触发时机与重试（CORE-46）；服务端（CORE-25）；同步界面（CORE-36）。

**依赖**：CORE-01、CORE-02、CORE-13、CORE-14、CORE-17、CORE-19、CORE-21、CORE-24、CORE-25、CORE-78

**接口契约**

```rust
// crates/fml-store/src/sync/mod.rs
pub struct AccountKeys { pub account_id: Uuid, pub account_epoch: u32, pub current: u32, keys: BTreeMap<u32, SecretKey> } // 由 account_key 表（CORE-24）加载
pub struct PushBatch { pub batch_id: Uuid, pub envelopes: Vec<Envelope> }        // Envelope 唯一定义见 CORE-68（经CORE-25依赖），import fml_sync_proto::Envelope；返回前已经 CORE-78 `save_batch` 持久化
pub enum PushResult { Ack { op_id: Uuid, server_seq: u64 }, Conflict { op_id: Uuid } }
pub struct PullPage { pub envelopes: Vec<Envelope>, pub next_cursor: String, pub has_more: bool, pub account_epoch: u32 }
pub struct ApplyReport { pub applied: u32, pub duplicates: u32, pub quarantined: u32, pub new_choices: u32 }
pub fn prepare_push(tx: &mut WriteTx, keys: &AccountKeys, rng: &mut dyn SecureRandom, max_count: u32 /* ≤ 200 */, max_bytes: u32 /* ≤ 1 MiB，口径见下 */) -> Result<Option<PushBatch>, FmlError>;
// 全部在调用方的同一写事务内：先调 CORE-78 `pending_batch(tx)`；有未结算批次且其 account_epoch == keys.account_epoch、key_version == keys.current，则原样返回其持久化字节，不取 rng、不重新加密；二者任一不一致（如另一设备轮换后本机经 import_account_key 取得新版本、或纪元已变），先 `invalidate_all(tx, Stale)` 再按当前密钥重建；无批次时读取 outbox 构造并加密新批次，并 `save_batch(tx)` 落盘。rng 由 FFI 适配传入 CORE-23 OsRandom，nonce 经 seal_with_rng 逐条取得
pub fn ack(store: &Store, batch_id: Uuid, results: &[PushResult]) -> Result<(), FmlError>;   // 在一个 Store::write 内调 CORE-78 `settle(tx, …)`：Ack 与 Conflict 的条目都出队（Conflict = 服务端已有同一 op_id 的修改，视为同一修改，不进隔离区，并按“整库回退”规则处理）；results 未覆盖的条目留在批次中；全部结算后的重复 ack 返回 Ok（CORE-78 重复结算语义）；批次已被作废而条目仍在 outbox → SYNC_BATCH_UNKNOWN（CORE-78 定义，调用方按良性处理）
pub fn apply_pull(store: &Store, keys: &AccountKeys, page: &PullPage) -> Result<ApplyReport, FmlError>; // 一个事务：业务表 + 游标
pub fn on_epoch_changed(store: &Store, server_epoch: u32) -> Result<(), FmlError>; // 清游标，按实体重建全量 outbox，并在同一事务调 CORE-78 `invalidate_all(EpochChanged)`
pub fn resolve_choice(store: &Store, choice_id: Uuid, chosen: RevisionId) -> Result<(), FmlError>;
```

- 实体类型与密钥用途：

| `entity_type` | 来源表（归属卡） | `KeyPurpose` |
| --- | --- | --- |
| `formula_item`、`formula_revision`（含其 `symbol_binding`）、`user_unit`、`notation_profile`、`constant_set` | CORE-14 | `UserFormula` |
| `calculation_plan` | CORE-48 | `UserFormula` |
| `study_card`、`review_event` | CORE-17 | `StudyData` |
| `book`、`study_plan`、`attempt`、`confusable_group` | CORE-19 | `StudyData` |
| `merge_choice` | 本卡 | `UserFormula` |
| `setting`（`local_setting.syncable = 1` 的键） | CORE-13 | `UserSettings` |
| `tombstone` | CORE-13 | 与被删实体相同 |

  不同步：`derivation`（由修订重建）、`study_session`、`*_cache`、识别历史、`device.*` 设置、本机密钥。
- 负载：明文为确定性 CBOR `{1: schema_version, 2: entity_type, 3: entity_id, 4: body（CORE-13 outbox 本地明文中 `entity` 部分的 JSON UTF-8 字节；删除时为空字节串）, 5: clocks（map：字段名 → `[counter, device_id 16 字节]`，原样取自同一 outbox 行的 `clocks`；删除只含 `__deleted`，不可变修订与事件只含 `__entity`）}`；本卡只做编码与加密，不重新取时钟；密钥 = `derive_subkey(AccountDataKey, purpose, key_version)`；AAD = `aad_cbor(AadFields { domain: "sync.entity", account_id, entity_type, entity_id, key_version, format_version: aad_version })`；解密后内层 `entity_type` / `entity_id` 必须与外层一致。修订负载携带源码与规范化元数据而非 AST，接收端在 CORE-06 预算内重新解析。

合并规则：

| 实体 | 策略 |
| --- | --- |
| 公式修订 | 不可变修订 DAG；出现并发头时生成 `merge_choice`（ID 调 CORE-05 merge_choice_id，按规范字节生成，两端一致），用户选择一次，选择结果也同步；卡片在选择前保持原绑定 |
| 公式条目元数据、学习计划、书、自定义单位元数据 | 按字段合并：逐字段比较负载 `clocks` 与本地 `field_clock` 的 `(counter, device_id 网络字节)`，大者胜，胜出字段连同其时钟写入（CORE-13 合并规则）；标签为增删集合；不是整对象覆盖 |
| 自定义单位、记号方案命名冲突 | 两者都保留，后到者名称加后缀并生成提示，不静默覆盖 |
| 复习事件与作答 | 追加合并，按 event_id 去重；排序与重放规则见 CORE-17 |
| 设置 | 可同步标量按该键的 `(counter, device_id)`；设备设置不同步 |
| 删除 | 墓碑（只含对象 ID、版本与删除时间）保留 180 天；墓碑之后到达的旧版本被丢弃，防止复活 |

- 表（`crates/fml-store/migrations/0026_sync.sql`）：`sync_quarantine`（`op_id TEXT PK`，`entity_type TEXT`，`reason TEXT NOT NULL`（错误码），`received_at_ms`，`raw BLOB` ≤ 256 KiB；保留 30 天）、`merge_choice`（`id TEXT PK`，`item_id TEXT NOT NULL`，`heads_json TEXT NOT NULL`，`chosen_revision TEXT NULL`，`created_at_ms`，`resolved_at_ms NULL`）、`field_clock` 的 DDL 与本地生成规则只见 CORE-13，本卡迁移不得重复创建。
- FFI op：`sync.prepare_push`、`sync.ack`、`sync.apply_pull`、`sync.cursor`（→ `{ cursor, account_epoch }`）、`sync.on_epoch_changed`、`sync.status`（→ `{ outbox_len, quarantined, open_choices, last_applied_ms }`）、`sync.choices`、`sync.resolve_choice`（轮换/快照三op唯一归CORE-66）。请求与响应字段即上方 Rust 函数的参数与返回值（JSON，二进制 base64）。
- 错误码（触发条件）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `SYNC_DECRYPT_FAILED` | warning | 否 | 标签校验失败（该条进隔离区，批次其余照常） |
| `SYNC_AAD_MISMATCH` | warning | 否 | 内层与外层 `entity_type` / `entity_id` / `key_version` 不一致 |
| `SYNC_QUARANTINED` | warning | 否 | 未知 `schema_version`、未知 `entity_type`、负载无法解析或哈希不符 |
| `SYNC_KEY_MISSING` | error | 否 | 本地无 envelope 的 `key_version` 对应密钥：暂停该页、不前移游标，引导用恢复码或同步密语恢复 |
| `SYNC_DISABLED` | info | 否 | 游客或未开启同步时调用任一 `sync.*` op |
| `SYNC_CHOICE_INVALID` | error | 否 | `resolve_choice` 选择的修订不在该记录的头集合中 |

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `SYNC_BATCH_UNKNOWN` | CORE-78 | `ack` 的批次已被作废且条目仍在 outbox 时原样透传；重复全额结算不报错 |
| `SYNC_BATCH_INVALID` | CORE-78 | `prepare_push` 原样透传（仅在违反 CORE-78 不变量的编程错误下出现） |
| `STORE_BUSY`、`STORE_DISK_FULL`、`STORE_CORRUPT` | CORE-13 | `prepare_push`、`ack`、`apply_pull`、`on_epoch_changed`、`resolve_choice` 的写事务失败时原样透传 |

本地写入 → outbox → 上传 → 合并端到端不变量：

1. CORE-13 单事务提交实体、field_clock、op_id/设备序号及明文 outbox；事务内更新 stats_generation（见 CORE-20），失败全回滚。
2. prepare_push 在一个写事务内读取已提交 outbox，按 op_id 固定构造 Envelope；加密后的 Envelope 字节与批次在同一事务经 CORE-78 `save_batch` 写入 `push_batch`，提交后才返回给调用方发送；服务端按 (account_epoch,op_id) 幂等持久化，返回 ACK；客户端仅删 ACK/Conflict 覆盖项。超时、崩溃或重启后重发的是 push_batch 中的同一批次字节（不重新加密、nonce 与密文不变）。
3. pull 验证/AAD 解密后，一个档案事务按 CORE-13 时钟规则合并实体、递增 stats_generation 并写 cursor；缺密钥不前移，恶意内容按隔离规则处理，不产生回声 outbox。
4. 复习/作答事件按 UUID 去重，排序只用于纯重放，不用到达顺序。统计缓存与预置查询投影均非权威数据，不进同步。游客绝不上传，转注册只改变出网资格与密钥，不改变已有实体ID。

这些规则在 S2/S3/S4 各写仓储时已生效；本卡只组装推拉与合并，不能另定义时钟生成器。

- 整库回退（WIN-16 回滚、CORE-27 恢复或用户手动复制旧库后，本地 `local_clock` 落后于已推送的数据）：`apply_pull` 遇到 `device_id` 等于本机且 `device_seq` 大于本机 `local_clock.device_seq` 的 envelope，或推送结果中本机 op_id 返回 `CONFLICT`，即判定发生回退。处理在同一合并事务内完成：按普通远端数据合并这些 envelope（找回回退前已推送的修改），再调用 CORE-13 `rotate_device_id(本批见过的最大 counter)`，之后的本地写入用新设备身份，不再与旧序号或旧时钟重叠；`CONFLICT` 的 op_id 视为服务端已有同一修改（op_id 是一次本地修改的唯一标识），从 outbox 与 `push_batch` 删除，不重试，也不进隔离区；批次字节已持久化，同一 op_id 的原样重发得到 ACK，因此 `CONFLICT` 只会出现在整库回退（回退副本中的待推送修改早已由原库推送）或 op_id 复用时，随后由 `apply_pull` 的 `device_seq` 规则完成身份更换。回退到更换身份之间产生的同时钟异值由 CORE-13 的 BLAKE3 规则裁决（ADR-V5-33）。
- 持久化批次（ADR-V5-43）：`push_batch` 表、`save_batch/pending_batch/settle/invalidate_all` 与迁移 `0078_sync_batch.sql` 归 CORE-78（自本卡拆出），本卡只在 `prepare_push`、`ack`、`on_epoch_changed` 中调用；同一时刻至多一个未结算批次；未 ACK 且纪元、密钥版本未变的批次在下次 `prepare_push` 原样重发，`op_id` 与密文字节不变；纪元或密钥版本已变的批次作废后按当前密钥重建（重建条目中服务端已存的 op_id 返回 `CONFLICT` 并按同一修改出队）。
- 批次字节口径（ADR-V5-43）：`PushBatch` 中每个 Envelope 的元素字节为 CORE-68 `to_canonical_json`，即 CORE-78 `StoredBatch.envelopes` 的元素；`max_bytes` 计量 CORE-25 `POST /v1/sync/push` 的请求体紧凑 JSON 字节数：`{"envelopes":[` + 各元素以 `,` 连接 + `]}`，即 16 + Σ元素字节 + (n − 1)；构造时按 outbox 顺序累加，加入下一条会使该值超过 `max_bytes` 或条数超过 `max_count` 即停止。Envelope 的字符串字段均为 ASCII 且不含需转义字符（UUID、标准 base64、十六进制、蛇形名），CORE-46 以紧凑 JSON 发送（无空白、不转义 `/`）时请求体长度与此计量逐字节相等。`device_seq` 只取 CORE-13 `local_clock`（经 `WriteTx::stamp` 分配），本卡不另存计数。

Store读写/加密批次编排和上述接收Store的API归fml-store::sync；纯字段合并在fml-sync只消费解密后的实体/字段时钟与已有值，返回合并值/冲突，不持Store、不I/O。fml-store可依赖fml-sync，反向禁止；CORE-66同样在存储层。

本卡全部op为profile scope。处理适配先由CORE-03解析profile_handle取得Store，再从CORE-24的account_key/account_state表在同一只读快照构造AccountKeys（current=max(key_version)；`sync.prepare_push` 例外：在一个 `Store::write` 内用该写事务读表构造 AccountKeys 并调用 `prepare_push(tx, …)`，使密钥读取、批次作废与落盘在同一事务，不与轮换或纪元变化交错），其账户必须等于库内account_id；缺失返回SYNC_KEY_MISSING。AccountKeys只作为原生Zeroizing局部值，禁止经JSON入出。prepare_push body={max_count:u32=200,max_bytes:u32=1048576}（适配层传入 CORE-23 OsRandom，不经 JSON），ok={batch?:PushBatch}（无待推送省略batch）；ack body={batch_id:UUID,results:PushResult[]}，ok={}；apply_pull body={page:PullPage}，ok=ApplyReport；cursor/status/choices body={}，分别返回既定游标、状态、{choices:MergeChoice[]}（本卡merge_choice表列一一映射，heads_json解为UUID数组）。on_epoch_changed body={server_epoch:u32}，resolve_choice body={choice_id:UUID,chosen:RevisionId}，ok均{}。上述均submit（含cursor/status，统一避免主线程等待Store），例status ok={"outbox_len":0,"quarantined":0,"open_choices":0,"last_applied_ms":0}；prepare_push无队列ok={}。

产品约束追踪：见README §6 Q3；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 禁止对任何数据使用整对象“最后写入胜出”；字段级比较只用于标量字段。
- outbox 与业务同事务写入（CORE-13）；`apply_pull` 在一个事务内写业务表、`field_clock` 与游标，失败整体回滚。
- 每批对象数与字节数限制同 CORE-25；单个负载 > 256 KiB 的实体拆分为修订链或拒绝写入（`LIB_*` 由 CORE-14 校验上限）。
- 核心不发网络请求，不持有令牌。
- 外部前提：CBOR 编码复用 CORE-21 的最小编码器；`uuid` v5。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-26_TEST.md](../Test/core/S6_CORE-26_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 380 行；主包 `crates/fml-store/src/sync/`（push70、pull100、payload60、merge编排50；不含测试约60），附属 `crates/fml-sync/src/merge.rs`（纯合并60）、`crates/fml-ffi/src/ops/sync.rs`（40）。不含CORE-66的snapshot/rotation；实作超估算必须先拆卡；批次持久化已拆出为 CORE-78。

