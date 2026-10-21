# CORE-56 测试方案

> 来源卡：[S1_CORE-56_引擎.md](../../core/S1_CORE-56_引擎.md)（内置引擎数据与上下文编排）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R19] 同代base投影：Embedded单位经Pack覆盖、再叠加User；完整data含User但base_units/base_kinds只等于同层集合去User后compose结果，含Pack覆盖值。以base构造MemRegistry并覆盖事务内未发布的最新用户定义，验证不读旧User、不混generation；发布失败保留原Arc及两套投影，在途Arc与新Arc各自一致，临时overlay不发布/不跨事务存活。
- [R12][R13][R09] 无账户且断网，fml_call 对 F=ma、m=2 kg、a=3 m/s² 得 6 N 并产生非空 DisplayList；cn-default/iso 可切换（同一 `A^{*}` 在 cn-default 绑定为伴随、在 iso 绑定为共轭转置，两次 engine.check 的 symbols 不同）；无需 S4 文件。
- [R13][R19] 纯 analyze_source 用显式两组 profile/user_decls/单位表对同一原文执行，结果随输入而非全局当前档案变化；保留 SourceMap 与 RawSymbol.id/occurrences。语法致 ast=None 时 bind/check 的 spy 调用数为零、symbols.decls 为空、typed=None、Invalid 且保留解析诊断；可解析的量纲冲突为 ast=Some/Invalid/typed=None，未绑定/待确认 Warning 为 Unresolved；Hole 的 PARSE_HOLE_UNFILLED 不被后续状态冲掉。按 parse→bind→check 对比完整诊断序列，warning/info/error 均不丢失，重复也不静默去除；输入不被修改。同一快照上 engine.check/calc.* 的 SymbolId 与 helper 一致，换全局快照不改变已经传入的输入；engine.check 无 AST 走 FmlError、有 AST 的 Invalid/Unresolved 走成功 DTO，未知方案 NOTATION_UNBOUND 不回退。无账户/Store/数据库即可构建并运行本组；S6 事务适配测试归消费卡，不作为 S1 前提。
- [R12] c 同时有 given=3e8、教材=3e8、Exact=299792458 时取 given；去掉 given 取教材，再去掉教材取 Exact，constants_used 保留来源。
- [R19] 在途任务持 generation=0 时 `set_layer` 成功返回 1，新请求用 1，旧任务仍读 0；损坏层返回 `ENGINE_DATA_INVALID` 且 generation 与层集合不变。
- [R19] 叠加向量 `contracts/vectors/engine-data-v1/compose.yaml`（每例为输入层列表 + 期望：成功时给出合成后被检查的单位/字体下标，失败时给出错误码与 details 类别；单位值引用 CORE-08 UNIT-X 向量）全部通过，至少覆盖：Pack 替换内置单位、Pack 改变内置单位量纲被拒、两包同 ID 冲突、User 层含非 `user:` 单位、移除 Pack 层后恢复内置值、追加字体后内置字体下标不变。
- [R19] `mark_unavailable` 后 `calc.evaluate` 返回 `ENGINE_UNAVAILABLE`；随后 `set_layer` 成功即恢复，结果使用新层。
- [R19] 并发：8 个线程循环调用 `engine.check`/`calc.evaluate`，1 个写者交替 `set_layer`/`remove_layer` 1000 次，无死锁，每个线程观测到的 generation 单调不减；安装由同一数据生成的 bootstrap 引擎层后，语料的 `engine.check` 结果与 DisplayList 与安装前逐字节一致。

- [R18] 同pack_id从v1升级v2（复用同一单位/字体ID）只保留一个Pack层并更新内容；v2无效时旧快照/generation不变；不同pack_id冲突仍拒绝。

- [R19] 以代数MAX-1夹具成功发布到MAX，再set_layer/remove_layer/mark_unavailable分别返回ENGINE_UNAVAILABLE；Arc与代数不再变化、无通知，后续snapshot和业务op拒绝，generation查询available=false；在途旧Arc可完成，重建实例恢复。
- [R19] 加载与构造（CO-28）：`EngineData::from_files` 对内置清单成功；缺文件、多余文件、路径含 `..`、manifest BLAKE3 不符、schema≠1、JSON 未知字段、字体哈希不符各返回 ENGINE_DATA_INVALID 且 details.path 正确；`EngineContext::new` 两个实例互不影响；`user_layer` 对含前向引用的 user 定义成功、对环/未知引用原样返回 CORE-08 码、对非 user: 前缀返回 ENGINE_DATA_INVALID；同 ID 重复返回 UNIT_DUPLICATE。
- [R19] 合成校验逐类各一反例：常数单位不可解析、compatible_with 指向不存在种类、方案内别名 (glyph, context, meaning_key) 完全重复、字体无 MATH 表、合成后无 MATH 字体、Pack 改变内置单位的量的种类，均为 ENGINE_DATA_INVALID 且 generation 不变；`remove_layer` 移除不存在的 Pack/User 层返回当前 generation、不发布、不唤醒通知。
- [R19] 状态与只读 op：`generation_status` 在正常、mark_unavailable、耗尽三态分别返回 (g,true)/(g,false)/(MAX,false)；notation.profiles、notation.bind 类 op、constants.resolve、units.compatible、units.convert 在 unavailable 时均返回 ENGINE_UNAVAILABLE 且不调用领域函数（spy 为零）；ENGINE_UNAVAILABLE 的 details.reason 三值各一例。
- [R19] 编排错误：calc.evaluate 对 F = m + a（Invalid）返回 EVAL_NOT_COMPUTABLE；calc.solvable_targets 对量纲溢出的公式返回 EVAL_NOT_COMPUTABLE 而非 UNIT_OVERFLOW；typeset.glyph_outlines 未知 font_id 返回 TYPESET_NO_FONT；typeset.layout 遇缺字形整体返回 TYPESET_MISSING_GLYPH、不返回部分 DisplayList。
- [R13] 语料（用于并发与 bootstrap 一致性）：`F=ma`、`v=\frac{s}{t}`、`pV=\nu RT`、`\int f(x)\,\mathrm{d}x=F(x)+C`、`\sin(\omega t)`、`E=\frac{1}{2}mv^2`，固定在 `contracts/vectors/engine-data-v1/corpus.yaml`。
