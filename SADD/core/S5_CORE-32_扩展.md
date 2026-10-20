### CORE-32 识别会话状态机与历史 GC

**目标**：持久化识别会话、按“保留最近 N 次识别”规则可靠地清理历史，并保证中断、崩溃与云端未知状态下不丢结果、不残留数据、不重复付费。

**范围**
- 包含：识别会话状态机、序号与计数、`recognition_counter`、`recognition_session`、`recognition_asset`、`cleanup_job`、`pending_cloud_job` 五张表与仓储、会话文件加密存储、两阶段 GC、磁盘配额、Pin、采纳关联与“识别图片已清理”提示、历史密钥的平台包装与装入（含 Dart 附属 `HistoryKeyUnlocker`）、一键清空、启动恢复、FFI op。
- 不包含：云端调用（CORE-34）；界面（CORE-40）；平台目录（AND-06、WIN-07 经 CORE-04 `LocalFileStore` 提供 `StoreArea.recognition` 与 `StoreArea.staging` 的实际位置）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-13、CORE-21、CORE-23、CORE-29、CORE-30、CORE-31

**接口契约**

```text
IMPORTED → PREVIEW → [AUTHORIZED（仅云端）] → RUNNING → SUCCEEDED | FAILED | CANCELLED | UNKNOWN_REMOTE
UNKNOWN_REMOTE → SUCCEEDED | FAILED | CANCELLED | EXPIRED_UNKNOWN（“可能已计费”）
终态 → RETAINED（保留）| DELETING → PURGED
```

