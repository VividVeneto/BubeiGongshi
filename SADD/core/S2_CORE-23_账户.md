### CORE-23 账户状态、登录边界与本机解锁

**目标**：实现“未登录不可使用、可选游客、注册可同步”的账户状态机，管理本机多账户档案、数据库密钥的平台包装、系统级本机解锁与登出行为。

**范围**
- 包含：Rust 档案注册表、账户状态、设置、FFI op 与包装密文持久化。
- 不包含：Dart 控制器与 TokenStore 实现，迁至 CORE-65（下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-13、CORE-21、CORE-22、CORE-28

**接口契约**

```text
状态：Uninitialized → GuestUnlocked | RegisteredUnlocked
      RegisteredUnlocked ⇄ RegisteredLocked（登出）
      GuestUnlocked → UpgradingGuest → RegisteredUnlocked（CORE-24）
Uninitialized：没有已打开的档案；只能看到账户入口（游客 / 注册 / 登录），任何业务 op 返回 AUTH_NO_PROFILE
GuestUnlocked：全部本地功能；网络只允许用户显式触发的公开资源包下载与更新检查
RegisteredUnlocked：全部本地功能 + 云识别（逐次授权）+ 已开启时的同步
RegisteredLocked：已登出，数据库已关闭、内存中的 DbKey 已清零；不做任何上传；业务 op 返回 AUTH_LOCKED；重新登录后打开
启动：device_registry 中 last_used 档案存在且未登出 → 系统级解包 DbKey 后自动打开；已登出的注册档案 → 停在账户入口（RegisteredLocked）；无档案 → Uninitialized
本机只用系统级解锁（平台密钥自动解包），不提供应用锁与应用自有 PIN（README §6 Q41，甲方确认）
```

