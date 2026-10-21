# CORE-94 测试方案

> 来源卡：[S1_CORE-94_引擎.md](../../core/S1_CORE-94_引擎.md)（完整DisplayList布局与缓存）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**
- [R01] 快照测试（insta）：语料中全部公式的 DisplayList JSON 在 Android 与 Windows 构建上逐字节一致；光栅化允许像素差异，但布局尺寸与 NodePath 一致。
- [R08] hit-test：点击错误节点区域返回对应 NodePath；属性测试保证 DisplayList 中的 NodePath 与 AST 节点一一对应。
- [R10] 缺字形返回 `TYPESET_MISSING_GLYPH`；超深嵌套返回 `TYPESET_DEPTH_EXCEEDED`；超长公式在 `max_width` 内换行。
- [R08] 无障碍：`semantic_text` 对语料抽样 50 条与人工期望一致。
- [R01] 多字体：在 `fonts` 末尾追加一个扩展字体后，不使用它的公式 DisplayList 逐字节不变；`font_ids` 只列实际引用的字体，`Glyph.font` 均为其合法下标。
- [R03] 性能：单式排版满足 CORE-01 全局资源预算表“单式排版”行；测量方法：criterion 基准对语料中 ≤256 节点公式取 P95。
- [R01] 缓存键包含规范AST、symbols规范哈希、按序字体字节BLAKE3与全部LayoutOptions；逐项改变不误命中，按字节淘汰。Wrap后所有bounds/命中区域同步变换；Hole几何/朗读/命中一致。
- [R01] CORE-12内核可单独构建；本卡final layout不反向改变底层类型/错误语义。
