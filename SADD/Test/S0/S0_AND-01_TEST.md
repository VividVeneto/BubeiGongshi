# AND-01 测试方案

> 来源卡：[S0_AND-01_基座.md](../../S0/S0_AND-01_基座.md)（工程与构建）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R01] 在 arm64 真机安装调试包，S0 阶段启动后显示 CORE-04 冒烟页，行为按 CORE-04 `smokeEntry`：显示 ABI 版本；runtime 仍为 Unsupported 时显示固定“运行时信息待平台卡实现”、不崩溃，替换为真实端口后显示快照；启动日志列出全部 11 个端口当前为 unsupported。
- [R18] 用 MAJOR+1 的核心库替换 `jniLibs` 中的 `libfmlcore.so` 后安装，应用显示“核心版本不匹配，请重新安装”，不崩溃。
- [R41] `app/lib/ui/` 中 `Platform.isAndroid` 与平台判断零命中（CI 规则由 CORE-41 执行）；Android 专属 Dart 代码只在 `app/lib/platform/android/`、`main_android.dart` 与 `ports_android.dart`。
- [R23] 两次干净构建得到的 `libfmlcore.so` 哈希一致；`llvm-readelf -l` 显示所有 LOAD 段对齐为 0x4000。
