### CORE-27 备份导出与恢复

**目标**：提供用户可控的加密导出文件与离线恢复；恢复失败时原库保持不变。

**范围**
- 包含：导出范围与表映射、`.fmlbackup` 容器格式、导出后自检、两阶段恢复（准备 → 用户确认 → 提交）、合并与替换规则、临时文件清理、FFI op。
- 不包含：迁移前本地备份（CORE-13）；服务端备份（CORE-43）；保存位置与文件选择（CORE-04 `FileExporter`、`DocumentPicker`，由界面 CORE-36 调用）；识别历史与已安装内容包（不导出，见实现约束）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-13、CORE-17、CORE-21、CORE-23

**接口契约**

```rust
// crates/fml-store/src/backup/mod.rs
pub struct ExportScope { pub formulas: bool, pub study: bool, pub units: bool, pub plans: bool, pub settings: bool }  // 默认全为 true；五项全 false → BACKUP_SCOPE_INVALID
pub enum ExportProtection { Password(String) /* CORE-21 口令策略 + Argon2id */, RecoveryCode(String) /* 仅注册用户；CORE-21 recovery_key */ }
pub struct ExportManifest { pub format_version: u16 /* 1 */, pub schema_version: u32, pub app_version: String,
                            pub created_at_ms: i64, pub scope: ExportScope,
                            pub closure_added: BTreeMap<String, u64> /* 外键闭包自动带出的行数，按表名；无则空 */,
                            pub row_counts: BTreeMap<String, u64> /* 范围行按表名，闭包行按 "表名#closure" */,
                            pub payload_len: u64, pub payload_blake3: [u8; 32], pub header_blake3: [u8; 32] }
// 落盘位置见下“字节协议”：块 0 存 format_version/schema_version/app_version/created_at_ms/scope/closure_added/header_blake3，末块存 row_counts/payload_len/payload_blake3；verify 与 prepare_restore 读完两处后合成本结构
pub fn export(store: &Store, scope: &ExportScope, prot: &ExportProtection, rng: &mut dyn SecureRandom, out_path: &Path, cancel: &CancelFlag) -> Result<ExportManifest, FmlError>; // rng 取文件密钥、盐与每块 nonce；由 FFI 适配传入 CORE-23 OsRandom
pub fn verify(file: &Path, prot: &ExportProtection, cancel: &CancelFlag) -> Result<ExportManifest, FmlError>;   // 完整解密并校验，不写库
pub enum RestoreMode { Merge, Replace }
pub struct RestorePreview { pub manifest: ExportManifest, pub mode: RestoreMode, pub inserts: BTreeMap<String, u64>,
                            pub kept_local: u64 /* 合并时两端同主键、保留本地的行数 */, pub replaced: u64 /* 替换时将删除的本地行数 */,
                            pub possible_duplicates: Vec<(FormulaItemId, FormulaItemId)>, pub missing_packs: Vec<String> }
pub struct PreparedRestore { pub token: Uuid, pub preview: RestorePreview }   // 临时库句柄由本卡在进程内按 token 保存
pub fn prepare_restore(store: &Store, file: &Path, prot: &ExportProtection, mode: RestoreMode, rng: &mut dyn SecureRandom, staging: &Path, cancel: &CancelFlag) -> Result<PreparedRestore, FmlError>; // rng 只用于临时库的随机 DbKey
pub fn commit_restore(store: &Store, token: Uuid) -> Result<RestoreReport, FmlError>;
pub fn discard_restore(token: Uuid) -> Result<(), FmlError>;
pub fn cleanup_staging(staging: &Path) -> Result<u32, FmlError>;   // 启动时删除遗留临时库，返回删除个数
pub struct RestoreReport { pub inserted: BTreeMap<String, u64>, pub kept_local: u64, pub replaced: u64, pub cards_replayed: u64 }
```

- 容器 `.fmlbackup`（字节序小端）：

