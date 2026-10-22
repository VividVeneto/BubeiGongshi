### CORE-02 错误码注册表与诊断模型

**目标**：用一份注册表生成 Rust 与 Dart 的错误码和诊断类型，使所有模块的错误可定位、可本地化、可追踪。

**范围**
- 包含：`contracts/errors/registry.yaml` 格式、生成器、`fml-error` crate（`FmlError`、`Diagnostic`、`TraceId`）、Dart 侧 `FmlException` 与消息键。
- 不包含：复现包导出（CORE-28）；各模块具体错误码（各卡在注册表中追加条目）；逐 op 期望错误集合（`manifest.json` 的 `error_codes`，文本真源是 op 所有者卡逐 op 行；本卡只保证被引用的码已登记，见 ADR-V5-55/58 ⑥）；`contracts/dto/types.schema.json` 的 Diagnostic 字段集合（`recovery` 的派生规则属本卡语义校验，不改 schema）。

**依赖**：CORE-01。（阶段2 的 Dart 异常桥另需他卡已生成的诊断数据类型，属产物依赖、不计入本卡的直接依赖，卡级顺序见“接口契约”末段的两阶段说明，ADR-V5-58 ⑤⑧。）

**接口契约**

注册表条目（`registry.yaml` 顶层为 `{ registry_version: <u32>, entries: [...] }`；条目只允许下列 11 个字段，出现未知字段即失败；字段边界与取值来源见 ADR-V5-58 ①④⑤⑥⑦）：

```yaml
- code: TYPE_DIM_CONFLICT      # 大写蛇形，前缀为命名空间
  namespace: TYPE
  owner: CORE-09              # 首次定义卡；唯一所有权来源
  severity: error             # error | warning | info
  message_key: err.type.dim_conflict
  fix_hint: true               # 该码在 errors_zh.arb 中还有 <message_key>.fix 修复建议
  retryable: false
  surface: client              # client | server | both：该码由哪一侧产生，决定能否填 http_status
  since: 1
```

| 字段 | 类型 | 必填 | 取值与校验 |
| --- | --- | --- | --- |
| code | string | 是 | 正则 `^[A-Z]+(_[A-Z0-9]+)+$`；首段等于 namespace；全表唯一 |
| namespace | string | 是 | 下列命名空间之一 |
| owner | string | 是 | 卡号文本；该 code 的首次定义卡，唯一所有权来源。生成器只校验形如 `^(CORE\|AND\|WIN)-\d{2}$`，该卡号是否为现行卡由 DTOcheck REG-01 按 SADD 卡索引判定（生成器不读 SADD，ADR-V5-58 ⑤） |
| severity | enum | 是 | error、warning、info |
| message_key | string | 是 | 固定为 `err.` + code 按首个下划线分为命名空间与余部后分别小写并以点连接（如 `TYPE_DIM_CONFLICT` → `err.type.dim_conflict`）；`errors_zh.arb` 中必须存在，不允许自由改名 |
| fix_hint | bool | 否 | 缺省 false。为 true 表示该码有修复建议消息：`errors_zh.arb` 必须同时存在 `message_key` 与 `message_key + ".fix"`；`Diagnostic.recovery` 只对这类码可用，且必须等于本码 `message_key + ".fix"` |
| retryable | bool | 是 | 调用方原样重试可能成功时为 true |
| since | u32 | 是 | 引入时的 registry_version，`1 ≤ since ≤ registry_version`；registry_version ≥ 1。新增码的 `since` 取写入后的 `registry_version`；条目增加、废弃或任何字段改动都使 `registry_version` 递增（ADR-V5-58 ⑦） |
| deprecated_since | u32 | 否 | `since ≤ deprecated_since ≤ registry_version`；废弃条目保留且仍生成、可解析，不得复用 code |
| surface | string | 是 | `client`、`server`、`both` 之一：该码由端侧产生、由服务端产生、两侧都会产生。生成器为此产出 `is_server_output()`（`server`、`both` 为 true）与 `surface()`（签名 `pub fn surface(&self) -> &'static str`，返回注册表原文 `client`/`server`/`both`，与 `is_server_output()` 同源）；本字段是 `http_status` 能否填写的机器判据，取代“所有者卡约定由服务端输出”这种不可机械校验的说法 |
| http_status | u16 | 否 | 仅 `surface` 为 `server` 或 `both` 的码可填，整数 400–599；服务端未填时映射 400。`surface: client` 的纯端侧码填写即生成失败；此字段不改变 FFI 返回码。本字段以本注册表为唯一来源，所有者卡错误表的 HTTP 列只是生成展示值 |

