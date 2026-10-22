### CORE-62 客户端 API 与令牌刷新适配

**目标**：客户端 API 与令牌刷新适配，与原卡分开实施与验收。

**范围**
- 包含：ApiClient、ApiResponse、TokenStore；只消费 CORE-22 HTTP 协议。
- 不包含：依赖卡已定义的业务算法、存储与平台能力；不修改其契约。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-22

**接口契约**

```dart
// app/lib/net/api_client.dart（客户端侧最小封装，经 CORE-04 HttpTransport）
final class ApiResponse { const ApiResponse(this.status, this.json, this.requestId); final int status; final Map<String, Object?>? json; final String requestId; }
class ApiClient {
  // 版本头来源（D2 暂行默认）：构建期 --dart-define FML_APP_VERSION，缺省 0.0.0-dev（与界面卡关于页的版本同源）；不新增构造参数
  static const String appVersion = String.fromEnvironment('FML_APP_VERSION', defaultValue: '0.0.0-dev');
  Stream<NetEvent> get events;
  ApiClient(HttpTransport transport, TokenStore tokens, {required Uri baseUrl});
  Future<ApiResponse> call(String method, String path, {Object? json, required String requestId, String? idempotencyKey, required RequestPurpose purpose, String? consentToken});
  // 每个请求统一附加 Authorization: Bearer <tokens.accessToken()>（为 null 时不带该头）与 X-Fml-App-Version=<appVersion>；
  // 非cloudRecognition的401刷新后重试一次，刷新失败抛 FmlException('AUTH_REAUTH_REQUIRED')；
  // 刷新请求：POST /v1/auth/token，Content-Type: application/x-www-form-urlencoded，体 grant_type=refresh_token&refresh_token=<当前刷新令牌>（CORE-22，不递归刷新）；
  // 刷新成功：解析 /v1/auth/token 返回的 access_token、refresh_token、token_type、expires_in（秒）；token_type 大小写不敏感须为 Bearer，access_token 与 refresh_token 缺一即按刷新失败处理；
  // 解析成功后以一次 tokens.save(access_token, refresh_token) 同时写回两个值（两者都被轮换，旧值不保留；expires_in 不落地，本卡不做本地过期计时）；
  // cloudRecognition 上传遇401且刷新成功时不重发，抛 FmlException('AUTH_UPLOAD_RECONFIRM_REQUIRED')；
  // 426 → 抛 FmlException('SERVER_CLIENT_TOO_OLD') 并广播 clientTooOld 事件，由同步模块停止写入
}
abstract interface class TokenStore {   // 契约所有者为本卡；由 CORE-65 实现（经 SecureKeyValueStore 保存刷新令牌）
  Future<String?> accessToken(); Future<String?> refreshToken(); Future<void> save(String access, String refresh); Future<void> clear();
}
// 刷新写回口径：save 保持两参数签名，不加过期时间——刷新完全由 401 驱动、不做本地过期计时、CORE-22 的 expires_in 不持久化；
// 因此 CORE-65 的实现只需严格照本签名，无需变更。刷新失败走 tokens.clear()，并发 401 共享同一刷新结果，只广播一次 ReauthenticationRequired。
```



```dart
sealed class NetEvent { const NetEvent(); }
final class ClientTooOld extends NetEvent { const ClientTooOld(this.minimumVersion); final String? minimumVersion; // CORE-22 semver；无效或缺失为null }
final class ReauthenticationRequired extends NetEvent { const ReauthenticationRequired(); }
// ApiClient增加 Stream<NetEvent> get events；broadcast，响应426每请求发一次ClientTooOld；刷新失败只发一次ReauthenticationRequired。
```
最小版本只取426 JSON顶层min_app_version（CORE-22，SemVer字符串）；缺失或非法时minimumVersion=null，仍停止同步写入并提示升级，不回退为0；订阅不重放旧事件，Coordinator建立后先查自身状态。

**实现约束**
- call显式透传purpose/consentToken到HttpRequestDto，不按path猜用途。cloudRecognition只用于POST /v1/recognition/jobs且须令牌；查询/取消/政策/功能同意用CORE-04显式cloudControl（CORE-28仅放行固定路由），其他同步用sync，登录刷新用auth。上传遇401可共享刷新但不自动重发原POST：刷新成功抛 `AUTH_UPLOAD_RECONFIRM_REQUIRED`，调用方回到预览重新确认，沿用同一业务幂等键；刷新失败仍抛 `AUTH_REAUTH_REQUIRED`（回到登录）；该保守行为避免消耗型令牌被验证两次。其他用途401只刷新一次并重发一次；刷新请求不能递归刷新；并发401共享一次刷新Future，失败清令牌并广播重登。
- 请求体编码：`json` 非 null 时以 `dart:convert` 的 `jsonEncode` 编为 UTF-8 字节作为请求体（紧凑无空白、不转义 `/`、Map 按插入顺序输出键、整数原样输出），头 `Content-Type: application/json; charset=utf-8`；`json` 为 null 时不发请求体。ApiClient 不重排键、不追加字段，调用方可据此精确计量请求体字节（CORE-46 推送批次依赖此规则；下游说明，非契约）。
- 426 广播停止写入事件，错误复用 CORE-22。令牌和口令不写日志。
- 错误码（本卡唯一定义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `AUTH_UPLOAD_RECONFIRM_REQUIRED` | warning | 否 | `cloudRecognition` 上传遇 401 且刷新成功；按规则不自动重发，调用方须让用户在预览页重新确认后再提交 |

- 外部前提：沿用原卡已登记的工具链与依赖，按 ADR-V5-15 锁定；未获得的真机/供应商能力保留外部门槛。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-62_TEST.md](../Test/core/S2_CORE-62_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 200 行；主包 `app/lib/net/`。

