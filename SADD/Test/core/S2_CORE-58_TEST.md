# CORE-58 测试方案

> 来源卡：[S2_CORE-58_界面.md](../../core/S2_CORE-58_界面.md)（设计组件、命令与外观入口）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R42.e] Widget 测试：`DesignGallery` 的 `list`、`input`、`detail` 样例（滚到第 120 行、在 `gallery.input` 输入 `v^2` 并把光标放在第 1 位、选中第 3 行）在 360×800 与 800×360 之间来回切换尺寸各 3 次，页面 `State` 为同一对象、输入框文本与光标、列表滚动偏移与焦点保持不变，期间不发出核心调用。
- [R42.c] Widget 测试：`DesignWarmup.run` 在测试绑定下完成，第二次调用立即返回且不再绘制；注入抛错的绘制时只写一条 `AppLog`、不抛出；`budget` 为 0 时不绘制即返回；CORE-36 启动钩子表 order 90 在 order 80 之后执行且不阻塞首帧。
- [R42.f] S2 假宿主直接打开 `/settings/appearance`，选择五套预设与三种模式后 AppearanceController 通知并持久化；选择“紫藤”与“深色”后界面立即为紫藤深色且未弹确认框；Fake `DevicePrefStore` 收到键 `appearance.v1`，outbox 无新增记录；不用等待 S6 设置页。
- [R42.b] Widget 测试：登记 Fake `UiFeedbackSink` 时外观页显示“触感反馈”开关，关闭后判对与点击不再调用 `emit`，写入的 `appearance.v1` 含 `"haptics":false`；未登记时不显示该开关（自 CORE-47 移入）。
- [R42.b] 命令未声明或 callback 为 null 时 invoke 返回 false；最内层挂载 scope 生效，销毁后恢复外层。

- [R42.d] Widget 测试：两层嵌套 `FmlCommandScope` 声明同一 ID 时 `FmlCommands.invoke` 调用内层回调；值为 null 时 `isAvailable` 为 false、`invoke` 返回 false；推入新路由后旧路由的 scope 不再生效；登记 Fake `ShortcutLabelSource` 返回 `Ctrl+Enter` 时指针密度下 `ShortcutHint('study.primary')` 显示该文本，触摸密度或未登记时不显示，`changes` 通知后文本更新。
- [R42.b] Widget 测试：触摸方式下所有可点击组件命中区 ≥ 48 dp，指针方式下 ≥ 32 px；`input`、`form`、`task` 样例的主按钮矩形在紧凑档位于屏幕下部 40%，矮高度（800×360）时位于右半下半部。
- [R42.a] Widget 测试：5 个 `GallerySample` 各自的 `FmlButtonVariant.primary` 数与 j 表“主按钮”列一致（0 或 1）；`task` 样例在 360×640 下无需滚动即可见三个计数与主按钮。
- [R42.c] Widget 测试：所有组件动画时长 ≤ `FmlMotion.max`；`disableAnimations` 为真时位移、缩放动画时长为 0；`MotionScaleSource.scale = 0.5` 时 `standard` 为 100 ms；延迟 100 ms 的 Fake 不出现骨架，延迟 500 ms 时 150 ms 起显示骨架。
- [R42.d] 黄金图测试：同一组件在 `touch` 与 `pointer` 下分别生成黄金图，在固定 Linux CI 镜像、锁定 Flutter 与字体下对主机黄金图像素差 ≤ 1%；跨端真机截图对照由 AND-12/WIN-13 的 checklist 执行，不作跨栅格器逐像素相等承诺；`no_platform_check_test.dart` 扫描 `app/lib/ui/` 无平台判断、`token_literal_test.dart` 扫描无颜色与时长字面量。
- [R42.d] Widget 测试：注入 Fake `InputModalitySource` 由 `pointer` 切到 `touch` 后控件高度由 36 变为 48、`ShortcutHint` 隐藏，布局档与焦点不变；收到鼠标 `PointerHoverEvent` 后切回 `pointer`。
- [R42.b] Widget 测试：`textScaler` 2.0 下 360×800 与 800×360 的 `form`、`list`、`task` 样例 `tester.takeException()` 为 null（无 `RenderFlex` 溢出）且文字不截断；判定条、掌握度图例除颜色外含图标或文字；读屏语义树中判定条为 `liveRegion`。
- [R42.a] 评审检查（checklist，放入 PR 描述）：界面中无来自不背单词的配色、图标、插画、文案、音效与版式；5 套预设色值与本卡一致。