命名空间：`AST_ CONTENT_ PARSE_ TYPE_ NOTATION_ UNIT_ EVAL_ ENGINE_ DERIVE_ TYPESET_ EXPORT_ STORE_ LIB_ PACK_ STUDY_ GRADE_ CRYPTO_ AUTH_ SYNC_ BACKUP_ PRIVACY_ RECOG_ IMG_ CLOUD_ FFI_ PLATFORM_ NET_ SERVER_`。错误码一经发布不得改义，只能废弃。

```rust
// crates/fml-error/src/lib.rs
// codes.rs 由生成器产出：#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)] pub enum ErrorCode { … }，
// 并生成 as_str()（注册表 code 原文）、domain()（命名空间前缀去下划线小写，如 TYPE_ → "type"）、severity()、retryable()、message_key()、fix_hint()、surface()/is_server_output()、http_status()（均取注册表值；message_key/fix_hint 用于校验 recovery，is_server_output 与 http_status() 同源：`pub fn http_status(self) -> Option<u16>` 对 client 返回 None，对 server/both 返回注册表值、未声明时返还默认 400，供 CORE-22/25 填 HTTP 状态）
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
    pub recovery: Option<String>,        // 修复建议的消息键：仅 code.fix_hint() 时可为 Some，且须等于 message_key() + ".fix"
    pub needs_confirm: bool,             // Warning 需用户确认时为 true
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FmlError {
    // 字段声明顺序即规范 JSON 顺序（code, domain, retryable, trace_id, diagnostics）：
    // derive(Serialize) 按声明顺序输出，与 errors-v1 的 canonical 逐字节比较规则一致（ADR-V5-58 ③）
    pub code: ErrorCode, pub domain: String, pub retryable: bool,
    pub trace_id: TraceId, pub diagnostics: Vec<Diagnostic>,
}
impl FmlError {
    pub fn new(code: ErrorCode) -> Self;                      // domain/retryable 取 code 的生成值，diagnostics 为空，trace_id = TraceId::default()；领域 crate（无 I/O、无随机）只用此构造
    pub fn with_diagnostic(self, d: Diagnostic) -> Self;      // 追加一条诊断
    pub fn with_trace(self, t: TraceId) -> Self;              // 由用例/FFI 层在返回前填入本次调用的 trace_id（仅当仍为零值时覆盖）
}
```

生成的 `ErrorCode` 变体按 code 的下划线分段：每段 ASCII 小写后仅首字母大写并连接（缩写段 AST、JSON 分别转换为 Ast、Json，数字段如 429 保持不变）；首段为字母，结果总是合法 Rust 标识符，生成器检测转换后名称碰撞并拒绝。实现 `FromStr` 与 `TryFrom<&str>`，失败返回公开的 `UnknownErrorCode`（实现 Debug/Display/Error），不得 panic、回退到其他码或丢失未知值错误。`ErrorCode` 的 Display 等于 `as_str()`；`FmlError` 实现 Display（仅 code 与 trace_id，不打印 diagnostics/args）与 `std::error::Error`（source 为 None），`From<ErrorCode>` 等价于 `new`。

serde：`FmlError`、`Diagnostic`、`Severity`（蛇形小写）与 `TraceId`（32 位小写十六进制字符串）按下例 JSON 形式实现 Serialize/Deserialize；`ErrorCode` 序列化为注册表 code 原文，反序列化拒绝未知码。反序列化校验 `domain == code.domain()`、`retryable == code.retryable()`，Diagnostic 的 severity 必须等于自身 `code.severity()`，不随外层错误级别改变。`input_range` 是 UTF-8 半开字节区间 `[start,end)`（u32，start ≤ end）；越界、倒序、未知字段与错误类型均报错，不悄悄修复。`recovery` 存在时必须等于该 code 的 `message_key() + ".fix"` 且 `fix_hint()` 为 true，否则报错，不按自由文本放行。领域内零 trace 可往返；传输边界另行拒绝零值。`retryable`/`domain` 只由注册表按 code 决定，不提供调用点覆盖（无 with_retryable/with_domain），客户端、服务端与 FFI 也不得按调用点改写；需要不同重试语义时登记不同 code。结构体声明顺序即规范字节顺序（`code, domain, retryable, trace_id, diagnostics`），derive 输出与该顺序一致，手写实现必须保持。反序列化用 `deny_unknown_fields` 拒绝 error 对象层未知字段；Diagnostic 内部未声明键 Rust 同样拒绝、Dart 按 CORE-67 生成类规则忽略，故 `errors-v1` 的未知字段负例只写 error 对象层。

