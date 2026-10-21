# CORE-96 测试方案

> 来源卡：[S4_CORE-96_功能.md](../../core/S4_CORE-96_功能.md)（在线资源包信任元数据适配）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**
- [R30] 元数据：过期 timestamp 返回 `PACK_METADATA_EXPIRED` 且已安装包可用；snapshot 版本回退返回 `PACK_EPOCH_ROLLBACK`。
- [R30] 本机时间早于last_seen_ms超过24h暂停更新；TUF timestamp有效期≤7天；验证失败已安装内容可用，不得提升水位或发布Offer。
- [R30] 锁定tough后用可运行fixture与官方源码核实load/expiration/datastore/可注入时钟及逐版root轮换，验证签名链、角色版本防回退与过期拒绝；M0未闭合不得标自动通过，不关过期检查或自研TUF绕过。
- [R30] pack.check_updates正确base64解码四角色，经CORE-95原子单调持久化SecurityState后返回Offer；check_updates调用点与处理仅本卡所有，不重复登记于95。
