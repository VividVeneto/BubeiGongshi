# CORE-50 测试方案

> 来源卡：[S5_CORE-50_界面.md](../../core/S5_CORE-50_界面.md)（识别结果、云端确认与识别历史界面）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R25][R33] routes 用 deps.sessions 与唯一 HistoryKeyUnlocker 构造 VM，null 禁用校正/保存/历史操作且无 FFI；A→closing/null→B 后清空 A 候选/预览/详情，排空成功才构造 B VM，同 profileId 新 handle 也重建；Widget 不持裸 core/source。
- [R06][R25] 在 correct/final_check、保存页返回、recog.adopt、ensure/history.list/pin/session.get/clearAll 的各 await 屏障切换档案；A 迟到 Saved 不向 B adopt、不在 closing 后补写 A，迟到列表/详情/错误不更新 B。同步 replaceSymbol 与 check/save 串行，快速替换不会保存旧 LaTeX/旧声明。
- [R25][R33] stopAndDrain 同步禁止新动作并发取消，等待已发核心事务/暂存副本清理；挂起保存页回调可撤销、不无限等用户，迟到返回丢弃。disposeAsync 并发/重复幂等，ChangeNotifier.dispose 不能代替它；清理仅删当前实例 staging 副本不删持久图。任一排空失败 current=null、A未释放/B未打开，其他beforeClose停止前缀仍执行，重试只补未完项。
- [R37] 登记 Fake `ImageDropSource` 并推送含 3 张图、`skippedNotImage = 1` 的批次：流程进入 `Cropping`，来源为 `dragDrop`，并显示跳过提示。
- [R06] 候选页：选第 2 个候选 → 替换一个符号 → `final_check` 无 Error → `save` 打开新建页且预填该 LaTeX；新建页返回 `Saved` 后调用一次 `recog.adopt`，返回 null 时不调用；Error 级诊断时保存按钮禁用。
- [R40] 同意页：选“未满 14 周岁”且未勾选监护人同意时提交按钮禁用；预览页显示的文件 SHA-256 等于 `UploadPreview.imageHash`；额度为 0 时不可确认。
- [R33] 历史页：Pin 的会话在 GC 后仍在列表；一键清空后列表为空；`has_images = false` 项显示“识别图片已清理”。
- [R26] 游客界面审计：`cloud` 为 null 时识别页、历史页均无云端入口与云端标识（Widget 树中查找不到对应 Key）。
- [R33] 存储守护完整行为测试已迁 CORE-101：本卡只测试只读 StorageStatus=true 显示原提示及 /settings/history 跳转，false/null 隐藏，页面销毁后不再响应；UI 不写状态、不调用 freeBytes/ensure/GC，也不登记 order55。