```rust
// crates/fml-store/src/account/mod.rs
pub enum AccountState { Uninitialized, GuestUnlocked, RegisteredUnlocked, RegisteredLocked, UpgradingGuest }
pub enum BlobKind { DbKey, RefreshToken }
pub struct Profile { pub profile_id: Uuid, pub account_id: Option<Uuid> /* 游客为 None */, pub email_masked: Option<String>,
                     pub db_path: PathBuf, pub logged_out: bool, pub sync_enabled: bool, pub last_used_ms: i64 }
pub struct LocalSetting { pub reminder_time: Option<String> /* "HH:MM"，默认 None（界面按 20:00 显示） */ }   // 识别历史设置归 CORE-32（存 recognition_counter）
pub trait DeviceRegistry {               // device_registry.db：普通 SQLite，位于应用私有目录；不含学习内容，账户只存 ID 与脱敏邮箱
    fn profiles(&self) -> Result<Vec<Profile>, FmlError>;
    fn create_guest(&self) -> Result<(Profile, DbKey), FmlError>;               // 每个系统用户每台设备至多一个游客档案
    fn create_registered(&self, account_id: Uuid, email_masked: &str) -> Result<(Profile, DbKey), FmlError>; // 同一 account_id 已有档案 → 返回该档案与 AUTH_PROFILE_EXISTS
    fn put_blob(&self, profile: Uuid, kind: BlobKind, wrapped: &[u8]) -> Result<(), FmlError>;   // 只存平台包装后的密文
    fn get_blob(&self, profile: Uuid, kind: BlobKind) -> Result<Option<Vec<u8>>, FmlError>;
    fn set_logged_out(&self, profile: Uuid, logged_out: bool) -> Result<(), FmlError>;   // 登出置 true，登录成功置 false
    fn set_sync_enabled(&self, profile: Uuid, enabled: bool) -> Result<(), FmlError>;   // 只改注册表 profile.sync_enabled（Profile 的唯一存放处）
    fn touch_last_used(&self, profile: Uuid, now_ms: i64) -> Result<(), FmlError>;      // 时间由调用方传入（本 crate 不读时钟）；启动选择 last_used 档案用
    fn delete_profile(&self, profile: Uuid) -> Result<(), FmlError>;                    // 删除档案：见下文“删除档案”；本进程仍有开放 handle → STORE_BUSY
}
// 唯一生产实现；随机源与恢复器构造时注入（ADR-V5-41），create_* 的 profile_id 与 DbKey 只取自注入的 rng
pub struct SqliteRegistry { /* device_registry.db 连接、rng、recovery、开放 handle 表 */ }
impl SqliteRegistry {
    pub fn open(path: &Path, database_dir: &Path, backup_root: &Path,
                rng: Box<dyn SecureRandom + Send>, recovery: Box<dyn ProjectionRecovery>) -> Result<Self, FmlError>;   // 运行独立迁移域并补完 deleting=1 的未完成删除
}
impl DeviceRegistry for SqliteRegistry {}
pub fn open_profile(reg: &SqliteRegistry, profile: Uuid, key: DbKey) -> Result<(Store, AccountState), FmlError>;   // 规则见下文；FFI account.open_profile 只调用它
pub fn account_state(reg: &SqliteRegistry, profile: Option<Uuid>) -> Result<AccountState, FmlError>;         // account.state 规则见下文
// crates/fml-store/src/account/recovery.rs：升级投影恢复接缝（S2 定义，S6 CORE-24 实现）
pub trait ProjectionRecovery: Send + Sync {
    fn pending(&self, store: &Store) -> Result<Option<RegistryProjection>, FmlError>;   // 档案库内未完成升级日志要求的注册表投影；无则 None
    fn projected(&self, store: &Store, commit_id: &str) -> Result<(), FmlError>;         // 注册表已按该 commit 投影后回调，由实现方清自己的待投影标志
}
pub struct RegistryProjection { pub account_id: Option<Uuid>, pub email_masked: Option<String>,
                                pub profile_commit_id: String, pub upgrading: bool /* 日志未到 Done */ }
pub struct NoRecovery;   // S2 生产默认：pending 恒 Ok(None)、projected 不可达；impl ProjectionRecovery
// crates/fml-store/src/account/rng.rs：CORE-21 SecureRandom 的唯一 OS 实现（ADR-V5-41）
pub struct OsRandom;   // impl SecureRandom：封装 getrandom；平台失败 → CRYPTO_RNG_FAILED，不回退、不用全零；fml-ffi 与 fml-store 其他卡经它取得 &mut dyn SecureRandom，不得另建 OS 随机实现
// 测试注入点（crate 内部，非公共契约）：#[cfg(test)] 下 OsRandom 内部熵函数可替换为失败/固定函数（crate 私有构造），生产路径只走 getrandom；失败替身经此验证 CRYPTO_RNG_FAILED
// 同模块公开导出 fml_store::account::{OsRandom, RandomIds}；IdSource 唯一定义归 CORE-13
pub struct RandomIds<R: SecureRandom + Send> { /* 持有注入的 rng，不读取其他随机源 */ }
impl<R: SecureRandom + Send> RandomIds<R> { pub fn new(rng: R) -> Self; }
// impl<R: SecureRandom + Send> IdSource for RandomIds<R>：每次只取16字节，按UUID-v4设置version/variant，返回Uuid；fill失败原样CRYPTO_RNG_FAILED，不回退、不重试。生产RandomIds::new(OsRandom)，测试固定序列/失败替身；设备/op ID唯一性与非法提供器输出拒绝由CORE-13负责。
// LocalSetting 存在已打开档案库的 local_setting 表（CORE-13），键 device.reminder_time，syncable = 0
pub fn local_setting(store: &Store) -> Result<LocalSetting, FmlError>;
pub fn set_local_setting(store: &Store, s: &LocalSetting) -> Result<(), FmlError>;   // 越界 → AUTH_SETTING_INVALID
```

