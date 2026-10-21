# CORE-84 测试方案

> 来源卡：[S6_CORE-84_扩展.md](../../core/S6_CORE-84_扩展.md)（备份恢复与合并）。本文件是该卡验收标准全文；修改范围时同步修改，工具从下方验收标准行起拼回。

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
- [R27] token30min超时、未知/过期token拒绝；prepare失败、commit成功/失败、discard/取消和启动cleanup_staging均无临时库遗留；commit仅事务开始前取消生效，开始后报告最终结果。
- [R27][R19] schema只经CORE-13/PRAGMA，调度用CORE-17 replay；完整性/外键/未知列/旧列默认值检查按协议，RestorePreview显示missing_packs，重装包自动关联。
- [R27][R18] 恢复与导出同消费 CORE-13 table_policies()：Immutable 分类不手列三张表，Replace 只删所选 scope 且满足固定行过滤的行，保留其他行/闭包已有本地行。加入迁移的默认值列/复合 FK 后无需改恢复列清单；缺当前必填无默认值、文件未知/重复列、未知/Never 表、伪造 scope/kind 或过滤外行拒绝 BACKUP_CORRUPT，原库不变。
- [R27][R18] 分别测试未来未合入表和本构建必需表缺失：前者不创建，后者 STORE_CORRUPT 且清理 staging，不得漏恢复成功；静态策略不含设备库。PRAGMA 变化不改变五项范围、包稳定 ID 引用及 missing_packs 既有语义。
