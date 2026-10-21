### CORE-98 账户密钥网络生命周期

**目标**：协调包装记录上传下载、新设备密钥恢复、同步密语与设备吊销后轮换，不实现加密内核。

**范围**
- 包含：KeyService及keys端点封装、恢复/口令包装/设备吊销后密钥轮换网络步骤、密文重加密推完再提升min_key_version、安装登记。
- 不包含：加密/本地状态（CORE-23/26/78）；常规同步循环/快照（CORE-46）；升级（CORE-99）；CORE-36端口/门面定义与平台实现。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-22、CORE-23、CORE-25、CORE-26、CORE-36、CORE-62、CORE-78

**接口契约**

```dart
// app/lib/sync/key_service.dart
abstract interface class KeyService {
  Future<void> restoreOnNewDevice(KeySecretInput secret);  // GET /v1/keys → account.import_account_key
  Future<void> setSyncPassphrase(String passphrase);  // account.wrap_with_passphrase → PUT /v1/keys/{v}/sync_passphrase
  Future<String> rotateAfterRevoke(String deviceId);  // DELETE /v1/devices/{id}（CORE-22）→ account.rotate_account_key → 上传 → sync.reencrypt → 推送完毕后 POST /v1/keys/min-version；返回新恢复码
}
```

- KeySecretInput继续使用CORE-36定义，不迁移或重定义；SyncFacade/UpgradeFacade也留CORE-36。KeyService唯一实现/keys API归本卡。
- rotateAfterRevoke只调用CORE-22/23/26/78本地op与CORE-25 API：DELETE设备→rotate_account_key→上传包装→sync.reencrypt→以本地prepare_push/POST/ack步进排空重加密批次→POST /v1/keys/min-version，随后返回新恢复码。这个受限轮换排空过程归本卡，不import或调用CORE-46 SyncCoordinator，不能形成98→46→98依赖环；常规同步/快照循环仍归46。错误/中断可重入，未推完不提升min-version。
- 新设备GET /v1/keys再import_account_key；设置口令用wrap_with_passphrase再PUT /v1/keys/{v}/sync_passphrase。服务端只有包装记录与密文，恢复前旧版本未结算批次按CORE-26失效重建。
- 不新增业务码；AUTH_*/SYNC_*/NET_*按CORE-22/23/25/26/62/78唯一定义透传。

**实现约束**
- 安装点app/lib/sync/install_keys.dart的installKeys(CompositionContext ctx)只构造/登记KeyService；顺序CORE-98→CORE-46→CORE-99，FeatureInstallers片段由聚合维护者合入。
- 全部网络经ApiClient RequestPurpose.sync；紧凑推送JSON/幂等与持久批次沿CORE-25/26，重试不重新加密；恢复码/口令/密钥不进日志或崩溃报告，Dart字符串用后不再持有引用。
- 平台/生命周期端口实现继续CORE-36，不把接口声明预算误作实现迁入；无新增第三方依赖，内存fake服务端仅是测试夹具。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-98_TEST.md](../Test/core/S6_CORE-98_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约220行；主包 `app/lib/sync/key_service.dart`150行、keys端点封装60行、install_keys.dart及聚合接入10行；包装/轮换加密内核、服务端、生成物、fixture与自测不计。单阶段先于46独立构建测试恢复/口令/吊销轮换与min-version时序。
