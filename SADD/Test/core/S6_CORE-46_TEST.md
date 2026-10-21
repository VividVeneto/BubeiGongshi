# CORE-46 测试方案

> 来源卡：[S6_CORE-46_扩展.md](../../core/S6_CORE-46_扩展.md)（同步网络协调与快照）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R28] 两台设备（同一进程内两个档案 + `fake_sync_server`）：设备 A 升级为注册并开启同步，设备 B 登录后用恢复码 `restoreOnNewDevice`，同步后公式与复习事件一致；服务端替身中只有包装记录与密文。
- [R28] 中断：推送响应丢失后重试同一批次，服务端返回原 `server_seq`，本地无重复；`SYNC_EPOCH_STALE` 后自动全量重传并成功。
- [R28] KeyService轮换/恢复由CORE-98验收；本卡对sync.ack返回SYNC_BATCH_UNKNOWN继续prepare_push重建，状态不变为failed、不退避、不计失败。
- [R26] 游客与未开启同步时，触发任意 `SyncTrigger` 均不产生请求（Fake `HttpTransport` 审计）。
- [R24] 刷新令牌失效时同步停止并回到登录，本地数据与 outbox 保持不变。

- [R12][R28] 两设备同步已保存两步calculation_plan，另一端重开与运行结果一致（复用CORE-48夹具）。
- [R28] 快照分片逐片SHA256校验/已有正确片复用续传，apply携带完整chunk_count/total_bytes/hashes/covers_through/key_version，成功或放弃清理目录；上传build逐片PUT再commit，随后增量无重复。单次50往返停止、singleflight合并、paused取消、Retry-After/前台退避/426/密钥与quota状态均满足契约。
