# CORE-99 测试方案

> 来源卡：[S6_CORE-99_扩展.md](../../core/S6_CORE-99_扩展.md)（游客升级网络协调）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**
- [R28] 两台设备（同一进程内两个档案 + `fake_sync_server`）：设备 A 升级为注册并开启同步，设备 B 登录后用恢复码 `restoreOnNewDevice`，同步后公式与复习事件一致；服务端替身中只有包装记录与密文。
- [R25] 升级故障注入：在每一步网络调用前后让替身返回错误，重启后 `resumeIfPending` 继续，最终完成；失败期间游客数据可用。
- [R25] NewAccount confirmSaved=false不推进KeyUploaded；MergeInto缺askSecret拒绝，导入目标账户包装后再Commit；失败日志保留与游客可用，重启order30续接、完成后询问开启同步并调用afterUpgrade。
- [R28] 安装顺序98→46→99，CORE-36门面/端口定义不迁；order70常规同步仍归46，46不反向import升级协调器。
