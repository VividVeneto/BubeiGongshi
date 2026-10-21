### CORE-24 游客升级日志与账户密钥

**目标**：把游客本地数据可靠地转为注册账户，或为CORE-83并入已有账户提供日志与密钥步骤，过程可中断恢复且失败时游客数据始终可用。

**范围**
- 包含：升级日志状态机与表、各步幂等实现（纯本地，网络结果由调用方作为输入传入）、升级后首次全量上传的触发标记。
- 不包含：驱动升级的联网协调器与首次全量上传（CORE-99，经 CORE-25 的 `/v1/keys`）；注册用例（CORE-23）；账户界面（CORE-36）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-13、CORE-21、CORE-22、CORE-23

**接口契约**

```rust
// crates/fml-store/src/sync/upgrade.rs
pub enum UpgradeStep { Prepared, IdentityReady, KeyReady, LocalCommitted, Done }
pub enum UpgradeMode { NewAccount, MergeInto }
pub struct UpgradeJournal { pub id: Uuid, pub step: UpgradeStep, pub mode: UpgradeMode, pub target_account: Option<Uuid> /* IdentityReady 后非空 */,
                            pub started_ms: i64, pub updated_ms: i64, pub last_error: Option<String> /* 错误码，不含内容 */ }
pub fn begin(store: &Store, mode: UpgradeMode) -> Result<UpgradeJournal, FmlError>;   // 暂停业务写入（写 op 返回 SYNC_UPGRADE_IN_PROGRESS）
pub enum StepInput {
    Identity { account_id: Uuid },                       // 调用方已完成注册或登录（CORE-23）
    NewKey,                                              // NewAccount：本卡生成 AccountDataKey 与恢复码，返回 KeyOutput 供界面显示与上传
    KeyUploaded { key_version: u32 },                    // 调用方已上传恢复码包装记录且用户已确认保存恢复码
    ExistingKey { account_id: Uuid, records: Vec<WrapRecord>, secret: KeySecret }, // MergeInto：调用方下载的包装记录 + 用户输入，本卡解包
    Commit,                                              // 执行本地提交
}
pub enum KeySecret { RecoveryCode(String), Passphrase(String) }
pub struct KeyOutput { pub recovery_code: RecoveryCode, pub wrap_record: WrapRecord }   // 只返回一次，不落盘恢复码
pub fn import_account_key(store: &Store, account_id: Uuid, records: &[WrapRecord], secret: &KeySecret) -> Result<u32 /* 导入的最高 key_version */, FmlError>;
    // 新设备登录或密钥轮换后：解包全部可解的 key_version 写入 account_key
pub fn rotate_account_key(store: &Store, rng: &mut dyn SecureRandom) -> Result<(u32 /* 新 key_version */, KeyOutput), FmlError>;
    // 设备吊销或怀疑泄露：生成新 AccountDataKey 与新恢复码（旧恢复码对新版本无效）；已设同步密语时须由调用方再次包装
pub fn advance(store: &Store, rng: &mut dyn SecureRandom, j: &mut UpgradeJournal, input: StepInput) -> Result<(UpgradeStep, Option<KeyOutput>), FmlError>;
    // rng 由 FFI 适配传入 CORE-23 的 OsRandom；仅 NewKey 与 rotate_account_key 实际取随机字节，其余步骤不消耗
    // 只做本地工作，每步幂等，可重入；输入与当前步骤不匹配 → SYNC_UPGRADE_STEP_INVALID
pub fn resume_on_start(store: &Store) -> Result<Option<UpgradeJournal>, FmlError>;   // 启动时读取未完成日志，由协调器继续
pub fn abandon(store: &Store, j: &UpgradeJournal) -> Result<(), FmlError>;           // 仅 LocalCommitted 之前允许；恢复游客写入
```

