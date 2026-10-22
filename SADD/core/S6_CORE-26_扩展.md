### CORE-26 同步引擎（加密、合并与隔离）

**目标**：在核心内把本地变更加密成 envelope、解密并合并远端变更，保证幂等、可中断、无“最后写入胜出”；网络收发由 CORE-46 完成。

**范围**
- 包含：outbox 取批与 ACK 处理、实体负载编码、加密与 AAD、拉取结果的校验与按实体合并、隔离区、待选择记录、字段逻辑时钟、纪元变化处理；快照与轮换已迁至CORE-66（下游说明，非契约）；对应 FFI op。
- 不包含：HTTP 收发、触发时机与重试（CORE-46）；服务端（CORE-25）；同步界面（CORE-36）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-13、CORE-14、CORE-17、CORE-19、CORE-21、CORE-24、CORE-25、CORE-56、CORE-68、CORE-78、CORE-82、CORE-86

**接口契约**

```rust
// crates/fml-store/src/sync/mod.rs
pub struct AccountKeys { pub account_id: Uuid, pub account_epoch: u32, pub current: u32, keys: BTreeMap<u32, SecretKey> } // 由 account_key 表（CORE-24）加载
pub struct PushBatch { pub batch_id: Uuid, pub envelopes: Vec<Envelope> }        // Envelope 唯一定义见 CORE-68（经CORE-25依赖），import fml_sync_proto::Envelope；返回前已经 CORE-78 `save_batch` 持久化
pub use fml_sync_proto::{PushItemResult as PushResult, PullResponse as PullPage};   // 线类型唯一定义见 CORE-68（Ack{op_id,server_seq} / Conflict{op_id}；PullPage 字段 envelopes/next_cursor/has_more/account_epoch），本卡不另定义
pub const PULL_CURSOR_STREAM: &str = "sync_pull";                                   // CORE-13 sync_cursor.stream 唯一取值；该行 epoch = keys.account_epoch；apply_pull 与 CORE-66 apply_snapshot 写、sync.cursor 读
pub struct ApplyReport { pub applied: u32, pub duplicates: u32, pub quarantined: u32, pub new_choices: u32 }
pub fn prepare_push(tx: &mut WriteTx, keys: &AccountKeys, rng: &mut dyn SecureRandom, max_count: u32 /* ≤ 200 */, max_bytes: u32 /* ≤ 1 MiB，口径见下 */) -> Result<Option<PushBatch>, FmlError>;
// 全部在调用方的同一写事务内：先调 CORE-78 `pending_batch(tx)`；有未结算批次且其 account_epoch == keys.account_epoch、key_version == keys.current，则原样返回其持久化字节，不取 rng、不重新加密；二者任一不一致（如另一设备轮换后本机经 import_account_key 取得新版本、或纪元已变），先 `invalidate_all(tx, Stale)` 再按当前密钥重建；无批次时读取 outbox 构造并加密新批次，并 `save_batch(tx)` 落盘。rng 由 FFI 适配传入 CORE-23 OsRandom，nonce 经 seal_with_rng 逐条取得
pub fn ack(store: &Store, batch_id: Uuid, results: &[PushResult]) -> Result<(), FmlError>;   // 在一个 Store::write 内调 CORE-78 `settle(tx, …)`：Ack 与 Conflict 的条目都出队（Conflict = 服务端已有同一 op_id 的修改，不进隔离区；正常密钥/epoch重包装也可能出现，不据此单独旋转身份）；results 未覆盖的条目留在批次中；全部结算后的重复 ack 返回 Ok（CORE-78 重复结算语义）；批次已被作废而条目仍在 outbox → SYNC_BATCH_UNKNOWN（CORE-78 定义，调用方按良性处理）
pub fn apply_pull(store: &Store, registry: &EntityRegistry, analyzer: &dyn RemoteRevisionAnalyzer, cancel: &CancelFlag, page: &PullPage, now_ms: i64) -> Result<ApplyReport, FmlError>; // 一个事务：业务表 + 游标 + 保留期清理；now_ms 由调用方传入（核心不读时钟）
pub fn on_epoch_changed(store: &Store, registry: &EntityRegistry, server_epoch: u32) -> Result<(), FmlError>; // 清游标，按实体重建全量 outbox，并在同一事务调 CORE-78 `invalidate_all(EpochChanged)`
pub fn resolve_choice(store: &Store, choice_id: Uuid, chosen: RevisionId, now_ms: i64) -> Result<(), FmlError>; // 唯一入口；语义见下“待选择解析”。core 不读时钟，now_ms 由调用方传入；本卡不写 formula_item、不改字段时钟，重绑走 CORE-14 受控入口
```

