# CORE-27 测试方案

> 来源卡：[S6_CORE-27_扩展.md](../../core/S6_CORE-27_扩展.md)（备份格式、导出与校验）。本文件是该卡验收标准全文；修改范围时同步修改，工具从下方验收标准行起拼回。

**验收标准**
- [R27] 随机库导出后verify完整通过，范围行/闭包行数量与顺序正确；只选study仅带被引用公式行，只选含用户单位formulas带对应user_unit，永不导出表不在文件；五项全false报BACKUP_SCOPE_INVALID且不创建文件。
- [R19] BK-V1独立人工复核固定字节向量逐字节一致；末块后追加、缺末块、块号乱序、block_count/payload_len/哈希/行数篡改均报BACKUP_CORRUPT。
- [R19] 分别翻转头/块0/中间块/末块、删除/交换块，verify拒绝；WrapRecord被改或错误口令报BACKUP_WRONG_SECRET；导出取消/自检失败清理输出，负载从不落明文临时文件。
- [R25] 游客可口令导出、verify，无HttpTransport请求。
- [R19][R28] 导出后解析WrapRecord.key_version=1，backup.chunk/final AAD也为1；两种包装均可由verify解包校验；任意改成0的包装按CORE-21拒绝，不生成自拒绝文件。
- [R27] 弱口令在KDF/创建文件前按CORE-21拒绝；恢复实现不被原卡反向导入，共享解码器只交付认证行流。
