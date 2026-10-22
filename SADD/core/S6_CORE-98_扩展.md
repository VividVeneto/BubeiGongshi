### CORE-98 账户密钥网络生命周期

**目标**：协调包装记录上传下载、新设备密钥恢复、同步密语与设备吊销后轮换，不实现加密内核。

**范围**
- 包含：KeyService与keys三端点（`GET /v1/keys`、`PUT /v1/keys/{key_version}/{wrap_kind}`、`POST /v1/keys/min-version`）的唯一 HTTP 封装、新设备恢复/同步密语包装/设备吊销后轮换的网络步骤、min-version 提升入口、安装登记。
- 不包含：加密与本地密钥状态（CORE-21/23/24/26/78）；重排入队（CORE-66）；重加密批次的推送与结算及常规同步循环/快照（CORE-46）；游客升级流程（CORE-99）；CORE-36 端口/门面定义与平台实现；上文对 CORE-46/47/99 的分工描述均为下游说明，非契约。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-22、CORE-23、CORE-24、CORE-25、CORE-26、CORE-36、CORE-62、CORE-65、CORE-66、CORE-78

**接口契约**

```dart
// app/lib/sync/key_service.dart
enum KeyWrapKind { recoveryCode, syncPassphrase }        // 线上名 recovery_code / sync_passphrase（CORE-21）
final class KeyRecord { const KeyRecord({required this.keyVersion, required this.wrapKind, required this.recordBase64, required this.createdAt});
  final int keyVersion; final KeyWrapKind wrapKind; final String recordBase64; final String createdAt; }   // createdAt 保留服务端原字符串
final class KeyRecordSet { const KeyRecordSet({required this.minKeyVersion, required this.records});
  final int minKeyVersion; final List<KeyRecord> records; }

abstract interface class KeyService {
  Future<void> stopAndDrain(ProfileSession session);   // 先停止新推进，再排空旧 handle 的在途步骤
  Future<KeyRecordSet> fetchRecords();                 // GET /v1/keys → { min_key_version, records[] }
  Future<void> uploadWrapRecord({required int keyVersion, required KeyWrapKind kind, required String recordBase64});  // PUT /v1/keys/{keyVersion}/{kind} → 204
  Future<void> raiseMinKeyVersion(int minKeyVersion);  // POST /v1/keys/min-version { min_key_version } → 204（只增）
  Future<void> restoreOnNewDevice(KeySecretInput secret);   // fetchRecords → account.import_account_key
  Future<void> setSyncPassphrase(String passphrase);        // account.wrap_with_passphrase → uploadWrapRecord(syncPassphrase)
  Future<String> rotateAfterRevoke(String deviceId);        // DELETE /v1/devices/{id}（CORE-22）→ account.rotate_account_key → uploadWrapRecord(recoveryCode) → sync.reencrypt；返回新恢复码
}
final class DefaultKeyService implements KeyService {
  DefaultKeyService({required ProfileSessionSource sessions, required ApiClient api});
  // 三个 keys 方法全部转调本文件内私有 _KeysApi（三端点唯一实现，不导出）；实现上面全部方法，不缓存 root CoreBinding，不 import CORE-46（下游说明，非契约）
}
```

