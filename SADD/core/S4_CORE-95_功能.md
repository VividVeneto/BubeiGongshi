### CORE-95 资源包安装、激活、恢复与引擎层接入

**目标**：组合CORE-15安全内核，实现设备级原子安装/崩溃恢复/高水位与Pack层一致更新。

**范围**
- 包含：安装七步、设备级PackMetaStore与installed_pack、SecurityState持久化/镜像、激活与回滚、读者句柄/卸载钩子；pack.install/list/uninstall/recover处理、Pack层试合成/推送、PackCatalog安装接入。
- 不包含：包格式/验签/路径与条目安全/读取内核（CORE-15）；TUF及pack.check_updates调用点/处理（CORE-96）；Dart启动聚合（CORE-51）；账户投影（CORE-14）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-13、CORE-14、CORE-15、CORE-56

**接口契约**

```rust
// crates/fml-pack/src/lib.rs；Manifest/InstalledPack/SecurityState等共享类型由CORE-15定义
pub fn install(file: &Path, packs_root: &Path, root: &TrustRoot, meta: &PackMetaStore, cancel: &CancelFlag) -> Result<InstalledPack, FmlError>;
pub fn recover(packs_root: &Path, meta: &PackMetaStore) -> Result<Vec<InstalledPack>, FmlError>;  // 启动时清理 staging 与半成品
pub type UninstallHook = Box<dyn Fn(&str /* pack_id */) -> Result<(), FmlError> + Send + Sync>;
pub fn add_uninstall_hook(hook: UninstallHook);   // pack.uninstall 删除版本目录前按登记顺序调用；任一钩子出错则中止卸载并返回该错误
pub struct PackMetaStore { /* root(StoreArea.packs)/pack_meta.db，设备级 SQLite，无用户内容 */ }
impl PackMetaStore { pub fn open(root: &Path) -> Result<Self,FmlError>; }
```

- 安装步骤：① 写入 staging 并校验长度与整包哈希；② 先读 ≤ 1 MiB 的 manifest 并以内置公钥验签；③ 校验 format/app/core/ABI/AST 版本、依赖无环、`security_epoch` 不低于已记录值、`pack_version` 不低于已安装版本；④ 检查限额：条目 ≤ 10000、压缩后 ≤ 256 MiB、解压后 ≤ 512 MiB、单条目 ≤ 128 MiB（模型包例外须经 ADR）、压缩比 ≤ 100；⑤ 流式解压并逐条校验 BLAKE3；⑥ 写入按内容哈希命名的只读版本目录与完成标记并 fsync；⑦ 原子替换 `active.json` 指针并写 `installed_pack`。任一步失败保留旧包。
- 回滚：内容回滚只允许回到本机已验证、未吊销、同 `security_epoch` 的上一可用版本；拒绝远端旧包。
- 引擎层：第 ⑥ 步后读取新包的 `units`/`notation`/`constants`/`fonts` 条目（CORE-56 引擎数据格式），连同现有层调用 CORE-56 `compose` 试合成，失败按该 `ENGINE_DATA_*` 错误拒绝安装并保留旧包；⑦ 成功后 `set_layer(LayerSource::Pack)`。`pack.recover` 对每个已激活包同样设置层，`pack.uninstall` 删除目录前 `remove_layer`。不含引擎条目的包不设层。
- FFI op：`pack.install`（长任务，请求 `{"file": "<staging 内绝对路径>", "expected_size"?: u64, "expected_blake3"?: "<64 位十六进制>"}`，在线安装由 CORE-51 按 PackOffer 填入，离线导入省略，此时只靠签名与条目哈希；响应 InstalledPack）、`pack.list`（响应 `[InstalledPack]`）、`pack.uninstall`（请求 `{pack_id}`；bootstrap 包与被依赖的包拒绝，返回 `PACK_DEP_MISSING`）、`pack.recover`（启动时调用，响应 `[InstalledPack]`）。
- 表（本卡（由CORE-15迁移） `crates/fml-pack/migrations/0001_pack_meta.sql`）：`installed_pack`（`pack_id TEXT PK`，`pack_version TEXT NOT NULL`，`security_epoch INTEGER NOT NULL`，`content_hash TEXT NOT NULL`，`dir TEXT NOT NULL`（相对 `StoreArea.packs`），`manifest_json TEXT NOT NULL`，`installed_at_ms INTEGER NOT NULL`，`previous_version TEXT`）；SecurityState 存设备级 PackMetaStore（下述约定），绝不存账户 local_setting。

