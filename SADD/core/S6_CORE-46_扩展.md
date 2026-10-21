### CORE-46 同步网络协调与快照

**目标**：在 Dart 侧驱动同步与快照的网络往返：调用 CORE-25 接口，把结果交给 CORE-24、CORE-26 的本地步进 op，处理触发时机、重试、纪元与密钥异常，并向界面提供状态。

**范围**
- 包含：SyncApi的同步端点薄封装、SyncCoordinator拉取→推送/触发/退避/单飞/纪元异常、快照分片续传/校验/应用/上传提交，落实CORE-36 SyncFacade；密钥操作委托注入的CORE-98 KeyService。
- 不包含：KeyService/密钥API/恢复与轮换（CORE-98）；UpgradeCoordinator/升级网络步进与order30（CORE-99）；加密/合并/本地状态（CORE-24、CORE-26）；界面与门面定义（CORE-36）；服务端（CORE-25/66）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-23、CORE-25、CORE-26、CORE-36、CORE-62、CORE-66、CORE-78、CORE-98、CORE-65、CORE-28

**接口契约**

```dart
// app/lib/sync/sync_api.dart：CORE-25/66 同步及快照端点薄封装，均调用 CORE-62 ApiClient
final class SyncApi { SyncApi(ApiClient api); } // 端点 payload/错误逐字消费上述两来源卡，不另造 HTTP 模型
// app/lib/sync/sync_coordinator.dart
// SyncTrigger、SyncPhase、SyncStatus、UpgradeChoice、KeySecretInput 定义在 CORE-36 app/lib/composition/facades.dart，本卡直接使用
abstract interface class SyncCoordinator implements SyncFacade {        // SyncFacade 由 CORE-36 定义；provideKey / setSyncPassphrase / revokeDeviceAndRotate 委托 KeyService
  Stream<SyncStatus> get status;
  Future<SyncStatus> syncNow(SyncTrigger trigger);   // 同一时间只运行一次；并发调用合并为同一次
  Future<void> setEnabled(bool enabled);              // 写 CORE-23 sync_enabled；关闭时取消进行中的同步
  void attach(AppLifecycle lifecycle);                // resumed → syncNow(resumed)；paused → 取消
  Future<void> stopAndDrain(ProfileSession session);
}
final class DefaultSyncCoordinator implements SyncCoordinator {
  DefaultSyncCoordinator({required ProfileSessionSource sessions, required SyncApi api,
    required KeyService keys, required PlatformPorts ports});
  // 实现 SyncCoordinator / SyncFacade 全部方法，不缓存 root CoreBinding。
}

```

- 同步一次（`syncNow`）：① current=null、游客或未开启 → `disabled`，不发请求也不调用 sync op；② 循环 `GET /v1/sync/pull` → `sync.apply_pull { page, now_ms }`（now_ms 取 CORE-46 注入时钟的 UTC 毫秒），直到 `has_more = false`；③ 循环 `sync.prepare_push` → `POST /v1/sync/push` → `sync.ack`，直到无批次；④ 单次最多 50 个往返，超出则结束并在下次触发继续。新设备首次同步先 `GET /v1/sync/snapshots/latest`，有快照则把分片逐个下载为 `StoreArea.staging/snapshot-<id>/chunk-NNNN.bin`（校验 `sha256`，已存在且哈希相符的分片跳过以便续传）→ `sync.snapshot_apply { staging_root, in_dir, chunk_count, total_bytes, chunk_hashes, covers_through, key_version }`，成功或放弃后删除该目录，再从 `covers_through` 拉增量；上传方向由 `sync.snapshot_build { staging_root, out_dir }` 生成分片目录后逐片 `PUT …/chunks/{n}`，再 `commit`（CORE-66，ADR-V5-45）。staging_root 取 CORE-04 `LocalFileStore.root(StoreArea.staging)` 的绝对路径（ADR-V5-53）；快照目录名固定 `snapshot-<snapshot_id>`（构建方用新 UUID）。应用启动、任何同步开始之前调用一次 `sync.snapshot_cleanup { staging_root, older_than_ms: 86400000, now_ms }` 清理崩溃遗留目录，失败只记 warning 诊断不阻断同步。
- 异常处理：