| 段 | 内容 |
| --- | --- |
| 头 | `FMLBACK\0`（8 字节）‖ `format_version` u16 = 1 ‖ `header_len` u32 ‖ 头 CBOR：`{1: WrapRecord, 2: chunk_size = 1048576, 3: created_at_ms}`（确定性 CBOR，CORE-21 编码器） |
| 文件密钥 | 每次导出 `random_key(rng)` 生成；`WrapRecord` 的 `wrap_kind` 为 `ExportPassword`（KEK = `passphrase_key`，随机盐，默认 `KdfParams`）或 `RecoveryCode`（KEK = `recovery_key`）；`key_version = 1`（文件独立版本，不是账户轮换版本） |
| 块 | 重复：`len` u32 ‖ `Sealed` 字节（`seal_with_rng`）；明文 ≤ 1 MiB；块号从 0 连续递增；AAD = `aad_cbor` `{domain: "backup.chunk"（块 0 与数据块）或 "backup.final"（唯一末块）, entity_id: 块号十进制, key_version: 1, format_version: 1}` |
| 明文流 | 块 0 = 清单 CBOR；块 1…N−2 = 负载流的连续切片；块 N−1 = 末块（尾部 CBOR）。负载流为一串“表段”：`[表名, [列名…], kind]`（kind：0 = 范围行，1 = 外键闭包行），接着每行一个 CBOR 数组（SQLite 值 → null / 整数 / 浮点 / 文本 / 字节串），每段以 `null` 结束 |

- 字节协议（ADR-V5-44；整数小端，CBOR 一律为 CORE-21 的确定性编码，键升序、最短整数）：
  - 头段 `header_blake3` = BLAKE3(头 CBOR 字节)，不含魔数、`format_version`、`header_len`；头 CBOR 键：`1` WrapRecord（bstr）、`2` chunk_size（uint，1048576）、`3` created_at_ms（int）。
  - 块 0 明文 = 清单 CBOR：`1` format_version、`2` schema_version、`3` app_version（tstr）、`4` created_at_ms、`5` scope（map：`1` formulas、`2` units、`3` study、`4` plans、`5` settings，值 bool）、`6` closure_added（map tstr→uint，无则空 map）、`7` header_blake3（bstr 32）。
  - 数据块：负载流按 1 MiB 切片，除最后一片外每片恰为 1 MiB；负载流为空则没有数据块（块 0 后直接是末块）。
  - 末块（AAD domain `backup.final`）明文 = 尾部 CBOR：`1` row_counts（map tstr→uint，范围行键为表名，闭包行键为 "表名#closure"）、`2` payload_len（uint，负载流总字节数）、`3` payload_blake3（bstr 32，BLAKE3(负载流全部字节)，即数据块明文按块号拼接）、`4` block_count（uint，含块 0 与末块）。
  - 解析：先读块 0，再顺序读至 AAD 为 `backup.final` 的块；块号与 AAD 不符、末块之后仍有字节、未见末块即文件结束、`block_count`、`payload_len`、哈希或行数不符 → `BACKUP_CORRUPT`。
  - 固定字节向量 BK-V1（`crates/fml-store/tests/vectors/backup_v1.hex`）：`FixedRandom`、固定 `now_ms`、固定口令与最小 KDF 测试参数、含两张小表的库；头、块 0、一个数据块、末块的期望字节由独立于实现的 RFC 8949 编码与 CORE-21 KV 向量方法人工计算并双人复核，不由被测实现生成。
- 负载不落明文临时文件：导出时从 `ReadTx` 快照逐行编码、分块加密写入 `out_path`（调用方传入 `StoreArea.staging` 下路径，随后由 Dart 经 `FileExporter.saveAs` 流式保存并删除）；恢复时逐块解密直接插入临时库。
- 导出范围与外键闭包（ADR-V5-44）：所选范围的表整表导出；若所选行经外键引用了未选范围（不含“永不导出”）的父行，这些**被引用的父行**自动随导出带出（沿 `PRAGMA foreign_key_list` 向父表方向传递闭包，只含被引用行），在负载中作为 kind = 1 的闭包段写在所有范围段之前、父表在前，并计入 `closure_added` 与 `row_counts["表名#closure"]`。典型：只选 `study` 时带出被引用的 `formula_item`、`formula_revision`、`symbol_binding`；选 `formulas` 时带出被引用的 `user_unit`。若闭包需要“永不导出”表中的行 → `BACKUP_SCOPE_INVALID`（实现错误，由往返测试覆盖）。界面在范围选择处显示“将同时带出被引用的 N 条公式/单位”。
- 导出范围与表（固定顺序，父表在前）：