- 实体类型与密钥用途：

| `entity_type` | 来源表（归属卡） | `KeyPurpose` |
| --- | --- | --- |
| `formula_item`、`formula_revision`（含其 `symbol_binding`）、`user_unit`、`notation_profile`、`constant_set` | CORE-14 | `UserFormula` |
| `calculation_plan` | CORE-86（仓储、codec/applier 与删除） | `UserFormula` |
| `study_card`、`review_event` | CORE-17 | `StudyData` |
| `book`、`study_plan`、`attempt`、`confusable_group` | CORE-19（纯模型与 DDL）；CORE-82（仓储、codec/applier 与删除） | `StudyData` |
| `merge_choice` | 本卡 | `UserFormula` |
| `local_setting`（`syncable = 1` 的键；entity_type 按 CORE-13 规则取表名） | CORE-13 | `UserSettings` |
| Delete 墓碑（仍用原实体类型） | 原实体所有者；CORE-13 存墓碑 | 与被删实体相同 |

  不同步：`derivation`（由修订重建）、`study_session`、`*_cache`、识别历史、`device.*` 设置、本机密钥。
- 负载：明文为确定性 CBOR `{1: schema_version, 2: entity_type, 3: entity_id, 4: body（CORE-13 outbox 本地明文中 `entity` 部分的 JSON UTF-8 字节；删除时为空字节串）, 5: clocks（map：字段名 → `[counter, device_id 16 字节]`，原样取自同一 outbox 行的 `clocks`；删除只含 `__deleted`，不可变修订与事件只含 `__entity`）}`；本卡只做编码与加密，不重新取时钟；密钥 = `derive_subkey(AccountDataKey, purpose, key_version)`；AAD = `aad_cbor(AadFields { domain: "sync.entity", account_id, entity_type, entity_id, key_version, format_version: aad_version })`；解密后内层 `entity_type` / `entity_id` 必须与外层一致。修订负载携带源码与规范化元数据而非 AST，接收端在 CORE-06 预算内重新解析。

合并规则：

| 实体 | 策略 |
| --- | --- |
| 公式修订 | 不可变修订 DAG；出现并发头时生成 `merge_choice`（ID 调 CORE-05 merge_choice_id，按规范字节生成，两端一致），用户选择一次，选择结果也同步；卡片在选择前保持原绑定 |
| 公式条目元数据、学习计划、书、自定义单位元数据 | 按字段合并：逐字段比较负载 `clocks` 与本地 `field_clock` 的 `(counter, device_id 网络字节)`，大者胜，胜出字段连同其时钟写入（CORE-13 合并规则）；tags_json 作为规范化有序标签数组整体按单字段 LWW（不另造增删集合时钟）；不是整对象覆盖 |
| 自定义单位、记号方案命名冲突 | 两者都保留，后到者名称加后缀并生成提示，不静默覆盖 |
| 复习事件与作答 | 追加合并，按 event_id 去重；排序与重放规则见 CORE-17 |
| 设置 | 可同步标量按该键的 `(counter, device_id)`；设备设置不同步 |
| 删除 | 墓碑（只含对象 ID、版本与删除时间）保留 180 天；墓碑之后到达的旧版本被丢弃，防止复活 |

