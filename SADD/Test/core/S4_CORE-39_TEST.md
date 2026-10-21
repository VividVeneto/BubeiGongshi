# CORE-39 测试方案

> 来源卡：[S4_CORE-39_界面.md](../../core/S4_CORE-39_界面.md)（学习会话界面）。本文件是该卡“验收标准”字段的全文；修改功能时同步更新。工具自“**验收标准**”行起拼回卡片。

**验收标准**
- [R42.b] Widget 测试：`Asking` 选择题中 `FmlCommands.invoke('study.option2')` 等同点击 B 并提交；`ShowingFeedback` 中 `invoke('study.primary')` 进入下一题；`SelfRating` 中 `isAvailable('study.option1')` 为 false 且 `invoke` 返回 false、状态不变。
- [R04][R04.d] 预置 `Feedback`（判错，`will_reappear = true`）后显示标准答案与重现提示，`next()` 后显示下一条 `Ask`。
- [R04][R04.e] 收到 `StartDictation` 后进入默写页，逐题作答后一次提交 `DictationDone`，收到 `Finished` 显示小结（首次正确数、重现数、默写错题）。
- [R04][R04.f] 题干显示考试标签。
- [R04][R04.g] 反馈 `related` 含 2 条易混公式时，反馈页列出两条并可跳转详情。
- [R04][R04.h] 点“记错了”调用 `study.appeal` 一次并显示更正提示；Undetermined 时进入自评页，选择后发送 `SelfRated`。
- [R04] 跳过、暂停、续学：暂停后切到后台 10 min 再恢复，`duration_ms` 不含暂停时长；`STUDY_SESSION_EXPIRED` 进入过期页。
- [R06] `AnswerInputRegistry`：未注册 Handwriting 时 `resolve(handwriting)` 返回 Input 实现并带提示；注册 Fake 手写实现后返回该实现。
- [R42.a][R42.c] Widget 测试：`Asking`、`ShowingFeedback`、`SelfRating` 各状态中 `FmlButtonVariant.primary` 至多 1 个；判错反馈以 `VerdictBanner` 显示且无 `Dialog`；登记 Fake `UiFeedbackSink` 后判对、判错各收到一次 `correct`、`wrong`。
- [R42.b][R42.e] Widget 测试：手机竖屏（宽 390）时主操作位于屏幕下 40% 区域；矮高度（800×400）时题干在左、作答区与主操作在右，主操作无需滚动即可点到。
- [R42.e][R42.b] 页面接入验收（Fake CoreBinding、Fake AnswerInputRegistry）：Asking公式输入题已输入v^2、光标在末尾，360×800↔800×360往返3次，SessionVm和页面State同一对象，index、输入、光标不变，计时不重置，不发study.session.*；textScaler 2.0下Asking、ShowingFeedback、Summary无异常；每个学习状态恰有1个primary（自评为“会/不会”一组），紧凑档主按钮位于下部40%、矮高度位于右半下半。
