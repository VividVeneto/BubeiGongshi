### CORE-15 资源包格式、验签与安装

**目标**：定义与程序剥离的通用资源包格式，并在两端以同一实现完成验签、安全解包、原子激活与防回滚。

**范围**
- 包含：包格式与 manifest、Ed25519 签名与条目哈希、安装 7 步、解包安全检查、激活指针与崩溃恢复、防降级与安全高水位、在线更新元数据校验、离线导入、包内资源读取 API、`pack.*` 处理与向 CORE-56 推送 Pack 层（`crates/fml-ffi/src/ops/pack.rs`）。
- 不包含：包内容的制作与签名流水线（CORE-16）；包下载的 HTTP 调用（平台卡与 CORE-43 提供地址）；模型推理（CORE-35）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-13、CORE-14、CORE-56

**接口契约**

包文件 `<pack_id>-<pack_version>.fmlpack`：受限 ZIP，内含 `manifest.json`、`manifest.sig`、`entries/…`。

```json
{
  "format_version": 1,
  "pack_id": "content-university-physics",
  "pack_version": "1.0.0",
  "security_epoch": 1,
  "key_id": "fml-pack-2026-a",
  "min_app_version": "1.0.0",
  "min_core_version": 1,
  "engine_abi_major": 1,
  "ast_schema": 1,
  "subject": "physics",
  "education_level": "university",
  "dependencies": [{"pack_id": "bootstrap-pack", "min_version": "1.0.0"}],
  "entries": [{"path": "items/mechanics.json", "type": "formula_items", "size": 12345,
               "blake3": "…", "logical_id": "phys.mech"}],
  "source_licenses": [{"source": "self-authored", "license": "CC-BY-4.0", "scope": "all"}],
  "provenance": [{"tool": "fml-content", "version": "1.0.0", "reviewed_by": "…"}]
}
```

```rust
// crates/fml-pack/src/lib.rs
pub struct TrustRoot { pub keys: Vec<(String /* key_id */, [u8; 32] /* Ed25519 公钥 */)> } // 编译进程序，不随包下发
pub struct InstalledPack { pub pack_id: String, pub pack_version: String, pub security_epoch: u32, pub dir: PathBuf, pub content_hash: [u8; 32] }
pub struct Manifest {                       // 字段与上面 JSON 一一对应；未知字段拒绝（PACK_INCOMPATIBLE）
    pub format_version: u16, pub pack_id: String /* ^[a-z0-9-]{3,64}$ */, pub pack_version: semver::Version,
    pub security_epoch: u32, pub key_id: String, pub min_app_version: semver::Version, pub min_core_version: u32,
    pub engine_abi_major: u16, pub ast_schema: u16, pub subject: String, pub education_level: String /* high_school | university | any */,
    pub dependencies: Vec<PackDep>, pub entries: Vec<ManifestEntry>,
    pub source_licenses: Vec<SourceLicense>, pub provenance: Vec<ProvenanceRecord>,
}
pub struct PackDep { pub pack_id: String, pub min_version: semver::Version }
pub struct ManifestEntry { pub path: String, pub r#type: EntryType, pub size: u64, pub blake3: [u8; 32] /* JSON 中为 64 位小写十六进制 */, pub logical_id: String }
pub enum EntryType { FormulaItems, Units, Notation, Constants, Fonts, Model, Lexicon, Metadata }   // JSON 为蛇形小写
pub struct SourceLicense { pub source: String, pub license: String /* SPDX 标识 */, pub scope: String }
pub struct ProvenanceRecord { pub tool: String, pub version: String, pub reviewed_by: String }
pub struct EntryReader { /* impl std::io::Read；读到 EOF 时比对 BLAKE3，不符返回 PACK_HASH_MISMATCH */ }
pub struct SecurityState { pub max_epoch: u32, pub last_timestamp_version: u64, pub last_snapshot_version: u64, pub last_seen_ms: i64 }
pub struct UpdateMetadata { pub root: Vec<u8>, pub timestamp: Vec<u8>, pub snapshot: Vec<u8>, pub targets: Vec<u8> }   // 四个角色的原始 JSON
pub struct PackOffer { pub pack_id: String, pub pack_version: semver::Version, pub security_epoch: u32,
                       pub url_path: String /* 相对 CDN 根，如 packs/<pack_id>/<version>.fmlpack */, pub size: u64, pub blake3: [u8; 32],
                       pub subject: String, pub education_level: String }
pub fn verify_manifest(manifest: &[u8], sig: &[u8], root: &TrustRoot) -> Result<Manifest, FmlError>;
pub fn install(file: &Path, packs_root: &Path, root: &TrustRoot, meta: &PackMetaStore, cancel: &CancelFlag) -> Result<InstalledPack, FmlError>;
pub fn recover(packs_root: &Path, meta: &PackMetaStore) -> Result<Vec<InstalledPack>, FmlError>;  // 启动时清理 staging 与半成品
pub fn open_entry(pack: &InstalledPack, logical_id: &str) -> Result<EntryReader, FmlError>; // 读取时再校验哈希
pub fn verify_update_metadata(meta: &UpdateMetadata, root: &TrustRoot, now_ms: i64, last_seen: &SecurityState) -> Result<Vec<PackOffer>, FmlError>;
pub type UninstallHook = Box<dyn Fn(&str /* pack_id */) -> Result<(), FmlError> + Send + Sync>;
pub fn add_uninstall_hook(hook: UninstallHook);   // pack.uninstall 删除版本目录前按登记顺序调用；任一钩子出错则中止卸载并返回该错误
```