- 待选择解析（`resolve_choice`，本卡唯一入口；选择结果也同步）：
  - 合法性：同一 `Store::write` 内按 `choice_id` 读 `merge_choice` 行；无该行、或 `chosen` 不在此行 `heads_json` 解析出的 UUID 集合中 → `SYNC_CHOICE_INVALID`，整事务不写。
  - 幂等：行已 `resolved_at_ms` 非空且 `chosen_revision == chosen` → 返回 Ok，不写行、不产生 outbox（重复点击与重试安全）；已 resolved 而 `chosen` 不同 → `SYNC_CHOICE_INVALID`（选择一次不可改；要改只能由修订变化产生新的 `merge_choice`，ID 由 CORE-05 `merge_choice_id` 决定，因此不会与旧 ID 相同）。
  - 同一事务三段写入：①`UPDATE merge_choice SET chosen_revision = ?, resolved_at_ms = now_ms WHERE id = ?`；②该 `merge_choice` 实体按 CORE-13 outbox 钩子在本事务入 outbox（body/clocks 见下“merge_choice 负载”，`op_id` 与 device_seq 由 CORE-13 分配，本卡不另造）；③调用 CORE-14 的受控重绑入口把 `formula_item` 的 head 重绑到 `chosen`。任一步失败整体回滚（含 outbox 与选择行）。
  - 卡片状态：`study_card.pending_choice` 由 CORE-17 在同一事务据 `merge_choice` 行重算/清空，本卡不写 `study_card`；卡片在解析前保持原绑定（CORE-17 语义）。
  - 远端应用：`apply_pull` 收到 `merge_choice` 实体时由本卡 applier 写入/更新行，并在同一保存点对 `item_id` 调用同一 CORE-14 重绑入口；重绑只在行的 `chosen_revision` 因此次负载发生变化时执行一次，重复到达（Duplicate）与重复订阅不为每次到达重绑。两端 head 由此收敛到同一修订。
  - 契约变更单（README §8.4，所有者 CORE-14，本卡只提出不得代签）：新增 `rebind_head_from_choice(tx: &mut WriteTx, item_id: &str, chosen: RevisionId, now_ms: i64) -> Result<(), FmlError>`（旧：无公开重绑入口；新：上列签名）。约束：校验 `chosen` 存在于该条目的 `formula_revision` 行且属于其当前 heads，写 `formula_item` head 但不改写任何 `field_clock`、不写 `sync_outbox`（选择本身经 `merge_choice` 实体同步，重绑是派生结果，否则回声）。消费者与迁移风险：CORE-26 `resolve_choice` 与 `apply_pull` 依赖此入口；CORE-17 的 `pending_choice` 重算必须与「行 resolved」同一事务判定；CORE-14 现有 head 更新路径若不复用同一校验，则本机与远端会出现 head 分叉。CORE-14 的 Test 需补「外部重绑只改 head、不改 field_clock、不产生 outbox」「chosen 不在 heads → SYNC_CHOICE_INVALID」。**在 CORE-14 修订落地前，本卡 `resolve_choice` 视为阻断于所有者卡（CO-46 组），不得以私加声明绕过。**
- `merge_choice` 负载与合并（本卡是唯一所有者：`entity_type = merge_choice`、`KeyPurpose = UserFormula`）：
  - body = JSON UTF-8（确定性键序）`{"id":"<uuid>","item_id":"<uuid>","heads":["<uuid>",…],"chosen_revision":"<uuid>"|null,"created_at_ms":<i64>,"resolved_at_ms":<i64>|null}`；`heads` 按 UUID 字典序规范化，解析后集合相等即视为同一内容；`created_at_ms` 取首次生成时刻，重发不变。
  - clocks 只含 `__entity`：`[counter, device_id]`（由 CORE-13 `stamp` 分配），**不写字段级时钟**、不参与逐字段合并；本卡不为其写 `field_clock` 行。
  - 合并为整实体 LWW：`__entity` 大者胜；且 `resolved_at_ms` 非空的行不被同 ID 的空值负载覆盖（resolved 单调，防止已选择被回退）。两设备并发选择同一 `merge_choice` 时按 `__entity` 取一侧，另一侧的 `chosen_revision` 被丢弃，head 重绑随之收敛到胜者，不产生第二张 `merge_choice`。
  - Delete：`merge_choice` 不产生墓碑，也不进 180 天墓碑清理（记录只增；resolved 后保留以便重复页与回溯）。`sync.choices` 只返回 `resolved_at_ms IS NULL` 的行。
  - 表列与 body 一一对应（`id/item_id/heads_json/chosen_revision/created_at_ms/resolved_at_ms`），无第二套字段名。

