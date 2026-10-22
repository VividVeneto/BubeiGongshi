### CORE-03 C ABI 与 Dart 绑定

**目标**：提供唯一的跨语言边界——稳定 C ABI（`fmlcore` 动态库）和由头文件生成的 dart:ffi 绑定，全部核心能力以“op + DTO”形式调用。

**范围**
- 包含：`fml-ffi` crate、`contracts/include/fmlcore.h`、DTO 序列化、同步快速调用与长任务提交/取消/完成回调、句柄与缓冲区管理、panic 隔离、Dart `CoreBinding`。
- 不包含：业务 op 的实现（各功能卡在 `crates/fml-ffi/src/ops/<域>.rs` 中登记）；鸿蒙 NAPI 封装（CORE-44 只验证头文件可被 C 消费）。

**依赖**：CORE-01、CORE-02、CORE-67

**接口契约**

```c
/* contracts/include/fmlcore.h —— 唯一导出面 */
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
#define FML_ABI_MAJOR 1
#define FML_ABI_MINOR 0
typedef struct { uint8_t *ptr; size_t len; uint64_t allocation_id; } FmlBuf;   /* 核心分配；只能用 fml_free_buffer 释放一次 */
typedef uint64_t FmlHandle;                           /* 高 16 位为代数（generation），拒绝过期句柄 */
typedef void (*FmlCompletion)(uint64_t job_id, FmlBuf result, void *user_data);

uint32_t fml_abi_version(void);                       /* (MAJOR<<16)|MINOR */
FmlBuf   fml_capabilities(void);                      /* JSON：op 列表、DTO 版本、构建信息 */
int32_t  fml_call(const char *op, const uint8_t *req, size_t req_len, FmlBuf *out);  /* 同步快速路径 */
int32_t  fml_submit(const char *op, const uint8_t *req, size_t req_len, uint64_t *job_id);
int32_t  fml_cancel(uint64_t job_id);                 /* 返回0后保证该任务资源已释放（已发出回调的缓冲区仍由接收方释放） */
int32_t  fml_register_completion(FmlCompletion cb, void *user_data);
int32_t  fml_free_buffer(FmlBuf buf);   /* 0 成功，-1 非本分配/已释放；用 allocation_id 防 ABA */
int32_t  fml_close_handle(FmlHandle h);                  /* 0=已受理关闭（进入 closing 后立即返回，不等待排空）；-4=句柄未知/代数不符/已退役；-6=已在 closing 或仍有不可取消活跃 job（定义见下表 FFI_BUSY 行） */
#ifdef __cplusplus
}
#endif
```

- 返回码：`0` 成功（`out` 为下述成功信封）；`1` 业务错误（`out` 为下述错误信封）；负数为 FFI 层错误，此时 `out` 尽量写入同样错误信封（分配失败时 `ptr` 为 NULL、`len` 为 0）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `FFI_BAD_ARG` | error | 否 | 返回 -1：空指针、req_len 超过 16 MiB、非合法 UTF-8 JSON、缺 v/body/trace_id 或 trace_id 格式错误/全零、重复释放缓冲区、未注册回调就 submit |
| `FFI_UNKNOWN_OP` | error | 否 | 返回 -2：op 未登记，或该 op 不支持当前调用方式（同步 op 走 submit，反之亦然） |
| `FFI_VERSION_MISMATCH` | error | 否 | 返回 -3：DTO 主版本 v 不是该 op 支持的主版本 |
| `FFI_STALE_HANDLE` | error | 否 | 返回 -4：句柄代数不符或已关闭；未知 job_id |
| `FFI_PANIC` | error | 否 | 返回 -5：op 内部 panic 被 catch_unwind 捕获 |
| `FFI_BUSY` | error | 是 | 返回 -6：排队 + 运行 ≥ 64（并发上限常量 `MAX_INFLIGHT_JOBS`）；或仍有活跃 job/未释放回调缓冲时注册、替换或 NULL 注销回调；或 `fml_close_handle` 时句柄已在 closing、或仍有不可取消活跃 job（见下条定义） |