- 安装步骤：① 写入 staging 并校验长度与整包哈希；② 先读 ≤ 1 MiB 的 manifest 并以内置公钥验签；③ 校验 format/app/core/ABI/AST 版本、依赖无环、`security_epoch` 不低于已记录值、`pack_version` 不低于已安装版本；④ 检查限额：条目 ≤ 10000、压缩后 ≤ 256 MiB、解压后 ≤ 512 MiB、单条目 ≤ 128 MiB（模型包例外须经 ADR）、压缩比 ≤ 100；⑤ 流式解压并逐条校验 BLAKE3；⑥ 写入按内容哈希命名的只读版本目录与完成标记并 fsync；⑦ 原子替换 `active.json` 指针并写 `installed_pack`。任一步失败保留旧包。
- 路径拒绝规则：绝对路径、`..`、盘符与 UNC、混用分隔符、重复路径、大小写冲突、NTFS 备用数据流、Windows 保留设备名、符号链接与重解析点。包内禁止 `.so`、`.dll`、`.exe`、脚本与模型自定义算子库。
- 在线更新元数据：服务端发布带 root/targets/snapshot/timestamp 角色的 TUF 风格元数据，timestamp 有效期 ≤ 7 天；使用成熟 TUF 客户端实现，不自研协议；过期或时钟异常时暂停在线更新，已安装内容照常可用。
- 回滚：内容回滚只允许回到本机已验证、未吊销、同 `security_epoch` 的上一可用版本；拒绝远端旧包。
- 引擎层：第 ⑥ 步后读取新包的 `units`/`notation`/`constants`/`fonts` 条目（CORE-56 引擎数据格式），连同现有层调用 CORE-56 `compose` 试合成，失败按该 `ENGINE_DATA_*` 错误拒绝安装并保留旧包；⑦ 成功后 `set_layer(LayerSource::Pack)`。`pack.recover` 对每个已激活包同样设置层，`pack.uninstall` 删除目录前 `remove_layer`。不含引擎条目的包不设层。
- FFI op：`pack.install`（长任务，请求 `{"file": "<staging 内绝对路径>", "expected_size"?: u64, "expected_blake3"?: "<64 位十六进制>"}`，在线安装由 CORE-51 按 PackOffer 填入，离线导入省略，此时只靠签名与条目哈希；响应 InstalledPack）、`pack.list`（响应 `[InstalledPack]`）、`pack.uninstall`（请求 `{pack_id}`；bootstrap 包与被依赖的包拒绝，返回 `PACK_DEP_MISSING`）、`pack.check_updates`（请求 UpdateMetadata 四个角色的 base64，由平台卡下载；响应 `[PackOffer]`，并持久化新的 SecurityState）、`pack.recover`（启动时调用，响应 `[InstalledPack]`）。
- 表（本卡 `crates/fml-pack/migrations/0001_pack_meta.sql`）：`installed_pack`（`pack_id TEXT PK`，`pack_version TEXT NOT NULL`，`security_epoch INTEGER NOT NULL`，`content_hash TEXT NOT NULL`，`dir TEXT NOT NULL`（相对 `StoreArea.packs`），`manifest_json TEXT NOT NULL`，`installed_at_ms INTEGER NOT NULL`，`previous_version TEXT`）；SecurityState 存设备级 PackMetaStore（下述约定），绝不存账户 local_setting。
- 错误码（触发条件）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `PACK_SIG_INVALID` | error | 否 | manifest 签名验证失败 |
| `PACK_KEY_UNKNOWN` | error | 否 | `key_id` 不在 TrustRoot 中 |
| `PACK_HASH_MISMATCH` | error | 否 | 整包长度或哈希、条目 BLAKE3 与声明不符（含读取时复验） |
| `PACK_DOWNGRADE` | error | 否 | `pack_version` 低于已安装版本 |
| `PACK_EPOCH_ROLLBACK` | error | 否 | `security_epoch` 低于生效高水位 `max_epoch`；TUF 元数据版本号回退 |
| `PACK_INCOMPATIBLE` | error | 否 | `format_version`、`min_app_version`、`min_core_version`、`engine_abi_major`、`ast_schema` 不满足，或 manifest 含未知字段 |
| `PACK_DEP_MISSING` | error | 否 | 依赖包未安装或版本不足、依赖成环；卸载被依赖的包 |
| `PACK_LIMIT_EXCEEDED` | error | 否 | 超过第 ④ 步任一限额，或 manifest 超过 1 MiB |
| `PACK_UNSAFE_PATH` | error | 否 | 命中路径拒绝规则 |
| `PACK_FORBIDDEN_ENTRY` | error | 否 | 包含禁止的文件类型（按扩展名与魔数双重判断） |
| `PACK_METADATA_EXPIRED` | error | 否 | timestamp 超过有效期，或本机时间早于 `last_seen_ms` 超过 24 h |

