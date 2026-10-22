### CORE-04 平台端口契约

**目标**：用 Dart 抽象接口定义全部平台能力，用例与 UI 只依赖接口，Android 与 Windows 各自提供实现。

**范围**
- 包含：端口接口、端口 DTO、平台错误码在 `contracts/errors/registry.yaml` 中的登记、测试替身（`FakeXxx`）与可复用的端口契约测试套件、`PlatformPorts` 聚合记录。
- 不包含：任何平台实现（AND-xx、WIN-xx 卡）；出网白名单与授权检查（CORE-28 `NetworkGuard` 包裹 `HttpTransport`）。

**依赖**：CORE-01、CORE-02、CORE-03

**接口契约**（`app/lib/ports/`，每个端口一个文件；`CancelToken` 见 CORE-03，`FmlException` 见 CORE-02）

端口 DTO：

```dart
enum KeySecurityLevel { strongBox, tee, software, dpapi }
enum StoreArea { database, packs, recognition, staging, drafts, exports, logs }
enum LifecycleEvent { resumed, paused, detached, lowMemory }
enum HttpMethod { get, post, put, delete }
enum RequestPurpose { packDownload, updateCheck, auth, sync, cloudRecognition, cloudControl, diagnostics }

final class LocalTime {              // 设备本地时区的时刻
  const LocalTime(this.hour, this.minute);   // hour 0–23，minute 0–59，越界抛 ArgumentError
  final int hour; final int minute;
}
final class RuntimeSnapshot {
  final String os;                   // 'android' | 'windows'
  final String osVersion;            // Android 为 API 级别（如 '29'）；Windows 为内部版本号（如 '10.0.17763'）
  final String locale;               // BCP 47，如 'zh-CN'
  final int availMemBytes;           // ≥ 0
  final double dpiScale;             // > 0，1.0 = 160 dpi（Android）或 96 dpi（Windows）
  final String abi;                  // 'arm64-v8a' | 'armeabi-v7a' | 'x86_64' | 'x64'
  final bool gpuAvailable;           // 可用于本地推理加速的 GPU；未知时 false
}
final class HttpRequestDto {
  final HttpMethod method;
  final Uri url;                     // 必须为 https；主机须在 CORE-28 NetworkPolicy 白名单中
  final RequestPurpose purpose;      // 必填；NetworkGuard 据此做白名单与授权检查
  final Map<String, String> headers; // 默认 {}；不得含 Cookie
  final Uint8List? body;             // 默认 null；上限 16 MiB
  final Duration timeout;            // 默认 30 s，总时限；连接超时固定 5 s
  final String? consentToken;        // 仅 purpose == cloudRecognition 时必填（CORE-34 ConsentToken）
  final File? saveTo;                // 非空时响应体流式写入该文件（须位于 StoreArea.staging），HttpResult.body 为空
  final int? rangeStart;             // 断点续传起点字节；仅与 saveTo 同用，服务端返回 206 时追加写入
}
final class HttpResult {
  final int status;                  // HTTP 状态码；非 2xx 不抛异常，调用方按 CORE-02 FmlError 解析响应体
  final Map<String, String> headers; // 键为小写
  final Uint8List body;              // saveTo 非空时为空数组
  final int receivedBytes;           // 本次实际接收字节数
}
abstract interface class ImportedImage {
  String get displayName;            // 仅用于界面显示，不写日志
  String get mimeType;               // 'image/jpeg' | 'image/png' | 'image/webp'；用户选中的 HEIC/HEIF 由平台实现用系统解码器转为 JPEG（质量 92）后再返回
  int get byteLength;
  DateTime get expiresAt;            // 创建后 1 h
  Future<Uint8List> readBytes();     // 只读；过期或导入会话结束后抛 PLATFORM_IO
}
```

端口：

