# AND-02 测试方案

> 来源卡：[S2_AND-02_平台.md](../../and/S2_AND-02_平台.md)（权限与清单）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R38] `check_android_manifest.py`：Release 构建的合并清单包含本阶段必需集合且属于上表白名单；S7 完整能力包包含全部启用项；在 `app/build.gradle.kts` 引入一个带 `READ_EXTERNAL_STORAGE` 的测试依赖后脚本退出 1 并打印该权限。
- [R42.e] `check_android_manifest.py`：给任一 Activity 加 `android:screenOrientation="portrait"`，或从 MainActivity 的 `configChanges` 中删去 `uiMode`，脚本退出 1 并打印该 Activity 与属性；按 AND-02 接口契约窗口属性表 声明时退出 0。
- [R38] Widget 测试（假通道）：向 `ChannelPermissionService` 注入返回测试 harness 上下文的上下文提供者后，用户在用途说明中点“暂不”时不调用系统请求；注入返回 null 的提供者时跳过用途说明、直接调用系统请求并按系统结果返回；`permanently_denied` 时返回 `permanentlyDenied` 且不再弹系统框。
- [R31] 手动：拒绝相机权限后，“相册导入”与“文件导入”仍可用并能完成识别。
- [R04] 手动：拒绝通知权限后学习功能不受影响，提醒设置页显示“提醒未开启”。
- [R01] 在无 GMS 的国产手机上完成首次启动、游客模式、学习与识别冒烟。

- [R38] 合并清单launchMode=singleTop正例通过；缺失/改standard的夹具审计失败并定位属性。

- [R38] 审计fixtures逐一验证：删除本阶段必需INTERNET→失败；新增READ_MEDIA_IMAGES→失败；多个库合并同一正常权限→集合去重通过；signature自定义permission缺uses或反向缺声明、protectionLevel非signature→失败；CAMERA/POST_NOTIFICATIONS被maxSdkVersion截断到低于目标支持区间→失败；未引入可选AndroidX动态权限时不强加，成对引入时通过。报告包含manifest行、来源、期望/实际，不能只比较权限数量。
