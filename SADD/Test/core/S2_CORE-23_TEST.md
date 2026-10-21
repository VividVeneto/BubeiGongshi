# CORE-23 测试方案

> 来源卡：[S2_CORE-23_账户.md](../../core/S2_CORE-23_账户.md)（账户状态、登录边界与本机解锁）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R27] 注册表版本域：只含registry/0023与档案0023的夹具分别打开，断言表与schema_migration/user_version完全隔离；新增低序号补执行不降低最大版本；注册表已执行SQL改名/改字节→STORE_MIGRATION_FAILED，文件缺失/更高版本→STORE_SCHEMA_TOO_NEW；注入迁移中途失败验证无部分DDL或版本提交，不发布Unlocked。不把空库重建当成受损注册表恢复。profile_commit_id确实存在且不出现在Profile wire。
- [R27][R28] RandomIds使用固定SecureRandom，逐字节断言16字节输入只修改UUID-v4 version/variant位、每次恰一次fill、连续请求按固定序列产生ID；失败源原样CRYPTO_RNG_FAILED且无重试。Store::open注入同一提供器：新库初始化device_id，已有库打开不消耗ID，后续op_id/rotate才消耗；提供器零/非法版本/重复ID由CORE-13拒绝并回滚；生产适配无其他OS随机入口。account.open_profile注入失败不留开放handle、不发布Unlocked，JSON无ids/rng字段。
- [R25][R28] account.create_guest/create_registered与open_profile的FFI错误集合包含CRYPTO_RNG_FAILED；平台熵源失败时没有部分注册表/时钟/outbox记录，不返回或持久化全零密钥。
- [R24] 状态机单元测试：Uninitialized 下调用任何业务 op 返回 `AUTH_NO_PROFILE`；RegisteredLocked 下返回 `AUTH_LOCKED`；首次启动只显示账户入口（与 CORE-36 集成测试）。
- [R24] 注册流程（Fake `HttpTransport` 模拟 CORE-22/45）：获取验证码 → 注册（201 `{ account_id }`，响应中无授权码与令牌）→ 授权码 + PKCE 登录 → 换令牌 → 生成注册档案；刷新令牌在 `profile_blob` 中只以包装密文存在。
- [R25] 游客创建后全部本地功能可用；同一系统用户第二次创建游客返回 `AUTH_GUEST_EXISTS`。
- [R26] 游客状态网络白名单测试：Fake `HttpTransport` 记录全部请求，只有用户显式触发的资源包下载与更新检查，且请求不含用户内容（与 CORE-28 守卫联测）。
- [R28] 注册后默认不开启同步，用户确认开启后才产生上传请求。
- [R27] 登出后数据库已关闭、密钥已清零、`profile.logged_out` 为真，重启后停在账户入口；重新登录可打开；删除本地数据需二次确认后才执行；游客档案重启后自动打开。
- [R28] OsRandom：对两次 `fill` 返回不同字节（概率检查）；注入平台失败的替身时返回 `CRYPTO_RNG_FAILED`，且不产生全零输出；`fml-crypto` 依赖图不含 `getrandom`（CORE-21 检查），`getrandom` 只出现在 `fml-store`。
