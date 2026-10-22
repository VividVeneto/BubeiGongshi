### CORE-47 设置页与账户安全界面

**目标**：提供设置页及其子页：外观（主题色与深浅色）、账户与设备管理、同步开关与状态、游客升级向导、恢复码与同步密语、导出与恢复、识别历史设置、提醒与关于。

**范围**
- 包含：`/settings` 及子路由 `/settings/account`、`/settings/devices`、`/settings/sync`、`/settings/upgrade`、`/settings/backup`、`/settings/history`、`/settings/reminders`、`/settings/privacy`、`/settings/about` 的页面与视图模型；外观只提供导航入口到CORE-58独立路由；升级向导（新建账户 / 并入已有账户）、恢复码展示与确认保存、needsKey 时的恢复码或同步密语输入、设备吊销后展示新恢复码；导出与恢复的选择、口令输入、预览与确认（调用 CORE-27 导出与 CORE-84 恢复 op，文件经 CORE-04 `DocumentPicker` 与 `FileExporter`）；识别历史 `keep_last` 设置与一键清空；关于页与开源许可。
- 不包含：门面与组装层（CORE-36）；同步/升级实现（CORE-46/99）；备份格式（CORE-27）与恢复实现（CORE-84）；识别历史 GC（CORE-85，低层契约 CORE-32）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-23、CORE-27、CORE-32、CORE-36、CORE-55、CORE-58、CORE-62、CORE-65、CORE-84

**接口契约**

```dart
// app/lib/settings/routes.dart（页面在 app/lib/ui/settings/，只收 VM 与 deps.ui）
List<GoRoute> settingsRoutes(AppDeps deps);                 // 追加到 CORE-36 composition/routes.dart（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
// app/lib/settings/view_models.dart（均为 ChangeNotifier，可脱离 Widget 单测）
final class SyncSettingsVm    { SyncSettingsVm(SyncFacade sync, AccountController account); SyncStatus get status; Future<void> toggle(bool on); Future<void> syncNow();
                                Future<void> provideKey(KeySecretInput secret); Future<void> setSyncPassphrase(String passphrase);
                                Future<List<({String choiceId, String itemId, List<String> heads})>> choices(); Future<void> resolveChoice(String choiceId, String chosenRevisionId); }
final class AccountSettingsVm { AccountSettingsVm(AccountController account, ProfileSessionSource sessions, SecureKeyValueStore keys); AccountState? get state;
                                Future<KeySecurityLevel?> securityLevel(); Future<void> logout({required bool deleteLocalData}); }
final class AboutInfo         { static const String appVersion = String.fromEnvironment('FML_APP_VERSION', defaultValue: '0.0.0-dev'); }
final class UpgradeWizardVm   { UpgradeWizardVm(UpgradeFacade upgrade); UpgradeStep get step; String? get recoveryCode; String? get errorCode; bool get savedChecked; bool get enableSyncQuestion;
                                Future<void> start(UpgradeChoice c); Future<void> submitCredentials(UpgradeCredentials credentials);
                                Future<void> confirmSaved(); Future<void> submitSecret(KeySecretInput secret);
                                Future<void> answerEnableSync(bool enable); Future<void> resume(); Future<void> abandon(); }
enum UpgradeStep { choose, credentials, showRecoveryCode, askSecret, running, done, askEnableSync, failed }
final class BackupVm          { BackupVm(ProfileSessionSource sessions, PlatformPorts ports); Future<void> export(BackupScopeDto scope, ExportProtectionDto protection);
                                Future<RestorePreviewDto> pickAndPrepare(ExportProtectionDto protection, RestoreModeDto mode); Future<void> commit(); Future<void> discard(); Future<void> stopAndDrain(ProfileSession session); Future<void> disposeAsync(); }
final class HistorySettingsVm { HistorySettingsVm(ProfileSessionSource sessions, HistoryKeyUnlocker keys); int get keepLast; Future<void> setKeepLast(int n); Future<void> clearAll(); Future<void> stopAndDrain(ProfileSession session); Future<void> disposeAsync(); }
final class DevicesVm         { DevicesVm(ApiClient api, SyncFacade sync); Future<List<DeviceDto>> load(); Future<String> revoke(String deviceId); }
// app/lib/settings/device_dto.dart：CORE-22 `GET /v1/devices` 响应项的手写 HTTP 模型（不是 FFI 生成类型），字段与 CORE-22 逐一对应，时间保留服务端原字符串
final class DeviceDto { const DeviceDto({required this.deviceId, required this.platform, required this.appVersion, required this.createdAt, required this.lastSeenAt, required this.current});
  final String deviceId, platform, appVersion, createdAt, lastSeenAt; final bool current;
  factory DeviceDto.fromJson(Map<String, Object?> json); }   // 缺字段或类型不符 → FormatException；DevicesVm 捕获后显示通用加载失败并允许重试，不伪造错误码
```

