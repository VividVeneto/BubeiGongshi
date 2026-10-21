### WIN-01 工程与构建

**目标**：建立 Windows 桌面工程，把 Rust 核心编译为 `fmlcore.dll` 并按绝对路径安全加载，组装 Windows 端口，产出可运行的 Release 构建。

**范围**
- 包含：`app/windows/` CMake 工程与 runner；Cargo 构建 `x86_64-pc-windows-msvc` 并把 `fmlcore.dll` 装入构建输出；DLL 搜索路径加固；`main_windows.dart` 入口；`composition/ports_windows.dart` 组装（未实现的端口先用 CORE-04 的 Unsupported 占位）；通道注册约定；版本资源；工具链版本文件。
- 不包含：安装器与启动器（WIN-02、WIN-16）；自更新（WIN-03）；签名（WIN-12）；各端口实现（WIN-04～10）；ABI 校验与“核心不可用”页面（CORE-04 `runPlatformApp`）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04

**接口契约**

调用的公共契约（定义见 CORE-03 与 CORE-04，逐字摘录）：

```dart
static CoreBinding open(CoreLibrarySpec spec) => FfiCoreBinding(spec);           // CORE-03
Future<void> runPlatformApp(CoreLibrarySpec spec, PlatformPorts Function() buildPorts,
    {CoreBinding Function(CoreLibrarySpec)? open /* 测试注入；默认 CoreBinding.open */});   // CORE-04 entry.dart
```

本卡实现：

```dart
// app/lib/main_windows.dart
Future<void> main(List<String> args) async {
  // 仅显式FML_TEST_BUILD测试构建允许故障注入；正式发布流水线拒绝全部FML_TEST_* define。
  const crash = bool.fromEnvironment('FML_TEST_CRASH_ON_FIRST_START');
  const testBuild = bool.fromEnvironment('FML_TEST_BUILD');
  if (crash && !testBuild) throw StateError('test define in production');
  if (crash && args.any((a) => a.startsWith('--update-nonce'))) exit(3);
  setWindowsLaunchArguments(args);
  await runPlatformApp(CoreLibrarySpec(appDirFile('fmlcore.dll')), buildWindowsPorts);
}
// app/lib/composition/windows_launch.dart（本卡所有；只记录参数，不解析更新或托盘业务）
List<String> get windowsLaunchArguments; // 不可变快照
void setWindowsLaunchArguments(List<String> args); // main调用一次，再写抛StateError
// runner使用Flutter Windows模板GetCommandLineArguments()/DartProject.set_dart_entrypoint_arguments透传用户参数；
// 不将更新nonce误从Dart VM的Platform.executableArguments读取；后续卡各自读取windowsLaunchArguments。
String appDirFile(String name) => File(Platform.resolvedExecutable).parent.uri.resolve(name).toFilePath();   // 可执行文件同目录的绝对路径

// app/lib/composition/ports_windows.dart
PlatformPorts buildWindowsPorts();
// 每个端口字段一行：初始全部为 CORE-04 的 Unsupported 占位Xxx，并 debugPrint('port <字段名>: unsupported')；camera 恒为 WIN-04 的不支持实现（WIN-04 完成前用 UnsupportedCamera）。
// platformInstallers 初始为 const []；后续卡按下文最终顺序表接入。
// WIN-04～WIN-10 实现某端口时只替换该字段对应的一行；替换与追加行计入对应功能卡规模，不重复计入本卡骨架；仍属同一构建单元。
```

```text
app/windows/
  CMakeLists.txt            BINARY_NAME = "bubeigongshi_app"（固定名 BubeiGongshi.exe 留给 WIN-16 启动器）
  rust.cmake                add_custom_command：cargo build -p fml-ffi --release --target x86_64-pc-windows-msvc
                            （RUSTFLAGS 含 -C target-feature=+crt-static 与 --remap-path-prefix），产物 fmlcore.dll 经 install(FILES) 放到 exe 同目录；
                            cargo 退出码非 0 → CMake 构建失败并原样输出
  runner/main.cpp           wWinMain 第一行：SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_APPLICATION_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32); SetDllDirectoryW(L"");
  runner/flutter_window.cpp OnCreate 中按“每个平台卡一行”调用 RegisterXxxChannel(messenger, hwnd)；通道名前缀 "fml/windows/"
  runner/Runner.rc          FileVersion/ProductVersion 取 pubspec 版本；ProductName "BubeiGongshi"
  runner/runner.exe.manifest  dpiAwareness PerMonitorV2；supportedOS Windows 10
  toolchain.versions        msvc=、windows_sdk=、cmake=、inno= 的锁定版本（每行 key=value；Rust 与 Flutter 只在 CORE-01 的 rust-toolchain.toml、app/.flutter-version）
构建命令：flutter build windows --release --dart-define=FML_API_HOST=<host> --dart-define=FML_PACK_HOST=<host>
```

- 本卡不新增错误码；核心加载失败与 ABI 不符由 CORE-04 `runPlatformApp` 处理。

