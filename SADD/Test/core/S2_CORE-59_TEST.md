# CORE-59 测试方案

> 来源卡：[S2_CORE-59_界面.md](../../core/S2_CORE-59_界面.md)（公式编辑控制器与输入组件）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R08] Widget 测试：15 种模板逐一插入后 `engine.check` 返回非空 `ast`，空位数与模板表一致；nextHole 依次经过全部空位；在空位键入后该空位被替换。
- [R08] 结构化导航：语料抽样 50 条公式，left/right 遍历的停靠点集合与叶节点起止下标去重集合相同，光标从不落在命令名内部。
- [R08] 删除：`\frac{a}{b}` 光标在 b 后连续退格依次得到 `\frac{a}{\fmlhole}` → 光标移到 a 后 → `\frac{\fmlhole}{\fmlhole}` → 空串。
- [R08] 撤销/重做 50 步后源码与选区逐步复原；1 s 内连续键入合并为一步；结构化 → LaTeX → 结构化后源码逐字相同；LaTeX 模式源码含 `PARSE_SYNTAX` 时切换返回 false。
- [R10] 结构化模式粘贴 `\input{x}`：自动切到 LaTeX 模式，`PARSE_FORBIDDEN_COMMAND` 下划线覆盖 UTF-16 [0, 6)；源码前有中文与全角字符时下划线位置仍正确（字节换算单元测试）。
- [R09] 符号面板每一项单独 `engine.check` 无 Error；标为 ISO 的项在 `contracts/vectors/iso80000-2.yaml` 中 `input` 能力为真；国内方案与 ISO 方案下 `\mathrm{tg}\,x` 均能排版且无 Error。
- [R14] 在声明面板修改量纲后，下一个 worker 结果即更新诊断；冲突时 `TYPE_DIM_CONFLICT` 的 NodePath 区域出现 Error 下划线。
- [R08] Widget 测试：`FormulaCopyButton` 点击调用一次 `copy(format: auto)`，返回 false 时显示“已复制”；右键与长按打开“复制为”菜单，`formatsFor` 不含的项置灰；未登记 `FormulaCopier` 时点击写入 LaTeX 文本。
- [R08] Widget 测试：`FeatureRegistry` 中登记测试用 `EditorPlatformBindings` 时其 `accessoryBar` 出现在公式区下方且按键先交给它；未登记时 Tab 依次选中空位；模拟 IME 组合输入“α”期间源码不变，组合结束后插入一次。
- [R42.d] Widget 测试：`InputModalityScope` 为 `pointer` 与 `touch` 时编辑器工具栏按钮最小尺寸分别为 32 与 48；切换深色主题后公式颜色变为 `onSurface` 且未重新调用排版。

- [R08][R14] Fake FormulaCopier记录formatsFor/copy的userDecls：按钮透传当前声明且不修改；相同latex/方案而声明不同不复用旧导出，编辑器声明修改后菜单与复制均取新快照。