- 表（`crates/fml-store/migrations/0026_sync.sql`）：`sync_quarantine`（`op_id TEXT PK`，`entity_type TEXT`，`reason TEXT NOT NULL`（错误码），`received_at_ms INTEGER NOT NULL`（= apply_pull 的 now_ms），`raw BLOB NOT NULL`（该 Envelope 的 `to_canonical_json` 字节，最多保留前 393 216 字节即 384 KiB，足以容纳 CORE-68 上限内的完整 Envelope），`raw_truncated INTEGER NOT NULL CHECK (raw_truncated IN (0,1))`（超过 384 KiB 被截断时为 1）；同一 op_id 再次隔离时保留首行；保留 30 天）、`merge_choice`（`id TEXT PK`，`item_id TEXT NOT NULL`，`heads_json TEXT NOT NULL`，`chosen_revision TEXT NULL`，`created_at_ms`，`resolved_at_ms NULL`）、`field_clock` 的 DDL 与本地生成规则只见 CORE-13，本卡迁移不得重复创建。
- FFI op：`sync.prepare_push`、`sync.ack`、`sync.apply_pull`、`sync.cursor`（→ `{ cursor, account_epoch }`）、`sync.on_epoch_changed`、`sync.status`（→ `{ outbox_len, quarantined, open_choices, last_applied_ms }`）、`sync.choices`、`sync.resolve_choice`（轮换/快照三op唯一归CORE-66）。请求与响应字段即上方 Rust 函数的参数与返回值（JSON，二进制 base64）。
- `sync.status` 响应中 `last_applied_ms` 字段的唯一真源：`sync_cursor` 中 `stream = 'sync_pull'`（即 `PULL_CURSOR_STREAM`）行的 `updated_at_ms`（列定义见 CORE-13），无该行时为 0。只有 `apply_pull` 成功提交才写该行并把 `updated_at_ms` 置为本次 `now_ms`（即使该页 `has_more=false` 且无 envelopes 也提交，表示“最近一次成功应用时间”）；page 校验失败、缺密钥、取消、存储错误、分析前提故障导致整页回滚时该值保持原值，不前移。`on_epoch_changed` 清游标后该项回到 0（不得保留旧纪元时间）。CORE-36 的 `lastSuccessAt` 直接映射此值，不另存本地时间戳、不按请求发出时间更新。
- 错误码（触发条件）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `SYNC_DECRYPT_FAILED` | warning | 否 | 标签校验失败（该条进隔离区，批次其余照常） |
| `SYNC_AAD_MISMATCH` | warning | 否 | 内层与外层 entity_type/entity_id 不一致；key_version 篡改由 AAD/认证校验拒绝（内层没有该字段） |
| `SYNC_QUARANTINED` | warning | 否 | Envelope 未通过 CORE-68 `validate`（含哈希不符与超长）、entity_id 形态与 entity_type 不符（UUID 实体须为小写 UUID、local_setting 须为匹配 `^[a-z0-9_.]+$` 的键）、未知 `schema_version`、未知 `entity_type` 或负载无法解析 |
| `SYNC_DISABLED` | info | 否 | 游客或未开启同步时调用任一 `sync.*` op |
| `SYNC_CHOICE_INVALID` | error | 否 | `resolve_choice` 选择的修订不在该记录的头集合中 |

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `SYNC_BATCH_UNKNOWN` | CORE-78 | `ack` 的批次已被作废且条目仍在 outbox 时原样透传；重复全额结算不报错 |
| `SYNC_KEY_MISSING` | CORE-24 | 本地无 envelope 的 `key_version` 对应密钥：暂停该页、不前移游标，引导用恢复码或同步密语恢复；`load_account_keys_tx` 产生的同码原样透传 |
| `SYNC_EPOCH_STALE` | CORE-25 | `apply_pull` 的 page.account_epoch 与库内不符时不合并并透传；`on_epoch_changed` 的 server_epoch 小于本地纪元时返回且不写入 |
| `SYNC_BATCH_INVALID` | CORE-78 | `prepare_push` 原样透传（仅在违反 CORE-78 不变量的编程错误下出现） |
| `STORE_BUSY`、`STORE_DISK_FULL`、`STORE_CORRUPT` | CORE-13 | `prepare_push`、`ack`、`apply_pull`、`on_epoch_changed`、`resolve_choice` 的写事务失败时原样透传 |

本地写入 → outbox → 上传 → 合并端到端不变量：

