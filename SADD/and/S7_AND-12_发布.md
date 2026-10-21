### AND-12 性能、能耗与真机矩阵

**目标**：在真机矩阵上测量 Android 性能、内存与能耗预算，给出可重复执行的测量脚本、报告模板，以及需要真机才能完成的跨卡联测（进程恢复、导入大图）。

**范围**
- 包含：`app/integration_test/android/` 测量用集成测试；`tools/perf/android/` 矩阵运行与报告汇总脚本；真机矩阵定义（含手机与平板的横竖屏）；CORE-01 界面流畅性 5 行预算的测量；进程被杀后的草稿与会话恢复联测；跨端一致性抽查。
- 不包含：各卡的功能正确性测试（各卡完成）；预算数值本身（CORE-01 预算表，本卡只引用）；修复不达标项（由对应卡修复）。

**依赖**：CORE-01、CORE-02、AND-03、AND-04、AND-07、AND-08、AND-09、AND-11、AND-13、AND-15

**接口契约**

测量项与预算（数值以 CORE-01 预算表为准，下表只列 Android 列的引用名）：

| 测量项 | CORE-01 预算表行 | 集成测试文件 |
| --- | --- | --- |
| 冷启动到可交互首页 | 冷启动到首页 | `cold_start_test.dart` |
| 公式库列表滚动 | 列表滚动 | `scroll_test.dart` |
| 公式解析、量纲校验、单式排版 | 公式解析（≤256 节点）、量纲校验、单式排版 | `editor_latency_test.dart` |
| 手写墨迹上屏 | 手写墨迹上屏 | `ink_latency_test.dart` |
| 公式库搜索首屏 | 公式库搜索首屏（10000 条） | `search_test.dart` |
| 单张图片预处理、连续导入 20 张 1200 万像素图片 | 图片预处理、连续 20 张 12 MP 图片 | `import_20_images_test.dart` |
| 本地模型识别（模型已加载）、首次加载 | 本地模型识别（单式，模型已加载）、本地模型首次加载 | `local_model_test.dart`（无模型包时跳过并在报告注明） |
| 常驻内存 | 常驻内存 | 各测试结束时采样 `dumpsys meminfo` |
| 点击到按压态出现 | 点击到可见反馈（按压态出现） | `ui_feedback_latency_test.dart`（`PointerDownEvent` 时间戳到按压态首帧的 `FrameTiming`） |
| 提交作答到判定条出现 | 作答到判定反馈（提交到判定条出现，含判分） | `verdict_latency_test.dart` |
| 页面转场与会话内题目切换 | 转场与动效 | `transition_frames_test.dart`（转场期间的帧耗时与掉帧数） |
| 横竖屏旋转、分屏与窗口尺寸变化 | 旋转与窗口尺寸变化（到新布局首帧） | `rotation_test.dart`（`didChangeMetrics` 到新布局首帧；关闭自动旋转后用 `adb shell settings put system user_rotation` 切换） |
| 切换预设与外观模式 | 主题切换（预设或外观模式，到新主题首帧） | `theme_switch_test.dart` |

```text
tools/perf/android/（本卡实现；退出码 0 全部达标 / 1 有不达标项 / 2 脚本错误）
  run_matrix.sh [--serial <id>]...   对每台已连接设备：按 CORE-01 测量口径运行 release 外部采样；框架内观测可用 profile 但不能作为 release 达标证据，结果写 out/<设备>/<测试>.json
                                     JSON：{device, android_api, ram_gb, rom, orientation, metric, unit, samples[], p50, p95, budget, pass}
  summarize.py out/ → out/report.md  按 report_template.md 汇总，每项 P50、P95、预算、是否达标
  energy_check.sh --minutes 30       运行“学习 + 识别”脚本后导出 batterystats，检查：无持有 > 60 s 的唤醒锁、后台无网络、无前台服务
  report_template.md                 设备、系统版本、RAM、ROM、各指标结果、手动验收清单（02 文档各卡的手动验收项逐条列出，签字栏）
app/integration_test/android/
  上表测试文件；process_restore_test.dart（见验收）；consistency_test.dart（读 CORE-06 与 CORE-09 契约向量中的公式，至少 50 条，
  输出 engine.check 的 AST JSON、诊断码与 NodePath 到 out/consistency-android.json，由 WIN-13 的同名输出比对）
```

真机矩阵（至少）：4 GB RAM 中端机、8 GB RAM 主流机、无 GMS 的国产 ROM（至少两家厂商）、Android 8 / Android 13 / 当年主流版本各一台、平板或折叠屏一台（带触控笔优先）、学习平板一台；其中至少一台手机与一台平板（最短边 ≥ 600 dp）分别在竖屏与横屏下运行上表全部测试，至少一台刘海或挖孔屏手机，手势导航与三键导航各至少一台。

- 错误码：无。

按 CORE-41 acceptance_jobs.json 收集本平台所有真机/手动验收；缺设备或依赖未交付记 pending，不能记通过。性能用Release与CORE-01采样，进程内交互可用Profile integration_test；回滚/旋转/杀进程由外部主机驱动。跨端截图对照检查关键元素位置/可见性/语义，主机黄金图不代替平台检查。

主机驱动约定：`python tools/android/host_tests/run.py --serial <adb-id> --apk <path> --case lifecycle|picker|notification|rotation --out <dir>`，0通过/1断言失败/2设备工具缺失；主机用adb安装/启动/kill/旋转/展开通知，并用`adb shell uiautomator dump` + hierarchy XML选择系统控件，Flutter存活阶段读取语义/测试结果JSON。Android SDK platform-tools版本由AND-01锁定，不额外假设integration_test能调用UIAutomator。测试前保存rotation/权限等设置，finally恢复并清理夹具；选择器与通知由主机断言。框架本体唯一归AND-15（S2），本卡S7只注册完整业务场景与矩阵；AND-15未通过框架自检前本卡保持M-HOST阻断，不重复实现驱动。
图片100张性能使用正式系统选择器路径与主机已预置MediaStore夹具，或CORE-40控制器层FakeImagePicker做算法诊断；不得将Fake路径称端到端性能，不依赖AND-03不存在的注入。业务草稿/学习恢复等按S7依赖完整实现后执行，S2平台卡只用Fake页面/路由。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本阶段功能只注册本卡fixture场景，完整业务与真机性能由AND-12（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

产品约束追踪：见README §6 Q17；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 最终性能证据只用 Release，冷启动至少30次、核心操作至少1000次、图片至少100张，其他项及预热/设备条件完整引用 CORE-01 测量口径；Profile 仅定位问题，报告注明，不混合样本。
- 不达标项须在发布前由对应卡修复，或在附录 A 记录豁免（含原因与期限）后才可签字发布。
- 测试不依赖网络（云识别与资源包下载不在本卡测量），飞行模式下可运行。
- 外部前提：真机矩阵设备由甲方或开发团队提供（附录 D 记录到位情况）；`adb`、Flutter SDK 版本随 ADR-V5-15 锁定。

**验收标准**：测试方案全文见 [Test/and/S7_AND-12_TEST.md](../Test/and/S7_AND-12_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 490 行；主包 `app/integration_test/android/`（约 370 行），附属：`tools/perf/android/`（约 120 行，脚本与模板）。

