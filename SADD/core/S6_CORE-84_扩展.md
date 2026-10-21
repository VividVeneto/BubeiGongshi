### CORE-84 备份恢复与合并

**目标**：复用CORE-27格式/解码校验，提供准备→确认→提交的两阶段恢复，保证失败时原库不变。

**范围**
- 包含：RestoreMode/Preview/PreparedRestore/Report、prepare/commit/discard、Merge/Replace、重放、临时库/token/启动清理及三个恢复op。
- 不包含：导出范围/字节协议/加密解码/verify（CORE-27）；算法复制或新表结构；文件选择界面。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-13、CORE-17、CORE-21、CORE-23、CORE-27

**接口契约**

```rust
// crates/fml-store/src/backup/restore.rs；Store与导出共享类型分别来自CORE-13/27
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

- 准备恢复 6 步：① 读头、解包文件密钥（失败 → `BACKUP_WRONG_SECRET`）；② 解密块 0，核对 `header_blake3`；③ `schema_version > SCHEMA_VERSION` → `BACKUP_SCHEMA_TOO_NEW`；④ 在 `staging` 用随机 `DbKey` `Store::open` 新临时库（迁移到当前版本），按列名插入负载（迁移只增不删，旧备份缺少的新列取默认值；出现当前 schema 没有的列 → `BACKUP_CORRUPT`）；⑤ 核对 `payload_blake3`、行数与末块标记、`integrity_check` 与外键检查；⑥ 计算 `RestorePreview`。任一步失败删除临时库，原库未被写入。
- 提交（单个 `Store::write` 事务，ATTACH 临时库）：
  - `Replace`：删除本地属于所选范围的表的全部行，再整表插入；kind = 1 的闭包行**按 Merge 处理**（只插入本地缺失行，主键已存在时保留本地行并计入 `kept_local`），不删除本地其余公式或单位；
  - `Merge`：不可变表（`formula_revision`、`review_event`、`attempt`）按主键插入缺失行；可变表主键已存在时保留本地行（计入 `kept_local`），不存在时插入；用户自建公式规范 AST 哈希相同但 ID 不同只列入 `possible_duplicates`，不自动合并；
  - 两种模式下插入的行都经 `enqueue_outbox`（同步开启时上传）；有新 `review_event` 的卡片用 CORE-17 `replay` 重算 `study_card` 调度；清空 `mastery_cache` 与 `stats_cache`（CORE-20 缺缓存时全量重算）；`formula_fts` 由 CORE-14 触发器维护。
  - 提交成功或失败后都删除临时库；`token` 30 min 未提交自动丢弃。

- 容器、块序/AAD/末块/摘要与行数检查严格复用CORE-27；已认证行流直接插入临时库，不落明文负载文件、不另写第二套解码器。范围、闭包kind=1及永不导出表来自CORE-27，恢复不扩大范围。
- 表结构只依赖CORE-13的Store/schema与PRAGMA；CORE-17仅提供review_event后的replay算法，因此ADR-V5-50“只依赖CORE-13”限定表结构依赖，不排除CORE-17重放依赖；不新建重复迁移。
- 唯一登记op：submit `backup.prepare_restore` `{path,protection,mode}`→`{token,preview}`（可取消）、`backup.commit_restore` `{token}`→`{report}`（submit；取消只在提交事务开始前生效，事务开始后不可取消，返回最终报告）；call `backup.discard_restore` `{token}`→`{}`。本卡fml-ffi适配向prepare_restore传入CORE-23 OsRandom（仅生成临时库随机DbKey，不经JSON）；秘密不进日志。
- 同步开启时Replace拒绝；Merge插入行经enqueue_outbox上传。预置派生ID依CORE-05稳定规则，未安装包列missing_packs，重装后自动关联；识别历史/包本体仍不恢复。游客口令恢复全程无需网络，旧文件密钥不受账户轮换影响。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| BACKUP_CORRUPT、BACKUP_WRONG_SECRET | CORE-27 | 校验失败删除临时库，保留原库 |
| BACKUP_SCHEMA_TOO_NEW | CORE-27 | 版本高于SCHEMA_VERSION，提示升级 |
| BACKUP_REPLACE_BLOCKED_BY_SYNC | CORE-27 | 关闭同步或改Merge |
| BACKUP_DISK_FULL | CORE-27 | 恢复前空间小于备份3倍拒绝 |
| BACKUP_TOKEN_UNKNOWN | CORE-27 | 拒绝不存在/过期token |
| BACKUP_PROTECTION_UNAVAILABLE、BACKUP_SCOPE_INVALID | CORE-27 | 复用保护/范围策略 |
| CRYPTO_RECOVERY_CODE_FORMAT | CORE-21 | 格式先验拒绝，不伪装口令错误 |

**实现约束**
- 准备失败、提交成功/失败、取消/discard均清理临时库；应用启动调用cleanup_staging；token30min未提交自动丢弃，进程内句柄不跨进程恢复。
- 用户确认RestorePreview后才提交；单个Store.write事务ATTACH临时库，不分批破坏原子性。
- 无新增第三方依赖，加密/CBOR/BLAKE3共享CORE-27/21/05。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-84_TEST.md](../Test/core/S6_CORE-84_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约370行；crates/fml-store/src/backup/restore.rs及本卡编写的crates/fml-ffi/src/ops/backup_restore.rs，含准备/合并替换/replay接入/token清理和3op；不重复计CORE-27共享格式/校验，不计DDL/schema、生成物、自测及夹具。
