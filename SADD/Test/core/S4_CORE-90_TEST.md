# CORE-90 测试方案

> 来源卡：[S4_CORE-90_界面.md](../../core/S4_CORE-90_界面.md)（提醒设置与自建书编辑界面）。本文件是该卡“验收标准”字段的全文；修改功能时同步更新。工具自“**验收标准**”行起拼回卡片。

**验收标准**
- [R04][R04.i] 提醒：开启并选 21:30 后 `FakeNotificationScheduler` 记录 21:30 的提醒且 `device.reminder_time` 为 21:30；权限被拒时开关回到关闭、设置未写入。
- [R04][R04.j] 自建书：新建 3 章（含一个二级章）、加入 20 个条目后保存，`study.books.create` 收到的章节树与条目一致；第 5 层章节被拒；删除书后条目仍在公式库。
- [R04][R04.i] Widget 测试：登记返回两项（一项未通过且 `canFix`）的测试用 `ReminderSelfCheck` 时入口出现，点“去设置”调用 `openFix`；未登记时入口不出现。
- [R04][R04.i] ReminderSelfCheck的ok显示正常、warn才标红，unknown用中性信息并显示detail/可选设置入口，不把未知状态当配置错误；返回前台后重新检查。
