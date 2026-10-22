### CORE-02 错误码注册表与诊断模型

**目标**：用一份注册表生成 Rust 与 Dart 的错误码和诊断类型，使所有模块的错误可定位、可本地化、可追踪。

**范围**
- 包含：`contracts/errors/registry.yaml` 格式、生成器、`fml-error` crate（`FmlError`、`Diagnostic`、`TraceId`）、Dart 侧 `FmlException` 与消息键。
- 不包含：复现包导出（CORE-28）；各模块具体错误码（各卡在注册表中追加条目）。

**依赖**：CORE-01

**接口契约**

注册表条目（`registry.yaml` 顶层为 `{ registry_version: <u32>, entries: [...] }`）：

```yaml
- code: TYPE_DIM_CONFLICT      # 大写蛇形，前缀为命名空间
  namespace: TYPE
  owner: CORE-09              # 首次定义卡；唯一所有权来源
  severity: error             # error | warning | info
  message_key: err.type.dim_conflict
  retryable: false
  since: 1
```

| 字段 | 类型 | 必填 | 取值与校验 |
| --- | --- | --- | --- |
| code | string | 是 | 正则 `^[A-Z]+(_[A-Z0-9]+)+$`；首段等于 namespace；全表唯一 |
| namespace | string | 是 | 下列命名空间之一 |
| owner | string | 是 | 有效卡号；该 code 的首次定义卡，唯一所有权来源 |
| severity | enum | 是 | error、warning、info |
| message_key | string | 是 | 固定为 `err.` + code 按首个下划线分为命名空间与余部后分别小写并以点连接（如 `TYPE_DIM_CONFLICT` → `err.type.dim_conflict`）；`errors_zh.arb` 中必须存在，不允许自由改名 |
| retryable | bool | 是 | 调用方原样重试可能成功时为 true |
| since | u32 | 是 | 引入时的 registry_version，`1 ≤ since ≤ registry_version`；registry_version ≥ 1 |
| deprecated_since | u32 | 否 | `since ≤ deprecated_since ≤ registry_version`；废弃条目保留且仍生成、可解析，不得复用 code |
| http_status | u16 | 否 | 仅在所有者卡约定由服务端输出的码可填，整数 400–599；服务端未填时映射 400。纯端侧码禁止填写；此字段不改变 FFI 返回码 |

命名空间：`AST_ CONTENT_ PARSE_ TYPE_ NOTATION_ UNIT_ EVAL_ ENGINE_ DERIVE_ TYPESET_ EXPORT_ STORE_ LIB_ PACK_ STUDY_ GRADE_ CRYPTO_ AUTH_ SYNC_ BACKUP_ PRIVACY_ RECOG_ IMG_ CLOUD_ FFI_ PLATFORM_ NET_ SERVER_`。错误码一经发布不得改义，只能废弃。

```rust
// crates/fml-error/src/lib.rs
// codes.rs 由生成器产出：#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)] pub enum ErrorCode { … }，
// 并生成 as_str()（注册表 code 原文）、domain()（命名空间前缀去下划线小写，如 TYPE_ → "type"）、severity()、retryable()（取注册表值）
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Default)]   // Default = 全零，表示“尚未填入”
pub struct TraceId(pub [u8; 16]);
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Severity { Error, Warning, Info }
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Diagnostic {
    pub code: ErrorCode,                 // 由 registry.yaml 生成的枚举
    pub severity: Severity,
    pub node_path: Option<String>,       // NodePath 的文本形式 "0.2.1"（CORE-05）
    pub input_range: Option<(u32, u32)>, // 源码 UTF-8 字节区间
    pub args: std::collections::BTreeMap<String, String>,     // 本地化参数
    pub recovery: Option<String>,        // 修复建议的消息键
    pub needs_confirm: bool,             // Warning 需用户确认时为 true
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FmlError {
    pub code: ErrorCode, pub domain: String,
    pub diagnostics: Vec<Diagnostic>, pub trace_id: TraceId, pub retryable: bool,
}
impl FmlError {
    pub fn new(code: ErrorCode) -> Self;                      // domain/retryable 取 code 的生成值，diagnostics 为空，trace_id = TraceId::default()；领域 crate（无 I/O、无随机）只用此构造
    pub fn with_diagnostic(self, d: Diagnostic) -> Self;      // 追加一条诊断
    pub fn with_trace(self, t: TraceId) -> Self;              // 由用例/FFI 层在返回前填入本次调用的 trace_id（仅当仍为零值时覆盖）
}
```

