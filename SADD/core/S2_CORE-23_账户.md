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
// LocalSetting 存在已打开档案库的 local_setting 表（CORE-13），键 device.reminder_time，syncable = 0
pub fn local_setting(store: &Store) -> Result<LocalSetting, FmlError>;
pub fn set_local_setting(store: &Store, s: &LocalSetting) -> Result<(), FmlError>;   // 越界 → AUTH_SETTING_INVALID
```

- 表（`crates/fml-store/migrations/registry/0023_registry.sql`，只用于 device_registry.db）：`profile`（`profile_id TEXT PK`，`account_id TEXT UNIQUE NULL`，`email_masked TEXT NULL`，`is_guest INTEGER`，`db_file TEXT`，`logged_out INTEGER NOT NULL DEFAULT 0`，`sync_enabled INTEGER DEFAULT 0`，`last_used_ms INTEGER`；部分唯一索引保证 `is_guest=1` 至多一行）、`profile_blob`（`profile_id`，`kind TEXT`，`wrapped BLOB`，PK `(profile_id, kind)`）。档案库内的 `account_state`（`crates/fml-store/migrations/0023_account.sql`，单行：`profile_id TEXT PK`，`account_id TEXT NULL`，`account_epoch INTEGER NOT NULL DEFAULT 0`，`converted_at_ms INTEGER NULL`）供 CORE-24 在本地提交步骤更新。
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

创建返回db_key后，CORE-65先平台wrap、put_blob持久化，再open_profile；失败清零且不发布Unlocked。open_profile从注册表生成路径/backup_dir/read_pool=2，检查profile_id与库内account_state相等（初建时同事务写入），不得相信任意传入路径。已打开同档案返回STORE_BUSY。close_profile完成后才发布RegisteredLocked或Uninitialized；lock=true须先落logged_out=true，崩溃后仍停入口。进程重启旧handle一律无效。对已存在注册档案的create_registered返回AUTH_PROFILE_EXISTS且不返回新db_key；从get_blob恢复原包装值。

本卡wire补充：profile_id/account_id为CORE-03 UUID，email_masked为1～254字符且不含完整邮箱，db_key解码32字节（x-sensitive），wrapped为1～65536字节标准base64（设备密文），kind为db_key/refresh_token，state为五状态snake_case；Profile字段按Rust结构全部必填，account_id/email_masked缺省时省略。profiles返回数组上限100；空列表为[]。LocalSetting.reminder_time可省略，缺省无提醒。除两个submit外其余本卡op均call。例open请求body={"profile_id":"00000000-0000-4000-8000-000000000001","db_key":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}（仅fixture），ok={"state":"guest_unlocked","profile_id":"00000000-0000-4000-8000-000000000001","handle":"281474976710657"}；local_setting以该profile_handle及空body调用，ok={"setting":{}}。

FFI错误镜像（不重定义代码；通用信封错误见CORE-03）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| account.close_profile | STORE_CORRUPT、STORE_BUSY |
| account.create_guest | AUTH_GUEST_EXISTS、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
| account.create_registered | AUTH_PROFILE_EXISTS、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
| account.get_blob | AUTH_NO_PROFILE、STORE_CORRUPT、STORE_BUSY |
| account.local_setting | AUTH_NO_PROFILE、AUTH_LOCKED、STORE_CORRUPT、STORE_BUSY |
| account.open_profile | AUTH_NO_PROFILE、AUTH_LOCKED、STORE_KEY_INVALID、STORE_SCHEMA_TOO_NEW、STORE_MIGRATION_FAILED、STORE_CORRUPT、STORE_DISK_FULL、STORE_BUSY |
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
- 外部前提：rusqlite（随 CORE-13 锁定）；登录的系统浏览器回调用 AND-03 / WIN-04 提供的深链处理（`fml://auth/callback`）。

**验收标准**
- [R24] 状态机单元测试：Uninitialized 下调用任何业务 op 返回 `AUTH_NO_PROFILE`；RegisteredLocked 下返回 `AUTH_LOCKED`；首次启动只显示账户入口（与 CORE-36 集成测试）。
- [R24] 注册流程（Fake `HttpTransport` 模拟 CORE-22/45）：获取验证码 → 注册（201 `{ account_id }`，响应中无授权码与令牌）→ 授权码 + PKCE 登录 → 换令牌 → 生成注册档案；刷新令牌在 `profile_blob` 中只以包装密文存在。
- [R25] 游客创建后全部本地功能可用；同一系统用户第二次创建游客返回 `AUTH_GUEST_EXISTS`。
- [R26] 游客状态网络白名单测试：Fake `HttpTransport` 记录全部请求，只有用户显式触发的资源包下载与更新检查，且请求不含用户内容（与 CORE-28 守卫联测）。
- [R28] 注册后默认不开启同步，用户确认开启后才产生上传请求。
- [R27] 登出后数据库已关闭、密钥已清零、`profile.logged_out` 为真，重启后停在账户入口；重新登录可打开；删除本地数据需二次确认后才执行；游客档案重启后自动打开。
- [R28] OsRandom：对两次 `fill` 返回不同字节（概率检查）；注入平台失败的替身时返回 `CRYPTO_RNG_FAILED`，且不产生全零输出；`fml-crypto` 依赖图不含 `getrandom`（CORE-21 检查），`getrandom` 只出现在 `fml-store`。

**规模**：约 485 行；主包 `crates/fml-store/src/account/`（注册表/包装密文150、状态/打开关闭130、设置40、OsRandom25、测试140），附属 `crates/fml-ffi/src/ops/account.rs`（40）；迁移SQL为数据。

