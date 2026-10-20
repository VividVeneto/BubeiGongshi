# CORE-04 测试方案

> 来源卡：[S0_CORE-04_基座.md](../../S0/S0_CORE-04_基座.md)（平台端口契约）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R01] `app/test/ports/contract/` 下每个端口的契约套件对 Fake 实现通过；AND、WIN 卡用同一套件在真机上跑通各自实现。
- [R41] 两端实现分别位于 `app/lib/platform/android/` 与 `app/lib/platform/windows/`；`tools/ci/check_deps.py` 验证用例与 UI 不 import 平台目录。
- [R19] `FeatureRegistry` 同类型重复登记抛 `StateError`；`startupHooks` 按 order 稳定排序。
- [R18] `runPlatformApp` 注入返回 MAJOR+1 的假绑定时显示 `CoreUnavailableScreen(abiMismatch)` 且 `buildPorts` 未被调用；注入抛 `ArgumentError` 的 `open` 时显示 `loadFailed`。
- [R19] 构造 `LocalTime(24, 0)`、`pick(maxCount: 0)`、`pick(maxCount: 11)` 均抛 `ArgumentError`；过期 `ImportedImage` 的 `readBytes` 抛 `PLATFORM_IO`；`FakeHttpTransport` 对未预置请求抛 `StateError`（测试夹具缺失，不冒充网络策略错误）。
- [R20] 错误码表中每个 `PLATFORM_*`、`NET_*` 码都在 `registry.yaml` 中且有中文消息键。
- [R01] Widget 测试：`smokeEntry` 在 Fake `RuntimeInfo.snapshot` 抛 `PLATFORM_UNSUPPORTED` 时显示 ABI 版本与固定文案“运行时信息待平台卡实现”、无异常；返回快照时显示快照字段。

- [R27] LocalFileStore契约套件：私有子目录排除成功；兄弟目录、../越界、指向外部的符号链接（平台支持时）抛ArgumentError且目标不变；Fake与真实端口相同。

- [R19] 安装点夹具A返回未完成Future、B读取A登记值：A未完成时B不执行，A完成后按顺序执行B；A失败则compose失败且不发布AppDeps，不运行后续安装点；同步安装点亦保持既定顺序。
