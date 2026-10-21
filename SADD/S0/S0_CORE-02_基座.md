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
  severity: error             # error | warning | info
  message_key: err.type.dim_conflict
  retryable: false
  since: 1
```

| 字段 | 类型 | 必填 | 取值与校验 |
| --- | --- | --- | --- |
| code | string | 是 | 正则 `^[A-Z]+(_[A-Z0-9]+)+$`；首段等于 namespace；全表唯一 |
| namespace | string | 是 | 下列命名空间之一 |
| severity | enum | 是 | error、warning、info |
| message_key | string | 是 | 正则 `^err\.[a-z0-9_.]+$`；`errors_zh.arb` 中必须存在 |
| retryable | bool | 是 | 调用方原样重试可能成功时为 true |
| since | u32 | 是 | 引入时的 registry_version，≥ 1 |
| deprecated_since | u32 | 否 | 废弃时的 registry_version；废弃条目保留，不得复用 code |
| http_status | u16 | 否 | 仅服务端返回的错误码填写（400–599），默认 400 |

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

serde：`FmlError`、`Diagnostic`、`Severity`（蛇形小写）与 `TraceId`（32 位小写十六进制字符串）按下例 JSON 形式实现 Serialize/Deserialize；`ErrorCode` 序列化为注册表 code 原文。

Dart：`class FmlException implements Exception { final String code; final List<DiagnosticDto> diagnostics; final String traceId; final bool retryable; }`；消息在 `app/lib/l10n/errors_zh.arb`。`DiagnosticDto` 字段与 `Diagnostic` 一一对应（`code, severity, nodePath?, inputRange?, args, recovery?, needsConfirm`）。

`FmlError` 的 JSON 形式（FFI 返回码 1 的 `out` 与服务端错误响应体共用，字段名固定）：

```json
{ "error": { "code": "TYPE_DIM_CONFLICT", "domain": "type", "retryable": false,
    "trace_id": "0f8e…（32 位小写十六进制）",
    "diagnostics": [ { "code": "TYPE_DIM_CONFLICT", "severity": "error", "node_path": "0.2.1",
        "input_range": [4, 9], "args": { "left": "L", "right": "L T^-1" },
        "recovery": "err.type.dim_conflict.fix", "needs_confirm": false } ] } }
```

`diagnostics` 可为空数组；`node_path`、`input_range`、`recovery` 缺省表示无。`TraceId` 文本形式为 32 位小写十六进制。

生成命令：`tools/ci/gen_errors.py` 输出 `crates/fml-error/src/codes.rs`、`app/lib/binding/error_codes.g.dart` 与 `contracts/errors/README.md`（错误码表）。

跨卡共享格式清单（索引只指向所有者，不在本卡复制定义；实现卡建立相应 contracts/vectors 文件）：

| 格式 | 唯一定义卡 | 版本 | 向量位置 |
| --- | --- | --- | --- |
| AST 规范 JSON、BLAKE3 | CORE-05 | ast_schema=1 | contracts/vectors/ast-canonical.yaml |
| UUIDv5 命名空间与拼接、seed | CORE-05 | id-v1 | contracts/vectors/ids-v1.json |
| WrapRecord、wrap_kind 与 AAD CBOR | CORE-21 | wrap=1、aad=1 | contracts/vectors/wrap-v1.json |
| Envelope | CORE-68 | envelope_version=2 | contracts/vectors/envelope-v2.json |
| merge_choice ID | CORE-05 | id-v1 | contracts/vectors/ids-v1.json |
| RecognitionMode 的 Rust/HTTP 取值 | CORE-29 | API v1 | contracts/vectors/recognition-mode.json |
| 引擎数据 JSON（units/kinds/profiles/constants/fonts/manifest）与层叠加规则 | CORE-56 | schema=1 | contracts/vectors/engine-data-v1/ |

错误码只在首个所有者卡的标准表中登记；消费者写“复用 + 处理”，不得复制 severity/retryable。新增代码先登记 contracts/errors/registry.yaml，生成器拒绝重复 code。

错误码共享写入：本卡创建contracts/errors/ownership.yaml（version=1，entries:[{code,owner}]，code唯一、owner为有效卡号），从各卡标准错误定义表逐码预登记；通用前缀可共享，不能以整段AUTH_/PLATFORM_前缀强行归某张业务卡。业务卡新增前提交{code,owner,level,retryable,condition,http?}独立片段，由CORE-02维护者合入registry和ownership后生成代码；遇到已占用code只引用所有者或先走契约变更单，禁止本地改语义。CI比对registry/ownership与SADD唯一定义，缺owner、重复code、消费者重定义均失败。

PR3预分配机器表contracts/policies/shared-writes.json中的error项由本卡单写，key为完整错误码、owner为首次定义卡；前缀只是命名空间，不替代逐码所有者（AUTH/PLATFORM可多卡共享不同码）。本卡建立registry时逐项迁入ownership并校验一致；后续新增必须先申请唯一code，不能占用整个通用前缀。

**实现约束**
- UI 显示本地化消息；日志只记 `code`、`trace_id`、模块与版本、耗时与预算，不记公式正文、图片、路径、令牌、密钥或恢复码。
- 每次用例调用生成 `trace_id`，跨 FFI 与 HTTP 透传；领域 crate 返回的 `FmlError` 的 trace_id 为零值，由该用例的 FFI/HTTP 适配层在返回前用 `with_trace` 填入，零值不得出现在 FFI/HTTP 输出中。
- V1 只提供简体中文消息；缺失消息键时 CI 失败。
- 本卡不定义业务错误码；各卡在本卡注册表中追加条目，并在各自“接口契约”的错误码表中写明触发条件。
- 外部前提：Python 3 与 PyYAML（Python 版本见 `tools/toolchain.versions`，PyYAML 锁入 `tools/requirements.txt`，ADR-V5-15）。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-02_TEST.md](../Test/S0/S0_CORE-02_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约455行；主包 crates/fml-error/ 165行；附属 tools/ci/gen_errors.py及本卡CI接入230行、app/lib/binding/errors.dart手写异常桥60行；registry/ownership/消息资源与生成物不计。 单阶段可独立构建测试；只计本卡实现及本卡编写的附属接入，不计数据/生成物/自测。

