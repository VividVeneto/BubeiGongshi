### CORE-66 同步快照与密钥轮换编排

**目标**：同步快照与密钥轮换编排，与原卡分开实施与验收。

**范围**
- 包含：快照构建/应用、旧事件重新包装与轮换事务。
- 不包含：依赖卡已定义的业务算法、存储与平台能力；不修改其契约。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-13、CORE-21、CORE-24、CORE-25、CORE-26、CORE-56、CORE-68、CORE-78

**接口契约**

```rust
pub struct SnapshotManifest { pub chunk_count: u32 /* 1..=256 */, pub total_bytes: u64 /* ≤ 64 MiB */,
                              pub chunk_hashes: Vec<[u8; 32]> /* 每个分片文件的 SHA-256，与 CORE-25 commit 的 chunk_hashes 同口径 */,
                              pub covers_through: String, pub key_version: u32 }
pub fn reencrypt_for_rotation(store: &Store, registry: &EntityRegistry, new_version: u32) -> Result<u32 /* 入队条数 */, FmlError>;
// 分片写入/读取 StoreArea.staging 下的目录，不经 JSON 传大块数据（ADR-V5-45）
pub fn build_snapshot(store: &Store, registry: &EntityRegistry, rng: &mut dyn SecureRandom, staging: &Path, out_dir: &Path, cancel: &CancelFlag) -> Result<SnapshotManifest, FmlError>;  // M5
pub fn apply_snapshot(store: &Store, registry: &EntityRegistry, analyzer: &dyn RemoteRevisionAnalyzer, staging: &Path, in_dir: &Path, manifest: &SnapshotManifest, cancel: &CancelFlag) -> Result<(), FmlError>; // M3
pub fn cleanup_snapshot_dirs(staging: &Path, older_than_ms: i64, now_ms: i64) -> Result<u32, FmlError>; // 删除 staging 直接子目录中超龄的 snapshot-* 目录，返回删除个数；经 sync.snapshot_cleanup 由 CORE-46 启动时调用
// staging 为 CORE-04 LocalFileStore.root(StoreArea.staging) 的绝对路径，由调用方随请求传入（ADR-V5-53），核心不保存全局暂存根
```
从 CORE-26 接收 AccountKeys/Envelope；I/O 与事务归 fml-store，领域解密/合并仍调用 fml-sync。

FFI唯一归属：sync.reencrypt、sync.snapshot_build、sync.snapshot_apply均为submit（CORE-03）；sync.snapshot_cleanup 为 device scope 同步 op，body={staging_root:string,older_than_ms:i64,now_ms:i64}、ok={removed:u32}，例 body={"staging_root":"C:/Users/u/AppData/Local/fml/staging","older_than_ms":86400000,"now_ms":1760000000000}、ok={"removed":0}；其Rust参数/返回对应上表。线类型必须使用档案handle并从已打开账户安全上下文加载AccountKeys，不能把SecretKey当普通JSON。继承CORE-03的profile_handle；build在同一Store.read快照读CORE-24密钥及全部实体；apply/reencrypt在同一个Store.write使用load_account_keys_tx读取密钥，结束清零，不沿用事务前旧keys。FFI适配只向 snapshot_build 传入 CORE-23 的 OsRandom（不经 JSON）；reencrypt不接收伪随机端口，创建新op_id由Store内部IdSource负责。reencrypt body={new_version:u32}、ok={enqueued:u32}，例 body={"new_version":2}、ok={"enqueued":0}；snapshot_build/snapshot_apply 的线格式只按下段目录协议。

