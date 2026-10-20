# AND-07 测试方案

> 来源卡：[S5_AND-07_平台.md](../../and/S5_AND-07_平台.md)（手写与编辑器的 Android 适配）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R06] 单元测试：`AndroidInkPolicy` 对 stylus 按下返回 true；`stylusSeen: true` 时 touch 返回 false；`radiusMajor: 30` 的 touch 返回 false；`pressure 0.5`（min 0、max 1）得 0.5；invertedStylus 判为橡皮擦。
- [R06] 手动（触控笔平板）：用笔书写时手掌压在屏幕上不留笔迹；只用手指的手机上可正常书写；笔尾橡皮擦删除整笔。
- [R08] Widget 测试：模拟 `viewInsets.bottom = 300` 时 `FormulaEditor` 下方出现快捷栏，点“分式”后源码为 `\frac{\fmlhole}{\fmlhole}`，点“下一空位”后选区移到第二个空位；`viewInsets.bottom = 0` 时无快捷栏。
- [R08] 手动：软键盘弹出时公式区与快捷栏均可见，不被键盘遮挡。
- [R42.b] Widget 测试：`TemplateBar` 每个按钮的命中区不小于 48×48 dp。
- [R42.e] 手动：手机横屏弹出软键盘时公式区、快捷栏与主按钮均可见；横竖屏切换后快捷栏仍在键盘上方，已输入内容不丢。
