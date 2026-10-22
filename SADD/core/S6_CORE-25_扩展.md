### CORE-25 服务端同步存储与账户删除

**目标**：在服务端提供只按对象 ID 存取的密文同步服务、快照、包装密钥记录与账户删除流程，服务端无法解密任何学习内容。

**范围**
- 包含：`/v1/sync` 推送、拉取、快照、重置接口；`(account_id, account_epoch, op_id)` 唯一约束与幂等 ACK；大小、数量与容量配额；包装密钥记录存取与最低版本；账户删除与保留例外；对应表结构。
- 不包含：客户端加密与合并（CORE-26）；部署、对象存储与备份运维（CORE-43）。

**依赖**：CORE-01、CORE-02、CORE-22、CORE-21、CORE-68

**接口契约**

```text
POST /v1/sync/push      { envelopes: Envelope[] }（≤ 200 条且请求体 ≤ 1 MiB）
                        → 200 { results: [ { op_id, status: "ACK", server_seq } | { op_id, status: "CONFLICT" } ], account_epoch }
GET  /v1/sync/pull?after=<cursor>&limit=200&max_bytes=1048576
                        → 200 { envelopes: Envelope[], next_cursor, has_more, account_epoch }（after 缺省 = 从头）
PUT  /v1/sync/snapshots/{snapshot_id}/chunks/{n}   请求体为分片字节（≤ 4 MiB，n 从 0 起，≤ 255）→ 204
POST /v1/sync/snapshots/{snapshot_id}/commit       { covers_through: <cursor>, key_version, chunk_hashes: [sha256 hex] } → 204
GET  /v1/sync/snapshots/latest                     → 200 { snapshot_id, covers_through, key_version, chunks: [{ n, size, sha256, url }] } | 404
POST /v1/sync/reset                                （需 300 s 内重新认证）→ 200 { account_epoch }：删除该账户全部 envelope 与快照，纪元 + 1
GET  /v1/keys                                      → 200 { min_key_version, records: [{ key_version, wrap_kind, record_base64, created_at }] }
PUT  /v1/keys/{key_version}/{wrap_kind}            { record_base64 }（CORE-21 WrapRecord CBOR 的不透明标准 base64，解码≤4 KiB；服务端不解析密钥字段）→ 204；同键覆盖（重新包装）；wrap_kind 取 CORE-21 线上名，只接受 recovery_code | sync_passphrase（其他路径段返回 404 `SYNC_NOT_FOUND`），GET 原样返回 PUT 存入的字节
POST /v1/keys/min-version                          { min_key_version }（只增不减）→ 204
POST /v1/account/delete                            { confirm: "DELETE" }（需 300 s 内重新认证）→ 202 { deletion_id }
GET  /v1/account/deletions/{deletion_id}           → 200 { state: requested|revoked|data_deleted|done }
```

Envelope v2字段、Rust结构和编码唯一归CORE-68，本卡/客户端都import fml_sync_proto::Envelope，禁止镜像。上面 push 请求/响应与 pull 响应体同样以 CORE-68 的 PushRequest、PushItemResult（`status` 标签扁平对象）、PushResponse、PullResponse 序列化，本卡不另定义线类型。push 请求体先按 1 MiB 与 200 条限额读取，再以 `push_request_from_json` 解析校验，任一元素失败即整请求拒绝且不写入：`Invalid` → `SYNC_ENVELOPE_INVALID`（批内 op_id 重复同样以 `args.field = "op_id"` 拒绝）、`TooLarge` → `SYNC_PAYLOAD_TOO_LARGE`、`HashMismatch` → `SYNC_HASH_MISMATCH`；pull 响应中的 envelope 一律原样输出所存字节（即 push 时的 `to_canonical_json` 字节）。`results` 与请求 `envelopes` 等长、下标一一对应、顺序相同。

