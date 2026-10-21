### WIN-18 Windows 环境矩阵与发布测量汇总

**目标**：消费 WIN-13 的原始测量输出，执行设备矩阵、能耗检查与预算判定，汇总发布证据；不重复实现性能场景。

**范围**
- 包含：`tools/perf/windows/` 的矩阵脚本、报告模板、能耗与预算汇总、跨平台一致性比较。
- 不包含：具体业务与性能场景（WIN-13）；主机驱动（WIN-17）；预算数值（CORE-01）；不达标项修复。

**依赖**：CORE-01、CORE-02、CORE-41、WIN-13、WIN-17、AND-12

**接口契约**

```text
tools/perf/windows/
  run_matrix.ps1 -Machines <csv>     分别构建 Profile 并运行集成测试、安装正式 Release 做外部冒烟与采样；收集 JSON 并标注 build_mode
  summarize.py --in build/perf --budget SADD/S0/S0_CORE-01_基座.md --out build/perf/report.md
                                     按行名解析 CORE-01 预算表 Windows 列，标记 PASS/FAIL；任一 FAIL 退出 1
  energy_check.ps1                   powercfg /energy /duration 60（需管理员，在矩阵机上手动执行），检查报告中本应用的计时器分辨率请求与唤醒
  compare.py                         两端一致性比对，任一字段不同退出 1
  report_template.md                 环境矩阵、测量结果、各 WIN 卡手动验收项勾选表、豁免记录（链接附录 A）
环境矩阵（最少）：Windows 10 1809 x64 实体机或虚拟机；Windows 11 23H2 4 核 / 8 GB / SSD（基线）；Windows 11 二合一触屏 + 触控笔（含平板姿态与键盘姿态切换）；
                 外接数位板（如 Wacom 或同类，驱动开启与关闭 Windows Ink 各一轮，含双显示器映射）；
                 高 DPI 双显示器（100% + 200%）；禁用 GPU（专用矩阵机切换到 Microsoft Basic Display Adapter，同 soft_render_test；远程桌面会话不算禁用 GPU）；远程桌面连接冒烟一轮（启动、渲染与输入）；系统对比度主题开启（如“夜空”）的冒烟一轮
```

输入协议唯一见 WIN-13 的样本输出；矩阵脚本只消费，不自行复制/重算算法结果。缺少场景实现、设备或外部供应能力时记录 pending/N/A，不能写通过。

**实现约束**
- 性能证据仅用 Release，Profile 集成结果只作趋势/诊断且单独标注；冷启动30次、核心1000次、图片100张与界面项采样按CORE-01，记录命令、锁版、设备、适配器与构建模式。
- 预算值按 CORE-01 行名读取，不复制阈值；失败须修复或由附录 A 记录带期限的豁免。主机复用 WIN-17 协议，退出时恢复设备设置/清理夹具。
- 按 CORE-41 acceptance_jobs.json 收集手动项及签字栏，矩阵中逐台记录，不以主机黄金图或Fake值替代平台证据。
- 不在每次CI提交跑全矩阵；Profile冒烟趋势与Release外部冒烟分列；powercfg需要矩阵机管理员权限，未提供保留pending。
- 不新增公共错误码。

**验收标准**：测试方案全文见 [Test/win/S7_WIN-18_TEST.md](../Test/win/S7_WIN-18_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约 350 行；`tools/perf/windows/`（矩阵/Release采样150、预算汇总85、跨平台比较55、能耗60）。本卡交付的脚本实现计入规模，模板数据、自身验证测试不计。