```dart
/// 平台密钥保护：只包装/解包核心生成的密钥，不向 UI 暴露原始密钥。
abstract interface class SecureKeyValueStore {
  Future<Uint8List> wrap(String alias, Uint8List secret);     // 返回包装后的密文；alias 匹配 ^[a-z0-9_.-]{1,64}$
  Future<Uint8List> unwrap(String alias, Uint8List wrapped);  // 密钥失效抛 PLATFORM_KEY_UNAVAILABLE；包装与解包都不要求用户认证
  Future<void> delete(String alias);                          // 别名不存在时静默成功
  Future<KeySecurityLevel> securityLevel(String alias);
}
/// 应用私有目录；返回的目录都位于应用私有根目录之内，不存在时自动创建。
abstract interface class LocalFileStore {
  Future<Directory> root(StoreArea area);                     // 目录位于应用私有根内并已创建；StoreArea.staging 的绝对路径即 staging 类 op 的 staging_root（ADR-V5-53），核心不保存全局暂存根
  Future<int> freeBytes();                                    // 应用私有根目录所在卷的可用字节数
  /// dir须在本应用私有根目录内（解析符号链接后的真实路径）；越界抛ArgumentError，不创建/修改目标。
  Future<void> excludeFromSystemBackup(Directory dir);
}
/// 图片来源：系统选择器、文件管理器、拖拽、剪贴板、扫描。
abstract interface class ImagePicker {
  Future<List<ImportedImage>> pick({required int maxCount});  // maxCount 1–10，越界抛 ArgumentError；用户取消返回空列表
}
abstract interface class CameraController {
  Future<ImportedImage?> capture();                           // 用户取消返回 null；只写应用私有目录
}
abstract interface class NotificationScheduler {
  Future<bool> requestPermission();                           // 已授权或无需授权返回 true
  Future<void> scheduleDailyReminder(LocalTime time, String body); // 只保留一个每日提醒，重复调用替换；body 只含待复习数量
  Future<void> cancelAll();
  Stream<void> taps();                                        // 用户点击提醒通知；应用由通知冷启动时，首个订阅者也收到这一次
}
abstract interface class ClipboardAdapter {
  Future<String?> readText();
  Future<void> writeText(String text);
  Future<ImportedImage?> readImage();                         // 剪贴板无图片或平台不支持时返回 null
}
abstract interface class RuntimeInfo {
  Future<RuntimeSnapshot> snapshot();
}
abstract interface class AppLifecycle {
  Stream<LifecycleEvent> events();                            // 广播流
}
abstract interface class HttpTransport {
  /// 底层只执行传输/TLS/超时；主机白名单与游客授权唯一由 CORE-28 NetworkGuard 在调用前校验，平台不复制策略。
  Future<HttpResult> send(HttpRequestDto req, {CancelToken? cancel});
}
abstract interface class FileExporter {
  Future<bool> saveAs(String suggestedName, Stream<List<int>> bytes); // 由用户选择保存位置；用户取消返回 false
}
/// 非图片文件选择（备份恢复 CORE-84、公式批量导入 CORE-79）：由系统选择器选取后复制到 StoreArea.staging。
abstract interface class DocumentPicker {
  Future<PickedDocument?> pick({required List<String> extensions, required int maxBytes});
  // extensions 为小写、不含点（如 ['fmlbackup']、['csv', 'tex', 'txt']）；用户取消返回 null；超过 maxBytes 抛 PLATFORM_FILE_TOO_LARGE
}
final class PickedDocument { final File file /* 位于 StoreArea.staging，调用方用完删除 */; final String displayName; final int byteLength; }
final class PlatformPorts {
  final SecureKeyValueStore keys; final LocalFileStore files; final ImagePicker picker;
  final CameraController camera; final NotificationScheduler notifications;
  final ClipboardAdapter clipboard; final RuntimeInfo runtime; final AppLifecycle lifecycle;
  final HttpTransport http; final FileExporter exporter; final DocumentPicker documents;
  final List<Installer> platformInstallers;   // 平台专属接缝的安装点（如 AND-07、WIN-08 登记编辑器按键与墨迹策略）；默认 const []；在 featureInstallers 之后执行（CORE-36）
}
```