- 游标：不透明字符串（base64url 编码的 `v1:<account_epoch>:<server_seq>`）；省略游标表示本次只读快照当前epoch的序号0，空的首次pull也返回该epoch/0的编码；非首次空页保留原游标。纪元不符、序号为负或超出BIGINT、非规范整数或无法解析 → `SYNC_CURSOR_INVALID`。
- 表（`server/migrations/0025_sync.sql`）：`sync_account`（`account_id PK`，`account_epoch INTEGER NOT NULL DEFAULT 1`，`min_key_version INTEGER NOT NULL DEFAULT 1`，`bytes_used BIGINT`，`object_count BIGINT`，`last_seq BIGINT NOT NULL DEFAULT 0 CHECK (last_seq >= 0)`）、`sync_envelope`（`server_seq BIGINT NOT NULL CHECK (server_seq > 0)`，`account_id`，`account_epoch`，`op_id UUID`，`device_id`，`device_seq`，`key_version`，`entity_type`，`entity_id`，`size INTEGER`，`ciphertext_hash BYTEA`，`body BYTEA`（该 Envelope 的完整 `to_canonical_json` 字节，pull 直接拼入响应，不从列重建；其余列只作索引与配额），`received_at`；主键 `(account_id, account_epoch, server_seq)`，唯一 `(account_id, account_epoch, op_id)`；按该主键顺序分页）、`key_wrap`（PK `(account_id, key_version, wrap_kind)`，`record BYTEA`，`created_at`）、`snapshot`（`snapshot_id UUID PK`，`account_id`，`account_epoch`，`covers_through BIGINT`，`key_version`，`state TEXT`（`uploading`/`committed`），`chunk_hashes JSONB`，`created_at`；分片存对象存储 `snap/<account_id>/<snapshot_id>/<n>`）、`account_deletion`（`deletion_id UUID PK`，`account_id_hash BYTEA`，`state TEXT`，`requested_at`，`completed_at NULL`）。删除清单不放数据库（同库备份恢复后会缺失备份之后的删除）：data_deleted 完成时在对象存储独立前缀 `deletions/<deletion_id>.json` 只追加写入 `{"version":1,"account_id_hash":<小写 hex SHA-256(account_id 16 字节)>,"account_id":<UUID>,"deleted_at":<RFC 3339 UTC>}`，该前缀不进数据库备份、保留至最后一份备份过期（35 天）后清理。
- 序号分配与提交可见性（ADR-V5-48）：禁止BIGSERIAL/数据库sequence先取号后提交。push在同一数据库事务内先以INSERT … ON CONFLICT DO NOTHING建立sync_account行，再SELECT … FOR UPDATE锁定该账户；持锁后重新核对账户可写状态、epoch、最低密钥版本、配额及幂等记录。仅新插入的envelope按请求数组顺序递增last_seq并赋给server_seq；ACK重复与CONFLICT均不消耗序号。计数、envelope和配额更新一起提交后才返回ACK；整批事务失败则全部回滚，不能提前释放锁或逐条独立提交。last_seq不能溢出BIGINT；达到上限时拒绝新增为SYNC_QUOTA_EXCEEDED，重复ACK仍可返回既有序号。
- 同一账户的push、reset、最低密钥版本变更与删除禁写状态切换共用该行锁，并按相同顺序获取其他锁；不同账户没有全局互斥锁或全局序列依赖。reset在行锁内删除旧epoch数据、递增epoch并将last_seq置0，故序号只在(account_id, account_epoch)内有序且不复用；旧游标仍按epoch拒绝。账户删除后不得通过push重新创建可写账户，行初始化必须受CORE-22账户存续状态检查约束。
- pull 参数：`limit` 1..=200（缺省 200）、`max_bytes` 65 536..=1 048 576（缺省 1 048 576），超出范围按边界截取；按序加入 envelope，使 Σ`body` 字节 + (n − 1) ≤ `max_bytes`，加入下一条会超过即停止，但每页至少返回一条，即使该条单独超过 `max_bytes`（单条 body 受 CORE-68 密文上限约束，约 350 KiB）；`has_more` 表示停止时仍有未返回的已提交记录。
- pull不预分配序号；在一个只读一致性快照内读取epoch、按server_seq升序的已提交envelope及分页状态，next_cursor只前进到本页最后一条实际返回的序号（空页保留原游标），不使用last_seq/MAX(sequence)或未返回记录推进。因写者持同一账户行锁直到提交，不会在已经返回的较大游标之后才出现较小的已提交序号；不同账户的数值可相同，游标与查询始终受令牌account_id隔离。
- 配额：每账户密文总量 ≤ 512 MiB、对象 ≤ 1 000 000 条、保留最近 2 个已提交快照；推送每账户每分钟 ≤ 60 次请求。
- 错误码（触发条件）：

