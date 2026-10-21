# CORE-23 测试方案

> 来源卡：[S2_CORE-23_账户.md](../../core/S2_CORE-23_账户.md)（账户状态、登录边界与本机解锁）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R27] 注册表版本域：只含registry/0023与档案0023的夹具分别打开，断言表与schema_migration/user_version完全隔离；新增低序号补执行不降低最大版本；注册表已执行SQL改名/改字节→STORE_MIGRATION_FAILED，文件缺失/更高版本→STORE_SCHEMA_TOO_NEW；注入迁移中途失败验证无部分DDL或版本提交，不发布Unlocked。不把空库重建当成受损注册表恢复。profile_commit_id确实存在且不出现在Profile wire。
- [R27][R28] RandomIds使用固定SecureRandom，逐字节断言16字节输入只修改UUID-v4 version/variant位、每次恰一次fill、连续请求按固定序列产生ID；失败源原样CRYPTO_RNG_FAILED且无重试。Store::open注入同一提供器：新库初始化device_id，已有库打开不消耗ID，后续op_id/rotate才消耗；提供器零/非法版本/重复ID由CORE-13拒绝并回滚；生产适配无其他OS随机入口。account.open_profile注入失败不留开放handle、不发布Unlocked，JSON无ids/rng字段。
- [R25][R28] account.create_guest/create_registered与open_profile的FFI错误集合包含CRYPTO_RNG_FAILED；平台熵源失败时没有部分注册表/时钟/outbox记录，不返回或持久化全零密钥。
- [R24] 状态机单元测试：Uninitialized 下调用任何业务 op 返回 `AUTH_NO_PROFILE`；RegisteredLocked 下返回 `AUTH_LOCKED`。account_state 规则逐格：省略 profile_id → uninitialized；未打开且未登出的游客/注册档案 → uninitialized；logged_out=true 的注册档案 → registered_locked；本进程开放 handle 的游客/注册档案 → guest_unlocked/registered_unlocked。首次启动只显示账户入口与 Guard 映射由 CORE-36 验收，本卡不测 Dart。
- [R24] 注册档案（Rust 层，固定 SecureRandom 注入 SqliteRegistry）：create_registered 返回的 profile_id/db_key 逐字节等于固定序列；以 kind=refresh_token put_blob 后注册表 profile_blob 只含传入的包装字节，表中无明文列。同一 account_id 再建 → AUTH_PROFILE_EXISTS 且 args.profile_id 为既有档案、响应无 db_key、rng 未被消耗、注册表行数不变。注册/验证码/PKCE 网络流程归 CORE-65 验收。
- [R25] 游客创建后可 open_profile 并读写 local_setting；同一系统用户第二次创建游客返回 `AUTH_GUEST_EXISTS`（部分唯一索引兜底，绕过检查直插亦被拒）。
- [R26] 游客网络白名单（Fake HttpTransport 记录请求）归 CORE-28/CORE-36 联测；本卡只断言游客档案的 account.state=guest_unlocked、Profile.account_id/email_masked 缺省省略，作为映射输入。
- [R28] 同步开关：create_* 后 Profile.sync_enabled=false；account.set_sync_enabled(true) 后 profiles 返回 true、重开仍为 true；信封 handle 与 body.profile_id 不一致 → FFI_BAD_ARG，未打开/已登出 → AUTH_NO_PROFILE/AUTH_LOCKED。“用户确认后才上传”归 CORE-26/CORE-65。
- [R27] 登出：set_logged_out(true)+close_profile(lock=true) 后 handle 失效、Store 已关闭、DbKey 缓冲已清零（Zeroizing 替身计数）、logged_out=true；模拟在 close 前崩溃（只落 logged_out）后重启仍为 registered_locked；重新 open_profile 可打开。启动选择：touch_last_used 以注入时间更新，last_used 取最大且 deleting=0，NULL 最旧，已登出注册档案不自动打开、游客档案自动打开。
- [R27] 删除档案：开放 handle 时 delete_profile → STORE_BUSY 且行/文件/blob 均不变；关闭后删除 → db 文件、-wal/-shm、backup_dir、profile_blob 与 profile 行全部消失，再调用 → AUTH_NO_PROFILE；在③注入文件删除失败 → STORE_BUSY 且 deleting=1、profiles 不列出、其他 op 返回 AUTH_NO_PROFILE，重调或重新 SqliteRegistry::open 补完删除；未登记的库文件不被删除。二次确认与平台别名删除归 CORE-65。
- [R27] 投影恢复接缝：NoRecovery 下 open_profile/account_state 从不返回 upgrading_guest；注入 Fake ProjectionRecovery 返回 Some(upgrading=true) → 注册表行的 account_id/email_masked/profile_commit_id 按投影覆盖、projected 恰调用一次、状态为 upgrading_guest；重复打开同值覆盖幂等；注册表写失败或 projected 失败 → Store 关闭、无 handle、错误原样返回。
- [R27] 错误与边界：AUTH_SETTING_INVALID 覆盖 "24:00"、"7:5"、"12:60"、""、"07:05 "，"00:00"/"23:59" 通过；put_blob/get_blob 1 字节与 65536 字节往返逐字节相等，0 字节与 65537 字节在 schema 层 FFI_BAD_ARG；db_key 解码非 32 字节、email_masked 0 或 255 字符 → FFI_BAD_ARG；open_profile 库内 account_state.profile_id 与请求不符 → STORE_CORRUPT 且无 handle；已打开同档案再 open → STORE_BUSY；进程重启后旧 handle 返回 FFI 句柄错误。全部 ready op 的 manifest error_codes 与本卡 FFI 错误镜像逐项相等。
- [R28] OsRandom：对两次 `fill` 返回不同字节（概率检查）；注入平台失败的替身时返回 `CRYPTO_RNG_FAILED`，且不产生全零输出；`fml-crypto` 依赖图不含 `getrandom`（CORE-21 检查），`getrandom` 只出现在 `fml-store`。
