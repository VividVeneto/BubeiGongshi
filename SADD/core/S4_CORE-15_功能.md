### CORE-15 资源包格式、验签与安全读取

**目标**：定义通用资源包格式与底层验签、安全解包/读取能力；安装激活恢复由CORE-95组合，在线信任由CORE-96处理。

**范围**
- 包含：包格式/manifest与共享运行时数据类型；Ed25519签名、版本/依赖/安全限额、路径与文件类型安全、流式解包/条目哈希复验；PackCatalog底层只读适配。
- 不包含：安装七步/active指针/meta高水位/恢复卸载/pack四op与Pack层推送（CORE-95）；TUF及pack.check_updates（CORE-96）；制包签名流水线（CORE-16）；下载HTTP、模型推理。

**依赖**：CORE-01、CORE-02、CORE-14

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
pub fn open_entry(pack: &InstalledPack, logical_id: &str) -> Result<EntryReader, FmlError>; // EOF时复验BLAKE3
```

- 本卡manifest/validate/extract/reader为底层模块，可由CORE-95调用；安全校验不能由安装层复制。CORE-15不调用CORE-95/96；共享SecurityState/UpdateMetadata/PackOffer仅是数据类型，持久化与处理分别归95/96。
- 安全限额：manifest≤1MiB；条目≤10000、压缩后≤256MiB、解压后≤512MiB、单条目≤128MiB（模型例外须ADR）、压缩比≤100；按声明大小/实际流量双重检查，校验每条BLAKE3。版本兼容检查覆盖format/app/core/ABI/AST，依赖无环，拒绝远端旧包；当前版本/高水位由95传入，底层不自行打开meta。
- 路径拒绝规则：绝对路径、`..`、盘符与 UNC、混用分隔符、重复路径、大小写冲突、NTFS 备用数据流、Windows 保留设备名、符号链接与重解析点。包内禁止 `.so`、`.dll`、`.exe`、脚本与模型自定义算子库。

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

错误码全集唯一保留本卡（含生命周期与TUF触发语义）；CORE-95/96只引用透传，不重复定义。表installed_pack、SecurityState持久库/镜像的唯一所有者迁CORE-95；本卡无DDL。

**实现约束**
- 验签在解包之前完成；bootstrap 包虽随安装包内置，也经同一加载器验签。
- 开发构建可加载未签名包，发布构建编译期移除该路径。
- 包内资源读取时按logical_id映射并在EOF复验；InstalledPack共享类型不代表已执行激活，完成状态由CORE-95保证。PackCatalog只读内容访问适配与字段归本卡，账户目录打开/更新通知由CORE-95安装点衔接，CORE-14负责投影。
- 外部前提：ed25519-dalek/blake3/zip（只读及store/deflate）/semver按ADR-V5-15锁入Cargo.lock；TrustRoot与私钥流程由CORE-16/43提供，发布前登记首个key_id。TUF未决门槛完整迁CORE-96，不在本卡宣告闭合。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-15_TEST.md](../Test/core/S4_CORE-15_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约450行；主包 `crates/fml-pack/src/{manifest,validate,extract,reader,catalog}.rs`：manifest120、版本/依赖/限额80、安全解包180、读取/catalog70；无本卡FFI附属。清单/公钥/DDL/资源/生成物/自测不计。单阶段以底层验证/安全读取独立构建测试交付。原1090行另520归CORE-95、120归CORE-96。

