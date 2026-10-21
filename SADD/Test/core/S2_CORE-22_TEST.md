# CORE-22 测试方案

> 来源卡：[S2_CORE-22_账户.md](../../core/S2_CORE-22_账户.md)（服务端骨架与身份认证）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18] 错误中间件注入零trace的FmlError，断言补入合法请求trace；注入已有不同非零trace的错误则保持不变，响应头X-Fml-Request-Id、响应日志request_id与error.trace_id一致且均非零32位小写hex。缺失/非法/全零入站头均分配非零fallback，成功响应使用请求trace；缺省http_status为400，已登记HTTP状态不被覆盖。
- [R18] CORE-01骨架上首次加入本卡后，cargo metadata --no-deps列出fml-server且根members只追加一次server，cargo build --workspace仍通过；客户端初始检查不要求server预存在。服务端不依赖fml-store/fml-ffi。
- [R28] 集成测试（`server/tests/auth.rs`，`EmailCodeService` 用 Fake，Casdoor 用受测 Fake 令牌端点）：注册仅得 account_id → 浏览器授权码 + PKCE 登录 → 刷新令牌轮换（旧刷新令牌再次使用返回 `AUTH_REFRESH_REVOKED`，同族最新刷新令牌随之失效）→ 登出后该族刷新返回 `AUTH_REFRESH_REVOKED`；吊销设备后绑定该设备的族失效，其他设备的族不受影响。
- [R24] 令牌过期或被吊销时，受保护接口返回 401，客户端刷新失败后回到账户入口而本地数据不受影响（`app/test/net/api_client_test.dart`，Fake `HttpTransport`）。
- [R24] 找回口令：Fake 验证码通过后新口令可登录、旧口令返回 `AUTH_INVALID_CREDENTIALS`、原刷新令牌全部失效。
- [R23] 客户端版本低于 `min_app_version` 时返回 426，客户端停止同步写入、本地功能照常（集成测试 + Fake 服务端）。
- [R18] 越权测试：用 A 的令牌访问 B 的设备或数据返回 404/403。

- [R18][R24] Casdoor 受测容器契约：错误 verifier/state/nonce 被拒；不带 client_secret 直接向 Casdoor 刷新授权码令牌被拒（刷新只能经本服务）；刷新重放使令牌族失效；刷新所得访问令牌调用敏感接口返回 `AUTH_RECENT_LOGIN_REQUIRED`，prompt=login 重新交互登录后成功，301 s 后再次被拒；访问、ID、刷新三种令牌的 payload 不含邮箱、手机号与昵称；验证码/管理适配超时重试不重复创建账户。Fake 通过只证明适配代码，不替代真实部署验收。