- KeySecretInput继续使用CORE-36定义，不迁移或重定义；SyncFacade/UpgradeFacade也留CORE-36。keys三端点只在本卡的 `_KeysApi` 实现一次：CORE-99 取包装记录与上传一律经 `fetchRecords/uploadWrapRecord`，界面与CORE-46只经CORE-36门面转到的本卡方法，不得自写 keys 请求（ADR-V5-60；本句对 CORE-99/46/47 的描述为下游说明，非契约）。
- keys 边界按CORE-25唯一定义：`fetchRecords` 期望200 `{min_key_version, records:[{key_version, wrap_kind, record_base64, created_at}]}`，`minKeyVersion ≥ 1`，`record_base64` 为CORE-21 WrapRecord CBOR的不透明标准base64；`wrap_kind` 只接受 `recovery_code|sync_passphrase`，其他值属编程错误按FormatException拒绝，不伪造业务码；`uploadWrapRecord` 请求体 `{"record_base64": <string>}`，同键覆盖（即重新包装），解码>4 KiB 时服务端413 `SYNC_PAYLOAD_TOO_LARGE` 原样上抛；`raiseMinKeyVersion` 请求体 `{"min_key_version": <u32>}`，服务端现值更大时仍204（幂等），请求值小于现值时409 `SYNC_KEY_VERSION_REJECTED` 原样上抛并由界面提示“已有更新版本”。401 按CORE-62刷新/重登规则（`AUTH_TOKEN_EXPIRED`/`AUTH_TOKEN_INVALID`/`AUTH_REAUTH_REQUIRED`），网络错误用CORE-04 `NET_*`；本卡不新增错误码。
- `restoreOnNewDevice`：`fetchRecords` → `account.import_account_key {account_id, records:[record_base64 原样], secret:{recovery_code}|{passphrase}}`（CORE-24）。`account_id` 取 `account.profiles`（CORE-23）中 `profile_id` 与本会话一致的档案的 `account_id`；导入返回的 `key_version` 只用本次调用，不落盘。`SYNC_UPGRADE_KEY_FAILED`、`CRYPTO_*`、`SYNC_KEY_MISSING` 原样透传，由界面区分“秘密不对”与“无可解密版本”。
- `setSyncPassphrase`：策略与KDF由CORE-21 `wrap_with_passphrase` 执行（`CRYPTO_PASSPHRASE_WEAK` 原样透传，回显在输入框），其返回 `record_base64` 直接上传；本卡不缓存口令、不写 `account_key_wrap`（CORE-24 是唯一写者）。
- `rotateAfterRevoke`：DELETE /v1/devices/{device_id}（204，吊销令牌族）→ `account.rotate_account_key {now_ms}` → `KeyOutput.key_version`/`wrap_record` → `uploadWrapRecord(recoveryCode)` → `sync.reencrypt {new_version}`（CORE-66，只入队不产生密文）→ 返回新恢复码。**本卡不做推送、不提min-version**：重加密批次的推送与结算归CORE-46，CORE-46 在该版本全部条目推送并ack完成后调用本卡 `raiseMinKeyVersion`（ADR-V5-60），由此保证“未推完不提升”；本卡因此不 import CORE-46、也不形成 98→46→98 环。轮换不保留同步密语：新版本只有 recovery_code 包装，已设密语的用户由CORE-47提示后自行调用 `setSyncPassphrase` 重新包装，本卡不索取、不缓存旧口令（与CORE-24:33、CORE-46:69同向；对 CORE-46/47 调用行为的描述为下游说明，非契约）。
- 重入：DELETE 已成功而 rotate 未完成的，重试先 `GET /v1/devices`（CORE-22 只返回未吊销设备）确认设备已不在列表再跳过 DELETE，从 `rotate_account_key` 起重入；rotate 已成功而上传未完成的，重试先 `fetchRecords` 查同版本 recovery_code 是否已在服务端，在则不重复上传。已提升的min-version不重复提升。

**实现约束**
- 每个公开方法入口捕获 sessions.current 并校验账户处于本操作允许状态；null/锁定不发 HTTP/档案 op，在入口以 StateError 拒绝本地调用前置条件（不新增业务错误码），UI转账户入口处理未就绪。一次 fetch→import、wrap→PUT、DELETE→rotate→PUT→reencrypt 全程只使用捕获 session.core，每个 HTTP/FFI await 后与下一副作用前核对对象身份+handle，不凭 profileId 相等接续。按 handle 串行密钥变更，重复点击同一动作单飞；A 的返回不能写 B 密钥、返回 B 恢复码或替 B 提升 min-version。
- stopAndDrain 同步前缀禁止旧 handle 新调用/后续步骤并取消请求和长任务，再等待在途本地事务/响应/清理全部落定；已提交的本地轮换与CORE-66入队保留原可重入状态，不伪称回滚、不继续推进剩余网络步骤；`raiseMinKeyVersion` 请求已发时记录原 handle 的已知/未知结果，不向 B 重发。排空失败上抛，宿主保持 closing/null，不释放 A、不打开 B；重试关闭只补未完清理。
- 输入/解包/FFI 编码形成的可变 Uint8List 密钥与秘密副本在成功、异常、取消、过代所有 finally 路径 fillRange 清零；包装密文可按既有协议保留，Dart 不可变恢复码/口令 String 只释放引用，不声称可清零。不向日志、错误详情或新会话 UI 泄露迟到秘密。
- 安装点 app/lib/sync/install_keys.dart 的 `installKeys(CompositionContext ctx)` 从 `ctx.features` 取 ProfileSessionSource 与 ApiClient，构造 `DefaultKeyService(sessions: sessions, api: api)`，以 KeyService 登记并以 `keys.lifecycle` 登记 `sessions.addBeforeClose` 的 `stopAndDrain`；任一依赖缺失则安装点抛 StateError（安装点失败即启动失败，不静默降级）。顺序CORE-98→CORE-46→CORE-99，FeatureInstallers片段由聚合维护者合入（安装顺序说明为下游说明，非契约）。
- 全部网络经ApiClient `RequestPurpose.sync`（`call('GET'|'PUT'|'POST', '/v1/keys…', json: …)`，CORE-62）；紧凑推送JSON/幂等与持久批次沿CORE-25/26；恢复码/口令/密钥不进日志或崩溃报告，Dart字符串用后不再持有引用。
- 平台/生命周期端口实现继续CORE-36，不把接口声明预算误作实现迁入；无新增第三方依赖，内存fake服务端仅是测试夹具。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-98_TEST.md](../Test/core/S6_CORE-98_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约310行；主包 `app/lib/sync/key_service.dart` 245行（会话捕获/串行/排空70、恢复/口令/轮换方法110、keys字段映射与会话核对65），`_KeysApi` 三端点封装45行，install_keys.dart及聚合接入20行；包装/轮换加密内核、CORE-66重排、CORE-46推送、服务端、生成物、fixture与自测不计。单阶段先于CORE-46独立构建测试恢复/口令/吊销轮换与三端点边界（对 CORE-46 的下游说明，非契约）。
