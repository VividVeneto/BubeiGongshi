# CORE-46 测试方案

> 来源卡：[S6_CORE-46_扩展.md](../../core/S6_CORE-46_扩展.md)（同步网络协调与快照）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**

- [R24][R28] pull HTTP/prepare/push HTTP/ack/snapshot下载及apply逐项暂停后关闭A：null立即disabled取消，drain前不native close/openB；迟到A响应不进入B的apply/ack/状态。相同handle多触发同singleflight，新handle新Future。attach两次一订阅，paused取消网络/FFI/退避并排空，A计时器不触发B；档案70每handle一次。
- [R26][R28] null/guest/off每种SyncTrigger均disabled且HTTP/profile同步op零次，不抛SYNC_NOT_AVAILABLE；显式低层SYNC_DISABLED仅收敛disabled。setEnabled(false)排空后只写原仍有效handle，竞争切换不写B。
- [R28] SYNC_BATCH_UNKNOWN断言warning/不可重试诊断一次，下一步prepare_push而非重试ack；failed/lastErrorCode/弹窗/失败计数/退避不变且仍计50往返。日志无key/token/恢复码。
- [R28] 两台设备（同一进程内两个档案 + `fake_sync_server`）：设备 A 升级为注册并开启同步，设备 B 登录后用恢复码 `restoreOnNewDevice`，同步后公式与复习事件一致；服务端替身中只有包装记录与密文。
- [R28] 中断：推送响应丢失后重试同一批次，服务端返回原 `server_seq`，本地无重复；`SYNC_EPOCH_STALE` 后自动全量重传并成功。
- [R28] KeyService轮换/恢复由CORE-98验收；本卡对sync.ack返回SYNC_BATCH_UNKNOWN继续prepare_push重建，状态不变为failed、不退避、不计失败。
- [R26] 游客与未开启同步时，触发任意 `SyncTrigger` 均不产生请求（Fake `HttpTransport` 审计）。
- [R24] 刷新令牌失效时同步停止并回到登录，本地数据与 outbox 保持不变。

- [R12][R28] 两设备同步已保存两步calculation_plan，另一端重开与运行结果一致（复用CORE-48夹具）。
- [R28] 快照分片逐片SHA256校验/已有正确片复用续传，apply携带完整chunk_count/total_bytes/hashes/covers_through/key_version，成功或放弃清理目录；上传build逐片PUT再commit，随后增量无重复。单次50往返停止、singleflight合并、paused取消、Retry-After/前台退避/426/密钥与quota状态均满足契约。
- [R28] 纪元与游标错误：Fake ApiClient 返回 `SYNC_EPOCH_STALE`（args.account_epoch="3"）时以 server_epoch=3 调用 `sync.on_epoch_changed` 并只重试一轮；`SYNC_CURSOR_INVALID` 带与不带 account_epoch 两种情况分别按表处理，第二次失败进入 `failed`；`SYNC_ENVELOPE_INVALID` 不重试且批次保留。
- [R28] 推送字节口径：Fake HttpTransport 记录请求体；`sync.prepare_push` 返回 n 个 Envelope 时请求体字节等于 16 + Σ 各 Envelope 规范 JSON 字节 + (n − 1)，键序与 op 返回一致、无空白、`/` 不转义；构造总长恰为 1 048 576 字节的批次照常推送，1 048 577 字节的批次不会由 CORE-26 产生（以 Fake op 注入时本卡不截断、原样发送）。
- [R28] 错误分类：快照 commit 返回 `SYNC_SNAPSHOT_INCOMPLETE`、`sync.snapshot_apply` 返回 `SYNC_SNAPSHOT_CORRUPT` 或 `SYNC_PATH_INVALID` 时进入 failed 且暂存目录被删除；`SYNC_BATCH_INVALID`、`STORE_DISK_FULL`、`CRYPTO_RNG_FAILED` 进入 failed 不重试；`STORE_BUSY` 重试 3 次后 failed；未列出的可重试码按退避重试；隔离只体现为 `quarantined` 计数变化，phase 不为 failed。
- [R28] 状态字段：完整同步成功后 lastSuccessAt 等于注入时钟时刻、lastErrorCode 为 null；因 50 往返上限结束或中途失败时 lastSuccessAt 不变；outboxLen/quarantined/openChoices 与最后一次 `sync.status` 返回一致。
- [R28] 退避与 426：连续网络失败的等待依次为 30 s、60 s、120 s…封顶 15 min（Fake 时钟断言），响应带 Retry-After 时以其为准；后台时不安排重试；426 后 phase=clientTooOld 且之后不再调用 prepare_push/push。
- [R28] needsKey：push 返回 `SYNC_KEY_VERSION_REJECTED` 且 `GET /v1/keys` 显示更高版本时 phase=needsKey；`provideKey(RecoveryCodeInput)` 委托 KeyService 后再次同步成功；`SYNC_QUOTA_EXCEEDED` 后不再推送但拉取继续。
- [R28] 并发头：Fake `sync.choices` 返回一条未决、一条已决记录时 `choices()` 只返回未决一条且 heads 与 heads_json 一致；`resolveChoice` 以 {choice_id, chosen} 调用 `sync.resolve_choice` 后触发一次同步；op 返回 `SYNC_CHOICE_INVALID` 时原样抛出；current=null 时两方法都不调用 op。
- [R28] 同步密语与日志：`setSyncPassphrase` 委托 KeyService 一次；全流程 AppLog 输出中不出现恢复码、同步密语、密钥字节与令牌（以注入的已知字符串扫描）；档案 order 70 钩子在每个新 handle 恰运行一次。