```rust
// crates/fml-recognize/src/session.rs
pub struct RecognitionSession { pub id: Uuid, pub seq: u64 /* 每 (设备, 账户) 单调递增，开始时分配 */, pub state: SessionState,
                                pub source: InputSource /* Ink | Camera | Gallery | File | Clipboard | DragDrop */,
                                pub backend_id: String, pub model_version: String, pub mode: RecognitionMode,
                                pub pinned: bool, pub adopted_revision: Option<RevisionId>, pub quality: Option<QualityReport>, pub created_ms: i64 }
// HistoryRepo 的实现在构造时注入 `Box<dyn SecureRandom + Send>`（生产为 CORE-23 OsRandom，测试为 FixedRandom）；start 生成会话密钥、begin_rotation 生成历史密钥时使用，trait 方法签名不增加 rng 参数（ADR-V5-41）
pub trait HistoryRepo {
    fn start(&self, source: InputSource, mode: RecognitionMode) -> Result<RecognitionSession, FmlError>;
    fn transition(&self, id: Uuid, to: SessionState, payload: TransitionPayload) -> Result<(), FmlError>;
    fn record_pending_cloud(&self, id: Uuid, job_id: &str, image_hash: [u8; 32]) -> Result<(), FmlError>;
    fn pending_cloud_jobs(&self) -> Result<Vec<PendingCloudJob>, FmlError>;   // 启动时由 CORE-34 查询状态，不重新提交
    fn pin(&self, id: Uuid, on: bool) -> Result<(), FmlError>;
    fn adopt(&self, id: Uuid, rev: RevisionId) -> Result<(), FmlError>;      // 公式库中保存文本 + 来源会话 ID
    fn list(&self, page: u32) -> Result<Page<SessionSummary>, FmlError>;
    fn key_status(&self) -> Result<HistoryKeyStatus, FmlError>;              // 不返回明文密钥
    fn provide_key(&self, version: u32, key: Zeroizing<[u8; 32]>) -> Result<(), FmlError>; // 用 key_check 校验后装入本 Store 实例内存
    fn begin_rotation(&self) -> Result<(u32, Zeroizing<[u8; 32]>), FmlError>; // 用构造时注入的 SecureRandom 调 CORE-21 random_key 生成 version + 1 的待提交密钥，只在内存；失败 → CRYPTO_RNG_FAILED
    fn commit_rotation(&self, version: u32, wrapped: &[u8], clear: bool) -> Result<(), FmlError>; // 单写者事务；clear = true 即一键清空
}
pub struct HistoryKeyStatus { pub version: u32 /* 0 = 尚未建立 */, pub wrapped: Option<Vec<u8>>, pub loaded: bool }
pub fn gc_plan(store: &Store, now_ms: i64) -> Result<GcPlan, FmlError>;   // keep_last 与 history_disk_cap_mb 读自 recognition_counter  // 阶段一：单写者事务内标记 DELETING、删会话密钥包装、写 cleanup_job
pub fn gc_execute(plan: &GcPlan, fs: &dyn HistoryFs, now_ms: i64) -> Result<GcReport, FmlError>; // 阶段二：幂等删除密文、缩略图、推理缓存、临时副本，置 PURGED 并写 purged_ms = now_ms；随后删除已过 PURGED_RETENTION_MS（7 天）的 Purged 行。时钟只来自调用方传入的 now_ms
pub fn recover_on_start(store: &Store, fs: &dyn HistoryFs) -> Result<RecoveryReport, FmlError>;
pub enum SessionState { Imported, Preview, Authorized, Running, Succeeded, Failed, Cancelled, UnknownRemote, ExpiredUnknown, Deleting, Purged }
pub enum InputSource { Ink, Camera, Gallery, File, Clipboard, DragDrop }
pub enum AssetKind { Confirmed /* 确认输入图（降采样） */, Original /* 仅“保存原图”开启时 */, Upload, Thumbnail, Ink }
pub struct TransitionPayload { pub assets: Vec<(AssetKind, PathBuf /* 暂存区明文文件，写入后删除 */)>, pub candidates: Option<Vec<Candidate>>,
                               pub error_code: Option<String>, pub quality: Option<QualityReport>, pub backend_id: Option<String>, pub model_version: Option<String> }
pub struct PendingCloudJob { pub session_id: Uuid, pub job_id: String, pub image_hash: [u8; 32], pub submitted_ms: i64, pub expires_ms: i64 }
pub struct SessionSummary { pub id: Uuid, pub seq: u64, pub state: SessionState, pub source: InputSource, pub backend_id: String,
                            pub created_ms: i64, pub pinned: bool, pub adopted: bool, pub has_images: bool }
pub struct GcPlan { pub sessions: Vec<Uuid>, pub job_ids: Vec<i64> }
pub struct GcReport { pub purged: u32, pub retry_later: u32, pub bytes_freed: u64 }
pub struct RecoveryReport { pub staging_cleared: u32, pub jobs_resumed: u32, pub orphans_removed: u32, pub pending_cloud: u32 }
pub trait HistoryFs {                       // 平台目录由 StoreArea.recognition 提供；文件名只用 <session_id>/<asset_kind>.bin
    fn write(&self, session: Uuid, kind: AssetKind, sealed: &[u8]) -> Result<u64, FmlError>;
    fn read(&self, session: Uuid, kind: AssetKind) -> Result<Vec<u8>, FmlError>;
    fn remove_session(&self, session: Uuid) -> Result<(), FmlError>;   // 不存在视为成功；不跟随符号链接或重解析点
    fn list_sessions(&self) -> Result<Vec<Uuid>, FmlError>;             // 只列受控目录下名称为 UUID 的子目录
    fn used_bytes(&self) -> Result<u64, FmlError>;
}
```

- 表（主包外附属：`crates/fml-store/migrations/0032_recognition.sql` 与仓储 `crates/fml-store/src/recognition/`；全部本地，不进 outbox、不导出）：

