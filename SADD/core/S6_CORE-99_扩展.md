### CORE-99 游客升级网络协调

**目标**：驱动 CORE-24 升级步进的网络往返，并在失败后续接，保留游客数据。

**范围**
- 包含：UpgradeCoordinator；NewAccount/MergeInto 两条网络驱动路径；confirmSaved/askSecret/askCredentials/askEnableSync 回调消费；order30 恢复钩子；Done 后询问并开启同步。
- 不包含：本地升级日志/步进事务/密钥生成与导入/游客并入（CORE-23/24/83）；keys 端点与密钥网络生命周期（CORE-98）；同步循环、快照与min-version提升（CORE-46）；UpgradeFacade/选择与秘密类型定义（CORE-36）；注册登录用例与账户状态串行化（CORE-65）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-23、CORE-24、CORE-25、CORE-36、CORE-46、CORE-65、CORE-83、CORE-98

**接口契约**

```dart
// app/lib/sync/upgrade_coordinator.dart
abstract interface class UpgradeCoordinator implements UpgradeFacade {
  @override
  Future<void> run(UpgradeChoice choice, {required Future<bool> Function(String recoveryCode) confirmSaved,
                   Future<KeySecretInput> Function()? askSecret,           // mergeInto 必填
                   Future<UpgradeCredentials> Function()? askCredentials, // newAccount 必填
                   Future<bool> Function()? askEnableSync});              // Done 后至多询问一次
  @override
  Future<UpgradeResumeState> resumeIfPending();   // ProfileHooks 每新 handle order 30
  @override
  Future<void> abandonPending();                  // 取消：仅本地已提交（第 4 步）之前
  Future<void> stopAndDrain(ProfileSession session);
}
final class DefaultUpgradeCoordinator implements UpgradeCoordinator {
  DefaultUpgradeCoordinator({required ProfileSessionSource sessions, required AccountController account,
    required KeyService keys, required SyncFacade sync, required SecureKeyValueStore secureKeys});
  // secureKeys（CORE-04）仅用于解包目标档案 DbKey 别名 fml.<target_profile_id>.db，供 CORE-83 account.upgrade_merge 的 x-sensitive 参数
  // UpgradeCredentials/UpgradeResumeState/UpgradeChoice/KeySecretInput/SyncTrigger 全部取 CORE-36 定义，本卡不重定义
}
```

- 步进器以 `account.upgrade_status {}`（CORE-24，profile scope）取日志为唯一进度来源，按 `journal.step` 派生动作；同一 handle 同一时刻只有一条升级链。下表“第 n 步”按 CORE-24 `UpgradeStep` 的取值顺序编号（1 已准备、2 身份就绪、3 密钥就绪、4 本地已提交、5 已完成）：动作表（"推进"均指 `account.upgrade_advance`，长任务提交，`now_ms` 由本卡读 Dart 时钟）：

| journal.step | newAccount | mergeInto |
| --- | --- | --- |
| 无日志 | `account.upgrade_begin {mode:'new_account'}` → 见 Prepared | `account.upgrade_begin {mode:'merge_into'}` → 见 Prepared |
| Prepared | `askCredentials`（缺省则 run 抛 StateError）→ `account.registerForUpgrade` → 推进 `{identity:{account_id}}` | `account.loginForUpgrade` → 推进 `{identity:{account_id}}` |
| IdentityReady | 推进 `"new_key"` → `KeyOutput{key_version, recovery_code, wrap_record}`；`confirmSaved(recovery_code)` 为真才继续 | 走下一行合并动作（无新密钥） |
| Prepared/IdentityReady 的 mergeInto 收尾 | — | `keys.fetchRecords()` + `askSecret`（缺省则 run 抛 StateError）→ 推进 `{existing_key:{account_id, records:[record_base64 原样], secret}}` |
| KeyReady | `keys.uploadWrapRecord(keyVersion, recoveryCode, wrapRecord)` → 推进 `{key_uploaded:{key_version}}` | 同上收尾已进入合并 |
| 第 4 步（本地已提交，含 KeyUploaded 后） | 推进 `"commit"` | 本机已有该 account_id 的目标档案 → `account.upgrade_merge {target_profile_id, target_db_key}`（CORE-83，submit；`target_db_key` 由本卡经 `secureKeys` 解包别名 `fml.<target_profile_id>.db` 得到 32 字节，随调用交出并在 finally 清零；目标档案以 `account.profiles` 的 `Profile.account_id` 判定）；否则推进 `"commit"` |
| Done | 结束（不再推进） | 结束 |

