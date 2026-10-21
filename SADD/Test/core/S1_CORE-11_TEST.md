# CORE-11 测试方案

> 来源卡：[S1_CORE-11_引擎.md](../../core/S1_CORE-11_引擎.md)（公式间代入、推导链与计算链）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R16] 代入集 `tests/fixtures/dimension/sx.yaml`（输入为 LaTeX + 符号声明，期望为结构断言与 canonical_hash 可复现）：SX-01 目标 `F=ma`（F: L M T^-2，m: M，a: L T^-2，SymbolId F0 m1 a2）、槽位 a 的 NodePath "1.1"、来源 `a=\frac{\mathrm{d}v}{\mathrm{d}t}`（a0 v1 t2）、var_map [(0→2)] → new_ast 为 `F=m\frac{\mathrm{d}v}{\mathrm{d}t}`，v、t 获新 id 3、4，Derivation.depth=1，check Verified，两次运行 canonical_hash 相同；SX-03 目标 `y=x\cdot k` 代入来源 `x=\int_0^{T} f(x)\,\mathrm{d}x`（积分变量 glyph x 与目标 x 同名）→ 新积分变量 glyph 为 `x'`，无捕获；SX-04 方差 `V=\sigma^2` 代入 DX-11 → VerifiedPolymorphic；SX-06 来源 `x^2=a` 求 x：branch None 报 DERIVE_TYPE_MISMATCH（reason branch），branch 0/1 分别得 `\sqrt{a}`、`-\sqrt{a}`。
- [R17] 防误代：SX-02 力矩代入能量变量默认不列为候选，确认后可代入并留记录；SX-05 对 `rank_candidates` 纯函数（不经 derive.rank op，其 pool 上限 200）传入 10000 条候选，为 Count 槽位列候选时不出现 Probability、Correlation 量。
- [R17] rank 判定表：两侧 kind 相同 → QuantityKindExact；一侧 None → DimensionUnified；不同 → 仅 include_cross_kind 时 CrossKind；任一侧 dimension None 省略；Energy/Heat（compatible_with）在 rank 中仍为 CrossKind。
- [R16] SX-07 的编辑拦截与脱离归 CORE-14（下游说明，非契约）验收；本卡只验：以未脱离派生修订为目标的 substitute 正常生成新派生修订（depth 递增）。SX-08 深度 9、节点超 4096、互相依赖分别返回 DERIVE_DEPTH_EXCEEDED、DERIVE_NODE_LIMIT、DERIVE_CYCLE。
- [R16] typed 一致性：derive.substitute/run_plan 请求中 typed 与重算不等 → FFI_BAD_ARG；重算非 Verified → DERIVE_NOT_VERIFIED。
- [R12] 计算链：两步计划 ① `v=\frac{s}{t}`（s=100.0 m，t=9.58 s，output v，feeds 下一步 v）② `E=\frac{1}{2}mv^2`（m=70.0 kg，output E，feeds None）→ 第一步 display Full、第二步 E=3.81×10³ J（35×(100.0/9.58)²≈3813.5）、sig_figs 3，与逐步手算一致；第一步 output_unit 取下一步 v 的声明单位；最后一步 feeds 非 None 返回 FFI_BAD_ARG；修订数不变。
- [R16] 跨修订合一：目标槽位类型 `L·D0` 与来源输出 `T·D0`（两份 typed 均自 D0 编号）按协议代入成功、不报 `DERIVE_TYPE_MISMATCH`；`rank_candidates` 对同样两份 typed 判定量纲可合一（MatchLevel 不低于 `DimensionUnified`）；候选输出量纲的合一触发 `Overflow` 时该候选被省略且其余候选照常排序。
