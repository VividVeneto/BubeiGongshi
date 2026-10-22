### AND-02 权限与清单

**目标**：把 Android 权限压到最少，按需请求，拒绝后功能可降级使用，并在构建时审计合并后的清单。

**范围**
- 包含：`AndroidManifest.xml` 声明；运行时权限请求封装（Dart 接口 + Kotlin 通道）；拒绝与“不再询问”后的引导；合并清单审计脚本（含 AND-13 窗口属性的审计）；备份规则文件的引用（规则内容由 AND-06 定义）。
- 不包含：各功能对权限的具体使用（AND-04 相机、AND-08 通知）；MainActivity 窗口属性的取值（AND-02 接口契约窗口属性表，本卡只写入清单并审计）。

**依赖**：CORE-01、CORE-02、CORE-04、AND-01、AND-15

**接口契约**

```dart
// app/lib/platform/android/permissions.dart
enum AndroidPermission { camera, postNotifications }
enum PermissionOutcome { granted, denied, permanentlyDenied }
abstract interface class PermissionService {
  /// 已授权直接返回 granted；否则先显示用途说明对话框（文案键 rationaleKey，用户点“暂不”则返回 denied 且不弹系统框），
  /// 再弹系统权限框。Android 12 及以下请求 postNotifications 直接返回 granted（系统无此运行时权限）。
  Future<PermissionOutcome> request(AndroidPermission p, {required String rationaleKey});
  Future<PermissionOutcome> status(AndroidPermission p);     // 不弹任何对话框
  Future<void> openAppSettings();                            // 打开本应用的系统设置页
}
final class ChannelPermissionService implements PermissionService {
  /// contextProvider 是用途说明对话框唯一的宿主来源，由组合层注入（见下文“对话框宿主与注入点”）。
  /// 返回 null 或该 context 已不在挂载树中时，request() 跳过用途说明、只弹系统权限框。
  ChannelPermissionService(this.contextProvider);
  final BuildContext? Function() contextProvider;
}
```

```text
MethodChannel "fml/android/permissions"（Kotlin 侧 PermissionsHandler.kt，挂在 MainActivity）
  status  {perm: "camera" 或 "post_notifications"} → "granted" 或 "denied" 或 "permanently_denied"
  request {perm} → 同上（用 ActivityResultContracts.RequestPermission；
                    拒绝且 shouldShowRequestPermissionRationale 为 false 且曾请求过 → permanently_denied）
  openSettings → null（Settings.ACTION_APPLICATION_DETAILS_SETTINGS）
tools/ci/check_android_manifest.py <merged-manifest.xml> → 退出码 0 通过；1 时逐行打印多出或缺少的权限，
  以及违反 AND-02 接口契约窗口属性表 的 Activity 与属性（任一 Activity 声明 screenOrientation 或 resizeableActivity="false"；
  MainActivity 的 configChanges 集合、windowSoftInputMode 与表不符；application 未声明 enableOnBackInvokedCallback="true"）
```

**对话框宿主与注入点（唯一）**：用途说明对话框只由组合层注入的上下文提供者驱动。`ChannelPermissionService(BuildContext? Function() contextProvider)` 的唯一构造点在组合层 `app/lib/composition/ports_android.dart`（该文件由 AND-01 的聚合维护者单写合入，本卡只提交构造与传递片段，计入本卡规模）：组合层创建唯一实例，并把同一实例传给 AND-04 的 `AndroidCameraController` 与 AND-08 的 `AndroidNotificationScheduler`；其他位置（含 `app/lib/ui/` 与各特性目录）不得再构造本类。提供者的实现也归组合层，取自它在 CORE-36 组装流程中自己创建的 `GoRouter`（`router.routerDelegate.navigatorKey.currentContext`，编码时按锁定的 go_router 版本核验该 API），取不到时返回 null。本卡不新增根导航键（不改 CORE-36 契约），`ChannelPermissionService` 不持有全局导航键、不从 `WidgetsBinding` 取上下文、不对平台作判断；`request`、`status`、`openAppSettings` 签名不变，AND-04、AND-08 的调用不变。`contextProvider()` 返回 null，或返回的 context 已不在挂载树中（界面不可用）时，`request()` 不弹用途说明、直接弹系统权限框，不抛异常也不阻塞请求。对话框侧只做展示与两个按钮（“继续”“暂不”），文案按调用方给的 `rationaleKey` 定位（文案条目归界面侧维护，本卡只透传键名），符合 CORE-01 依赖方向第 5 条（平台层只经端口调用，共享界面不判断平台）。Widget 测试按此注入提供者：注入返回测试 harness 上下文的提供者驱动对话框分支，注入返回 null 的提供者验证只弹系统框的降级分支。

最终权限白名单（系统普通权限不弹运行时框；按来源卡启用，审计为“必需集合 ⊆ 实际集合 ⊆ 最终白名单”，可选库项随锁定依赖启用）：

