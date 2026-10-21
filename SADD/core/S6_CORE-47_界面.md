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
final class SyncSettingsVm    { SyncSettingsVm(SyncFacade sync, AccountController account); SyncStatus get status; Future<void> toggle(bool on); Future<void> syncNow(); }
final class UpgradeWizardVm   { UpgradeWizardVm(UpgradeFacade upgrade); UpgradeStep get step; String? get recoveryCode; Future<void> start(UpgradeChoice c); Future<void> confirmSaved(); }
enum UpgradeStep { choose, credentials, showRecoveryCode, askSecret, running, done, failed }
final class BackupVm          { BackupVm(ProfileSessionSource sessions, PlatformPorts ports); Future<void> export(BackupScopeDto scope, ExportProtectionDto protection);
                                Future<RestorePreviewDto> pickAndPrepare(ExportProtectionDto protection, RestoreModeDto mode); Future<void> commit(); Future<void> discard(); Future<void> stopAndDrain(ProfileSession session); Future<void> disposeAsync(); }
final class HistorySettingsVm { HistorySettingsVm(ProfileSessionSource sessions, HistoryKeyUnlocker keys); int get keepLast; Future<void> setKeepLast(int n); Future<void> clearAll(); Future<void> stopAndDrain(ProfileSession session); Future<void> disposeAsync(); }
final class DevicesVm         { DevicesVm(ApiClient api, SyncFacade sync); Future<List<DeviceDto>> load(); Future<String> revoke(String deviceId); }
```

- op 与端点：备份 `backup.export`（CORE-27）、`backup.prepare_restore / commit_restore / discard_restore`（CORE-84）；识别历史 `recog.settings.get / set` 与 `HistoryKeyUnlocker.clearAll()`（CORE-32，`HistoryKeyUnlocker` 从 `AppDeps.features` 取）；设备 `GET /v1/devices`（CORE-22）与 `SyncFacade.revokeDeviceAndRotate`。`BackupScopeDto`、`ExportProtectionDto`、`RestorePreviewDto`、`RestoreModeDto`、`DeviceDto` 为 `contracts/` 生成类型。
- 错误码：不新增；只按 CORE-02 的统一 FmlException.code 消息映射展示，来源为已依赖的 CORE-04（`PLATFORM_*`）、CORE-27、CORE-84（含其透传的 CORE-21 `CRYPTO_PASSPHRASE_WEAK`、`CRYPTO_RECOVERY_CODE_FORMAT`）、CORE-32、CORE-36、CORE-65。同步/升级页面经 SyncFacade 提供状态与回调，状态含错误码时也用同一映射，不消费 CORE-46 私有错误表。

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/settings/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/settings/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

产品约束追踪：见README §6 Q13、Q19、Q20、Q27；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 设置首页第一组为“外观”，展示当前预设/模式并导航到CORE-58唯一的/settings/appearance；页面、AppearancePicker及触感开关均由58提供，本卡仅验收入口导航。
- 平台设置项：设置首页在“关于”之前按 `order` 渲染 `deps.features.require<SettingsSections>().items`（CORE-36）的 `build` 结果，标题取 `titleKey`；本卡不认识具体平台项。
- 恢复码只在 `showRecoveryCode` 步骤显示一次，离开页面后从内存清除；用户须勾选“已保存”才能继续。不设防截屏（README §6 Q41）。
- 备份范围与闭包（CORE-27，ADR-V5-44）：范围选择处固定提示“所选范围引用到的公式/单位会一并导出”；导出完成后用 `manifest.closure_added` 显示实际带出的条数；恢复预览显示 `manifest.closure_added`，并说明“被带出的公式/单位只补充缺失项，不会覆盖或删除本机已有内容”。`backup.commit_restore` 是长任务：提交事务开始前可取消，开始后“取消”按钮置灰并显示进行中，结果以报告展示。
- 导出口令须经两次输入一致并调用backup.export，由CORE-27在写文件之前执行CORE-21 check_passphrase_policy；CRYPTO_PASSPHRASE_WEAK回显在口令框，不在Dart复制策略；恢复先选择 Merge/Replace 再 `prepare_restore`（预览按所选模式计算），显示预览（条目数、时间、范围、replaced/kept_local），用户确认后才 `commit_restore`，改选模式须 discard 后重新 prepare；离开页面自动 `discard_restore`。导出保护可选口令或恢复码：恢复码入口仅对已注册账户显示，游客隐藏（`BACKUP_PROTECTION_UNAVAILABLE` 作为后备映射）。请求体的 now_ms 取 PlatformPorts 时钟，staging_root 取 CORE-04 StoreArea.staging，commit 的 day 取当前档案学习设置中的 StudyDay（与 srs.due_queue 调用方同源）。
- `keep_last` 控件限制在 0–100，并说明“0 表示识别完成后不保留历史”。
- settingsRoutes 在特性层以 deps.sessions 构造 BackupVm/HistorySettingsVm，监听 changes 及 beforeClose，VM key 用 session identity/handle；null 立即禁用操作、清掉口令/恢复码/预览，再排空旧操作并重建新 VM；不能仅按 profileId 复用。Sync/Upgrade/Devices 等 VM 同样隔离旧回调，Widget 不取裸 source/core。
- 每次 backup/history 调用捕获当前 session.core；null 不调用 profile op，返回账户入口。文件选择、导出、prepare、commit、设置及 keys.ensure 后均核对世代再发下一调用/显示结果；restore_token 与预览私有绑定原 handle。切换/离页时等待 prepare 返回，若得到 token 仅用原 core discard；不能把 A token 交给 B。commit/discard 同一 token 串行且互斥，commit 已进事务不可取消时必须等待完成再允许 close；结果过期不发布到 B。disposeAsync/stopAndDrain await 长任务取消、token discard、临时文件清理，失败阻止释放旧句柄而不吞掉；普通 ChangeNotifier.dispose 仅做同步UI解绑，不替代异步资源关闭。
- HistorySettingsVm 的 setKeepLast/clearAll 串行，ensure→设置/清空全程一个 handle；UI 重复点击合并/禁用，不并发轮换。迟到 load/revoke/向导确认不更新新档案，口令字节副本 finally 清零、String 释放引用，不声称可清零。
- 游客设置页显示“游客：无内容上传”，隐藏同步、设备与云识别项；页面只收 VM 与 `deps.ui`，`AppDeps` 只在 `app/lib/settings/routes.dart` 使用。
- 设置主页含“资源包”一项，跳转 `/packs`（CORE-51 提供；该路由未追加时置灰，同 CORE-36 主导航规则）。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-47_TEST.md](../Test/core/S6_CORE-47_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 790 行；用例/状态目录 `app/lib/settings/`；`app/lib/ui/settings/`。分阶段：① 设置首页与账户/同步/设备/升级（routes 骨架与首页、Sync/Upgrade/Devices/Account/needsKey 的视图模型与页面，约 480）；② 备份、识别历史、提醒、隐私与关于（视图模型、页面与子路由登记，约 310，其中备份VM/长任务/令牌清理约90，历史VM/密钥串行与异步释放约50，备份/历史页面约90，提醒/隐私/关于及子路由约80；包含本次新增世代隔离与beforeClose逻辑，不另藏附属行）。

---

