# CORE-75 测试方案

> 来源卡：[S0_CORE-75_基座.md](../../S0/S0_CORE-75_基座.md)（共享写入点预分配门禁）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18] 正例预分配通过；同kind重复key、未知owner、非法route/order、未知字段/版本退出1；坏JSON/文件缺失退出2。
- [R18] actual只含已预分配子集通过且mode=implementation；相同key改owner/point或新增未分配项失败；不带actual时只输出design。
- [R18] startup/profile/firstFrame/settings各自成序列；跨序列同order可并存，profile内部重复或非规范/越界order失败。六项档案钩子迁至profile与ProfileHooks，错报startup或旧point的actual必须失败；design预分配不冒充真实构建回执。
- [R18] point 形式可校验：error 条目的 point 必须为 contracts/errors/registry.yaml；file 与 installer 为仓库相对路径；shortcut/startup/firstFrame/settings/profile 为 Class 或 Class.member；profile 的 point 必须逐字为 ProfileHooks，形近拼写、大小写错误、空串、含空白或 .. 均退出1并与预分配不符时报 EXT-4。
- [R18] route 父子前缀与归属：现存 /study 与 /study/stats、/settings 与 /settings/appearance、/library 与 /library/new 的分属不同 owner 时通过（本卡不要求跨 owner 前缀互异，不得实现成前缀全互异）；同一 route key 委派两个 owner 失败；参数段重命名（/a/:x 与 /a/:y）按重复失败；回执按最长前缀匹配、同长度取静态段，/libraryx 不匹配 /library，根 / 只匹配自身。
- [R18] stdout 与退出码契约：stdout 恰为 {mode, entries, errors} 的 JSON；不给 --actual 时 mode 为 design，给出时为 implementation；违约时退出1且 stdout 仍为合法 JSON；policy 或 actual 不可读、JSON 损坏时退出2，stderr 含 EXT-INPUT: 且不输出半份结构。
