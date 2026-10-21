### CORE-94 完整 DisplayList 布局与缓存

**目标**：在CORE-12数学Box内核上完成伸缩、换行、中文朗读与缓存，向两端交付最终DisplayList。

**范围**
- 包含：伸缩括号/根号路径、Wrap/Scroll宽度策略、坐标重排、中文semantic_text、完整内容键/按字节LRU、最终layout门面。
- 不包含：共享DisplayList/FontData/LayoutOptions模型、Box/字形度量/outline/hit_test内核（CORE-12）；字体文件读取/哈希/校验及FFI（CORE-56）；Flutter光栅化交互（CORE-37）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-12

**接口契约**

```rust
// crates/fml-typeset/src/lib.rs；共享类型由CORE-12唯一定义
pub fn layout(ast: &FormulaNode, symbols: &SymbolEnv, fonts: &[FontData], opts: &LayoutOptions) -> Result<DisplayList, FmlError>;
```

- 本卡单向调用CORE-12 layout_boxes/glyph_outline/hit_test，拥有最终layout实现；CORE-12不得调用本卡。CORE-56 typeset.layout调用本卡；typeset.glyph_outlines仍可直接消费CORE-12。
- DisplayList完整字段与坐标系、PathSeg/DrawCmd及font_ids首次使用次序复用CORE-12，重排后同时更新bounds/baseline/node_bounds/hit_regions；命中规则仍为包含点的最小面积，面积相同取更深NodePath。
- 所有TYPESET_*错误仍由CORE-12唯一定义，本卡透传；缺字形整体Err且diagnostics带NodePath，不允许部分DisplayList或方框代替。

**实现约束**
- 布局结果按 `(规范AST哈希, symbols规范内容哈希, 按fonts顺序的字体字节BLAKE3列表, 选项全部字段)` 进行按字节计量的 LRU 缓存；最大布局深度与 CORE-05 `MAX_DEPTH` 一致。
- 超长公式按WrapMode换行或横向滚动，不越界；伸缩按注入MATH度量与路径实现，不依赖平台文本栈。
- 中文朗读按AST语义生成，Hole读“空位”；Hole几何仍用CORE-12宽0.6em高0.8em/描边1px的虚线方框并保持命中。
- Flutter只光栅化与交互，不做布局；同字体注入两端的尺寸/NodePath与DisplayList JSON逐字节一致；字体ID只列实际使用字体，追加未用字体不能改变结果。
- 自研Rust布局选型仍遵ADR-V5-04，不替换为Flutter公式库；ttf-parser/insta锁版与字体许可前提沿CORE-12/附录C。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-94_TEST.md](../Test/core/S1_CORE-94_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约370行；主包 `crates/fml-typeset/src/{stretch,wrap,semantic,cache}.rs`（100/100/90/80，含最终layout接入）；无本卡FFI附属。字体/固定词表/生成物/自测不计；单阶段以内核+完整门面独立构建、跨端快照/宽度/朗读/缓存验收交付。
