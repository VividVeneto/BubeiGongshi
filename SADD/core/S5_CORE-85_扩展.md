### CORE-85 识别历史仓储、加密存储与GC

**目标**：实现CORE-32的HistoryRepo/HistoryFs/op契约与两阶段GC、恢复，不让领域crate反向依赖存储。

**范围**
- 包含：五表仓储、序号/配额/Pin/采纳、会话资产加密、全部持久化recog op、两阶段GC与启动恢复。
- 不包含：纯会话状态/DTO/错误/op协议、Dart解锁器（CORE-32）；云请求（CORE-34，下游说明）；平台真实目录（CORE-04）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-05、CORE-13、CORE-21、CORE-23、CORE-29、CORE-30、CORE-31、CORE-32

**接口契约**

CORE-32定义的HistoryRepo/HistoryFs、op/错误协议为唯一权威，本卡实现不得另定义同名DTO/错误。文件系统实现接收StoreArea.recognition/staging解析后的受控根。

```rust
// crates/fml-store/src/recognition/gc.rs；Store类型仅出现在本存储卡
pub fn gc_plan(store: &Store, now_ms: i64) -> Result<GcPlan, FmlError>;   // keep_last 与 history_disk_cap_mb 读自 recognition_counter  // 阶段一：单写者事务内标记 DELETING、删会话密钥包装、写 cleanup_job
pub fn gc_execute(store: &Store, plan: &GcPlan, fs: &dyn HistoryFs, now_ms: i64) -> Result<GcReport, FmlError>; // 阶段二：幂等删除密文、缩略图、推理缓存、临时副本，置 PURGED 并写 purged_ms = now_ms；随后删除已过 PURGED_RETENTION_MS（7 天）的 Purged 行。时钟只来自调用方传入的 now_ms
pub fn recover_on_start(store: &Store, fs: &dyn HistoryFs, now_ms: i64) -> Result<RecoveryReport, FmlError>; // 清未提交暂存、重试 next_try_ms ≤ now_ms 的 cleanup_job、对账孤儿、expires_ms ≤ now_ms 的 pending_cloud_job → EXPIRED_UNKNOWN
```

- 表（主包外附属：`crates/fml-store/migrations/0085_recognition.sql` 与仓储 `crates/fml-store/src/recognition/`；全部本地，不进 outbox、不导出）：

| 表 | 列 | 说明 |
| --- | --- | --- |
| `recognition_counter` | `id INTEGER PK CHECK (id = 1)`，`next_seq INTEGER NOT NULL`，`history_key_version INTEGER NOT NULL DEFAULT 0`，`history_key_wrapped BLOB NULL`（CORE-04 `SecureKeyValueStore.wrap` 的输出，库内不存明文密钥），`history_key_check BLOB NULL`（CORE-21 `seal_with_rng(rng, history_key, 空明文, aad)` 的 `Sealed::to_bytes`，AAD 的 domain 为 `recognition.keycheck`，用于校验解包结果），`keep_last INTEGER NOT NULL DEFAULT 5 CHECK (keep_last BETWEEN 0 AND 100)`，`history_disk_cap_mb INTEGER NOT NULL DEFAULT 200 CHECK (history_disk_cap_mb BETWEEN 50 AND 2000)` | 每个档案库一行，即每（设备，账户） |
| `recognition_session` | `id TEXT PK`，`seq INTEGER UNIQUE NOT NULL`，`state`，`source`，`mode`，`backend_id`，`model_version`，`pinned INTEGER`，`adopted_revision TEXT NULL`，`quality_json TEXT NULL`，`result_sealed BLOB NULL`（候选与校正，用会话密钥加密），`error_code TEXT NULL`，`session_key_wrap BLOB NULL`（CORE-21 seal_with_rng(rng,history_key,SessionKey,aad) 的 Sealed::to_bytes，不是 WrapRecord；表约束 `CHECK (state IN ('Deleting','Purged') OR session_key_wrap IS NOT NULL)`，阶段一进入 Deleting 的同一事务置 NULL），`created_ms INTEGER`，`finished_ms INTEGER NULL`，`purged_ms INTEGER NULL`（进入 Purged 的时刻，其余状态为 NULL；`CHECK ((state = 'Purged') = (purged_ms IS NOT NULL))`） | 索引 `(state, seq)` |
| `recognition_asset` | `session_id TEXT`，`kind TEXT`，`sha256 BLOB`，`bytes INTEGER`；PK `(session_id, kind)` | 文件内容在 `HistoryFs` |
| `cleanup_job` | `id INTEGER PK`，`session_id TEXT`，`attempts INTEGER`，`next_try_ms INTEGER`，`last_error TEXT NULL` | 阶段二待办 |
| `pending_cloud_job` | `session_id TEXT PK`，`job_id TEXT`，`image_hash BLOB`，`submitted_ms INTEGER`，`expires_ms INTEGER` | 24 h 过期 |
- Deleting 与 Purged 的数据（ADR-V5-42）：阶段一（`gc_plan`，单写者事务）把会话置 `Deleting`，同事务将 `session_key_wrap`、`result_sealed`、`quality_json` 置 NULL（密文此后不可解），删除该会话的 `pending_cloud_job` 行，并写 `cleanup_job`；阶段二（`gc_execute`）幂等删除文件、删除其 `recognition_asset` 行后置 `Purged`。`Purged` 行**保留 7 天**（`PURGED_RETENTION_MS = 7 × 86 400 000`，常量不可配置，2026-10-20 负责人确认）：保留 `id、seq、state、source、mode、backend_id、model_version、pinned、adopted_revision、error_code、created_ms、finished_ms、purged_ms`，这些元数据不含图片、候选与密钥。`gc_execute` 在阶段二后删除满足 `purged_ms + PURGED_RETENTION_MS ≤ now_ms` 的 Purged 行；`seq` 由 `recognition_counter.next_seq` 单调分配，删行不会使序号回退或复用。行被删后，公式来源按“会话不存在”同样显示“识别图片已清理”。`recog.session.get` 对 `Purged` 或已删除的会话返回 `RECOG_SESSION_NOT_FOUND`；`recog.history.list` 不列 `Deleting/Purged`（采纳关联只读 `adopted_revision` 与 `state`）。`rotate_commit(clear = true)` 对全部会话走同一阶段一。