- op 与端点：备份 `backup.export`（CORE-27）、`backup.prepare_restore / commit_restore / discard_restore`（CORE-84）；识别历史 `recog.settings.get / set` 与 `HistoryKeyUnlocker.clearAll()`（CORE-32，`HistoryKeyUnlocker` 从 `AppDeps.features` 取）；设备 `GET /v1/devices`（CORE-22）与 `SyncFacade.revokeDeviceAndRotate`。`BackupScopeDto`、`ExportProtectionDto`、`RestorePreviewDto`、`RestoreModeDto` 为 CORE-67 按 `contracts/dto` 生成的 FFI 类型（对应 schema 仍为 pending，随 CORE-27/84 编码补齐）；`DeviceDto` 是本卡手写的 HTTP 模型（见上）。
- 错误码：不新增；只按 CORE-02 的统一 FmlException.code 消息映射展示，来源为已依赖的 CORE-04（`PLATFORM_*`）、CORE-21（经 CORE-27/84/98 透传的 `CRYPTO_PASSPHRASE_WEAK`、`CRYPTO_RECOVERY_CODE_FORMAT` 等）、CORE-27、CORE-84、CORE-32、CORE-36、CORE-62（`AUTH_REAUTH_REQUIRED`、`SERVER_CLIENT_TOO_OLD`，设备列表与吊销请求）、CORE-65。同步/升级页面经 SyncFacade 提供状态与回调，状态含错误码时也用同一映射，不消费 CORE-46 私有错误表。

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/settings/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/settings/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

