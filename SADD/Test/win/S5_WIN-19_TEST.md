# WIN-19 测试方案

> 来源卡：[S5_WIN-19_平台.md](../../win/S5_WIN-19_平台.md)。

**验收标准**
- [R37] 拖入 3 张图片与 1 个 txt：识别页进入裁剪，提示跳过 1 个非图片文件；拖入含 200 张图片的文件夹先显示数量与大小确认框，取消后无副本产生。
- [R31] 拖入 25 MiB 图片：不复制，`readBytes` 抛 `PLATFORM_FILE_TOO_LARGE` 并提示；导入 1200 万像素 JPEG 期间界面无超过 100 ms 的帧卡顿（DevTools 时间线）。
- [R36] drop导入完成/到期仅清本批目录，picker与clipboard活动批次仍可读；源文件hash/mtime不变。交错init/清理、重复订阅与无订阅拖放均不复制多余文件。
- [R37] 扫描只一层、不跟随符号链接/连接点；确认回调缺失视取消，零图片批次仍发送跳过计数但不进入识别。
- [R37] 同时注册files与drop：选择/copyImage仍走WIN-04 handler，scanFolder及dropped只走drop；拖入与选择器交错无覆盖/重复回复，detach后无事件或悬空delegate。