Dart：`class FmlException implements Exception { final String code; final List<DiagnosticDto> diagnostics; final String traceId; final bool retryable; FmlException(String code, {List<DiagnosticDto> diagnostics = const [], String? traceId}); factory FmlException.fromJson(Map<String, Object?> json); }`。`DiagnosticDto` 是 CORE-67 生成类 `Diagnostic`（`app/lib/binding/dto/types.g.dart`，ADR-V5-58 ⑧）的别名：本卡在 `app/lib/binding/errors.dart` 写 `typedef DiagnosticDto = Diagnostic;`，本卡不复制诊断序列化类、不改 CORE-67 的类名与未知键规则。两类错误的异常类型分工固定：命名构造器只收调用方传入的 code 与参数，非法参数（未登记 code、traceId 不是 32 位小写十六进制、diagnostics 元素类型不符）抛 `ArgumentError`；`fromJson` 只处理载荷问题（缺字段、类型不符、取值不一致、error 对象层未知字段、诊断 severity 或 recovery 与生成表不符、零值 trace_id）抛 `FormatException`；两者都不显示原始载荷。命名构造器供客户端本地错误（如各卡写的 `FmlException('SYNC_NOT_AVAILABLE')`）：code 必须在 `error_codes.g.dart` 中已登记，retryable 只取生成表，traceId 省略时以 Random.secure 生成非零 32 位小写十六进制，不提供覆盖 retryable/domain 的参数。工厂读取根信封 `{error:{...}}`（CORE-03 先剥除 v/外层 trace_id 等信封元数据后把整个 `{error:{…}}` 交给本工厂；信封本身不属本卡），校验必填字段、已知 code、domain/retryable 与生成表相符、诊断 severity、区间与非零 32 位小写十六进制 trace_id。error 对象层拒绝未知字段/类型或不一致值；`Diagnostic` 内部未声明键由 CORE-67 生成类的 fromJson 规则忽略（信封向前兼容，见该卡），本卡不额外收紧，故 `errors-v1` 的未知字段负例只针对 error 对象层。诊断的 `recovery` 按同一派生规则与 `fix_hint` 校验（阶段2，随 CORE-67 生成的 `Diagnostic` 生效）。消息在 `app/lib/l10n/errors_zh.arb`；初次由本卡为全部基线已登记码建立简中消息，业务所有者审核文字，后续新增由所有者随登记片段提供。

`FmlError` 的 JSON 形式（FFI 返回码 1 的 `out` 与服务端错误响应体共用，字段名固定）：

```json
{ "error": { "code": "TYPE_DIM_CONFLICT", "domain": "type", "retryable": false,
    "trace_id": "0f8e…（32 位小写十六进制）",
    "diagnostics": [ { "code": "TYPE_DIM_CONFLICT", "severity": "error", "node_path": "0.2.1",
        "input_range": [4, 9], "args": { "left": "L", "right": "L T^-1" },
        "recovery": "err.type.dim_conflict.fix", "needs_confirm": false } ] } }
```

`diagnostics` 可为空数组；`node_path`、`input_range`、`recovery` 缺省表示无。`TraceId` 文本形式为 32 位小写十六进制。

