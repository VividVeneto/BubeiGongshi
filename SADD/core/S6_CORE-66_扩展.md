### CORE-66 同步快照与密钥轮换编排

**目标**：同步快照与密钥轮换编排，与原卡分开实施与验收。

**范围**
- 包含：快照构建/应用、旧事件重新包装与轮换事务。
- 不包含：依赖卡已定义的业务算法、存储与平台能力；不修改其契约。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-13、CORE-21、CORE-24、CORE-25、CORE-26、CORE-78

**接口契约**

```rust
pub struct SnapshotManifest { pub chunk_count: u32 /* 1..=256 */, pub total_bytes: u64 /* ≤ 64 MiB */,
                              pub chunk_hashes: Vec<[u8; 32]> /* 每个分片文件的 SHA-256，与 CORE-25 commit 的 chunk_hashes 同口径 */,
                              pub covers_through: String, pub key_version: u32 }
pub fn reencrypt_for_rotation(store: &Store, keys: &AccountKeys, rng: &mut dyn SecureRandom, new_version: u32) -> Result<u32 /* 入队条数 */, FmlError>;
// 分片写入/读取 StoreArea.staging 下的目录，不经 JSON 传大块数据（ADR-V5-45）
pub fn build_snapshot(store: &Store, keys: &AccountKeys, rng: &mut dyn SecureRandom, out_dir: &Path, cancel: &CancelFlag) -> Result<SnapshotManifest, FmlError>;  // M5
pub fn apply_snapshot(store: &Store, keys: &AccountKeys, in_dir: &Path, manifest: &SnapshotManifest, cancel: &CancelFlag) -> Result<(), FmlError>; // M3
pub fn cleanup_snapshot_dirs(staging: &Path, older_than_ms: i64, now_ms: i64) -> Result<u32, FmlError>; // 启动时删除遗留 snapshot-* 目录；CORE-46 启动时传入 older_than_ms = 24 h（86 400 000）、now_ms 取调用方时钟
```
从 CORE-26 接收 AccountKeys/Envelope；I/O 与事务归 fml-store，领域解密/合并仍调用 fml-sync。

FFI唯一归属：sync.reencrypt、sync.snapshot_build、sync.snapshot_apply均为submit（CORE-03）；其Rust参数/返回对应上表。线类型必须使用档案handle并从已打开账户安全上下文加载AccountKeys，不能把SecretKey当普通JSON。继承CORE-03的profile_handle；AccountKeys由CORE-24/26所定的单请求只读快照加载，结束清零。reencrypt body={new_version:u32}、ok={enqueued:u32}；snapshot_build body={}、ok={chunks:[base64]}；snapshot_apply body={chunks:[base64],covers_through:string}、ok={}。FFI适配向 reencrypt 与 snapshot_build 传入 CORE-23 的 OsRandom（不经 JSON）。reencrypt body={new_version:u32}、ok={enqueued:u32}，例 body={"new_version":2}、ok={"enqueued":0}。

快照传输协议（ADR-V5-45，取代原 base64 数组）：snapshot_build body={out_dir:string}、ok={chunk_count:u32,total_bytes:u64,chunk_hashes:[64位小写hex],covers_through:string,key_version:u32}；snapshot_apply body={in_dir:string,chunk_count:u32,total_bytes:u64,chunk_hashes:[hex],covers_through:string,key_version:u32}、ok={}。两者 submit（可取消）。JSON 只携带路径与清单（≤256 个哈希，约 20 KiB），不受 CORE-03 的 16 MiB 请求上限影响。分片文件名 `chunk-0000.bin`…`chunk-0255.bin`（四位十进制，从 0 起），每个文件为 CORE-26 Envelope 风格的已加密分片字节，≤ 4 MiB；总量 ≤ 64 MiB；单个目录占用不超过总量加一片。`out_dir`/`in_dir` 必须是 `StoreArea.staging` 下的目录：`build` 要求其不存在或为空，由本卡创建，取消或失败时删除本卡已写入的分片与目录；`apply` 只读，不删除输入，由调用方（CORE-46）在成功或放弃后清理。路径不在暂存区、含符号链接或重解析点、非空 `out_dir` → `SYNC_PATH_INVALID`。CORE-46 逐分片读写文件完成上传（`PUT …/chunks/{n}`）与下载，续传以分片序号为准；`apply_snapshot` 以清单中的 `chunk_hashes` 为准。
- 错误码（本卡唯一定义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `SYNC_PATH_INVALID` | error | 否 | 目录不在 `StoreArea.staging` 下、含符号链接/重解析点，或 `build` 的 `out_dir` 非空 |
| `SYNC_SNAPSHOT_CORRUPT` | error | 否 | 分片缺失、数量/总量/哈希与清单不符、认证标签失败、`key_version` 无对应密钥；业务库与 `covers_through` 游标均未修改 |

**实现约束**
- 快照验证完整后才单事务应用并保存 covers_through 游标，失败保留旧库与游标；轮换先保存新包装再切版本，旧密钥保留到全部确认。
- 不发网络、不持有令牌；服务端上传/确认由 CORE-46（下游说明，非契约）。
- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-66_TEST.md](../Test/core/S6_CORE-66_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 400 行；主包 `crates/fml-store/src/sync/snapshot.rs`、`crates/fml-store/src/sync/rotation.rs`（含测试与必要的同构建单元接缝）；附属 `crates/fml-ffi/src/ops/sync_snapshot.rs`（三个 submit op 的薄适配，约 40 行）。

