# WIN-03 测试方案

> 来源卡：[S7_WIN-03_发布.md](../../win/S7_WIN-03_发布.md)（自更新客户端）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R23] 手动：从 1.0.0 经设置页更新到 1.1.0，数据与设置保留；下载中断网后恢复，续传完成且哈希一致。
- [R19] 故障注入：篡改安装包一个字节 → `PLATFORM_UPDATE_HASH_MISMATCH` 且文件被删除；用另一证书签名的安装包 → `PLATFORM_UPDATE_SIG_INVALID`；以 `--dart-define=FML_TEST_BUILD=true --dart-define=FML_TEST_CRASH_ON_FIRST_START=true` 构建的新版本首启退出 → 启动器回滚，旧版本启动并显示“更新失败，已恢复到 1.0.0”，数据库可打开。
- [R27] 回滚后 `database\` 的文件哈希与更新前备份一致。
- [R26] 游客检查更新的请求不含 `Authorization` 头与设备标识（抓包验证）。
- [R23] 连续 3 次更新后 `%LOCALAPPDATA%\Programs\BubeiGongshi\` 下只保留 2 个 `app-*` 目录。
- [R23] 启动器子进程挂起时 confirmHealthy/confirmOpened 在 1.5 s 内返回，每次启动各至多调用一次；管道内容不符或服务端 PID 不符时不退出并显示 PLATFORM_IO；Inno 失败后下次启动显示更新失败且 update-failed.txt 被删除。
