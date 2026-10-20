### WIN-10 网络传输

**目标**：提供 Windows 上的 `HttpTransport` 端口实现：仅 HTTPS、系统证书、超时、取消、流式落盘与断点续传，并跟随系统静态代理。

**范围**
- 包含：`WindowsHttpTransport`（基于 `dart:io` `HttpClient`）；系统代理读取（通道 `fml/windows/net`）；异常到 CORE-04 错误码的映射；契约套件运行。
- 不包含：主机白名单、用途与授权检查（CORE-28 `NetworkGuard` 包裹本卡实现）；云识别前后台行为（CORE-34）；资源包下载流程（CORE-51）；更新下载流程（WIN-03）。

**依赖**：CORE-01、CORE-02、CORE-04、WIN-01、WIN-17

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
// app/lib/platform/windows/net/windows_http.dart
final class WindowsHttpTransport implements HttpTransport {
  WindowsHttpTransport(AppLifecycle lifecycle, {SecurityContext? testContext});
  void dispose();   // 内部持有一个 HttpClient：connectionTimeout 5 s，idleTimeout 15 s，autoUncompress false（仅接受identity），userAgent 'FML/<版本> Windows'
}
```

```text
send(req, cancel) 步骤（调用前由CORE-28完成HTTPS/主机/Cookie/用途校验）：
  1 rangeStart != null且(saveTo==null或rangeStart<0) → ArgumentError；rangeStart>0要求文件存在且长度恰好相等，否则ArgumentError，不修改文件
  2 打开请求、followRedirects=false、Accept-Encoding: identity；rangeStart>0加Range: bytes=<rangeStart>-；写入body
  3 saveTo==null → 收集响应上限16 MiB，超出中止并抛PLATFORM_IO
  4 saveTo非空：200截断重写；206仅在Content-Range起点==rangeStart（未指定视为0）、终点/长度合法、Content-Encoding为空或identity时追加；
    错位、非法或压缩206不写入本次响应，关闭响应后只重发一次无Range请求（仍在原总时限内）并截断重下；重发仍非法则PLATFORM_IO，不递归重试；其他状态不写文件，响应body按16 MiB上限返回
  5 req.timeout覆盖连接/响应/落盘与一次纠错重发；cancel在等待及每64 KiB检查，HttpClientRequest.abort并抛FfiCancelled
异常映射：SocketException、HttpException → NET_OFFLINE；HandshakeException、TlsException → NET_TLS；TimeoutException → NET_TIMEOUT；FileSystemException → PLATFORM_IO
系统代理：构造时与每次 lifecycle resumed 后经 MethodChannel "fml/windows/net" 的 proxy → {host, port} 或 null
          （WinHttpGetIEProxyConfigForCurrentUser：取 lpszProxy 中 https= 项，无则取不带协议前缀的项；fAutoDetect 或 lpszAutoConfigUrl 存在而无静态代理 → null）
          设置 HttpClient.findProxy；读取失败按直连
```

- 错误码：只使用 CORE-04 登记的 `NET_OFFLINE`、`NET_TLS`、`NET_TIMEOUT`、`PLATFORM_IO`；取消抛 CORE-03 `FfiCancelled`；本卡不新增错误码。

构造器订阅传入的AppLifecycle，在构造和resumed后刷新代理；dispose取消订阅并关闭HttpClient（本卡实现显式dispose方法，组装层生命周期清理调用）。testContext仅供非发布测试构造；kReleaseMode且非空运行时抛StateError，不用assert，不设置badCertificateCallback。生产使用默认信任库。与AND-09共同遵守CORE-04的续传验证协议；平台不引用对方卡作会话材料。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

**实现约束**
- 证书只用 `dart:io` 默认信任库；不设置 `badCertificateCallback`，不做证书固定（V1）。
- 非 2xx 不抛异常、不自动重试、`followRedirects = false`；不记录请求体、响应体与请求头值。
- 两端传输实现刻意保持同构（同一步骤与映射表），差异只在代理读取；两者都跑 CORE-04 契约套件。
- 外部前提：不引入 HTTP 插件；PAC 自动代理脚本不支持（记入附录 D 遗留），企业网络需配置静态代理。

**验收标准**：测试方案全文见 [Test/win/S2_WIN-10_TEST.md](../Test/win/S2_WIN-10_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 240 行；`app/lib/platform/windows/net/` 与 `app/windows/runner/net_channel.cpp`（同属 `app/` 构建单元）。

---