- 表（`crates/fml-store/migrations/registry/0023_registry.sql`，只用于 device_registry.db）：`profile`（`profile_id TEXT PK`，`account_id TEXT UNIQUE NULL`，`email_masked TEXT NULL`，`is_guest INTEGER`，`db_file TEXT`，`logged_out INTEGER NOT NULL DEFAULT 0`，`sync_enabled INTEGER DEFAULT 0`，`last_used_ms INTEGER NULL`，`deleting INTEGER NOT NULL DEFAULT 0 CHECK (deleting IN (0,1))`（删除进行中标记，非Profile线上字段），`profile_commit_id TEXT NULL`（升级投影标记，非Profile线上字段）；部分唯一索引保证 `is_guest=1` 至多一行）、`profile_blob`（`profile_id`，`kind TEXT`，`wrapped BLOB`，PK `(profile_id, kind)`）。档案库内的 `account_state`（`crates/fml-store/migrations/0023_account.sql`，单行：`profile_id TEXT PK`，`account_id TEXT NULL`，`account_epoch INTEGER NOT NULL DEFAULT 0`，`converted_at_ms INTEGER NULL`）供 CORE-24 在本地提交步骤更新。
- 注册表独立迁移域（ADR-V5-50）：本卡的 `REGISTRY_SCHEMA_VERSION` 只取 `migrations/registry/` 直接子级的四位序号SQL最大值（V1当前0023）；注册表连接有自己的 `schema_migration(version,name,applied_at_ms,checksum)` 与 `PRAGMA user_version`。CORE-13档案库运行器与 `SCHEMA_VERSION` 只取 `migrations/` 直接子级，绝不递归registry目录；两个0023分属两个库，不互相执行或覆盖版本。注册表按序补执行未登记文件、全部待执行迁移与最终user_version同事务提交；已登记文件逐项校验文件名/字节BLAKE3，checksum或名称不符拒绝打开并报STORE_MIGRATION_FAILED；已执行迁移文件缺失或库版本高于本程序注册表最大版本报STORE_SCHEMA_TOO_NEW，禁止静默重建/降级。迁移失败完整回滚，不发布任何档案会话。
- 平台密钥别名（与 AND-06、WIN-07 一致）：只有 `fml.<profile_id>.db` 一个别名，系统级包装 DbKey 与刷新令牌，解包不要求用户认证。
- FFI op（请求 → 响应；`db_key` 为 base64，只在本进程 FFI 内传递，Dart 侧用后立即清零）：

| op | 请求 | 响应 |
| --- | --- | --- |
| `account.state` | `{ profile_id? }`（device scope，省略表示未选择档案） | `{ state, profile_id? }` |
| `account.profiles` | `{}` | `{ profiles: Profile[] }` |
| `account.create_guest` | `{}` | `{ profile, db_key }`（Dart 包装后调 `account.put_blob`） |
| `account.create_registered` | `{ account_id, email_masked }` | `{ profile, db_key }` |
| `account.put_blob` | `{ profile_id, kind, wrapped }` | `{}` |
| `account.get_blob` | `{ profile_id, kind }` | `{ wrapped? }` |
| `account.open_profile` | `{ profile_id, db_key }`（device scope，submit） | `{ state, profile_id, handle }`（CORE-13 Store::open所得句柄，十进制u64） |
| `account.close_profile` | `{ lock: bool }`（profile scope，submit） | `{ state }`（关闭该句柄、清零密钥；lock仅指本次关闭后是否停在登出入口，不引入应用锁） |
| `account.set_logged_out` | `{ profile_id, logged_out }` | `{}` |
| `account.set_sync_enabled` | `{ profile_id, enabled }` | `{}` |
| `account.touch_last_used` | `{ profile_id, now_ms }`（device scope） | `{}` |
| `account.delete_profile` | `{ profile_id }`（device scope，submit） | `{}` |
| `account.local_setting` | `{}`（profile scope） | `{ setting: LocalSetting }` |
| `account.set_local_setting` | `{ setting: LocalSetting }`（profile scope） | `{}` |

- 错误码（触发条件）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `AUTH_NO_PROFILE` | error | 否 | Uninitialized 下调用任何业务 op，或 `profile_id` 不存在（含 deleting=1 的删除中档案） |
| `AUTH_GUEST_EXISTS` | error | 否 | 已有游客档案时再次创建游客 |
| `AUTH_PROFILE_EXISTS` | warning | 否 | 同一 account_id 再次创建注册档案（客户端改为打开已有档案）；诊断 `args.profile_id` 为既有档案 UUID，不返回新 db_key |
| `AUTH_LOCKED` | error | 否 | RegisteredLocked（已登出）状态下调用业务 op |
| `AUTH_SETTING_INVALID` | error | 否 | `LocalSetting` 字段越界（`reminder_time` 不是 00:00–23:59 的 HH:MM） |

- 本卡无 Dart 代码：CORE-28 GuardContext 的实现与五状态映射（uninitialized/guest/upgrading/registered/registeredLocked 及 syncEnabled=Profile.sync_enabled）由 CORE-36 AccountGuardContext 在其安装点登记并验收；本卡只提供 account.state 与 Profile.sync_enabled 两个来源（下游说明，非契约）。

