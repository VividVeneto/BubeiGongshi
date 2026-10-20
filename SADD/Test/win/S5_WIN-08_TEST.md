# WIN-08 测试方案

> 来源卡：[S5_WIN-08_平台.md](../../win/S5_WIN-08_平台.md)（编辑器快捷键、输入法与笔输入）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R08] Widget 测试：在 `FormulaEditor` 中按 Ctrl+/ 后源码为 `\frac{\fmlhole}{\fmlhole}`，按 Tab 选区移到第二个空位；Ctrl+Shift+= 插入上标、Ctrl+= 插入下标；Ctrl+E 切换模式；表中每个编辑器命令触发对应动作；Ctrl+Shift+Z 与 Ctrl+Y 都执行重做。
- [R19] Widget 测试（`WindowsShellKeys` 挂入 WIN-15 `WindowsKeyRouter`）：在任意页面按 Ctrl+1，`AppNavigator` 收到 `'/study'`；Ctrl+2、Ctrl+3、Ctrl+4 分别收到 `'/library'`、`'/recognize'`、`'/settings'`，Ctrl+5 不导航；Alt+= 收到 `'/library/new'`；Ctrl+F 收到 `'/library?search=1'`；编辑器获得焦点时按 Ctrl+1 同样导航，按 Ctrl+/ 不导航。
- [R08] 单元测试：把 `holder.value` 换成分式为 Ctrl+Shift+F 的键位后，Ctrl+Shift+F 插入分式、Ctrl+/ 不再插入；`suspended = true` 时两个处理器均返回 ignored；`isReservedChord` 对 Ctrl+C、Ctrl+Space、Ctrl+.、Alt+F4、Ctrl+Alt+E、Ctrl+T、Shift+F10 返回 true。
- [R08] 手动：使用微软拼音输入法在 LaTeX 模式输入中文注释，组合期间方向键与 Backspace 不移动公式光标，Ctrl 快捷键在上屏后才生效；Ctrl+Space 切换输入法不被本应用拦截。
- [R06] 单元测试：`WindowsInkPolicy` 对 stylus 返回 true，`stylusSeen: true` 时 touch 返回 false，mouse 返回 true 且 `pressureOf` 为 null；invertedStylus、以及 buttons 含 `kPrimaryStylusButton` 的 stylus 按下判为橡皮擦，只含 `kStylusContact` 的不判；手动（二合一设备）：笔书写时手掌不留笔迹，笔尾擦除整笔。
- [R06] Widget 测试（假通道）：`status` 返回 `{devices: [], wintab_driver: true}` 时设置区“笔与数位板”显示开启 Windows Ink 提示；返回含 `integrated: false` 的设备时显示“数位板：<name>”且无提示；发出 `devicesChanged` 后刷新；通道失败时显示“未检测到触控笔或数位板”且无错误提示。
- [R06] 手动（外接数位板，驱动开启 Windows Ink，如 Wacom 或同类）：设置区列出该数位板；书写后调试构建打印的 `InkController.strokes` 中 pressure 非 null 且随用力变化；笔尾擦除整笔；书写区内按住侧键落笔擦除；书写区外点按侧键打开与鼠标右键相同的菜单（或按外部前提记入附录 D）；在书写区长按不弹出系统右键圆环；数位板映射到双显示器全部区域与只映射一台显示器两种设置下，窗口在两台显示器上的落笔位置都与光标一致。
- [R06] 手动（同一数位板在驱动中关闭 Windows Ink）：仍可按鼠标书写，设置区显示开启提示；在驱动中重新开启并插拔数位板后提示消失，压感与擦除恢复。
