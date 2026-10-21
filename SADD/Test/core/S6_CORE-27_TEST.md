# CORE-27 测试方案

> 来源卡：[S6_CORE-27_扩展.md](../../core/S6_CORE-27_扩展.md)（备份格式、导出与校验）。本文件是该卡验收标准全文；修改范围时同步修改，工具从下方验收标准行起拼回。

**验收标准**
- [R27] 随机库导出后verify完整通过，范围行/闭包行数量与顺序正确；只选study仅带被引用公式行，只选含用户单位formulas带对应user_unit，永不导出表不在文件；五项全false报BACKUP_SCOPE_INVALID且不创建文件。
- [R19] BK-V1独立人工复核固定字节向量逐字节一致；末块后追加、缺末块、块号乱序、block_count/payload_len/哈希/行数篡改均报BACKUP_CORRUPT。
- [R19] 分别翻转头/块0/中间块/末块、删除/交换块，verify拒绝；WrapRecord 结构被破坏（CBOR 头字节、截断、wrap_kind 改为未知值、key_version 改 2）报 BACKUP_CORRUPT，密文/标签字节被改或错误口令、用恢复码打开口令文件报 BACKUP_WRONG_SECRET；导出取消/自检失败清理输出，负载从不落明文临时文件。
- [R25] 游客可口令导出、verify，无HttpTransport请求。
- [R19][R28] 导出后解析WrapRecord.key_version=1，backup.chunk/final AAD也为1；两种包装均可由verify解包校验；任意改成0的包装按CORE-21拒绝，不生成自拒绝文件。
- [R27] 弱口令在KDF/创建文件前按CORE-21拒绝；恢复实现不被原卡反向导入，共享解码器只交付认证行流。
- [R27][R18] 同源策略：导出只消费 CORE-13 table_policies()，不保留备份表/过滤 SQL 副本；Fake 已合入迁移中增加允许表的带默认值列/复合 FK 后，PRAGMA 发现的列序、主键与外键组直接决定负载列与闭包，不修改消费者硬编码。未知表/Never/过滤外行均不导出；闭包不能越过 Never。
- [R27][R18] 构建差异：未来未合入表不创建也不假要求存在；当前 slice 所需表或固定过滤列被删则 STORE_CORRUPT 且无输出，不能漏表成功。单快照内数据/列/闭包一致，不能在另一连接拼出混合视图。
- [R27] 保护与前置检查：RecoveryCode 保护导出→verify 往返成功；游客选 RecoveryCode 报 BACKUP_PROTECTION_UNAVAILABLE、格式错误恢复码报 CRYPTO_RECOVERY_CODE_FORMAT；Fake 空间探针使 staging 可用空间小于库文件大小时报 BACKUP_DISK_FULL；以上与弱口令均不创建文件、不运行 KDF。
- [R27] verify 只读：对同一文件连续 verify 两次结果相同，过程中不打开任何 Store、不写文件；out_path 不在 staging_root 直接子项或扩展名不是 .fmlbackup 报 FFI_BAD_ARG。
- [R19] 确定性：FixedRandom、相同 now_ms 与库内容两次导出逐字节相同；头与清单 created_at_ms、WrapRecord 创建时间均等于传入 now_ms，app_version 等于 fml-ffi 版本；BK-V1 期望字节来自 gen_backup_v1.py 参考脚本且该脚本不链接被测代码。
- [R27] 失败清理与清单：FixedRandom 在第 n 次 fill 失败（覆盖文件密钥、盐、头 nonce、中间块 nonce）与导出中途取消，均返回原错误码且 staging 中无 out_path 及临时文件；清单的范围位键按协议编号逐项断言（与 ExportScope 字段声明顺序无关，单独设置每一项范围核对对应位）。
