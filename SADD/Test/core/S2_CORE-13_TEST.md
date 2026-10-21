# CORE-13 测试方案

> 来源卡：[S2_CORE-13_功能.md](../../core/S2_CORE-13_功能.md)（本地库 Schema、单写者与迁移）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R27] 离线读取测试：用 sqlite3 或任意未带密钥的工具打开库文件、WAL 与临时文件均失败；对库目录做明文关键字扫描（样例公式与笔记文本）零命中。
- [R18] 迁移链测试：`tests/fixtures/db/` 中每个历史版本的样例库逐级迁移到最新版本，数据与校验和一致；注入迁移中途失败后新构建返回STORE_MIGRATION_FAILED，原库/备份不变；用旧兼容构建重开旧库成功，不能把新构建返回错误说成已打开。
- [R18] 乱序到达：样例库已执行 0013、0078，随后加入 0026 后打开，0026 被补执行并记入 `schema_migration`，`user_version` 保持 78；全部已记录文件不重复执行。
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
