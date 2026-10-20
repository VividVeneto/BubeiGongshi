# WIN-15 测试方案

> 来源卡：[S2_WIN-15_平台.md](../../win/S2_WIN-15_平台.md)（Windows 桌面交互与窗口适配）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R42.d] Widget 测试（假通道）：`interactionMode` 返回 touch 时 `InputModalityScope.of` 为 `touch`、控件高 48；事件发出 pointer 后为 `pointer`、控件高 36，布局档与焦点不变；通道失败时为 `pointer`。
- [R42.c] 单元测试（假通道）：`clientAreaAnimation` 为 false 时 `WindowsMotionScale.scale` 为 0 并发出一次，事件改为 true 后为 1.0；通道失败为 1.0。
- [R42.f] Widget 测试：执行 `installWindowsInteraction` 后 `AppearanceController.load` 经 `WindowsDevicePrefStore` 读写，Fake `WindowsPrefs` 收到键 `appearance.v1` 与 `{"v":1,…,"haptics":true}`；`features.get<UiFeedbackSink>()` 为 null，外观页不显示“触感反馈”开关。
- [R42.f] Widget 测试（假通道）：`resolvedChanges` 发出 dark 时通道收到 `titleBar {dark: true, caption: <surface>, text: <onSurface>}`，相同参数连续发出只调用一次；扫描测试：`app/lib/` 中 `"titleBar"` 只出现在 `windows_title_bar.dart`。
- [R42.b] 单元测试：`StudyCommand` 的全部 `id` 与 a 表命令 ID 逐字相等且无重复；`defaultStudyBindings` 内部无重复组合键，带修饰的组合键均含 Ctrl，不带修饰的只属于 `unmodifiedAllowed` 命令；`KeyChord.encode` 与 `decode` 往返一致。
- [R42.b] Widget 测试（Fake 学习页挂 `FmlCommandScope`）：按 2 调用 `study.option2` 回调；焦点在 `TextField` 中按 2 不调用且文本框收到“2”；公式编辑器获得焦点时按 Ctrl+Enter 调用 `study.primary`；命令值为 null 时按键返回 ignored 并交给页面；`suspended = true` 时任何键返回 ignored；按住 Ctrl+Enter 重复只调用一次；挂入的内层处理器返回 handled 时不再查学习命令。
- [R42.b] Widget 测试：登记 `WindowsShortcutLabels` 后指针密度下 `ShortcutHint('study.primary')` 显示“Ctrl+Enter”；把 `StudyKeymapHolder.value` 中 `pause` 改为 Ctrl+Shift+Q 后 `changes` 通知、`labelOf('study.pause')` 为“Ctrl+Shift+Q”，按 Ctrl+Shift+Q 触发暂停、Ctrl+Shift+P 不再触发。
- [R42.e] 集成测试（`app/integration_test/windows/interaction_test.dart`，真机）：以 `SetWindowPos` 设为 400 × 300 逻辑像素后 `windowMetrics.min_track_px` 等于 600 × 500 × DPI/96（工作区更小时等于工作区），窗口实际不小于该值；在学习页输入未提交文本后于 1280 × 800、600 × 500、最大化之间切换各 2 次，路由、文本、光标与滚动偏移不变。
- [R42.e] 手动（100% + 200% 双显示器）：在 100%、125%、150%、175%、200% 下最小窗口均可用且无截断；把窗口从 100% 显示器拖到 200% 显示器后最小尺寸按新 DPI 生效、分档按新逻辑尺寸重算、正在输入的公式与焦点不丢。
- [R42.b] 手动（键盘，不用鼠标）：从学习首页按 Ctrl+Enter 开始，选择题按 1～4 或 A～D、自评按 Y / N、公式输入题按 Ctrl+Enter 提交、反馈页 Ctrl+Enter 下一题、Ctrl+Shift+M 记错了、Ctrl+Shift+S 跳过、Ctrl+Shift+P 暂停后 Ctrl+Enter 继续、默写用 Ctrl+PageUp/PageDown 换题并提交，完成一组到小结；全程焦点环可见，Tab 顺序与 d 表一致；开启微软拼音输入法时以上按键行为不变。
- [R42.d] 手动（鼠标与精确式触摸板）：按 d 表逐行核对悬停提示、右键菜单（含 Shift+F10）、滚轮行数与 Shift+滚轮横滚、触摸板双指惯性滚动。
- [R42.d] 手动（外接数位板，驱动开启 Windows Ink）：笔悬停或落笔后切到触控笔密度，移动鼠标后回到指针密度，布局档与焦点不变；书写区外点按笔侧键打开与鼠标右键相同的上下文菜单（M0 不满足时按 WIN-08 外部前提处理）。
- [R42.d] 手动（Windows 11 二合一触屏 + 触控笔）：拆下键盘或翻折为平板姿态后控件变为触摸密度、快捷键提示隐藏；接回键盘并移动触摸板后恢复指针密度；全过程不改布局档、不丢输入。
- [R42.f] 手动：Windows 10 1809 与 Windows 11 上切换系统深浅色（外观模式“跟随系统”）及应用内深浅色，标题栏随之切换；开启对比度主题（如“夜空”“沙漠”）后应用改用高对比度令牌、标题栏为系统颜色，关闭后恢复。
- [R42.c] WIN-13 在基线机型与二合一机型上测量 CORE-01 预算表 a 段所列五行，P95 在 Windows 列预算内。

- [R11][R42.d] Fake库scope按↓/Shift+↓分别只invoke move.down/extend.down一次；文本焦点不调用，方向repeat可调用，Delete repeat不调用；WIN-08内层handled时库/学习均不调用，未声明命令继续焦点链。

- [R42.d] 主机切换深浅色及高对比度，截取标题栏确认更新；切换前后位置/尺寸/前台窗口不变，DWM失败夹具回退系统默认且不崩溃。
