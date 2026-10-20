# CORE-12 测试方案

> 来源卡：[S1_CORE-12_引擎.md](../../core/S1_CORE-12_引擎.md)（排版 DisplayList）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R01] 快照测试（insta）：语料中全部公式的 DisplayList JSON 在 Android 与 Windows 构建上逐字节一致；光栅化允许像素差异，但布局尺寸与 NodePath 一致。
- [R08] hit-test：点击错误节点区域返回对应 NodePath；属性测试保证 DisplayList 中的 NodePath 与 AST 节点一一对应。
- [R10] 缺字形返回 `TYPESET_MISSING_GLYPH`；超深嵌套返回 `TYPESET_DEPTH_EXCEEDED`；超长公式在 `max_width` 内换行。
- [R08] 无障碍：`semantic_text` 对语料抽样 50 条与人工期望一致。
- [R01] 多字体：在 `fonts` 末尾追加一个扩展字体后，不使用它的公式 DisplayList 逐字节不变；`font_ids` 只列实际引用的字体，`Glyph.font` 均为其合法下标。
- [R03] 性能：单式排版满足 CORE-01 全局资源预算表“单式排版”行；测量方法：criterion 基准对语料中 ≤256 节点公式取 P95。
