# CORE-87 测试方案

> 来源卡：[S2_CORE-87_界面.md](../../core/S2_CORE-87_界面.md)。

**验收标准**
- [R09] 符号面板每一项单独 `engine.check` 无 Error；标为 ISO 的项在 `contracts/vectors/iso80000-2.yaml` 中 `input` 能力为真；国内方案与 ISO 方案下 `\mathrm{tg}\,x` 均能排版且无 Error。
- [R14] 在声明面板修改量纲后，下一个 worker 结果即更新诊断；冲突时 `TYPE_DIM_CONFLICT` 的 NodePath 区域出现 Error 下划线。
- [R08] Widget 测试：`FormulaCopyButton` 点击调用一次 `copy(format: auto)`，返回 false 时显示“已复制”；右键与长按打开“复制为”菜单，`formatsFor` 不含的项置灰；未登记 `FormulaCopier` 时点击写入 LaTeX 文本。
- [R08] Widget 测试：`FeatureRegistry` 中登记测试用 `EditorPlatformBindings` 时其 `accessoryBar` 出现在公式区下方且按键先交给它；未登记时 Tab 依次选中空位；模拟 IME 组合输入“α”期间源码不变，组合结束后插入一次。
- [R42.d] Widget 测试：`InputModalityScope` 为 `pointer` 与 `touch` 时编辑器工具栏按钮最小尺寸分别为 32 与 48；切换深色主题后公式颜色变为 `onSurface` 且未重新调用排版。
- [R08][R14] Fake FormulaCopier记录formatsFor/copy的userDecls：按钮透传当前声明且不修改；相同latex/方案而声明不同不复用旧导出，编辑器声明修改后菜单与复制均取新快照。
- [R08] 完整编辑器在结构化/LaTeX两模式消费同一controller，诊断/预览/输入法组合与平台按键互不重复提交；默认bindings无平台服务可独立运行。
- [R08] Widget 测试逐一点击 15 个模板入口，验证源码模板与控制器结果一致、空位 Tab 导航顺序与选中替换正确；不能只用控制器单测代替入口接线覆盖。
