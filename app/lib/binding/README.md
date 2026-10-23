# CORE-03 Dart 绑定（阶段③候选）

公共入口为 [core_binding.dart](core_binding.dart)，底层八符号来自真实 ffigen 输出 [fmlcore.g.dart](fmlcore.g.dart)，不是手写 ABI。错误通过既有 [errors.dart](errors.dart) 与 CORE-67 DTO 解码。阶段③修复了响应版本类型、状态/错误码一致性与请求字节所有权；仍须独立代码复核，不能作为整卡验收通过。

## 所有权与调用

平台层提供 `CoreLibrarySpec(path)`，根 isolate 调用 `CoreBinding.open(spec)`；加载错误原样抛出。调用方比较 `abiVersion() >> 16` 与生成常量 `FML_ABI_MAJOR`，决定启动错误页，不由绑定创建 UI。一个根绑定独占进程 completion listener；其他 isolate 可同步 call，但 submit 抛 StateError。DLL 保留到进程退出。

`scopedTo(handle)` 返回不可改绑的档案视图；十进制 u64 句柄通过 envelope.profile_handle 传递，不转换为 double。视图 dispose 不关闭根 listener 或 Store，根 dispose 后所有视图拒绝新请求。Store/session 所有权仍在 CORE-65/23；绑定没有公开 close_handle。

call 返回 ok 内业务 Map，submit 返回 Future；取消 token 幂等，底层阻塞 cancel 在后台 isolate 执行。根 dispose 拒新、取消、等待所有任务及取消调用，Busy 注销时让出事件循环，只有注销成功才关闭 NativeCallable。迟到或未知 job 的 buffer 也复制后 finally 释放。

领域错误抛 FmlException，FFI 负状态抛 FfiException，取消抛 FfiCancelled；畸形响应抛 FormatException。响应 v 必须为整数 1；先完整校验 envelope、诊断与 status/code 一致性，再由 engineGenerations 同步广播通知订阅者，畸形响应不得发布 generation；不把 envelope 元数据混入返回 Map。生产 OPS 在当前原生基线为空，不能把 test_ops 当作业务支持。

请求不写日志。包装在 finally 清零自持可写请求字节和 native 请求分配；调用方对象、不可变 JSON String、VM/runtime 内部副本不在可保证擦除范围。直接持有 utf8.encode 返回的 Uint8List，不额外复制一个不可追踪的可写临时数组。源码所有权回归只检查该路径和 finally 擦除顺序，不是 VM 内存擦除证明。

## 重新生成

固定依赖 ffi 2.2.0、ffigen 23.0.0；Flutter/Dart 使用仓库锁定 SDK，不安装另一个 SDK。从 app 目录执行：

```sh
flutter pub get --offline
dart run ffigen --config ffigen.yaml
```

若 libclang 不在默认搜索位置，复制 [ffigen.yaml](../../ffigen.yaml) 为不提交的本机配置：仅替换 output、headers.entry-points 为仓库绝对路径并添加 `llvm-path: [本机libclang动态库路径]`。然后 `dart run ffigen --config 本机配置路径`。不要把机器绝对路径写回正式配置。当前 ffigen 的 YAML deprecated 警告不影响生成，未来迁移另行评估。对同一头文件连续生成两次比较 SHA-256，并执行格式化/分析。

## Windows 真实同步与补充边界测试

仓库根执行以下命令（需锁定 Rust、Python、MSVC 工具链），再从 app 跑 Flutter。不要在测试未预建 DLL 时误判为包缺失：

```sh
cargo build -p fml-ffi --features test_ops --target-dir build/binding-test
cargo build -p fml-ffi --features abi_major_bump --target-dir build/binding-bump
python app/test/build_binding_fixture.py
# working directory: app
flutter test test/binding_test.dart test/binding_fault_test.dart
```

`FML_TEST_LIBRARY`、`FML_BUMP_LIBRARY` 可覆盖真实 Rust DLL；`FML_FAULT_LIBRARY` 只用于专用 C 故障夹具。C 夹具测试验证 Dart 的 by-value trampoline、free-once、阻塞取消与 drain，不证明 Rust 线程池或64并发上限。DLL 不打包提交。Windows C 编译器诊断原始字节保存在 build 下，不能假定本地编码。

## 阶段②后真实异步联调

[异步测试](../../test/binding_async_test.dart) 在未提供 `FML_ASYNC_LIBRARY` 时明确 skip，绝不能算 pass；指定库后缺少 `FML_ASYNC_CASES` 会失败。用阶段②正式候选的 Rust test_ops DLL，不可使用本目录 C 故障库替代。CASE JSON 的 success/domain/panic/long 四项各需 op、body，success 另需 expected 业务 Map，domain 另需 code。已合入的阶段②提供 fake.async、fake.async_error、fake.async_panic、fake.wait；附加用例验证 fake.async_traced 与 fake.async_invalid。Git Bash 示例：

```sh
export FML_ASYNC_LIBRARY='本WT的build/binding-test/debug/fmlcore.dll绝对路径'
export FML_ASYNC_CASES='{"success":{"op":"fake.async","body":{},"expected":{"echo":{},"dto":1,"budget_ms":null}},"domain":{"op":"fake.async_error","body":{},"code":"EVAL_TIMEOUT"},"panic":{"op":"fake.async_panic","body":{}},"long":{"op":"fake.wait","body":{"wait_ms":5000}}}'
flutter test test/binding_async_test.dart test/binding_native_async_test.dart
```

long 有限时且支持协作取消；三个在途任务由根 dispose 取消并等待。原生 Dart 探针以 cancel 返回和注销结果同步，验证 0 无回调、1 持有结果、free 后 -4 以及 Busy -6，不以任意延迟推断资源归零。C 故障夹具单独确定性覆盖 submit 返回前回调、畸形/迟到 finally free、Busy 注销仍保持 listener 和阻塞取消不占事件循环；不能把它冒充 Rust 线程池。原生 jobs 单测以有限屏障验证真正64/65上限及 actor 关闭回收；真实 Store 关闭映射与A/B隔离、Android同夹具、双平台性能、启动错误页仍须对应模块/整合验收。
