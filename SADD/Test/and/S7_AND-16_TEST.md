# AND-16 测试方案

> 来源卡：[S7_AND-16_发布.md](../../and/S7_AND-16_发布.md)。

**验收标准**
- [R03] 4 GB 中端机上 `run_matrix.sh` 全部项 P95 达标并生成 `out/report.md`；人为把某预算改小 1 ms 时脚本退出 1 并标出该项。
- [R03] `energy_check.sh` 在 30 分钟脚本后退出 0（无长唤醒锁、无后台网络、无前台服务）。
- [R41] `report_template.md` 逐项列出 02 文档全部手动验收项，矩阵中每台设备填写完成后作为 Android 发布签字依据。
- [R03] 缺设备、场景或真实模型时汇总保留pending/N/A；Profile数据不作为Release预算通过依据。
