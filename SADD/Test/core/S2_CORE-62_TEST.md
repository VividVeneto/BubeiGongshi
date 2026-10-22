# CORE-62 测试方案

> 来源卡：[S2_CORE-62_账户.md](../../core/S2_CORE-62_账户.md)（客户端 API 与令牌刷新适配）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R24] Fake HttpTransport：401→刷新→重试成功；刷新失败不循环，抛 AUTH_REAUTH_REQUIRED；并发401只发一次刷新；426通知订阅者。
- [R24] Fake HttpTransport：purpose=cloudRecognition 的 POST 遇 401、刷新成功时抛 `AUTH_UPLOAD_RECONFIRM_REQUIRED`，传输层只收到 1 次该 POST 和 1 次刷新；刷新失败时抛 `AUTH_REAUTH_REQUIRED`；每个请求的 `HttpRequestDto.purpose` 与 `consentToken` 与调用参数逐字相同。

- [R26][R40] 401、连接异常及超时的cloudRecognition均只有一次POST；相同requestId的后续调用必须由上层重新确认并传新consentToken，ApiClient不保存/重用令牌；idempotencyKey逐字透传，刷新不改变它。
- [R24][R26][R40] 头映射：Fake HttpTransport 收到每个请求的 `X-Fml-Request-Id` 等于传入的 `requestId`，`idempotencyKey` 非 null 时另收到同名等值的 `Idempotency-Key`、为 null 时不带该头；`ApiResponse.requestId` 取 Fake 返回响应头 `x-fml-request-id`（CORE-04 的 `HttpResult.headers` 键为小写），该头缺失时回落为传入的 `requestId`；401 刷新重发与一次重试前后这两个头的值都不变（本卡不生成、不改写幂等键）。
- [R28] 请求体编码：Fake HttpTransport 收到的请求体字节等于 `utf8.encode(jsonEncode(json))`；键按传入 Map 的插入顺序、无空白、`a/b` 中的 `/` 不转义、非 ASCII 字符按 UTF-8 原样输出，Content-Type 为 `application/json; charset=utf-8`；json 为 null 时请求体为空且无该头。
- [R24] 刷新写回：Fake HttpTransport 对 `POST /v1/auth/token` 的刷新响应给出新 `access_token`/`refresh_token`/`token_type: Bearer`/`expires_in: 900` 时，Fake `TokenStore.save` 恰被调用一次且两参数分别等于响应中的 `access_token` 与 `refresh_token`（旧刷新令牌不残留）；重发的原请求带新的 `Authorization`。刷新响应缺 `refresh_token`、或 `token_type` 非 `Bearer`（`bearer` 小写仍通过）时不重发原请求、`save` 不被调用、抛 `AUTH_REAUTH_REQUIRED` 且 `clear` 恰调用一次、`ReauthenticationRequired` 只广播一次。
- [R24] 版本头：Fake HttpTransport 收到每个请求的 `X-Fml-App-Version` 等于 `ApiClient.appVersion`；未传 `--dart-define=FML_APP_VERSION` 时为 `0.0.0-dev`，传 `--dart-define=FML_APP_VERSION=1.2.3` 的测试构建中为 `1.2.3`；`ApiClient` 构造仍是 `ApiClient(transport, tokens, baseUrl: …)` 三参数（CORE-36 `composeApp` 调用点不变）。
- [R18] 事件与响应值对象可直接 `const` 构造：`const ApiResponse(200, null, 'r-1')`、`const ClientTooOld(null)`、`const ClientTooOld('1.4.0')`、`const ReauthenticationRequired()` 均通过静态分析；`ClientTooOld.minimumVersion` 来自 426 JSON 顶层 `min_app_version`，缺失或非法时为 `null`。
