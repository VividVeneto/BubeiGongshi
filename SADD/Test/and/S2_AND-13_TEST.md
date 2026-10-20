# AND-13 测试方案

> 来源卡：[S2_AND-13_平台.md](../../and/S2_AND-13_平台.md)（Android 触摸交互与横竖屏适配）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R42.b] Widget 测试（假通道）：`AndroidHaptics` 收到 `correct` 时通道收到一次 `haptic {kind: "correct"}`；80 ms 内连续 3 次 `tap` 只发 1 次；把 `AppearancePref.haptics` 设为 false 后对任意 kind 调用 `emit`，通道无调用（关闭后不再触发）。
- [R42.b] 手动：应用内“触感反馈”关闭后点击、判对、判错均无振动；重新打开后恢复；系统设置关闭“触摸振动”后同样无振动。
- [R42.c] 单元测试（假通道）：`animatorScale` 返回 0.5 时 `scale` 为 0.5 并发出一次；事件重复 0.5 不再发出；返回 12 截为 10；通道失败时为 1.0。手动：开发者选项“动画时长缩放”设为关闭后页面转场无动画、各功能正常。
- [R42.d] Widget 测试：执行 `installAndroidInteraction` 后 `InputModalityScope.of` 为 `touch`、密度最小触控目标为 48；未登记 `DevicePrefStore` 时 `AppearanceController` 使用 `FileDevicePrefStore`。
- [R42.f] Widget 测试：`resolvedChanges` 发出 dark 时 `SystemChrome` 收到浅色图标样式、发出 light 时收到深色图标样式，相同样式连续发出只调用一次；扫描测试：`app/lib/` 中 `setSystemUIOverlayStyle` 只出现在 `android_system_bars.dart`。
- [R42.e] 扫描测试：`app/lib/` 与 `app/android/` 中无 `setPreferredOrientations`、`requestedOrientation`；合并清单的 MainActivity 属性等于 AND-02“b. MainActivity 窗口属性”表（由 AND-02 `check_android_manifest.py` 检查）。
- [R42.e] S7由AND-12主机驱动作业（进程内断言脚本app/integration_test/android/interaction_test.dart）：在编辑页输入未保存文本、在公式库列表滚动后，关闭自动旋转并用 `adb shell settings put system user_rotation` 依次切到 1、0，`windowMetrics` 的 `orientation` 随之变化且 `create_count` 不变，路由、文本与滚动偏移不变。
- [R42.e] 手动（一台手机、一台平板）：自动旋转开启时横竖屏切换均可用且布局按 CORE-55 分档；开启旋转锁定后旋转设备保持当前方向；分屏 1/3、1/2、2/3 与折叠屏展开折叠后当前路由与输入保留；开启“不保留活动”后切到后台再返回，回到原路由。
- [R42.b] 手动（刘海或挖孔屏手机，手势导航与三键导航各一次）：竖屏与两向横屏下内容与可点击控件不被挖孔、状态栏和导航栏遮挡，系统栏透明且图标明暗与主题一致；软键盘弹出时输入框与主按钮可见；横屏输入法不进入全屏提取界面。
- [R42.b] 手动（Android 13+ 手势返回一台、Android 8 返回键一台）：按对照表 e 逐行操作，系统返回结果与表一致且每行都有可见等价按钮；“学习”根页返回时显示回到桌面的预测性动画。
- [R42.c] 集成验收（S7由AND-12统一执行，不计本卡S2完成条件）：AND-12 在真机矩阵上测量 CORE-01 预算表“点击到可见反馈（按压态出现）”“旋转与窗口尺寸变化（到新布局首帧）”“主题切换（预设或外观模式，到新主题首帧）”，P95 在预算内。

- [R08][R19] Fake库scope收到Ctrl+A/Space/Delete各一次语义命令；EditableText/composing/KeyUp/不可用scope均ignored；repeat方向可连续移动，repeat删除不执行；handled后焦点链不再调用同一动作，重复登记ShellKeyHandler失败。
