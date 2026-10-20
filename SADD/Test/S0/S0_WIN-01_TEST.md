# WIN-01 测试方案

> 来源卡：[S0_WIN-01_基座.md](../../S0/S0_WIN-01_基座.md)（工程与构建）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R01] 在 Windows 10 1809 与 Windows 11 上运行 Release 构建，S0 阶段显示 CORE-04 冒烟页（ABI版本；runtime Unsupported时按CORE-04显示固定未实现提示，不读取不存在快照）；启动日志列出全部 11 个端口当前为 unsupported。
- [R18] 用 MAJOR+1 的核心库替换 `fmlcore.dll` 后启动，显示“核心版本不匹配，请重新安装”，不崩溃；删除 `fmlcore.dll` 后显示“核心组件加载失败，请重新安装”。
- [R19] DLL 劫持测试：在当前工作目录与 `%PATH%` 首个目录放置同名 `fmlcore.dll` 后从其他目录启动，Process Monitor 显示只加载了 exe 同目录中的 DLL。
- [R41] `app/lib/ui/` 中 `Platform.isWindows` 与平台判断零命中（CORE-41 规则）；Windows 专属 Dart 代码只在 `app/lib/platform/windows/`、`main_windows.dart` 与 `ports_windows.dart`。
- [R23] 两次干净构建得到的 `fmlcore.dll` 哈希一致；`dumpbin /dependents` 显示其不依赖 `vcruntime140.dll`。