生成的 `ErrorCode` 变体按 code 的下划线分段：每段 ASCII 小写后仅首字母大写并连接（缩写段 AST、JSON 分别转换为 Ast、Json，数字段如 429 保持不变）；首段为字母，结果总是合法 Rust 标识符，生成器检测转换后名称碰撞并拒绝。实现 `FromStr` 与 `TryFrom<&str>`，失败返回公开的 `UnknownErrorCode`（实现 Debug/Display/Error），不得 panic、回退到其他码或丢失未知值错误。`ErrorCode` 的 Display 等于 `as_str()`；`FmlError` 实现 Display（仅 code 与 trace_id，不打印 diagnostics/args）与 `std::error::Error`（source 为 None），`From<ErrorCode>` 等价于 `new`。

serde：`FmlError`、`Diagnostic`、`Severity`（蛇形小写）与 `TraceId`（32 位小写十六进制字符串）按下例 JSON 形式实现 Serialize/Deserialize；`ErrorCode` 序列化为注册表 code 原文，反序列化拒绝未知码。保留公开字段，但序列化与反序列化均校验 `domain == code.domain()`、`retryable == code.retryable()`；每条 Diagnostic 的 severity 必须等于自身 code.severity()，不随外层错误级别改变。`input_range` 是 UTF-8 半开字节区间 `[start,end)`，两端 u32 且 start ≤ end；越界、倒序、未知字段与错误类型均报序列化错误，不悄悄修复。领域内零 trace 可往返；传输边界另行拒绝零值。`retryable` 与 `domain` 只由注册表按 code 决定：不提供调用点覆盖的构造或方法（无 with_retryable/with_domain 等），客户端、服务端与 FFI 也不得按调用点改写；同一失败需要不同重试语义时，登记不同 code。

Dart：`class FmlException implements Exception { final String code; final List<DiagnosticDto> diagnostics; final String traceId; final bool retryable; FmlException(String code, {List<DiagnosticDto> diagnostics = const [], String? traceId}); factory FmlException.fromJson(Map<String, Object?> json); }`；无名构造器供客户端本地错误（如各卡写的 `FmlException('SYNC_NOT_AVAILABLE')`）：code 必须在 `error_codes.g.dart` 中已登记，否则抛 ArgumentError；retryable 只取生成表；traceId 省略时以 Random.secure 生成非零 32 位小写十六进制，给出时按 fromJson 同规则校验；不提供覆盖 retryable/domain 的参数。工厂读取根对象 `{error:{...}}`（CORE-03 先剥除 v/外层 trace_id 等信封元数据），校验必填字段、已知 code、domain/retryable 与生成表相符、诊断 severity、区间与非零 32 位小写十六进制 trace_id；拒绝未知字段/类型或不一致值，抛 FormatException，不显示原始载荷。`DiagnosticDto` 唯一实现由 CORE-67 从共享 Diagnostic schema 生成到 `app/lib/binding/dto/`，字段与 Rust 一一对应（`code, severity, nodePath?, inputRange?, args, recovery?, needsConfirm`）；本卡只手写异常桥，不复制诊断序列化类。消息在 `app/lib/l10n/errors_zh.arb`；初次由本卡为全部基线已登记码建立简中消息，业务所有者审核文字，后续新增由所有者随登记片段提供。

`FmlError` 的 JSON 形式（FFI 返回码 1 的 `out` 与服务端错误响应体共用，字段名固定）：

```json
{ "error": { "code": "TYPE_DIM_CONFLICT", "domain": "type", "retryable": false,
    "trace_id": "0f8e…（32 位小写十六进制）",
    "diagnostics": [ { "code": "TYPE_DIM_CONFLICT", "severity": "error", "node_path": "0.2.1",
        "input_range": [4, 9], "args": { "left": "L", "right": "L T^-1" },
        "recovery": "err.type.dim_conflict.fix", "needs_confirm": false } ] } }
```

`diagnostics` 可为空数组；`node_path`、`input_range`、`recovery` 缺省表示无。`TraceId` 文本形式为 32 位小写十六进制。

生成命令：`tools/ci/gen_errors.py` 唯一读取 `contracts/errors/registry.yaml` 的错误元数据，输出 `crates/fml-error/src/codes.rs`、`app/lib/binding/error_codes.g.dart`、`contracts/errors/README.md`（含 owner/severity/retryable/http_status 的完整错误码表）、`contracts/errors/ownership.yaml`，并更新 `contracts/policies/shared-writes.json` 的 error 投影（保留其他类别不变）；顺序按 code 排序，结果确定。`--check` 只比较不改文件，任一生成物漂移即失败。生成器不从镜像或 SADD 反推 registry。

本卡 Rust/生成器可先独立构建；Dart 异常桥集成需 CORE-67 已生成 DiagnosticDto，未交付时标未执行，不用手写替身宣称整卡通过。黄金样例由本卡建立 `contracts/vectors/errors-v1.json`，固定外层 error、内层 code/domain/retryable/trace_id/diagnostics 顺序，Diagnostic 依结构声明顺序、args 按键排序，供 Rust 与 Dart 共同验证；不以 CORE-03/服务端尚未实现为本卡单元测试的隐性前提。

