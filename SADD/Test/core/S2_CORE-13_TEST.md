# CORE-13 测试方案

> 来源卡：[S2_CORE-13_功能.md](../../core/S2_CORE-13_功能.md)（本地库 Schema、单写者与迁移）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R27] 离线读取测试：用 sqlite3 或任意未带密钥的工具打开库文件、WAL 与临时文件均失败；对库目录做明文关键字扫描（样例公式与笔记文本）零命中。
- [R18] 迁移链测试：`tests/fixtures/db/` 中每个历史版本的样例库逐级迁移到最新版本，数据与校验和一致；注入迁移中途失败后新构建返回STORE_MIGRATION_FAILED，原库/备份不变；用旧兼容构建重开旧库成功，不能把新构建返回错误说成已打开。
- [R18] 乱序到达（S2 时 0026/0078 尚未交付，用 `tests/fixtures/db/migrations-synthetic/` 中同名序号的合成迁移文件经测试专用嵌入入口注入，不依赖后续卡）：样例库已执行 0013、0078，随后加入 0026 后打开，0026 被补执行并记入 `schema_migration`，`user_version` 保持 78；全部已记录文件不重复执行。
- [R19] 故障注入：写事务中途杀进程，重启后库可打开且无半条记录；磁盘满时返回 `STORE_DISK_FULL`，原数据不变。
- [R28] 单元测试：业务写与 `enqueue_outbox` 同事务，回滚时两者都不落库。
- [R28] 同一事务内写 2 个实体的 outbox 与 1 条事件行：三者共用同一 lamport 与 device_seq，local_clock 只前进 1；回滚后 local_clock 不变；payload 等于 `read_entity` 回读结果与字段时钟。
- [R18][R19] 已执行迁移即使无pending仍校验：改原始字节/换行或name返回STORE_MIGRATION_FAILED，缺文件/已记录版本过高返回STORE_SCHEMA_TOO_NEW；均不写原库。build.rs只枚举migrations直接子文件，registry/不参与SCHEMA_VERSION；重复序号构建失败，checksum为原始UTF-8 BLAKE3小写64hex。
- [R28] IdSource固定序列覆盖新库device_id、两个op_id、rotate；现库重开不取新device_id，重发不换op_id。失败CRYPTO_RNG_FAILED与非法/重复UUID的STORE_CORRUPT均回滚身份/业务/时钟/outbox，不无限重试；FFI store.open请求未新增rng字段。
- [R28] Fake codec/applier/analyzer验证EntityRegistry重复注册拒绝、稳定类型/ID枚举、setting排除device.*及syncable=0；ApplyOutcome的非法实体回滚保存点、存储故障整页回滚由调用方fixture验证，owner不stamp/enqueue或嵌套Store调用。
- [R28] requeue_outbox覆盖存活/墓碑/不存在/缺时钟/游客/注册未开同步，字段值/field_clock逐字不变，完整清队列+重排失败全回滚；初始化升级资格后可入队，重复既定重建不多一份实体。
- [R18] 所有已合入迁移中的表均在本卡策略表出现且owner/scope/mutability唯一；never闭包不导出，动态列/FK由PRAGMA读取而非复制他卡DDL；S2仅Fake和已交付setting，不要求未交付业务表存在。
- [R18][R27] table_policies() 返回只读静态 slice：每个已合入 profile 表恰一条且 owner/scope/mutability/RowFilter 与唯一清单相符；不同构建只含各自已合入表，尚未交付表不创建；独立设备库表不进入 slice。未知表默认 Never，重复/矛盾策略、缺已合入表/过滤必需列返回 STORE_CORRUPT，不静默跳过。
- [R27] 固定行过滤 fixture 覆盖用户/预置 item、非包/包缓存 revision、按 revision_id 的绑定、按 result_revision 的派生索引、syncable 设置及 device.*；未通过过滤的行隐式 Never，不能由 FK 闭包带出。RowFilter 只取闭集枚举，不接受任意 SQL。
- [R27] 错误逐码（CO-29）：错误密钥打开返回 STORE_KEY_INVALID 且不改文件；文件头被覆写返回 STORE_CORRUPT；迁移前剩余空间设为库文件 2 倍减 1 字节（可注入的空间探针）返回 STORE_DISK_FULL 且未建备份、未开迁移事务；写命令在 actor 前排队超过 5 s（注入阻塞的前一命令）返回 STORE_BUSY 且该命令未执行，前一命令照常提交。
- [R28] 只读池：read_pool=2 时两个并发 read 各见自己开始时的 WAL 快照，期间提交的写对已开始的 read 不可见、对之后的 read 可见；read 闭包内无法取得可写连接。
- [R28] 时钟边界：tombstone 写入 (entity_type, entity_id, deleted_at_ms) 且同事务 enqueue Delete 的 payload 为 entity=None、clocks 含 __deleted；local_clock.lamport 或 device_seq 为 i64::MAX 时 stamp 返回 STORE_CORRUPT 并回滚，不回绕；rotate_device_id(min_lamport) 后 device_seq=0、lamport=max(原值, min_lamport)，已有 field_clock 与 outbox 行逐字不变。
- [R28] 向量 CLOCK-01、CLOCK-02 按本卡表逐条断言（合并后 lamport=12，本地编辑 title 时钟=(13,本设备)、outbox 同事务 1 条；outbox 注入磁盘满后业务、field_clock、L/S 与 outbox 全部回到原值）。
- [R18] SCHEMA_VERSION：构建产物中的常量等于 migrations/ 直接子文件最大序号（夹具构建仅含 0013 时为 13）；store.open 返回的 schema_version 等于该常量。
- [R19] Store op：按本卡字段表示例逐条调用 store.open/close/integrity_check（schema_version 断言 ≥ 13）；同一规范路径第二次 store.open 返回 STORE_BUSY 且首个句柄可继续使用；db_key_b64 解码非 32 字节返回 CORE-03 参数错误；close 后再用该句柄返回 CORE-03 句柄错误。
- [R28] 墓碑清理：`purge_tombstones(before_ms)` 只删除 deleted_at_ms 严格小于 before_ms 的行（等于时保留）、返回删除条数、不写 outbox 与 field_clock；事务回滚后墓碑仍在。
