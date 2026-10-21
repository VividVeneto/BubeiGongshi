# CORE-18 测试方案

> 来源卡：[S4_CORE-18_功能.md](../../core/S4_CORE-18_功能.md)（三层判分器）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R04][R19] 三个诊断码逐项夹具：不可解析作答 → GRADE_PARSE_FAILED/error/false 与 reason=parse_failed；预算耗尽 → GRADE_TIMEOUT/warning/false；不匹配答题种类或不支持节点 → GRADE_UNSUPPORTED/warning/false。均返回 Undetermined、诊断 severity 与 registry 相同；grade.answer 适配单测验证成功 ok=GradeResult，不把 error 级诊断变为 FmlError。解析失败的“不记录事件”由消费方处理，本卡验证可区分的 reason/诊断，不能新增隐式写事件依赖。registry/ownership/shared-writes 中三个 code 的 owner 均为 CORE-18；不将 pending 的 op schema/manifest 生成工作冒充本卡已实现。
- [R04][R04.c][R04.e] 正反例集 `crates/fml-grade/tests/fixtures/gx.yaml` 全部通过（同一 `seed` 两端结果一致）：GX-01 ½mv² 与 mv²/2 Correct；GX-02 移项 Correct；GX-03 d(tan x)/dx 与 1/cos²x Correct（两边共同域 cos x≠0）；GX-04 国内方案 Var(X) = EX² − (EX)² Correct、ISO 方案报 `NOTATION_AMBIGUOUS`；GX-05 漏系数、GX-06 正负号、GX-07 分母错位、GX-08 分子分母颠倒 Incorrect；GX-09 不定积分缺 +C 与 GX-10 不符合要求形式 Incorrect 并说明原因；GX-11 ln x² = 2ln x、GX-12 √(x²) = x Incorrect（抽样发现反例）；GX-13 (AB)ᵀ = AᵀBᵀ Incorrect；GX-14 Γ(1/2)/2 Undetermined。
- [R04] 扩充集：等价集与错误集各 ≥ 600 条（高等数学、线性代数、概率统计、大学物理各 ≥ 120 条，注明来源与变体类型）；等价集 Correct ≥ 99% 且误判 Incorrect ≤ 0.5%，错误集 Incorrect ≥ 99% 且误判 Correct ≤ 0.5%，Undetermined 比例单列。期望值由人工判例给出，不用待测实现生成。
- [R03] 性能：单题判分满足 CORE-01 全局资源预算表“单题判分”行；测量方法：GX 集逐题 100 次取 P95。