- **不可取消活跃 job**（上表 `FFI_BUSY` 的 close 场景）：已完成或已发出完成回调的 job，以及已越过取消检查点、即将发出回调而 `fml_cancel` 再也无法收回的 job。仍在队列中或运行中但未越过取消检查点的 job 属可取消：只有这类在途 job 的活跃句柄，`fml_close_handle` 返回 0，并在排空阶段为其置位取消、丢弃其结果。

- `fml_cancel`：返回 `0` 表示已取消且不会再回调；返回 `1` 表示任务已完成或回调已发出（取消无效）；未知 `job_id` 返回 `-4`。
- `fml_register_completion`：进程内只保存一个回调，只有无活跃job及未释放回调缓冲时允许替换；否则返回-6。cb=NULL注销也遵守此规则；回调在核心工作线程上执行，`result` 的所有权交给回调方，用完须 `fml_free_buffer`。长任务工作线程数为 `min(4, CPU 核数)`。
- `budget_ms`：只对声明支持预算的 op 生效，超时由该 op 返回本域错误码（如 `EVAL_TIMEOUT`）；其他 op 忽略此字段且不报错。声明集合的唯一来源是本卡 `crates/fml-ffi` 内的常量表 `BUDGET_OPS`（初始 `engine.parse`、`calc.evaluate`、`grade.answer`）；`fml_capabilities` 的 `ops[].budget` 由同一张表生成，不得另写第二份清单或散落到各 op 卡。新增支持预算的 op 先按 README §8.4 提交契约变更单，由本卡所有者修订该表。集合成员与 `fml_capabilities` 投影同源已在上文限定；成员的默认值与取值范围不归本卡，`fml_capabilities` 也不复制这些值：`engine.parse` 的默认 100 ms、范围 1～1000 见 CORE-06，`calc.evaluate` 默认 200 ms 见 CORE-10，`grade.answer` 默认 50 ms 见 CORE-18，验收按各 op 所有者卡与 DTO manifest 断言。
- DTO 映射规则（各卡 FFI op 未另行列出字段时适用）：请求 `body` 与响应 DTO 是对应 Rust 结构体的 serde JSON——字段名与结构体字段同名（snake_case）；无数据的枚举值为 snake_case 字符串，带数据的变体为 `{"<变体名>": 数据}`；`Option` 为 `None` 时省略字段；`FormulaNode` 一律用 CORE-05 规范 JSON；UUID 类 ID 为小写带连字符字符串，`SymbolId` 为整数；十进制数值（值、不确定度、区间端点）一律为字符串；时间为 `*_ms` 整数（Unix 毫秒）；二进制为 base64 字符串。请求缺必填字段或类型不符时返回 `FFI_BAD_ARG`。
- `fml_capabilities` 示例：`{"abi":"1.0","ops":[{"op":"engine.parse","dto":1,"mode":"call","budget":true},{"op":"image.decode","dto":1,"mode":"submit","budget":false}],"build":{"app":"1.0.0","git":"<sha>","target":"aarch64-linux-android","test_build":false}}`。`budget` 与 `BUDGET_OPS` 同源，`build.test_build` 在测试专用构建中为 `true`、正常与发布构建为 `false`。`abi` 字段是十进制 `"MAJOR.MINOR"` 字符串（示例中的 `"1.0"`），与 `fml_abi_version()` 的返回同源生成；Dart 侧只用 `abiVersion() >> 16` 与 `FML_ABI_MAJOR` 比较主版本、不解析该字符串，两处不一致按构建缺陷处理（比较与不可用页的分工见下文 Dart 绑定说明）。
- ABI 兼容规则：`FML_ABI_MAJOR` 不同即拒绝启动，Dart 侧与 `runPlatformApp` 都只比较 MAJOR。同一 MAJOR 内只允许新增 op、新增错误码与新增 `fml_capabilities` 字段，调用方忽略未知 op 与未知 capabilities 字段；请求/响应 DTO 的字段集变化走 DTO 主版本 `v`，不在 MINOR 内静默改变。绑定 MINOR 低于核心时只使用 `fml_capabilities` 声明存在的能力，不按编译期常量假设。
- DTO：UTF-8 JSON，顶层 `{"v": <dto_major>, "trace_id": "...", "budget_ms": <u32 可选>, "profile_handle": <十进制u64字符串，可选>, "expected_generation": <十进制u64字符串，可选>, "body": {...}}`；schema 在 `contracts/dto/<op>.schema.json`；未知主版本拒绝。
- op 命名 `<域>.<动作>`，如 `engine.parse`、`engine.check`、`typeset.layout`、`calc.evaluate`。每张功能卡在“接口契约”中列出它登记的 op。
- 长任务（图片解码、本地推理、导出、迁移）走 `fml_submit`，由核心通过 `FmlCompletion` 通知；不提供轮询接口。回调线程不得持锁，不得重入 UI。