快照传输协议（ADR-V5-45，取代原 base64 数组）：snapshot_build body={staging_root:string,out_dir:string}、ok={chunk_count:u32,total_bytes:u64,chunk_hashes:[64位小写hex],covers_through:string,key_version:u32}；snapshot_apply body={staging_root:string,in_dir:string,chunk_count:u32,total_bytes:u64,chunk_hashes:[hex],covers_through:string,key_version:u32}、ok={}。两者 submit（可取消）。JSON 只携带路径与清单（256 个哈希 × 67 字节 ≈ 17 KiB，加两个 ≤ 4096 字节的路径，总计 < 32 KiB），不受 CORE-03 的 16 MiB 请求上限影响。分片文件名 `chunk-0000.bin`…`chunk-0255.bin`（四位十进制，从 0 起），每个文件格式见下段“快照分片格式”，≤ 4 MiB；总量 ≤ 64 MiB；目录内只出现 `chunk-NNNN.bin`。`out_dir`/`in_dir` 必须是 `staging_root` 的直接子目录且名称以 `snapshot-` 开头（两者规范化后比较，staging_root 本身须为已存在的绝对目录）：`build` 要求其不存在或为空，由本卡创建，取消或失败时删除本卡已写入的分片与目录；`apply` 只读，不删除输入，由调用方（CORE-46）在成功或放弃后清理。路径不在暂存区、含符号链接或重解析点、非空 `out_dir` → `SYNC_PATH_INVALID`。CORE-46 逐分片读写文件完成上传（`PUT …/chunks/{n}`）与下载，续传以分片序号为准；`apply_snapshot` 以清单中的 `chunk_hashes` 为准。
- 错误码（本卡唯一定义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `SYNC_PATH_INVALID` | error | 否 | 目录不在 `StoreArea.staging` 下、含符号链接/重解析点，或 `build` 的 `out_dir` 非空 |
| `SYNC_SNAPSHOT_CORRUPT` | error | 否 | 分片缺失、数量/总量/哈希与清单不符、分片头或明文记录流非法、认证标签失败；业务库与 `covers_through` 游标均未修改 |

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `SYNC_KEY_MISSING` | CORE-24 | `apply_snapshot` 的 `key_version` 在本地无对应密钥：不读分片、不改库，CORE-46 按同一行引导恢复码或同步密语 |
| `CRYPTO_RNG_FAILED` | CORE-21 | `build_snapshot` 取 nonce 失败：删除已写分片与目录后返回 |

快照分片格式（format_version 1，CO-30）：
- 明文记录流：按 CORE-26 apply_pull 的拓扑顺序（user_unit、notation_profile → formula_revision → formula_item → 其余实体按 entity_type 字节升序），同类型内按 entity_id UTF-8 字节升序，逐条写 `u32 大端长度 ‖ CORE-26 负载 CBOR`（与 SY-PAYLOAD-V1 同一编码，含 clocks；墓碑为删除负载）。包含：registry 登记的全部存活可同步实体（含 merge_choice、syncable=1 的 local_setting）与未过期墓碑；不含 sync_quarantine、sync_outbox、push_batch、游标、study_session、参数与缓存。未推送的本地修改已体现在实体与字段时钟中，接收端按时钟幂等合并，之后到达的同一 op 不再改变结果。
- 切片与加密：明文流按每片 4 194 263 字节（4 MiB − 41）切分，最后一片可更短；空流也产生 1 片空明文。第 n 片文件 = CORE-21 `Sealed::to_bytes`（version=1 ‖ 24 字节 nonce ‖ 密文含 16 字节标签），nonce 经 `seal_with_rng` 由 rng 逐片取得；密钥 = `derive_subkey(AccountDataKey, KeyPurpose::SyncSnapshot, key_version)`；AAD = `aad_cbor(AadFields { domain: "sync.snapshot", account_id, entity_type: Some("snapshot_chunk"), entity_id: Some("<covers_through>/<n>/<chunk_count>"), key_version, format_version: 1 })`，n 与 chunk_count 为十进制，从而绑定片序、片数与覆盖游标，截断、重排或换片均使标签失败。记录可跨片，接收端解密全部分片并拼接后再解析；长度越界、尾部残余字节或负载 CBOR 非法均为 SYNC_SNAPSHOT_CORRUPT。
- covers_through：build 在同一读快照取 CORE-26 拉取游标行（`stream = "sync_pull"`）的 cursor，无该行时为空串（新设备从头拉增量，重复内容按时钟幂等）；apply 成功时在同一事务写该行 `cursor = covers_through`、`epoch = keys.account_epoch`。total_bytes = 全部分片文件字节之和，chunk_hashes 为各分片文件 SHA-256。
- 字节向量 SY-SNAPSHOT-V1 由本卡在 `crates/fml-store/tests/vectors/snapshot_v1/` 交付：固定账户密钥、FixedRandom、两类实体与一个墓碑，含单片与跨片（以测试专用小片长构造）两组，期望值由独立参照脚本生成，不得用被测实现生成。
- 清理：`cleanup_snapshot_dirs` 只检查 staging 直接子项中名称以 `snapshot-` 开头、本身为真实目录（非符号链接或重解析点，跳过不删）且目录修改时间早于 `now_ms − older_than_ms` 的项，递归删除时不跟随链接；CORE-46 只在启动、任何同步开始之前调用，因此不会删除正在使用的目录。