- 设备注册表只是档案状态的可重建投影，附 profile_commit_id TEXT NULL。恢复接缝即上方 ProjectionRecovery：open_profile 在 Store::open 成功后、返回前调用 recovery.pending(&store)；Some(p) → 单事务把 account_id/email_masked/profile_commit_id 写入该行（同值覆盖幂等）后调用 projected(&store, &p.profile_commit_id)，任一步失败关闭 Store、不返回 handle 并原样返回错误；p.upgrading 为真时本次打开的状态为 UpgradingGuest。S2 生产注入 NoRecovery，故 S2 的 account.state/open_profile 永不返回 upgrading_guest；S6 CORE-24 以自己的实现替换构造参数，不改本卡签名。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `PLATFORM_KEY_UNAVAILABLE` | CORE-04 | 平台密钥失效（如系统重置或更换系统用户）→ 引导重新登录 + 恢复码恢复（CORE-24），游客只能新建档案 |

account.profiles/create_guest/create_registered/put_blob/get_blob/state/set_logged_out/open_profile/touch_last_used/delete_profile 均为device scope，持久化目标由显式profile_id（或创建响应）决定；close_profile/set_sync_enabled/local_setting/set_local_setting 为profile scope。account.state不读全局活动档案：省略profile_id返回uninitialized；给出profile_id时以注册表logged_out及该档案是否有开放handle计算，尚未打开且未登出的游客/注册档案仍返回uninitialized，不能宣称可访问业务。account.set_sync_enabled由信封profile_handle绑定档案，body.profile_id必须一致，不匹配返回FFI_BAD_ARG，状态变更由CORE-65串行化。

创建返回db_key后，CORE-65先平台wrap、put_blob持久化，再open_profile；失败清零且不发布Unlocked。open_profile从注册表生成路径/backup_dir/read_pool=2，内部构造Box::new(RandomIds::new(OsRandom))，调用CORE-13的Store::open(&cfg,key,ids)；IdSource不经JSON传入，不更改现有请求/响应。生产只使用本卡OsRandom，测试以固定/失败SecureRandom构造同一适配；既有库打开不额外消耗device_id随机数，新库创建或后续写需要ID时才由actor取用。检查profile_id与库内account_state相等（初建时同事务写入），不符 → STORE_CORRUPT 且关闭 Store、不返回 handle；不得相信任意传入路径。已打开同档案返回STORE_BUSY。close_profile完成后才发布RegisteredLocked或Uninitialized；lock=true须先落logged_out=true，崩溃后仍停入口。进程重启旧handle一律无效。对已存在注册档案的create_registered返回AUTH_PROFILE_EXISTS（args.profile_id=既有档案）且不返回新db_key、不消耗rng；客户端从get_blob恢复原包装值。create_* 先从注入rng取16字节profile_id与32字节DbKey（直接填入CORE-13 DbKey的Zeroizing缓冲，不经CORE-21 SecretKey），任一fill失败返回CRYPTO_RNG_FAILED且注册表无写入；随后单事务插入profile行。open_profile成功后由CORE-65调用touch_last_used；启动规则中的last_used档案取last_used_ms最大且deleting=0者，NULL视为最旧。

删除档案（delete_profile，CORE-65 在二次确认并 close_profile 后调用）：①本进程仍有该档案开放handle → STORE_BUSY，不改任何状态；②单事务置profile.deleting=1（此后 profiles 不列出、其他 op 视为不存在）；③删除该行db_file及其-wal/-shm与注册表为其生成的backup_dir，文件被占用或删除失败 → STORE_BUSY（可重试，保持deleting=1）；④单事务删除profile_blob与profile行。重复调用对deleting=1的行从③继续，幂等；SqliteRegistry::open发现deleting=1的行同样从③补完，失败只留待下次，不阻断其他档案。平台别名fml.<profile_id>.db由CORE-65在本op成功后经CORE-04 SecureKeyValueStore.delete删除；本卡不删除未登记的库文件（注册表重建以库文件为准）。