**op 注册与派发（Rust 内部面；`extern "C"` 只出现在 `crates/fml-ffi/src/abi.rs`，注册面与派发面都是普通 Rust 公共项）**

各功能卡在自己的 `crates/fml-ffi/src/ops/<域>.rs` 里声明静态条目，本卡只提供下面的类型、运行时与一张空表。处理器类型是 `OpHandler`，派发上下文是只读的 `OpCtx`；取消面用本卡自己的 `CancelHandle`（`fml-ast` 的 `CancelFlag` 归 CORE-05，不在本卡依赖闭包内，由各 op 处理器自行适配，本卡不依赖它）。

```rust
// crates/fml-ffi/src/ops/mod.rs —— CORE-03 定义；各卡只在自己的 ops/<域>.rs 追加条目
pub enum OpMode { Sync, Submit }
pub enum Scope { None, Device, Profile }
pub enum OpReply { Ok(Vec<u8>), Err(FmlError) }
pub enum CloseTrigger { NativeClose, StoreClose }
pub enum CloseReply { Accepted, Busy, Stale }

// 取消面：由本卡 job 表持有；cancel() 置位，is_cancelled() 供处理器检查
pub struct CancelHandle(/* job 表持有的原子取消标志 */);
// 句柄面：slot + 代数 + 租约计数 + closing 标志；lease()/is_closing()/begin_close()/retire()
pub struct HandleActor(/* 句柄表条目 */);

pub struct OpCtx<'a> {
    pub op: &'static str,
    pub dto: u32,
    pub mode: OpMode,
    pub scope: Scope,
    pub handle: Option<FmlHandle>,
    pub actor: &'a HandleActor,
    pub cancel: &'a CancelHandle,
    pub trace_id: TraceId,
    pub budget_ms: Option<u32>,
}

pub trait OpHandler: Send + Sync { fn call(&self, ctx: &OpCtx<'_>, body: &[u8]) -> OpReply; }

pub struct OpEntry { pub op: &'static str, pub mode: OpMode, pub scope: Scope, pub handler: &'static dyn OpHandler }

// 启动期静态登记表：各卡在自己的 ops/<域>.rs 里 pub const ENTRIES: &[OpEntry]，本卡汇总；阶段①只有 Fake op。
pub static OPS: &[OpEntry] = &[];
```

- 注册入口是静态表 `OPS`：没有运行时可变注册表，启动不扫描目录、不加锁；阶段①用 Fake op 走通派发。这里不提供 `register_op` 一类运行时 API（理由与否决见 ADR-V5-61）。
- 谁在何时注册：每个 op 的所有者卡在自己的 `crates/fml-ffi/src/ops/<域>.rs` 写条目，由本卡的汇总代码在编译期并入 `OPS`；注册发生在构建期，运行期不可能新增或改写 op。
- 重复注册同一 op 名是硬错误：`OPS` 自检（`ops::tests::op_names_unique`）、debug 构建的启动断言与 `crates/fml-ffi/tests/abi.rs` 三层都要求 op 名唯一，且 `mode`/`scope` 与该 op 的 manifest 条目一致；覆盖式注册一律视为缺陷，不做“后者胜”。
- 派发流程固定为：解析入参 → 校验信封、`mode` 与 `scope` → 在 `OPS` 查 op（未知 op 或入口与 `mode` 不符返回 `FFI_UNKNOWN_OP`）→ `actor.lease()` 取租约（句柄未知/代数不符/已退役/已在 closing 返回 `FFI_STALE_HANDLE`）→ DTO 主版本不符 `FFI_VERSION_MISMATCH`、必填字段缺失 `FFI_BAD_ARG`、profile op 缺 `profile_handle` 由档案路由返回 CORE-23 的 `AUTH_NO_PROFILE` → `catch_unwind` 调 `handler.call`（panic 转 `FFI_PANIC`）→ 序列化 `OpReply` 并写错误信封。
- 关闭编排只有一个调用入口 `HandleActor::begin_close(CloseTrigger)`：`fml_close_handle` 传 `NativeClose`，`store.close`/`account.close_profile` 的处理器传 `StoreClose`，两者都只调它，并按 `Accepted`/`Busy`/`Stale` 对应 C ABI 的 0/-6/-4（映射见下文关闭编排映射表）；`store.close` 在 `Accepted` 之后由该处理器驱动 Store 排空与密钥清零，最后 `retire()` 退役 slot，不自行改写 closing 状态、不复用旧代数。

