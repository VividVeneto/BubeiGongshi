# CORE-55 测试方案

> 来源卡：[S2_CORE-55_界面.md](../../core/S2_CORE-55_界面.md)（界面设计系统与主题）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R42.f] 单元测试（`app/test/ui/design/contrast_test.dart`）：按 WCAG 2.1 公式对 5 套预设 × 浅/深色计算 c 中各项对比度，全部达到门槛，且与 c 表数值误差 ≤ 0.01；语义色在 5 套预设中取值相同。
- [R42.f] Widget 测试：`AppearanceController.set` 切换预设与外观模式后同一帧内 `Theme.of` 已变化，路由栈与页面 `State` 不变；用 Fake `DevicePrefStore` 断言写入键 `appearance.v1` 与 `{"v":1,…}`；重新 `load` 后恢复；写入损坏 JSON 或 `"v":2` 时得到默认值（`system`、`qunqing`）；偏好不出现在 outbox 与备份范围中。
- [R42.e] Widget 测试：`LayoutInfo.fromSize` 对 d 表每一行的典型尺寸（360×800、800×360、800×1280、1280×800、600×500、960×1032、1920×1080）得到表中的档位、矮高度与导航形态；`textScale` 2.0 时宽档降为中等档。
- [R42.c] 性能：两端真机按 CORE-01 全局资源预算表“点击到可见反馈”“转场与动效”“主题切换”行测量（AND-12、WIN-13 执行），满足预算。

- [R42.d] of(context)返回FmlTokens，5预设×2明暗字段齐全且与ThemeExtension是同一对象；嵌套Theme读最近值；缺少任一扩展抛FML_THEME_MISSING而非空指针；切主题后color随新Theme更新。