产品约束追踪：见README §6 Q13、Q19、Q20、Q27；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 设置首页第一组为“外观”，展示当前预设/模式并导航到CORE-58唯一的/settings/appearance；页面、AppearancePicker及触感开关均由58提供，本卡仅验收入口导航。
- 平台设置项：设置首页在“关于”之前按 `order` 渲染 `deps.features.require<SettingsSections>().items`（CORE-36）的 `build` 结果，标题取 `titleKey`；本卡不认识具体平台项。
- 恢复码只在 `showRecoveryCode` 步骤显示一次，离开页面后从内存清除；用户须勾选“已保存”才能继续。不设防截屏（README §6 Q41）。
- 升级向导与门面回调的桥接（本卡只做界面侧，语义与错误归 CORE-99/24/36）：`start(choice)` 调 `upgrade.run(choice, confirmSaved: …, askCredentials: …, askSecret: …, askEnableSync: …)`，四个回调各返回一个由 VM 持有的 `Completer.future`；门面调用某回调时 VM 才把 `step` 切到 `credentials`/`showRecoveryCode`/`askSecret`/`askEnableSync` 并通知界面，对应的 `submitCredentials/confirmSaved/submitSecret/answerEnableSync` 完成该 completer 后回到 `running`；不得自行推断步骤或重复调用 `run`。`confirmSaved` 仅在勾选“已保存”后完成（未勾选为 false 时门面不推进，停留在 `showRecoveryCode`）。`run` 抛错 → `failed`，显示按 CORE-02 映射的错误码并只提供“继续”（重新 `run`）与“放弃”（`abandon`）两个动作；升级已本地提交后放弃被拒（`SYNC_UPGRADE_NOT_ABANDONABLE`）时提示“升级已提交，不能放弃”并隐藏放弃按钮。离开页面或会话过代时，未完成的 completer 以 false/null 完成，不停等用户输入。
- 开启同步询问：`askEnableSync` 被调用时进入 `askEnableSync` 步，显示一次“升级完成，是否开启同步？”（开启/暂不开启两个动作，默认不开启）。选“开启”调 `answerEnableSync(true)`，由门面先 `setEnabled(true)` 再 `syncNow(SyncTrigger.afterUpgrade)`，本卡不直接调 `setEnabled/syncNow`；同步失败只显示“已开启同步，首次同步失败：<映射文案>，可稍后手动同步”，升级仍显示完成。
- 升级恢复入口：进入升级页时调用 `resume()`（内部 `resumeIfPending()`）——返回 `needsUser` 显示“上次升级未完成”与“继续”（重新进入 `choose`，须选与上次相同的升级方式；选错时门面报错，按映射显示“请选择与上次相同的升级方式”），返回 `completed` 直接显示 `done`（不再显示恢复码），返回 `none` 不显示该入口。
- 备份范围与闭包（CORE-27，ADR-V5-44）：范围选择处固定提示“所选范围引用到的公式/单位会一并导出”；导出完成后用 `manifest.closure_added` 显示实际带出的条数；恢复预览显示 `manifest.closure_added`，并说明“被带出的公式/单位只补充缺失项，不会覆盖或删除本机已有内容”。`backup.commit_restore` 是长任务：界面观察不到事务何时开始（CORE-03 只在结束时返回），因此进行中“取消”按钮始终可点；点击后调用取消，若任务仍以成功结束（事务已开始、取消无效），展示成功报告并附“恢复已完成，未能取消”提示，若返回 `BACKUP_CANCELLED` 则显示“已取消，原数据未改变”。
- 导出口令须经两次输入一致并调用backup.export，由CORE-27在写文件之前执行CORE-21 check_passphrase_policy；CRYPTO_PASSPHRASE_WEAK回显在口令框，不在Dart复制策略；恢复先选择 Merge/Replace 再 `prepare_restore`（预览按所选模式计算），显示预览（条目数、时间、范围、replaced、kept_local、可能重复的公式对数 possible_duplicates 与缺失资源包列表 missing_packs，后两项非空时单独提示“不会自动合并”“重新安装资源包后自动关联”），用户确认后才 `commit_restore`；同步已开启时 Replace 选项禁用并说明须先关闭同步（`BACKUP_REPLACE_BLOCKED_BY_SYNC` 作为后备映射），`BACKUP_WRONG_SECRET` 回显在口令框并允许重输，`BACKUP_TOKEN_UNKNOWN`（预览超过 30 分钟）提示重新选择文件，改选模式须 discard 后重新 prepare；离开页面自动 `discard_restore`。导出保护可选口令或恢复码：恢复码入口仅对已注册账户显示，游客隐藏（`BACKUP_PROTECTION_UNAVAILABLE` 作为后备映射）。请求体的 now_ms 取 PlatformPorts 时钟，staging_root 取 CORE-04 StoreArea.staging，commit 的 day 取当前档案学习设置中的 StudyDay（与 srs.due_queue 调用方同源）。
- `keep_last` 控件限制在 0–100，并说明“0 表示识别完成后不保留历史”。
- 账户页 `/settings/account`：显示账户状态；`securityLevel()` 以当前 session 的 `fml.<profileId>.db` 别名调用 CORE-04 `SecureKeyValueStore.securityLevel`（current=null 返回 null 且不调用），结果为 `software` 时显示“本机密钥保护能力较弱”及原因“此设备未提供硬件密钥保护”（AND-06 指派文案，下游说明，非契约）；并始终显示“恢复出厂或清除应用数据会丢失本机密钥，请保存恢复码或定期导出备份”。退出登录提供“仅锁定”与“删除本机数据”两项，后者二次确认后才调用 `logout(deleteLocalData: true)`。
- needsKey 与同步密语（`/settings/sync`）：phase 为 needsKey 时显示输入卡，可选恢复码或同步密语后调用 `provideKey`；“设置同步密语”表单两次输入一致后调用 `setSyncPassphrase`，`CRYPTO_PASSPHRASE_WEAK` 回显在输入框。设备页吊销成功后按恢复码同一规则显示新恢复码（须勾选已保存），并提示“原同步密语不适用于新密钥，请重新设置同步密语”且提供直达按钮（直达“设置同步密语”表单，提交经 `SyncFacade.setSyncPassphrase` → CORE-98 `setSyncPassphrase`）。升级 `done` 步在用户未保存恢复码时作同一提示的只读文案“如未保存恢复码，可在此设置同步密语作为备用解锁方式”，不重建、不重放恢复码。
- 修订选择：`status.openChoices > 0` 时同步页显示“有 n 处公式修订冲突待选择”入口，子页列出 `choices()` 的每条（公式与各头修订），用户选定后调用 `resolveChoice`；`SYNC_CHOICE_INVALID` 时刷新列表。
- 提醒、隐私与关于：`/settings/reminders` 只重定向到 `/study/reminder`（CORE-90 提供，下游说明，非契约；未追加时设置项置灰），`/settings/privacy` 只重定向到 `/privacy`（CORE-63 提供，下游说明，非契约），本卡不复制其内容；关于页显示 `AboutInfo.appVersion`（发布构建由 `--dart-define=FML_APP_VERSION` 注入，与 AND-09 的 User-Agent 版本同源（下游说明，非契约），未注入时为 0.0.0-dev）并以 Flutter `showLicensePage` 展示开源许可。
- settingsRoutes 在特性层以 deps.sessions 构造 BackupVm/HistorySettingsVm，监听 changes 及 beforeClose，VM key 用 session identity/handle；null 立即禁用操作、清掉口令/恢复码/预览，再排空旧操作并重建新 VM；不能仅按 profileId 复用。Sync/Upgrade/Devices 等 VM 同样隔离旧回调，Widget 不取裸 source/core。
- 每次 backup/history 调用捕获当前 session.core；null 不调用 profile op，返回账户入口。文件选择、导出、prepare、commit、设置及 keys.ensure 后均核对世代再发下一调用/显示结果；restore_token 与预览私有绑定原 handle。切换/离页时等待 prepare 返回，若得到 token 仅用原 core discard；不能把 A token 交给 B。commit/discard 同一 token 串行且互斥，commit 已进事务不可取消时必须等待完成再允许 close；结果过期不发布到 B。disposeAsync/stopAndDrain await 长任务取消、token discard、临时文件清理，失败阻止释放旧句柄而不吞掉；普通 ChangeNotifier.dispose 仅做同步UI解绑，不替代异步资源关闭。
- HistorySettingsVm 的 setKeepLast/clearAll 串行，ensure→设置/清空全程一个 handle；UI 重复点击合并/禁用，不并发轮换。迟到 load/revoke/向导确认不更新新档案，口令字节副本 finally 清零、String 释放引用，不声称可清零。
- 游客设置页显示“游客：无内容上传”，隐藏同步、设备与云识别项；页面只收 VM 与 `deps.ui`，`AppDeps` 只在 `app/lib/settings/routes.dart` 使用。
- 设置主页含“资源包”一项，跳转 `/packs`（CORE-51 提供；该路由未追加时置灰，同 CORE-36 主导航规则）。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-47_TEST.md](../Test/core/S6_CORE-47_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 795 行；用例/状态目录 `app/lib/settings/`；`app/lib/ui/settings/`。分阶段：① 设置首页与账户/同步/设备/升级（routes 骨架与首页、Sync/Upgrade/Devices/Account/needsKey 的视图模型与页面、DeviceDto、修订选择子页约20、升级向导回调桥接与开启同步询问约20，约 500）；② 备份、识别历史、提醒、隐私与关于（视图模型、页面与子路由登记，约 295，其中备份VM/长任务/令牌清理约90，历史VM/密钥串行与异步释放约50，备份/历史页面约90，提醒/隐私重定向与关于页及子路由约65；包含本次新增世代隔离与beforeClose逻辑，不另藏附属行）。

---

