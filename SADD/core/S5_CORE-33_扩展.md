### CORE-33 服务端云识别网关与 worker

**目标**：提供唯一的云端识别入口，统一鉴权、配额、幂等、供应商调用与临时数据清理，供应商 API Key 只存在于服务端。

**范围**
- 包含：`/v1/recognition/jobs` 接口、任务表与状态机、配额预留与结算、幂等、供应商适配器（统一图片输入、请求上限、模型版本、返回结构与错误分类）、超时与取消、输出过滤、临时图片加密存储与清理、费用墓碑、全局预算熔断。
- 不包含：客户端（CORE-34）；部署、密钥管理与监控（CORE-43）。

**依赖**：CORE-01、CORE-02、CORE-22

**接口契约**

```text
GET  /v1/recognition/policy               → 200 { providers: [{ backend_id, provider_name, model_version, region: "cn", policy_version, retention_days, trains_on_data: false,
                                                                consent_id? /* 当前账户已同意当前版本时返回 */ }],
                                                   quota: { daily_limit, used_today } }
POST /v1/recognition/consents             { backend_id, policy_version, age_under_14: bool, guardian_confirmed: bool } → 201 { consent_id }
     （同一账户、backend_id、policy_version 重复调用返回同一 consent_id；age_under_14 为自我声明（README §6 Q14），为 true 时 guardian_confirmed 须为 true，否则 403）
POST /v1/recognition/jobs
  Headers: Authorization: Bearer <access_token>; Idempotency-Key: <uuid>
  Body: { image_base64 (PNG，≤ 4 MiB，≤ 4 MP), image_hash (SHA-256 小写十六进制), consent_id, policy_version, backend_id,
          mode: "lookup"|"answer", context: { subject?, symbol_hints[≤ 50] } }
  → 202 { job_id, state: "QUEUED" }
GET  /v1/recognition/jobs/{job_id}        → 200 { state, candidates?: [{ latex, confidence? }], model_version, error_code?, billed: "none"|"reserved"|"charged"|"unknown" }
POST /v1/recognition/jobs/{job_id}/cancel → 200 { state }（已提交供应商的任务只置 CANCEL_REQUESTED，结果到达后丢弃，billed 如实返回）
服务端状态：QUEUED → SUBMITTING → RUNNING → SUCCEEDED | FAILED；QUEUED/SUBMITTING/RUNNING → CANCEL_REQUESTED → CANCELLED；
            worker 在 SUBMITTING 后崩溃 → UNKNOWN；结果保留期（24 h）过后查询 → EXPIRED_UNKNOWN（只剩墓碑）
```

```rust
// server/src/recognition/provider.rs
#[derive(Serialize, Deserialize)]
#[serde(rename_all="snake_case")]
// 服务端不依赖 fml-recognize：本地镜像 CORE-29 的识别模式枚举，取值与 CORE-29 逐字一致，由同一向量 recognition-mode.json 测试；不是第二个契约
pub enum RecognitionModeWire { Lookup, Answer } // JSON 只有 lookup/answer，其他值 HTTP400
pub struct ProviderPrompt { pub mode: RecognitionModeWire, pub subject: Option<String>, pub symbol_hints: Vec<String> } // 模板在 server/src/recognition/prompts/
pub struct ProviderOutput { pub candidates: Vec<(String, Option<f32>)>, pub model_version: String, pub billed_units: u32 }
pub enum ProviderError { Timeout, RateLimited, Rejected(String /* 供应商错误码，不含图片或文本 */), Transport, Unknown }
#[async_trait]
pub trait VisionProvider: Send + Sync {
    fn id(&self) -> &str;                          // = backend_id；端点来自配置白名单
    fn model_version(&self) -> &str;
    async fn recognize(&self, png: &[u8], prompt: &ProviderPrompt, deadline: Duration) -> Result<ProviderOutput, ProviderError>;
}
// 实现：server/src/recognition/providers/<id>.rs；测试替身 FakeVisionProvider（可编程延迟、错误、非法输出，记录调用次数）
```