**实体所有者与原生接线**

- FFI由与CORE-26相同的组合层注入完整EntityRegistry，snapshot_apply复用CORE-26的RemoteRevisionAnalyzer适配；cancel直接借用CORE-03任务CancelFlag。registry/analyzer/cancel均非JSON字段，S6 fml-ffi接线计入本卡附属规模，不把Store/conn放入CORE-56 S1。 同样先拒绝不可用引擎、按事务自建方案→同 Arc 内置/包同 ID 精确选取，并显式传 ParseOptions { budget_ms: 100, allow_unicode: true }；ENGINE_UNAVAILABLE/NOTATION_UNBOUND 是本地分析前提 Err，整份快照与 covers_through 回滚，不改写为 SYNC_SNAPSHOT_CORRUPT 或部分隔离成功。
- build只枚举registry的可同步实体与未过期墓碑，保留原实体ID/全部FieldClock；不以备份scope表代替同步白名单，不导出会话/参数/缓存/密钥。apply验证全部分片后，在同一事务调用registry.apply，以与CORE-26相同拓扑顺序先单位/记号、后修订/条目、再其余实体；读取当前事务叠加层分析修订，不信任上传AST/validation。快照不能部分隔离后宣称完整：任一Invalid/未知实体/非法时钟导致SYNC_SNAPSHOT_CORRUPT整份回滚；存储故障/取消原样Err，游标保持旧值；成功才写covers_through。
- 轮换同一事务load_account_keys_tx校验new_version存在，再作废KeyRotated批次、清旧outbox并按registry稳定枚举/requeue_outbox重建，保持业务字段与时钟；全部重排入队成功才提交，不在中途切换对外版本。此函数只建立待加密队列，不产生新密文；真正AEAD nonce/加密由CORE-26 prepare_push完成。轮换完成必须等待实际prepare_push、上传及确认条件，不能把重排成功报告成密文已轮换；旧密钥保留到全部确认。只重排不产生虚假的本地业务修改，IdSource随机失败CRYPTO_RNG_FAILED不部分入队。账户密钥版本导入/保存仍归CORE-24。

**实现约束**
- 快照验证完整后才单事务应用并保存 covers_through 游标，失败保留旧库与游标；轮换先保存新包装再切版本，旧密钥保留到全部确认。
- 不发网络、不持有令牌；服务端上传/确认由 CORE-46（下游说明，非契约）。
- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-66_TEST.md](../Test/core/S6_CORE-66_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 470 行；主包 `crates/fml-store/src/sync/snapshot.rs`、`crates/fml-store/src/sync/rotation.rs`（约 370 行，含分片格式与清理；实体枚举与重推入队调用 CORE-13 的 list_entity_ids、requeue_outbox，不计）；附属 `crates/fml-ffi/src/ops/sync_snapshot.rs`（三个 submit op 与 snapshot_cleanup 的薄适配，约 100 行（含复用CORE-26分析适配的接线，不复制实现））。