本卡wire补充：profile_id/account_id为CORE-03 UUID，email_masked为1～254字符且不含完整邮箱，db_key解码32字节（x-sensitive），wrapped为1～65536字节标准base64（设备密文），kind为db_key/refresh_token，state为五状态snake_case，now_ms为i64毫秒；Profile字段按Rust结构全部必填，account_id/email_masked缺省时省略。profiles返回数组上限100；空列表为[]。LocalSetting.reminder_time可省略，缺省无提醒。除open_profile/close_profile/delete_profile三个submit外其余本卡op均call。例open请求body={"profile_id":"00000000-0000-4000-8000-000000000001","db_key":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}（仅fixture），ok={"state":"guest_unlocked","profile_id":"00000000-0000-4000-8000-000000000001","handle":"281474976710657"}；local_setting以该profile_handle及空body调用，ok={"setting":{}}。

FFI错误镜像（不重定义代码；通用信封错误见CORE-03）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| account.close_profile | STORE_CORRUPT、STORE_BUSY |
| account.create_guest | AUTH_GUEST_EXISTS、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY、CRYPTO_RNG_FAILED |
| account.create_registered | AUTH_PROFILE_EXISTS、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY、CRYPTO_RNG_FAILED |
| account.delete_profile | AUTH_NO_PROFILE、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
| account.get_blob | AUTH_NO_PROFILE、STORE_CORRUPT、STORE_BUSY |
| account.local_setting | AUTH_NO_PROFILE、AUTH_LOCKED、STORE_CORRUPT、STORE_BUSY |
| account.open_profile | AUTH_NO_PROFILE、AUTH_LOCKED、STORE_KEY_INVALID、STORE_SCHEMA_TOO_NEW、STORE_MIGRATION_FAILED、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY、CRYPTO_RNG_FAILED |
| account.profiles | STORE_CORRUPT |
| account.put_blob | AUTH_NO_PROFILE、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
| account.set_local_setting | AUTH_NO_PROFILE、AUTH_LOCKED、AUTH_SETTING_INVALID、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
| account.set_logged_out | AUTH_NO_PROFILE、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
| account.set_sync_enabled | AUTH_NO_PROFILE、AUTH_LOCKED、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
| account.state | AUTH_NO_PROFILE、STORE_CORRUPT |
| account.touch_last_used | AUTH_NO_PROFILE、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |

产品约束追踪：见README §6 Q9；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 游客是本地一等账户，不是“未登录匿名状态”；游客不向云端提交公式、图片、笔记、复习日志、识别结果、内容偏好或诊断数据。
- 注册用户可离线编辑、查阅、计算和复习；云识别与同步需要网络。登录与注册都需网络；离线时已登录档案照常打开。
- 登出不清空本地数据；选择游客时打开独立的游客库，绝不打开之前注册账户的库。每个档案一个数据库文件（`StoreArea.database` 下 `<profile_id>.db`）。
- 安全等级降级（`securityLevel` 返回 `software`）必须显式提示，不得静默宣称强隔离。
- `DbKey`、刷新令牌明文不落盘、不进日志；Dart 侧 `Uint8List` 用后填零。
- 外部前提：rusqlite（随 CORE-13 锁定）；getrandom由本卡首次使用时依ADR-V5-15锁入Cargo.lock，OS熵源仅OsRandom生产实现使用。登录回调深链 `fml://auth/callback` 属 CORE-65 外部前提，不列于本卡。
- 依赖说明：CORE-04 供 PLATFORM_KEY_UNAVAILABLE 处理与别名约定；CORE-22（服务端账户状态与 account_id 语义）、CORE-28（GuardAccountState 五值语义）为语义依赖，本卡 Rust 代码不引用其符号。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-23_TEST.md](../Test/core/S2_CORE-23_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 615 行，分阶段：① `crates/fml-store/src/account/` 的注册表/包装密文与独立迁移运行约190、同步开关/last_used/删除档案约35、状态与打开关闭约110、投影恢复接缝约15、设置约35、OsRandom/RandomIds约35、类型与错误约45，共约465，先以注入熵源/提供器及临时双库夹具独立构建测试；② 本卡附属跨界接线 `crates/fml-ffi/src/ops/account.rs` 的account.*（14 个 op）解码、句柄接线及错误透传约150，依赖第一阶段后可独立构建并跑op验收。迁移SQL、向量及自测不计；profile_commit_id恢复接缝仍归本卡，实际升级恢复器归CORE-24，不以未来移走工作掩盖本卡规模。

