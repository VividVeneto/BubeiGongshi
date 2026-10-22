# CORE-25 测试方案

> 来源卡：[S6_CORE-25_扩展.md](../../core/S6_CORE-25_扩展.md)（服务端同步存储与账户删除）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R28] 同步/keys/delete路由注入零trace与既有非零trace的错误，逐项断言CORE-22公共中间件仅补零、不覆盖已有值，响应头、响应日志request_id与error.trace_id一致且非零；HTTP状态仍按各码登记映射。
- [R28] 集成测试（`server/tests/sync.rs`）：推送 → 拉取往返；重复推送同 op_id 返回原 server_seq；同 op_id 不同哈希返回 CONFLICT；每个超限条件返回 `SYNC_PAYLOAD_TOO_LARGE`；分页拉取在 `max_bytes` 内且游标连续。
- [R28] PostgreSQL真实并发集成测试（不用sleep推测时序）：用两条独立连接与屏障令同账户事务A持行锁并分配N后暂停，B尝试写入并确认其阻塞，第三连接pull不得看到B的N+1或跳过A；分别让A提交/回滚后释放B，逐页拉取的op_id集合与已提交集合完全相等、无遗漏/重复，server_seq严格递增；回滚不遗留计数或数据。重复ACK/CONFLICT不增last_seq，批内多条按数组顺序分配，批后失败全部回滚；BIGINT上限拒绝新增且计数不回绕，重复ACK仍幂等。另让A持账户甲锁时，账户乙写入在A释放前完成，证明没有全局锁。
- [R28] 同账户push与reset/min-version/delete禁写切换交错：锁后复检拒绝旧epoch/过期key/已删除账户，不出现旧纪元晚提交；reset将last_seq清0但新旧epoch游标隔离；pull跨并发reset只返回同一一致性快照的数据/epoch，不混读，空页游标不跳到未返回序号；首次无游标空库返回当前epoch/0的规范编码，后续空页精确保留已给游标；负数、BIGINT溢出及非规范整数拒绝SYNC_CURSOR_INVALID。
- [R28] 快照：分片上传 → 提交 → `latest` 返回分片清单；缺分片提交返回 `SYNC_SNAPSHOT_INCOMPLETE`；第 3 个快照提交后最旧快照被清理。
- [R28] 重置：`/v1/sync/reset` 后纪元 + 1，旧纪元的推送与游标分别返回 `SYNC_EPOCH_STALE` 与 `SYNC_CURSOR_INVALID`。
- [R28] 服务端存储检查：数据库与对象存储中无可解析的公式文本（注入已知明文后扫描零命中）。
- [R28] 账户删除：认证时间超过 300 s 被拒；删除后令牌失效、数据查询为空、对象存储无该账户前缀；费用墓碑与安全日志按例外保留。
- [R26] 未注册（无令牌）请求一律 401 `AUTH_TOKEN_INVALID`；[R18] 用 A 的令牌读取 B 的 `snapshot_id`、`deletion_id` 返回 404 `SYNC_NOT_FOUND`，不存在的 ID 返回同一响应体（除 trace）；无已提交快照时 `snapshots/latest` 返回 404 `SYNC_NOT_FOUND`。
- [R28] 入站校验：push 请求以 `contracts/vectors/envelope-v2.json` 中 `group=invalid` 的用例（按文件顺序）逐个替换批内第 2 条，返回 400 `SYNC_ENVELOPE_INVALID` 且 `args.field` 与向量的 `expect.field` 一致、整批不写入（数据库 last_seq 不变）；`group=too_large` 的 `too_large_ciphertext` 返回 413 `SYNC_PAYLOAD_TOO_LARGE`、`group=hash_mismatch` 的 `hash_mismatch` 返回 400 `SYNC_HASH_MISMATCH`（文件结构与分组见 CORE-68 测试方案）；push/pull 响应体可由 CORE-68 PushResponse/PullResponse 以 deny_unknown_fields 反序列化。
- [R28] 推送结果与批内校验：一批 5 条（含 1 条已存在同哈希、1 条 CONFLICT）时 `results` 长度为 5 且下标与请求一一对应；批内两条 op_id 相同返回 400 `SYNC_ENVELOPE_INVALID`、`args.field = "op_id"` 且不写入；pull 返回的每条 envelope 字节与 push 时 `to_canonical_json` 字节逐字节相等。
- [R28] 拉取参数边界：limit 0/1/200/201、max_bytes 65535/65536/1048576/1048577 按边界截取；Σbody+(n−1) ≤ max_bytes；单条超过 max_bytes 时仍返回该一条；has_more 在恰好取尽时为 false。
- [R28] 纪元参数：`SYNC_EPOCH_STALE` 与纪元不符的 `SYNC_CURSOR_INVALID` 响应 `args.account_epoch` 等于服务端当前纪元（十进制字符串）；游标无法解析时不带该参数。
- [R28] 密钥与版本：`/v1/keys` PUT 后 GET 返回与 PUT 相同字节；wrap_kind 只接受 recovery_code、sync_passphrase，其他值 404 `SYNC_NOT_FOUND`；包装记录解码超过 4 KiB 返回 413 `SYNC_PAYLOAD_TOO_LARGE`；min-version 提升后 `key_version` 低于下限的推送返回 `SYNC_KEY_VERSION_REJECTED`；ciphertext_hash 不符返回 `SYNC_HASH_MISMATCH`。
- [R28] 配额与限流：账户超过 512 MiB 或 1 000 000 条返回 `SYNC_QUOTA_EXCEEDED`；同账户每分钟第 61 次推送返回 429 `AUTH_RATE_LIMITED` 且带 `Retry-After`；快照分片数 n ≤ 255、单片 ≤ 4 MiB，超出返回 `SYNC_PAYLOAD_TOO_LARGE`。
- [R28] 删除状态机与重放：删除请求经各状态推进至 data_deleted，`GET` deletions 返回各状态；data_deleted 时对象存储写入 `deletions/<deletion_id>.json`（字段与卡片一致）；从删除前的数据库备份恢复后运行 `fml-server replay-deletions`，该账户数据再次清空、输出重放条数，重复运行幂等、清单损坏时非零退出。
