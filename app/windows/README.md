# WIN-01 Windows 工程样品

入口是 `lib/main_windows.dart`；应用为 `bubeigongshi_app.exe`，不是未来 WIN-16 的启动器。只支持 x64。Flutter/Rust 版本沿用仓库锁，Windows 工具记录在 [toolchain.versions](toolchain.versions)。Inno 未安装，安装器、签名、升级及实际平台适配器不在本卡交付内。

## 构建与启动

从 app 目录执行：

```text
flutter build windows --release -t lib/main_windows.dart
```

构建调用 [build_core.dart](build_core.dart) 运行锁定 Cargo 的生产 fml-ffi（无测试 feature），使用静态 CRT、路径映射、固定 SOURCE_DATE_EPOCH、/Brepro 与符号信息。DLL 自动安装到应用同目录；PDB 保留在构建目录供归档，不属于运行时安装步骤。Flutter 引擎 DLL 自身依赖的 VC runtime 与 Rust DLL 的静态 CRT 要求不同。

启动最早限制 DLL 搜索目录；Dart 只构造 exe 相邻绝对 DLL 路径。CORE-04 负责先验 ABI MAJOR，失败只显示不可用页，不创建端口。当前 11 个槽均为 Unsupported，installers 为空，每槽打印一次；冒烟页显示真实 ABI 与运行时待实现提示，不含公式业务。

## 通道接入与销毁

[flutter_window.cpp](runner/flutter_window.cpp) 是唯一注册/消息分发位置；后续卡只能在此加入自己的真实 RegisterXxxChannel 调用，不能替换 engine WndProc。top/view HWND 分开。顶层委托使用 Flutter token，并在退出注销；view 使用可移除 SetWindowSubclass。观察消息返回 nullopt，消费消息返回 LRESULT。所有注册与回调 API 只允许平台线程调用。

工作线程只持有 shared PlatformDispatch，使用带 request_id 的结果字节 Complete；不持 messenger、MethodResult、窗口对象或 Dart 回调。平台线程 ExpectReply 返回 id，WM_APP+1 才取出/擦除并回复；重复或未知 id 丢弃。PostMessage 失败即丢弃结果并返回 false，通道所有者负责其任务取消，不得在工作线程补回调。

通道用 ShutdownHooks 注册幂等清理：先拒绝新请求/关闭队列，再全部 cancel_and_join（不持队列锁），再注销 wait/委托/subclass，丢弃待回复对象，释放通道，最后销毁引擎。关闭后 Complete 返回 false。当前没有后台服务、通知或生命周期通道；其真实语义须由对应后续卡实现并测，不用 Fake 的通过替代。

## 测试

从 app 设置 FML_WINDOWS_LIBRARY 为本次构建的绝对 DLL 路径，FML_BUMP_LIBRARY 为 CORE-03 abi_major_bump 测试 DLL；再执行 `flutter test test/windows`。没有这些前提时相应两项明确 skip，不是完整验收。全套绑定测试另依 CORE-03 的测试 DLL 与 CASES 环境。

[reproducibility.dart](tests/reproducibility.dart) 从任意目录运行：

```text
dart app/windows/tests/reproducibility.dart <dumpbin.exe的绝对路径>
```

执行两次 flutter clean + Release 构建，逐字节比较 fmlcore.dll 并检查导入表。不声称不同 SDK/目录/机器的产物也相同。

原生纯队列测试：

```text
cmake -S app/windows/tests -B build/win01-tests -A x64
cmake --build build/win01-tests --config Release
ctest --test-dir build/win01-tests -C Release --output-on-failure
```

真实 Flutter host 测试：在先完成 Release 后配置 app/build/windows/x64 的 FML_RUNNER_TESTS=ON，构建 win01_runner_test；在含 data 与 flutter_windows.dll 的 Release 目录运行。该测试验证真实顶层/子窗口委托、工作线程结果恰好一次回复、注销与 shutdown join 顺序。测试选项默认关闭；测试程序不安装。

仅测试构建可同时设置环境 FML_WINDOWS_TEST_BUILD=1、Dart define FML_TEST_BUILD=true，并选 FML_TEST_CRASH_ON_FIRST_START=true。此时任一用户参数 startsWith(--update-nonce) 在入口 exit(3)，无匹配参数仍正常启动；不解析 nonce 业务。生产未显式 opt-in 时任何 FML_TEST_* define（包括 false）均拒绝。windowsLaunchArguments 仅接受首次不可变拷贝，不使用 Dart VM executableArguments。

## 手动/环境矩阵

- Windows 10 1809 与 Windows 11 分别运行 Release：ABI、固定待实现提示、11 日志及关闭。单一 Windows 10 22H2 的通过不覆盖这两个目标。
- 用真实 MAJOR+1 DLL 与缺失/损坏 DLL 分别启动；只能看到对应不可用页与退出按钮。单元测试覆盖同一 CORE-04 入口，但不等同每个 OS 的打包程序验收。
- Process Monitor 检查 hostile cwd/PATH 下实际 Image Load；进程模块枚举是补充证据，不能冒称已运行 Process Monitor。
- 发布前用批准图标替换 Flutter 模板图标，按后续发布卡配置公司元数据/签名并归档 PDB。
