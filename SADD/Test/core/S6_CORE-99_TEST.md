# CORE-99 测试方案

> 来源卡：[S6_CORE-99_扩展.md](../../core/S6_CORE-99_扩展.md)（游客升级网络协调）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**

- [R25][R28] 安装构造 DefaultUpgradeCoordinator 并将同一实例登记两门面；ProfileHooks order30 对每新 handle resumeIfPending 一次，null 不执行，进程/首帧动作不重复；顺序30先于70而非另造普通 StartupHook。
- [R25] Fake 对登录/注册、confirmSaved、askSecret、GET包装/PUT包装、每步 advance/merge 与 Done 后询问逐一设置 await 屏障。A→closing/null→B（含同 profileId 不同 handle）后迟到确认/秘密不能推进步骤、上传、Commit 或触发 B 的 syncNow(afterUpgrade)；未完成用户弹窗的回调撤销不阻塞关闭，迟到秘密字节清零。
- [R25] MergeInto 断言来源信封为 A guest handle，目标仅 CORE-24/83 私有迁移能力，ProfileSessionSource 不发布目标；目标打开成功后分别注入成功/异常/取消，必须收到关闭与密钥清零确认才允许来源关闭。跨库失败保留目标幂等 journal，不宣称原子回滚，不丢游客数据。
- [R25][R28] 关闭先启动全部停止前缀再 await；在途核心事务/目标关闭/清零失败保持 closing/null、不 close A/open B。已提交日志阶段不退回，原档案再次打开才恢复。Done 后只有仍 current 的完成档案可询问开启同步并 syncNow(SyncTrigger.afterUpgrade)；交互 handle 已换时旧 run 停止，由新 handle 恢复/确认接续；DisabledSyncFacade 不把已完成升级改失败。
- [R28] 两台设备（同一进程内两个档案 + `fake_sync_server`）：设备 A 升级为注册并开启同步，设备 B 登录后用恢复码 `restoreOnNewDevice`，同步后公式与复习事件一致；服务端替身中只有包装记录与密文。
- [R25] 升级故障注入：在每一步网络调用前后让替身返回错误，重启后 `resumeIfPending` 继续，最终完成；失败期间游客数据可用。
- [R25] NewAccount confirmSaved=false不推进KeyUploaded；MergeInto缺askSecret拒绝，导入目标账户包装后再Commit；失败日志保留与游客可用，重启order30续接、完成后询问开启同步并调用afterUpgrade。
- [R28] 安装顺序98→46→99，CORE-36门面/端口定义不迁；order70常规同步仍归46，46不反向import升级协调器。
