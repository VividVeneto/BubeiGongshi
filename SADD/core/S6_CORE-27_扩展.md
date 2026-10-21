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
pub fn export(store: &Store, scope: &ExportScope, prot: &ExportProtection, rng: &mut dyn SecureRandom, staging: &Path, out_path: &Path,
              now_ms: i64, app_version: &str, cancel: &CancelFlag) -> Result<ExportManifest, FmlError>;
// rng 取文件密钥、盐与每块 nonce，由 FFI 适配传入 CORE-23 OsRandom；now_ms 写入头/清单 created_at_ms 与 WrapRecord 创建时间，核心不读时钟；
// app_version 由 FFI 适配传 fml-ffi 的 CARGO_PKG_VERSION（不经 JSON）；out_path 须为 staging 的直接子项且扩展名 .fmlbackup（ADR-V5-53），否则 FFI_BAD_ARG
pub fn verify(file: &Path, prot: &ExportProtection, cancel: &CancelFlag) -> Result<ExportManifest, FmlError>;   // 完整解密并校验，不写库
```

- 容器 `.fmlbackup`（字节序小端）：

| 段 | 内容 |
| --- | --- |
| 头 | `FMLBACK\0`（8 字节）‖ `format_version` u16 = 1 ‖ `header_len` u32 ‖ 头 CBOR：`{1: WrapRecord, 2: chunk_size = 1048576, 3: created_at_ms}`（确定性 CBOR，CORE-21 编码器） |
| 文件密钥 | 每次导出 `random_key(rng)` 生成；`WrapRecord` 的 `wrap_kind` 为 `ExportPassword`（KEK = `passphrase_key`，随机盐，默认 `KdfParams`）或 `RecoveryCode`（KEK = `recovery_key`）；`key_version = 1`（文件独立版本，不是账户轮换版本） |
| 块 | 重复：`len` u32 ‖ `Sealed` 字节（`seal_with_rng`）；明文 ≤ 1 MiB；块号从 0 连续递增；AAD = `aad_cbor` `{domain: "backup.chunk"（块 0 与数据块）或 "backup.final"（唯一末块）, entity_id: 块号十进制, key_version: 1, format_version: 1}` |
| 明文流 | 块 0 = 清单 CBOR；块 1…N−2 = 负载流的连续切片；块 N−1 = 末块（尾部 CBOR）。负载流为一串“表段”：`[表名, [列名…], kind]`（kind：0 = 范围行，1 = 外键闭包行），接着每行一个 CBOR 数组（SQLite 值 → null / 整数 / 浮点 / 文本 / 字节串），每段以 `null` 结束 |

- 头解析与错误归类：头 CBOR 解码失败、`WrapRecord::from_bytes` 结构失败、`wrap_kind` 不是 `export_password`/`recovery_code` 或 `key_version ≠ 1`、KDF 参数越界 → `BACKUP_CORRUPT`（结构损坏，不提示换口令）；结构完好但请求的 `ExportProtection` 种类与 `wrap_kind` 不符，或 AEAD 解包认证失败 → `BACKUP_WRONG_SECRET`。
- 字节协议（ADR-V5-44；整数小端，CBOR 一律为 CORE-21 的确定性编码，键升序、最短整数）：
  - 头段 `header_blake3` = BLAKE3(头 CBOR 字节)，不含魔数、`format_version`、`header_len`；头 CBOR 键：`1` WrapRecord（bstr）、`2` chunk_size（uint，1048576）、`3` created_at_ms（int）。
  - 块 0 明文 = 清单 CBOR：`1` format_version、`2` schema_version、`3` app_version（tstr）、`4` created_at_ms、`5` scope（map：`1` formulas、`2` units、`3` study、`4` plans、`5` settings，值 bool）、`6` closure_added（map tstr→uint，无则空 map）、`7` header_blake3（bstr 32）。
  - 数据块：负载流按 1 MiB 切片，除最后一片外每片恰为 1 MiB；负载流为空则没有数据块（块 0 后直接是末块）。
  - 末块（AAD domain `backup.final`）明文 = 尾部 CBOR：`1` row_counts（map tstr→uint，范围行键为表名，闭包行键为 "表名#closure"）、`2` payload_len（uint，负载流总字节数）、`3` payload_blake3（bstr 32，BLAKE3(负载流全部字节)，即数据块明文按块号拼接）、`4` block_count（uint，含块 0 与末块）。
  - 解析：先读块 0，再顺序读至 AAD 为 `backup.final` 的块；块号与 AAD 不符、末块之后仍有字节、未见末块即文件结束、`block_count`、`payload_len`、哈希或行数不符 → `BACKUP_CORRUPT`。
  - 固定字节向量 BK-V1（`crates/fml-store/tests/vectors/backup_v1.hex`）：`FixedRandom`（字节序列写在向量文件头注释）、`now_ms = 1700000000000`、固定口令、CORE-21 默认 KdfParams（m_kib 65536、t 3、p 4；CORE-21 不允许更小的测试参数）、含两张小表的库；头、块 0、一个数据块、末块的期望字节由独立参考脚本 `crates/fml-store/tests/vectors/gen_backup_v1.py`（Python，argon2-cffi、PyNaCl 的 XChaCha20-Poly1305、blake3 与脚本内手写 RFC 8949 确定性编码，不调用被测 Rust 代码）生成，由第二人逐段复核 CBOR 结构与长度字段后入库；脚本与其依赖版本属测试夹具，不计规模、不进产品构建。
- 负载不落明文临时文件：导出从ReadTx快照逐行编码、分块加密至调用方传入的StoreArea.staging/out_path，Dart经FileExporter.saveAs流式保存后删除；共享解码器按块/行流式交付已认证负载，不在本卡实施恢复写库。
- 导出范围与外键闭包（ADR-V5-44）：所选范围只导出满足 CORE-13 表策略固定行过滤的行；若所选行经外键引用了未选范围（不含“永不导出”）的父行，这些**被引用的父行**自动随导出带出（沿 `PRAGMA foreign_key_list` 向父表方向传递闭包，只含被引用行），在负载中作为 kind = 1 的闭包段写在所有范围段之前、父表在前，并计入 `closure_added` 与 `row_counts["表名#closure"]`。典型：只选 `study` 时带出被引用的 `formula_item`、`formula_revision`、`symbol_binding`；选 `formulas` 时带出被引用的 `user_unit`。若闭包需要“永不导出”表中的行 → `BACKUP_SCOPE_INVALID`（实现错误，由往返测试覆盖）。界面在范围选择处显示“将同时带出被引用的 N 条公式/单位”。
- 表策略唯一来自 CORE-13 的 table_policies()：将 ExportScope 五个开关对应到 BackupScope，按 TablePolicy.scope/row_filter 选行；Never 以及不满足固定行过滤的记录不进入范围或闭包。CORE-27 不再维护表白名单、所有权、不可变类别或过滤 SQL 副本；列/约束也不从其他业务卡转录。独立设备库不属于导出数据源。
- 在同一 ReadTx 快照内，经 PRAGMA table_info 读取当前列名/列序/类型/默认值/主键序，经 PRAGMA foreign_key_list 读取完整外键分组（复合键按 id/seq 配对）；仅在 CORE-13 策略允许的 profile 表之间求被引用父行闭包。表段列名来自该快照的实际列，行值按相同列序编码；表名只取策略白名单并正确引用 SQL 标识符，不把文件表名或任意 SQL 当查询输入。未知实际表默认 Never，不因被 PRAGMA 发现而扩大 ExportScope。
- table_policies() 仅包含本构建已合入迁移的 profile 表：未来尚未合入表不要求存在、不创建；策略已声明应存在却缺失的表或固定过滤所需列按 CORE-13 返回 STORE_CORRUPT，禁止默默跳过或导出不完整文件。PRAGMA 只解决结构发现，不改变范围、包引用或闭包 kind=1 语义；预置内容仍仅按既有稳定 ID 引用并由恢复层报告 missing_packs，不借 schema 重构新增产品限制。

- FFI op唯一登记：submit `backup.export` `{scope, protection, staging_root, out_path, now_ms}`→`{manifest}`、`backup.verify` `{path, protection}`→`{manifest}`，均可取消；本卡fml-ffi适配向export传CORE-23 OsRandom，不经JSON。BACKUP_SCOPE_INVALID、BACKUP_PROTECTION_UNAVAILABLE、口令策略与 BACKUP_DISK_FULL 均在创建输出文件与KDF之前检查（磁盘可用空间探针按 CORE-13 同类接缝 #[cfg(test)] 可替换）；verify 不接收 Store、不写任何库；口令/恢复码只在请求中，不进日志。恢复op由CORE-84（下游说明，非契约）登记。
- 错误码：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `BACKUP_CORRUPT` | error | 否 | 魔数或版本不符、头或 WrapRecord 结构损坏（见“头解析与错误归类”）、块认证失败、块序号或末块标记不符、哈希或行数不符、未知列、完整性或外键检查失败 |
| `BACKUP_WRONG_SECRET` | error | 是 | 文件密钥解包认证失败（口令或恢复码不对）或保护种类与文件不符；恢复码格式错误时先报 `CRYPTO_RECOVERY_CODE_FORMAT` |
| `BACKUP_SCHEMA_TOO_NEW` | error | 否 | 备份的 `schema_version` 大于本程序 `SCHEMA_VERSION`（提示升级应用） |
| `BACKUP_REPLACE_BLOCKED_BY_SYNC` | error | 否 | 当前档案已开启同步时请求 `Replace`（须先关闭同步，或改用 `Merge`） |
| `BACKUP_DISK_FULL` | error | 是 | 导出前 `staging` 所在卷可用空间 < 库文件大小，或恢复前 < 备份文件 3 倍 |
| `BACKUP_TOKEN_UNKNOWN` | error | 否 | `commit_restore` / `discard_restore` 的 token 不存在、已过期或不属于当前档案（CORE-84（下游说明，非契约）使用） |
| `BACKUP_PROTECTION_UNAVAILABLE` | error | 否 | 游客档案（account_state 无 account_id）选择 `RecoveryCode` 保护；恢复码是否已被用户保存由 CORE-47 在提供入口前确认，本卡只校验格式（`CRYPTO_RECOVERY_CODE_FORMAT`） |
| `BACKUP_SCOPE_INVALID` | error | 否 | `ExportScope` 五项全为 false，或外键闭包需要“永不导出”表中的行 |
| `BACKUP_CANCELLED` | info | 否 | `CancelFlag` 置位：`export`/`verify` 在每个数据块前检查，导出时按下条清理部分文件；CORE-84（下游说明，非契约）的准备与提交事务开始前取消也返回本码 |

backup.export在创建输出文件/耗时KDF之前校验check_passphrase_policy，失败返回CORE-21 CRYPTO_PASSPHRASE_WEAK且不生成部分文件；CORE-47只做两次输入一致与错误呈现。

**实现约束**
- 表结构来源：业务表的列、主键与外键在运行时由 PRAGMA 读取，范围与分类只来自 CORE-13 table_policies()；本卡不依赖、也不转录各表所有者卡的 DDL（README §8.1 材料缺这些表定义属预期，R3-27-09）；预置派生 ID 只按已存列值原样导出，不调用 CORE-05 派生函数。
- 识别历史不导出：图片资产/保留清理由识别历史所有者管理，V1只覆盖R27用户数据；已安装内容包不导出。预置内容派生ID依CORE-05 pack_item_id/card_id保持稳定，恢复消费者据此生成missing_packs。
- 导出完成后立即对输出文件调用 `verify`，失败则删除文件并报原错误码。
- 导出中途任一错误（含 `CRYPTO_RNG_FAILED`、`BACKUP_CANCELLED`、写失败）删除 `out_path` 与其临时文件后返回原错误码，staging 下不留部分文件。
- 导出不触发 CORE-13 `rotate_device_id`，也不写 outbox；文件只读快照，ADR-V5-33 的整库回退检测不适用于导出（恢复侧见 CORE-84（下游说明，非契约））。
- 导出时用户再次确认范围；口令保护须通过 CORE-21 `check_passphrase_policy`。
- 导出取消/自检失败清理本卡部分输出；恢复staging启动清理由CORE-84（下游说明，非契约）承担，不混淆两类临时文件。
- 外部前提：无新增第三方依赖（加密、CBOR、BLAKE3 已由 CORE-21、CORE-05 引入）。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-27_TEST.md](../Test/core/S6_CORE-27_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约500行；crates/fml-store/src/backup/的范围闭包、字节协议、共享编码解码、export/verify及本卡编写的crates/fml-ffi/src/ops/backup_export.rs适配；不含恢复/合并代码，不计DDL/schema/资源数据、生成物、自测及夹具。若编码超出500而总量不超800，按范围闭包/格式校验二级边界分阶段，不隐去附属op行。
