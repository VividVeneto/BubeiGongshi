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
int32_t  fml_close_handle(FmlHandle h);
#ifdef __cplusplus
}
#endif
```

- 返回码：`0` 成功（`out` 为下述成功信封）；`1` 业务错误（`out` 为下述错误信封）；负数为 FFI 层错误，此时 `out` 尽量写入同样错误信封（分配失败时 `ptr` 为 NULL、`len` 为 0）：

| 返回码 | 错误码 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| -1 | `FFI_BAD_ARG` | 否 | 空指针、`req_len` 超过 16 MiB、请求不是合法 UTF-8 JSON、顶层缺 `v` 或 `body`、重复释放缓冲区、未注册回调就调用 `fml_submit` |
| -2 | `FFI_UNKNOWN_OP` | 否 | op 未登记，或该 op 不支持当前调用方式（同步 op 走了 `fml_submit`，反之亦然） |
| -3 | `FFI_VERSION_MISMATCH` | 否 | DTO 主版本 `v` 不是该 op 支持的主版本 |
| -4 | `FFI_STALE_HANDLE` | 否 | 句柄代数不符或已关闭；未知 `job_id` |
| -5 | `FFI_PANIC` | 否 | op 内部 panic（已被 `catch_unwind` 捕获） |
| -6 | `FFI_BUSY` | 是 | 长任务队列已满（排队 + 运行 ≥ 64）；或 `fml_register_completion` 在仍有活跃 job 或未释放回调缓冲时被调用（含 NULL 注销） |

- `fml_cancel`：返回 `0` 表示已取消且不会再回调；返回 `1` 表示任务已完成或回调已发出（取消无效）；未知 `job_id` 返回 `-4`。
- `fml_register_completion`：进程内只保存一个回调，只有无活跃job及未释放回调缓冲时允许替换；否则返回-6。cb=NULL注销也遵守此规则；回调在核心工作线程上执行，`result` 的所有权交给回调方，用完须 `fml_free_buffer`。长任务工作线程数为 `min(4, CPU 核数)`。
- `budget_ms`：只对声明支持预算的 op 生效，超时由该 op 返回本域错误码（如 `EVAL_TIMEOUT`）；其他 op 忽略此字段。
- DTO 映射规则（各卡 FFI op 未另行列出字段时适用）：请求 `body` 与响应 DTO 是对应 Rust 结构体的 serde JSON——字段名与结构体字段同名（snake_case）；无数据的枚举值为 snake_case 字符串，带数据的变体为 `{"<变体名>": 数据}`；`Option` 为 `None` 时省略字段；`FormulaNode` 一律用 CORE-05 规范 JSON；UUID 类 ID 为小写带连字符字符串，`SymbolId` 为整数；十进制数值（值、不确定度、区间端点）一律为字符串；时间为 `*_ms` 整数（Unix 毫秒）；二进制为 base64 字符串。请求缺必填字段或类型不符时返回 `FFI_BAD_ARG`。
- `fml_capabilities` 示例：`{"abi":"1.0","ops":[{"op":"engine.parse","dto":1,"mode":"call"},{"op":"image.decode","dto":1,"mode":"submit"}],"build":{"app":"1.0.0","git":"<sha>","target":"aarch64-linux-android"}}`。
- DTO：UTF-8 JSON，顶层 `{"v": <dto_major>, "trace_id": "...", "budget_ms": <u32 可选>, "profile_handle": <十进制u64字符串，可选>, "expected_generation": <十进制u64字符串，可选>, "body": {...}}`；schema 在 `contracts/dto/<op>.schema.json`；未知主版本拒绝。
- op 命名 `<域>.<动作>`，如 `engine.parse`、`engine.check`、`typeset.layout`、`calc.evaluate`。每张功能卡在“接口契约”中列出它登记的 op。
- 长任务（图片解码、本地推理、导出、迁移）走 `fml_submit`，由核心通过 `FmlCompletion` 通知；不提供轮询接口。回调线程不得持锁，不得重入 UI。

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
  final String code;                 // 如 'FFI_BUSY'
  final String? traceId;
}
final class FfiCancelled implements Exception {}
// 业务错误抛 FmlException（CORE-02）；FFI 层错误抛 FfiException。
// 启动时 abiVersion() 的 MAJOR 与 Dart 侧常量不一致即拒绝启动并提示重装。
```

