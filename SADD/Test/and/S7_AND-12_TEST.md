# AND-12 测试方案

> 来源卡：[S7_AND-12_发布.md](../../and/S7_AND-12_发布.md)（测量场景）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R31] `import_20_images_test.dart` 在 4 GB 机型上连续导入 20 张 1200 万像素 JPEG（经M-HOST主机驱动的AND-03正式选择器，两批各10张，禁止虚构测试注入路径）不 OOM，峰值内存增量在 CORE-01 预算内。
- [R08][R04] `process_restore_test.dart`：编辑公式草稿与学习会话进行中执行 `adb shell am kill <包名>`（模拟后台回收），重新打开后回到原页面，草稿内容与会话进度保留。
- [R01] `consistency_test.dart` 输出与 WIN-13 的 Windows 输出逐字节一致（AST JSON、诊断码、NodePath）。
- [R42.c] 手机与平板在竖屏、横屏下，“点击到可见反馈（按压态出现）”“作答到判定反馈（提交到判定条出现，含判分）”“转场与动效”“旋转与窗口尺寸变化（到新布局首帧）”“主题切换（预设或外观模式，到新主题首帧）”P95 均在 CORE-01 预算内，`report.md` 按设备与方向分列。
- [R42.e] `rotation_test.dart` 在手机与平板上竖→横、横→竖各 20 次，旋转前后编辑草稿文本与列表滚动偏移不变。
- [R03] 原始样本输出保留设备/构建模式/metric/unit/samples及P50/P95字段，缺依赖或设备标pending；矩阵验收另见AND-16。
- [R03] Release/Profile样本按schema=1输出build_mode/row/metric/unit/samples/p50/p95；原始文件无budget/pass，pending无伪造数值；AND-16据row合并预算且不混合两构建模式。