| 范围 | 表 |
| --- | --- |
| `formulas` | `formula_item`、`formula_revision`、`symbol_binding`、`notation_profile`、`constant_set`、`derivation`、`calculation_plan` |
| `units` | `user_unit` |
| `study` | `book`、`study_card`、`review_event`、`study_session`、`attempt`、`confusable_group` |
| `plans` | `study_plan` |
| `settings` | `local_setting` 中 `syncable = 1` 的行（`device.*` 不导出） |
| 永不导出 | `schema_migration`、`sync_*`、`tombstone`、`field_clock`、`push_batch`、`merge_choice`、`account_*`、`upgrade_journal`、`installed_pack`、识别相关表、`mastery_cache`、`stats_cache`、`formula_fts`、`formula_draft` |

- 准备恢复 6 步：① 读头、解包文件密钥（失败 → `BACKUP_WRONG_SECRET`）；② 解密块 0，核对 `header_blake3`；③ `schema_version > SCHEMA_VERSION` → `BACKUP_SCHEMA_TOO_NEW`；④ 在 `staging` 用随机 `DbKey` `Store::open` 新临时库（迁移到当前版本），按列名插入负载（迁移只增不删，旧备份缺少的新列取默认值；出现当前 schema 没有的列 → `BACKUP_CORRUPT`）；⑤ 核对 `payload_blake3`、行数与末块标记、`integrity_check` 与外键检查；⑥ 计算 `RestorePreview`。任一步失败删除临时库，原库未被写入。
- 提交（单个 `Store::write` 事务，ATTACH 临时库）：
  - `Replace`：删除本地属于所选范围的表的全部行，再整表插入；kind = 1 的闭包行**按 Merge 处理**（只插入本地缺失行，主键已存在时保留本地行并计入 `kept_local`），不删除本地其余公式或单位；
  - `Merge`：不可变表（`formula_revision`、`review_event`、`attempt`）按主键插入缺失行；可变表主键已存在时保留本地行（计入 `kept_local`），不存在时插入；用户自建公式规范 AST 哈希相同但 ID 不同只列入 `possible_duplicates`，不自动合并；
  - 两种模式下插入的行都经 `enqueue_outbox`（同步开启时上传）；有新 `review_event` 的卡片用 CORE-17 `replay` 重算 `study_card` 调度；清空 `mastery_cache` 与 `stats_cache`（CORE-20 缺缓存时全量重算）；`formula_fts` 由 CORE-14 触发器维护。
  - 提交成功或失败后都删除临时库；`token` 30 min 未提交自动丢弃。
- FFI op（适配层向 `export` 与 `prepare_restore` 传入 CORE-23 的 OsRandom，不经 JSON）。submit（长任务，经 CORE-03 提交）：`backup.export` `{ scope, protection, out_path }` → `{ manifest }`（可取消）；`backup.verify` `{ path, protection }` → `{ manifest }`（可取消）；`backup.prepare_restore` `{ path, protection, mode }` → `{ token, preview }`（可取消）；`backup.commit_restore` `{ token }` → `{ report }`（**submit**；取消只在提交事务开始前生效，事务开始后不可取消，结果以报告返回）。call（快速调用）：`backup.discard_restore` `{ token }` → `{}`。`BACKUP_SCOPE_INVALID` 在创建输出文件与 KDF 之前检查。口令与恢复码只出现在请求中，不进日志。
- 错误码：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `BACKUP_CORRUPT` | error | 否 | 魔数或版本不符、块认证失败、块序号或末块标记不符、哈希或行数不符、未知列、完整性或外键检查失败 |
| `BACKUP_WRONG_SECRET` | error | 是 | 文件密钥解包失败（口令或恢复码不对）；恢复码格式错误时先报 `CRYPTO_RECOVERY_CODE_FORMAT` |
| `BACKUP_SCHEMA_TOO_NEW` | error | 否 | 备份的 `schema_version` 大于本程序 `SCHEMA_VERSION`（提示升级应用） |
| `BACKUP_REPLACE_BLOCKED_BY_SYNC` | error | 否 | 当前档案已开启同步时请求 `Replace`（须先关闭同步，或改用 `Merge`） |
| `BACKUP_DISK_FULL` | error | 是 | 导出前 `staging` 所在卷可用空间 < 库文件大小，或恢复前 < 备份文件 3 倍 |
| `BACKUP_TOKEN_UNKNOWN` | error | 否 | `commit_restore` / `discard_restore` 的 token 不存在或已过期 |
| `BACKUP_PROTECTION_UNAVAILABLE` | error | 否 | 游客或未保存恢复码的账户选择 `RecoveryCode` 保护 |
| `BACKUP_SCOPE_INVALID` | error | 否 | `ExportScope` 五项全为 false，或外键闭包需要“永不导出”表中的行 |