| 表 | 列 | 说明 |
| --- | --- | --- |
| `recognition_counter` | `id INTEGER PK CHECK (id = 1)`，`next_seq INTEGER NOT NULL`，`history_key_version INTEGER NOT NULL DEFAULT 0`，`history_key_wrapped BLOB NULL`（CORE-04 `SecureKeyValueStore.wrap` 的输出，库内不存明文密钥），`history_key_check BLOB NULL`（CORE-21 `seal_with_rng(rng, history_key, 空明文, aad)` 的 `Sealed::to_bytes`，AAD 的 domain 为 `recognition.keycheck`，用于校验解包结果），`keep_last INTEGER NOT NULL DEFAULT 5 CHECK (keep_last BETWEEN 0 AND 100)`，`history_disk_cap_mb INTEGER NOT NULL DEFAULT 200 CHECK (history_disk_cap_mb BETWEEN 50 AND 2000)` | 每个档案库一行，即每（设备，账户） |
| `recognition_session` | `id TEXT PK`，`seq INTEGER UNIQUE NOT NULL`，`state`，`source`，`mode`，`backend_id`，`model_version`，`pinned INTEGER`，`adopted_revision TEXT NULL`，`quality_json TEXT NULL`，`result_sealed BLOB NULL`（候选与校正，用会话密钥加密），`error_code TEXT NULL`，`session_key_wrap BLOB NULL`（CORE-21 seal_with_rng(rng,history_key,SessionKey,aad) 的 Sealed::to_bytes，不是 WrapRecord；表约束 `CHECK (state IN ('Deleting','Purged') OR session_key_wrap IS NOT NULL)`，阶段一进入 Deleting 的同一事务置 NULL），`created_ms INTEGER`，`finished_ms INTEGER NULL`，`purged_ms INTEGER NULL`（进入 Purged 的时刻，其余状态为 NULL；`CHECK ((state = 'Purged') = (purged_ms IS NOT NULL))`） | 索引 `(state, seq)` |
| `recognition_asset` | `session_id TEXT`，`kind TEXT`，`sha256 BLOB`，`bytes INTEGER`；PK `(session_id, kind)` | 文件内容在 `HistoryFs` |
| `cleanup_job` | `id INTEGER PK`，`session_id TEXT`，`attempts INTEGER`，`next_try_ms INTEGER`，`last_error TEXT NULL` | 阶段二待办 |
| `pending_cloud_job` | `session_id TEXT PK`，`job_id TEXT`，`image_hash BLOB`，`submitted_ms INTEGER`，`expires_ms INTEGER` | 24 h 过期 |

- 状态转换合法表：`Imported → Preview | Cancelled`；`Preview → Authorized | Running | Cancelled`（`Authorized` 仅当 `backend_id` 为 networked）；`Authorized → Running | Cancelled`；`Running → Succeeded | Failed | Cancelled | UnknownRemote`；`UnknownRemote → Succeeded | Failed | Cancelled | ExpiredUnknown`；终态 → `Deleting`（仅 GC 或清空）；`Deleting → Purged`。其余转换 → `RECOG_TRANSITION_INVALID`。
- Deleting 与 Purged 的数据（ADR-V5-42）：阶段一（`gc_plan`，单写者事务）把会话置 `Deleting`，同事务将 `session_key_wrap`、`result_sealed`、`quality_json` 置 NULL（密文此后不可解），删除该会话的 `pending_cloud_job` 行，并写 `cleanup_job`；阶段二（`gc_execute`）幂等删除文件、删除其 `recognition_asset` 行后置 `Purged`。`Purged` 行**保留 7 天**（`PURGED_RETENTION_MS = 7 × 86 400 000`，常量不可配置，2026-10-20 负责人确认）：保留 `id、seq、state、source、mode、backend_id、model_version、pinned、adopted_revision、error_code、created_ms、finished_ms、purged_ms`，这些元数据不含图片、候选与密钥。`gc_execute` 在阶段二后删除满足 `purged_ms + PURGED_RETENTION_MS ≤ now_ms` 的 Purged 行；`seq` 由 `recognition_counter.next_seq` 单调分配，删行不会使序号回退或复用。行被删后，公式来源按“会话不存在”同样显示“识别图片已清理”。`recog.session.get` 对 `Purged` 或已删除的会话返回 `RECOG_SESSION_NOT_FOUND`；`recog.history.list` 不列 `Deleting/Purged`（采纳关联只读 `adopted_revision` 与 `state`）。`rotate_commit(clear = true)` 对全部会话走同一阶段一。

