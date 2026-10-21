### CORE-22 服务端骨架与身份认证

**目标**：搭建最小服务端（模块化单体），提供注册、登录、令牌刷新、设备登记与版本门禁，作为同步、云识别网关与邮箱验证码的共同基础。

**范围**
- 包含：server/ 认证、设备、版本、业务账户映射与令牌族代理；公开 HTTP 契约。
- 不包含：Dart ApiClient/TokenStore，迁至 CORE-62（下游说明，非契约）；发信实现 CORE-45（下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-04

**接口契约**

```text
POST /v1/auth/register            { email, email_code, password } → 201 { account_id }（不返回授权码；随后显式 authorize）
POST /v1/auth/password/reset      { email, email_code, new_password } → 204（身份服务吊销该账户全部会话/刷新令牌后才成功）
GET /v1/auth/authorize            302 → Casdoor discovery 的 authorization_endpoint；保留 client_id、redirect_uri、state、nonce、code_challenge=S256
POST /v1/auth/token               代理 discovery 的 token_endpoint，本服务作为机密客户端注入 client_secret；authorization_code 必带原 code_verifier；
                                  refresh_token 必轮换并经令牌族表检测重放；可带头 X-Fml-Device-Id 把令牌族绑定到设备
POST /v1/auth/logout              { refresh_token } → 204（吊销该刷新令牌所在令牌族；令牌未知也返回 204）
POST /v1/devices                  { device_id (UUID), platform: android|windows, app_version } → 201；同一 device_id 重复登记返回 200
GET  /v1/devices                  → 200 { devices: [{ device_id, platform, app_version, created_at, last_seen_at, current: bool }] }（只含未吊销设备）
DELETE /v1/devices/{device_id}    吊销设备并吊销绑定该设备的令牌族 → 204（触发 CORE-26 密钥轮换提示）
GET  /v1/meta/client-policy       → 200 { min_app_version, api_major: 1 }（无需令牌）
GET  /healthz                     → 200 { status: "ok", version }
所有请求头：Authorization: Bearer <token>（除注册、令牌、client-policy、healthz）；X-Fml-App-Version；X-Fml-Request-Id（32 位十六进制，缺省由服务端生成）
版本过低：HTTP 426 { error: { code: "SERVER_CLIENT_TOO_OLD", … }, min_app_version }
错误体：CORE-02 的 FmlError JSON（`error.code`、`error.retryable`、`error.trace_id` = 请求 ID）；HTTP 状态取注册表 `http_status`
限流响应：429 + 头 `Retry-After`（秒），错误码 `AUTH_RATE_LIMITED`
```

```rust
// server/src/auth/email_code.rs —— 由 CORE-45 实现，本卡只定义并在测试中使用 Fake
pub enum EmailPurpose { Register, ResetPassword }
#[async_trait]
pub trait EmailCodeService: Send + Sync {
    async fn request(&self, email: &str, purpose: EmailPurpose, client_ip: IpAddr) -> Result<RequestOutcome, FmlError>;
    async fn verify_and_consume(&self, email: &str, purpose: EmailPurpose, code: &str) -> Result<(), FmlError>;
}
pub struct RequestOutcome { pub resend_after_s: u32 }
// server/src/config.rs 中的发信配置键（值由 CORE-43 部署注入）：
// email.primary = "aliyun" | "tencent"、email.fallback、email.aliyun.*、email.tencent.*、email.code_hmac_key
```

- 唯一所有权：Casdoor 保存邮箱/口令哈希、授权会话、签名密钥、授权码与刷新令牌；业务 PostgreSQL 的 account 只保存 id UUID PK、oidc_issuer TEXT、oidc_sub TEXT、email_normalized TEXT UNIQUE、created_at、deleted_at，UNIQUE(oidc_issuer,oidc_sub)。device 保存 id、account_id、platform、app_version、revoked_at；audit_log 保存 action、request_id、at。业务库不保存 password_hash，也不保存刷新令牌明文；令牌族表只存 HMAC（见下条）。
- 注册/找回门面只经内部受认证 Casdoor 管理适配器执行，禁止公开管理凭据：先用 EmailCodeService 校验消费，再以请求 ID 幂等创建身份账户/改密与吊销；跨系统结果记 auth_operation(id PK, action, email_hash, state, subject NULL)，故障重试先查 subject 与状态，绝不因本地超时再次消费验证码。验证码未通过不查询或透露账户存在性。Casdoor 默认公开注册/找回关闭，所有本项目入口都经该门面；原生表单若启用，也必须调用同一门面。
- 登录/重新认证：系统浏览器打开 authorize，state 与 nonce 随机生成并绑定本机待完成请求，回调 URI 严格白名单，授权码只由 Casdoor 在成功登录后的重定向签发。账户入口发起的登录一律带 prompt=login，系统浏览器里残留的 Casdoor 会话不能静默登入（共用设备）。敏感操作遇 AUTH_RECENT_LOGIN_REQUIRED 时以 prompt=login、max_age=0 重新走 PKCE，并用这次换得的访问令牌立即重发敏感请求；失败不执行敏感操作。
- 令牌声明：iss、sub、aud、exp、iat、jti 必填；auth_time 只出现在授权码换得的令牌中，值为身份服务本次交互认证的 UTC 秒。Casdoor 刷新签发的令牌不带 auth_time，也不带 sid（ADR-V5-32），因此普通接口不要求 auth_time，敏感接口（CORE-25 的 `POST /v1/sync/reset` 与 `POST /v1/account/delete`）在 auth_time 缺失或 now-auth_time >300 s 时返回 AUTH_RECENT_LOGIN_REQUIRED，不能用 iat 冒充。校验固定 issuer/audience、允许算法白名单、discovery 的 JWKS 签名、exp/nbf（容差 60 s）；ID token 还校验 nonce，不能当 API access token。业务 account_id 由 (iss,sub) 映射。令牌 payload 不得含邮箱、手机号、昵称、头像（Q7 含未成年人）：Casdoor 应用 TokenFormat 固定为 JWT-Custom，tokenFields 只选非个人信息字段；JWT 与 JWT-Empty 格式都会内嵌邮箱，禁止使用。
- 令牌族（ADR-V5-32）：Casdoor 对授权码换得的令牌，刷新时要求 client_secret，只有本服务持有，因此刷新只能经 /v1/auth/token。表 `auth_refresh_family`（family_id UUID PK、account_id、device_id UUID NULL、current_hash BYTEA UNIQUE、created_at、rotated_at、revoked_at NULL）与 `auth_refresh_used`（hash BYTEA PK、family_id、used_at，保留 30 天），hash = HMAC-SHA256(服务端密钥, refresh_token)。授权码换令牌成功后建族；刷新时先查 used 表，命中即重放：吊销整族并返回 AUTH_REFRESH_REVOKED；再按 current_hash 行锁定后调用 Casdoor，成功则旧 hash 移入 used、current_hash 换为新值；Casdoor 判为无效时同样吊销整族。Casdoor 超时或 5xx 返回 SERVER_UNAVAILABLE，不移动 hash。登出、找回口令、吊销设备分别吊销对应的一族、该账户全部族、该设备绑定的族；已签发的访问令牌最长 15 min 自然过期。
- 错误码（唯一所有者；服务端复用只描述处理，不重复登记）：

