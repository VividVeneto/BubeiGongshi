### CORE-12 数学 Box 布局内核

**目标**：在Rust中完成不依赖平台的数学Box、字体度量/轮廓及命中内核；完整DisplayList门面由CORE-94组合。

**范围**
- 包含：数学Box（分式、上下标、根式、大型运算符、矩阵）、DisplayList共享结构、基础node_bounds/hit-test、字体度量/outline注入接口。
- 不包含：伸缩括号/根号路径、换行/滚动策略、语义朗读、完整键LRU与最终layout门面（CORE-94）；光栅化与交互（CORE-37 的 Flutter 组件）；字体文件的读取、哈希与 MATH 表校验（CORE-56，字体以 `FontData` 从引擎快照注入；资源包字体经 CORE-15 推送为 Pack 层）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-06

**接口契约**

```rust
// crates/fml-typeset/src/lib.rs
pub struct FontData { pub id: String, pub bytes: Arc<[u8]> }       // OpenType MATH 表字体，由 CORE-56 注入
pub struct LayoutOptions { pub font_size_px: f32, pub max_width_px: Option<f32>, pub wrap: WrapMode /* Wrap | Scroll */,
                           pub display_style: bool, pub highlight: Vec<NodePath> }
pub enum WrapMode { Wrap, Scroll }
pub struct Rect { pub x: f32, pub y: f32, pub w: f32, pub h: f32 }   // 逻辑像素，原点在左上，y 向下
pub enum PathSeg { MoveTo(f32, f32), LineTo(f32, f32), QuadTo(f32, f32, f32, f32), CubicTo(f32, f32, f32, f32, f32, f32), Close }
pub enum DrawCmd {
    Glyph { font: u16 /* DisplayList.font_ids 下标 */, glyph_id: u16, x: f32, y: f32 /* 基线 */, size: f32 },
    Rule { x: f32, y: f32, w: f32, h: f32 },                      // 分数线、根号横线
    Path { segs: Vec<PathSeg>, stroke_width: Option<f32> /* None = 填充 */ },  // 伸缩括号与根号
}
pub struct DisplayList {
    pub layout_version: u16,            // 布局算法版本，当前 1；变化时快照全部更新
    pub font_ids: Vec<String>,          // 本列表实际引用的字体 ID，按首次使用顺序
    pub nodes: Vec<DrawCmd>,
    pub bounds: Rect, pub baseline: f32,
    pub node_bounds: Vec<(NodePath, Rect)>,
    pub hit_regions: Vec<(NodePath, Rect)>,   // 点击、选区与错误高亮
    pub semantic_text: String,                 // 由 AST 生成的中文数学朗读串
}
pub fn layout_boxes(ast: &FormulaNode, symbols: &SymbolEnv, fonts: &[FontData], opts: &LayoutOptions) -> Result<DisplayList, FmlError>;
pub fn hit_test(dl: &DisplayList, x: f32, y: f32) -> Option<NodePath>;
pub fn glyph_outline(font: &FontData, glyph_id: u16) -> Option<(u16 /* units_per_em */, Vec<PathSeg>)>;   // 字体设计单位、y 轴向上；op typeset.glyph_outlines 与 CORE-52 SVG 导出共用
```

- layout_boxes是完整门面下层：返回未换行、未施加伸缩路径的Box基础坐标及node_bounds/hit_regions，semantic_text为空，仅供CORE-94组合；它不是最终typeset.layout成功响应，不得以空朗读串冒充完整交付。共享类型与glyph_outline/hit_test唯一留本卡。
- FFI op：`typeset.layout`、`typeset.glyph_outlines` 的 DTO 与处理由 CORE-56 登记（字体取自引擎快照，请求按字体 ID 而非下标指定字体）；Flutter 据 `glyph_outlines` 把 `Glyph` 画成路径，不经平台文本栈。`hit_test` 不导出为 FFI op：Flutter 侧（CORE-37）直接按 `hit_regions` 判定，规则与 Rust `hit_test` 相同——取包含该点、面积最小的区域，面积相同取 NodePath 更深者。
- 错误码（唯一定义；沿用原触发语义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `TYPESET_MISSING_GLYPH` | error | 否 | 字体中无该字形，诊断带NodePath；不显示方框 |
| `TYPESET_DEPTH_EXCEEDED` | error | 否 | 嵌套超过CORE-05 MAX_DEPTH |
| `TYPESET_NO_FONT` | error | 否 | 快照没有含MATH表的字体，或请求的字体ID不存在 |
- 外部前提：OpenType 解析使用 `ttf-parser` crate（须支持 MATH 表），快照测试用 `insta`，版本按 ADR-V5-15 由首张使用卡开工时锁入 `Cargo.lock`；数学字体按附录 C 的许可审查结果选用，未定前开发用 Latin Modern Math（GUST Font License）。

缺字形是整体 Err(TYPESET_MISSING_GLYPH)，其 FmlError.diagnostics 包含对应 NodePath；不返回部分 DisplayList 或方框替代。因此保持 Result<DisplayList,FmlError> 签名；只有非阻断提示才放成功信封 diagnostics。

**实现约束**
- Flutter 只按 DisplayList 光栅化与处理交互，不做公式布局；DisplayList 中坐标与字形 ID 只依赖注入的字体，不依赖平台字体。
- 字体：CORE-56 内置一套开源数学字体（与 bootstrap 包同源，候选与许可见附录 C），扩展字体走 `font-extension` 包，经 CORE-15 推送为 Pack 层。
- 最大布局深度与CORE-05 MAX_DEPTH一致；最终内容键/按字节LRU迁CORE-94，内核不读缓存、不反向依赖完整门面。
- WrapMode与LayoutOptions由本卡共享类型保留，完整宽度策略由CORE-94施加，内核不自行绕过宽度约束冒充最终结果。
- `Hole` 排为虚线方框（宽 0.6 em、高 0.8 em，`Path` 描边 1 px），登记 hit region；“空位”朗读由CORE-94补全。
- 选型：保留自研 Rust 布局与 DisplayList，不改为 Flutter 侧公式渲染库（附录 A ADR-V5-04，对 v4 ADR-002 的不采纳决定）。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-12_TEST.md](../Test/core/S1_CORE-12_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约720行，分阶段：①共享类型55、注入字体/MATH/outline140、基础Box120及命中65，共380行；②分式/根式/上下标170及大型运算/微积分/矩阵/分段170，共340行。主包 `crates/fml-typeset/` 的内核；不含CORE-56 FFI。①独立构建测试度量/轮廓/命中，②独立构建测试完整节点Box/Hole/深度错误，不声称最终语义/换行验收；字体资源、生成物与自测不计。原1090行另370行归CORE-94。

---