动态库名：Android `libfmlcore.so`，Windows `fmlcore.dll`；加载方式由 AND-01、WIN-01 规定。

**跨语言信封、回调与资源**
- 请求示例：`{"v":1,"trace_id":"00000000000000000000000000000001","body":{}}`。成功示例：`{"v":1,"trace_id":"00000000000000000000000000000001","ok":{"profiles":[]},"diagnostics":[]}`。业务错误/负返回码示例：`{"v":1,"trace_id":"00000000000000000000000000000001","error":{"code":"FFI_BAD_ARG","domain":"ffi","retryable":false,"trace_id":"00000000000000000000000000000001","diagnostics":[]}}`。ok/error 必有且仅有一个；error 内部形状归 CORE-02；完成回调传相同信封，负状态由 error.code 判别；call/submit 的 Dart 包装只向业务返回 ok。
- Dart ≥3.1 使用 `NativeCallable.listener`，不使用 Pointer.fromFunction。C 工作线程调用后返回；Dart isolate 收到后在 try/finally 中复制、解析结果并 fml_free_buffer；取消竞态收到的迟到结果也必须释放。绑定为进程主 isolate 保存唯一 listener，活跃 job 与已投递结果未清零前不得 close listener/卸载 DLL；dispose先拒绝新call/submit、对绑定活跃job调用cancel，等待已投递通知经finally释放；用fml_register_completion(NULL,NULL)确认无活跃job/回调buf后才close listener，Busy则继续事件循环等待，不能同步阻塞isolate。结果分配至Dart释放的全过程计入未释放回调缓冲计数；无listener的其他isolate绑定dispose不注销全局listener。动态库保持进程寿命，不假设Dart有可安全卸载API。
- `store.open` 是 FmlHandle 的产生者，JSON 用十进制字符串表示 u64；generation 高16位、slot低48位，耗尽后 slot 不复用。close/integrity 等携 handle 查表，拒绝过期值；close 等待在途读写后销毁。缓冲区在注册表按 allocation_id 核对 ptr/len，未知值不解引用，重复释放返回-1；id 进程内单调且不复用。
- db_key_b64、恢复码、口令、令牌均为敏感字段，schema 标记 writeOnly/x-sensitive；禁止请求/响应全量日志、快照与异常插值。FFI只读const请求并在返回前复制需要保留的字节，绝不写入调用者内存；核心拥有的敏感副本使用Zeroizing。Dart自己分配的临时Uint8List在native调用返回（submit已同步复制）后的finally填零；其他C调用者负责自己可写缓冲区清理。JSON/String的不可控副本不能承诺可靠擦除，产品安全边界明确为“不持久化、不记录”，不是“明文从不进Dart堆”。
- 每个 op 在所有者卡维护字段表与成功例，`contracts/dto/<op>.schema.json` 的 `$defs` 必含 request/ok，公共类型经 `$ref` 到所属卡 schema；manifest 记录 owner/mode/error_codes/sensitive_paths。未知字段 additionalProperties=false；未知枚举/缺必填/非有限数拒绝，None省略，数值精度规则按上述映射。全量清单与生成门禁见 CORE-67。

ABI不匹配测试专用Cargo feature abi_major_bump仅让fml_abi_version返回MAJOR+1，不修改公共头或生成的Dart常量；与正常产物用不同target-dir，测试安装脚本替换仅核心库。发布CI拒绝该feature及capabilities中的test_build标记；AND-01/WIN-01复用此机制。

档案路由（ADR-V5-39）：manifest 的 scope 必为 none/device/profile，未知或缺失 scope 拒绝注册。profile op 必须携信封 profile_handle；缺失返回 AUTH_NO_PROFILE，未知/已关闭/closing 句柄返回 FFI_STALE_HANDLE。绑定在派发前取得该 handle 的 Store 租约，绝不从“当前账户”单例取库。若 body 另含 profile_id，须与句柄登记身份相等，否则 FFI_BAD_ARG；store.close/integrity_check 的 body.handle 与信封同时出现时也须相同。none/device op 禁带 profile_handle，避免调用方误以为受到档案隔离。升级合库的 target_handle 是 CORE-24 明列的第二句柄，不靠全局切库。

