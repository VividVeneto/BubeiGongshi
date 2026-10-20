# AND-06 测试方案

> 来源卡：[S2_AND-06_平台.md](../../and/S2_AND-06_平台.md)（本地存储与 Keystore）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R27] CORE-04 的 `SecureKeyValueStore`、`LocalFileStore` 契约套件在真机（`integration_test/android/storage_test.dart`）全部通过。
- [R27] 手动：执行 `adb shell bmgr backupnow <package>` 与设备迁移后，新设备上不存在 `database/`、`recognition/`、`drafts/` 内容。
- [R27] 在支持 StrongBox、仅 TEE、模拟器三类设备上 `securityLevel` 分别返回 `strongBox`、`tee`、`software`。
- [R27] 篡改 `wrap` 结果中任一字节后 `unwrap` 抛 `PLATFORM_KEY_UNAVAILABLE`。
