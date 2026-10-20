# AND-14 测试方案

> 来源卡：[S3_AND-14_平台.md](../../and/S3_AND-14_平台.md)（剪贴板与公式多格式复制）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R08] 仪器测试：以 CORE-52 夹具负载 `write` 后读回主剪贴项：描述含 text/plain、text/html、image/png，`coerceToText` 为 LaTeX 源码，`htmlText` 等于负载 html，URI 可经 `ContentResolver` 读出与负载相同的 PNG；连续复制两次后 `cacheDir/clip/` 只剩 1 个文件；“复制为图片”只有 image/png。
- [R08] 手动矩阵（结果记入附录 D）：“复制公式”后在系统便签/备忘录粘贴得到 LaTeX 或图片、在微信输入框粘贴得到 LaTeX 文本、“复制为 → 图片”后在支持图片粘贴的聊天应用得到公式图片。
- [R08] 单元测试：长度已知 20 MiB+1 的图片直接抛 `PLATFORM_FILE_TOO_LARGE`；长度未知的流复制到 20 MiB+1 字节即停止、删除副本并抛同一码；GIF、HEIC、SVG 返回 `PLATFORM_UNSUPPORTED`；PNG 的 MIME 按实际解码结果为 image/png，扩展名改为 .jpg 也不变。
- [R01] CORE-04 ClipboardAdapter契约套件通过；读取无图片返回null，下一次readImage即结束上一批，已复制到业务staging的文件不被清理。