平台错误码（端口以 CORE-02 的 `FmlException` 抛出；由本卡登记到 `contracts/errors/registry.yaml`）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `PLATFORM_UNSUPPORTED` | error | 否 | 当前平台不提供该能力（如 Windows 的 `CameraController`） |
| `PLATFORM_PERMISSION_DENIED` | error | 是 | 用户拒绝或系统撤销相机、通知、存储等权限 |
| `PLATFORM_KEY_UNAVAILABLE` | error | 否 | 别名不存在、密钥因系统重置或更换系统用户失效、密文被篡改 |
| `PLATFORM_IO` | error | 是 | 文件读写失败、`ImportedImage` 已过期、网络传输未指定 `saveTo` 时响应收集超过 16 MiB 上限（WIN-10、AND-09 实现） |
| `PLATFORM_FILE_TOO_LARGE` | error | 否 | `DocumentPicker.pick` 选中的文件超过 `maxBytes`；`ImportedImage` 原文件超过 20 MiB 时其 `readBytes` |
| `PLATFORM_FILE_TYPE_MISMATCH` | error | 否 | `DocumentPicker.pick` 选中文件的扩展名不在 `extensions` 中（系统选择器无法按自定义扩展名过滤时发生） |
| `PLATFORM_CANCELLED` | info | 否 | 平台对话框被系统中断（用户主动取消按各方法约定返回空值，不抛此码） |
| `PLATFORM_UPDATE_SIG_INVALID` | error | 否 | Windows 自更新：更新包签名校验失败 |
| `PLATFORM_UPDATE_HASH_MISMATCH` | error | 是 | Windows 自更新：下载文件哈希与清单不符 |
| `PLATFORM_UPDATE_DISK_FULL` | error | 是 | Windows 自更新：可用空间不足 |
| `PLATFORM_UPDATE_ROLLED_BACK` | warning | 否 | Windows 自更新：新版本首启失败并已回滚 |
| `NET_OFFLINE` | error | 是 | 无网络连接或 DNS 解析失败 |
| `NET_TLS` | error | 否 | TLS 握手或证书校验失败 |
| `NET_TIMEOUT` | error | 是 | 连接 5 s 或总时限 `timeout` 超时 |
| `NET_HOST_NOT_ALLOWED` | error | 否 | 主机不在编译期白名单，或 URL 不是 https |

- 组装：`app/lib/composition/ports_android.dart` 与 `ports_windows.dart`（由 AND-01、WIN-01 起各平台卡编写）各返回一个 `PlatformPorts`；平台入口文件只调用下方 `runPlatformApp`，不直接依赖 CORE-36。
- 组装原语（本卡定义，供所有后续卡的“安装点”使用；`composeApp` 与安装顺序见 CORE-36）：

```dart
// app/lib/composition/composition.dart
final class FeatureRegistry {                  // 服务按类型登记；取不到即该功能不可用
  void register<T extends Object>(T impl);     // 同类型重复登记 → StateError
  T? get<T extends Object>();
  T require<T extends Object>();               // 取不到 → StateError（只用于组装期）
}
typedef StartupHook = Future<void> Function(FeatureRegistry features);
final class CompositionContext {
  CompositionContext({required this.core, required this.ports, required this.apiBase, required this.packBase});
  final CoreBinding core; final PlatformPorts ports;
  final Uri apiBase, packBase;                 // --dart-define=FML_API_HOST / FML_PACK_HOST（与 CORE-28 NetworkPolicy 同源）
  late HttpTransport http = ports.http;        // 传输安装点可替换（CORE-28 换成 NetworkGuard）
  final FeatureRegistry features = FeatureRegistry();
  void addStartupHook(int order, String name, StartupHook hook);   // order 表见 CORE-36；生产同order重复抛StateError
  List<(int, String, StartupHook)> get startupHooks;               // 按order排序，生产序列拒绝重复order
  void addFirstFrameHook(int order, String name, StartupHook hook);
  List<(int, String, StartupHook)> get firstFrameHooks; // 只做路由/窗口基础就绪，不得等账户、用户、网络；按 order 稳定排序
}
typedef Installer = FutureOr<void> Function(CompositionContext ctx); // dart:async；同步安装点兼容，异步安装必须等待

// app/lib/composition/entry.dart —— 平台入口与应用入口之间的唯一接缝
typedef AppEntry = Future<void> Function(PlatformPorts ports, CoreBinding core);
const AppEntry appEntry = smokeEntry;   // S0 为冒烟入口；CORE-36 完成时把本行改为 mainCommon（只改这一行，不计入 CORE-36 规模）
Future<void> smokeEntry(PlatformPorts ports, CoreBinding core);   // runApp 一个页面，显示ABI版本MAJOR.MINOR；runtime.snapshot成功则显示快照，PLATFORM_UNSUPPORTED则显示固定“运行时信息待平台卡实现”，不伪造快照、不崩溃
Future<void> runPlatformApp(CoreLibrarySpec spec, PlatformPorts Function() buildPorts,
    {CoreBinding Function(CoreLibrarySpec)? open /* 测试注入；默认 CoreBinding.open */});
// 步骤：① WidgetsFlutterBinding.ensureInitialized ② open(spec)；加载失败（ArgumentError）或 abiVersion() >> 16 != FML_ABI_MAJOR（ffigen 从头文件生成的常量）
//       → runApp(CoreUnavailableScreen(reason: loadFailed 或 abiMismatch)) 后返回，不调用 buildPorts ③ await appEntry(buildPorts(), core)
```
- `CoreUnavailableScreen` 文案：加载失败“核心组件加载失败，请重新安装”；版本不符“核心版本不匹配，请重新安装”；只提供“退出”按钮，不进入任何功能页。
- 测试替身（`app/test/fakes/`）：`FakeSecureKeyValueStore`（内存，可逆变换，级别 `software`，可注入失效别名）、`FakeLocalFileStore`（临时目录）、`FakeImagePicker` / `FakeCameraController` / `FakeClipboardAdapter`（返回预置图片或 null）、`FakeNotificationScheduler`（记录最近一次提醒，可调用 `simulateTap()` 产生点击）、`FakeRuntimeInfo`（预置快照）、`FakeAppLifecycle`（手动 `emit(event)`）、`FakeHttpTransport`（按 `(method, url)` 返回预置 `HttpResult` 或错误码，并记录全部请求供审计）、`FakeFileExporter`（写入内存）、`FakeDocumentPicker`（返回预置文件或 null）。
- 契约套件：`app/test/ports/contract/<端口>_contract.dart` 各导出 `void run<端口>Contract(<端口> Function() create)`，Fake 在单元测试中运行，平台卡在 `integration_test/` 中对真实实现运行同一函数。

