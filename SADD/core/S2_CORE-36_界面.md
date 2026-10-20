### CORE-36 应用壳、组装层、账户入口与导航

**目标**：提供两端共用的应用骨架：组装层与功能安装点、启动流程、账户入口（游客 / 注册 / 登录 / 找回口令）、主导航与无障碍基线（主题、令牌与自适应布局由 CORE-55 定义，本卡负责接入），以及界面访问同步与升级的门面接口。

**范围**
- 包含：应用壳、组装层、门面、启动/首帧钩子、主导航与路由守卫。
- 不包含：账户入口表单与隐私正文页（CORE-63，下游说明，非契约）；业务功能页面。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-22、CORE-23、CORE-55、CORE-28、CORE-56、CORE-62、CORE-65、CORE-58

**接口契约**

```dart
// app/lib/composition/compose_app.dart（CompositionContext、FeatureRegistry、Installer、StartupHook 定义在 CORE-04）
Future<AppDeps> composeApp({required CoreBinding core, required PlatformPorts ports});
    // ① 建 ctx → ② 逐项await transportInstallers（前项成功完成后才执行后项） → ③ 用 ctx.http 构造 TokenStore、ApiClient、AccountController 并登记到 ctx.features
    // → ④ 逐项await featureInstallers，再逐项await ports.platformInstallers；任一失败即停止、清理已创建资源并抛错，不发布AppDeps → ⑤ 生成 AppDeps（ports.http 替换为 ctx.http；sync/upgrade 取不到时用 Disabled 实现）
// app/lib/composition/installers.dart —— CORE-36维护者单写；特性卡只提交自己的installXxx登记片段，不直接修改本文件
final List<Installer> transportInstallers = [ /* CORE-28: installPrivacy */ ];
final List<Installer> featureInstallers = [ /* 顺序固定：installDesign（CORE-55，第一项）、installDesignComponents（CORE-58）、installEditor（CORE-37）、installEditorInput（CORE-59）、installFormulaCopy（CORE-52）、installLatexCompletion（CORE-53）、installLibraryBatch（CORE-54）、installStudy（CORE-39）、installRecognition（CORE-40）、installStorageGuard（CORE-50）、
                                                 installCloud（CORE-34）、installReminders（CORE-20）、installSync（CORE-46）、installPacks（CORE-51） */ ];

final class AppDeps {   // 只给组装层与特性目录（app/lib/<feature>/，含各卡 routes.dart）使用；app/lib/ui/ 不得接收或保存
  final CoreBinding core; final PlatformPorts ports; final AccountController account; final FeatureRegistry features;
  final SyncFacade sync; final UpgradeFacade upgrade; final List<(int, String, StartupHook)> firstFrameHooks, startupHooks;   // 来自 ctx.startupHooks
  UiDeps get ui;          // 去掉 core/ports 的界面视图
}
final class UiDeps {    // app/lib/ui/ 中 Widget 允许接收的唯一依赖对象；不含 CoreBinding、PlatformPorts（ADR-V5-34）
  final AccountController account; final FeatureRegistry features; final SyncFacade sync; final UpgradeFacade upgrade;
}

// app/lib/composition/facades.dart —— 界面只依赖这些类型；实现由 CORE-46 提供
enum SyncTrigger { appStart, resumed, manual, afterUpgrade }
enum SyncPhase { disabled, idle, syncing, offline, needsKey, clientTooOld, failed }
final class SyncStatus { final SyncPhase phase; final DateTime? lastSuccessAt; final int outboxLen, quarantined, openChoices; final String? lastErrorCode; }
enum UpgradeChoice { newAccount, mergeInto }
sealed class KeySecretInput { const KeySecretInput(); }
final class RecoveryCodeInput extends KeySecretInput { const RecoveryCodeInput(this.code); final String code; }
final class PassphraseInput extends KeySecretInput { const PassphraseInput(this.passphrase); final String passphrase; }
abstract interface class SyncFacade {
  Stream<SyncStatus> get status;
  Future<SyncStatus> syncNow(SyncTrigger trigger);
  Future<void> setEnabled(bool enabled);
  Future<void> provideKey(KeySecretInput secret);          // needsKey 时由界面收集恢复码或同步密语
  Future<void> setSyncPassphrase(String passphrase);
  Future<String> revokeDeviceAndRotate(String deviceId);   // 返回新恢复码
}
abstract interface class UpgradeFacade {
  Future<void> run(UpgradeChoice choice, {required Future<bool> Function(String recoveryCode) confirmSaved,
                   Future<KeySecretInput> Function()? askSecret /* mergeInto 必填 */});
  Future<void> resumeIfPending();
}
final class DisabledSyncFacade implements SyncFacade { /* status 恒为 disabled；其余方法抛 FmlException('SYNC_NOT_AVAILABLE') */ }
final class DisabledUpgradeFacade implements UpgradeFacade { /* run 抛 SYNC_NOT_AVAILABLE；resumeIfPending 什么也不做 */ }

// app/lib/composition/shell_ext.dart —— 平台卡经 PlatformPorts.platformInstallers 扩展外壳；ui/ 中不得判断平台
abstract interface class AppNavigator { void go(String location); }   // ③ 登记；路由器建好前的调用排队，建好后按序执行
abstract interface class ShellKeyHandler {                           // 可选；AppShell 用 FocusManager.addEarlyKeyEventHandler 先交给它，返回 ignored 再走焦点链；AppShell 只取一个（同类型重复登记抛StateError），平台若有多组按键规则须自行合并为一个处理器（Windows 为 WIN-15 WindowsKeyRouter）
  KeyEventResult handle(KeyEvent event, AppNavigator nav); }
abstract interface class SettingsSection { String get id; int get order; String get titleKey; Widget build(BuildContext context); }
final class SettingsSections { final List<SettingsSection> items = []; }   // ③ 登记空列表；CORE-47 设置首页按 order 渲染

// app/lib/composition/routes.dart —— 汇总各卡 xxxRoutes(AppDeps)，由CORE-36维护者单写（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
List<RouteBase> buildRoutes(AppDeps deps);
// app/lib/ui/shell/app_shell.dart
class AppShell extends StatelessWidget { const AppShell({super.key, required this.deps, required this.router}); final UiDeps deps; final GoRouter router; }
// app/lib/main_common.dart
Future<void> mainCommon(PlatformPorts ports, CoreBinding core);   // 平台 main.dart 构造端口与 CoreBinding 后调用
```

