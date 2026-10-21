# CORE-24 测试方案

> 来源卡：[S6_CORE-24_扩展.md](../../core/S6_CORE-24_扩展.md)（游客转注册与游客并入）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R25] 故障注入：在每两个步骤之间杀进程，重启后 `resume_on_start` + `advance` 继续，最终状态一致；LocalCommitted 之前任一步失败或 `abandon` 后游客数据完整可用且可继续写入。
- [R28] LocalCommitted 后 `sync_outbox` 含全部用户公式、修订与复习事件各一次；`account_key_wrap` 只含恢复码 / 同步密语包装记录；outbox 与 `KeyOutput` 中没有 DbKey 与识别历史。
- [R26] 升级开始前游客期间无任何上传（Fake `HttpTransport` 审计）。

- [R28] 档案提交前/后、注册表投影前/后、registry_pending 清除前分别崩溃并重开：最终档案/注册表一致、首次 outbox 各一次，无已提交数据丢失；平台密钥不可用、档案未打开或ProfileSession无效时业务路由不开放；密钥可用即自动打开，不弹应用认证。
- [R28] load_account_keys/load_account_keys_tx读取相同account_id/epoch/版本升序全集；后者可见同事务未提交轮换，不另开快照、不跨档案/请求缓存，缺钥SYNC_KEY_MISSING；结束密钥清零。
- [R28] Commit注入registry枚举全部已注册存活实体及墓碑，现有ID/field_clock逐字不变；device设置/会话/参数/缓存/识别历史不入队。中途codec或入队故障回滚account_state/日志/outbox，重入LocalCommitted不重复首次队列；registry为原生参数，JSON不增字段。