Dart 包装（`app/lib/binding/core_binding.dart`）：

```dart
abstract interface class CoreBinding {
  /// 打开动态库并校验 ABI；可在多个 isolate 中各自打开，共享同一核心状态。
  static CoreBinding open(CoreLibrarySpec spec) => FfiCoreBinding(spec);
  Future<void> dispose();           // 仅关闭本绑定；listener所有者按下文取消/排空；不卸载共享动态库
  CoreBinding scopedTo(String profileHandle); // 不可变视图；call/submit注入信封profile_handle，dispose不关闭主listener
  CoreLibrarySpec get spec;          // 可跨 isolate 发送
  int abiVersion();
  Stream<String> get engineGenerations; // 本绑定收到的快照代数，十进制u64；不代表所有外部更新
  Map<String, Object?> call(String op, Map<String, Object?> body, {Duration? budget, String? expectedGeneration});
  Future<Map<String, Object?>> submit(String op, Map<String, Object?> body, {CancelToken? cancel, String? expectedGeneration});
}
final class CoreLibrarySpec {      // Android 为 'libfmlcore.so'；Windows 为 fmlcore.dll 的绝对路径
  const CoreLibrarySpec(this.path);
  final String path;
}
final class CancelToken {            // 由调用方创建；cancel() 后 submit 的 Future 以 FfiCancelled 结束
  void cancel();
  bool get isCancelled;
}
final class FfiException implements Exception {
  final int status;                  // 负返回码
  final String? code;                // 如 'FFI_BUSY'；未登记负值时为 null，不发明新码
  final String? traceId;
}
final class FfiCancelled implements Exception {}
// 业务错误先提取 {error: envelope.error} 交 CORE-02 FmlException.fromJson；FFI 层错误抛 FfiException。
// FfiException.status → code 的唯一反查表就是上表六码（-1…-6）；未登记负值的 code 为 null，只报 status，禁止临时造码。
// CoreBinding.open 失败（库缺失/无法加载）原样上抛底层加载异常，不包装成 FfiException；具体异常类型与“核心加载失败/版本不匹配”两分支的展示由 CORE-04 的平台入口固定（下游说明，非契约）。
// 打开成功后由调用方比较 abiVersion() >> 16 与 FML_ABI_MAJOR；不一致不抛异常，由平台入口显示核心不可用页并提示重装。
```

动态库名：Android `libfmlcore.so`，Windows `fmlcore.dll`；加载方式由 AND-01、WIN-01 规定。

