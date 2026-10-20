# CORE-03 测试方案

> 来源卡：[S0_CORE-03_基座.md](../../S0/S0_CORE-03_基座.md)（C ABI 与 Dart 绑定）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R01] 契约测试（`crates/fml-ffi/tests/abi.rs` 与 `app/test/binding_test.dart`）：同一组 fixtures 在 Android 与 Windows 上得到逐字节相同的输出。
- [R19] 故障注入：过期句柄、重复释放、空指针、超限 DTO、未知 op、未知 DTO 主版本、op 内 panic 均返回上表约定的返回码与错误码，进程不崩溃；第 65 个并发长任务返回 `-6`。
- [R01] 取消测试：提交长任务后立即 `fml_cancel`，回调至多触发一次，`fml_cancel` 返回0后该 job 的任务资源归零；已投递回调经 Dart 消费后未释放缓冲区归零；Store 句柄按 close 单独计数。
- [R02] `contracts/include/fmlcore.h` 能被纯 C 程序编译链接（由 CORE-44 执行）。
- [R19] dispose 测试（`app/test/binding_test.dart`）：有 3 个活跃 job 时 dispose 后新 call/submit 被拒绝、3 个 job 均收到 cancel；首次 `fml_register_completion(NULL, NULL)` 返回 -6 时绑定继续处理事件循环、不阻塞 isolate，迟到结果仍被释放，计数归零后注销成功并关闭 listener；非主 isolate 的绑定 dispose 不注销全局 listener。

- [R27][R19] A/B两个档案并发写同名fixture只改变各自库；缺handle返回AUTH_NO_PROFILE，A视图传B的profile_id返回FFI_BAD_ARG，关闭A后旧worker请求返回FFI_STALE_HANDLE且B不变；close等在途租约排空并清零敏感副本。