- 启动恢复钩子（order 10）由 CORE-51 的 Dart 安装点 `installPacks` 向 CORE-04 FeatureRegistry 登记：调用 `pack.recover`；bootstrap 包缺失时以随应用分发的签名 bootstrap 包调用 `pack.install`；再 `pack.list` 刷新 PackService 状态。CORE-36 只调度已登记回调；S2/S3 未登记时引擎只用 CORE-56 内置层。

```rust
pub struct PackMetaStore { /* root(StoreArea.packs)/pack_meta.db，设备级 SQLite，无用户内容 */ }
impl PackMetaStore { pub fn open(root: &Path) -> Result<Self,FmlError>; }
```
installed_pack 与 SecurityState 归此库，全设备共用，账户切换不复制。首次离线且尚无账户时先用 CORE-56 的编译期数据；order 10 钩子打开此库，并在缺失时安装内置签名 bootstrap-pack。高水位：SecurityState 另以 `StoreArea.packs/security_state.json`（schema=1，字段同 SecurityState）镜像，先写临时文件、刷盘后原子替换，再事务更新 pack_meta.db 与 active.json；生效高水位 = 库中值、镜像与已验证安装目录中 manifest 最大 security_epoch 的逐字段 max。`security_state.json` 不进入任何备份或回滚集合（WIN-16 只回滚 pack_meta.db 及其 WAL/SHM），因此恢复旧库不会降低高水位；两处都丢失时由已安装 manifest 推出 epoch 下限，TUF 版本号重新从已信任 root 开始，仍须通过签名与有效期校验。威胁边界：防备份恢复与程序回滚造成的降级，不防能任意改写本机应用数据目录的攻击者。`recover` 依据完成标记与 active.json 修正 installed_pack：指向的目录不完整，或其 min_app_version/min_core_version 高于当前程序时，回退到 previous_version 的完整目录，都不可用时回退到内置 bootstrap；修正不降低高水位。active.json 临时文件写入并刷盘后原子替换；失败保留旧可用指针。

安装只更新设备目录与 meta，不遍历账户库。PackCatalog（CORE-14）适配器由本卡安装点提供，账号库打开/首次查询时发现 catalog generation 变化，才按 CORE-14 规则刷新该账户的只读投影。

TUF 适配核实状态（A-32）：当前 `verify_update_metadata(now_ms)` 与 tough 内部时钟/datastore 的可替换性没有完成验证；此函数不能作为已闭合 sans-I/O 签名编码。M0须锁定tough版本并用官方源码验证load/expiration/datastore/逐版root轮换，提交可运行适配fixture后修订签名；在此之前CORE-15在线更新部分为外部前提阻断，不得关过期检查或自研TUF绕过。离线包验签不受此未决项阻止。

**实现约束**
- 验签在解包之前完成；bootstrap 包虽随安装包内置，也经同一加载器验签。
- 开发构建可加载未签名包，发布构建编译期移除该路径。
- 激活后旧版本目录在无读者句柄时才删除；Windows 上重命名失败时保留旧指针，延迟到下次启动激活。
- 外部前提：`ed25519-dalek`、`blake3`、`zip`（只用读取与存储/deflate）、`semver`、TUF 客户端 `tough` crate，版本按 ADR-V5-15 由首张使用卡开工时锁入 `Cargo.lock`；TrustRoot 公钥与私钥保管流程由 CORE-16 与 CORE-43 提供，发布前须登记首个 `key_id`。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-15_TEST.md](../Test/core/S4_CORE-15_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 500 行；主包 `crates/fml-pack/`（约 450 行），附属：领域表迁移 `crates/fml-pack/migrations/0001_pack_meta.sql` 与仓储 `crates/fml-pack/src/meta.rs`（约 20 行，DDL 不计）、op 处理与 Pack 层推送 `crates/fml-ffi/src/ops/pack.rs`（约 30 行）。