**跨语言信封、回调与资源**
- 请求示例：`{"v":1,"trace_id":"00000000000000000000000000000001","body":{}}`。成功示例：`{"v":1,"trace_id":"00000000000000000000000000000001","ok":{"profiles":[]},"diagnostics":[]}`。业务错误/负返回码示例：`{"v":1,"trace_id":"00000000000000000000000000000001","error":{"code":"FFI_BAD_ARG","domain":"ffi","retryable":false,"trace_id":"00000000000000000000000000000001","diagnostics":[]}}`。ok/error 必有且仅有一个；error 内部形状归 CORE-02；完成回调传相同信封，负状态由 error.code 判别；call/submit 的 Dart 包装只向业务返回 ok。
- Trace 边界：call/submit 的请求 trace_id 必须是非零 32 位小写十六进制；Dart 包装在每次调用前生成，scopedTo 不另生成第二个 ID，C 调用方自行提供。Rust 在校验失败而尚不能取到合法请求 trace 时生成非零备用 ID（仅边界允许随机源），可写错误信封使用该 ID；无 out 参数的 ABI 函数仍只返回状态，不新增 ABI。领域错误、FFI 错误及捕获的 panic 在序列化前统一 `with_trace(request_trace)`；已非零错误 trace 保留，响应外层 trace_id 必须等于最终 error.trace_id。异步 job 在提交时捕获 trace，完成/失败回调沿用，不读工作线程“当前调用”。成功响应沿用请求 trace。负状态且无缓冲区时 Dart FfiException.traceId 可空；有信封时必须验证非零且内外一致，否则拒绝为格式损坏，不伪装业务错误。
- Dart ≥3.1 使用 `NativeCallable.listener`，不使用 Pointer.fromFunction。C 工作线程调用后返回；Dart isolate 收到后在 try/finally 中复制、解析结果并 fml_free_buffer；取消竞态收到的迟到结果也必须释放。绑定为进程主 isolate 保存唯一 listener，活跃 job 与已投递结果未清零前不得 close listener/卸载 DLL；dispose先拒绝新call/submit、对绑定活跃job调用cancel，等待已投递通知经finally释放；用fml_register_completion(NULL,NULL)确认无活跃job/回调buf后才close listener，Busy则继续事件循环等待，不能同步阻塞isolate。结果分配至Dart释放的全过程计入未释放回调缓冲计数；无listener的其他isolate绑定dispose不注销全局listener。动态库保持进程寿命，不假设Dart有可安全卸载API。
- `store.open` 是 FmlHandle 的产生者，JSON 用十进制字符串表示 u64；generation 高16位、slot低48位，耗尽后 slot 不复用。close/integrity 等携 handle 查表，拒绝过期值；close 等待在途读写后销毁。缓冲区在注册表按 allocation_id 核对 ptr/len，未知值不解引用，重复释放返回-1；id 进程内单调且不复用。
- db_key_b64、恢复码、口令、令牌均为敏感字段，schema 标记 writeOnly/x-sensitive；禁止请求/响应全量日志、快照与异常插值。FFI只读const请求并在返回前复制需要保留的字节，绝不写入调用者内存；核心拥有的敏感副本使用Zeroizing。Dart自己分配的临时Uint8List在native调用返回（submit已同步复制）后的finally填零；其他C调用者负责自己可写缓冲区清理。JSON/String的不可控副本不能承诺可靠擦除，产品安全边界明确为“不持久化、不记录”，不是“明文从不进Dart堆”。
- 每个 op 在所有者卡维护字段表与成功例，`contracts/dto/<op>.schema.json` 的 `$defs` 必含 request/ok，公共类型经 `$ref` 到所属卡 schema；manifest 记录 owner/mode/error_codes/sensitive_paths。未知字段 additionalProperties=false；未知枚举/缺必填/非有限数拒绝，None省略，数值精度规则按上述映射。全量清单与生成门禁见 CORE-67。

ABI不匹配测试专用Cargo feature abi_major_bump仅让fml_abi_version返回MAJOR+1，不修改公共头或生成的Dart常量；与正常产物用不同target-dir，测试安装脚本替换仅核心库。发布拒绝由本卡自己的构建期门禁承担：`crates/fml-ffi/src/lib.rs` 在 `#[cfg(all(feature = "abi_major_bump", not(debug_assertions)))]` 下 `compile_error!`，使带该 feature 的 release（非 debug）产物直接编译失败，因此发布二进制不可能出现 `capabilities.build.test_build=true`。该拒绝步骤不转给 CORE-41（其 manifest 不含此步，理由与后果见 CO-59）；AND-01/WIN-01 复用此机制，测试构建走 debug 或独立 target-dir。

档案路由（ADR-V5-39）：manifest 的 scope 必为 none/device/profile，未知或缺失 scope 拒绝注册。profile op 必须携信封 profile_handle；缺失返回 AUTH_NO_PROFILE，未知/已关闭/closing 句柄返回 FFI_STALE_HANDLE。绑定在派发前取得该 handle 的 Store 租约，绝不从“当前账户”单例取库。若 body 另含 profile_id，须与句柄登记身份相等，否则 FFI_BAD_ARG；store.close/integrity_check 的 body.handle 与信封同时出现时也须相同。none/device op 禁带 profile_handle，避免调用方误以为受到档案隔离。升级合库的 target_handle 是 CORE-24 明列的第二句柄，不靠全局切库。

