# CORE-50 测试方案

> 来源卡：[S5_CORE-50_界面.md](../../core/S5_CORE-50_界面.md)（识别结果、云端确认与识别历史界面）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R37] 登记 Fake `ImageDropSource` 并推送含 3 张图、`skippedNotImage = 1` 的批次：流程进入 `Cropping`，来源为 `dragDrop`，并显示跳过提示。
- [R06] 候选页：选第 2 个候选 → 替换一个符号 → `final_check` 无 Error → `save` 打开新建页且预填该 LaTeX；新建页返回 `Saved` 后调用一次 `recog.adopt`，返回 null 时不调用；Error 级诊断时保存按钮禁用。
- [R40] 同意页：选“未满 14 周岁”且未勾选监护人同意时提交按钮禁用；预览页显示的文件 SHA-256 等于 `UploadPreview.imageHash`；额度为 0 时不可确认。
- [R33] 历史页：Pin 的会话在 GC 后仍在列表；一键清空后列表为空；`has_images = false` 项显示“识别图片已清理”。
- [R26] 游客界面审计：`cloud` 为 null 时识别页、历史页均无云端入口与云端标识（Widget 树中查找不到对应 Key）。
- [R33] `FakeLocalFileStore.freeBytes` 返回 400 MiB 时启动后恰好提交一次 `recog.gc` 且 `StorageStatus` 为 true；10 分钟内再次 `resumed` 不重复提交。