- 路由表（go_router）：本卡只提供主导航外壳和路由守卫；账户路由由 CORE-63 的 accountRoutes 提供（下游说明，非契约），未登记时 `/` 为不可用占位；功能路由由各卡在自己的特性目录提供 `List<GoRoute> xxxRoutes(AppDeps deps)`（文件 `app/lib/<feature>/routes.dart`，不在 `ui/`），在那里用 `deps` 构造 VM 后只把 VM、DTO 或 `deps.ui` 交给 `ui/` 中的页面；经 `app/lib/composition/routes.dart` 汇总（该文件由本卡维护者单写，各功能卡只提交路由登记片段）。归属：

| 路由前缀 | 提供函数 | 卡片 |
| --- | --- | --- |
| `/settings/appearance` | `designComponentRoutes(AppearanceController)` | CORE-58 |
| `/library`、`/library/new`、`/library/:itemId` | `libraryRoutes` | CORE-38 |
| `/library/import`、`/library/units` | `libraryToolsRoutes` | CORE-60 |
| `/`、`/account`、`/privacy` | `accountRoutes` | CORE-63 |
| `/calc` | `calcRoutes` | CORE-48 |
| `/study`、`/study/books`、`/study/books/:bookId`、`/study/plan/:bookId`、`/study/session/:id` | `studyRoutes` | CORE-39 |
| `/study/stats`、`/study/reminder`、`/study/books/new`、`/study/books/:bookId/edit` | `statsRoutes` | CORE-49 |
| `/recognize`、`/recognize/history`、`/recognize/history/:sessionId` | `recognitionRoutes` | CORE-50 |
| `/settings` 及其子路由 | `settingsRoutes` | CORE-47 |
| `/packs` | `packRoutes` | CORE-51 |

