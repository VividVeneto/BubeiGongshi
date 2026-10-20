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
PUT  /v1/keys/{key_version}/{wrap_kind}            { record_base64 }（CORE-21 WrapRecord CBOR 的不透明标准 base64，解码≤4 KiB；服务端不解析密钥字段）→ 204；同键覆盖（重新包装）；wrap_kind 取 CORE-21 线上名，只接受 recovery_code | sync_passphrase，GET 原样返回 PUT 存入的字节
POST /v1/keys/min-version                          { min_key_version }（只增不减）→ 204
POST /v1/account/delete                            { confirm: "DELETE" }（需 300 s 内重新认证）→ 202 { deletion_id }
GET  /v1/account/deletions/{deletion_id}           → 200 { state: requested|revoked|data_deleted|done }
```

Envelope v2字段、Rust结构和编码唯一归CORE-68，本卡/客户端都import fml_sync_proto::Envelope，禁止镜像。

- 游标：不透明字符串（base64url 编码的 `v1:<account_epoch>:<server_seq>`）；纪元不符或无法解析 → `SYNC_CURSOR_INVALID`。
- 表（`server/migrations/0025_sync.sql`）：`sync_account`（`account_id PK`，`account_epoch INTEGER NOT NULL DEFAULT 1`，`min_key_version INTEGER NOT NULL DEFAULT 1`，`bytes_used BIGINT`，`object_count BIGINT`）、`sync_envelope`（`server_seq BIGSERIAL PK`，`account_id`，`account_epoch`，`op_id UUID`，`device_id`，`device_seq`，`key_version`，`entity_type`，`entity_id`，`size INTEGER`，`ciphertext_hash BYTEA`，`body BYTEA`，`received_at`；唯一 `(account_id, account_epoch, op_id)`，索引 `(account_id, server_seq)`）、`key_wrap`（PK `(account_id, key_version, wrap_kind)`，`record BYTEA`，`created_at`）、`snapshot`（`snapshot_id UUID PK`，`account_id`，`account_epoch`，`covers_through BIGINT`，`key_version`，`state TEXT`（`uploading`/`committed`），`chunk_hashes JSONB`，`created_at`；分片存对象存储 `snap/<account_id>/<snapshot_id>/<n>`）、`account_deletion`（`deletion_id UUID PK`，`account_id_hash BYTEA`，`state TEXT`，`requested_at`，`completed_at NULL`）、`deletion_manifest`（`account_id_hash`，`deleted_at`；备份恢复后重放）。
- 配额：每账户密文总量 ≤ 512 MiB、对象 ≤ 1 000 000 条、保留最近 2 个已提交快照；推送每账户每分钟 ≤ 60 次请求。
- 错误码（触发条件）：

| 错误码 | 级别 | 可重试 | HTTP | 触发条件 |
| --- | --- | --- | --- | --- |
| `SYNC_PAYLOAD_TOO_LARGE` | error | 否 | 413 | 单个 envelope 密文 > 256 KiB、请求 > 200 条或 > 1 MiB、分片 > 4 MiB、包装记录 > 4 KiB |
| `SYNC_HASH_MISMATCH` | error | 否 | 400 | `ciphertext_hash` 或快照分片哈希与内容不符 |
| `SYNC_KEY_VERSION_REJECTED` | error | 否 | 409 | `key_version` < `min_key_version`；`min-version` 请求值小于现值 |
| `SYNC_EPOCH_STALE` | error | 否 | 409 | envelope 或快照的 `account_epoch` 与服务端不符 |
| `SYNC_QUOTA_EXCEEDED` | error | 否 | 507 | 写入后超出容量或对象数配额 |
| `SYNC_CURSOR_INVALID` | error | 否 | 400 | 游标无法解析或纪元不符 |
| `SYNC_SNAPSHOT_INCOMPLETE` | error | 否 | 409 | 提交时缺分片或 `chunk_hashes` 数量与已传分片不符 |

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `AUTH_RECENT_LOGIN_REQUIRED` | CORE-22 | `sync/reset` 与 `account/delete` 检查访问令牌 `auth_time`，缺失（刷新所得令牌）或超过 300 s 即返回 401 |
| `AUTH_RATE_LIMITED` | CORE-22 | 推送超过每账户每分钟 60 次返回 429 与 `Retry-After` |

**实现约束**
- 服务端只能看到账户 ID、account_epoch、设备 ID 与序号、op_id、key_version、entity_type、随机 entity_id、密文大小与时间；不提供内容搜索；隐私政策须披露 entity_type 频次与大小等元数据。
- 幂等：先在一个数据库事务中持久化再 ACK；同 op_id 同哈希返回原 `server_seq`，不同哈希返回 CONFLICT（该条不写入，其余照常；op_id 是一次本地修改的唯一标识，客户端按“服务端已有同一修改”处理，见 CORE-26）。`server_seq` 只用于传输游标，不参与合并语义。
- 资源所有者只取自令牌；所有查询带 `account_id` 条件；越权访问返回 404。
- 账户删除：requested →（立即）revoked：吊销全部会话、拒绝之后的上传 → data_deleted：删除生产数据、对象存储分片与包装记录（目标 24 h 内）→ done；备份 30 天内过期，从备份恢复时按 `deletion_manifest` 重放删除；保留例外仅限：费用墓碑（job_id 哈希、计费状态、时间，30 天）、网络与安全日志（按法规不少于 6 个月）、删除清单（至最后一份备份过期）。
- 同步不是备份：服务端数据库每日加密备份由 CORE-43 负责。
- 外部前提：对象存储 S3 兼容接口（产品随 CORE-43 部署选定）；sqlx 与 PostgreSQL 版本随 ADR-V5-15锁定。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-25_TEST.md](../Test/core/S6_CORE-25_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 500 行；`server/`（`server/src/sync/`、`server/src/account/` 与迁移 `server/migrations/0025_sync.sql`，DDL 不计）。

