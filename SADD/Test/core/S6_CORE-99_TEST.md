# CORE-99 测试方案

> 来源卡：[S6_CORE-99_扩展.md](../../core/S6_CORE-99_扩展.md)（游客升级网络协调）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**

- [R25][R28] 安装与登记：sessions/account/keys/sync/secureKeys 齐全时构造 DefaultUpgradeCoordinator 并以 UpgradeCoordinator/UpgradeFacade 登记同一实例；任一依赖缺失只登记 DisabledUpgradeFacade 且不抛错；ProfileHooks order30 id `upgrade.resume` 对每新 handle 执行一次 `resumeIfPending`，session 为 null 时跳过，顺序 30 先于 70 且不另造 StartupHook。
- [R25][R28] 两条路径步进顺序：Fake CORE-24/65/83/98/46 下，newAccount 为 `begin → askCredentials → registerForUpgrade → advance(identity) → advance(new_key) → confirmSaved → keys.uploadWrapRecord → advance(key_uploaded) → advance(commit) → done`；mergeInto 为 `begin → loginForUpgrade → advance(identity) → keys.fetchRecords + askSecret → advance(existing_key) →（本机已有该 account_id 档案→account.upgrade_merge，否则 advance(commit)） → done`；合并时断言 `target_db_key` 取自 `secureKeys` 别名 `fml.<target_profile_id>.db`、随调用交出后字节副本清零且不写日志，别名缺失时以 CORE-04 错误上抛且不调用 `account.upgrade_merge`；断言 `askCredentials`/`askSecret` 缺省时 run 抛 StateError，`confirmSaved=false` 时不推进 `key_uploaded`、不上传包装。
- [R25][R28] 会话屏障：A→closing/null→B（含同 profileId 不同 handle）逐步设 await 屏障，迟到的 confirmSaved/秘密/推进结果不写 B 的 journal、不向 B 上传包装、不触发 B 的 `syncNow(afterUpgrade)`；宿主关闭或会话过代时四类用户回调立即以 false/null 完成，`stopAndDrain` 不无限等待用户输入。
- [R25][R28] resumeIfPending 三态：session 为 null / 无日志 / step 已 Done → `none`；Prepared、IdentityReady → `needsUser` 且不自动推进、不解除写门；KeyReady → 用 CO-47-01 变更单提出的待上传包装记录 op 取 `uploaded=0` 的 `recovery_code` 补传后 `advance(key_uploaded)`→`advance(commit)`→`completed`，本地已提交（第 4 步）→ `advance(commit)`→`completed`；`advance(new_key)` 返回 `SYNC_UPGRADE_STEP_INVALID` 时只补传已存包装，断言未生成新密钥、未删除既有包装。
- [R25][R28] 失败与取消：在每步网络调用前后注入错误，升级失败后 journal 与写门保持、游客数据仍可读、业务写返回 `SYNC_UPGRADE_IN_PROGRESS`，重启后 order30 能续接；`abandonPending` 在第 4 步之前成功、之后返回 `SYNC_UPGRADE_NOT_ABANDONABLE`（不离开写门、不删日志）、step Done 时为 no-op 且不报错。
- [R25][R28] 开启同步唯一发生点：Done 后 `sync_enabled` 未为真且回调存在时询问至多一次，返回 true 时断言 `setEnabled(true)` 先于 `syncNow(SyncTrigger.afterUpgrade)`；`syncNow` 失败只记录 `SyncStatus.lastErrorCode`，升级仍为完成；`sync_enabled` 已为真或回调缺省时不询问；CORE-65 `register(promptEnableSync:false)` 路径不出现第二次询问。
- [R28] 两台设备（同一进程内两个档案 + `fake_sync_server`）：设备 A 升级为注册并开启同步，设备 B 登录后用恢复码 `restoreOnNewDevice`，同步后公式与复习事件一致；服务端替身中只有包装记录与密文。
- [R28] 安装顺序 98→46→99，CORE-36 门面/端口定义不迁入；order70 常规同步仍归 CORE-46，断言 CORE-46 不反向 import 升级协调器，本卡不直接持有 ApiClient 或自写 keys 端点。
