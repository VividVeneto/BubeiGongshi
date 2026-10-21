# CORE-24 测试方案

> 来源卡：[S6_CORE-24_扩展.md](../../core/S6_CORE-24_扩展.md)（游客转注册与游客并入）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R25] 故障注入：在每两个步骤之间杀进程，重启后 `resume_on_start` + `advance` 继续，最终状态一致；LocalCommitted 之前任一步失败或 `abandon` 后游客数据完整可用且可继续写入。
- [R28] LocalCommitted 后 `sync_outbox` 含全部用户公式、修订与复习事件各一次；`account_key_wrap` 只含恢复码 / 同步密语包装记录；outbox 与 `KeyOutput` 中没有 DbKey 与识别历史。
- [R26] 升级开始前游客期间无任何上传（Fake `HttpTransport` 审计）。

- [R28] 档案提交前/后、注册表投影前/后、registry_pending 清除前分别崩溃并重开：最终档案/注册表一致、首次 outbox 各一次，无已提交数据丢失；平台密钥不可用、档案未打开或ProfileSession无效时业务路由不开放；密钥可用即自动打开，不弹应用认证。
- [R28] load_account_keys/load_account_keys_tx读取相同account_id/epoch/版本升序全集；后者可见同事务未提交轮换，不另开快照、不跨档案/请求缓存，缺钥SYNC_KEY_MISSING；结束密钥清零。
- [R28] Commit注入registry枚举全部已注册存活实体及墓碑，现有ID/field_clock逐字不变；device设置/会话/参数/缓存/识别历史不入队。中途codec或入队故障回滚account_state/日志/outbox，重入LocalCommitted不重复首次队列；registry为原生参数，JSON不增字段。
- [R25] 放弃边界：Identity/NewKey/ExistingKey 各步后 `abandon` 成功，删除本次写入的 account_key 与 account_key_wrap、日志标记放弃、游客写入恢复；LocalCommitted 及之后 `abandon` 返回 `SYNC_UPGRADE_NOT_ABANDONABLE` 且状态不变。
- [R28] 密钥导入：`import_account_key` 用恢复码/同步密语在一个事务导入全部能解开的版本并返回最高版本（旧恢复码只导入旧版本）；kind 不符的记录跳过；一个也解不开返回 `SYNC_UPGRADE_KEY_FAILED` 且不写入；入参 account_id 与 account_state 不同返回 `SYNC_UPGRADE_STEP_INVALID` 且不写入；重复导入幂等。
- [R28] 轮换：`rotate_account_key` 返回 key_version = 原最大版本 + 1 与新 KeyOutput（key_version 一致、wrap_kind 为 recovery_code）；旧版本密钥与包装行保留，旧恢复码不能解包新版本；新版本包装行 uploaded=0、created_at_ms = now_ms。
- [R28] 同步密语包装：`wrap_with_passphrase` 对存在版本写 sync_passphrase 行（uploaded=0、created_at_ms = now_ms），用同一口令经 CORE-21 unwrap 得回原密钥；版本不存在 `SYNC_KEY_MISSING`；口令违反策略 `CRYPTO_PASSPHRASE_WEAK`；Fake rng 失败 `CRYPTO_RNG_FAILED` 且不写入。
- [R28] 错误逐码：每个 `SYNC_UPGRADE_*` 码至少一个触发用例，其中升级进行中业务写 op 返回 `SYNC_UPGRADE_IN_PROGRESS`、放弃或完成后恢复；NewKey 时 Fake rng 耗尽返回 `SYNC_UPGRADE_KEY_FAILED`、last_error 为 `CRYPTO_RNG_FAILED`，日志不回退且恢复 rng 后重试可继续；`begin`、`rotate_account_key`、`wrap_with_passphrase` 的 rng 失败直接透传 `CRYPTO_RNG_FAILED` 且不写入。
- [R28] 时间与 ID：`begin` 的 journal.id 为由 Fake rng 字节确定的 UUID-v4，started_ms = updated_ms = now_ms；每次 advance/abandon 只以传入 now_ms 更新 updated_ms，核心不读时钟（同输入两次运行结果逐字节相同）。
- [R19] op 形状：本卡各 FFI op 的请求/响应（含 now_ms、KeyOutput.key_version）与 manifest 登记和文内示例往返一致；upgrade_advance、import/rotate/wrap_with_passphrase 走 submit，begin/status/abandon 走 call。
