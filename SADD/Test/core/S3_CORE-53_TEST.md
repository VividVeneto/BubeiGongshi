# CORE-53 测试方案

> 来源卡：[S3_CORE-53_界面.md](../../core/S3_CORE-53_界面.md)（LaTeX 命令补全）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R10] 单元测试 `contextAt`：`\fr|` 为 CommandPrefix(typed "fr")；`a\\|` 为 null；`\\\al|` 为 CommandPrefix；`\begin{pm|` 为 EnvironmentPrefix(typed "pm")；`\begin{pmatrix}|` 为 null；源码前含中文与全角字符时下标正确。
- [R10] 单元测试排序：`\fr|` 首项为 `frac`；`\Del|` 中 `Delta` 先于 `delta`；`\sq|` 含 `sqrt`；子序列 `\ifty|` 能找到 `infty` 且排在前缀匹配项之后；同档内 `recent` 次数高者在前。
- [R08] 单元测试接受：`\fr|` 接受 `frac` 得 `\frac{\fmlhole}{\fmlhole}` 且选中第一个空位；`a\al|pha` 接受 `alpha` 得 `a\alpha`；`\begin{pm|}` 接受 `pmatrix` 得完整 2×2 环境且不残留多余 `}`。
- [R08] Widget 测试（LaTeX 模式 `FormulaEditor`）：键入 `\su` 弹出含 `sum` 的列表；↓ 后 Enter 插入第二项；Esc 后继续键入字母不再弹出，键入新的 `\` 后再次弹出；弹层可见时源码框始终持有焦点；接受后撤销一次恢复为 `\su`；点按候选与按 Enter 结果相同。
- [R08] Widget 测试：模拟输入法组合“阿尔法”期间不弹出；`features` 未登记 `LatexSourceAssist` 时源码框行为与 CORE-37 一致。
- [R10] 数据测试：`latex_commands.json` 每项的 `insert` 经 `engine.check` 只可能出现 `PARSE_HOLE_UNFILLED`，不出现 `PARSE_UNSUPPORTED_COMMAND` 与 `PARSE_FORBIDDEN_COMMAND`；`palette.json` 中每个命令都有对应项；不含禁止清单中的名称。
- [R03] 性能：rankCandidates按CORE-01 预算表“补全rankCandidates（锁定完整数据，P95）”行，由AND-12/WIN-13在S7真机测量；本卡Widget只验证候选正确及帧泵后可见，不用Fake计时证明性能。
