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
- [R28] 每类实体由其owner applier执行，FakeRegistry审计分派/拓扑顺序；同一页先单位/记号后修订，其分析能读到本事务overlay；conn合同只读，不嵌套Store调用。Fake分析器和真实CORE56 helper适配分别验证ast/symbols/validation/diagnostics输出，ast=None不回退上传AST；任务cancel使整页和游标回滚。
- [R28] prepare/apply在写事务内load_account_keys_tx；与导入/轮换交错只能读到同一事务版本。page epoch不匹配不写业务/游标；缺钥不前移，非法单条保存点回滚并隔离而其他合法条可提交，存储错误整页回滚。
- [R28] SY-PAYLOAD-V1独立字节向量与CBOR非法最短编码/重复键/不定长/尾字节反例；逐项断言Envelope的固定version/kind、原outbox身份序号、修订专用revision_id、purpose/base64/hash与AAD一致，内层不虚构key_version。
- [R28] 正常Stale重包装Conflict仅出队，不改变device_id；只有通过验证的本机高device_seq触发rotate，篡改/未知schema的高序号不能旋转；RNG失败整页回滚。epoch全量重排保留业务时钟，含未过期原类型墓碑，不上传tombstone第二类型。
- [R28] 事务分析前提矩阵：未自建的cn-default/iso从同Arc内置方案精确取得；同ID自建方案以当前事务记录覆盖，真正未知ID返回NOTATION_UNBOUND而非任意默认。快照获取失败/不可用返回ENGINE_UNAVAILABLE；Fake记录ParseOptions=100/true、empirical=false。以上前提故障均整页/游标回滚、无隔离行，不与无效远端内容的逐条Invalid混淆。
- [R28] 入站 Envelope 校验：apply_pull 的页内依次放入 `contracts/vectors/envelope-v2.json` 中可由 PullResponse 反序列化的非法用例（字段越界、HashMismatch、TooLarge）与 setting 实体使用 UUID entity_id、formula 实体使用设置键的两条，每条进隔离区并计 `SYNC_QUARANTINED`，同页合法条目照常应用、游标前移；`PushResult`/`PullPage` 与 CORE-68 类型为同一 Rust 类型（编译期 `TypeId` 断言）。
- [R28] 隔离逐码：同一页分别放入篡改 ciphertext 一字节（`SYNC_DECRYPT_FAILED`）、未知 schema_version=2、未登记 entity_type、负载 CBOR 非法（非最短整数、重复键、尾随字节）、entity_id 形态与类型不符（UUID 实体用大写 UUID、local_setting 键含大写）、内外 entity_id 不一致但解密成功（`SYNC_AAD_MISMATCH`，用测试密钥构造），各自进入 sync_quarantine 且 reason 为对应码，其余条目照常应用、游标前移，ApplyReport.quarantined 计数正确；同一 op_id 再次到达不新增行。
- [R28] 隔离 raw：合法上限 Envelope（密文 262 144 字节）隔离时 raw 为完整规范字节、raw_truncated=0；伪造超过 384 KiB 的 Envelope 只存前 393 216 字节、raw_truncated=1。
- [R28] 保留期：apply_pull 以 now_ms 调用后 received_at_ms 早于 now_ms − 30 天的隔离行被删、恰等于边界的保留；早于 now_ms − 180 天的墓碑被删；墓碑清理后到达的旧版本按普通实体应用（文档化行为）；页回滚时清理一并回滚。
- [R28] 待选择：resolve_choice 选择不在 heads 中的修订返回 `SYNC_CHOICE_INVALID` 且不写入；合法选择后 `sync.choices` 不再列出该记录，选择结果作为 merge_choice 实体入 outbox。
- [R28] 命名冲突与设置：两端各建同名自定义单位/记号方案后同步，两者都保留、后到者加后缀并生成提示；`local_setting` 仅 syncable=1 的键产生 envelope，`device.*` 键与 syncable=0 键不出现在 prepare_push 结果中，同键并发修改按 (counter, device_id) 收敛。
- [R28] 查询 op：`sync.cursor`、`sync.status`、`sync.choices` 在空库与有数据时的返回字段与卡片 FFI 段一致（status 空库例值逐字节相等）。
- [R28] 透传：Fake CORE-78 让 `save_batch` 返回 `SYNC_BATCH_INVALID` 时 prepare_push 原样返回该码且事务回滚；负载超过 256 KiB 的实体不进入批次且返回所有者卡的 `LIB_*` 上限错误（在写入时已拒绝，本卡不再拆分）。
- [R28] 负载字段：Envelope 的 nonce 解码为 24 字节、ciphertext 不含版本字节与 nonce；以 version=1 重组 Sealed 可解密；ciphertext_hash 等于 SHA-256(ciphertext) 小写 hex。
- [R28] 纪元同值：`on_epoch_changed` 传入与本地相同的纪元时仍作废批次、清游标并重建 outbox；传入更小值返回 `SYNC_EPOCH_STALE` 且不写入。