- 计数单位：一次识别会话 = 一张图片或一块墨迹画布（含其中所有公式区域）；一次导入 10 张图片 = 10 个会话；重试复用原会话，“再次识别”新建会话；作答模式同样计数；空导入与导入前取消不计。终态 SUCCEEDED、FAILED、CANCELLED、EXPIRED_UNKNOWN 都计入。按开始序号排序，不按完成时间。
- 保留规则：在终态会话中保留序号最大的 `keep_last` 个普通会话（默认 5，范围 0–100）；Pinned 与 Adopted 会话不受次数 GC；超出 `history_disk_cap_mb`（默认 200 MB，可调）时先清缓存与暂存，再按序号从旧到新清普通会话。`keep_last = 0` 表示识别完成后立即清空未采纳历史（结果只在内存中的确认页），已入库公式不受影响。
- 保留内容：用户确认的实际输入图（降采样图；开启“保存原图”时另存原图，默认关闭）、实际上传图（按哈希去重）、候选与校正、诊断、识别来源、质量分、时间、后端与模型版本、与已入库公式的溯源关联。导入的全尺寸原始副本在会话结束后删除。
- 触发 GC：会话进入终态、调小 `keep_last`、启动恢复、存储紧张、账户清理。
- FFI op：`recog.session.start` `{ source, mode }` → `{ session }`；`recog.session.transition` `{ id, to, payload }` → `{}`；`recog.session.get` `{ id }` → `{ session, candidates?, assets }`（图片以解密到暂存区的路径返回，界面用完删除）；`recog.pending_cloud.record / list`；`recog.pin`、`recog.adopt`、`recog.history.list` `{ page }`、`recog.key.status` `{}` → `{ key_version, wrapped?, loaded }`、`recog.key.provide` `{ key_version, history_key }` → `{}`、`recog.key.rotate_begin` `{}` → `{ key_version, history_key }`、`recog.key.rotate_commit` `{ key_version, wrapped, clear }` → `{}`（一键清空即 `clear = true`；`history_key` 只在 FFI 缓冲区中传递，Rust 侧放入 `Zeroizing`，档案关闭时随 Store 清零）、`recog.gc` `{ now_ms }` → `{ purged, retry_later, bytes_freed }`（长任务，`gc_plan` + `gc_execute`；`now_ms` 由 Dart 调用方传入）、`recog.recover`（长任务，启动时调用）；`recog.settings.get` `{}` → `{ keep_last, history_disk_cap_mb }`；`recog.settings.set` `{ keep_last?, history_disk_cap_mb? }` → `{}`（`keep_last` 越界 → `RECOG_KEEP_LAST_OUT_OF_RANGE`；`history_disk_cap_mb` 取值 50–2000，越界同样拒绝；值存 `recognition_counter`，设置变小后立即触发一次 `recog.gc`）。
- 错误码：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `RECOG_SESSION_NOT_FOUND` | error | 否 | id 不存在、已 `Purged`，或 `Purged` 行已满 7 天被删除 |
| `RECOG_ACTIVE_TASK_EXISTS` | warning | 是 | 已有会话处于 `Running` 或 `Authorized` 时 `start` 新会话（`UnknownRemote` 不占用） |
| `RECOG_TRANSITION_INVALID` | error | 否 | 不在合法转换表中的转换 |
| `RECOG_KEEP_LAST_OUT_OF_RANGE` | error | 否 | 设置 `keep_last` 不在 0–100，或 `history_disk_cap_mb` 不在 50–2000 |
| `RECOG_QUOTA_EXCEEDED` | warning | 否 | GC 后 `used_bytes` 仍超过 `history_disk_cap_mb`（只剩 Pinned/Adopted），新会话仍可进行但提示用户取消固定 |
| `RECOG_IMAGE_LOST` | warning | 否 | 读取的资产文件不存在或解密失败（界面显示“识别图片已清理”） |
| `RECOG_HISTORY_KEY_UNAVAILABLE` | error | 是 | 本 Store 尚未装入历史密钥时调用需要它的 op（`session.start / transition / get`、`history.list`、`gc`、`recover`）；`provide` 的版本与库内不符或 key_check 校验失败；`rotate_commit` 没有对应的待提交密钥或版本不是当前值 + 1 |

写资产文件时空间不足返回 CORE-13 定义的 `STORE_DISK_FULL`（不在本卡重复登记）。