scopedTo 只产生绑定视图，不拥有 Store；CORE-65 是交互档案句柄的唯一关闭者。调用者不能在已scoped视图上改绑其他handle；worker由主绑定传入同一handle后scopedTo，任务创建时捕获句柄，切换后不重定向到新库。fml_close_handle 与 store.close 共用同一个关闭过程：先标 closing 并拒绝新租约，取消/排空该句柄的job，等租约归零，关闭Store及其Zeroizing密钥，再退役slot。取消失败的已投递结果仍释放；关闭失败维持closing并报告STORE错误，禁止将旧handle复活。关闭是submit，不能在Dart UI线程同步等待。

expected_generation 只用于引擎快照消费op（CORE-56五op及CORE-11三个derive op；CORE-52导出处理器同样遵守）；为非负u64十进制字符串，未给时取当前快照，给出时必须与所取快照一致，不一致返回 ENGINE_UNAVAILABLE且不执行算法。成功和业务错误信封可含 engine_generation（同格式），由本次所持快照填写，不能读取完成时的全局值。CoreBinding新增只读 Stream<String> get engineGenerations；解析信封时先投递generation再向业务返回ok，未知字段不得混入业务DTO。无快照的op不带该字段；通知契约的所有者见CORE-73（下游说明，非契约）。

关闭控制操作store.close/account.close_profile/fml_close_handle只解析并校验句柄身份，不取得会阻止自己完成的普通Store租约；控制任务不计入待排空的本句柄业务job集合。关闭开始即原子撤销新租约，既有租约的释放路径不再请求关闭锁。scoped视图只允许profile op；device/none操作显式用root绑定。关闭后的再次关闭由ProfileSession复用同一Future，原生旧句柄仍返回FFI_STALE_HANDLE。

**实现约束**
- 不暴露 Rust 泛型、trait 对象与生命周期；所有句柄由核心分配和释放；传入缓冲区必须带长度；字符串消息一次性拷贝。
- 每个导出函数用 `catch_unwind` 包裹，panic 转 `FFI_PANIC` 并记录 trace_id，不得跨边界展开。
- `fml_call` 只用于 P95 ≤30 ms 的操作，超出的 op 必须走 `fml_submit`。
- `fml_call` 必须可从多个线程并发调用；完成回调只由主 isolate 的绑定注册，其他 isolate 打开的绑定调用 `submit` 抛 `StateError`。
- Dart 侧 DTO 统一由 CORE-67 从 schema 生成至 `app/lib/binding/dto/`，业务层与界面层只引用生成类型；禁止在特性目录再手写同名序列化类。字段归属仍为业务所有者卡，生成器不定义业务语义。
- 头文件与 `ffigen` 生成的 Dart 绑定纳入版本控制，CI 做 ABI 漂移检查（CORE-41）。
- 外部前提：Dart `ffigen` 包（版本按 ADR-V5-15 锁入 `pubspec.lock`）；Android NDK 与 MSVC 工具链见 AND-01、WIN-01。
- 选型：C ABI + dart:ffi 单一导出面，不另引入第二套绑定导出，使未来鸿蒙 NAPI 复用同一头文件（附录 A ADR-V5-02）。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-03_TEST.md](../Test/S0/S0_CORE-03_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 775 行；主包 `crates/fml-ffi/`（导出边界、缓冲区、句柄代数与关闭、op 分派、信封、档案路由、长任务池、错误映射，约 490），附属：`contracts/include/fmlcore.h`（约 25 行手写声明）与跨语言另一侧 `app/lib/binding/`（CoreBinding/FfiCoreBinding、submit 与 NativeCallable 监听、dispose 与 scopedTo、异常与取消类型、ffigen 配置，约 260）；ffigen 与 CORE-67 生成物不计，业务 schema/生成器归 CORE-67。分阶段：① C ABI 与同步运行时（含 fmlcore.h，约 350）；② Rust 长任务池、监听/取消与关闭收敛（约 165）；③ Dart 核心绑定（app/lib/binding/，约 260）。阶段①以同步op和Fake派发独立构建验证，阶段②以Rust回调夹具验证长任务，阶段③接入Dart并完成跨语言验收，不提前宣称后续阶段通过。

