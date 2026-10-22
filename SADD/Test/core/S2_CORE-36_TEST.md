# CORE-36 测试方案

> 来源卡：[S2_CORE-36_界面.md](../../core/S2_CORE-36_界面.md)（应用壳、组装层、账户入口与导航）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**

- [R24][R26] Fake composeApp按真实签名构造Host/TokenStore/ApiClient/DefaultAccountController，所有特性共享同一source；只传ctx.http。五状态Guard映射与sync_enabled正确，初始默认拒绝；无ConsentVerifier上传拒绝，有真实verifier时每次上传恰verify一次，无第二层guard。
- [R19][R24] 进程startup10/12/15/20/40/85/90与firstFrame各一次；profile30/50/55/60/70/80在A、B、同profile新handleC各顺序一轮，初次20打开A再start不重复。null期间不启动后续profile项，取消排空在途；失败日志后继续，无startup重跑；重复id/order拒绝。早登记ProfileHooks等待晚登记特性操作，晚stop同步取消可解等待；首stop失败其余也执行且不native close。
- [R24][R27] route在null立即禁写/隐藏A敏感状态，await排空再销毁；B以新handle构造新VM，A迟到结果不发布到B。UiDeps/Widget不得持source/core/ports。已安装同步guest/off返回disabled零HTTP，不抛SYNC_NOT_AVAILABLE；未安装占位才抛。closing只保留旧任务取消认证，不允许新业务或刷新，drain完成才清除。
- [R19] 路由器建好前调用 `AppNavigator.go('/study')` 两次，建好后依次执行且最终位于 `/study`；登记测试用 `ShellKeyHandler` 后按键先交给它。
- [R28] `installers.dart` 为空列表时 `composeApp` 成功，`deps.sync` 为 `DisabledSyncFacade`，调用 `setEnabled` 抛 `SYNC_NOT_AVAILABLE`；登记 Fake 门面后取得的是 Fake。
- [R19] 启动钩子按 order 执行；一个钩子抛错时其后的钩子仍执行，错误被记录。
- [R03] 集成测试测量冷启动时间，满足 CORE-01 预算（两端真机测量由 AND-12、WIN-13 执行）。
- [R04] Widget 测试：`FakeNotificationScheduler.simulateTap()` 后当前路由为 `/study`。
- [R42.a][R42.e] Widget 测试：游客完成账户入口后当前路由为 `/study`；主导航入口依次为学习、公式库、识别、设置；窗口宽 400 时为底部导航栏、1000 时为侧栏，宽度来回切换后路由栈与当前页输入不丢失。


- [R19] order 20 档案打开钩子悬挂超过 120 s、order 70 同步不完成时，firstFrameHooks 仍先完成且只执行一次；首帧前不执行。
- [R19] 托盘首帧钩子悬挂不返回时，2 s 后健康确认钩子照常执行，随后启动钩子开始；悬挂项记录一条超时日志。
- [R18] 源码扫描：`app/lib/ui/` 下任何 Widget 的构造参数或字段类型为 `AppDeps`、`CoreBinding`、`PlatformPorts` 时 CORE-69 DEP-5（CORE-41 编排）失败；`app/lib/<feature>/routes.dart` 读取 `deps.core` 不报错。
- [R19] 组装顺序与失败：两个 Fake transportInstaller 中第一项挂起时第二项零次调用，完成后才执行；platformInstallers 全部在 featureInstallers 之后；第 k 个 featureInstaller 抛错时其后安装点与 platformInstallers 零次、已创建的 ProfileSessionHost/ApiClient 被释放、composeApp 抛原错误且不返回 AppDeps；installDesign 是 featureInstallers 第一项，AppearanceController.load 在 runApp 之前完成。
- [R19] 启动失败：FML_API_HOST 为空或任一安装点抛错时 mainCommon 显示 StartupFailedScreen（只有“退出”），路由器未创建、firstFrame/startup/profile 钩子零次、提醒点击订阅零次，AppLog 恰一条 error 且界面不含异常原文。
- [R24] 启动恢复登记：composeApp 后 ctx.startupHooks 中 order 20 恰一项 id 为 account.restore，执行时调用 Fake DefaultAccountController.restoreOnStartup 恰一次；ApiClient 的 baseUrl 等于 ctx.apiBase。
- [R19] 路由：/study/books/new 命中 bookReminderRoutes 的新建页而非 studyHomeRoutes 的 :bookId；/library/trash、/library/new、/library/import 均不被 /library/:itemId 吞掉；/settings/appearance 命中 CORE-58；Uninitialized 下访问 /library 被重定向到 /，/account/x 与 /privacy 放行。
- [R18][R19] 登记门禁：FeatureRegistry 同类型重复登记、SettingsSections 同 id 或同 order、ProfileHooks 同 id/order、ShellKeyHandler 第二次登记均抛 StateError；正常组装后导出 build/extensions.json，含每项 owner/key/point 且与 contracts/policies/shared-writes.json 对应项一致。
- [R28] Disabled 门面：DisabledSyncFacade.status 首个值为 SyncStatus(phase: disabled) 且计数为 0；choices 返回空列表；syncNow/setEnabled/provideKey/setSyncPassphrase/revokeDeviceAndRotate/resolveChoice 各抛 code 为 SYNC_NOT_AVAILABLE 的 FmlException；DisabledUpgradeFacade.run 抛同码，resumeIfPending 正常返回且无副作用。
- [R24] 游客：AccountState 为 guestUnlocked 时设置页与识别页不出现云识别与同步入口；未登记 CloudRecognitionService 时注册用户同样不出现；源码扫描 app/lib/ui/ 无平台判断。
- [R19] 状态恢复：MaterialApp.router 的 restorationScopeId 为 fml、GoRouter 为 router；在 /library/<id> 触发 restoration 往返后回到同一路由。
- [R19] 系统返回（Widget 测试模拟 Android 返回）：二级页返回上一页；/library、/recognize、/settings 根页返回切到 /study；/study 根页返回交给系统（canPop 为真）且不弹提示；打开的底部面板/对话框先关闭自身；页面自设 PopScope(canPop: false) 时外壳规则不执行。
- [R04] 提醒点击在账户入口未完成（Uninitialized）时到达：先停留账户入口，完成游客入口后当前路由为 /study，且只跳转一次。
