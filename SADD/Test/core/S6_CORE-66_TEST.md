# CORE-66 测试方案

> 来源卡：[S6_CORE-66_扩展.md](../../core/S6_CORE-66_扩展.md)（同步快照与密钥轮换编排）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R28] T-SNAPSHOT（M3 读路径）：`apply_snapshot` 后再应用其后的增量，结果与全量重放一致。
- [R28] 轮换中断后重试不重复事件，旧记录仍可解密；快照分片缺失/篡改不能修改业务库。
- [R28] 目录分片协议：用接近上限的 64 MiB 测试库 `build_snapshot` 得到 ≤ 256 个、每个 ≤ 4 MiB 的分片，FFI 请求与响应 JSON 均 < 64 KiB；缺一片、少一片、片序错乱、改一字节、清单哈希被改均报 `SYNC_SNAPSHOT_CORRUPT`，业务库字节与游标不变；构建中途取消后 `out_dir` 不存在；路径在暂存区之外、符号链接、非空 `out_dir` 报 `SYNC_PATH_INVALID`；`cleanup_snapshot_dirs` 只删除超龄的 `snapshot-*` 目录。
- [R28] 轮换重排（reencrypt_for_rotation）使用固定IdSource时队列确定，创建op_id失败返回CRYPTO_RNG_FAILED且不入队部分条目；函数不接rng、不声称已产生新密文；轮换提交在同一事务调 CORE-78 `invalidate_all(KeyRotated)`，使未 ACK 的 `push_batch` 作废，条目留在 outbox 按新密钥重建（与 CORE-26 的批次失效用例联测）。
- [R28] 快照build按registry稳定枚举权威实体/墓碑并保留ID/FieldClock，不导出session/参数/缓存/密钥；apply与增量使用相同owner applier及拓扑顺序，analyzer看见同事务用户叠加层，任务cancel原样传递；任一Invalid整份SYNC_SNAPSHOT_CORRUPT回滚，无部分隔离成功。
- [R28] build密钥与实体同一读快照，apply/reencrypt密钥与当前版本同一写事务读取，不跨请求缓存；轮换requeue保留业务字段与时钟。FFI仅路径/清单/版本，registry/analyzer/rng/cancel均由原生接线注入，复用26适配不重复实现56。
- [R28] 重排成功后仍为待加密状态；CORE26 prepare_push 的nonce RNG失败不返回伪成功密文，队列保留可重试；真实加密/上传/确认完成前不得报轮换完成或删除旧密钥。
- [R28] 复用真实26分析适配验证内置方案、自建同ID叠加与未知方案；不可用引擎/未知方案分别透传ENGINE_UNAVAILABLE/NOTATION_UNBOUND，covers_through与所有业务行均保持原值，不报告SYNC_SNAPSHOT_CORRUPT/部分成功；ParseOptions固定100/true，全部输入来自同Arc与当前事务。
