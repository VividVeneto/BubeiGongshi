# WIN-07 测试方案

> 来源卡：[S2_WIN-07_平台.md](../../win/S2_WIN-07_平台.md)（本地存储与 DPAPI）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R27] CORE-04 的 `SecureKeyValueStore`、`LocalFileStore` 契约套件（`integration_test/windows/storage_test.dart`）全部通过；`securityLevel` 返回 `dpapi`。
- [R27] 把数据目录复制到另一 Windows 用户下运行，`unwrap` 抛 `PLATFORM_KEY_UNAVAILABLE`，应用提示且不崩溃；篡改包装结果任一字节同样抛该码。
- [R27] `icacls "%LOCALAPPDATA%\BubeiGongshi"` 只列出当前用户与 SYSTEM，且无继承项。
- [R27] 设置页显示“安全说明”区，包含上述各项说明。
