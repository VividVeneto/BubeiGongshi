### CORE-28 隐私守卫、日志与复现包

**目标**：在代码层面强制隐私红线：所有出网请求经白名单与授权检查，日志在类型层面无法写入用户内容，复现包由用户手动生成且先预览脱敏结果。

**范围**
- 包含：`NetworkGuard`（包裹 CORE-04 `HttpTransport`）与按账户状态、请求用途的放行规则；`NetworkPolicy` 主机配置；`ConsentVerifier` 接口（CORE-34 实现）；Dart 结构化日志 `AppLog` 与 Rust 侧日志写入；日志轮转；复现包生成、脱敏扫描与预览；调试面板数据源；禁止直接构造 HTTP 客户端的源码扫描测试。
- 不包含：云识别授权界面与令牌签发（CORE-34）；平台 HTTP 实现（AND/WIN 卡）；第三方崩溃收集（V1 不接入）；自动诊断上报（V1 不提供，见实现约束）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-06、CORE-12、CORE-56

**接口契约**

```dart
// app/lib/privacy/network_guard.dart
enum GuardAccountState { uninitialized, guest, upgrading, registered, registeredLocked }
abstract interface class GuardContext {             // 组装层用 CORE-23 账户状态提供方（仅通过本卡 GuardContext 注入）.state 与当前 Profile.sync_enabled 实现
  GuardAccountState get accountState; bool get syncEnabled;
}
abstract interface class ConsentVerifier {          // CORE-34 实现：令牌存在、未过期、未使用，且与请求体图片哈希一致
  bool verify(String consentToken, Uint8List? body);
}
final class NetworkPolicy {
  final String apiHost;    // --dart-define=FML_API_HOST；auth、sync、cloudRecognition、cloudControl
  final String packHost;   // --dart-define=FML_PACK_HOST；packDownload、updateCheck
  const NetworkPolicy({required this.apiHost, required this.packHost});
  factory NetworkPolicy.fromEnvironment();          // 任一为空 → 启动失败（StateError），不回退到默认主机
}
final class NetworkGuard implements HttpTransport {
  NetworkGuard(HttpTransport inner, GuardContext ctx, NetworkPolicy policy, ConsentVerifier consent);
  @override
  Future<HttpResult> send(HttpRequestDto req, {CancelToken? cancel});
}
// app/lib/privacy/app_log.dart
enum LogLevel { debug, info, warning, error }
sealed class LogValue {}                            // 只能承载数值、错误码、ID 与版本，不能承载任意文本
final class LogInt extends LogValue { LogInt(int v); }
final class LogCode extends LogValue { LogCode(String code); }   // 须匹配 ^[A-Z][A-Z0-9_]{2,63}$，否则断言失败并记为 INVALID_CODE
final class LogTrace extends LogValue { LogTrace(String traceId); } // 32 位小写十六进制
final class LogVersion extends LogValue { LogVersion(String v); }  // 须匹配 ^[0-9A-Za-z.+-]{1,32}$
enum LogKey { module, op, traceId, requestId, elapsedMs, budgetMs, count, version, status, errorCode }
abstract final class AppLog {
  static Future<void> init(Directory logsDir, {LogLevel level = LogLevel.info}); // 同时调用 core.log_init
  static void event(LogLevel level, String event /* 编译期常量 */, Map<LogKey, LogValue> fields);
  static Future<List<String>> tail(int lines);       // 调试面板与复现包使用，最多 500 行
}
// app/lib/privacy/repro.dart
final class ReproInput { final String op; final String traceId; final String sourceLatex; final FmlException? error; }
final class ReproBundle { final String json; final int redactionHits; }  // 预览即展示 json
abstract final class ReproBuilder {
  static Future<ReproBundle> build(ReproInput input, CoreBinding core, {required bool syntheticSource});
  static Future<bool> save(ReproBundle bundle, FileExporter exporter);   // 用户在预览页确认后调用
}
// app/lib/privacy/debug_info.dart
final class TraceRecord { final String traceId; final String? errorCode; final int atMs; }
final class DebugInfo {
  final RuntimeSnapshot runtime;            // CORE-04 RuntimeInfo.snapshot()
  final List<String> logTail;               // AppLog.tail(200)
  final List<TraceRecord> recentTraces;     // 最近 20 条，新在前；来自 AppLog 写入时带 traceId 的事件（内存环形缓冲，不落盘）
}
final class DebugInfoSource {
  DebugInfoSource(RuntimeInfo runtime);
  Future<DebugInfo> snapshot();             // 只读，不发网络请求；开发者选项关闭时调用方不得展示
}
```