| 错误码 | 级别 | 可重试 | HTTP | 触发条件 |
| --- | --- | --- | --- | --- |
| `AUTH_INVALID_CREDENTIALS` | error | 否 | 401 | 邮箱或口令错误（不区分哪一项） |
| `AUTH_TOKEN_EXPIRED` | error | 否 | 401 | 访问令牌过期 |
| `AUTH_REFRESH_REVOKED` | error | 否 | 401 | 刷新令牌已吊销、过期、不在令牌族表中，或旧刷新令牌被重复使用（同时吊销整个令牌族） |
| `AUTH_REAUTH_REQUIRED` | error | 否 | — | 仅客户端刷新失败，回到账户入口 |
| `AUTH_RECENT_LOGIN_REQUIRED` | error | 否 | 401 | 服务端敏感操作的 auth_time 缺失（刷新所得令牌）或距今超过 300 s |
| `AUTH_EMAIL_TAKEN` | error | 否 | 409 | 注册时邮箱已存在（验证码校验通过之后才返回，避免枚举） |
| `AUTH_PASSWORD_WEAK` | error | 否 | 400 | 口令少于 8 个字符或在常见口令表中 |
| `AUTH_RATE_LIMITED` | error | 是 | 429 | 登录同一邮箱 15 min 内失败 10 次、同一 IP 每分钟超过 60 次认证请求；CORE-25 推送超过每账户每分钟 60 次；CORE-45 发码限流（均带 `Retry-After`） |
| `SERVER_CLIENT_TOO_OLD` | error | 否 | 426 | `X-Fml-App-Version` 低于 `min_app_version` |
| `SERVER_UNAVAILABLE` | error | 是 | 503 | 数据库或依赖不可用（可重试） |

验证码相关错误码（`AUTH_EMAIL_CODE_*`）由 CORE-45 定义；客户端网络错误为 CORE-04 的 `NET_*`。

规模复核：auth路由/令牌校验160、devices70、meta/config/main50，共280（测试约180行，按README §8.4不计入规模）；邮件与注册门户归CORE-45，不在本卡重复实现。

**实现约束**
- 技术选型：Rust（axum）+ PostgreSQL + 对象存储；与客户端核心共享 `contracts/` 中的错误码与 DTO 定义（ADR-V5-03，见附录 A）。
- OIDC 授权服务固定为 Casdoor；本服务只实现业务映射与适配，绝不签发授权码或令牌（ADR-V5-14、附录 A §A.4.4）。访问令牌 15 min，刷新令牌轮换且闲置 30 天失效；对应 Casdoor 应用配置 ExpireInHours=0.25、RefreshExpireInHours=720、DisableRefreshRotation=false、TokenFormat=JWT-Custom，与镜像 digest 一起锁定（ADR-V5-15）。这些是部署验收策略，不能假定 Casdoor 出厂配置已满足。
- 资源所有者只取自令牌，忽略客户端提交的 account_id；参数化查询；TLS ≥ 1.2（优先 1.3）；签名与令牌密钥轮换周期 ≤ 90 天。
- API 只做向后兼容的加法变更；破坏性变更升 `/v2`。
- 日志只记账户 ID、请求 ID、路由、状态码与耗时，不记请求体。
- 账户标识只用邮箱：V1 不收集、不绑定手机号，不接短信验证码（暂无运营商短信通道，README §6 Q9）。
- 注册只有验证码校验通过才创建账户；找回口令成功后吊销该账户所有刷新令牌。口令不参与账户密钥派生（ADR-V5-05），找回口令不影响端到端加密数据。
- 外部前提：Rust stable、axum、sqlx、PostgreSQL、Casdoor 的版本与 digest 按开工锁定规则确定（ADR-V5-14、ADR-V5-15）；测试用 PostgreSQL 容器。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-22_TEST.md](../Test/core/S2_CORE-22_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 280 行；主包 `server/src/{main.rs,config.rs,auth/,devices/,meta/}`、`server/migrations/0022_auth.sql`。