- 表（`server/migrations/0033_recognition.sql`）：`recognition_consent`（`consent_id UUID PK`，`account_id`，`backend_id`，`policy_version`，`age_under_14`，`guardian_confirmed`，`created_at`；UNIQUE `(account_id, backend_id, policy_version)`）；`recognition_job`（`job_id UUID PK`，`account_id`，`device_id`，`idempotency_key`，`image_hash`，`backend_id`，`mode`，`state`，`billed`，`model_version NULL`，`result_sealed BYTEA NULL`（服务端数据密钥加密），`error_code NULL`，`created_at`，`updated_at`，`expires_at`；UNIQUE `(account_id, idempotency_key)`）；`recognition_quota`（`(scope, scope_key, day) PK`，scope ∈ account/device/ip，`reserved`，`charged`）；`recognition_budget`（`day PK`，`spent_units`，`reserved_units`，`overrun_units`（实际扣费超过预占的累计量），`breaker_open`（布尔，超额后置真））；`recognition_provider_breaker`（`(provider_id, day) PK`，`opened_at`，`reason`，`cleared_at NULL`，`cleared_by NULL`）；`recognition_tombstone`（`job_id_hash PK`，`billed`，`final_state`，`created_at`；30 天）。临时图片存对象存储 `recog-tmp/<job_id>`，以每任务随机密钥加密，密钥只在 `recognition_job` 行内（终态即删）。
- worker：`tokio` 任务池，并发 `recognition.workers`（默认 4）；取任务用 `SELECT … FOR UPDATE SKIP LOCKED`；先把状态写为 SUBMITTING 并提交事务，再调用供应商。
- 配置键（`server/deploy/config.example.toml`，CORE-43 注入）：`recognition.providers[] = { id, endpoint, model, api_key_env, timeout_s = 30 }`、`recognition.quota.account_daily = 50`、`device_daily = 50`、`ip_daily = 100`、`recognition.daily_budget_units`、`recognition.policy_version`、`recognition.workers = 4`。
- 错误码（HTTP 状态取 CORE-02 注册表）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `CLOUD_NOT_ELIGIBLE`（403） | error | 否 | 账户已删除或云识别被熔断 |
| `CLOUD_CONSENT_INVALID`（403） | error | 否 | `consent_id` 不属于该账户与 backend，或 `policy_version` 不是当前版本，或未满 14 周岁未经监护人确认 |
| `CLOUD_IMAGE_TOO_LARGE`（413） | error | 否 | 解码后 > 4 MiB 或 > 4 MP，或不是 PNG |
| `CLOUD_HASH_MISMATCH`（400） | error | 否 | 图片字节的 SHA-256 与 `image_hash` 不符 |
| `CLOUD_IDEMPOTENCY_CONFLICT`（409） | error | 否 | 同一 Idempotency-Key 已用于不同 `image_hash` |
| `CLOUD_QUOTA_EXCEEDED`（429） | warning | 是 | 账户、设备或 IP 当日配额用尽（`Retry-After` = 次日 0 点，Asia/Shanghai） |
| `CLOUD_BUDGET_BREAKER`（503） | error | 是 | 全局当日预算用尽、运维手动熔断、当日 `recognition_budget.breaker_open` 为真，或所选供应商在 `recognition_provider_breaker` 中有当日未解除记录 |
| `CLOUD_PROVIDER_TIMEOUT` | error | 是 | 供应商 30 s 内无响应（任务 FAILED，billed 按供应商回执，未知则 unknown） |
| `CLOUD_PROVIDER_ERROR` | error | 是 | 供应商返回错误或限流 |
| `CLOUD_OUTPUT_REJECTED` | warning | 否 | 供应商输出 > 256 KiB 或全部候选被过滤 |
| `CLOUD_UNKNOWN_OUTCOME` | warning | 否 | 任务处于 UNKNOWN（查询时作为 `error_code` 返回） |
| `CLOUD_JOB_NOT_FOUND`（404） | error | 否 | job_id 不存在或不属于该账户 |

