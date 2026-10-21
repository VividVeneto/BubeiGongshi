# CORE-31 测试方案

> 来源卡：[S5_CORE-31_扩展.md](../../core/S5_CORE-31_扩展.md)（识别候选后处理与忠实转写）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R06] 后处理单元测试：Fake 后端返回 5 个候选（含非法 LaTeX、量纲错误、正确式），输出 ≤ 3 个，且查找模式下正确式排第一。
- [R13] 量纲错误候选带诊断；final_check成功返回Invalid及诊断，由保存消费方拒绝无效修订，不把校验结果伪装成外层Err；Unresolved返回成功结果，是否确认保存按Q32。
- [R06][R13] 逐候选绑定：同一profile/user_decls输入两条符号首次出现顺序相反的LaTeX，核对各自RawSymbol→SymbolId→SymbolEnv对应关系，不共享预绑定env；同一字形在两个不同记号方案下分别核对符号定义。Fake CandidateAnalyzer记录每次显式profile/user_decls/units/cancel，证明每条候选、校正后的完整新文本和终检都调用一次独立分析；新source_map/跨度指向新文本。真实FFI薄适配与CORE-56 analyze_source逐字段一致，empirical=false，领域crate依赖图无fml-ffi。
- [R06][R13] 解析失败保持原文、ast=None、Invalid诊断且不伪造AST；修正后重新绑定而不复用旧SymbolId。三个入口在已取消及分析途中置位时均返回RECOG_CANCELLED，不发布取消后候选。未知notation_profile_id返回NOTATION_UNBOUND；一次请求捕获的profile/units来自同一引擎代数，处理中发布新快照不混用。recog.*仍为pending，不将Rust适配测试当作跨语言schema已就绪。
- [R04] 作答模式：返回 `m v^2`（漏 ½）时候选不被纠正为 ½mv²，交给判分后判错（与 CORE-18 GX-05 联测）。
- [R07] 含脚本标签、超长输出与外链的返回被拒绝。
