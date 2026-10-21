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
}
// crates/fml-store/src/account/rng.rs：CORE-21 SecureRandom 的唯一 OS 实现（ADR-V5-41）
pub struct OsRandom;   // impl SecureRandom：封装 getrandom；平台失败 → CRYPTO_RNG_FAILED，不回退、不用全零；fml-ffi 与 fml-store 其他卡经它取得 &mut dyn SecureRandom，不得另建 OS 随机实现
// 同模块公开导出 fml_store::account::{OsRandom, RandomIds}；IdSource 唯一定义归 CORE-13
pub struct RandomIds<R: SecureRandom + Send> { /* 持有注入的 rng，不读取其他随机源 */ }
impl<R: SecureRandom + Send> RandomIds<R> { pub fn new(rng: R) -> Self; }
// impl<R: SecureRandom + Send> IdSource for RandomIds<R>：每次只取16字节，按UUID-v4设置version/variant，返回Uuid；fill失败原样CRYPTO_RNG_FAILED，不回退、不重试。生产RandomIds::new(OsRandom)，测试固定序列/失败替身；设备/op ID唯一性与非法提供器输出拒绝由CORE-13负责。
// LocalSetting 存在已打开档案库的 local_setting 表（CORE-13），键 device.reminder_time，syncable = 0
pub fn local_setting(store: &Store) -> Result<LocalSetting, FmlError>;
pub fn set_local_setting(store: &Store, s: &LocalSetting) -> Result<(), FmlError>;   // 越界 → AUTH_SETTING_INVALID
```

- 表（`crates/fml-store/migrations/registry/0023_registry.sql`，只用于 device_registry.db）：`profile`（`profile_id TEXT PK`，`account_id TEXT UNIQUE NULL`，`email_masked TEXT NULL`，`is_guest INTEGER`，`db_file TEXT`，`logged_out INTEGER NOT NULL DEFAULT 0`，`sync_enabled INTEGER DEFAULT 0`，`last_used_ms INTEGER`，`profile_commit_id TEXT NULL`（升级投影标记，非Profile线上字段）；部分唯一索引保证 `is_guest=1` 至多一行）、`profile_blob`（`profile_id`，`kind TEXT`，`wrapped BLOB`，PK `(profile_id, kind)`）。档案库内的 `account_state`（`crates/fml-store/migrations/0023_account.sql`，单行：`profile_id TEXT PK`，`account_id TEXT NULL`，`account_epoch INTEGER NOT NULL DEFAULT 0`，`converted_at_ms INTEGER NULL`）供 CORE-24 在本地提交步骤更新。
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
| `account.local_setting` | `{}`（profile scope） | `{ setting: LocalSetting }` |
| `account.set_local_setting` | `{ setting: LocalSetting }`（profile scope） | `{}` |

- 错误码（触发条件）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `AUTH_NO_PROFILE` | error | 否 | Uninitialized 下调用任何业务 op，或 `profile_id` 不存在 |
| `AUTH_GUEST_EXISTS` | error | 否 | 已有游客档案时再次创建游客 |
| `AUTH_PROFILE_EXISTS` | warning | 否 | 同一 account_id 再次创建注册档案（客户端改为打开已有档案） |
| `AUTH_LOCKED` | error | 否 | RegisteredLocked（已登出）状态下调用业务 op |
| `AUTH_SETTING_INVALID` | error | 否 | `LocalSetting` 字段越界（`reminder_time` 不是 00:00–23:59 的 HH:MM） |

- 本卡安装点登记 CORE-28 GuardContext，将本卡状态映射为 GuardAccountState；Uninitialized 默认只允许匿名 auth、packDownload、updateCheck，不发任何内容。

- 设备注册表只是档案状态的可重建投影，附 profile_commit_id TEXT NULL；存在未完成升级时，解锁后按档案 upgrade_journal 补投影再开放业务。S2 提供此恢复接缝，S6 CORE-24 安装实际 journal 恢复器。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `PLATFORM_KEY_UNAVAILABLE` | CORE-04 | 平台密钥失效（如系统重置或更换系统用户）→ 引导重新登录 + 恢复码恢复（CORE-24），游客只能新建档案 |

account.profiles/create_guest/create_registered/put_blob/get_blob/state/set_logged_out/open_profile 均为device scope，持久化目标由显式profile_id（或创建响应）决定；close_profile/set_sync_enabled/local_setting/set_local_setting 为profile scope。account.state不读全局活动档案：省略profile_id返回uninitialized；给出profile_id时以注册表logged_out及该档案是否有开放handle计算，尚未打开且未登出的游客/注册档案仍返回uninitialized，不能宣称可访问业务。account.set_sync_enabled由信封profile_handle绑定档案，body.profile_id必须一致，不匹配返回FFI_BAD_ARG，状态变更由CORE-65串行化。

创建返回db_key后，CORE-65先平台wrap、put_blob持久化，再open_profile；失败清零且不发布Unlocked。open_profile从注册表生成路径/backup_dir/read_pool=2，内部构造Box::new(RandomIds::new(OsRandom))，调用CORE-13的Store::open(&cfg,key,ids)；IdSource不经JSON传入，不更改现有请求/响应。生产只使用本卡OsRandom，测试以固定/失败SecureRandom构造同一适配；既有库打开不额外消耗device_id随机数，新库创建或后续写需要ID时才由actor取用。检查profile_id与库内account_state相等（初建时同事务写入），不得相信任意传入路径。已打开同档案返回STORE_BUSY。close_profile完成后才发布RegisteredLocked或Uninitialized；lock=true须先落logged_out=true，崩溃后仍停入口。进程重启旧handle一律无效。对已存在注册档案的create_registered返回AUTH_PROFILE_EXISTS且不返回新db_key；从get_blob恢复原包装值。

本卡wire补充：profile_id/account_id为CORE-03 UUID，email_masked为1～254字符且不含完整邮箱，db_key解码32字节（x-sensitive），wrapped为1～65536字节标准base64（设备密文），kind为db_key/refresh_token，state为五状态snake_case；Profile字段按Rust结构全部必填，account_id/email_masked缺省时省略。profiles返回数组上限100；空列表为[]。LocalSetting.reminder_time可省略，缺省无提醒。除两个submit外其余本卡op均call。例open请求body={"profile_id":"00000000-0000-4000-8000-000000000001","db_key":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}（仅fixture），ok={"state":"guest_unlocked","profile_id":"00000000-0000-4000-8000-000000000001","handle":"281474976710657"}；local_setting以该profile_handle及空body调用，ok={"setting":{}}。

FFI错误镜像（不重定义代码；通用信封错误见CORE-03）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| account.close_profile | STORE_CORRUPT、STORE_BUSY |
| account.create_guest | AUTH_GUEST_EXISTS、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY、CRYPTO_RNG_FAILED |
| account.create_registered | AUTH_PROFILE_EXISTS、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY、CRYPTO_RNG_FAILED |
| account.get_blob | AUTH_NO_PROFILE、STORE_CORRUPT、STORE_BUSY |
| account.local_setting | AUTH_NO_PROFILE、AUTH_LOCKED、STORE_CORRUPT、STORE_BUSY |
| account.open_profile | AUTH_NO_PROFILE、AUTH_LOCKED、STORE_KEY_INVALID、STORE_SCHEMA_TOO_NEW、STORE_MIGRATION_FAILED、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY、CRYPTO_RNG_FAILED |
| account.profiles | STORE_CORRUPT |
| account.put_blob | AUTH_NO_PROFILE、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
| account.set_local_setting | AUTH_NO_PROFILE、AUTH_LOCKED、AUTH_SETTING_INVALID、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
| account.set_logged_out | AUTH_NO_PROFILE、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
| account.set_sync_enabled | AUTH_NO_PROFILE、AUTH_LOCKED、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
| account.state | AUTH_NO_PROFILE、STORE_CORRUPT |

产品约束追踪：见README §6 Q9；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 游客是本地一等账户，不是“未登录匿名状态”；游客不向云端提交公式、图片、笔记、复习日志、识别结果、内容偏好或诊断数据。
- 注册用户可离线编辑、查阅、计算和复习；云识别与同步需要网络。登录与注册都需网络；离线时已登录档案照常打开。
- 登出不清空本地数据；选择游客时打开独立的游客库，绝不打开之前注册账户的库。每个档案一个数据库文件（`StoreArea.database` 下 `<profile_id>.db`）。
- 安全等级降级（`securityLevel` 返回 `software`）必须显式提示，不得静默宣称强隔离。
- `DbKey`、刷新令牌明文不落盘、不进日志；Dart 侧 `Uint8List` 用后填零。
- 外部前提：rusqlite（随 CORE-13 锁定）；getrandom由本卡首次使用时依ADR-V5-15锁入Cargo.lock，OS熵源仅OsRandom生产实现使用；登录的系统浏览器回调用 AND-03 / WIN-04 提供的深链处理（`fml://auth/callback`）。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-23_TEST.md](../Test/core/S2_CORE-23_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 555 行，分阶段：① `crates/fml-store/src/account/` 的注册表/包装密文与独立迁移运行约190、状态与打开关闭约110、设置约35、OsRandom/RandomIds约35、类型与错误约45，共约415，先以注入熵源/提供器及临时双库夹具独立构建测试；② 本卡附属跨界接线 `crates/fml-ffi/src/ops/account.rs` 的account.*解码、句柄接线及错误透传约140，依赖第一阶段后可独立构建并跑op验收。迁移SQL、向量及自测不计；profile_commit_id恢复接缝仍归本卡，实际升级恢复器归CORE-24，不以未来移走工作掩盖本卡规模。