- Done 后的“开启同步”只有本卡一处发生点（ADR-V5-60）：`askEnableSync` 为 null 或该档案 `Profile.sync_enabled` 已为真 → 不询问；否则询问至多一次，返回 true 时**先** `sync.setEnabled(true)`（CORE-46 写 `account.set_sync_enabled`，CORE-23 唯一存放处）**再** `sync.syncNow(SyncTrigger.afterUpgrade)`；`syncNow` 失败只作为非致命提示（`SyncStatus.lastErrorCode`），不改写升级结论、不回退 journal。询问由本卡发起、CORE-65 `register` 不再重复询问（CORE-65 变更单 CO-47-02 增 `promptEnableSync:false`）。
- 身份获取经 CORE-65 `registerForUpgrade({email,emailCode,password})` / `loginForUpgrade()`（变更单 CO-47-02）：只完成授权码+PKCE+令牌换取并返回 `{account_id, email_masked}`，不调用 `create_registered`、不打开/切换会话、不问是否开启同步；档案登记与本地提交留给 CORE-24 的 Commit 步骤。本卡不调用 CORE-23 之外的 Dart 接口，`AccountController.register/login`（会切换会话）在升级期间禁止调用，避免与写门和捕获 handle 冲突。
- MergeInto 的目标档案：只经 `account.upgrade_merge` 由核心临时打开目标库。`target_db_key` 按 CORE-83 契约为协调器注入的 x-sensitive 参数，本卡从 CORE-04 `SecureKeyValueStore` 解包别名 `fml.<target_profile_id>.db` 后立即交出，不缓存、不落盘、不写日志，成功后不再持有；解包失败（别名缺失/别名不对）按 CORE-04 错误原样上抛并放弃本次合并，不新建目标库、不改来源 guest。本卡不发布、不替换交互会话，`account.state` 仍报 UpgradingGuest 直到 Commit 完成。
- `resumeIfPending`：捕获 sessions.current 为 null → 返回 `UpgradeResumeState.none`（不发网络、不发档案 op）；`account.upgrade_status` 无日志或 step 已 Done → `none`；Prepared/IdentityReady → `needsUser`（不自动推进、不解除写门，由界面再走 `run` 收凭据）；第 3 步（KeyReady）→ 只走补传：CORE-24 变更单 CO-47-01 提出的「待上传包装记录」op（未在该卡定义前本卡不编码）取 `uploaded=0` 的 `recovery_code` 记录 → `keys.uploadWrapRecord` → 推进 `{key_uploaded:{key_version}}` → 推进 `"commit"` → `completed`；`account.upgrade_advance {new_key}` 返回 `SYNC_UPGRADE_STEP_INVALID`（已有 account_key）时，同样只转为补传已存包装记录，**绝不删除、替换或重新生成密钥**；第 4 步（本地已提交）→ 推进 `"commit"` → `completed`；任何步骤失败原样上抛，保留 journal 与写门，不改步、不清理密钥。
- 失败、取消与写门：升级期间 CORE-24 写门生效——读操作与设置页可用，业务写返回 `SYNC_UPGRADE_IN_PROGRESS`，游客数据不清除、不迁移半成品；`abandonPending` → `account.upgrade_abandon {now_ms}`，仅在第 4 步之前允许，之后返回 `SYNC_UPGRADE_NOT_ABANDONABLE` 且界面只提示“升级已提交，不能放弃”；step 已 Done 时 `abandonPending` 为 no-op（不报错）；放弃成功后恢复业务写、释放内存秘密。
- 恢复码只出现一次（CORE-24 只返回一次、不落盘）：本卡不缓存、不重放、不由恢复路径重建恢复码；`completed` 分支只可在界面提示“如未保存恢复码，可在同步设置中设置同步密语作为备用解锁方式”（调用 CORE-46 `setSyncPassphrase`），设备吊销后取得新恢复码走 CORE-47 设备页→CORE-46 `revokeDeviceAndRotate`→CORE-98（CORE-47 设备页路径为下游说明，非契约）。