生成命令：`tools/ci/gen_errors.py` 唯一读取 `contracts/errors/registry.yaml` 的错误元数据，输出 `crates/fml-error/src/codes.rs`、`app/lib/binding/error_codes.g.dart`、`contracts/errors/README.md`（含 owner/severity/retryable/surface/http_status/fix_hint 的完整错误码表）、`contracts/errors/ownership.yaml`，并更新 `contracts/policies/shared-writes.json` 的 error 投影（保留其他类别不变）；顺序按 code 排序，结果确定。`--check` 只比较不写文件，退出码与 CORE-67 的 `gen_dto.py` 一致：0 无漂移、1 任一生成物漂移、2 输入或环境错误（registry 或 arb 不可解析、缺 PyYAML），供 CI 聚合入口使用。生成器不从镜像或 SADD 反推 registry；`owner` 只校验卡号格式 `^(CORE|AND|WIN)-\d{2}$`，该卡是否为现行卡由 DTOcheck REG-01 判定（生成器不读 SADD，ADR-V5-58 ⑤）。生成器同时校验结构约束：`surface` 必填且取值合法，`surface: client` 的条目填 `http_status` 即失败，`1 ≤ since ≤ registry_version`、`since ≤ deprecated_since`；并校验消息资源：每条 `message_key` 必须在 `errors_zh.arb` 存在，`fix_hint: true` 的条目还须存在 `message_key + ".fix"`，任何 `*.fix` 键的基键必须是已登记码（孤儿键失败），消息键不得手改。

交付分两个阶段（ADR-V5-58 ⑤⑧）。阶段1 为本卡 Rust 核心、生成器与消息资源，可独立构建与测试（此时只能判“阶段1 就绪”）。阶段2 为 Dart 异常桥 `app/lib/binding/errors.dart`（含 `typedef DiagnosticDto = Diagnostic;`），须在 CORE-67 已生成 `Diagnostic` 之后、CORE-03 开工之前完成，单独提交、单独复核；阶段2 未完成时不得宣称整卡通过，也不得用手写替身代替生成类。阶段2 的前置是 CORE-67 阶段1 的**产物**而非整卡，卡级顺序为 CORE-01 → 本卡阶段1 → CORE-67（生成 `Diagnostic`，其错误码只消费本卡阶段1 产物）与 CORE-100（manifest 引用本卡登记的码）→ 本卡阶段2 → CORE-03（读 FFI 错误信封），不存在 02↔67 卡级环。若后续 schema 变更使生成类名不再是 `Diagnostic`，本卡按 README §8.4 提契约变更单改别名一行，不改 CORE-67 的 title 或类名，也不复刻生成类。

黄金样例由本卡建立 `contracts/vectors/errors-v1.json`，Rust 与 Dart 共同消费；本卡是唯一所有者，CORE-03（FFI 返回码 1 的 `out`）、CORE-22/25（HTTP 错误响应体）与 CORE-40 只按本格式读取，不另建第二份：

- 顶层 `{ "schema": 1, "version": 1, "error_version": 1, "cases": [...] }`；`version` 是 `contracts/vectors/` 全部向量的通用格式版本（DTOcheck DTO-20），本文件与 `schema` 同步为 1，语义不同于 `error_version`；`error_version` 描述 `{error:{...}}` 中 error 对象的形状，字段集合或语义变化时递增，当前为 1；`registry_version` 变化（增删码、改条目字段）不递增 `error_version`（ADR-V5-58 ⑦）。CORE-03 读 FFI 错误信封时把 `error_version` 与自身支持下限比较，CORE-22/25 在 HTTP 错误响应体填本值。
- 正例 `{ "id": "ERR-01", "input": { "error": {…} }, "canonical": "…" }`：`input` 一律是**根信封** `{error:{…}}`（与 CORE-03 FFI `out`、服务端错误响应体同形，ADR-V5-58 ③），Rust 侧取 `input["error"]` 反序列化 `FmlError`，Dart 侧把整个 `input` 交给 `FmlException.fromJson`；`canonical` 是 error 对象规范序列化的期望文本，字段顺序与外层/Diagnostic 内顺序、`args` 排序及缺省可选字段的省略规则一律按 ADR-V5-58 ③，不得另定。Rust 序列化结果逐字节等于 `canonical`，Dart 逐字段相等。
- 负例 `{ "id": "ERR-NEG-01", "input": {…}, "valid": false, "why": "unknown_field" }`：`why` 取 ADR-V5-58 ③ 的 9 个取值之一（`unknown_field`/`wrong_type`/`range`/`trace_format`/`domain_mismatch`/`retryable_mismatch`/`severity_mismatch`/`recovery_invalid`/`envelope_invalid`），两端必须拒绝且不 panic。`unknown_field` 只写 error 对象层；`envelope_invalid` 用于 `input` 缺 `error` 键或 `error` 非对象（Rust 取 `input["error"]` 失败、Dart 工厂直接拒绝）。
- `id` 发布后不得改名或复用，删除用例只留空号（不重排、不回填）；正例至少 8 类（真实 32 位 trace、多诊断、空诊断、省略可选字段、`args` 乱序、`fix_hint: true` 且输出派生 `recovery`、`fix_hint: false` 时不输出 `recovery`、severity 为 warning/info 各一条），负例至少 9 条并覆盖 `why` 全部取值，随阶段1 建立。
- 不以 CORE-03 或服务端尚未实现为本卡单元测试的隐性前提；Dart 侧消费在阶段2 就绪后执行（见测试方案）。