历史密钥唯一存放规则：`RecognitionHistoryKey` 由 `begin_rotation` 生成，经 CORE-04 `SecureKeyValueStore.wrap` 用档案已有别名 `fml.<profile_id>.db`（CORE-23）包装后存入 `recognition_counter.history_key_wrapped`；不新建平台别名（与 AND-06、WIN-07 的别名清单一致）。档案打开后由 Dart 附属 `HistoryKeyUnlocker` 解包并经 `recog.key.provide` 装入当前 Store 实例的 `Zeroizing` 内存；档案锁定或关闭（CORE-23 `close_profile`）时随 Store 清零。数据库只存包装值、`key_check` 与版本。SessionKey 每会话调用 CORE-21 random_key 独立生成，seal 的 AAD 为 aad_cbor(domain="recognition.session",account_id=None,entity_type="session",entity_id=session_id小写UUID,key_version=history_key_version,format_version=1)，不从 AccountDataKey/KeyPurpose 派生，不定义新 WrapKind。会话资产/候选再用 SessionKey 分域 seal，id、kind必入AAD，防跨会话/资产替换。

```dart
// app/lib/recognition/history_key.dart（本卡附属；CORE-40 安装点构造并登记到 ctx.features，CORE-47、CORE-50 从 features 取用）
final class HistoryKeyUnlocker {
  HistoryKeyUnlocker(CoreBinding core, SecureKeyValueStore keys, String Function() profileId); // core必须为该profileId对应的scopedTo视图（CORE-03），调用前捕获同一会话
  Future<bool> ensure();   // 幂等；返回 true 表示因平台密钥失效已清空历史，调用方提示一次
  Future<void> clearAll(); // 一键清空：轮换并 clear = true
}
```

`ensure`：`recog.key.status` 已 `loaded` 直接返回 false；有 `wrapped` 则 `unwrap(fml.<profile_id>.db, wrapped)` 后 `provide`；`version = 0`（新档案）则轮换且 `clear = false`；`unwrap` 抛 `PLATFORM_KEY_UNAVAILABLE` 或 `provide` 返回 `RECOG_HISTORY_KEY_UNAVAILABLE`（库与密钥不匹配，如快照回滚）时轮换且 `clear = true` 并返回 true。轮换 = `rotate_begin` → `wrap` → `rotate_commit`；`rotate_commit` 在一个事务内更新包装值、`key_check` 与版本，`clear = true` 时同一事务把全部会话置 `Deleting`、删除会话密钥包装并写 `cleanup_job`，提交后新密钥生效。提交前崩溃：库内仍是旧版本，待提交密钥随进程消失；提交后崩溃：旧会话包装已删除，阶段二按 `cleanup_job` 补删文件。旧密钥只存在于被覆盖的包装值中，`recognition` 库开启 `secure_delete` 并在提交后截断 WAL。需要历史密钥的调用方在档案解锁后首次调用前 `ensure()`，收到 `RECOG_HISTORY_KEY_UNAVAILABLE` 时 `ensure()` 后重试一次。GC 删除单会话只删其包装，历史密钥与包装值都不上传、不导出。

`Page<T>`引用CORE-05。recog.pending_cloud.record body=`{id,job_id,image_hash}`（image_hash为64hex），ok=`{}`；list body=`{}`，ok=`{jobs:[PendingCloudJob]}`；均call。PendingCloudJob字段session_id/job_id/image_hash/submitted_ms/expires_ms对应本卡表；不存在id复用RECOG_SESSION_NOT_FOUND。

本卡持久化的recog.session.*/history.*/settings.*/key.*/pending_cloud.*/recover/gc均为profile scope，core视图来自CORE-65（下游说明，非契约）的已打开会话，使用CORE-03信封profile_handle；临时推理recog.run/backends/register_remote是CORE-29的none scope，不借全局当前档案。key.provide只装入该handle的Store，关闭清零；HistoryKeyUnlocker.ensure前后核对profileId未切换，切换则丢弃解包结果并清零，不向新库提供旧密钥。