- 表（`crates/fml-store/migrations/0024_upgrade.sql`）：`upgrade_journal`（`id TEXT PK`，`step TEXT NOT NULL`，`mode TEXT NOT NULL`，`target_account TEXT NULL`，`started_ms INTEGER`，`updated_ms INTEGER`，`last_error TEXT NULL`，`registry_pending INTEGER NOT NULL DEFAULT 0`，`target_profile TEXT`；同时至多一行未到 `Done`）、`account_key_wrap`（`key_version INTEGER`，`wrap_kind TEXT`（CORE-21 线上名 `recovery_code` / `sync_passphrase`），`record BLOB NOT NULL`（CORE-21 `WrapRecord` 的 CBOR），`uploaded INTEGER NOT NULL DEFAULT 0`，PK `(key_version, wrap_kind)`）、`account_key`（`key_version INTEGER PK`，`key BLOB NOT NULL`；只存在于 SQLCipher 加密的档案库内，不进 outbox）。
- 步骤语义：

| 步骤 | 完成条件 | 中断后重入 |
| --- | --- | --- |
| Prepared | 日志行写入，业务写入暂停 | 直接进入下一步 |
| IdentityReady | 收到 `Identity` 输入，account_id 写入日志 | 同一 account_id 重复输入无副作用；不同 account_id → `SYNC_UPGRADE_STEP_INVALID` |
| KeyReady | `account_key` 与 `account_key_wrap` 写入（`NewKey`），收到 `KeyUploaded` 后 `uploaded = 1`；MergeInto 收到 `ExistingKey` | 已有 `account_key` 时 `NewKey` 不再生成新密钥，返回 `SYNC_UPGRADE_STEP_INVALID` 由协调器改为补传已存包装记录 |
| LocalCommitted | 只在目标档案库单事务提交 account_state、account_epoch、首次全量 outbox 与 upgrade_journal（含 registry_pending=1、target_profile）；游客 DbKey 保持不变。此事务不写 device_registry.db | 以档案库日志为准，提交后幂等投影 DeviceRegistry，成功后另一个档案事务清 registry_pending；不回滚已提交档案 |
| Done | registry_pending 已清且 DeviceRegistry 与已提交档案一致，日志标记完成，恢复业务写入；返回后由 CORE-23 询问是否开启同步 | — |

- FFI op（Commit 经 CORE-03 长任务提交，其余快速调用；入参类型按上方 UpgradeMode/StepInput/KeySecret 的 DTO 映射）：

| op | 请求 | 响应 | 说明 |
| --- | --- | --- | --- |
| `account.upgrade_begin` | `{ mode }` | `{ journal }` | — |
| `account.upgrade_advance` | `{ input }` | `{ step, key_output? }` | （`recovery_code` 只在此响应中出现一次） |
| `account.upgrade_status` | `{}` | `{ journal? }` | — |
| `account.upgrade_abandon` | `{}` | `{}` | — |
| `account.import_account_key` | `{ account_id, records, secret }` | `{ key_version }` | `records` 为 `GET /v1/keys` 返回的 `record_base64` 数组原样转交，由本卡按 CORE-21 wire v1 解码 |
| `account.rotate_account_key` | `{}` | `{ key_version, key_output }` | — |
| `account.wrap_with_passphrase` | `{ key_version, passphrase }` | `{ record_base64 }` | （CORE-21 口令策略校验；适配层向 `wrap_with_params` 传入 CORE-23 的 OsRandom 取盐与 nonce，失败 `CRYPTO_RNG_FAILED`）；`KeyOutput.wrap_record` 与 `StepInput::ExistingKey.records` 在 FFI 上同样用 `record_base64` |
- 错误码（触发条件）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `SYNC_UPGRADE_IN_PROGRESS` | warning | 是 | 升级期间调用业务写 op，或已有未完成日志时再次 `begin` |
| `SYNC_UPGRADE_STEP_INVALID` | error | 否 | 输入与当前步骤不匹配，或 IdentityReady 后输入了不同 account_id |
| `SYNC_UPGRADE_KEY_FAILED` | error | 是 | 经 `SecureRandom` 生成 AccountDataKey 或恢复码失败（底层 `CRYPTO_RNG_FAILED`，写入 `last_error`；日志已推进的步骤不回滚，重试时重新取随机字节），或 `ExistingKey` / `import_account_key` 的恢复码、密语无法解开任何记录（底层 `CRYPTO_*` 原因码记在 `last_error`） |
| `SYNC_UPGRADE_NOT_ABANDONABLE` | error | 否 | 已到 LocalCommitted 后调用 `abandon` |

