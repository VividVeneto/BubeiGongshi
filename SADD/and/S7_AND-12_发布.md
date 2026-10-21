### AND-12 Android 性能与业务联测场景

**目标**：交付Android性能、状态恢复与一致性测量场景，输出原始样本；矩阵调度、预算判定与发布汇总由 AND-16 消费。

**范围**
- 包含：`app/integration_test/android/` 测量场景、原始样本输出、业务恢复与一致性场景。
- 不包含：矩阵运行、预算汇总、能耗脚本与发布报告（AND-16）；预算值（CORE-01）；功能修复（对应功能卡）。

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
原始样本JSON：{schema:1, device, android_api, ram_gb, rom, orientation, build_mode, row, metric, unit, samples:[], p50, p95}；build_mode为release或profile，row为CORE-01预算表行名。原始输出不含budget/pass，AND-16读取预算判定；缺设备/依赖另以status=pending及reason记录，不伪造samples/分位数。
app/integration_test/android/
  上表测试文件；process_restore_test.dart（见验收）；consistency_test.dart（读 CORE-06 与 CORE-09 契约向量中的公式，至少 50 条，
  输出 engine.check 的 AST JSON、诊断码与 NodePath 到 out/consistency-android.json，由 WIN-18 的 compare.py 与 WIN-13 的 build/consistency/windows.json 输出比对）
```


- 错误码：无。

按 CORE-41 acceptance_jobs.json 收集本平台所有真机/手动验收；缺设备或依赖未交付记 pending，不能记通过。性能用Release与CORE-01采样，进程内交互可用Profile integration_test；回滚/旋转/杀进程由外部主机驱动。跨端截图对照检查关键元素位置/可见性/语义，主机黄金图不代替平台检查。

主机驱动约定：`python tools/android/host_tests/run.py --serial <adb-id> --apk <path> --case lifecycle|picker|notification|rotation --out <dir>`，0通过/1断言失败/2设备工具缺失；主机用adb安装/启动/kill/旋转/展开通知，并用`adb shell uiautomator dump` + hierarchy XML选择系统控件，Flutter存活阶段读取语义/测试结果JSON。Android SDK platform-tools版本由AND-01锁定，不额外假设integration_test能调用UIAutomator。测试前保存rotation/权限等设置，finally恢复并清理夹具；选择器与通知由主机断言。框架本体唯一归AND-15（S2），本卡S7只注册完整业务测量场景；矩阵调度归AND-16；AND-15未通过框架自检前本卡保持M-HOST阻断，不重复实现驱动。
图片100张性能使用正式系统选择器路径与主机已预置MediaStore夹具，或CORE-40控制器层FakeImagePicker做算法诊断；不得将Fake路径称端到端性能，不依赖AND-03不存在的注入。业务草稿/学习恢复等按S7依赖完整实现后执行，S2平台卡只用Fake页面/路由。

本卡需要主机的验收使用AND-15的run.py/cases.json/result.json协议；本卡交付完整业务测量场景；AND-15的框架fixture自检不替代本卡业务验收，AND-16（下游说明，非契约）在S7汇总。工具/设备未到标pending，不把主机能力写入Flutter进程。

产品约束追踪：见README §6 Q17；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 最终性能证据只用 Release，冷启动至少30次、核心操作至少1000次、图片至少100张，其他项及预热/设备条件完整引用 CORE-01 测量口径；Profile 仅定位问题，报告注明，不混合样本。
- 不达标项须在发布前由对应卡修复，或在附录 A 记录豁免（含原因与期限）后才可签字发布。
- 测试不依赖网络（云识别与资源包下载不在本卡测量），飞行模式下可运行。
- 外部前提：真机矩阵设备由甲方或开发团队提供（附录 D 记录到位情况）；`adb`、Flutter SDK 版本随 ADR-V5-15 锁定。

**验收标准**：测试方案全文见 [Test/and/S7_AND-12_TEST.md](../Test/and/S7_AND-12_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 560 行；`app/integration_test/android/`。分阶段：① 性能场景约 475 行；② 恢复与一致性场景约 85 行；每阶段以已实现依赖或替身独立构建与验证，不预报完整真机结论。场景本身是本卡交付实现计入规模，自身验证测试/数据夹具不计。
