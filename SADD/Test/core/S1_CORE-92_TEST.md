# CORE-92 测试方案

> 来源卡：[S1_CORE-92_引擎.md](../../core/S1_CORE-92_引擎.md)（LaTeX与Unicode语义导出）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**
- [R10] 往返向量 LX-01～LX-11 全部满足期望。
- [R10] 语料测试 `tests/fixtures/formulas/`：每条含 LaTeX、Unicode、AST JSON、期望诊断与来源，覆盖高中数学、高中物理、高等数学、大学物理；≥100 条冻结语法代表式（分数、矩阵、重积分、曲线积分、∇、级数、分段）全部通过。
- [R09] ISO 80000-2 清单逐项做 Unicode↔LaTeX 语义往返，规范哈希不变；清单能力标注与实际行为一致。
- [R10] 全AST导出再解析的canonical_hash一致；矩阵/多重上下限不能无损Unicode导出时逐节点报告PARSE_UNICODE_NOT_EXPORTABLE，禁止有损降级；Hole规范导出并保留语义。
- [R19] engine.export严格解码、AST limits/Hole与导出诊断代码透传正确；CORE-06单独构建不依赖本卡。