| 情况 | 处理 |
| --- | --- |
| `NET_*`、5xx、`AUTH_RATE_LIMITED` | `offline` / 退避重试：30 s、60 s、120 s… 上限 15 min，仅在前台；`Retry-After` 优先 |
| 401 | `ApiClient` 刷新一次；仍失败 → `AUTH_REAUTH_REQUIRED`，回到登录，本地数据不动 |
| 426 | `clientTooOld`，停止同步写入 |
| `SYNC_EPOCH_STALE` | 读取错误体 `args.account_epoch`（十进制字符串）→ `sync.on_epoch_changed { server_epoch }` → 重新同步一次 |
| `SYNC_CURSOR_INVALID` | 带 `args.account_epoch` 时同 `SYNC_EPOCH_STALE` 处理；不带（游标损坏）时调用 `sync.on_epoch_changed` 传入本地当前纪元以清空游标与批次并重入队，再重新同步一次；同一轮再次失败 → `failed` |
| `SYNC_ENVELOPE_INVALID`、`SYNC_HASH_MISMATCH`、`SYNC_PAYLOAD_TOO_LARGE`（push） | 客户端编码缺陷：`failed`，记录 error 诊断，不重试、不丢弃批次（等待升级修复） |
| `SYNC_KEY_VERSION_REJECTED`、`SYNC_KEY_MISSING` | `GET /v1/keys`；本地缺少更高版本 → `needsKey`，界面引导输入恢复码或同步密语（`restoreOnNewDevice`） |
| `SYNC_QUOTA_EXCEEDED` | `failed`，停止推送，拉取照常 |
| `SYNC_BATCH_UNKNOWN`（`sync.ack`） | 批次已因纪元变化或密钥更新被作废，属良性：丢弃本次 ack 结果，继续下一轮 `sync.prepare_push`（重建批次中服务端已存的 op_id 返回 CONFLICT 并出队），记录 warning 诊断后不计失败、不退避，不重试旧 ack |

- 升级网络步进完整迁CORE-99；本卡只提供syncNow(afterUpgrade)消费入口，不调用或依赖升级协调器。

- 本卡仅在 CORE-36 ProfileHooks 登记档案 order70 的 syncNow(appStart)（每个新 handle 一次，不是进程 startup）；order30 resumeIfPending归CORE-99，不由S2外壳直接调用。

**实现约束**
- 安装点：app/lib/sync/install.dart的installSync(CompositionContext ctx)消费已登记的CORE-98 KeyService，构造 DefaultSyncCoordinator(sessions: ctx.features.require<ProfileSessionSource>(), api: SyncApi(apiClient), keys: keyService, ports: ctx.ports) 并以 SyncFacade/SyncCoordinator 登记、attach(ctx.ports.lifecycle)、登记档案 order70 及唯一 sync.coordinator beforeClose。不构造升级实现；CORE-99后装。FeatureInstallers聚合由聚合维护者单写，本卡计接入行。
- syncNow 开始只捕获一次 session/handle，account.state/sync_enabled 与所有 apply/prepare/ack/snapshot op 均用这个 session.core。每次 HTTP/FFI/文件 await 后先比较 identity/handle；旧响应不得落入新库、发新请求或发布成功/错误到新状态流。singleflight 的 key 是 handle；相同 handle 多触发合并，不能把 A 的 Future 交给 B。null 到来即状态 disabled、取消网络/长任务/退避计时器；stopAndDrain 等到所有旧 Future 及暂存清理完成，失败传给 close；B 打开前不会留下 A 的 ack。attach 同一生命周期只订阅一次，释放时取消订阅。
- setEnabled/密钥门面也在调用时捕获 session；current=null 回账户入口，游客不写注册设置、不发请求。setEnabled(false) 先禁止新同步并排空当前 handle 的 singleflight，再在同一仍有效 session 写 sync_enabled；不把停用当 SYNC_DISABLED 异常。SYNC_DISABLED 只由 CORE-26 低层 op 在显式禁用时返回，本卡按 disabled 状态收敛；SYNC_NOT_AVAILABLE 只归未安装占位门面。provideKey/setSyncPassphrase/revokeDeviceAndRotate 委托已注入 KeyService，不能自行跨 handle 重试。
- SYNC_BATCH_UNKNOWN 复用 CORE-26 的 warning / 不可重试：AppLog.event(LogLevel.warning, 'sync_batch_unknown', {LogKey.errorCode: LogCode('SYNC_BATCH_UNKNOWN')})，不输出 batch/key/token；不设置 failed/lastErrorCode，不触发错误弹窗/失败计数/退避，继续重新 prepare_push，受原 50 往返预算约束。
- 只在应用前台、启动/恢复时、升级完成后或用户手动触发时同步；不做常驻后台同步与周期轮询。
- 网络全部经 CORE-62 `ApiClient`（`RequestPurpose.sync`）；恢复码、口令、密钥不进日志与崩溃报告，Dart 字符串用后不再持有引用。
- 推送请求体以紧凑 JSON 发送（无空白、不转义 `/`，字段按 `sync.prepare_push` 返回的顺序），其字节数与 CORE-26 的 `max_bytes` 计量一致。
- 推送不发 Idempotency-Key；CORE-25按(account_epoch,op_id)与密文哈希幂等。batch_id只作客户端持久化批次标识，重试不重新加密。
- 外部前提：无新增第三方依赖；测试用内存版 CORE-25 服务端替身 `app/test/fakes/fake_sync_server.dart`（实现本卡用到的全部端点与错误码）。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-46_TEST.md](../Test/core/S6_CORE-46_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约620行；主包 `app/lib/sync/`。分阶段：① 同步 API、循环、单飞/世代隔离、状态/异常与生命周期安装（约380）；② 快照分片续传/校验/应用/上传提交与同步接入（约240），各阶段在 CORE-98 之后可独立构建测试。加密、合并、服务端、fixture、生成物与自测不计；密钥与升级实现仍归 CORE-98/99，不由本次生命周期新增重复实现。

