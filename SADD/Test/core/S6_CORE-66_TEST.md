# CORE-66 测试方案

> 来源卡：[S6_CORE-66_扩展.md](../../core/S6_CORE-66_扩展.md)（同步快照与密钥轮换编排）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R28] T-SNAPSHOT（M3 读路径）：`apply_snapshot` 后再应用其后的增量，结果与全量重放一致。
- [R28] 轮换中断后重试不重复事件，旧记录仍可解密；快照分片缺失/篡改不能修改业务库。
- [R28] 目录分片协议：用接近上限的 64 MiB 测试库 `build_snapshot` 得到 ≤ 256 个、每个 ≤ 4 MiB 的分片，FFI 请求与响应 JSON 均 < 64 KiB；缺一片、少一片、片序错乱、改一字节、清单哈希被改均报 `SYNC_SNAPSHOT_CORRUPT`，业务库字节与游标不变；构建中途取消后 `out_dir` 不存在；路径在暂存区之外、符号链接、非空 `out_dir` 报 `SYNC_PATH_INVALID`；`cleanup_snapshot_dirs` 只删除超龄的 `snapshot-*` 目录。
- [R28] 轮换（`reencrypt_for_rotation`）使用 `FixedRandom` 时结果确定；rng 失败返回 `CRYPTO_RNG_FAILED` 且不入队部分条目；轮换提交在同一事务调 CORE-78 `invalidate_all(KeyRotated)`，使未 ACK 的 `push_batch` 作废，条目留在 outbox 按新密钥重建（与 CORE-26 的批次失效用例联测）。