- 启动恢复钩子（order 10）由 CORE-51 的 Dart 安装点 `installPacks` 向 CORE-04 FeatureRegistry 登记：调用 `pack.recover`；bootstrap 包缺失时以随应用分发的签名 bootstrap 包调用 `pack.install`；再 `pack.list` 刷新 PackService 状态。CORE-36 只调度已登记回调；S2/S3 未登记时引擎只用 CORE-56 内置层。

installed_pack 与 SecurityState 归此库，全设备共用，账户切换不复制。首次离线且尚无账户时先用 CORE-56 的编译期数据；order 10 钩子打开此库，并在缺失时安装内置签名 bootstrap-pack。高水位：SecurityState 另以 `StoreArea.packs/security_state.json`（schema=1，字段同 SecurityState）镜像，先写临时文件、刷盘后原子替换，再事务更新 pack_meta.db 与 active.json；生效高水位 = 库中值、镜像与已验证安装目录中 manifest 最大 security_epoch 的逐字段 max。`security_state.json` 不进入任何备份或回滚集合（WIN-16 只回滚 pack_meta.db 及其 WAL/SHM），因此恢复旧库不会降低高水位；两处都丢失时由已安装 manifest 推出 epoch 下限，TUF 版本号重新从已信任 root 开始，仍须通过签名与有效期校验。威胁边界：防备份恢复与程序回滚造成的降级，不防能任意改写本机应用数据目录的攻击者。`recover` 依据完成标记与 active.json 修正 installed_pack：指向的目录不完整，或其 min_app_version/min_core_version 高于当前程序时，回退到 previous_version 的完整目录，都不可用时回退到内置 bootstrap；修正不降低高水位。active.json 临时文件写入并刷盘后原子替换；失败保留旧可用指针。

安装只更新设备目录与 meta，不遍历账户库。PackCatalog（CORE-14）适配器由本卡安装点提供，账号库打开/首次查询时发现 catalog generation 变化，才按 CORE-14 规则刷新该账户的只读投影。

- SecurityState类型仍由CORE-15定义，其设备库/镜像与所有高水位写入由本卡唯一拥有，提供给CORE-96读取当前状态和原子单调发布验证后的新状态；CORE-96不直接写installed_pack或绕过本卡镜像顺序。在线版本字段由CORE-96算出，95只执行持久化，不反向依赖其TUF实现。
- 错误码不重定义：PACK_*仍唯一归CORE-15；ENGINE_DATA_*归CORE-56，其他信封错误归CORE-03。

**实现约束**
- 验签在解包之前完成；bootstrap 包虽随安装包内置，也经同一加载器验签。
- 开发构建可加载未签名包，发布构建编译期移除该路径。
- 激活后旧版本目录在无读者句柄时才删除；Windows 上重命名失败时保留旧指针，延迟到下次启动激活。
- 外部依赖与TrustRoot流程沿CORE-15；离线安装/恢复可独立交付，不能以CORE-96未决为由关闭验签或高水位。
- 聚合安装点仍由CORE-51 order10调用上述op，不迁移CORE-36平台/生命周期端口实现。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-95_TEST.md](../Test/core/S4_CORE-95_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约520行，分阶段：①安装/激活160、meta/高水位150、核心op10，共320行；②恢复/卸载120、其余op及Pack层80，共200行。主包 `crates/fml-pack/src/{install,meta,recover}.rs` 430行；附属 `crates/fml-ffi/src/ops/pack.rs` 四op/层接入90行；迁移DDL、状态数据、生成物、自测不计。①独立构建测安全安装/失败保旧/高水位，②独立构建测崩溃恢复/卸载/层一致性。check_updates接入20行已转归96，不重复。
