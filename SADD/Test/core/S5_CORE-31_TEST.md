# CORE-31 测试方案

> 来源卡：[S5_CORE-31_扩展.md](../../core/S5_CORE-31_扩展.md)（识别候选后处理与忠实转写）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R06] 后处理单元测试：Fake 后端返回 5 个候选（含非法 LaTeX、量纲错误、正确式），输出 ≤ 3 个，且查找模式下正确式排第一。
- [R13] 量纲错误候选带诊断；final_check成功返回Invalid及诊断，由保存消费方拒绝无效修订，不把校验结果伪装成外层Err；Unresolved返回成功结果，是否确认保存按Q32。
- [R06][R13] 逐候选绑定：同一profile/user_decls输入两条符号首次出现顺序相反的LaTeX，核对各自RawSymbol→SymbolId→SymbolEnv对应关系，不共享预绑定env；同一字形在两个不同记号方案下分别核对符号定义。Fake CandidateAnalyzer记录每次显式profile/user_decls/units/cancel，证明每条候选、校正后的完整新文本和终检都调用一次独立分析；新source_map/跨度指向新文本。真实FFI薄适配与CORE-56 analyze_source逐字段一致，empirical=false，领域crate依赖图无fml-ffi。
- [R06][R13] 解析失败保持原文、ast=None、Invalid诊断且不伪造AST；修正后重新绑定而不复用旧SymbolId。三个入口在已取消及分析途中置位时均返回RECOG_CANCELLED，不发布取消后候选。未知notation_profile_id返回NOTATION_UNBOUND；一次请求捕获的profile/units来自同一引擎代数，处理中发布新快照不混用。recog.*仍为pending，不将Rust适配测试当作跨语言schema已就绪。
- [R04] 作答模式：返回 `m v^2`（漏 ½）时候选不被纠正为 ½mv²，交给判分后判错（与 CORE-18 GX-05 联测）。
- [R07] 白名单逐项：`<script`、`http://`、`https://`、`\href`、`\url`、`\input`、`\include`、函数调用形式 JSON、代码围栏各一个候选均被丢弃并各产生一条 RECOG_OUTPUT_REJECTED（args.index 正确），同批合法候选照常返回；`$…$`、`\[…\]` 与首尾空白被剥离后通过；总长恰 262 144 字节通过、+1 字节报 RECOG_OUTPUT_TOO_LARGE；12 个候选只处理前 10 个且不报错。
- [R06] 评分：表驱动核对 Verified/VerifiedPolymorphic/Invalid/Unresolved/Draft/None 各自的绑定项与量纲项；全满且命中 5 个以上提示的候选 score = 1.1÷1.1 = 1.0、全满无提示 = 1.0÷1.1，两者不并列且前者在前；confidence 为 None 计 0.1，NaN/∞ 同 None，1.5 与 −0.2 夹到 1 与 0；提示加分上限 0.1；同分保持后端原序；输出至多 3 个。
- [R06] 结果语义：全部候选被拒时 Ok 且 candidates 为空、diagnostics 含 RECOG_ALL_CANDIDATES_INVALID；全部未被拒但都无法解析时 candidates 为前 3 个原文（ast=None）且含该诊断；symbol_hints 51 项、user_corrections 21 项经 FFI 适配报 FFI_BAD_ARG，纯函数只用前 50/20 项。
- [R13] 符号跨度与校正：`F = m a` 的 symbol_spans 按位置升序、source_range 为 UTF-8 字节区间且切片等于字形；含 v、0、l 的候选 alternatives 等于形近字表同组其余成员（表序，≤5），表外字形为空；apply_correction 成功后重新分析、跨度指向新文本；span 不属于该候选或替换为空报 RECOG_SPAN_INVALID。
- [R04] 作答模式：多候选时顺序与后端原序相同、score 不参与排序、文本不被替换；量纲诊断保留但不影响顺序。
- [R03] 预算：每候选分析按 CORE-01 预算表“公式解析（≤256 节点）”与“量纲校验”行基准测试（不另设毫秒数）。