- 汇总顺序：静态路径先于带参数路径（CORE-60静态导入/单位路由排在libraryRoutes的参数项之前，`statsRoutes` 排在 `studyRoutes` 之前，使 `/study/books/new` 不被 `/study/books/:bookId` 吞掉）；主导航四个入口依次指向 `/study`（首页）、`/library`、`/recognize`、`/settings`，由 CORE-55 `AdaptiveScaffold` 按宽度分档呈现为底部导航栏、导航轨或侧栏；完成账户入口后落在 `/study`；对应路由尚未追加时入口置灰。
- 入口接缝：本卡完成时把 CORE-04 `entry.dart` 中的 `appEntry` 由 `smokeEntry` 改为 `mainCommon`（只改这一行）。
- 首帧协议：路由器已创建且账户入口页（或已自动打开档案的首页）已渲染后，`mainCommon` 的 post-frame 回调先依次 await `firstFrameHooks`，再启动下面的顺序钩子。第一组只含本地短操作（托盘 order 10、最小化兜底显示 order 15、健康确认 order 20），每项以 2 s 为上限 await，超时或失败都记录 `AppLog` 并继续下一项（超时的 Future 不再等待，其结果被忽略）；失败的健康确认不得伪造标记。它不等待档案打开、同步或网络。`--minimized` 不影响路由创建与首帧渲染。
- 启动钩子（首帧协议完成后按 order 依次 await，单个钩子失败只记 `AppLog` 并继续）：

| order | 钩子 | 登记者 |
| --- | --- | --- |
| 10 | 资源包恢复与 bootstrap 安装（契约见 CORE-15；S2/S3 为空） | CORE-51 的安装点 `installPacks`（S4） |
| 12 | Windows自定义键位加载 | WIN-14平台安装点（下游说明，非契约） |
| 15 | 资源包更新检查（后台进行，不阻塞后续钩子，只检查不下载） | CORE-51 的安装点 |
| 20 | `account.profiles` → 恢复账户状态 → 打开档案（系统级解包 DbKey，不弹认证） | CORE-65账户安装点（宿主只调度） |
| 30 | 预留升级恢复区间，S2 为空 | CORE-46 自己的安装点（S6） |
| 40 | 本地模型注册（对 `model-` 开头的包调 `recog.local.register`） | CORE-40 的安装点 |
| 50 | 识别历史恢复（`recog.recover`） | CORE-40 的安装点 |
| 55 | 存储空间检查（可用空间 < 500 MiB 时 `recog.gc`） | CORE-50 的安装点 |
| 60 | 云任务查询（`resumePending`，仅注册用户） | CORE-34 的安装点 |
| 70 | 预留同步区间，S2 为空 | CORE-46 自己的安装点（S6） |
| 80 | 提醒重排 | CORE-20 的安装点 |
| 85 | Windows应用更新检查（仅检查不下载） | WIN-03平台安装点（下游说明，非契约） |
| 86 | 保留，不登记钩子；旧健康确认已迁firstFrameHooks 20 | WIN-03（下游说明，非契约） |
| 90 | 界面预热 `DesignWarmup.run`（空闲时进行，不阻塞后续操作） | CORE-58 的安装点 `installDesignComponents` |

- 文案键集中在 `app/lib/l10n/zh_CN.arb`；错误码到文案的映射由 CORE-02 生成（`app/lib/l10n/errors.g.dart`）。
- 错误码（本卡唯一定义）：账户相关错误复用 CORE-22、CORE-23。

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `SYNC_NOT_AVAILABLE` | info | 否 | 同步模块未安装或当前为游客时调用门面方法 |

规模复核：composition/安装聚合130、路由/壳90、启动钩子60、测试100，共380；ProfileSession实现与打开/关闭序列归CORE-65，本卡仅注入其source，不复制生命周期状态机。

启动order 95保留不登记：旧托盘创建已迁firstFrameHooks 10，最小化兜底15、健康确认20均属于首帧钩子独立序列，不得重新塞入顺序队列。startup12/85分别归Windows键位/更新，平台未安装时空缺；同号跨序列允许，同序列不同所有者冲突需CORE-36维护者分配，不靠登记先后碰运气。

PR3预分配以contracts/policies/shared-writes.json为机器索引，公共行为仍以上述契约为准。file项由单一维护者合入独立片段；installer每卡在自身install.dart定义，聚合文件由本卡维护者单写。route按最长路径前缀匹配（/settings/appearance优先于/settings），禁止相同前缀不同owner；未知前缀先申请再登记。startup/firstFrame/settings在各自序列内key唯一，86/95未分配不可注册；测试可用专用test-only表，不占生产号。快捷键固定保留与默认表归WIN-08/15（下游说明，非契约），命令ID归CORE-58；消费者只提交引用，不增第二份。运行时FeatureRegistry和SettingsSections必须拒绝重复生产ID/order并导出build/extensions.json登记回执，CORE-75（下游说明，非契约）比对owner/key/point，不以人工记顺序代替门禁。

