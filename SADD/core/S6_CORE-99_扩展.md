### CORE-99 游客升级网络协调

**目标**：驱动CORE-24升级步进的网络往返，并在失败后续接，保留游客数据。

**范围**
- 包含：UpgradeCoordinator、NewAccount/MergeInto网络驱动、confirmSaved/askSecret、order30恢复钩子、完成后询问并触发同步。
- 不包含：本地升级日志/合并/加密（CORE-24及CORE-83）；KeyService（CORE-98）；同步循环/快照（CORE-46）；UpgradeFacade/选择类型定义（CORE-36）；登录注册内核（CORE-23）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-23、CORE-24、CORE-36、CORE-46、CORE-62、CORE-83、CORE-98

**接口契约**

```dart
// app/lib/sync/upgrade_coordinator.dart
abstract interface class UpgradeCoordinator implements UpgradeFacade {  // UpgradeFacade 由 CORE-36 定义
  Future<void> run(UpgradeChoice choice, {required Future<bool> Function(String recoveryCode) confirmSaved,
                   Future<KeySecretInput> Function()? askSecret /* mergeInto 必填 */});   // 内部映射为 CORE-24 的 UpgradeMode 与 KeySecret DTO
  Future<void> resumeIfPending();                     // 启动钩子
}
```

- 升级（`UpgradeCoordinator.run`）：`account.upgrade_begin` → NewAccount：CORE-23 `register` / MergeInto：`login` → `Identity` → NewAccount：`NewKey` → `confirmSaved` 为真后 `PUT /v1/keys/{v}/recovery_code` → `KeyUploaded`；MergeInto：`GET /v1/keys` + `askSecret` → `ExistingKey` → `Commit` → `Done` → CORE-23 询问是否开启同步，开启则 `syncNow(afterUpgrade)`。任一步失败保留日志，下次启动 `resumeIfPending` 继续。

**实现约束**
- 安装点app/lib/sync/install_upgrade.dart的installUpgrade(CompositionContext ctx)消费CORE-98 KeyService与CORE-46 SyncFacade，构造/登记UpgradeFacade，order30登记resumeIfPending；CORE-46的appStart同步仍order70。顺序98→46→99，46不反向依赖本卡；FeatureInstallers登记片段由聚合维护者单写。
- run中NewAccount确认保存恢复码为真才上传包装并推进KeyUploaded；MergeInto必须askSecret，使用服务端包装记录与用户秘密导入；不为省规模改变升级日志状态机。任一步失败保留日志，重启resumeIfPending继续，失败期间游客数据可用。
- 网络经CORE-62 ApiClient，RequestPurpose.sync；恢复码/口令/密钥不进日志与崩溃报告，用后不再持有Dart字符串引用。
- CORE-36门面定义与平台/生命周期端口实现不迁；错误复用CORE-23/24/25/62/83/98消费集合，无本卡新增错误/表。无新增第三方依赖；fake服务端仅为自测。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-99_TEST.md](../Test/core/S6_CORE-99_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约155行；主包 `app/lib/sync/upgrade_coordinator.dart`145行，附属install_upgrade.dart/order30及聚合接入10行；本地升级日志/合并/加密、生成物、fixture与自测不计。单阶段在98/46之后独立构建，测试NewAccount/MergeInto逐步故障续接及完成后同步。
