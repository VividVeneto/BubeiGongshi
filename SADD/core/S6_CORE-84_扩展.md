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
pub struct PreparedRestore { pub token: Uuid, pub preview: RestorePreview }
pub struct RestoreSessions { /* 私有：token → (临时库句柄、mode、staging、started_ms) */ }   // 每个档案句柄一份，由 FFI 适配挂在 CORE-03 档案句柄资源上；无进程级全局表（ADR-V5-39）
impl RestoreSessions { pub fn new() -> Self; }   // Drop 时关闭并删除全部临时库；close_profile/登出释放档案句柄即丢弃
pub struct RestoreContext { pub now_ms: i64, pub day: StudyDay }   // StudyDay 来自 CORE-17；核心不读时钟
pub fn prepare_restore(store: &Store, sessions: &mut RestoreSessions, file: &Path, prot: &ExportProtection, mode: RestoreMode, rng: &mut dyn SecureRandom,
                       staging: &Path, now_ms: i64, cancel: &CancelFlag) -> Result<PreparedRestore, FmlError>; // rng 取 token（UUID-v4）与临时库随机 DbKey；先调 cleanup_staging
pub fn commit_restore(store: &Store, sessions: &mut RestoreSessions, token: Uuid, ctx: &RestoreContext, cancel: &CancelFlag) -> Result<RestoreReport, FmlError>;
pub fn discard_restore(sessions: &mut RestoreSessions, token: Uuid) -> Result<(), FmlError>;
pub fn cleanup_staging(staging: &Path, keep: &RestoreSessions) -> Result<u32, FmlError>;   // 删除 staging 直接子项中名为 restore-<uuid>.db（及 -wal/-shm）且不属于 keep 的遗留临时库，返回删除个数
pub struct RestoreReport { pub inserted: BTreeMap<String, u64>, pub kept_local: u64, pub replaced: u64, pub cards_replayed: u64 }
```

- 准备恢复 6 步：① 读头、解包文件密钥（失败 → `BACKUP_WRONG_SECRET`）；② 解密块 0，核对 `header_blake3`；③ `schema_version > SCHEMA_VERSION` → `BACKUP_SCHEMA_TOO_NEW`；④ 在 `staging` 用随机 `DbKey` `Store::open` 新临时库（迁移到当前版本），按列名插入负载（迁移只增不删，旧备份缺少的新列取默认值；出现当前 schema 没有的列 → `BACKUP_CORRUPT`）；⑤ 核对 `payload_blake3`、行数与末块标记、`integrity_check` 与外键检查；⑥ 计算 `RestorePreview`。任一步失败删除临时库，原库未被写入。
- 提交（单个 `Store::write` 事务，ATTACH 临时库）：
  - `Replace`：只删除 TablePolicy.scope 属于所选范围且满足固定 row_filter 的本地行，再插入经同一策略验证的范围行；kind = 1 的闭包行**按 Merge 处理**（只插入本地缺失行，主键已存在时保留本地行并计入 `kept_local`），不删除本地其余公式或单位；
  - Replace 外键规则：事务内 `PRAGMA defer_foreign_keys = ON`；所选范围内仍被**未选范围本地行**经外键（按 foreign_key_list 传递）引用的行不删除——文件中有同主键行时按列原地更新为文件值（计入 `replaced`），否则保留（计入 `kept_local`）；其余范围行删除（范围内循环外键由延迟检查处理）。插入完成后执行 `PRAGMA foreign_key_check`，有违例则回滚整个事务并返回 `BACKUP_CORRUPT`，原库不变。删除与更新经 CORE-13 写命令规则（墓碑、changed_fields 与 outbox），预览的 `replaced`/`kept_local` 按同一规则在临时库与只读快照上预先计算；
  - `Merge`：CORE-13 TablePolicy.mutability=Immutable 的表按主键插入缺失行；可变表主键已存在时保留本地行（计入 `kept_local`），不存在时插入；用户自建公式规范 AST 哈希相同但 ID 不同只列入 `possible_duplicates`，不自动合并；
  - 两种模式下插入的行都经 `enqueue_outbox`（同步开启时上传）；有新 `review_event` 的卡片在同一事务用 CORE-17 `load_params_tx` 取当前参数，以 `ctx.now_ms`、`ctx.day` 调 CORE-17 `replay` 重算 `study_card` 调度，outbox 的 created_at_ms 取 `ctx.now_ms`；恢复不触发 CORE-13 `rotate_device_id`（本机 device_id 与时钟连续，新写入行按本机时钟入队，ADR-V5-33 的整库回退只指同步检测到的旧身份 envelope）；清空 `mastery_cache` 与 `stats_cache`（CORE-20 缺缓存时全量重算）；`formula_fts` 由 CORE-14 触发器维护。
  - 提交成功或失败后都删除临时库；token 只在签发它的 RestoreSessions（同一档案句柄）内有效，`ctx.now_ms − started_ms ≥ 1 800 000` 视为过期并删除；不存在/过期/他档案 token 一律 `BACKUP_TOKEN_UNKNOWN`；commit 前核对 prepare 时的 mode。

- 容器、块序/AAD/末块/摘要与行数检查严格复用CORE-27；已认证行流直接插入临时库，不落明文负载文件、不另写第二套解码器。块与闭包kind=1规则复用CORE-27；范围/行过滤/不可变类别来自CORE-13 table_policies()，与导出同源，恢复不另写名单且不扩大范围。
- 表结构只依赖 CORE-13 的 Store/schema、table_policies() 与 PRAGMA：在已迁移临时库及目标事务连接用 table_info 读取列/默认值/主键，foreign_key_list 按 id/seq 读取复合外键，不转录 CORE-19/82/86 等所有者列或 DDL，也不建重复迁移。文件表段先匹配唯一 TablePolicy 再按列名映射；未知/重复列、未知表、Never 表/过滤外行或伪造 scope/kind 均报 BACKUP_CORRUPT。旧备份缺少当前列时，仅可用实际 schema 的默认值/可空规则；缺必填且无默认值即拒绝，不填造假值。未来未合入表不创建，当前策略声明却缺表/固定过滤列按 CORE-13 报 STORE_CORRUPT，不默默跳过。
- Mutable/LocalMutable 保留现有 Merge 冲突规则，Derived 只按既有所有者约束校验/重建，不当成用户修改；Never 永不插入/删除/作闭包。预置内容稳定 ID 与 missing_packs 保持原行为，PRAGMA 发现结构不是扩展或收紧产品范围的依据。CORE-17 仍提供 review_event 后的 replay；ADR-V5-50“只依赖CORE-13”限定表结构依赖，不排除重放算法依赖。
- 唯一登记op（profile scope，按信封 profile_handle 取该档案的 RestoreSessions）：submit `backup.prepare_restore` `{path,protection,mode,staging_root,now_ms}`→`{token,preview}`（可取消）、`backup.commit_restore` `{token,now_ms,day}`→`{report}`（submit；取消只在提交事务开始前生效并返回 CORE-27 `BACKUP_CANCELLED`（prepare_restore 取消同码），事务开始后不可取消，返回最终报告）；call `backup.discard_restore` `{token}`→`{}`。staging_root 随请求传入（ADR-V5-53），临时库为其直接子项 `restore-<token>.db`；启动遗留由下一次 prepare_restore 先行 cleanup_staging 清除（遗留库的随机 DbKey 随进程退出丢失，不可读），不另设 op。本卡fml-ffi适配向prepare_restore传入CORE-23 OsRandom（生成 token 与临时库随机DbKey，不经JSON）；秘密不进日志。
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
| STORE_CORRUPT | CORE-13 | 本构建策略必需表/过滤列缺失或策略矛盾，拒绝而非跳过 |

**实现约束**
- 准备失败、提交成功/失败、取消/discard、档案关闭均清理临时库；prepare_restore 先调 cleanup_staging；token 30 min（按调用方 now_ms）未提交即过期，句柄不跨进程、不跨档案。
- 用户确认RestorePreview后才提交；单个Store.write事务ATTACH临时库，不分批破坏原子性。
- 无新增第三方依赖，加密/CBOR/BLAKE3共享CORE-27/21/05。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-84_TEST.md](../Test/core/S6_CORE-84_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约400行；crates/fml-store/src/backup/restore.rs及本卡编写的crates/fml-ffi/src/ops/backup_restore.rs，含准备/合并替换（含 Replace 外键保留与原地更新）/replay接入/按档案 token 会话与清理和3op；不重复计CORE-27共享格式/校验，不计DDL/schema、生成物、自测及夹具。
