### CORE-46 同步网络协调与快照

**目标**：在 Dart 侧驱动同步与快照的网络往返：调用 CORE-25 接口，把结果交给 CORE-24、CORE-26 的本地步进 op，处理触发时机、重试、纪元与密钥异常，并向界面提供状态。

**范围**
- 包含：SyncApi的同步端点薄封装、SyncCoordinator拉取→推送/触发/退避/单飞/纪元异常、快照分片续传/校验/应用/上传提交，落实CORE-36 SyncFacade；密钥操作委托注入的CORE-98 KeyService。
- 不包含：KeyService/密钥API/恢复与轮换（CORE-98）；UpgradeCoordinator/升级网络步进与order30（CORE-99）；加密/合并/本地状态（CORE-24、CORE-26）；界面与门面定义（CORE-36）；服务端（CORE-25/66）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-23、CORE-25、CORE-26、CORE-36、CORE-62、CORE-66、CORE-78、CORE-98

**接口契约**

```dart
// app/lib/sync/sync_coordinator.dart
// SyncTrigger、SyncPhase、SyncStatus、UpgradeChoice、KeySecretInput 定义在 CORE-36 app/lib/composition/facades.dart，本卡直接使用
abstract interface class SyncCoordinator implements SyncFacade {        // SyncFacade 由 CORE-36 定义；provideKey / setSyncPassphrase / revokeDeviceAndRotate 委托 KeyService
  Stream<SyncStatus> get status;
  Future<SyncStatus> syncNow(SyncTrigger trigger);   // 同一时间只运行一次；并发调用合并为同一次
  Future<void> setEnabled(bool enabled);              // 写 CORE-23 sync_enabled；关闭时取消进行中的同步
  void attach(AppLifecycle lifecycle);                // resumed → syncNow(resumed)；paused → 取消
}

```

- 同步一次（`syncNow`）：① 未开启或游客 → `disabled`，不发请求；② 循环 `GET /v1/sync/pull` → `sync.apply_pull`，直到 `has_more = false`；③ 循环 `sync.prepare_push` → `POST /v1/sync/push` → `sync.ack`，直到无批次；④ 单次最多 50 个往返，超出则结束并在下次触发继续。新设备首次同步先 `GET /v1/sync/snapshots/latest`，有快照则把分片逐个下载为 `StoreArea.staging/snapshot-<id>/chunk-NNNN.bin`（校验 `sha256`，已存在且哈希相符的分片跳过以便续传）→ `sync.snapshot_apply { in_dir, chunk_count, total_bytes, chunk_hashes, covers_through, key_version }`，成功或放弃后删除该目录，再从 `covers_through` 拉增量；上传方向由 `sync.snapshot_build { out_dir }` 生成分片目录后逐片 `PUT …/chunks/{n}`，再 `commit`（CORE-66，ADR-V5-45）。
- 异常处理：

| 情况 | 处理 |
| --- | --- |
| `NET_*`、5xx、`AUTH_RATE_LIMITED` | `offline` / 退避重试：30 s、60 s、120 s… 上限 15 min，仅在前台；`Retry-After` 优先 |
| 401 | `ApiClient` 刷新一次；仍失败 → `AUTH_REAUTH_REQUIRED`，回到登录，本地数据不动 |
| 426 | `clientTooOld`，停止同步写入 |
| `SYNC_EPOCH_STALE` | 读取响应中的 `account_epoch` → `sync.on_epoch_changed` → 重新同步一次 |
| `SYNC_KEY_VERSION_REJECTED`、`SYNC_KEY_MISSING` | `GET /v1/keys`；本地缺少更高版本 → `needsKey`，界面引导输入恢复码或同步密语（`restoreOnNewDevice`） |
| `SYNC_QUOTA_EXCEEDED` | `failed`，停止推送，拉取照常 |
| `SYNC_BATCH_UNKNOWN`（`sync.ack`） | 批次已因纪元变化或密钥更新被作废，属良性：丢弃本次 ack 结果，继续下一轮 `sync.prepare_push`（重建批次中服务端已存的 op_id 返回 CONFLICT 并出队），不计失败、不退避 |

- 升级网络步进完整迁CORE-99；本卡只提供syncNow(afterUpgrade)消费入口，不调用或依赖升级协调器。

- 本卡仅登记order70的syncNow(appStart)；order30 resumeIfPending归CORE-99，不由S2外壳直接调用。

**实现约束**
- 安装点：app/lib/sync/install.dart的installSync(CompositionContext ctx)消费已登记的CORE-98 KeyService，构造SyncCoordinator并登记SyncFacade、attach(ctx.ports.lifecycle)及order70。不构造升级实现；CORE-99后装。FeatureInstallers聚合由聚合维护者单写，本卡计接入行。
- 只在应用前台、启动/恢复时、升级完成后或用户手动触发时同步；不做常驻后台同步与周期轮询。
- 网络全部经 CORE-62 `ApiClient`（`RequestPurpose.sync`）；恢复码、口令、密钥不进日志与崩溃报告，Dart 字符串用后不再持有引用。
- 推送请求体以紧凑 JSON 发送（无空白、不转义 `/`，字段按 `sync.prepare_push` 返回的顺序），其字节数与 CORE-26 的 `max_bytes` 计量一致。
- 推送不发 Idempotency-Key；CORE-25按(account_epoch,op_id)与密文哈希幂等。batch_id只作客户端持久化批次标识，重试不重新加密。
- 外部前提：无新增第三方依赖；测试用内存版 CORE-25 服务端替身 `app/test/fakes/fake_sync_server.dart`（实现本卡用到的全部端点与错误码）。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-46_TEST.md](../Test/core/S6_CORE-46_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约460行；主包 `app/lib/sync/`：同步API30、循环130、单飞/状态60、异常60、快照分片160、安装/生命周期及聚合20。单阶段在CORE-98之后独立构建/测试同步/快照/异常；加密、合并、服务端、fixture、生成物与自测不计。原835行另220归CORE-98、155归CORE-99。