跨文件恢复的唯一路径：CORE-23 首次启动扫描所有档案的未完成 journal（只在平台密钥可用且所需档案已打开后读），发现 LocalCommitted 后先补写 DeviceRegistry，再放行路由。注册表先更新/后崩溃则下次同值覆盖；档案提交后未投影则按 journal 补写；注册表损坏可重建，不能覆盖档案真值。平台密钥不可用或档案未打开时保持账户入口并报告原因，不把陈旧游客标记当成可写游客。CORE-23 设备记录附 profile_commit_id，等于 journal.id 即已投影。


本卡全部op为profile scope，继承CORE-03信封profile_handle。升级日志从该Store取当前未完成行，不能从单例查“当前游客”。StepInput线上形状为互斥单键对象：{"identity":{"account_id":UUID}}、"new_key"、{"key_uploaded":{"key_version":u32}}、{"existing_key":{"account_id":UUID,"records":[base64 WrapRecord],"secret":{"recovery_code":string}或{"passphrase":string}}}、"commit"；与CORE-03的外部标记枚举一致。KeyOutput为{recovery_code:string,wrap_record:string}，wrap_record为CORE-21规范CBOR的标准base64；不是内联Rust结构。secret/passphrase/recovery_code/target_db_key均x-sensitive。advance请求仅input，journal由本Store查询，响应step及可选key_output；不返回SecretKey。例begin body={"mode":"new_account"}，ok={"journal":{"id":"00000000-0000-4000-8000-000000000002","step":"prepared","mode":"new_account","started_ms":0,"updated_ms":0}}；advance body={"input":{"identity":{"account_id":"00000000-0000-4000-8000-000000000003"}}}，ok={"step":"identity_ready"}。

account_key读取接缝归本卡：load_account_keys(store)在同一只读快照加载account_state.account_id/account_epoch及account_key全部版本，返回本卡定义的AccountKeyRows { account_id:Uuid, account_epoch:u32, versions:Vec<(u32,SecretKey)> }；CORE-26消费者据此构造自己的AccountKeys（下游说明，非契约），本卡不引用下游类型；在当前账户没有密钥时SYNC_KEY_MISSING，不回退其他档案。每次同步操作读取独立Zeroizing快照，操作结束清零；轮换/导入提交后下次请求自动读取新版本，不跨请求长期缓存明文密钥。

产品约束追踪：见README §6 Q3；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- MergeInto且本机已有目标档案时，Commit由CORE-83的merge_guest完成；本卡advance(Commit)不调用下游实现，对该模式/场景返回SYNC_UPGRADE_STEP_INVALID，由协调器选择专用merge op。
- 为CORE-83提供本卡拥有的目标journal/注册表投影接缝：同一目标WriteTx内更新cursor/映射并提交LocalCommitted（registry_pending=1），其后由本卡resume_on_start完成投影；不在新卡重写此机制。
- 本机数据库密钥与识别历史密钥从不上传；只上传被恢复码或同步密语包装的 AccountDataKey。新设备生成自己的 DbKey；不得跨设备复制 SQLCipher 库文件。
- 升级成功前不得删除游客原库与原密钥包装；LocalCommitted 之后不自动回退为游客。首次同步失败时保留 outbox 待重试。
- 识别历史与 `*_cache` 表不写入首次全量 outbox。
- 本卡不发网络请求；联网协调（注册或登录、上传与下载包装记录、首次同步）由 CORE-99 完成并做端到端测试。
- 外部前提：`uuid` crate（v5 特性）随 CORE-13 锁定。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-24_TEST.md](../Test/core/S6_CORE-24_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约490行；主包`crates/fml-store/src/sync/upgrade.rs`与`keys.rs`，附属`crates/fml-ffi/src/ops/upgrade.rs`（除account.upgrade_merge外的处理/登记）及`migrations/0024_upgrade.sql`的数据定义。包含升级写门暂停/恢复接入，写门hook实现归CORE-13。DDL/自测/CORE-83并入实现不计。
