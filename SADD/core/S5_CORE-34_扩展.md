### CORE-34 云识别客户端与授权回执

**目标**：在客户端完成注册用户的云识别：功能级知情同意、逐次上传预览与确认、提交、状态查询、取消与重启恢复，且绝不重复付费调用。

**范围**
- 包含：拉取供应商政策与配额、功能级同意（按 backend 与 `policy_version` 各一次，含年龄自我声明与监护人确认）、远程后端描述符登记（`recog.register_remote`）、逐次上传预览与确认、`ConsentToken` 签发与校验（实现 CORE-28 `ConsentVerifier`）、调用 CORE-33 接口、状态映射与识别会话状态推进、取消、启动时恢复 `pending_cloud_job`、失败回退到手工或本地。
- 不包含：HTTP 传输实现（AND-09、WIN-10）；同意页与预览页的界面（CORE-40，本卡只提供数据与动作）；监护人身份核验（V1 不做，见 README §6 Q14）。

**依赖**：CORE-01、CORE-02、CORE-04、CORE-22、CORE-23、CORE-28、CORE-30、CORE-32、CORE-33、CORE-62

**接口契约**

```dart
// app/lib/recognition/cloud/cloud_recognition_service.dart
final class ProviderPolicy {               // 来自 GET /v1/recognition/policy
  final String backendId, providerName, modelVersion, region, policyVersion; final int retentionDays; final bool trainsOnData;
  final String? consentId;                 // 非空 = 当前账户已同意该版本
}
final class QuotaInfo { final int dailyLimit, usedToday; }
final class CloudPolicySnapshot { final List<ProviderPolicy> providers; final QuotaInfo quota; final DateTime fetchedAt; }
final class FeatureConsentInput { final bool ageUnder14; final bool guardianConfirmed; }
final class UploadPreview {
  final String sessionId; final ProviderPolicy policy; final QuotaInfo quota;
  final File image;                        // StoreArea.staging 下 fit_for_upload 的输出 PNG（无元数据），即实际上传的字节
  final Uint8List imageHash;               // 该文件的 SHA-256
  final int width, height, byteLength;
}
final class ConsentToken { final String tokenId; final Uint8List imageHash; final DateTime expiresAt; } // 有效 10 分钟，只能用于一次提交
sealed class CloudJobState { const CloudJobState(); }
final class CloudRunning extends CloudJobState {}
final class CloudSucceeded extends CloudJobState { final List<({String latex, double? confidence})> candidates; final String modelVersion; }
final class CloudFailed extends CloudJobState { final String errorCode; final String billed; }
final class CloudCancelled extends CloudJobState { final String billed; }
final class CloudUnknown extends CloudJobState { final String billed; }     // UNKNOWN：不自动重新提交
final class CloudExpiredUnknown extends CloudJobState {}                    // 查询不到且已过 24 h：显示“可能已计费”

abstract interface class CloudRecognitionService implements ConsentVerifier {
  Future<CloudPolicySnapshot> fetchPolicy();
      // 游客 → RECOG_BACKEND_NOT_ALLOWED；成功后对 consentId 非空的 provider 调 recog.register_remote（BackendCaps：networked = true，
      // input_kinds = [image]，model_version 取自政策），对其余 provider 不登记
  Future<String> grantFeatureConsent(ProviderPolicy p, FeatureConsentInput input);   // POST /v1/recognition/consents → consentId；之后登记远程后端
  Future<UploadPreview> preparePreview(String sessionId, String backendId);
      // 取会话的裁剪增强图（CORE-32 recog.session.get）→ img.fit_for_upload（CORE-30）→ 计算哈希；会话转 Preview
  ConsentToken confirmUpload(UploadPreview preview);   // 用户在预览页点“上传识别”后调用；会话转 Authorized
  Future<String> submit(UploadPreview preview, ConsentToken token, {String? subject, List<String> symbolHints = const []});
      // POST /v1/recognition/jobs，返回 job_id；随后 recog.pending_cloud.record，会话转 Running
  Stream<CloudJobState> watch(String jobId);           // 前台时轮询 GET /jobs/{id}：1 s 起，×2 退避，上限 10 s；终态后关闭流并推进会话状态
  Future<void> cancel(String jobId);
  Future<int> resumePending();                         // 启动时对 recog.pending_cloud.list 逐个查询，只查询不重新提交；返回恢复的任务数
  @override
  bool verify(String consentToken, Uint8List? body);   // 供 NetworkGuard 调用
}
// app/lib/recognition/cloud/cloud_recognition_service_impl.dart：唯一实现，经 ApiClient（CORE-62，其 transport 为 NetworkGuard）访问服务端
```

