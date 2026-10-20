# AND-05 测试方案

> 来源卡：[S2_AND-05_平台.md](../../and/S2_AND-05_平台.md)（生命周期、进程恢复与运行时信息）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R27] 集成测试（`integration_test/android/lifecycle_test.dart`）：在 `/library` 路由下用 `adb shell am kill <package>` 杀进程（应用在后台），重新打开后回到 `/library`。
- [R03] `adb shell am send-trim-memory <package> RUNNING_LOW` 后 `events()` 收到一次 `lowMemory`，10 s 内重复发送不再收到；应用不崩溃。
- [R01] CORE-04 的 `AppLifecycle` 与 `RuntimeInfo` 契约套件在真机通过；`snapshot()` 的 `osVersion` 等于 `Build.VERSION.SDK_INT`，`abi` 为 `arm64-v8a`。
- [R08][R42.e] 手机与平板横竖屏切换、折叠屏展开/折叠与分屏调整时 Activity 不重建（Kotlin 侧 `onCreate` 计数不变），当前路由保持。
- [R42.e] 开发者选项“不保留活动”开启后，在 `/library` 切到后台再返回，Activity 重建（`onCreate` 计数加 1）且回到 `/library`。