| 权限 | 时机 |
| --- | --- |
| `INTERNET` | 普通；AND-09 网络 |
| `ACCESS_NETWORK_STATE` | 普通；AND-09 网络变化 |
| `RECEIVE_BOOT_COMPLETED` | 普通；AND-08 提醒重排 |
| `${applicationId}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` | AndroidX core 合入，signature 自定义 permission 与 uses-permission 成对审计 |
| `CAMERA` | 用户第一次点击“拍照识别”时 |
| `POST_NOTIFICATIONS`（Android 13+） | 用户开启复习提醒时 |

- 错误码：调用方在 `denied/permanentlyDenied` 时由端口抛 `PLATFORM_PERMISSION_DENIED`（CORE-04 登记），本卡不新增错误码。
- 清单其他固定项：`android:allowBackup="false"`，并以 `android:dataExtractionRules` / `android:fullBackupContent` 指向 AND-06 的规则文件（全部排除）；`android:usesCleartextTraffic="false"`；无导出的 Service、Receiver、Provider（AND-08 的提醒接收器、AND-14 的剪贴板 `FileProvider` 均为 `exported="false"`）。
- 窗口属性：MainActivity 按 AND-02 接口契约窗口属性表 声明（不声明 `android:screenOrientation`，跟随系统旋转，README §6 Q17；`resizeableActivity="true"`；`configChanges`、`windowSoftInputMode` 与表一致）；AND-04 的 CameraActivity 同样不声明 `screenOrientation`。

b. MainActivity 窗口属性（唯一定义；AND-05/13 引用）

| 属性 | 取值 | 理由 |
| --- | --- | --- |
| `android:screenOrientation` | 不声明（unspecified） | 跟随系统自动旋转与旋转锁定，手机与平板相同（Q17） |
| `android:resizeableActivity` | `true` | 分屏、自由窗口、折叠屏 |
| `android:launchMode` | `singleTop` | AND-08通知点击复用顶部MainActivity并走onNewIntent |
| `android:configChanges` | `orientation\|keyboardHidden\|keyboard\|screenSize\|smallestScreenSize\|locale\|layoutDirection\|fontScale\|screenLayout\|density\|uiMode` | 与 Flutter 工程模板一致；旋转、尺寸、字号、深色变化由 Flutter 重排，不重建 Activity |
| `android:windowSoftInputMode` | `adjustResize` | 软键盘高度经 `viewInsets` 交给 Flutter |
| `android:enableOnBackInvokedCallback` | `true`（声明在 `<application>`，覆盖 Android 13） | 系统预测性返回 |
| 不声明 | `<layout>` 最小宽高、`maxAspectRatio`、`supportsPictureInPicture` | 不限制窗口尺寸与宽高比 |


本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

产品约束追踪：见README §6 Q41；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 不申请 `READ_EXTERNAL_STORAGE`、`READ_MEDIA_IMAGES`、`MANAGE_EXTERNAL_STORAGE`、定位、通讯录、电话、麦克风、精确闹钟（`SCHEDULE_EXACT_ALARM`）与前台服务权限；选图走系统选择器（AND-03）。
- 每次请求前先显示用途说明（界面不可用时按上文“对话框宿主与注入点”降级为只弹系统权限框，不抛异常也不阻塞请求）；拒绝后不反复弹窗，只在用户再次主动使用该功能时提示并提供“去设置”。
- 第三方依赖带入的白名单权限保留并核对 protectionLevel/maxSdkVersion；白名单外项先核实用途，再移除并跑能力测试，或先修 ADR 与本表，不得删掉动态接收器等正常工作所需权限。
- 不使用权限类第三方插件，权限请求只经本卡通道；不使用 Google Play 服务专属能力（推送、Play Integrity、Google 登录），保证无 GMS 设备可用。
- 审计脚本输入为 Gradle 生成的 `build/intermediates/merged_manifests/release/AndroidManifest.xml`；CI 在 release 构建后调用（CORE-41 的 `ci.yml` 追加一步）。

**验收标准**：测试方案全文见 [Test/and/S2_AND-02_TEST.md](../Test/and/S2_AND-02_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 300 行；主包 `app/`（`app/lib/platform/android/permissions.dart` 与 `app/android/` 的 `PermissionsHandler.kt` 接入，约 190 行，含组合层 `app/lib/composition/ports_android.dart` 的构造与传递片段约 5 行），附属 `tools/ci/check_android_manifest.py` 约 110 行。组件估算：Dart 权限封装与用途说明约 85 行，Kotlin 请求、曾请求状态与设置页约 100 行，组合层构造与传递片段约 5 行，合并清单审计约 110 行；CI 调用步骤在 `.github/workflows/ci.yml`（CORE-41 单写合入，本卡不编辑该文件，不计本卡）。只计本卡交付实现及附属接入代码；验证测试、夹具与静态配置/资源数据不计。