backup.export在创建输出文件/耗时KDF之前校验check_passphrase_policy，失败返回CORE-21 CRYPTO_PASSPHRASE_WEAK且不生成部分文件；CORE-47只做两次输入一致与错误呈现。

**实现约束**
- 识别历史不导出：其图片资产归 CORE-32 管理且有保留上限，V1 备份只覆盖用户数据（R27）；已安装内容包不导出，恢复后预置内容派生 ID（CORE-05 的 pack_item_id/card_id）在重新安装对应包后自动关联，`missing_packs` 列出需要重新安装的包。
- 导出完成后立即对输出文件调用 `verify`，失败则删除文件并报原错误码。
- 导出时用户再次确认范围；口令保护须通过 CORE-21 `check_passphrase_policy`。
- 应用启动时调用 `cleanup_staging`。
- 外部前提：无新增第三方依赖（加密、CBOR、BLAKE3 已由 CORE-21、CORE-05 引入）。

**验收标准**
- [R27] 往返：随机生成含公式、修订、事件、单位、计划、设置的库，导出 → 新库 `Replace` 恢复，所选范围各表逐行一致，未选范围与永不导出的表为空。
- [R27] 范围闭包往返：①只导出 `study`：恢复到不含公式的空库后外键检查通过，`closure_added` 与 `row_counts["…#closure"]` 等于被引用的公式行数，未被引用的公式不在文件中；②含用户单位的公式（只选 `formulas`）带出被引用的 `user_unit`；③在已有其他本地公式的库上 `Replace` 只恢复 `study`：本地其余公式与单位仍在，闭包行与本地同主键时保留本地；④五项全 false 报 `BACKUP_SCOPE_INVALID` 且不创建输出文件。
- [R19] 字节协议：BK-V1 固定向量与实现输出逐字节相同；`commit_restore` 为 submit，取消在事务开始前使原库字节不变，事务开始后不再响应取消；末块后追加字节、缺末块、块号乱序、`block_count` 或 `payload_len` 被改均报 `BACKUP_CORRUPT`。
- [R27] 合并：两库有公共与各自独有的数据，`Merge` 后不可变表为两端并集、可变表冲突保留本地、规范 AST 相同的自建公式出现在 `possible_duplicates`、受影响卡片调度与对全部事件 `replay` 的结果一致。
- [R19] 篡改：分别翻转头、块 0、中间块、末块各 1 字节，删除末块，交换两块顺序，均报 `BACKUP_CORRUPT`（头中 WrapRecord 被改报 `BACKUP_WRONG_SECRET`）；错误口令报 `BACKUP_WRONG_SECRET`；以上情况与提交前取消、`discard_restore` 后，原库文件字节不变、`staging` 无遗留。
- [R19] 兼容：用 schema 版本较旧的固定样例备份（`crates/fml-store/tests/fixtures/backup_v1_schema<N>.fmlbackup`，随每次新增迁移保留）恢复成功；人为提高 `schema_version` 的样例报 `BACKUP_SCHEMA_TOO_NEW`。
- [R28] 密钥轮换（CORE-24 `rotate_account_key`）后，旧备份仍可用导出时的恢复码或口令恢复（文件密钥与账户密钥无关）。
- [R26] 已开启同步时 `Replace` 报 `BACKUP_REPLACE_BLOCKED_BY_SYNC`；`Merge` 插入的行全部出现在 `sync_outbox`。
- [R25] 游客可用口令导出与恢复，过程无网络请求（Fake `HttpTransport` 审计）。

- [R19][R28] 导出后解析WrapRecord.key_version=1，backup.chunk/final AAD也为1；两种包装均可导入；任意改成0的包装按CORE-21拒绝，不生成自拒绝文件。

**规模**：约 490 行；`crates/fml-store/src/backup/`（同属 fml-store crate；闭包计算与字节协议约 +40 行）。

