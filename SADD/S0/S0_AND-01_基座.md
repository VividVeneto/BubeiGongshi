### AND-01 工程与构建

**目标**：建立 Android 工程，把 Rust 核心编译为 `libfmlcore.so` 并经 C ABI 加载，组装 Android 端口，产出可在真机运行的调试包。

**范围**
- 包含：`app/android/` Gradle 工程与 `MainActivity`；Cargo 交叉编译（cargo-ndk）的 Gradle 任务；ABI 选择；`libfmlcore.so` 打包；`main_android.dart` 入口；`composition/ports_android.dart` 组装（未实现的端口先用 CORE-04 的 UnsupportedXxx）；工具链版本文件；调试构建。
- 不包含：清单权限（AND-02）；签名与发布（AND-11）；各端口的具体实现（AND-02～09、AND-13/14（AND-10撤销））；ABI 版本校验与“核心不可用”页面（CORE-04 `runPlatformApp`）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04

**接口契约**

调用的公共契约（定义见 CORE-03 与 CORE-04，此处逐字摘录关键签名）：

```dart
static CoreBinding open(CoreLibrarySpec spec) => FfiCoreBinding(spec);           // CORE-03
Future<void> runPlatformApp(CoreLibrarySpec spec, PlatformPorts Function() buildPorts,
    {CoreBinding Function(CoreLibrarySpec)? open /* 测试注入；默认 CoreBinding.open */});   // CORE-04 entry.dart
```

本卡实现：

```dart
// app/lib/main_android.dart
void main() => runPlatformApp(const CoreLibrarySpec('libfmlcore.so'), buildAndroidPorts);

// app/lib/composition/ports_android.dart
PlatformPorts buildAndroidPorts();
// 每个端口字段一行：初始全部为 CORE-04 的 UnsupportedXxx（lib/ports/unsupported/），并 debugPrint('port <字段名>: unsupported')；
// platformInstallers 初始为 const []；最终顺序AND-13交互→AND-07输入→AND-14剪贴板→AND-08提醒，各追加一项（追加行同样不计入规模）。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）
// AND-03～AND-09 实现某端口时只替换该字段对应的一行（替换行不计入该卡规模，也不视为跨构建单元）。
```

```text
app/android/
  settings.gradle.kts、build.gradle.kts、app/build.gradle.kts    Android Gradle 工程（统一 Kotlin DSL，文件后缀 .gradle.kts）
  app/src/main/kotlin/.../MainActivity.kt            FlutterFragmentActivity 子类；本卡构造 AndroidChannelModule 列表，逐个 attach；通道全名必须唯一，不存在“注册前缀”机制
  toolchain.versions                                 ndk=、cargo-ndk=、gradle=、agp=、kotlin=、camerax= 的锁定版本（每行 key=value；Rust 与 Flutter 只在 CORE-01 的 rust-toolchain.toml、app/.flutter-version）
Gradle 任务 cargoNdkBuild（preBuild 依赖它）：
  cargo ndk --platform 26 -t arm64-v8a [-t armeabi-v7a] [-t x86_64（仅 debug）] -o app/src/main/jniLibs build -p fml-ffi [--release]
  cargo 退出码非 0 → Gradle 构建失败并原样输出 cargo 错误
构建命令：flutter build apk --debug --dart-define=FML_API_HOST=<host> --dart-define=FML_PACK_HOST=<host>
```

| 项目 | 规则 |
| --- | --- |
| minSdk | 26（Android 8.0） |
| targetSdk / compileSdk | 按 Google Play 与国内主流应用市场当年要求；数值写入 `toolchain.versions` 旁的 `app/build.gradle.kts`，升级走 PR |
| ABI | `arm64-v8a` 必须；`armeabi-v7a` 默认不打包（若 AND-12 真机矩阵或甲方提供的用户设备数据显示需要，再开启）；`x86_64` 只用于模拟器调试 |
| Rust 目标 | `aarch64-linux-android`；可选 `armv7-linux-androideabi`、`x86_64-linux-android` |
| 原生库 | `app/android/app/src/main/jniLibs/<abi>/libfmlcore.so`（构建产物，不入库） |
| 发布格式 | 应用商店 AAB；官网 APK（AND-11） |