产品约束追踪：见README §6 Q4；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 每个会话使用独立随机会话密钥，由 `RecognitionHistoryKey` 包装；元数据与密文分开存储；删除会话时删除密文、缩略图、缓存、记录与被包装的会话密钥。
- 阶段二失败保留 `cleanup_job`，指数退避，启动时重试；只按受控目录与文件 ID 对账孤儿文件，不扫描用户源目录，不跟随符号链接或重解析点。
- 暂存区：未提交云端的暂存在崩溃后启动时清理；已提交的保留到终态或 24 h；暂存运行期 TTL ≤ 1 h。
- 同一账户最多一个活动识别任务；`pending_cloud_job` 不受 N 限制，24 h 后过期为 EXPIRED_UNKNOWN。
- 被引用（Adopted）的会话不受次数 GC；被一键清空或用户手动删除后，公式来源显示“识别图片已清理”。V1 不提供“另存为公式附件”（需要长期保留时用 Pin）。
- 历史不同步；GC 保证逻辑不可访问并尽力物理删除，界面披露闪存擦除的局限。

**验收标准**
- [R33] GC 用例：`keep_last` = 0、1、5、100 时连续完成 N + 3 次识别，保留集合等于序号最大的 N 个普通会话 + 全部 Pinned/Adopted 会话。
- [R34] 设置 −1 与 101 被界面、FFI 与 `recognition_counter` 的 CHECK 约束三处拒绝（`keep_last` 0–100，`history_disk_cap_mb` 50–2000，越界值直接 SQL 写入亦失败）；0 与 100 可设置。
- [R35] 新建账户的默认 `keep_last` 为 5。
- [R36] 保留的会话可查看确认图、上传图、候选与校正结果；被清理的会话所有文件与密钥均不存在（磁盘扫描与数据库检查）。
- [R36] Purged 数据库检查（真实 SQLite 事务）：阶段一后该会话 `state = Deleting` 且 `session_key_wrap`、`result_sealed`、`quality_json` 为 NULL、`pending_cloud_job` 无该行；阶段二后 `state = Purged`、`purged_ms = now_ms`、`recognition_asset` 无该行、元数据保留；`now_ms` 推进到 `purged_ms + 7 天 − 1 ms` 时行仍在、`+ 0 ms` 时被删，删后新建会话的 `seq` 仍大于被删行的 `seq`；非 `Deleting/Purged` 行写入 NULL 包装被 CHECK 拒绝；`rotate_commit(clear = true)` 后全部既有会话同样如此。
- [R36] 故障注入：阶段一提交前、后及阶段二每步之间杀进程，重启后会话要么完整保留要么按阶段继续，无“有包装无密文/有密文无包装”的中间态可读。
- [R33] 故障注入：GC 各步骤之间杀进程、文件被占用、磁盘满，重启后最终一致且无孤儿文件；调小 N 与识别完成并发时结果正确。
- [R40] 已提交云端的会话在进程重启后保持 RUNNING/UNKNOWN_REMOTE，经状态查询收敛，不重新提交（与 CORE-34 联测）。
- [R27] 一键清空后历史目录为空、历史密钥已轮换、WAL 中无残留记录。

- [R27][R35] 明文 SQL 扫描无 32 字节历史密钥（只有平台包装值与 `key_check`）；锁定时无法读历史，解锁后 `ensure()` 装入即可读，未装入时 `recog.history.list` 返回 `RECOG_HISTORY_KEY_UNAVAILABLE`；将 A 会话包装换给 B 时 AAD 失败；Fake `SecureKeyValueStore` 注入别名失效时 `ensure()` 返回 true 且旧会话全部进入 `Deleting`；轮换在 `wrap` 后、`rotate_commit` 前与提交后各杀一次进程，重启后遵从已提交版本且旧会话不可恢复。

**规模**：约 500 行；主包 `crates/fml-recognize/`（`src/session.rs`、`src/gc.rs`，约 290 行）；附属：`crates/fml-store/src/recognition/` 与 `migrations/0032_recognition.sql`（约 160 行，归属本卡的表），`app/lib/recognition/history_key.dart`（约 50 行）。