跨卡共享格式清单（索引只指向所有者，不在本卡复制定义；实现卡建立相应 contracts/vectors 文件）：

| 格式 | 唯一定义卡 | 版本 | 向量位置 |
| --- | --- | --- | --- |
| AST 规范 JSON、BLAKE3 | CORE-05 | ast_schema=1 | contracts/vectors/ast-canonical.yaml |
| UUIDv5 命名空间与拼接、seed | CORE-05 | id-v1 | contracts/vectors/ids-v1.json |
| WrapRecord、wrap_kind 与 AAD CBOR | CORE-21 | wrap=1、aad=1 | contracts/vectors/wrap-v1.json |
| Envelope | CORE-68 | envelope_version=2 | contracts/vectors/envelope-v2.json |
| 错误信封的 `error_version` 与错误向量 | CORE-02 | error_version=1 | contracts/vectors/errors-v1.json（CORE-03 读信封时比较本下限；CORE-22/25 填本值；只读消费） |
| merge_choice ID | CORE-05 | id-v1 | contracts/vectors/ids-v1.json |
| RecognitionMode 的 Rust/HTTP 取值 | CORE-29 | recognition_mode=1 | contracts/vectors/recognition-mode.json（CORE-29 创建与维护，CORE-33 镜像只读消费） |
| `.fmlbackup` 备份容器（头、块、清单、末块） | CORE-27 | format_version=1 | crates/fml-store/tests/vectors/backup_v1.hex（BK-V1；CORE-84 恢复只读消费） |
| 引擎数据 JSON（units/kinds/profiles/constants/fonts/manifest）与层叠加规则 | CORE-56 | schema=1 | contracts/vectors/engine-data-v1/ |

错误码只在首个所有者卡的标准表中登记；消费者写“复用 + 处理”，不得复制 severity/retryable。新增代码先登记 contracts/errors/registry.yaml，生成器拒绝重复 code。

错误码共享写入：registry.yaml 是 code/owner/namespace/severity/retryable/surface/message_key/fix_hint/版本/http_status 的唯一真源；`condition`（触发条件）只在业务卡提交片段与各所有者卡错误表，不写入 registry、也不由 registry 生成，避免两处维护。`ownership.yaml`（version=1，entries:[{code,owner}]）只是生成镜像，不接受独立手改；通用前缀可共享，不能以整段 AUTH_/PLATFORM_ 强行归某张业务卡。业务卡新增前提交 `{code,owner,severity,retryable,surface,condition,http_status?,fix_hint?}` 独立片段及简中消息（`fix_hint: true` 时同时给 `<message_key>.fix`），由 CORE-02 维护者合入 registry 后生成；遇到已占用 code 只引用所有者或先走契约变更单。初次创建 registry 必须收齐全部 SADD 标准错误表，判据是“SADD 里有多少条定义，registry 就有多少条”，不是人工列的定数：按当前 SADD 为 47 张卡、238 条定义，该数只是快照，随各卡追加增长，不得写进生成物或测试断言。所有者卡错误表的“级别/可重试/HTTP”列是生成展示值：由首次定义卡维护，取值必须等于 registry（HTTP 列只对服务端输出的码声明，缺省即 400 语义，纯端侧码不得声明），不一致时改 registry 再重新生成。registry 未创建阶段，shared-writes.error 仅含 code/owner，DTOcheck 只比对 SADD 与预分配表的 code/owner（缺项、重复、所有者不符及消费者重定义失败），不声称已检查 severity/retryable/http_status。机械对照规则 REG-01（工具项，按 README §7.1 以 chore(sadd) 提交）：registry 存在时 DTOcheck 做三项判定——(1) 每条 `owner` 必须是 SADD 现存卡号（卡已撤销或不存在即失败；owner 有效性的唯一检查点，生成器只查格式）；(2) 所有者卡表逐列与 registry 一致（owner/severity/retryable/http_status），不一致即失败；(3) 双向全集：registry 每条码都能在某卡标准表找到定义，SADD 每条定义都在 registry，缺失或多余都失败。registry 不存在时输出“未执行”，不按通过计。REG-01 尚未实现（registry 与生成器均未创建），是本卡交付后的验收项（附录 D CO-40）；交付后另须补齐生成镜像漂移检查，未交付时这些检查明确未执行。registry 不承载逐 op 期望错误集合：哪个 op 返回哪些码写在 `contracts/dto/manifest.json` 的 `error_codes`（结构校验归 CORE-100，引用有效性归 DTO-06/DTO-18），本卡只保证被引用的码已登记且元数据一致（ADR-V5-58 ⑥）；逐 op 集合的文本真源是各 op 所有者卡的逐 op 错误镜像，双向比对归 DTO-06（ADR-V5-55，CO-56 修订）。DTO-06 回向检查（op 所有者卡逐 op 错误行 ↔ `manifest.json` 的 `error_codes` 双向）同属本卡工具项交付（落在 `tools/DTOcheck/`）：按 README §7.1 以 chore(sadd) 提交、不计本卡规模（“规模”行口径不变），与 REG-01 同批落地；交付前该组断言输出“未执行”，不按通过计。

