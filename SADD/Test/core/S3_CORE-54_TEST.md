# CORE-54 测试方案

> 来源卡：[S3_CORE-54_界面.md](../../core/S3_CORE-54_界面.md)（公式库批量选择与批量操作）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R11] Rust 单元测试：100 条测试库，`Query` 目标排除 3 条执行“加标签 期末” → `applied = 97`；其中已有 20 个标签的条目列入 `skipped`（`LIB_TAGS_LIMIT`）；已含该标签的条目计入 `unchanged`；每个有变化的条目恰好写入一条 outbox 记录。
- [R11] Rust 单元测试：处理到第 50 条时置位取消 → 返回 `LIB_BATCH_CANCELLED` 且数据库与 outbox 无变化；目标展开为 10001 条时返回 `LIB_BATCH_TOO_LARGE`；`Trash` 后 `search` 不再返回这些条目，`trashed = true` 时返回。
- [R11] Widget 测试（Fake CoreBinding 回放）：Fake分别invoke library.batch.toggle/extend.down/selectAll/clear及鼠标Ctrl/Shift单击的选中结果与选择规则一致；invoke trash后出现撤销提示条，invoke undo发出 `untrash` 且 ID 等于 `appliedIds`；invoke editTags打开编辑标签对话框；触控长按进入选择模式。
- [R11] Widget 测试：未登记 `LibraryListDecorator` 时列表无复选框、上述语义命令不可用；筛选变化后选择被清空。
- [R04] 集成测试（真实核心）：回收站页选中 5 条执行“恢复”，5 条回到公式库列表且修订历史不变。
- [R11] 性能：10000条加一标签按CORE-01“库批量写入”行，期间交互与滚动另按“列表滚动”行；由AND-12/WIN-13在S7分别测量，不以滚动FPS代替事务耗时，本卡只验事务/取消语义。
- [R42.b] Widget 测试：只点列表顶部“选择”按钮（不长按）即可进入选择模式；`touch` 下复选框点击区域 ≥ 48×48。
