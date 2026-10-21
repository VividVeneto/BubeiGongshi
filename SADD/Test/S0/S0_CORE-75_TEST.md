# CORE-75 测试方案

> 来源卡：[S0_CORE-75_基座.md](../../S0/S0_CORE-75_基座.md)（共享写入点预分配门禁）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18] 正例预分配通过；同kind重复key、未知owner、非法route/order、未知字段/版本退出1；坏JSON/文件缺失退出2。
- [R18] actual只含已预分配子集通过且mode=implementation；相同key改owner/point或新增未分配项失败；不带actual时只输出design。
- [R18] startup/profile/firstFrame/settings各自成序列；跨序列同order可并存，profile内部重复或非规范/越界order失败。六项档案钩子迁至profile与ProfileHooks，错报startup或旧point的actual必须失败；design预分配不冒充真实构建回执。
