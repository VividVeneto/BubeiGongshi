### CORE-98 账户密钥网络生命周期

**目标**：协调包装记录上传下载、新设备密钥恢复、同步密语与设备吊销后轮换，不实现加密内核。

**范围**
- 包含：KeyService及keys端点封装、恢复/口令包装/设备吊销后密钥轮换网络步骤、密文重加密推完再提升min_key_version、安装登记。
- 不包含：加密/本地状态（CORE-23/26/78）；常规同步循环/快照（CORE-46）；升级（CORE-99）；CORE-36端口/门面定义与平台实现。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-22、CORE-23、CORE-25、CORE-26、CORE-36、CORE-62、CORE-65、CORE-78

**接口契约**

```dart
// app/lib/sync/key_service.dart
abstract interface class KeyService {
  Future<void> stopAndDrain(ProfileSession session); // 先停止新推进，再排空旧 handle 的在途步骤
  Future<void> restoreOnNewDevice(KeySecretInput secret);  // GET /v1/keys → account.import_account_key
  Future<void> setSyncPassphrase(String passphrase);  // account.wrap_with_passphrase → PUT /v1/keys/{v}/sync_passphrase
  Future<String> rotateAfterRevoke(String deviceId);  // DELETE /v1/devices/{id}（CORE-22）→ account.rotate_account_key → 上传 → sync.reencrypt → 推送完毕后 POST /v1/keys/min-version；返回新恢复码
}
final class DefaultKeyService implements KeyService {
  DefaultKeyService({required ProfileSessionSource sessions, required ApiClient api});
  // 实现上面全部方法，不缓存 root CoreBinding，不依赖 CORE-46
}
```

- KeySecretInput继续使用CORE-36定义，不迁移或重定义；SyncFacade/UpgradeFacade也留CORE-36。KeyService唯一实现/keys API归本卡。
- rotateAfterRevoke只调用CORE-22/23/26/78本地op与CORE-25 API：DELETE设备→rotate_account_key→上传包装→sync.reencrypt→以本地prepare_push/POST/ack步进排空重加密批次→POST /v1/keys/min-version，随后返回新恢复码。这个受限轮换排空过程归本卡，不import或调用CORE-46 SyncCoordinator，不能形成98→46→98依赖环；常规同步/快照循环仍归46。错误/中断可重入，未推完不提升min-version。
- rotate_account_key、wrap_with_passphrase请求体的now_ms由本卡读Dart时钟传入（CORE-24不读时钟），二者与import_account_key均为长任务提交；上传路径的版本取rotate返回的key_version/KeyOutput.key_version。
- 新设备GET /v1/keys再import_account_key；设置口令用wrap_with_passphrase再PUT /v1/keys/{v}/sync_passphrase。服务端只有包装记录与密文，恢复前旧版本未结算批次按CORE-26失效重建。
- 不新增业务码；AUTH_*/SYNC_*/NET_*按CORE-22/23/25/26/62/78唯一定义透传。

**实现约束**
- 每个公开方法入口捕获 sessions.current 并校验账户处于本操作允许状态；null/锁定不发 HTTP/档案 op，在入口以 StateError 拒绝本地调用前置条件（不新增业务错误码），UI转账户入口处理未就绪。一次 GET→import、wrap→PUT、DELETE→rotate→上传→reencrypt→prepare_push/POST/ack→min-version 全程只使用捕获 session.core，每个 HTTP/FFI await 后与下一步之前核对对象身份+handle，不凭 profileId 相等接续。已有 API 幂等键、批次与加密算法不变。按 handle 串行密钥变更，重复点击同一动作单飞；A 的返回不能写 B 密钥、返回 B 恢复码或替 B 提升 min-version。
- stopAndDrain 同步前缀禁止旧 handle 新调用/后续步骤并取消请求和长任务，再等待在途本地事务/响应/清理全部落定；已提交的本地轮换与批次保留原可重入状态，不能伪称回滚或继续推进剩余网络步骤，未完全排空重加密绝不提升 min-version。若 min-version 请求已发则记录其原 handle 的已知/未知结果，后续仍按既有幂等恢复，不向 B 重发。排空失败上抛，宿主保持 closing/null，不释放 A、不打开 B；重试关闭只补未完清理。没有 CORE-46 协调器依赖，生命周期关闭不反向调用常规 sync。
- 输入/解包/FFI 编码形成的可变 Uint8List 密钥与秘密副本在成功、异常、取消、过代所有 finally 路径 fillRange 清零；包装密文可按既有协议保留，Dart 不可变恢复码/口令 String 只释放引用，不声称可清零。不向日志、错误详情或新会话 UI 泄露迟到秘密。
- 安装点app/lib/sync/install_keys.dart的installKeys(CompositionContext ctx)从 ctx.features 取 ProfileSessionSource/ApiClient，构造 DefaultKeyService(sessions: sessions, api: api)，登记 KeyService 并以 keys.lifecycle 登记 sessions.addBeforeClose 的 stopAndDrain；顺序CORE-98→CORE-46→CORE-99，FeatureInstallers片段由聚合维护者合入。
- 全部网络经ApiClient RequestPurpose.sync；紧凑推送JSON/幂等与持久批次沿CORE-25/26，重试不重新加密；恢复码/口令/密钥不进日志或崩溃报告，Dart字符串用后不再持有引用。
- 平台/生命周期端口实现继续CORE-36，不把接口声明预算误作实现迁入；无新增第三方依赖，内存fake服务端仅是测试夹具。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-98_TEST.md](../Test/core/S6_CORE-98_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约310行；主包 `app/lib/sync/key_service.dart`230行（新增会话捕获/串行/排空80）、keys端点封装60行、install_keys.dart及聚合接入20行（新增关闭登记10）；包装/轮换加密内核、服务端、生成物、fixture与自测不计。单阶段先于46独立构建测试恢复/口令/吊销轮换与min-version时序。
