### AND-09 网络传输

**目标**：提供 Android 上的 `HttpTransport` 端口实现：仅 HTTPS、系统证书、超时、取消、流式落盘与断点续传，并跟随系统代理。

**范围**
- 包含：`AndroidHttpTransport`（基于 `dart:io` `HttpClient`）；系统代理读取（通道 `fml/android/net`）；异常到 CORE-04 错误码的映射；契约套件真机运行。
- 不包含：主机白名单、用途与授权检查（CORE-28 `NetworkGuard` 包裹本卡实现）；云识别前后台行为（CORE-34）；资源包下载流程（CORE-51）；服务端（CORE-22、CORE-33、CORE-43）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-28、AND-15

**接口契约**

实现的端口（CORE-04，逐字摘录；`HttpRequestDto`、`HttpResult`、`CancelToken` 定义见 CORE-04、CORE-03）：

```dart
abstract interface class HttpTransport {
  /// 底层只执行传输/TLS/超时；主机白名单与游客授权唯一由 CORE-28 NetworkGuard 在调用前校验，平台不复制策略。
  Future<HttpResult> send(HttpRequestDto req, {CancelToken? cancel});
}
```

本卡实现：

```dart
// app/lib/platform/android/net/android_http.dart
final class AndroidHttpTransport implements HttpTransport {
  AndroidHttpTransport({SecurityContext? testContext});   // 内部持有一个 HttpClient：connectionTimeout 5 s，idleTimeout 15 s，autoUncompress false（仅identity），userAgent 'FML/<版本> Android'
}
```

```text
send(req, cancel) 步骤：
  1 HTTPS/主机/Cookie/用途由CORE-28调用前校验，本层不复制策略
  2 rangeStart与saveTo、现有文件长度、Accept-Encoding/Content-Range、纠错重发、超时与取消严格实现CORE-04统一续传协议
  3 saveTo为空收集响应至内存，上限16 MiB；非空按CORE-04流式写入，其他状态body同上限返回
  4 cancel在等待和每64 KiB检查，abort后抛FfiCancelled；req.timeout覆盖全过程
异常映射：SocketException、HttpException（连接被重置）→ NET_OFFLINE；HandshakeException、TlsException → NET_TLS；
          TimeoutException → NET_TIMEOUT；FileSystemException → PLATFORM_IO
系统代理：构造时与网络变化后经 MethodChannel "fml/android/net" 的 proxy → {host, port} 或 null（ConnectivityManager.getDefaultProxy），
          设置 HttpClient.findProxy；读取失败按直连
```

- 错误码：只使用 CORE-04 登记的 `NET_OFFLINE`、`NET_TLS`、`NET_TIMEOUT`、`NET_HOST_NOT_ALLOWED`、`PLATFORM_IO`；取消抛 CORE-03 `FfiCancelled`；本卡不新增错误码。

Dart HttpClient不受Android network_security_config自动注入，测试CA只能通过非发布构造器注入SecurityContext；构造器增加SecurityContext? testContext，若kReleaseMode且非空则在运行时抛StateError（不能用会被剥离的assert）；默认系统根、badCertificateCallback始终禁用，测试上下文只存在测试入口。

User-Agent使用FML/<AppVersion> Android；AppVersion唯一取发布构建--dart-define=FML_APP_VERSION，与CORE-42 bump_version输出相同，debug未提供时仅用0.0.0-dev；不取服务器值/运行时猜版本。假HTTP契约覆盖同主机302和跨主机307均无第二请求。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

**实现约束**
- 证书只用 `dart:io` 默认信任库（系统 CA，不含用户安装的证书）；不设置 `badCertificateCallback`，不做证书固定（V1）。
- 非 2xx 状态码不抛异常，原样返回 `HttpResult`（调用方按 CORE-02 解析）；不自动重试、一律不跟随重定向，含同主机；3xx原样返回（`followRedirects = false`）。
- 不记录请求体、响应体与请求头值；`AppLog` 只记录用途、状态码、耗时与 trace id（CORE-28 日志规则）。
- 后台不保持连接、不使用前台服务或 WorkManager；应用退到后台时进行中的请求由调用方决定是否取消。
- 外部前提：不引入 HTTP 插件或 OkHttp；Kotlin 侧只有代理查询一个方法。

**验收标准**：测试方案全文见 [Test/and/S2_AND-09_TEST.md](../Test/and/S2_AND-09_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 350 行；`app/lib/platform/android/net/`、`app/android/.../NetBridge.kt`、`app/`。组件估算：请求/响应/续传状态与纠错重发约 175 行，流式写/取消/总时限/异常约 115 行，代理通道与刷新/TLS守卫/接入约 60 行。只计本卡交付实现及附属接入代码；验证测试、夹具与静态配置/资源数据不计。

---