1. CORE-13 单事务提交实体、field_clock、op_id/设备序号及明文 outbox；事务内更新 stats_generation（见 CORE-20），失败全回滚。
2. prepare_push 在一个写事务内读取已提交 outbox，按 op_id 固定构造 Envelope；加密后的 Envelope 字节与批次在同一事务经 CORE-78 `save_batch` 写入 `push_batch`，提交后才返回给调用方发送；服务端按 (account_epoch,op_id) 幂等持久化，返回 ACK；客户端仅删 ACK/Conflict 覆盖项。超时、崩溃或重启后重发的是 push_batch 中的同一批次字节（不重新加密、nonce 与密文不变）。
3. pull 验证/AAD 解密后，一个档案事务按 CORE-13 时钟规则合并实体、递增 stats_generation 并写 cursor；缺密钥不前移，恶意内容按隔离规则处理，不产生回声 outbox。
4. 复习/作答事件按 UUID 去重，排序只用于纯重放，不用到达顺序。统计缓存与预置查询投影均非权威数据，不进同步。游客绝不上传，转注册只改变出网资格与密钥，不改变已有实体ID。

这些规则在 S2/S3/S4 各写仓储时已生效；本卡只组装推拉与合并，不能另定义时钟生成器。

- 整库回退：只有通过认证并完成负载/时钟校验的本机旧身份 envelope，其 device_seq 大于本机 local_clock.device_seq，才是回退证据。先按普通远端实体合并，再在同一事务 rotate_device_id(已验证远端最大 counter)；原实体 ID、事件 device_id/device_seq/tx_index 和 field_clock 不重写。Conflict 只结算对应 op_id，不单独证明回退：密钥/epoch 重包装也可正常产生 Conflict；后续 pull 完成证据判定。身份轮换 RNG 失败返回 CRYPTO_RNG_FAILED，整页含游标全回滚；同时钟异值按 CORE-13 BLAKE3 规则收敛。
- 持久化批次（ADR-V5-43）：`push_batch` 表、`save_batch/pending_batch/settle/invalidate_all` 与迁移 `0078_sync_batch.sql` 归 CORE-78（自本卡拆出），本卡只在 `prepare_push`、`ack`、`on_epoch_changed` 中调用；同一时刻至多一个未结算批次；未 ACK 且纪元、密钥版本未变的批次在下次 `prepare_push` 原样重发，`op_id` 与密文字节不变；纪元或密钥版本已变的批次作废后按当前密钥重建（重建条目中服务端已存的 op_id 返回 `CONFLICT` 并按同一修改出队）。
- 批次字节口径（ADR-V5-43）：`PushBatch` 中每个 Envelope 的元素字节为 CORE-68 `to_canonical_json`，即 CORE-78 `StoredBatch.envelopes` 的元素；`max_bytes` 计量 CORE-25 `POST /v1/sync/push` 的请求体紧凑 JSON 字节数：`{"envelopes":[` + 各元素以 `,` 连接 + `]}`，即 16 + Σ元素字节 + (n − 1)；构造时按 outbox 顺序累加，加入下一条会使该值超过 `max_bytes` 或条数超过 `max_count` 即停止。Envelope 的字符串字段均为 ASCII 且不含需转义字符（UUID、标准 base64、十六进制、蛇形名），CORE-46 以紧凑 JSON 发送（无空白、不转义 `/`）时请求体长度与此计量逐字节相等。`device_seq` 只取 CORE-13 `local_clock`（经 `WriteTx::stamp` 分配），本卡不另存计数。

Store读写/加密批次编排和上述接收Store的API归fml-store::sync；纯字段合并在fml-sync只消费解密后的实体/字段时钟与已有值，返回合并值/冲突，不持Store、不I/O。fml-store可依赖fml-sync，反向禁止；CORE-66同样在存储层。

本卡全部op为profile scope。处理适配先由CORE-03解析profile_handle取得Store，再从CORE-24的account_key/account_state表在同一只读快照构造AccountKeys（current=max(key_version)；prepare_push与apply_pull在各自Store.write内部用load_account_keys_tx，密钥与epoch读取不与轮换交错），其账户必须等于库内account_id；缺失返回SYNC_KEY_MISSING。AccountKeys只作为原生Zeroizing局部值，禁止经JSON入出。prepare_push body={max_count:u32=200,max_bytes:u32=1048576}（适配层传入 CORE-23 OsRandom，不经 JSON），ok={batch?:PushBatch}（无待推送省略batch）；ack body={batch_id:UUID,results:PushResult[]}，ok={}；apply_pull body={page:PullPage,now_ms:i64}，ok=ApplyReport；cursor/status/choices body={}，分别返回既定游标、状态、{choices:MergeChoice[]}（本卡merge_choice表列一一映射，heads_json解为UUID数组）。on_epoch_changed body={server_epoch:u32}，resolve_choice body={choice_id:UUID,chosen:RevisionId,now_ms:i64}，ok均{}。上述均submit（含cursor/status，统一避免主线程等待Store），例status ok={"outbox_len":0,"quarantined":0,"open_choices":0,"last_applied_ms":0}；prepare_push无队列ok={}。