- 计数单位：一次识别会话 = 一张图片或一块墨迹画布（含其中所有公式区域）；一次导入 10 张图片 = 10 个会话；重试复用原会话，“再次识别”新建会话；作答模式同样计数；空导入与导入前取消不计。终态 SUCCEEDED、FAILED、CANCELLED、EXPIRED_UNKNOWN 都计入。按开始序号排序，不按完成时间。
- 保留规则：在终态会话中保留序号最大的 `keep_last` 个普通会话（默认 5，范围 0–100）；Pinned 与 Adopted 会话不受次数 GC；超出 `history_disk_cap_mb`（默认 200 MB，可调）时先清缓存与暂存，再按序号从旧到新清普通会话。`keep_last = 0` 表示识别完成后立即清空未采纳历史（结果只在内存中的确认页），已入库公式不受影响。
- 保留内容：用户确认的实际输入图（降采样图；开启“保存原图”时另存原图，默认关闭）、实际上传图（按哈希去重）、候选与校正、诊断、识别来源、质量分、时间、后端与模型版本、与已入库公式的溯源关联。导入的全尺寸原始副本在会话结束后删除。
- 触发 GC：会话进入终态、调小 `keep_last`、启动恢复、存储紧张、账户清理。
写资产文件时空间不足返回 CORE-13 定义的 `STORE_DISK_FULL`（不在本卡重复登记）。
- 每个会话使用独立随机会话密钥，由 `RecognitionHistoryKey` 包装；元数据与密文分开存储；删除会话时删除密文、缩略图、缓存、记录与被包装的会话密钥。
- 阶段二失败保留 `cleanup_job`，`attempts + 1` 并按 CORE-32 退避公式设 `next_try_ms`，启动时与每次 `recog.gc` 重试到期项；只按受控目录与文件 ID 对账孤儿文件，不扫描用户源目录，不跟随符号链接或重解析点。
- 暂存区：未提交云端的暂存在崩溃后启动时清理；已提交的保留到终态或 24 h；暂存运行期 TTL ≤ 1 h。
- 同一账户最多一个活动识别任务（活动 = Running 或 Authorized，判定与 seq 分配在 `start` 的同一写事务）；用户单条删除 `delete` 在一个写事务内对该会话执行与 `gc_plan` 相同的阶段一；`pending_cloud_job` 不受 N 限制，24 h 后过期为 EXPIRED_UNKNOWN。
- 被引用（Adopted）的会话不受次数 GC；被一键清空或用户手动删除后，公式来源显示“识别图片已清理”。V1 不提供“另存为公式附件”（需要长期保留时用 Pin）。
- 历史不同步；GC 保证逻辑不可访问并尽力物理删除，界面披露闪存擦除的局限。

**实现约束**
- 唯一实现位置fml-store/src/recognition/，通过CORE-32 trait暴露；fml-recognize不依赖本卡/crate。构造时注入Box<dyn SecureRandom + Send>与HistoryFs/受控目录，不在领域crate取时钟/随机/路径数据。
- CORE-32规定的SessionKey、AAD、history_key_wrapped/key_check、pending旋转以及profile scope规则逐项实现；HistoryKeyUnlocker仍由32提供；操作错误复用32唯一定义，不双登记。
- 全部表本地、不进outbox/备份；0085_recognition.sql数据迁移归本卡（V1 发布前迁移序号取归属卡编号，CORE-13）；Store关闭清零，密钥不上传，清理实现不扫描用户目录。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-85_TEST.md](../Test/core/S5_CORE-85_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约570行；主包`crates/fml-store/src/recognition/`，附属`crates/fml-ffi/src/ops/recognition_history.rs`持久化op处理/登记。分阶段：① 仓储/加密存储/接入（含单条删除）395行；② GC/启动恢复175行；每阶段通过内存HistoryFs与故障注入独立构建验收，不冒称尚未实现的恢复通过。DDL、数据与自测不计。
