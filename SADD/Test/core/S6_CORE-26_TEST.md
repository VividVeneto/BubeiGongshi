# CORE-26 测试方案

> 来源卡：[S6_CORE-26_扩展.md](../../core/S6_CORE-26_扩展.md)（同步引擎（加密、合并与隔离））。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R28] T-SYNC（Rust 集成测试，两个 `Store` 经内存中继模拟服务端）：两端离线编辑同一公式产生并发头，交换后两端各出现同一 ID 的“待选择”，一端选择后另一端同步到选择结果；复习事件不丢失、不重复；墓碑之后到达的旧版本被丢弃。
- [R28] 中断测试：`prepare_push` 后不 ACK、ACK 丢失后重发同一批次、`apply_pull` 中途失败回滚，最终两端一致且无重复事件。
- [R28] T-RESEND：`prepare_push` 返回后杀进程并重启，再次 `prepare_push` 得到的 Envelope 字节（含 nonce 与密文）与第一次逐字节相同，且不消耗 rng（`FixedRandom` 字节未被取用）；部分 ACK 后重启，只重发剩余条目且其字节不变；同批次再次推送服务端返回原 `server_seq`。
- [R28] 批次失效（端到端，与 CORE-78 的单元测试对应）：`on_epoch_changed` 后旧批次被删除，条目重新进入新批次，旧密文不再发送；CORE-66 密钥轮换的对应用例见 CORE-66。
- [R28] T-STALE：设备 A 持有 key_version = 1 的未结算批次，设备 B 轮换到 2 并提高 `min_key_version`；A 经 `import_account_key` 取得版本 2 后，下一次 `prepare_push` 作废旧批次并以版本 2 重建，推送成功（已被服务端存储的 op_id 返回 CONFLICT 并出队），之后不再出现 `SYNC_KEY_VERSION_REJECTED`。
- [R28] 并发与口径：两个线程同时 `sync.prepare_push` 只产生一个批次、不出现 `SYNC_BATCH_INVALID`，两次返回同一 batch_id；构造一组元素使请求体恰为 1 048 576 字节时全部入批，再加 1 字节时末条留到下一批；返回的批次按紧凑 JSON 序列化后的字节数等于计量值；全额结算后重复 `sync.ack` 返回 `{}`。
- [R28] T-AAD：替换 envelope 的 entity_id 或 key_version 后解密被拒并进入隔离区，游标照常前移；`SYNC_KEY_MISSING` 时游标不前移。
- [R28] T-FIELD：A 端改公式条目标题、B 端同时改备注，交换后两端两字段都保留；两端同时改标题时 `(counter, device_id)` 大者胜且两端一致；负载 `clocks` 等于发送端 outbox 行的 `clocks`；接收端合并后 `field_clock` 更新且不生成 outbox。
- [R28] T-ROLLBACK：A 端推送 3 次修改后把档案库文件替换为推送前的副本，再离线改同一字段；同步后检测到回退、`device_id` 更换，A 与 B 两端该字段取值一致，回退前已推送的其他修改在 A 端恢复，CONFLICT 项不重复推送。
- [R28] 纪元变化：`on_epoch_changed` 后游标清空、outbox 含全部可同步实体各一条。
- [R26] 游客与未开启同步时任一 `sync.*` op 返回 `SYNC_DISABLED`。
