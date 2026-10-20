# CORE-51 测试方案

> 来源卡：[S4_CORE-51_界面.md](../../core/S4_CORE-51_界面.md)（资源包下载、导入与管理界面）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R30] `FakeHttpTransport` 提供元数据与包文件夹具：`checkUpdates` 返回 4 个课程包报价；`download` 依次产生 `PackDownloading` → `PackInstalling` → `PackDone`，之后 `installed()` 含该包且再次检查不再报价同版本。
- [R30] 续传：传输层在一半字节处抛 `NET_OFFLINE` → 状态 `PackFailed(resumable: true)`；再次下载的请求 `rangeStart` 等于已收字节，安装成功。
- [R29] `importFile` 导入篡改过的 `.fmlpack` 返回 `PACK_SIG_INVALID`，原已装版本仍在 `installed()` 中，暂存文件被删除。
- [R39] 筛选“高中”时可见 `content-high-school-math` 与 `content-high-school-physics`，筛选“大学 + 物理”只见 `content-university-physics`。
- [R26] 游客档案下完成检查与下载：`FakeHttpTransport` 记录的请求均为 `packBase` 主机、用途为 `updateCheck` 或 `packDownload`、无 `Authorization` 头。
- [R29] `freeBytes` 小于阈值时 `download` 直接返回 `PackFailed('PACK_STORAGE_LOW')`，未发出请求。