scopedTo 只产生绑定视图，不拥有 Store；CORE-65 是交互档案句柄的唯一关闭者。调用者不能在已scoped视图上改绑其他handle；worker由主绑定传入同一handle后scopedTo，任务创建时捕获句柄，切换后不重定向到新库。fml_close_handle 与 store.close 共用同一个关闭过程：先标 closing 并拒绝新租约，取消/排空该句柄的job，等租约归零，关闭Store及其Zeroizing密钥，再退役slot。取消失败的已投递结果仍释放；关闭失败维持closing并报告STORE错误，禁止将旧handle复活。关闭是submit，不能在Dart UI线程同步等待。Dart 侧不直接暴露 fml_close_handle：关闭的唯一 Dart 入口是 store.close/account.close_profile 的 submit，完成观测走该 submit 的回调/Future；fml_close_handle 只供 C 调用方与核心内部关闭路径使用。

expected_generation 只用于引擎快照消费op（CORE-56五op及CORE-11三个derive op；CORE-52导出处理器同样遵守）；为非负u64十进制字符串，未给时取当前快照，给出时必须与所取快照一致，不一致返回 ENGINE_UNAVAILABLE且不执行算法。成功和业务错误信封可含 engine_generation（同格式），由本次所持快照填写，不能读取完成时的全局值。CoreBinding新增只读 Stream<String> get engineGenerations；解析信封时先投递generation再向业务返回ok，未知字段不得混入业务DTO。无快照的op不带该字段；通知契约的所有者见CORE-73（下游说明，非契约）。

关闭控制操作store.close/account.close_profile/fml_close_handle只解析并校验句柄身份，不取得会阻止自己完成的普通Store租约；控制任务不计入待排空的本句柄业务job集合。关闭开始即原子撤销新租约，既有租约的释放路径不再请求关闭锁。scoped视图只允许profile op；device/none操作显式用root绑定。关闭后的再次关闭由ProfileSession复用同一Future，原生旧句柄仍返回FFI_STALE_HANDLE。

**关闭编排映射（`fml_close_handle`、`store.close`、`account.close_profile` 共用同一关闭过程；op 错误码的唯一定义仍归各自所有者卡，本卡只规定 C ABI 返回码与六个 FFI 码）**

| 触发时机 | `fml_close_handle` 返回 | Dart 侧观测（`store.close`／`account.close_profile`） | 对应 op 错误码（owner） |
| --- | --- | --- | --- |
| 句柄活跃，且只有仍可取消的在途 job | 0（已受理关闭，进入 closing 后立即返回，不等待排空） | submit 先得到 ok `{}`；最终结果由完成回调或 ProfileSession Future 给出 | 无（成功），owner CORE-13 |
| 句柄已在 closing，或仍有不可取消活跃 job（定义见 `FFI_BUSY` 行） | -6 | 同一绑定的关闭复用同一 Future；直接看原生返回则抛 `FfiException(status: -6)`、错误信封 code 为 `FFI_BUSY` | `STORE_BUSY`（CORE-13） |
| 句柄未知、代数不符或已退役（含关闭完成后再关） | -4 | 错误信封 code 为 `FFI_STALE_HANDLE`；ProfileSession 侧复用已完成的 Future | `FFI_STALE_HANDLE`（本卡） |
| 已受理后 Store 层失败（排空超时、IO 或校验损坏、密钥清零失败） | 无返回（0 已先返回） | 关闭响应或完成回调给 error：`STORE_BUSY` 或 `STORE_CORRUPT`；句柄保持 closing、不得复活旧 handle | `STORE_BUSY`、`STORE_CORRUPT`（CORE-13） |

