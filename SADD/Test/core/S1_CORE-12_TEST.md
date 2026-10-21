# CORE-12 测试方案

> 来源卡：[S1_CORE-12_引擎.md](../../core/S1_CORE-12_引擎.md)（数学Box布局内核）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R01] 内核Box/字形/轮廓与NodePath在Android/Windows一致；分式/根式/上下标/大型运算符/矩阵/Hole完整覆盖，不以未包装的空semantic_text冒充最终DisplayList。最终快照与性能迁CORE-94。
- [R08] hit-test：点击错误节点区域返回对应 NodePath；属性测试保证 DisplayList 中的 NodePath 与 AST 节点一一对应。
- [R10] 缺字形整体返回TYPESET_MISSING_GLYPH并带NodePath；超深返回TYPESET_DEPTH_EXCEEDED；无MATH字体或未知字体ID返回TYPESET_NO_FONT，不返回部分结果。
- [R01] 多字体：在 `fonts` 末尾追加一个扩展字体后，不使用它的公式 DisplayList 逐字节不变；`font_ids` 只列实际引用的字体，`Glyph.font` 均为其合法下标。