```rust
// crates/fml-error/src/log.rs（附属：Rust 侧写日志）
pub enum LogValue { Int(i64), Code(&'static str), Trace(TraceId), Version(&'static str) }   // 无法传入运行期字符串
pub fn log_event(level: Level, event: &'static str, fields: &[(&'static str, LogValue)]);
// FFI op core.log_init（同步）{ dir, level } → {}：之后写入 <dir>/core.log；未初始化时丢弃
```

- 放行规则（按顺序检查，第一条不满足即拒绝）：① URL 为 https 且主机等于该用途对应的 `apiHost` 或 `packHost`，否则 `NET_HOST_NOT_ALLOWED`；② 用途在当前状态下允许（下表），否则 `PRIVACY_REQUEST_BLOCKED`；③ `cloudRecognition` 须 `consent.verify(consentToken, body)` 为真，否则 `PRIVACY_CONSENT_MISSING`；④ 游客与锁定状态的请求不得带 `Authorization` 头，带了即 `PRIVACY_REQUEST_BLOCKED`。

| 用途 | 游客 | 升级中 | 注册已解锁 | 注册已登出 |
| --- | --- | --- | --- | --- |
| `packDownload`、`updateCheck` | 允许（无账户标识） | 允许 | 允许 | 允许 |
| `auth` | 允许（注册、登录、找回口令） | 允许 | 允许 | 允许（刷新令牌） |
| `sync` | 拒绝 | 允许（升级步骤的密钥上传） | 仅 `syncEnabled` | 拒绝 |
| `cloudRecognition` | 拒绝 | 拒绝 | 允许（仅POST /v1/recognition/jobs，须授权令牌） | 拒绝 |
| `cloudControl` | 拒绝 | 拒绝 | 允许（仅policy、consents、GET jobs/{id}、POST jobs/{id}/cancel，不含图片上传） | 拒绝 |
| `diagnostics` | `PRIVACY_DIAGNOSTICS_DISABLED` | 同左 | 同左 | 同左 |

- 日志：Dart 与 Rust 各写 `StoreArea.logs` 下 `app.log`、`core.log`，每行一个 JSON `{ts, level, event, …fields}`；按大小轮转 5 MiB × 3；`LogKey` 与 Rust 字段名同为蛇形小写。
- 复现包 JSON：`{format: 1, app_version, core_abi, platform: {os, os_version, abi}, op, trace_id, error: {code, diagnostics}, source, ast, display_list, log_tail}`。`syntheticSource = true`（默认）时，标识符按出现顺序替换为 `x_{1}`、`x_{2}`…、数字逐位替换为 1，再经 `engine.parse` 与 `typeset.layout` 重新生成 `ast` 与 `display_list`；之后对全文运行脱敏扫描：文件路径（盘符路径、`/data/`、`/storage/`、`/Users/`、`/home/`）、JWT 与 `Bearer` 令牌、恢复码形态（27 位 Crockford 分组）、邮箱地址；命中处替换为 `<redacted>` 并计入 `redactionHits`。
- 调试面板数据源：`DebugInfoSource.snapshot()` 返回 `DebugInfo`（`RuntimeSnapshot`、最近 200 行日志、最近 20 个 `trace_id` 与错误码）；仅在 `kDebugMode` 或设置中的“开发者选项”开启时可见。
- 错误码：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `PRIVACY_REQUEST_BLOCKED` | error | 否 | 用途在当前账户状态下不允许，或游客、锁定状态请求带 `Authorization` |
| `PRIVACY_CONSENT_MISSING` | error | 否 | `cloudRecognition` 请求缺少 `consentToken`，或 `ConsentVerifier` 判定无效、过期、已用或与图片不符 |
| `PRIVACY_DIAGNOSTICS_DISABLED` | info | 否 | 任何 `diagnostics` 用途请求（V1 恒拦截） |
| `PRIVACY_REPRO_FAILED` | error | 是 | 合成源码重新解析或排版失败（复现包仍可选择不含 AST 与 DisplayList 生成） |