| 错误码 | 级别 | 可重试 | HTTP | 触发条件 |
| --- | --- | --- | --- | --- |
| `SYNC_PAYLOAD_TOO_LARGE` | error | 否 | 413 | 单个 envelope 密文 > 256 KiB（即 262144 字节，含 16 字节 AEAD tag，口径唯一定义在 CORE-68；对应明文 CBOR 上限 262128 由 CORE-26 与实体所有者卡换算）、请求 > 200 条或 > 1 MiB、分片 > 4 MiB、包装记录 > 4 KiB |
| `SYNC_HASH_MISMATCH` | error | 否 | 400 | `ciphertext_hash` 或快照分片哈希与内容不符 |
| `SYNC_ENVELOPE_INVALID` | error | 否 | 400 | push 请求体或其中 envelope 未通过 CORE-68 字段域校验（`args.field` 为首个出错字段名，外层或 JSON 结构错误为 `$`） |
| `SYNC_KEY_VERSION_REJECTED` | error | 否 | 409 | `key_version` < `min_key_version`；`min-version` 请求值小于现值 |
| `SYNC_EPOCH_STALE` | error | 否 | 409 | envelope 或快照的 `account_epoch` 与服务端不符；`args.account_epoch` 为服务端当前纪元（十进制字符串），客户端据此调用 CORE-26 `on_epoch_changed` |
| `SYNC_QUOTA_EXCEEDED` | error | 否 | 507 | 写入后超出容量或对象数配额，或该账户当前epoch的last_seq已达BIGINT上限而仍需新增envelope |
| `SYNC_CURSOR_INVALID` | error | 否 | 400 | 游标无法解析或纪元不符；纪元不符时 `args.account_epoch` 为服务端当前纪元（十进制字符串） |
| `SYNC_NOT_FOUND` | error | 否 | 404 | `snapshots/latest` 无已提交快照、`snapshot_id`/`deletion_id` 不存在或不属于令牌账户、keys 路由的 `wrap_kind` 不是登记线上名（不区分两者，避免枚举） |
| `SYNC_SNAPSHOT_INCOMPLETE` | error | 否 | 409 | 提交时缺分片或 `chunk_hashes` 数量与已传分片不符 |

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `AUTH_RECENT_LOGIN_REQUIRED` | CORE-22 | `sync/reset` 与 `account/delete` 检查访问令牌 `auth_time`，缺失（刷新所得令牌）或超过 300 s 即返回 401 |
| `AUTH_RATE_LIMITED` | CORE-22 | 推送超过每账户每分钟 60 次返回 429 与 `Retry-After` |
| `AUTH_TOKEN_INVALID` / `AUTH_TOKEN_EXPIRED` | CORE-22 | 全部本卡路由经 CORE-22 认证中间件，无令牌或无效令牌 401，不在本卡另判 |

**实现约束**
- 所有同步/包装记录/删除路由复用CORE-22的HTTP错误中间件：CORE-02 FmlError::with_trace只补零，已有非零trace不覆盖；响应头X-Fml-Request-Id、响应日志request_id与error.trace_id一致，禁止零trace出边界，不在本卡复制错误模型或重定义消息键。
- 服务端只能看到账户 ID、account_epoch、设备 ID 与序号、op_id、key_version、entity_type、不透明 entity_id（UUID 或设置键，见 CORE-68）、密文大小与时间；不提供内容搜索；隐私政策须披露 entity_type 频次与大小等元数据，并披露预置内容条目使用确定性 ID（CORE-05 pack_item_id），服务端可据此推断账户使用了哪些公开预置内容。
- 幂等：先在一个数据库事务中持久化再 ACK；同 op_id 同哈希返回原 `server_seq`，不同哈希返回 CONFLICT（该条不写入，其余照常；op_id 是一次本地修改的唯一标识，客户端按“服务端已有同一修改”处理，见 CORE-26）。`server_seq` 只用于传输游标，不参与合并语义。
- 资源所有者只取自令牌；所有查询带 `account_id` 条件；越权访问返回 404 `SYNC_NOT_FOUND`。客户端只按 `error.code` 区分错误（409、507 等状态码仅供网关观测，CORE-46（下游说明，非契约）不依赖状态码）。
- 账户删除：requested →（立即）revoked：吊销全部会话、拒绝之后的上传 → data_deleted：删除生产数据、对象存储分片与包装记录（目标 24 h 内）→ done；备份 30 天内过期，从备份恢复时由 CORE-43 restore.sh 运行 `fml-server replay-deletions`：读取 `deletions/` 前缀全部清单，对每个 account_id 幂等执行 data_deleted 步骤（不存在即跳过），输出重放条数，任一失败非零退出；保留例外仅限：费用墓碑（job_id 哈希、计费状态、时间，30 天）、网络与安全日志（按法规不少于 6 个月）、删除清单（对象存储 `deletions/` 前缀，至最后一份备份过期）。
- 同步不是备份：服务端数据库每日加密备份由 CORE-43 负责。
- 外部前提：对象存储 S3 兼容接口（产品随 CORE-43 部署选定）；sqlx 与 PostgreSQL 版本随 ADR-V5-15锁定。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-25_TEST.md](../Test/core/S6_CORE-25_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 555 行；`server/`（`server/src/sync/`、`server/src/account/` 与迁移 `server/migrations/0025_sync.sql`，DDL 不计）。分阶段：① 同步存储与包装密钥记录（push 含 sync_account 行锁内分配 seq、pull 与游标、快照、reset、keys 三端点、路由与错误映射、数据访问层，约 420）；② 账户删除与保留例外（delete 端点与状态查询、删除执行器、删除清单写入与 replay-deletions 子命令、保留例外清理、路由，约 135）。

