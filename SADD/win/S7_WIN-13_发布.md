### WIN-13 性能与环境矩阵

**目标**：在 Windows 环境矩阵上按 CORE-01 预算表测量性能与内存，检查无常驻唤醒，并汇总各 WIN 卡的手动验收结果作为发布签字依据。

**范围**
- 包含：`app/integration_test/windows/` 下的性能集成测试与一致性测试；`tools/perf/windows/` 下的矩阵运行、汇总与能耗检查脚本；环境矩阵与报告模板。
- 不包含：功能正确性测试（各卡自带）；Android 测量（AND-12）。

**依赖**：CORE-01、CORE-02、WIN-04、WIN-05、WIN-08、WIN-09、WIN-10、WIN-12、WIN-15、WIN-14、WIN-17

**接口契约**

测量项与 CORE-01 预算表行的对应（预算值只在 CORE-01 中维护，脚本按行名读取 Windows 列）：

| 测量项 | 预算表行 | 方法 |
| --- | --- | --- |
| 冷启动 | 冷启动到首页 | 进程启动到首页首帧（`FML_PERF_MARK` 日志） |
| 公式解析、量纲校验、单式排版 | 公式解析（≤256 节点）、量纲校验、单式排版 | 按CORE-67 manifest固定mode计时；解析/校验/排版同步op使用core.call，不改submit；CORE-06/09/12契约向量各至少1000次，报告分别列FFI总耗时与算法耗时 |
| 公式库搜索 | 公式库搜索首屏（10000 条） | 预置 10000 条公式的库 |
| 列表滚动 | 列表滚动 | `watchPerformance` 帧时间，100%、125%、150%、175%、200% DPI 各一次 |
| 手写 | 手写墨迹上屏 | 合成指针事件到帧呈现 |
| 点击反馈 | 点击到可见反馈（按压态出现） | 合成鼠标按下到按压态首帧（`FML_PERF_MARK`）；二合一机型另以触摸按下测一次 |
| 判定反馈 | 作答到判定反馈（提交到判定条出现，含判分） | 学习页按数字键（选择题）与 Ctrl+Enter（公式输入题）提交到判定条首帧，各 20 次 |
| 转场与动效 | 转场与动效 | `watchPerformance` 记录页面转场、判定条与小结动效的帧时间、掉帧率与单段时长；“动画效果”关闭时记录时长为 0 |
| 窗口尺寸变化 | 旋转与窗口尺寸变化（到新布局首帧） | `SetWindowPos` 在 600 × 500、1280 × 800 与最大化间切换到新布局首帧；拖动缩放 5 s 的帧时间；在 100% 与 200% 显示器间移动一次；DPI 100%～200% 各一次 |
| 主题切换 | 主题切换（预设或外观模式，到新主题首帧） | 外观页切换预设与深浅色，及“跟随系统”时切换 Windows 应用模式，到新主题首帧 |
| 图片 | 图片预处理、连续 20 张 12 MP 图片 | 经 WIN-04 导入路径，`GetProcessMemoryInfo` 采样 |
| 本地模型 | 本地模型识别（单式，模型已加载）、本地模型首次加载 | Fake 模型仅测管线开销；真实模型性能待 M-MODEL，报告标 N/A，不能以 Fake 值判通过 |
| 内存 | 常驻内存 | 首页空闲 60 s 后 Private Bytes |
| 安装包 | 安装包（不含可选模型与内容包） | 由 WIN-12 `check_artifacts.py` 记录 |

```text
app/integration_test/windows/
  perf_test.dart              上表各项；UI项≥20次，冷启动≥30次、核心操作≥1000次、图片≥100张，输出 build/perf/windows-<机型>.json：[{row, p50, p95, samples}]
  consistency_test.dart       读 CORE-06 与 CORE-09 契约向量中的公式（至少 50 条），输出 AST JSON、诊断码与 NodePath 到
                              build/consistency/windows.json，与 AND-12 的 android.json 由 tools/perf/windows/compare.py 比对
  soft_render_test.dart       在专用矩阵机切换到 Microsoft Basic Display Adapter 后运行冒烟与滚动测量；记录 DXGI 适配器名，不能仅凭远程桌面宣称禁用 GPU
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

- 错误码：测试与脚本不新增错误码。

按 CORE-41 acceptance_jobs.json 收集本平台所有真机/手动验收；缺设备或依赖未交付记 pending，不能记通过。性能用Release与CORE-01采样，进程内交互可用Profile integration_test；回滚/旋转/杀进程由外部主机驱动。跨端截图对照检查关键元素位置/可见性/语义，主机黄金图不代替平台检查。

本卡需要主机的验收使用WIN-17的run.py/cases.json/result.json协议，按本卡前缀登记场景；本阶段fixture与S7真实业务/设备矩阵分开。缺交互桌面/设备保留pending，WIN-13汇总（下游说明，非契约）。

产品约束追踪：见README §6 Q5、Q31；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- integration_test 用 Profile：flutter drive -d windows --profile --driver=test_driver/integration_test.dart --target=integration_test/windows/perf_test.dart（consistency/soft_render 同理，驱动使用 integrationDriver 写出结果）；不依赖 Release 的 VM service。Release 由外部进程脚本采集启动/版本/签名/内存及 FML_PERF_MARK 时间日志，界面操作按 checklist 执行；不开放远程测试端口。UI项至少20次，冷启动/核心/图片优先遵守CORE-01的30/1000/100样本口径，报告 P50 与 P95；不达标项须修复，或在附录 A 记录豁免（含原因、影响与复测计划）。
- 预算值不复制到脚本或测试中；测试只输出测量值，判定由 `summarize.py` 读取 CORE-01 完成。
- 不在 CI 每次提交运行全矩阵；CI 只在 Windows 构建机上运行 `perf_test.dart` 的冒烟子集（冷启动、解析）作 Profile 趋势记录；Release 签名制品另跑外部冒烟。

S7业务恢复联测：学习页作答落库后从窗口/托盘退出，重启恢复原会话；S2的WIN-06只验Fake生命周期。依赖闭包经WIN-12→WIN-02/03→WIN-16覆盖02/03/06/07，经WIN-08覆盖14的反向并不成立，故本卡显式依赖WIN-14以验自定义键位。

**验收标准**：测试方案全文见 [Test/win/S7_WIN-13_TEST.md](../Test/win/S7_WIN-13_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 430 行；主包 `app/`（`app/integration_test/windows/`，约 310 行），附属：`tools/perf/windows/`（约 120 行，测量脚本，与测试一同维护）。

