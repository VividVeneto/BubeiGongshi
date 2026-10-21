### CORE-27 备份格式、导出与校验

**目标**：提供用户可控的加密导出、共享容器字节协议与完整校验，供恢复层复用。

**范围**
- 包含：导出范围/闭包与表映射、.fmlbackup容器/编码解码公共层、export/verify、导出后自检与导出临时文件清理、backup.export/verify处理。
- 不包含：准备/提交/丢弃恢复、合并替换和恢复staging生命周期（CORE-84，下游说明，非契约）；迁移前本地备份、服务端备份、文件选择；识别历史与内容包不导出。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-05、CORE-13、CORE-21、CORE-23

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
// 落盘位置见下字节协议；verify读完块0与末块合成ExportManifest。恢复消费者复用本卡共享解码层，不复制加密/格式逻辑。
pub fn export(store: &Store, scope: &ExportScope, prot: &ExportProtection, rng: &mut dyn SecureRandom, out_path: &Path, cancel: &CancelFlag) -> Result<ExportManifest, FmlError>; // rng 取文件密钥、盐与每块 nonce；由 FFI 适配传入 CORE-23 OsRandom
pub fn verify(file: &Path, prot: &ExportProtection, cancel: &CancelFlag) -> Result<ExportManifest, FmlError>;   // 完整解密并校验，不写库
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
- 负载不落明文临时文件：导出从ReadTx快照逐行编码、分块加密至调用方传入的StoreArea.staging/out_path，Dart经FileExporter.saveAs流式保存后删除；共享解码器按块/行流式交付已认证负载，不在本卡实施恢复写库。
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

- FFI op唯一登记：submit `backup.export` `{scope, protection, out_path}`→`{manifest}`、`backup.verify` `{path, protection}`→`{manifest}`，均可取消；本卡fml-ffi适配向export传CORE-23 OsRandom，不经JSON。BACKUP_SCOPE_INVALID在创建输出文件与KDF之前检查；口令/恢复码只在请求中，不进日志。恢复op由CORE-84（下游说明，非契约）登记。
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
- 识别历史不导出：图片资产/保留清理由识别历史所有者管理，V1只覆盖R27用户数据；已安装内容包不导出。预置内容派生ID依CORE-05 pack_item_id/card_id保持稳定，恢复消费者据此生成missing_packs。
- 导出完成后立即对输出文件调用 `verify`，失败则删除文件并报原错误码。
- 导出时用户再次确认范围；口令保护须通过 CORE-21 `check_passphrase_policy`。
- 导出取消/自检失败清理本卡部分输出；恢复staging启动清理由CORE-84（下游说明，非契约）承担，不混淆两类临时文件。
- 外部前提：无新增第三方依赖（加密、CBOR、BLAKE3 已由 CORE-21、CORE-05 引入）。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-27_TEST.md](../Test/core/S6_CORE-27_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约500行；crates/fml-store/src/backup/的范围闭包、字节协议、共享编码解码、export/verify及本卡编写的crates/fml-ffi/src/ops/backup_export.rs适配；不含恢复/合并代码，不计DDL/schema/资源数据、生成物、自测及夹具。若编码超出500而总量不超800，按范围闭包/格式校验二级边界分阶段，不隐去附属op行。