**配额与计费事务**：daily_budget_units缺省0（未配置即关闭云识别，运维按合同额度显式启用）。本卡“冻结”仅指云识别熔断，不增加账户身份状态；删除账户由CORE-25处理。
| 事件 | 原子变更 |
| --- | --- |
| 首次同键提交 | 锁account/device/ip/day三行及全局budget，先检查当日 breaker_open 为假且所选供应商无未解除熔断行（否则 CLOUD_BUDGET_BREAKER），再检查charged+reserved+1≤各自上限，且全局spent_units+reserved_units+max_units_per_job≤daily_budget_units；各reserved+1，全局reserved_units+provider配置的max_units_per_job，创建QUEUED；任一失败整体回滚 |
| 未提交供应商前取消/排队超时 | 仅一次reserved→refunded，减三项reserved与全局预占，不增加charged |
| 供应商确认计费（含失败但已计费） | reserved→charged，三项reserved-1/charged+1；全局释放预占并spent_units+=实际units，按job唯一结算；实际units超预占仍据实增加spent_units并记录超额，原day及当前供应商熔断停止新提交，人工对账后解除，不截断真实费用 |
| 明确未计费失败 | reserved→refunded，释放全部预占 |
| 提交后结果未知/worker崩溃 | 保持reserved且billed=unknown，不自动重调；对账确知后才charged/refunded；日切后仍保留原day结算，不能退款到新day |
recognition_job增加quota_state reserved/charged/refunded、reserved_units、quota_day；recognition_budget的预占、超额与熔断列见上方表定义；配置键 `recognition.providers[].max_units_per_job` 必填且>0，缺失时服务启动失败。实际扣费超过预占时据实写 spent_units、累加 overrun_units，并置当日 breaker_open 与该供应商的 recognition_provider_breaker 行；解除熔断只能由运维在数据库执行CORE-72（下游说明，非契约）提供的 `server/ops/clear_recognition_breaker.sql`（参数/事务与审计规则在该卡，必须完成后才可运维解除），不提供自动解除或公网管理接口。UNKNOWN与迟到回执用同job事务CAS，重复回执不重扣。结果TTL删除不删除未结算预占；费用墓碑保留对账状态，不含用户内容。
服务端输出过滤：候选≤10，总UTF8≤256KiB；去定界符后拒绝URL、script、代码围栏及\input/\include/\href/\url；不解析或替用户修公式，客户端仍按CORE-31完整检查。

产品约束追踪：见README §6 Q8；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 只接受内联图片，不接受 URL；供应商端点固定白名单，不按请求内容转发任意地址，不执行工具、不访问外链、不运行返回代码。
- 只允许注册账户；无匿名端点。按账户、设备、IP 的每日配额，超出返回 429；全局每日预算熔断；异常时只冻结云识别。
- 幂等：持久化 (account_id, idempotency_key) 唯一、输入哈希与配额预留后才交给 worker；同键同图返回已有任务；提交给供应商后崩溃标记 UNKNOWN，不自动重新付费调用。
- 超时：连接 5 s、供应商 30 s、排队等待 30 s。供应商输出 ≤ 256 KiB，按不可信输入过滤。
- 临时图片加密暂存，终态后 ≤ 60 s 清理；崩溃残留 TTL ≤ 1 h；任务结果与幂等记录 ≤ 24 h，之后只保留费用与状态墓碑 30 天。日志、APM 与备份不含图片和识别文本。
- 供应商 API Key 由服务端密钥管理保存，可轮换；不进入客户端发布产物、资源包、日志或复现包。
- 只接入已核实保留、训练与删除政策的供应商；默认不跨境；政策变化时提升 `policy_version`（客户端须重新征得同意，CORE-34）。
- 供应商选型（具体厂商、模型与合同条款）为 M0 待定事项，见附录 A ADR-V5-16（待定）；本卡只依赖 `VisionProvider` 端口，验收全部使用 `FakeVisionProvider`。
- 外部前提：tokio、axum、sqlx、async-trait、对象存储 S3 兼容接口与服务端数据密钥（由 CORE-43 的密钥管理提供）；版本随 ADR-V5-15锁定；测试用 PostgreSQL 容器与内存对象存储替身。

配额规则落点包括request handler和worker同一数据库事务，不能用内存计数替代。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-33_TEST.md](../Test/core/S5_CORE-33_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 380 行；主包 `server/src/recognition/`（路由80、worker100、配额/幂等100、provider边界60、迁移40；不含测试约100）；运维解除脚本迁至CORE-72，不计入本卡。首个供应商适配另据实测规模复评，当前仅Fake，不以未选供应商估算为已交付。