**所有者分派、事务与分析接线**

- FFI 的组合层建立一个 EntityRegistry：CORE-13 setting、CORE-14 公式/单位/记号/常数、CORE-17 卡片/事件、CORE-82 学习实体、CORE-86 calculation_plan 与本卡 merge_choice 各注册一次。registry 是原生只读接线，不新增 JSON 字段；不登记 study_session、参数或缓存。应用 Delete 仍分派原 entity_type。
- apply_pull 进入一个 Store.write 后调用 CORE-24 load_account_keys_tx，从相同事务构造 keys；按依赖拓扑先应用 user_unit/notation_profile，再 formula_revision，再 formula_item，再依赖修订的其他实体；同层按 entity_type/entity_id 稳定排序，不用到达次序决定缓存。每条保存点调用 registry.apply；Invalid 回滚该条并隔离，Duplicate 无写；SQL/I/O/取消/缺密钥等 Err 回滚整页与游标。先验证完整页的密钥与 epoch 再改表；page.account_epoch 与库不符不合并，透传 SYNC_EPOCH_STALE 交协调器处理。remote最大counter只取验证通过的负载，lamport=max(local,remote)，不调用 stamp/enqueue_outbox；统计失效hook归CORE-20，不在本卡重复计行。
- 具体 RemoteRevisionAnalyzer 实现位于本卡 fml-ffi/src/ops/sync_analysis.rs（S6，不属于 CORE-56 S1）：取得一次 EngineContext.snapshot()?，在调用领域算法前检查该 Arc 的 unavailable；快照获取失败或 unavailable 非空按 CORE-56 返回 ENGINE_UNAVAILABLE。对传入 conn 合同只读地加载当前事务全部 user_unit；目标记号方案按输入 notation_profile_id 精确查当前事务 notation_profile，自建记录存在时使用它，否则在同一个 Arc.data.profiles 中查同 ID 的 Embedded/Pack 方案，二者均无则 NOTATION_UNBOUND，绝不改用其他默认 ID。此顺序是事务自建叠加层加同代引擎基础数据，不混入另一代全局值。先以 CORE-08 MemRegistry::from_parts(snapshot.base_units.clone(),snapshot.base_kinds.clone()) 构造不含User的base，再 MemRegistry::with_user_definitions(&base,&tx_defs) 构造临时单位表；不修改全局 EngineContext、不嵌套 Store.read/write。将输入 source_latex/profile/user_decls/units/empirical 与 CORE-03 该任务 CancelFlag 连同显式 ParseOptions { budget_ms: 100, allow_unicode: true } 传给 CORE-56 analyze_source；把 ast/symbols 与 check_result.validation/diagnostics 投影成 CORE-13 RemoteRevisionAnalysis，保留并验证 conditions。没有 AST 则 None，不回退上传 AST；取消、ENGINE_UNAVAILABLE、NOTATION_UNBOUND 等本地分析前提故障原样 Err，整页与游标回滚，不作为恶意内容隔离。输出不依赖下游导入适配。
- apply_pull 的 analyzer/cancel 由该 FFI handler 构造/借用，cancel 是原任务旗标，不自建永不取消的旗标。快照 handler 复用此适配（接线行归 CORE-66）；Rust测试可注入Fake。接收方 formula_revision 的 user_decls=上传 symbols.decls.clone()（CORE-05 真字段），但重新 bind/check 的结果覆盖本地 ast/symbols/validation 缓存，不相信上传验证结论。
- 保留期清理：apply_pull 在同一写事务末尾删除 `received_at_ms < now_ms − 2 592 000 000`（30 天）的 sync_quarantine 行，并调用 CORE-13 `purge_tombstones(now_ms − 15 552 000 000)`（180 天）；清理不计入 ApplyReport，不入 outbox；页内容非法导致整页回滚时清理一并回滚。
- on_epoch_changed 同一写事务作废批次、清 cursor/outbox、更新 account_epoch（`server_epoch` 等于本地值时同样执行，用于 CORE-46 处理无纪元的 `SYNC_CURSOR_INVALID`；小于本地值返回 `SYNC_EPOCH_STALE` 不写入），然后按 registry 稳定枚举存活实体与未过期墓碑调用 requeue_outbox；保留字段时钟/实体ID，不伪造全库编辑；失败全回滚。
- Envelope 字段逐项来源：envelope_version=2、kind=event、account_epoch=keys.account_epoch；op_id/device_id/device_seq 来自该 outbox 固定行；key_version=keys.current；entity_type/entity_id 来自 codec；仅 formula_revision 有 revision_id=entity_id；schema_version=1、aad_version=1、purpose 为上表 KeyPurpose 的 CORE-21 蛇形线名；nonce 为 `Sealed.nonce`（24 字节）、ciphertext 为 `Sealed.ciphertext`（含 16 字节标签，不含 `Sealed.version` 字节与重复 nonce）各自的标准base64，`Sealed.version` 必须为 1、由 aad_version=1 隐含，接收端按 version=1 重组 Sealed 后解密，ciphertext_hash=SHA-256(raw ciphertext)小写hex。删除 body 空，但类型/ID与 __deleted 时钟仍认证。