**实现约束**
- 门面入口捕获 sessions.current：null 不发网络/档案 op，`resumeIfPending` 直接返回 `none`，`run`/`abandonPending` 以 StateError 拒绝；一次链只用捕获 session.core；每个 HTTP/FFI await 后与下一副作用前核对对象身份+handle，不凭 profileId 相等接续。按 handle 单飞，重复 `run`/`resumeIfPending` 单飞；A 的推进结果不写 B 的 journal、不向 B 上传包装记录、不给 B 发 `setEnabled`/`syncNow`；Done 后再核对 current 与账户状态才触发同步，若升级过程按 CORE-65 流程换过交互 handle，旧 run 不继续触发同步。
- 回调撤销：confirmSaved/askSecret/askCredentials/askEnableSync 在宿主关闭或会话过代时立即以 false/null 完成，`stopAndDrain` 不无限等待用户输入；已发出的网络请求取消后不重发到新 handle。`stopAndDrain` 同步前缀禁止旧 handle 新步骤，再等待在途步骤落定；已提交的 journal 步保持可重入，不伪称回滚。排空失败上抛，宿主保持 closing/null。
- 秘密处理：`UpgradeCredentials.password`、`KeySecretInput`、`KeyOutput.wrap_record` 与合并用的 `target_db_key` 字节副本只在栈上用，finally 清引用或 `fillRange` 清零；FRB/FFI 编码形成的可变 Uint8List 副本 fillRange 清零；Dart String 只释放引用，不声称可清零。不向日志、错误详情或新会话 UI 泄露迟到秘密。
- 安装点 app/lib/sync/install_upgrade.dart 的 `installUpgrade(CompositionContext ctx)` 从 `ctx.features` 取 ProfileSessionSource、AccountController、CORE-98 KeyService、CORE-46 SyncFacade 与 CORE-04 `SecureKeyValueStore`：任一缺失则只登记 `DisabledUpgradeFacade`（CORE-36:59，不抛错，由 composeApp ⑤ 取到 Disabled）；齐全则构造 `DefaultUpgradeCoordinator(sessions: …, account: …, keys: …, sync: …, secureKeys: …)`，以 UpgradeCoordinator/UpgradeFacade 登记，并以 `ProfileHooks.add(30, 'upgrade.resume', (session) async { await coordinator.resumeIfPending(); })` 登记恢复钩子（捕获 session，null 跳过，每新 handle 一次），以 `upgrade.coordinator` 登记 `sessions.addBeforeClose` 的 `stopAndDrain`。CORE-46 每档案 appStart 同步仍 order 70；顺序 CORE-98→CORE-46→CORE-99，installer 列表由聚合维护者合入。
- 网络全部经 CORE-98 KeyService 与 CORE-46 SyncFacade 发起，本卡不直接持有 ApiClient、不自写 keys 或同步端点（ADR-V5-60）；注册/登录网络由 CORE-65 负责。错误码只消费 CORE-23/24/25/62/65/83/98 的既有定义，本卡不新增错误、表或迁移。
- 平台/生命周期端口实现继续 CORE-36；无新增第三方依赖；测试中使用内存 fake（CORE-24/65/83/98/46 Fake）与同一 profileId 不同 handle 的假会话。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-99_TEST.md](../Test/core/S6_CORE-99_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约285行；主包 `app/lib/sync/upgrade_coordinator.dart` 260行（两条升级路径步进150、恢复与补传60、会话捕获/串行/取消与询问50），附属 `install_upgrade.dart` 及聚合接入25行；本地日志/合并/密钥内核算 CORE-24/83，同步与快照算 CORE-46，keys 端点算 CORE-98，fixture 与自测不计。单阶段，可先于 CORE-46 用 Fake SyncFacade 独立构建测试。