**runner 公共约定（ADR-V5-37）**
- 下游接入说明（非本卡依赖）：WIN-04的RegisterFilesChannel唯一注册fml/windows/files；WIN-19的RegisterImageDropChannel唯一注册fml/windows/drop及可注销拖放delegate。聚合维护者合入OnCreate/CMake，接入行各计对应特性卡；不得在同一通道覆盖handler。
- WIN-01 唯一维护 flutter_window.cpp；每卡只追加 `RegisterXxxChannel(messenger, topHwnd, viewHwnd)` 一行。topHwnd 是 Win32Window 顶层窗口；viewHwnd 取 `controller->view()->GetNativeWindow()`，不得混用。
- 通道 handler、MethodResult 回复、EventSink/InvokeMethod 均在平台线程执行。工作线程仅计算/复制，把含 request_id 的结果放进互斥队列，再 PostMessage(topHwnd, WM_APP+1,0,0) 唤醒；唯一调度 delegate 在平台线程取结果并回复一次。PostMessage 失败须回收结果；窗口关闭后丢弃未回复请求，不访问 messenger。
- 顶层消息每卡登记 RegisterTopLevelWindowProcDelegate，保存 token，关闭时注销。子视图消息须由本卡可移除的 SetWindowSubclass 转发到对应模块；不得替换引擎 WndProc，不在工作线程直接访问 HWND 对象所有者。消息只观察返回 nullopt，消费才返回 LRESULT。
- 退出顺序：停止接受请求→取消任务/等待工作线程→注销等待句柄/事件/窗口委托与子类化→释放通道与 messenger 引用→销毁 FlutterViewController/窗口。清理幂等；不在持锁状态 join 或发送同步窗口消息。
- Release：C++ runner/启动器编译 `/Zi`、链接 `/DEBUG:FULL /Brepro /PDBALTPATH:%_PDB%`；Rust `[profile.release] debug = "line-tables-only"`，Windows target rustflags 加 `-C link-arg=/Brepro`（保持路径映射）。PDB 保留构建产物，仅符号归档发布，不能装入安装器；完整可复现性仍由两次干净构建验证。

最终组装表（只随对应卡落地启用，不要求S0引用未来实现）：buildWindowsPorts先创建唯一WindowsPrefs，传给WindowsNotificationScheduler，并以闭包`(ctx) => installWindowsShell(ctx, prefs)`登记同一实例；初始Unsupported期间不创建此实例。端口构造先于安装点执行，构造器不得读取FeatureRegistry。

| 安装顺序 | 安装点 | 前置/用途 |
| --- | --- | --- |
| 1 | installWindowsShell（WIN-06） | 登记已构造的prefs、shell |
| 2 | installWindowsInteraction（WIN-15） | 取得prefs，唯一ShellKeyHandler |
| 3 | installWindowsStorage（WIN-07） | SettingsSections |
| 4 | installWindowsEditing（WIN-08） | attach到WIN-15 |
| 5 | installWindowsDrop（WIN-19） | 注册拖放 |
| 6 | installWindowsClipboard（WIN-05） | 注册公式复制 |
| 7 | installWindowsTray（WIN-09） | 取得WIN-06 shell/prefs |
| 8 | installWindowsKeymap（WIN-14） | 编辑/学习键位均已登记 |
| 9 | installWindowsUpdater（WIN-03） | 全局账户安装点CORE-65已完成 |

本表只约束平台安装点相对顺序；CORE-36总编排仍为transportInstallers→featureInstallers→platformInstallers。WIN-10为端口构造替换，无安装点。

产品约束追踪：见README §6 Q5；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 绑定方式只用 C ABI + `dart:ffi`（ADR-V5-02）；只按绝对路径加载 `fmlcore.dll`，不经当前工作目录、PATH 或用户目录搜索。
- `fmlcore.dll` 静态链接 C 运行时（`+crt-static`），不依赖另行安装的 VC++ 运行库；Flutter 自带的 `msvcp140.dll` 等按 Flutter 模板随包分发。
- 目标架构 x64；ARM64 原生构建不在 V1 范围（ARM64 设备以仿真运行，不做专项承诺）。
- Release 构建 MSVC 链接参数含 `/Brepro`，与 Rust 的路径重映射一起使 DLL 可复现。
- 外部前提：Visual Studio 生成工具（MSVC）、Windows SDK、CMake、Inno Setup 的具体版本由本卡按 ADR-V5-15 在 S0 写入 `toolchain.versions`；Rust 与 Flutter 以 CORE-01 的 `rust-toolchain.toml`、`app/.flutter-version` 为准。

**验收标准**：测试方案全文见 [Test/S0/S0_WIN-01_TEST.md](../Test/S0/S0_WIN-01_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 310 行；`app/windows/`、`app/lib/main_windows.dart`、`app/lib/composition/ports_windows.dart`、`app/`。组件估算：Cargo/CMake可执行构建规则约 70 行，runner模板补丁/DLL安全/调度与退出约 180 行，Dart入口/参数/聚合骨架约 60 行。只计本卡交付实现及附属接入代码；验证测试、夹具与静态配置/资源数据不计。