产品约束追踪：见README §6 Q3；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 禁止对任何数据使用整对象“最后写入胜出”；字段级比较只用于标量字段。
- outbox 与业务同事务写入（CORE-13）；`apply_pull` 在一个事务内写业务表、`field_clock` 与游标，失败整体回滚。
- 每批对象数与字节数限制同 CORE-25；单实体上限的唯一定义在 CORE-68（密文解码 262144 字节，含 16 字节 AEAD tag），故本卡编码前要求明文确定性 CBOR ≤ 262128 字节（= 262144 − 16），超限实体不生成 Envelope、不进入批次；本卡不拆分修订链、不新造错误码，写入侧对该实体的拒绝沿用其所有者卡的既有码（CORE-14 目前没有单实体负载超限码，缺口待其所有者补，本卡不代定义）。
- 核心不发网络请求，不持有令牌。
- 外部前提：本卡实现自身负载的最小严格确定性 CBOR 编解码，不调用 CORE-21 私有编码器；只接受上文 1..5 键、最短整数/长度、确定性 map 键序、无重复键/尾随字节、无不定长项。CORE-21 仅提供公开 aad_cbor/加解密。字节向量 SY-PAYLOAD-V1 由本卡在 crates/fml-store/tests/vectors/sync_payload_v1.hex 交付：固定实体/时钟，由独立 RFC 8949 参照手算复核，含 delete、空 clocks、非法编码反例；不得用被测实现生成期望值。uuid v5 仅用于 CORE-05 已定义确定性 ID，不用于 op_id。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-26_TEST.md](../Test/core/S6_CORE-26_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 730 行；主包 `crates/fml-store/src/sync/`（约 550），附属 `crates/fml-sync/src/merge.rs`（纯字段合并，约 70）、`crates/fml-ffi/src/ops/sync.rs`（8 个 sync.* op 与事务只读分析适配，约 110）。不含 CORE-66 的 snapshot/rotation、CORE-78 的批次持久化，各实体 applier 本体计入所有者卡。分阶段：① 推送、负载与加密（类型、确定性 CBOR、加解密、prepare_push、ack、on_epoch_changed、cursor/status 与 5 个 op，约 320）；② 拉取合并、隔离与待选择（apply_pull 与 EntityApplier 分派、字段合并编排、merge_choice/隔离区与 codec/applier、fml-sync 纯合并、3 个 op，约 410）。两阶段各自可独立构建与测试：①覆盖 T-RESEND、并发与口径、SY-PAYLOAD-V1、负载字段、查询 op 与推送侧 5 个 op；②覆盖 T-SYNC、T-AAD/T-FIELD/T-ROLLBACK、隔离逐码与 raw、保留期、待选择、纪元与 3 个 op。②的 410 是修订前估算，未单列本轮补写的 `merge_choice` codec/applier、`resolve_choice` 与 CORE-14 重绑调用；编码会话须在阶段②实测后如实回报，超出约 500 行即按 §8.4 拆分或改报告，不以估算通过代替实测。

