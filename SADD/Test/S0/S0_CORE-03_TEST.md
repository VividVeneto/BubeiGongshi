# CORE-03 测试方案

> 来源卡：[S0_CORE-03_基座.md](../../S0/S0_CORE-03_基座.md)（C ABI 与 Dart 绑定）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R19] Trace 矩阵（阶段①/②先 Rust Fake op，阶段③再 Dart）：同步/异步成功回传请求 trace；领域零 trace 错误填入请求 trace，已有非零 trace 原样保留且外层相等；panic 与异步失败回调都带捕获的非零 trace。缺失、全零、大写、长度错误或非十六进制请求 trace 返回 FFI_BAD_ARG，能写 out 时备用 trace 非零。无 out/模拟分配失败仍按负状态报告、不得新增 ABI，Dart 无错误缓冲时 traceId 可空，有缓冲时拒绝内外不一致/零 trace。Dart 每次调用生成非零32位小写hex，scoped视图不二次改写；六个 FFI 码 severity/retryable 与 registry 投影相同（registry.yaml 由 CORE-02 创建；未创建前该投影断言记 pending，不得以 DTOcheck 退出 0 或 shared-writes 索引代替）。
- [R01] 契约测试（`crates/fml-ffi/tests/abi.rs` 与 `app/test/binding_test.dart`）：同一组 fixtures 在 Android 与 Windows 上得到逐字节相同的输出；两条作业分别标记 `android-host`、`windows-host` 环境，各自对同一份期望 fixture 断言，汇总登记复用 CORE-70 的 acceptance_jobs，本卡不另建运行器。
- [R19] 故障注入：过期句柄、重复释放、空指针、超限 DTO、未知 op、未知 DTO 主版本、op 内 panic 均返回上表约定的返回码与错误码，进程不崩溃；第 65 个并发长任务返回 `-6`（超过并发上限 `MAX_INFLIGHT_JOBS`=64）。
- [R01] 取消测试：提交长任务后立即 `fml_cancel`，回调至多触发一次，`fml_cancel` 返回0后该 job 的任务资源归零；已投递回调经 Dart 消费后未释放缓冲区归零；Store 句柄按 close 单独计数。
- [R02] `contracts/include/fmlcore.h` 能被纯 C 程序编译链接（由 CORE-44 执行）。
- [R01] ABI 主版本：以 `--features abi_major_bump` 构建的核心（仅 `fml_abi_version` 返回 MAJOR+1，头文件与生成的 Dart 常量不变）替换安装目录中的单个核心库后，`CoreBinding.open` 仍成功、`abiVersion() >> 16` 与 `FML_ABI_MAJOR` 不等；`runPlatformApp` 显示 `CoreUnavailableScreen(abiMismatch)` 且 `buildPorts` 未被调用。带该 feature 的 release（非 debug）构建由 `fml-ffi` 自身的 `compile_error!` 直接编译失败，故发布产物不可能出现 `capabilities.build.test_build=true`（归属本卡的构建期门禁，不由 CORE-41 的 manifest 步骤承担）。
- [R19] budget：`BUDGET_OPS` 中的 Fake op 收到小于其执行时长的 `budget_ms` 时返回该 op 的域错误码，响应 trace 与请求一致；不在表内的 op 携带 `budget_ms` 仍成功且字段被忽略、不报错；`fml_capabilities` 中两类的 `budget` 分别为 true/false。另按 CORE-01 预算行的同步调用预算验收：`fml_call` 同步路径 ≥1000 次调用、预热 100 次后取 P95，`android-host` 与 `windows-host` 两条作业各自断言。
- [R01] capabilities 形状：JSON 含 `abi`、`ops[].{op,dto,mode,budget}`、`build.{app,git,target,test_build}` 且类型正确；`budget=true` 的 op 集合逐项等于本卡 `BUDGET_OPS` 表；正常构建 `test_build=false`，abi_major_bump 构建为 true。
- [R27] fml_close_handle：存在仍可取消在途 job 的活跃句柄调用返回 0 且立即返回（未等待排空），排空阶段为这些 job 置位取消；再次调用返回 -6，句柄已在 closing 或仍有不可取消活跃 job（已发出回调或已越过取消检查点）同样返回 -6；未知/代数不符/已退役返回 -4；最终结果由 `store.close` 的 submit 回调或 ProfileSession Future 给出，Dart 绑定不暴露该函数。关闭编排映射表逐行断言：0→Dart ok `{}`、-6→`STORE_BUSY`、-4→`FFI_STALE_HANDLE`、已受理后 Store 失败→`STORE_BUSY`/`STORE_CORRUPT` 且句柄保持 closing 不复活，与 CORE-13 的 store.close 错误集合一致。
- [R19] 未登记负状态：Fake 导出函数返回 -99 时 Dart 抛 `FfiException(status: -99, code: null)`，不新增错误码；-1…-6 与六个 FFI 码逐项对应。
- [R19] dispose 测试（`app/test/binding_test.dart`）：有 3 个活跃 job 时 dispose 后新 call/submit 被拒绝、3 个 job 均收到 cancel；首次 `fml_register_completion(NULL, NULL)` 返回 -6 时绑定继续处理事件循环、不阻塞 isolate，迟到结果仍被释放，计数归零后注销成功并关闭 listener；非主 isolate 的绑定 dispose 不注销全局 listener。

- [R27][R19] A/B两个档案并发写同名fixture只改变各自库；缺handle返回AUTH_NO_PROFILE，A视图传B的profile_id返回FFI_BAD_ARG，关闭A后旧worker请求返回FFI_STALE_HANDLE且B不变；close等在途租约排空并清零敏感副本。
