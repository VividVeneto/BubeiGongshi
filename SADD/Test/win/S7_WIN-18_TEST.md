# WIN-18 测试方案

> 来源卡：[S7_WIN-18_发布.md](../../win/S7_WIN-18_发布.md)。

**验收标准**
- [R03] 基线机型 `report.md` 中全部预算行 P95 达标（或有附录 A 豁免记录）。
- [R03] `energy_check.ps1` 报告中本应用无常驻高分辨率计时器请求，空闲 60 s 内无周期性唤醒。
- [R01] `compare.py` 比对 Windows 与 Android 的一致性输出，全部一致。
- [R42.c] 基线机型与二合一机型的 `report.md` 列出 CORE-01 预算表界面性能五行（点击到可见反馈、作答到判定反馈、转场与动效、旋转与窗口尺寸变化、主题切换）的 P50 与 P95，Windows 列全部达标或有附录 A 豁免。
- [R06] 外接数位板（开启 Windows Ink）上测量 CORE-01 预算表“手写墨迹上屏”，P95 在 Windows 列预算内；WIN-08 的数位板手动项（开启与关闭 Windows Ink 两轮）全部勾选并写入报告。
- [R41] `report_template.md` 逐项列出本文各卡的手动验收项，填写完成后作为 Windows 发布签字依据。
- [R03][R23] 报告分列 Profile 集成测试与 Release 外部测量，记录完整命令、Flutter 锁定版本、设备/适配器；Profile 驱动取得 VM service 并写出 JSON；Release 启动、版本、签名检查通过，无 FLUTTER_ENGINE_SWITCH 环境变量注入。
- [R03] 缺设备、场景或真实模型时汇总保留pending/N/A；Profile数据不作为Release预算通过依据。