产品约束追踪：见README §6 Q1、Q7、Q9、Q41；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 系统返回（Android 返回手势/返回键，Windows 不涉及）：用 `PopScope`（不用已弃用的 `WillPopScope`）统一处理——推入的二级页回到上一页；主导航中“学习”以外的根页返回切到 `/study`；“学习”根页 `canPop: true` 交给系统退到后台，不弹“再按一次退出”；底部面板、对话框与菜单先关闭自身。每种返回都有可见按钮等价（顶栏返回、导航项“学习”、关闭按钮）；平台侧对照见 AND-13 表 e。
- 视觉与交互遵守 CORE-55：颜色、字号、间距、圆角与动效只取 `FmlTheme` 令牌，控件用 CORE-58 核心组件，页面按 CORE-55 g「关键页面布局」在各宽度分档与矮高度下呈现，触控目标与密度取 `InputModalityScope`；不判断运行平台。
- 组装 CORE-55：`installDesign` 为 `featureInstallers` 第一项；`main_common.dart` 在 `composeApp` 之后、`runApp` 之前 `await AppearanceController.load()`；`AppShell` 以 `themeFor` 生成 `theme`/`darkTheme` 并按外观模式设 `themeMode`，在 `builder` 中包裹 `InputModalityScope`；主导航外壳用 `AdaptiveScaffold`。主题、深色模式、主题色与字体缩放规则只在 CORE-55 定义，本卡不另建 `ThemeData`。
- Uninitialized 状态下路由守卫只放行 `/`、`/account/*` 与 `/privacy`；游客隐藏云识别与同步入口（以 `FeatureRegistry` 取不到或 `account.state` 为游客判断，不写平台分支）。
- `composeApp` 与 `installers.dart` 之外的代码不得构造服务实现；`app/lib/ui/` 中的 Widget 构造参数与字段只能是 `UiDeps`、VM、DTO 与回调，不得出现 `AppDeps`、`CoreBinding`、`PlatformPorts`（CORE-41 DEP-5 检测）。`installers.dart` 与 `routes.dart` 的合入行计入聚合所有者预算，消费方片段与自己的安装实现计入本卡规模，也不视为跨构建单元。
- 状态恢复：`MaterialApp.router` 设 `restorationScopeId: 'fml'`，`GoRouter` 设 `restorationScopeId: 'router'`，使 Android 进程被回收重建后回到原路由（平台侧见 AND-05）；需要恢复的页面状态以路由参数表达，不依赖内存对象。
- 外壳扩展：`composeApp` ③ 同时登记 `AppNavigator`（实现 `_QueuedNavigator`）与空的 `SettingsSections`；`AppShell` 挂载时通过 `FocusManager.instance.addEarlyKeyEventHandler` 登记唯一回调，先调用 `features.get<ShellKeyHandler>()`，卸载时用同一回调 remove；handled 阻断焦点链，ignored 才交给 primaryFocus。不得用根 Focus 或 HardwareKeyboard.addHandler 代替：后者会广播全部 handler，不保证短路。平台窗口、托盘、快捷键与平台设置项（WIN-03、WIN-06、WIN-08、WIN-09）只经这三个接缝接入。
- 提醒点击：`mainCommon` 在路由器创建后订阅 `ports.notifications.taps()`，每次收到即 `router.go('/study')`（未完成账户入口时先完成入口再跳转）。
- 冷启动只加载 bootstrap 包与当前档案，其余资源按需加载；首帧不等待启动钩子；冷启动满足 CORE-01 预算（Android < 2 s，Windows < 1.5 s）。
- 无障碍：所有可点击控件有语义标签；公式控件提供 CORE-12 的 `semantic_text` 朗读；文字缩放、对比度、焦点与减少动效按 CORE-55 i。
- 外部前提：`go_router` 与 `flutter_localizations`（随 Flutter SDK），版本随 ADR-V5-15锁定。
- 产品取舍（2026-10-19 甲方确认）：主导航入口顺序与落地页见 README §6 Q21；Android 主导航根页的系统返回见 README §6 Q26。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-36_TEST.md](../Test/core/S2_CORE-36_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 380 行；主包 `app/lib/composition/`、`app/lib/ui/shell/`、`app/lib/main_common.dart`。