跨卡共享格式清单（索引只指向所有者，不在本卡复制定义；实现卡建立相应 contracts/vectors 文件）：

| 格式 | 唯一定义卡 | 版本 | 向量位置 |
| --- | --- | --- | --- |
| AST 规范 JSON、BLAKE3 | CORE-05 | ast_schema=1 | contracts/vectors/ast-canonical.yaml |
| UUIDv5 命名空间与拼接、seed | CORE-05 | id-v1 | contracts/vectors/ids-v1.json |
| WrapRecord、wrap_kind 与 AAD CBOR | CORE-21 | wrap=1、aad=1 | contracts/vectors/wrap-v1.json |
| Envelope | CORE-68 | envelope_version=2 | contracts/vectors/envelope-v2.json |
| merge_choice ID | CORE-05 | id-v1 | contracts/vectors/ids-v1.json |
| RecognitionMode 的 Rust/HTTP 取值 | CORE-29 | recognition_mode=1 | contracts/vectors/recognition-mode.json（CORE-29 创建与维护，CORE-33 镜像只读消费） |
| `.fmlbackup` 备份容器（头、块、清单、末块） | CORE-27 | format_version=1 | crates/fml-store/tests/vectors/backup_v1.hex（BK-V1；CORE-84 恢复只读消费） |
| 引擎数据 JSON（units/kinds/profiles/constants/fonts/manifest）与层叠加规则 | CORE-56 | schema=1 | contracts/vectors/engine-data-v1/ |

错误码只在首个所有者卡的标准表中登记；消费者写“复用 + 处理”，不得复制 severity/retryable。新增代码先登记 contracts/errors/registry.yaml，生成器拒绝重复 code。

错误码共享写入：registry.yaml 是 code/owner/namespace/severity/retryable/message_key/版本/http_status 的唯一真源。`ownership.yaml`（version=1，entries:[{code,owner}]）只是生成镜像，不接受独立手改；通用前缀可共享，不能以整段 AUTH_/PLATFORM_ 强行归某张业务卡。业务卡新增前提交 `{code,owner,severity,retryable,condition,http_status?}` 独立片段及简中消息，由 CORE-02 维护者合入 registry 后生成；遇到已占用 code 只引用所有者或先走契约变更单。初次创建 registry 必须收齐全部 SADD 标准错误表（包括 CORE-03/16/18 的 FFI_/CONTENT_/GRADE_），不得以“各卡后续追加”留下基线缺项。registry 未创建阶段，shared-writes.error 仅含 code/owner，现有 DTOcheck 只比对 SADD 与预分配表的 code/owner（缺项、重复、所有者不符及消费者重定义失败），不声称已检查 severity/retryable。registry 与生成器交付后，须由本卡补齐 SADD 对 registry 的 severity/retryable 逐项比较及全部生成镜像漂移检查；未交付时这些元数据/镜像检查明确未执行；触发条件仍由所有者卡定义，不生成第二份可编辑语义表。

PR3 预分配机器表 `contracts/policies/shared-writes.json` 的 error 项在 registry 未创建前为登记占位，由本卡单写，key 为完整错误码、owner 为首次定义卡；前缀不是所有权。建立 registry 时逐码核对并迁入 registry.owner，之后 shared-writes 的 error 项与 ownership 同为 registry 生成投影，不再独立维护；非 error 项不在本卡生成范围。后续新增必须先申请唯一 code。

**实现约束**
- UI 显示本地化消息；日志只记 `code`、`trace_id`、模块与版本、耗时与预算，不记公式正文、图片、路径、令牌、密钥或恢复码。
- 每次用例调用由 FFI/HTTP 适配层生成或验证非零 `trace_id`，领域 crate 无随机/I/O，`new` 的 trace_id 为零。边界返回前一律调用 `with_trace`；原值非零必须保留，不另造第二条错误链，零值不得出现在 FFI/HTTP 输出中。CORE-03 负责请求/完成回调，CORE-22/25 负责 HTTP 错误适配；FFI 外层 trace_id、HTTP request_id/日志关联值均取填充后的 `error.trace_id`，不是盲用新请求 ID。
- V1 只提供简体中文消息；缺失消息键时 CI 失败。
- 本卡不定义业务错误码；各卡在本卡注册表中追加条目，并在各自“接口契约”的错误码表中写明触发条件。
- 外部前提：Python 3 与 PyYAML（Python 版本见 `tools/toolchain.versions`，PyYAML 锁入 `tools/requirements.txt`，ADR-V5-15）。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-02_TEST.md](../Test/S0/S0_CORE-02_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约455行；主包 crates/fml-error/ 165行；附属 tools/ci/gen_errors.py及本卡CI接入230行、app/lib/binding/errors.dart手写异常桥60行；registry/ownership/消息资源与生成物不计。 单阶段可独立构建测试；只计本卡实现及本卡编写的附属接入，不计数据/生成物/自测。