- 幂等键：`Idempotency-Key = UUIDv5(NS_FML_CLOUD, sessionId + ":" + hex(imageHash))`，`NS_FML_CLOUD = UUIDv5(NAMESPACE_URL, UTF-8("urn:fml:cloud"))`；name为小写连字符sessionId + ASCII冒号 + imageHash的小写64位hex（无BOM/无尾换行），不得取系统本地编码。同一会话、同一张图的任何重试（含进程被杀后）都得到同一个键，服务端据此返回已有任务。
- `verify` 规则：令牌存在于内存表、未过期、未使用；请求体 JSON 的 `image_hash` 与令牌 `imageHash` 相同，且 `image_base64` 解码后 SHA-256 与之相同。校验通过即把令牌标为已用（同一令牌第二次校验返回 false）。令牌只存内存，进程重启后作废。
- 状态映射（服务端 → `CloudJobState` → CORE-32 会话状态）：

| 服务端 state | CloudJobState | 会话状态 |
| --- | --- | --- |
| QUEUED、SUBMITTING、RUNNING、CANCEL_REQUESTED | `CloudRunning` | Running |
| SUCCEEDED | `CloudSucceeded`（候选交 CORE-31 后处理） | Succeeded |
| FAILED | `CloudFailed` | Failed |
| CANCELLED | `CloudCancelled`（界面不保证未计费，显示 billed） | Cancelled |
| UNKNOWN | `CloudUnknown` | UnknownRemote |
| EXPIRED_UNKNOWN，或 404 且距提交已超过 24 h | `CloudExpiredUnknown` | ExpiredUnknown |
| 网络失败、5xx | 保持上一状态，流不结束 | 不变 |

- 错误码（本卡唯一定义，登记到 `contracts/errors/registry.yaml`；复用的码见下方引用表）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `CLOUD_TOKEN_EXPIRED` | warning | 否 | `submit` 时令牌已过期或已用；界面回到预览页重新确认 |
| `CLOUD_PREVIEW_STALE` | warning | 否 | 预览生成后会话图片被重新裁剪或切换增强（哈希变化） |

- mode 的 HTTP 值只取 CORE-29 RecognitionMode 的 lookup/answer（CORE-33 服务端按同一向量校验），其他值本地拒绝，不新增别名。

以下只列本卡展示/恢复处理；触发条件、级别与可重试性严格复用唯一定义卡，不在此改变语义。

| 错误码引用 | 唯一定义卡 | 本卡处理 |
| --- | --- | --- |
| `RECOG_BACKEND_NOT_ALLOWED` | CORE-29 | 仅游客请求networked后端时复用；锁定先由账户用例拒绝，不扩张此码语义 |
| `PRIVACY_CONSENT_MISSING` | CORE-28 | 由 NetworkGuard 抛出：令牌校验失败 |
| `CLOUD_*` | CORE-33 | 服务端返回，原样透传 |
| `NET_*`、`AUTH_REAUTH_REQUIRED` | CORE-04、CORE-22 | 传输与令牌刷新失败，原样透传 |
| `AUTH_UPLOAD_RECONFIRM_REQUIRED` | CORE-62 | 与 `CLOUD_TOKEN_EXPIRED` 同样处理：令牌作废，界面回到预览页重新确认，沿用同一幂等键 |

