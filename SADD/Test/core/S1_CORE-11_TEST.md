# CORE-11 测试方案

> 来源卡：[S1_CORE-11_引擎.md](../../core/S1_CORE-11_引擎.md)（公式间代入、推导链与计算链）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R16] 代入集 `tests/fixtures/dimension/sx.yaml`：SX-01 a = dv/dt 代入 F = ma 生成 F = m·dv/dt；SX-03 约束变量自动换名；SX-04 方差代入切比雪夫不等式仍为 VerifiedPolymorphic；SX-06 多值反解两支。
- [R17] 防误代：SX-02 力矩代入能量变量默认不列为候选，确认后可代入并留记录；SX-05 在 10000 条公式池中为 Count 槽位列候选时不出现 Probability、Correlation 量。
- [R16] SX-07 编辑派生修订返回 `DERIVE_READ_ONLY`，脱离后生成独立修订；SX-08 深度 9、节点超 4096、互相依赖均被拒绝。
- [R12] 计算链：两步计划重放结果与逐步手算一致，单位自动换算，修订数不变。
- [R16] 跨修订合一：目标槽位类型 `L·D0` 与来源输出 `T·D0`（两份 typed 均自 D0 编号）按协议代入成功、不报 `DERIVE_TYPE_MISMATCH`；`rank_candidates` 对同样两份 typed 判定量纲可合一（MatchLevel 不低于 `DimensionUnified`）；候选输出量纲的合一触发 `Overflow` 时该候选被省略且其余候选照常排序。
