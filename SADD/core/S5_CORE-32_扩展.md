### CORE-32 识别会话模型与历史密钥解锁

**目标**：定义不依赖Store/I/O的识别会话状态、HistoryRepo/HistoryFs与op协议，并实现Dart历史密钥解锁；持久化与GC由CORE-85实现。

**范围**
- 包含：纯会话状态与转换校验、HistoryRepo/HistoryFs接口和DTO/op协议、历史密钥解锁器；本卡不实现文件/数据库访问。
- 不包含：云端调用（CORE-34）；界面（CORE-40）；平台目录（AND-06、WIN-07 经 CORE-04 `LocalFileStore` 提供 `StoreArea.recognition` 与 `StoreArea.staging` 的实际位置）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-05、CORE-21、CORE-23、CORE-29、CORE-30、CORE-31、CORE-65

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
pub fn validate_transition(from: SessionState, to: SessionState, networked: bool) -> Result<(), FmlError>; // 只检验下述合法状态表，无I/O
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


- 状态转换合法表：`Imported → Preview | Cancelled`；`Preview → Authorized | Running | Cancelled`（`Authorized` 仅当 `backend_id` 为 networked）；`Authorized → Running | Cancelled`；`Running → Succeeded | Failed | Cancelled | UnknownRemote`；`UnknownRemote → Succeeded | Failed | Cancelled | ExpiredUnknown`；终态 → `Deleting`（仅 GC 或清空）；`Deleting → Purged`。其余转换 → `RECOG_TRANSITION_INVALID`。
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


历史密钥唯一存放规则：`RecognitionHistoryKey` 由 `begin_rotation` 生成，经 CORE-04 `SecureKeyValueStore.wrap` 用档案已有别名 `fml.<profile_id>.db`（CORE-23）包装后存入 `recognition_counter.history_key_wrapped`；不新建平台别名（与 AND-06、WIN-07 的别名清单一致）。档案打开后由 Dart 附属 `HistoryKeyUnlocker` 解包并经 `recog.key.provide` 装入当前 Store 实例的 `Zeroizing` 内存；档案锁定或关闭（CORE-23 `close_profile`）时随 Store 清零。数据库只存包装值、`key_check` 与版本。SessionKey 每会话调用 CORE-21 random_key 独立生成，seal 的 AAD 为 aad_cbor(domain="recognition.session",account_id=None,entity_type="session",entity_id=session_id小写UUID,key_version=history_key_version,format_version=1)，不从 AccountDataKey/KeyPurpose 派生，不定义新 WrapKind。会话资产/候选再用 SessionKey 分域 seal，id、kind必入AAD，防跨会话/资产替换。

```dart
// app/lib/recognition/history_key.dart（本卡附属；CORE-40 安装点构造并登记到 ctx.features，CORE-47、CORE-50 从 features 取用）
final class HistoryKeyUnlocker {
  HistoryKeyUnlocker(ProfileSessionSource sessions, SecureKeyValueStore keys); // CORE-65 仅供 Dart 附属层，不引入 Rust 依赖
  Future<bool> ensure();   // 幂等；返回 true 表示因平台密钥失效已清空历史，调用方提示一次
  Future<void> clearAll(); // 一键清空：轮换并 clear = true
  Future<void> stopAndDrain(ProfileSession session); // 取消待办并排空已开始的密钥操作，所有字节 finally 清零
}
```

`ensure`：`recog.key.status` 已 `loaded` 直接返回 false；有 `wrapped` 则 `unwrap(fml.<profile_id>.db, wrapped)` 后 `provide`；`version = 0`（新档案）则轮换且 `clear = false`；`unwrap` 抛 `PLATFORM_KEY_UNAVAILABLE` 或 `provide` 返回 `RECOG_HISTORY_KEY_UNAVAILABLE`（库与密钥不匹配，如快照回滚）时轮换且 `clear = true` 并返回 true。轮换 = `rotate_begin` → `wrap` → `rotate_commit`；`rotate_commit` 在一个事务内更新包装值、`key_check` 与版本，`clear = true` 时同一事务把全部会话置 `Deleting`、删除会话密钥包装并写 `cleanup_job`，提交后新密钥生效。提交前崩溃：库内仍是旧版本，待提交密钥随进程消失；提交后崩溃：旧会话包装已删除，阶段二按 `cleanup_job` 补删文件。旧密钥只存在于被覆盖的包装值中，`recognition` 库开启 `secure_delete` 并在提交后截断 WAL。需要历史密钥的调用方在档案解锁后首次调用前 `ensure()`，收到 `RECOG_HISTORY_KEY_UNAVAILABLE` 时 `ensure()` 后重试一次。GC 删除单会话只删其包装，历史密钥与包装值都不上传、不导出。

解锁器每次 ensure/clearAll 开始捕获 sessions.current 的 identity、handle、profileId 与 scoped core；null 不调用 FFI/平台端口，回账户入口。每次 status/unwrap/begin/wrap/provide/commit 的 await 后、下一次调用前核对同一世代；不符合则丢弃结果清零，不重定向新库。相同 profileId 的新 handle 也视为过期。ensure 按 handle singleflight；ensure 与 clearAll 共用该 handle 串行队列（clearAll 排在正在进行的 ensure 后，之后的 ensure 排在 clearAll 后），避免并发 rotate_begin 或 provide 旧版本。close 时移除待办，等待已执行操作返回并清零，不再启动后续 provide/commit；已提交的事务只等待结果，不伪造回滚。安装点以唯一 recognition.history_keys 登记 beforeClose，并在真实排空后释放订阅；失败传播，不提前关闭 Store。

重试只限同一仍 current 的 session，RECOG_HISTORY_KEY_UNAVAILABLE → ensure → 原业务最多一次；世代过期不能作为密钥失效来轮换新档案。所有 unwrap/rotate_begin/FFI 编解码得到的 Uint8List 及副本都在 finally fillRange 清零，wrapped 是密文无需冒称明文；不可变 String 不宣称可擦除。

`Page<T>`引用CORE-05。recog.pending_cloud.record body=`{id,job_id,image_hash}`（image_hash为64hex），ok=`{}`；list body=`{}`，ok=`{jobs:[PendingCloudJob]}`；均call。PendingCloudJob字段session_id/job_id/image_hash/submitted_ms/expires_ms对应本卡表；不存在id复用RECOG_SESSION_NOT_FOUND。

本卡持久化的recog.session.*/history.*/settings.*/key.*/pending_cloud.*/recover/gc均为profile scope，core视图来自CORE-65的已打开会话，使用CORE-03信封profile_handle；临时推理recog.run/backends/register_remote是CORE-29的none scope，不借全局当前档案。key.provide只装入该handle的Store，关闭清零；HistoryKeyUnlocker.ensure前后核对session identity与handle未切换，切换则丢弃解包结果并清零，不向新库提供旧密钥。

产品约束追踪：见README §6 Q4；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- crates/fml-recognize禁止依赖fml-store；HistoryRepo/HistoryFs以trait注入，签名不含Store。GC/恢复free函数与全部数据库/文件实现归CORE-85；原有op名称、scope和payload不变。
- 本卡的HistoryKeyUnlocker仅消费本卡所定义op契约，不依赖CORE-85具体Rust实现；CORE-40组装实际服务，保持32→领域、85→32而不成环。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-32_TEST.md](../Test/core/S5_CORE-32_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约320行；主包`crates/fml-recognize/src/session.rs`纯模型/转换校验，附属`app/lib/recognition/history_key.dart`解锁编排与接入。接口及错误/op协议仍在本卡定义，由CORE-85实现存储；不计其I/O实现、DDL、自测及生成DTO。