- 导入生命周期：每个 ImagePicker 实例的一次 pick 调用形成一批；下一次 pick 开始即结束前批（即使新调用取消），或各 ImportedImage.expiresAt 到期结束。CameraController 同理，下一次 capture 开始结束前次；拖拽/剪贴板由各自适配实例各持一批。readBytes 在有效期内可重复读取；结束后抛 PLATFORM_IO，平台异步删除副本。调用方在下一次选择前把所需字节拷入自己的 staging；过期清理、应用退出/下次启动清理均幂等，不删除调用方已接管文件。
- S0 占位实现使用 `app/lib/ports/unsupported/` 的 UnsupportedXxx（仅 Dart/Flutter 正式 SDK，不 import app/test/，所有未实现能力明确返回 PLATFORM_UNSUPPORTED 或空事件流）；测试 FakeXxx 仍在 app/test/fakes/，仅供测试与 debug 注入。PlatformPorts.platformInstallers 通过独立模块清单构建。

HttpTransport流式续传统一协议：rangeStart>=0且仅saveTo可用；>0时现有文件长度须相等，否则ArgumentError；请求Accept-Encoding: identity并禁自动解压。206仅在Content-Range起点与请求偏移（缺省0）一致且长度合法、编码identity时写入；错误206关闭后至多一次无Range截断重下，仍非法报PLATFORM_IO；200截断重写，其他状态不写文件。纠错重发仍受原timeout与cancel约束。HTTPS/主机/Cookie/用途由CORE-28调用前校验。

产品约束追踪：见README §6 Q41；已确认事项按确认值，待确认事项保持暂行默认，不能由编码会话自行改产品取舍。

**实现约束**
- 端口不得把用户内容写入日志；`ImportedImage.readBytes` 只在当前导入会话内有效，过期抛 `PLATFORM_IO`。
- 端口接口只用 Dart SDK 与 `dart:io` 类型，不引入第三方包类型；平台差异只体现在实现与注释中，接口文本两端相同。
- 平台卡内联本卡签名时须逐字复制本节代码，不得增删参数或改写注释。
- 核心加载失败的异常边界：`CoreBinding.open` 把 `DynamicLibrary.open` 的 `ArgumentError` 原样抛出，`runPlatformApp` 捕获后显示 `loadFailed`；ABI MAJOR 不一致不抛异常，由 `runPlatformApp` 比较 `abiVersion() >> 16` 后显示 `abiMismatch`。端口层不捕获也不重映射这两类失败（定义在 CORE-03，本卡照用）。
- 依赖分类：本卡只依赖 CORE-01、CORE-02、CORE-03。正文提到的 CORE-28、CORE-27、CORE-14、CORE-34、CORE-36、AND-07、WIN-08、AND-01、WIN-01 是消费方或下游说明，不是本卡的代码依赖，因此不加入“依赖”行（下游说明，非契约）。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-04_TEST.md](../Test/S0/S0_CORE-04_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约410行；主包 app/：app/lib/ports/ 180行、app/lib/ports/unsupported/ 70行、app/lib/composition/{composition,entry}.dart 160行；无跨构建单元附属；测试替身与端口契约测试不计。 单阶段可独立构建测试；只计本卡实现及本卡编写的附属接入，不计数据/生成物/自测。

---

