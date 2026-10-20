### CORE-45 邮箱验证码与发信

**目标**：为注册与找回口令生成、发送、校验 6 位邮箱验证码，并以可替换的境内发信服务完成投递（ADR-V5-11）。

**范围**
- 包含：`EmailCodeService` 的实现、验证码存储与限流、`POST /v1/auth/email-codes` 端点、`EmailSender` 端口及阿里云邮件推送、腾讯云 SES、Fake 三个实现、主备切换、邮件模板（简体中文）。
- 不包含：注册与找回口令端点本身（CORE-22）；发信账号、域名 SPF/DKIM/DMARC 与额度告警（CORE-43）。

**依赖**：CORE-01、CORE-02、CORE-22

**接口契约**

```text
POST /v1/auth/email-codes   { email, purpose: register|reset_password } → 202 { resend_after_s: 60 }
                            （无论邮箱是否已注册都返回 202 与相同响应体，不暴露账户是否存在）
```

```rust
// server/src/email/mod.rs —— 发信端口，供应商实现可替换（ADR-V5-11）
pub struct ProviderMessageId(pub String);
pub enum EmailError { Retryable(String) /* 超时、限流、5xx */, Permanent(String) /* 地址无效、鉴权失败、额度用尽 */ }
#[async_trait]
pub trait EmailSender: Send + Sync {
    async fn send_code(&self, to: &str, code: &str, purpose: EmailPurpose, locale: &str)
        -> Result<ProviderMessageId, EmailError>;
}
// 实现：AliyunDirectMail（默认）、TencentSes（备用）、FakeEmailSender（测试，记录到内存）
// server/src/email/service.rs：impl EmailCodeService for EmailCodeServiceImpl（CORE-22 定义的端口）
```

- 表（`server/migrations/0045_email_code.sql`）：`email_code`（`email_hash BYTEA`，`purpose TEXT`，`code_mac BYTEA NOT NULL`，`expires_at TIMESTAMPTZ`，`failed_attempts SMALLINT NOT NULL DEFAULT 0`，`consumed_at NULL`，PK `(email_hash, purpose)`）、`email_send_counter`（`scope TEXT`（`email:<hash>` 或 `ip:<addr>`），`window_start TIMESTAMPTZ`，`count INTEGER`，PK `(scope, window_start)`）。`email_hash` = HMAC-SHA256(服务端密钥, 规范化邮箱)。
- 错误码（本卡唯一定义）：

| 错误码 | 级别 | 可重试 | HTTP | 触发条件 |
| --- | --- | --- | --- | --- |
| `AUTH_EMAIL_CODE_INVALID` | error | 否 | 400 | 验证码错误、已使用或 5 次输错已作废 |
| `AUTH_EMAIL_CODE_EXPIRED` | error | 否 | 400 | 超过 10 分钟 |
| `AUTH_EMAIL_SEND_FAILED` | error | 是 | 503 | 主备通道均失败 |

复用 CORE-22 `AUTH_RATE_LIMITED`：发码阈值见下方限流，返回 429 与 Retry-After；本卡不重复定义。

**实现约束**
- 邮箱验证码：6 位数字，由 CSPRNG 生成；有效期 10 分钟、一次性使用；同一邮箱同一用途只保留最新一个；服务端只存 HMAC-SHA256(服务端密钥, 邮箱‖用途‖验证码)，比较用常量时间；输错 5 次即作废，需重新获取。
- 发送限流：同一邮箱 60 秒内 1 次、每日 10 次；同一 IP 每小时 20 次；超限返回 `AUTH_RATE_LIMITED`。限流计数在发送前检查，避免消耗发信额度；两个通道都失败时不计次。
- 主备切换：配置 `email.primary` / `email.fallback`；主通道返回 `Retryable` 时切备用，`Permanent` 不切换；同一验证码最多成功发出一次。
- 计数：每次调用供应商后以 `metrics` crate 门面记一次 `metrics::counter!("fml_email_send_total", "provider" => <id>, "result" => "ok" 或 "retryable" 或 "permanent")`；导出器由 CORE-43 安装，本卡不依赖导出器（未安装时计数为空操作）。
- 邮件只含验证码、用途、有效期与“非本人操作请忽略”；不含链接与跟踪像素。日志不记验证码，邮箱只记脱敏形式（如 `a***@qq.com`）。
- Casdoor 不配置原生邮件 provider（或只指向本服务内部受认证适配器），其公开注册、找回与“发送验证码”入口关闭；所有验证码都经本卡发出。部署检查由 CORE-43 执行（附录 A §A.4.4）。
- 外部前提：阿里云邮件推送与腾讯云 SES 的发信账号、已验证发信域名与 API 凭据由 CORE-43 提供（附录 A §A.4.3）；两家 HTTP API 的签名方式按各自官方文档实现，SDK 是否引入在 M0 定（ADR-V5-15）；单元测试只用 Fake，供应商实现以录制的请求样例做契约测试。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-45_TEST.md](../Test/core/S2_CORE-45_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 380 行；主包 `server/`（`server/src/email/` 与 `server/src/auth/email_codes_route.rs`）。