- 本卡不新增错误码；核心加载失败与 ABI 不符由 CORE-04 `runPlatformApp` 处理。

原生模块扩展（仅 MainActivity 属本卡）：

```kotlin
interface AndroidChannelModule {
  fun registerActivityResults(activity: FlutterFragmentActivity) {}
  fun onStart() {}
  fun onStop() {}
  fun attach(activity: FlutterFragmentActivity, engine: FlutterEngine)
  fun onTrimMemory(level: Int) {}
  fun onNewIntent(intent: Intent) {}
  fun detach() {}
}
```

各平台卡在自身目录实现模块，`AndroidModules.kt` 只追加工厂一行；MainActivity 统一 configureFlutterEngine/生命周期/Intent 转发，销毁按逆序 detach；ActivityResult 注册在 STARTED 之前。AndroidManifest.xml 由 AND-02 唯一维护，新增能力提交声明片段与白名单差异，不由多卡同时改主体；ports_android.dart 每卡只替换自己的端口字段。（登记片段由聚合维护者单写合入，消费卡不直接写共享文件。）

AndroidChannelModule生命周期补充：唯一MainActivity在onCreate中构造无engine的模块列表，先逐个registerActivityResults(this)，再super.onCreate；configureFlutterEngine取得engine后逐个attach。注册只在前一个钩子中执行，固定键fml.<模块>.<动作>，attach禁止再次注册；所有注册均在STARTED之前。MainActivity转发onStart/onStop；onDestroy先逆序detach再super，模块取消异步工作、注销事件/回调，未完成MethodChannel请求以PLATFORM_IO结束一次。旋转配置处理不重建；系统实际重建时新Activity重建模块并重注册，禁止旧实例持有新Activity。该时序须以锁定FlutterFragmentActivity/AndroidX的M0编译启动探针证明；未通过保留阻断，不自行延后注册。进程死亡不承诺旧Future续接。

**实现约束**
- 绑定方式只用 C ABI + `dart:ffi`（ffigen 生成），不使用 flutter_rust_bridge（附录 A ADR-V5-02）。
- 原生库按 16 KB 内存页对齐（NDK r28 及以上默认；r27 显式开启 flexible page sizes，Rust 链接始终验证，旧版本加链接参数 `-Wl,-z,max-page-size=16384`），以兼容 16 KB 页设备。
- Release 构建开启 R8，`proguard-rules.pro` 保留 Flutter 与各 MethodChannel 处理类；`.so` 去除调试符号，符号文件另行归档（AND-11）。
- 构建可复现：`toolchain.versions` 中的版本即 CI 使用的版本；Rust 构建设置 `--remap-path-prefix` 与固定 `SOURCE_DATE_EPOCH` 为源提交Unix时间戳（git show -s --format=%ct HEAD）。
- 宿主锁版门槛：FlutterFragmentActivity须通过AND-02 ActivityResult注册的最小编译探针；当前仅官方主干源码核对，不声称项目兼容已实测。
- 外部前提：Android SDK、NDK、cargo-ndk、Gradle/AGP/Kotlin、CameraX 的具体版本由本卡按 ADR-V5-15 在 S0 写入 `toolchain.versions`，Flutter SDK 以 CORE-01 的 `app/.flutter-version` 为准；调试真机至少一台 arm64 设备。

**验收标准**：测试方案全文见 [Test/S0/S0_AND-01_TEST.md](../Test/S0/S0_AND-01_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 300 行（Gradle 脚本、MainActivity、入口与组装）；`app/android/`、`app/lib/main_android.dart`、`app/lib/composition/ports_android.dart`（同属 `app/` 构建单元）。