PR3 预分配机器表 `contracts/policies/shared-writes.json` 的 error 项在 registry 未创建前为登记占位，由本卡单写，key 为完整错误码、owner 为首次定义卡；前缀不是所有权。建立 registry 时逐码核对并迁入 registry.owner，之后 shared-writes 的 error 项与 ownership 同为 registry 生成投影，不再独立维护；非 error 项不在本卡生成范围。后续新增必须先申请唯一 code。

**实现约束**
- UI 显示本地化消息；日志只记 `code`、`trace_id`、模块与版本、耗时与预算，不记公式正文、图片、路径、令牌、密钥或恢复码。
- 每次用例调用由 FFI/HTTP 适配层生成或验证非零 `trace_id`，领域 crate 无随机/I/O，`new` 的 trace_id 为零。边界返回前一律调用 `with_trace`；原值非零必须保留，不另造第二条错误链，零值不得出现在 FFI/HTTP 输出中。CORE-03 负责请求/完成回调，CORE-22/25 负责 HTTP 错误适配；FFI 外层 trace_id、HTTP request_id/日志关联值均取填充后的 `error.trace_id`，不是盲用新请求 ID。
- V1 只提供简体中文消息；缺失消息键时 CI 失败。
- 本卡不定义业务错误码；各卡在本卡注册表中追加条目，并在各自“接口契约”的错误码表中写明触发条件。
- 本卡不定义逐 op 期望错误集合，也不生成第二份逐 op 表（ADR-V5-58 ⑥）：op→码 的引用在 `contracts/dto/manifest.json`，结构校验归 CORE-100，引用有效性归 DTO-06/DTO-18（对照源为 op 所有者卡行，ADR-V5-55）。
- `registry_version` 与 `error_version` 互不替代：条目增加、废弃或字段改动只递增 `registry_version`；只有 error 对象形状变化才递增 `error_version`（ADR-V5-58 ⑦）。
- 外部前提：Python 3 与 PyYAML（Python 版本见 `tools/toolchain.versions`，PyYAML 锁入 `tools/requirements.txt`，ADR-V5-15）。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-02_TEST.md](../Test/S0/S0_CORE-02_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约1030行，分阶段（两阶段；阶段1 实测超 ADR-V5-52 约800行停下线，工程样品阶段按附录D D.14.8 RL-08 不拆卡，发布前收回）；主包 crates/fml-error/ 实测 320行（原估 175）；附属 tools/ci/gen_errors.py 含本卡CI接入实测 642行（原估 245，238 条码 × 5 种生成物及校验分支）、app/lib/binding/errors.dart 手写异常桥 70行；registry/ownership/消息资源/errors-v1 向量与生成物不计。阶段1 实测 962行，按两段登记复核：1a 错误模型 lib.rs 320、1b 生成器与CI接入 642（另加 registry/arb/errors-v1 数据文件），阶段2 约70行（errors.dart 手写异常桥与 `DiagnosticDto` 别名，前置与卡级顺序见“接口契约”末段的两阶段说明）；每阶段独立构建、独立测试、单独提交与复核。

