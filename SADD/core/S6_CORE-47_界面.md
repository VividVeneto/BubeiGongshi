### CORE-47 设置页与账户安全界面

**目标**：提供设置页及其子页：外观（主题色与深浅色）、账户与设备管理、同步开关与状态、游客升级向导、恢复码与同步密语、导出与恢复、识别历史设置、提醒与关于。

**范围**
- 包含：`/settings` 及子路由 `/settings/account`、`/settings/devices`、`/settings/sync`、`/settings/upgrade`、`/settings/backup`、`/settings/history`、`/settings/reminders`、`/settings/privacy`、`/settings/about` 的页面与视图模型；外观只提供导航入口到CORE-58独立路由；升级向导（新建账户 / 并入已有账户）、恢复码展示与确认保存、needsKey 时的恢复码或同步密语输入、设备吊销后展示新恢复码；导出与恢复的选择、口令输入、预览与确认（调用 CORE-27 op，文件经 CORE-04 `DocumentPicker` 与 `FileExporter`）；识别历史 `keep_last` 设置与一键清空；关于页与开源许可。
- 不包含：门面与组装层（CORE-36）；同步与升级逻辑（CORE-46）；备份格式与恢复逻辑（CORE-27）；识别历史 GC（CORE-32）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-23、CORE-27、CORE-32、CORE-36、CORE-55、CORE-58、CORE-62、CORE-65

**接口契约**

```dart
// app/lib/settings/routes.dart（页面在 app/lib/ui/settings/，只收 VM 与 deps.ui）
List<GoRoute> settingsRoutes(AppDeps deps);                 // 追加到 CORE-36 composition/routes.dart（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
// app/lib/settings/view_models.dart（均为 ChangeNotifier，可脱离 Widget 单测）
final class SyncSettingsVm    { SyncSettingsVm(SyncFacade sync, AccountController account); SyncStatus get status; Future<void> toggle(bool on); Future<void> syncNow(); }
final class UpgradeWizardVm   { UpgradeWizardVm(UpgradeFacade upgrade); UpgradeStep get step; String? get recoveryCode; Future<void> start(UpgradeChoice c); Future<void> confirmSaved(); }
enum UpgradeStep { choose, credentials, showRecoveryCode, askSecret, running, done, failed }
final class BackupVm          { BackupVm(CoreBinding core, PlatformPorts ports); Future<void> export(BackupScopeDto scope, String password);
                                Future<RestorePreviewDto> pickAndPrepare(String secret); Future<void> commit(RestoreModeDto mode); Future<void> discard(); }
final class HistorySettingsVm { HistorySettingsVm(CoreBinding core, HistoryKeyUnlocker keys); int get keepLast; Future<void> setKeepLast(int n); Future<void> clearAll(); }
final class DevicesVm         { DevicesVm(ApiClient api, SyncFacade sync); Future<List<DeviceDto>> load(); Future<String> revoke(String deviceId); }
```

- op 与端点：备份 `backup.export / prepare_restore / commit_restore / discard_restore`（CORE-27）；识别历史 `recog.settings.get / set` 与 `HistoryKeyUnlocker.clearAll()`（CORE-32，`HistoryKeyUnlocker` 从 `AppDeps.features` 取）；设备 `GET /v1/devices`（CORE-22）与 `SyncFacade.revokeDeviceAndRotate`。`BackupScopeDto`、`RestorePreviewDto`、`RestoreModeDto`、`DeviceDto` 为 `contracts/` 生成类型。
- 错误码：不新增；只按 CORE-02 的统一 FmlException.code 消息映射展示，来源为已依赖的 CORE-04（`PLATFORM_*`）、CORE-27、CORE-32、CORE-36、CORE-65。同步/升级页面经 SyncFacade 提供状态与回调，状态含错误码时也用同一映射，不消费 CORE-46 私有错误表。

Dart 文件归属：本卡 ViewModel/用例/Controller/Worker/DTO 在 `app/lib/settings/`（由安装点构造 CoreBinding/端口依赖）；Widget、绘制、页面与路由视图在 `app/lib/ui/settings/`。Widget 只接收前者的抽象/状态和回调，不接收 CoreBinding/CoreLibrarySpec，不从 FeatureRegistry 取裸绑定或 HttpTransport。两个目录仍属同一 app/ 构建单元。