确定性幂等键黄金文件：`contracts/vectors/cloud-idempotency-v1.json`固定namespace派生值、name UTF-8与三个跨session/image期望；重试只重签授权令牌，不改变文件中的业务键。

**实现约束**
- 安装点：`app/lib/recognition/cloud/install.dart` 的 `installCloud(CompositionContext ctx)` 构造唯一实现，登记为 `CloudRecognitionService` 与 `ConsentVerifier` 两个类型，并以 order 60 登记 `resumePending` 启动钩子（游客跳过）；账户切换为注册用户解锁后调用一次 `fetchPolicy` 以登记远程后端。
- 前后台：`installCloud` 订阅 `ports.lifecycle.events()`；`paused` 时暂停全部 `watch` 的轮询计时器（流不关闭、不发请求）；`resumed` 时对每个未终结任务立即查询一次再按退避继续；进程被杀后由启动钩子 `resumePending` 接续。两端行为相同，平台卡不参与。
- 每次上传都需用户在预览页确认：预览显示实际上传的图（`UploadPreview.image`，已剥离元数据）、处理目的、网关与模型供应商、保留天数与是否用于训练、删除方式与今日剩余额度。只上传裁剪图或墨迹规范渲染图与最小上下文；不上传原图、相册、源路径、位置、完整笔记或设备标识。
- 功能级同意展示供应商、模型、用途、数据范围、保留、训练、处理地域（V1 只有境内，见 README §6 Q8）、费用；政策版本变化后 `consentId` 为空，须重新同意。同意页要求用户声明是否未满 14 周岁；声明未满时须由监护人勾选确认，否则不调用接口、云识别不可用（README §6 Q7）。V1 只做自我声明，不做监护人身份核验。
- 上传请求的 `HttpRequestDto` 用 `purpose: cloudRecognition` 并携带 `consentToken: token.tokenId`，经 ApiClient → NetworkGuard 发送；本卡不得直接使用平台 `HttpTransport`。
- 云识别失败时保留校正页面，允许手工输入或用户主动选择本地模型；本地识别失败时不得自动上传。
- 上传401：ApiClient不自动重发已消耗令牌，回预览重新确认；同图沿用业务幂等键，若服务端已创建则返回原job。所有POST上传的自动重试次数固定为0：401、连接中断、超时后均销毁旧ConsentToken；只有用户再次点击预览页的“上传识别”才confirmUpload签发新tokenId（新随机UUID、新10分钟到期时间），旧令牌永不复用。预览的sessionId/imageHash/policyVersion未变时沿用原业务Idempotency-Key；图片或会话变则新键，政策变则先重新功能同意。请求体字节可重建但须重新校验哈希；NetworkGuard对新令牌只验证/消费一次。已知job_id仅GET查询；未知job_id经重新确认再POST，服务端按旧幂等键返回已有job，不重复收费。进程重启后令牌表为空，resumePending仍只查询；用户拒绝重新确认不发送。
- 超时只表示客户端停止等待；重试只用同一幂等键；`resumePending` 从不发起 POST /jobs。
- 外部前提：`uuid`（v5）与 `crypto`（SHA-256）Dart 包，版本随 ADR-V5-15锁定；测试用 CORE-04 `FakeHttpTransport` 模拟服务端。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-34_TEST.md](../Test/core/S5_CORE-34_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约650行，分阶段：①模型、政策/同意、预览令牌与提交400行；②watch/取消150、pending恢复60、安装/账户/生命周期接入40，共250行；主包app/lib/recognition/cloud/及本卡聚合接入，无跨构建单元附属；自测与生成DTO不计。 阶段独立构建/测试：①政策授权与显式提交（400行）：以FakeHttpTransport验证用户显式动作、单次令牌、幂等业务键；提交返回job后持久化pending，不声称自动恢复已完成。；②观察恢复与安装（250行）：加流/退避/前后台/恢复钩子，验证重启无POST、断网不结束、终态关闭。