RequestPurpose.updateCheck同时表示Windows更新清单与用户显式触发的安装包下载；同packHost、无账户标识。自动check不下载，用户点击下载允许计量网络，沿用已有显式下载策略，不新增后台自动下载。Cookie头统一由NetworkGuard在调用inner前拒绝并抛NET_HOST_NOT_ALLOWED；平台只执行传输，不重复此策略。

消耗型授权契约：NetworkGuard只负责对每个上传请求调用一次ConsentVerifier.verify，不做HTTP重试，不因401返还已消耗令牌。CORE-34（下游说明，非契约）重新取得用户确认后以新令牌发送同一业务幂等键；CORE-62（下游说明，非契约）禁止自动重发cloudRecognition。任何代理包装器不得重复verify或将旧consentToken跨请求转发。

FFI错误镜像（不重定义代码；通用信封错误见CORE-03）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| core.log_init | PLATFORM_IO |

core.log_init目标目录不可写或日志文件创建失败复用CORE-04 PLATFORM_IO；非法dir/level由CORE-03信封参数检查拒绝，不使用网络守卫PRIVACY_*错误。

产品约束追踪：见README §6 Q41；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 安装点：installPrivacy(CompositionContext ctx) 为 transportInstallers 第一项，用 _CtxGuard 将延迟登记的 GuardContext 映射为本卡状态（缺省 uninitialized），_LazyConsent 缺省拒绝；只改 ctx.http。消费方只从 CompositionContext.http 获取包装后的传输，不读 ports.http。账户卡在自己的安装点登记 GuardContext，避免本卡反向依赖账户实现。
- 组装层只暴露 NetworkGuard 包装后的 HttpTransport；no_direct_http_test.dart 与 CORE-41 PRIV-1 均读取 CORE-01 contracts/policies/network-construction.yaml，只有平台 net/ 构造器豁免，其他目录无例外。
- 游客红线：禁止云同步、云识别、云内容推荐、用户内容诊断上报、崩溃报告自动上传、把本地 ID 发给第三方；允许用户触发的更新检查、显式资源包下载、注册登录与本地导出。界面措辞为“无内容上传”，不写“绝不联网”。
- V1 不提供诊断上报：服务端没有对应端点，`diagnostics` 用途恒被拦截；用户需要反馈时手动导出复现包后自行发送。
- 复现包只由用户手动生成，预览确认后经 `FileExporter` 保存；不自动上传；`syntheticSource = false` 时预览页显著提示“包含原始公式”。
- 外部前提：无新增第三方依赖。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-28_TEST.md](../Test/core/S2_CORE-28_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 600 行；主包 `app/lib/privacy/`（约 495），附属 `crates/fml-error/src/log.rs`（Rust 侧日志写入，约 85）与 `crates/fml-ffi/src/ops/log.rs`（core.log_init 薄适配，约 20）。分阶段：① 网络守卫与结构化日志（network_guard、安装点、AppLog、log.rs、core.log_init，约 425）；② 复现包与调试面板数据源（repro.dart、debug_info.dart，约 175）。

---

