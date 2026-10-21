# CORE-48 测试方案

> 来源卡：[S3_CORE-48_界面.md](../../core/S3_CORE-48_界面.md)（计算器与代入向导）。本文件是该卡验收标准全文；修改范围时同步修改，工具从下方验收标准行起拼回。

**验收标准**
- [R12] 计算器（CX-01）：`F = m a` 代入 m = 2 kg、a = 3 m/s²，显示 6 N、有效数字 1 位、求解方式“直接”；切换目标为 a 后反解得到 a = F/m 的数值。
- [R12] 数值求根：`x \cdot e^{x} = 1`（CX-09）依次经过 6 步，显示残差 < 1e-12 与“数值解”标注；CX-08 显示区间 [9.98, 10.02]；CX-07 显示常数 c 的来源与版本。
- [R16] 代入向导：把 `v = a t` 代入 `E_k = \frac{1}{2} m v^2` 的 v 槽位，生成派生修订且校验为 Verified；派生条目只读。
- [R17] 防误代：能量量纲的式子代入力矩槽位时默认不出现；打开跨种类候选后选择须二次确认，修订中的 `cross_kind_confirmation` 非空；量纲不同的候选不出现。
- [R42.e] Widget 测试：打开不带 `revision` 的 `/calc` 显示空状态“从公式库选择一个公式”，点主操作后路由为 `/library`；宽 1200 时输入行与结果左右并排。
- [R42.e][R42.b] 页面接入验收（Fake CoreBinding，`calc.evaluate` 计数）：计算器 3 个输入行已填值与单位、焦点在第 2 行数值框且已有结果时 360×800 ↔ 800×360 往返 3 次，`CalculatorVm` 与页面 `State` 不变，输入行、结果与焦点保持，`calc.evaluate` 调用次数不因旋转增加；数值求解停在 `NumericStep.showResidual` 时旋转仍在该步；`textScaler` 2.0 下计算器与代入页 `tester.takeException()` 为 null，结果值、单位与区间不截断；每页恰有 1 个 `FmlButtonVariant.primary`（“计算”/“代入”），矮高度时位于右侧操作区底部。
- [R12][R16] calcRoutes只注册/calc和/calc/substitute；计算器与代入两阶段均可独立构建测试，不导入PlanVm/计算链仓储；不可计算状态编辑链接指CORE-88。
