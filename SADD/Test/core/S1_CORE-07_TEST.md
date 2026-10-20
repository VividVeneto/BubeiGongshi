# CORE-07 测试方案

> 来源卡：[S1_CORE-07_引擎.md](../../core/S1_CORE-07_引擎.md)（符号表、记号方案与常数集）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R09] 方案切换测试：tan/tg、arctan/arctg、ln/lg/log_a、A*、D(X)/Var(X)、C_n^k、EX²、ν 与 n 在两方案间切换，显示随方案变化，规范哈希与 SymbolId 不变。
- [R13] 歧义测试：同一方案内同字形多义报 `NOTATION_AMBIGUOUS`；`y = log x` 报 `NOTATION_LOG_BASE` 且状态为 Unresolved（DX-16）。
- [R12] 常数测试：同一常数同时存在 given、textbook、exact 时取 given；切换常数集后结果记录所用来源与版本。
