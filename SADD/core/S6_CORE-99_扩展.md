### CORE-99 游客升级网络协调

**目标**：驱动CORE-24升级步进的网络往返，并在失败后续接，保留游客数据。

**范围**
- 包含：UpgradeCoordinator、NewAccount/MergeInto网络驱动、confirmSaved/askSecret、order30恢复钩子、完成后询问并触发同步。
- 不包含：本地升级日志/合并/加密（CORE-24及CORE-83）；KeyService（CORE-98）；同步循环/快照（CORE-46）；UpgradeFacade/选择类型定义（CORE-36）；登录注册内核（CORE-23）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-23、CORE-24、CORE-36、CORE-46、CORE-62、CORE-65、CORE-83、CORE-98

**接口契约**

```dart
// app/lib/sync/upgrade_coordinator.dart
abstract interface class UpgradeCoordinator implements UpgradeFacade {  // UpgradeFacade 由 CORE-36 定义
  Future<void> run(UpgradeChoice choice, {required Future<bool> Function(String recoveryCode) confirmSaved,
                   Future<KeySecretInput> Function()? askSecret /* mergeInto 必填 */});   // 内部映射为 CORE-24 的 UpgradeMode 与 KeySecret DTO
  Future<void> resumeIfPending();                     // ProfileHooks 每新 handle order 30
  Future<void> stopAndDrain(ProfileSession session);
}
final class DefaultUpgradeCoordinator implements UpgradeCoordinator {
  DefaultUpgradeCoordinator({required ProfileSessionSource sessions, required ApiClient api, required KeyService keys, required SyncFacade sync});
  // 实现 UpgradeCoordinator/UpgradeFacade 全部方法，不把迁移目标发布成交互会话
}
```

- 升级（`UpgradeCoordinator.run`）：`account.upgrade_begin` → NewAccount：CORE-23 `register` / MergeInto：`login` → `Identity` → NewAccount：`NewKey` → `confirmSaved` 为真后 `PUT /v1/keys/{v}/recovery_code` → `KeyUploaded`；MergeInto：`GET /v1/keys` + `askSecret` → `ExistingKey` → `Commit` → `Done` → CORE-23 询问是否开启同步，开启则 `syncNow(afterUpgrade)`。任一步失败保留日志，下次启动 `resumeIfPending` 继续。`{v}` 取 NewKey 返回的 `KeyOutput.key_version`；`upgrade_begin`、`upgrade_advance`、`upgrade_abandon` 请求体的 `now_ms` 由本卡读 Dart 时钟传入（CORE-24 核心不读时钟），`upgrade_advance` 走长任务提交。

**实现约束**
- run/resumeIfPending 门面入口捕获一个 sessions.current，null 不发网络/档案 op、不弹秘密确认，resumeIfPending 直接完成，run 以 StateError 拒绝本地调用前置条件（不新增业务错误码）；一次升级链只使用捕获 session.core。登录/注册 HTTP 响应、confirmSaved、askSecret、GET/PUT、每步 advance/merge 的 await 后与下一副作用前都检查对象身份+handle，同 profileId 重开也过代。按 handle 单飞，用户确认尚未完成而关闭时撤销待处理回调，不无限等待用户；迟到确认/秘密只释放或清零，不能推进 A、上传包装或驱动 B。
- MergeInto 的来源仍为捕获的游客信封 handle。CORE-24/83 所需目标 profile/DbKey 仅为迁移私有能力；account.upgrade_merge 自行临时开目标 Store、完成/异常/取消后关闭并清零，不通过 ProfileSessionHost 发布、不以目标替换 current、不跨库声称原子事务。Dart 自己持有的目标密钥/FFI 编码副本也 finally 清零；已交给核心的目标处理必须等其关闭确认才算排空。
- stopAndDrain 同步前缀拒绝新升级步骤、撤销确认/秘密回调并取消 HTTP/长任务，随后 await 已发核心事务/临时目标句柄/秘密清理；失败维持 closing/null，不释放来源或开 B。已完成日志步骤保留供原档案显式恢复，不因关闭回退状态机或丢游客数据。beforeClose 的所有同步取消前缀先发出再统一 await，不能等待另一个尚未启动的关闭回调。恢复码/秘密可变字节副本在成功/错误/取消/过代路径清零，String 仅释放引用。
- Done 后询问开启同步也受原 handle 栅栏保护；询问返回后再次核对 current 及该档案已完成升级的账户状态，才调用注入 sync.syncNow(SyncTrigger.afterUpgrade)。若升级按 CORE-65 流程换过交互 handle，旧 run 不继续触发同步，由新 handle 的恢复/完成确认接续；A 迟到完成不触发 B 的同步，不因同步模块缺失把已成功升级改失败。
- 安装点app/lib/sync/install_upgrade.dart的installUpgrade(CompositionContext ctx)从 ctx.features 取得 ProfileSessionSource、ApiClient、CORE-98 KeyService 与 CORE-46 SyncFacade，构造 DefaultUpgradeCoordinator(sessions: sessions, api: api, keys: keys, sync: sync)；同一对象登记 UpgradeCoordinator/UpgradeFacade。以 CORE-36 ProfileHooks.add 的 order 30、id upgrade.resume 登记 resumeIfPending（捕获 session，null 跳过，每个新 handle 一次，不登记普通 StartupHook），以 upgrade.coordinator 登记 sessions.addBeforeClose 的 stopAndDrain；CORE-46每档案appStart同步仍order70。顺序98→46→99，46不反向依赖本卡；FeatureInstallers登记片段由聚合维护者单写。
- run中NewAccount确认保存恢复码为真才上传包装并推进KeyUploaded；MergeInto必须askSecret，使用服务端包装记录与用户秘密导入；不为省规模改变升级日志状态机。任一步失败保留日志，重启resumeIfPending继续，失败期间游客数据可用。
- 网络经CORE-62 ApiClient，RequestPurpose.sync；恢复码/口令/密钥不进日志与崩溃报告，用后不再持有Dart字符串引用。
- CORE-36门面定义与平台/生命周期端口实现不迁；错误复用CORE-23/24/25/62/83/98消费集合，无本卡新增错误/表。无新增第三方依赖；fake服务端仅为自测。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-99_TEST.md](../Test/core/S6_CORE-99_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约245行；主包 `app/lib/sync/upgrade_coordinator.dart`225行（新增会话栅栏/确认撤销/关闭排空80），附属install_upgrade.dart/order30及聚合接入20行（新增关闭登记10）；本地升级日志/合并/加密、生成物、fixture与自测不计。单阶段在98/46之后独立构建，测试NewAccount/MergeInto逐步故障续接及完成后同步。
