# CORE-62 测试方案

> 来源卡：[S2_CORE-62_账户.md](../../core/S2_CORE-62_账户.md)（客户端 API 与令牌刷新适配）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R24] Fake HttpTransport：401→刷新→重试成功；刷新失败不循环，抛 AUTH_REAUTH_REQUIRED；并发401只发一次刷新；426通知订阅者。
- [R24] Fake HttpTransport：purpose=cloudRecognition 的 POST 遇 401、刷新成功时抛 `AUTH_UPLOAD_RECONFIRM_REQUIRED`，传输层只收到 1 次该 POST 和 1 次刷新；刷新失败时抛 `AUTH_REAUTH_REQUIRED`；每个请求的 `HttpRequestDto.purpose` 与 `consentToken` 与调用参数逐字相同。

- [R26][R40] 401、连接异常及超时的cloudRecognition均只有一次POST；相同requestId的后续调用必须由上层重新确认并传新consentToken，ApiClient不保存/重用令牌；idempotencyKey逐字透传，刷新不改变它。