**实现约束**
- 不暴露 Rust 泛型、trait 对象与生命周期；所有句柄由核心分配和释放；传入缓冲区必须带长度；字符串消息一次性拷贝。
- 每个导出函数用 `catch_unwind` 包裹，panic 转 `FFI_PANIC` 并记录 trace_id，不得跨边界展开。
- `fml_call` 只用于 P95 ≤30 ms 的操作，超出的 op 必须走 `fml_submit`。
- `fml_call` 必须可从多个线程并发调用；完成回调只由主 isolate 的绑定注册，其他 isolate 打开的绑定调用 `submit` 抛 `StateError`。
- Dart 侧 DTO 统一由 CORE-67 从 schema 生成至 `app/lib/binding/dto/`，业务层与界面层只引用生成类型；禁止在特性目录再手写同名序列化类。字段归属仍为业务所有者卡，生成器不定义业务语义。
- 头文件与 `ffigen` 生成的 Dart 绑定纳入版本控制，CI 做 ABI 漂移检查（CORE-41）。
- 外部前提：Dart `ffigen` 包（版本按 ADR-V5-15 锁入 `pubspec.lock`）；Android NDK 与 MSVC 工具链见 AND-01、WIN-01。
- 选型：C ABI + dart:ffi 单一导出面，不另引入第二套绑定导出，使未来鸿蒙 NAPI 复用同一头文件（附录 A ADR-V5-02）。
- 依赖分类：本卡只依赖 CORE-01、CORE-02、CORE-67。正文提到的 CORE-05、CORE-06、CORE-10、CORE-11、CORE-13、CORE-18、CORE-23、CORE-24、CORE-41、CORE-44、CORE-52、CORE-56、CORE-65、CORE-70、CORE-73 与 AND-01、WIN-01 是消费方、被适配方或下游说明，不是本卡的代码依赖，因此不加入“依赖”行（下游说明，非契约）。其中 CORE-13 是本卡 op 派发面的消费方：`store.open`/`store.close`/`store.integrity_check` 的 op 语义、Dart 侧关闭入口与 STORE 系错误集合归 CORE-13（S2 阶段，晚于本卡），本卡只规定注册/派发/关闭入口与六个 FFI 码；CORE-23 是 `AUTH_NO_PROFILE` 的唯一所有者（S2 阶段），本卡只在派发流程里说明该错误由档案路由返回，不重新定义它。
- 错误码注册表是外部前提：`contracts/errors/registry.yaml` 由 CORE-02 创建并维护，本卡只登记六个 FFI 码的 code/owner；registry 尚未创建前，severity/retryable 投影的验收条记 pending，不得以 DTOcheck 退出 0 或 shared-writes 索引代替，也不得在本卡另建注册表或第二份错误表。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-03_TEST.md](../Test/S0/S0_CORE-03_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 775 行；主包 `crates/fml-ffi/`（导出边界、缓冲区、句柄代数与关闭、op 分派、信封、档案路由、长任务池、错误映射，约 490），附属：`contracts/include/fmlcore.h`（约 25 行手写声明）与跨语言另一侧 `app/lib/binding/`（CoreBinding/FfiCoreBinding、submit 与 NativeCallable 监听、dispose 与 scopedTo、异常与取消类型、ffigen 配置，约 260）；ffigen 与 CORE-67 生成物不计，业务 schema/生成器归 CORE-67。分阶段：① C ABI 与同步运行时（含 fmlcore.h，约 350）；② Rust 长任务池、监听/取消与关闭收敛（约 165）；③ Dart 核心绑定（app/lib/binding/，约 260）。阶段①以同步op和Fake派发独立构建验证，阶段②以Rust回调夹具验证长任务，阶段③接入Dart并完成跨语言验收，不提前宣称后续阶段通过。行数依据：350=头文件声明与生成常量25+缓冲区与分配表60+六码映射与参数校验50+信封编解码与trace 70+同步派发与句柄表145；165=长任务池与队列上限45+完成回调注册/替换/注销40+取消与竞态释放45+closing排空与退役35；260=CoreBinding/scopedTo 60+call/submit与信封50+NativeCallable监听与释放70+FfiException/CancelToken 30+dispose/StateError 25+ffigen配置与生成头25。实现后按实测修订；偏差超过±15%时同步本行与 SADD/core/00-总览.md 索引。本轮修订新增的 op 注册/派发面（`OpEntry`、`OpHandler`、`OpCtx`、`OPS` 自检与 Fake op）落在阶段①既有“同步派发与句柄表 145”与头文件项内，关闭编排映射表只是既有过程的说明、不新增实现，故合计仍在 ±15% 容差内；本行与 `SADD/core/00-总览.md` 索引的 775 保持不变。

