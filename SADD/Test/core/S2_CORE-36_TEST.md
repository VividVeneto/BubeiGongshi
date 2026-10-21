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