产品约束追踪：见README §6 Q13、Q19、Q20、Q27；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 设置首页第一组为“外观”，展示当前预设/模式并导航到CORE-58唯一的/settings/appearance；页面、AppearancePicker及触感开关均由58提供，本卡仅验收入口导航。
- 平台设置项：设置首页在“关于”之前按 `order` 渲染 `deps.features.require<SettingsSections>().items`（CORE-36）的 `build` 结果，标题取 `titleKey`；本卡不认识具体平台项。
- 恢复码只在 `showRecoveryCode` 步骤显示一次，离开页面后从内存清除；用户须勾选“已保存”才能继续。不设防截屏（README §6 Q41）。
- 备份范围与闭包（CORE-27，ADR-V5-44）：范围选择处固定提示“所选范围引用到的公式/单位会一并导出”；导出完成后用 `manifest.closure_added` 显示实际带出的条数；恢复预览显示 `manifest.closure_added`，并说明“被带出的公式/单位只补充缺失项，不会覆盖或删除本机已有内容”。`backup.commit_restore` 是长任务：提交事务开始前可取消，开始后“取消”按钮置灰并显示进行中，结果以报告展示。
- 导出口令须经两次输入一致并调用backup.export，由CORE-27在写文件之前执行CORE-21 check_passphrase_policy；CRYPTO_PASSPHRASE_WEAK回显在口令框，不在Dart复制策略；恢复先 `prepare_restore` 显示预览（条目数、时间、范围），用户确认后才 `commit_restore`；离开页面自动 `discard_restore`。
- `keep_last` 控件限制在 0–100，并说明“0 表示识别完成后不保留历史”。
- 游客设置页显示“游客：无内容上传”，隐藏同步、设备与云识别项；页面只收 VM 与 `deps.ui`，`AppDeps` 只在 `app/lib/settings/routes.dart` 使用。
- 设置主页含“资源包”一项，跳转 `/packs`（CORE-51 提供；该路由未追加时置灰，同 CORE-36 主导航规则）。

**验收标准**
- [R19] 向 `SettingsSections` 加入两个测试项（order 20、10）后设置首页依次显示 order 10、20 两项，未加入时不显示该区。
- [R28] 注册用户设置页可开启/关闭同步并显示最近同步时间、待推送数量与错误（Fake `SyncFacade` 驱动各 `SyncPhase`）。
- [R27] 备份界面（Fake `CoreBinding`）：只选“学习数据”时显示闭包提示，导出完成显示 `closure_added` 条数；恢复预览显示闭包条数与“不覆盖本机”说明；`commit_restore` 事务开始后取消按钮不可用；五项范围全取消时导出按钮禁用（`BACKUP_SCOPE_INVALID` 作为后备映射）。
- [R28] 升级向导：Fake `UpgradeFacade` 下“新建账户”经过显示恢复码 → 勾选已保存 → 完成；未勾选时无法继续；“并入已有账户”要求输入恢复码或同步密语。
- [R25] 游客设置页显示“游客：无内容上传”，不出现同步、设备与云识别项。
- [R27] 导出 → 选择文件恢复（Fake 端口）走完预览与确认；在预览页返回后 `discard_restore` 被调用，原库不变。
- [R34] 设置 `keep_last` 时输入 101 被拒绝并提示范围；设为 0 后调用 `recog.settings.set` 且 `keep_last` 为 0。
- [R42.f] Widget 测试：设置首页第一组显示“外观”项和当前预设/模式，点击后路由到 `/settings/appearance`（页面由 CORE-58 提供，本卡用占位页断言路由名）；游客模式同样可见。

- [R42.e][R42.b] 页面接入验收（Fake 门面与 CoreBinding）：备份导出页两个口令框已输入且焦点在第 2 个、`/settings` 首页滚到底部时，360×800 ↔ 800×360 往返 3 次，文本、焦点与滚动偏移不变；升级向导停在 `UpgradeStep.showRecoveryCode` 并勾选“我已保存”时旋转，仍在该步、勾选保留、恢复码文本不变，`UpgradeFacade` 不被再次调用；`textScaler` 2.0 下设置首页、外观子页、备份与升级向导 `tester.takeException()` 为 null；向导与表单每步恰有 1 个 `FmlButtonVariant.primary`；宽档为 `TwoPane`（左分组 240～360）。

**规模**：约 480 行；用例/状态目录 `app/lib/settings/`；`app/lib/ui/settings/`。

---

