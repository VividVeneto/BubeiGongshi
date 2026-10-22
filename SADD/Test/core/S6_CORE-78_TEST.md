# CORE-78 测试方案

> 来源卡：[S6_CORE-78_扩展.md](../../core/S6_CORE-78_扩展.md)（同步推送批次持久化）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R28] 保存 → 关闭并重新打开 Store → `pending_batch` 返回的 `batch_id`、`account_epoch`、`key_version`、`op_ids` 与保存时相等，`envelopes` 逐字节相同（含长度为 0 的元素与不等长元素；单元素真实上限由 CORE-25/68 的 Envelope 契约决定，本用例不据 1 MiB 合计上限推断单元素合法性）。
- [R28] 部分结算：被结算 op 的 outbox 行消失、其余保留；`SettleReport` 的 `removed_ops`、`remaining`、`batch_deleted` 与期望一致（`removed_ops` 只计实际删除的 outbox 行、`remaining` 只计批内剩余条目数：另构造一条 op 的 outbox 行先被其他路径删除的用例，断言该 op 从批次移除但不计入 `removed_ops`，`remaining` 只按条目数变化）；批次改写后剩余元素字节不变；全部结算删批次；不属于该批次的 op_id 被忽略；空 `settled` 不改动并返回 `{0, n, false}`（n 为批内条目数）；全部结算后用同参数再次 `settle` 返回 `{0, 0, true}`；`invalidate_all` 后用旧 batch_id 结算仍在 outbox 的 op_id 返回 `SYNC_BATCH_UNKNOWN`（warning、不可重试）且不改动任何行，不把旧批次回执当作可重试业务失败；重新读取待推送状态由调用方调度。
- [R28] `invalidate_all` 删除全部批次、返回删除数并保留 outbox；`save_batch` 对长度不等、空批次、批内重复 op_id、op_id 不在 outbox、超 200 条、元素字节和超 1 MiB（恰为 1 048 576 字节通过，再加 1 字节拒绝）、epoch 或 key_version 为 0、batch_id 重复、已有未结算批次分别报 `SYNC_BATCH_INVALID`。
- [R28] 故障注入：`#[cfg(test)]` 注入点让 `save_batch` 与 `settle` 在写入第 k 条语句后（k 取全部语句位置）返回 Err 或 panic，随后关闭并重开 Store；另以子进程在提交前 `std::process::abort()` 一次。重启后不出现半个批次，`settle` 要么整体生效要么整体不生效。
- [R28] 补充边界：空库 `pending_batch` 返回 None；`invalidate_all` 分别以 EpochChanged、KeyRotated、Stale 调用，删除数、表状态与 outbox 完全一致（Stale 为 CORE-26 纪元/密钥不一致路径，作废后可立即 `save_batch` 新批次）；保存后直接读 `push_batch` 行，`op_ids_json` 为小写带连字符 UUID 字符串数组；部分结算后 `batch_id`、`account_epoch`、`key_version`、`created_at_ms` 保持不变；含 70 000 字节元素（长度前缀超 u16）的批次往返逐字节相同。
- [R28] 读取损坏：分别把 `op_ids_json` 改为非法 JSON、大写 UUID，把 `envelopes` 截断 1 字节、追加 1 字节、首个长度前缀改为超出剩余长度，以及插入第二行批次，`pending_batch` 与 `settle` 均返回 `STORE_CORRUPT` 且不改动任何行（两个入口都执行同一套校验，含“表内多于一行”检查）。
