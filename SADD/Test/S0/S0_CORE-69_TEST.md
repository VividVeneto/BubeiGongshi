# CORE-69 测试方案

> 来源卡：[S0_CORE-69_基座.md](../../S0/S0_CORE-69_基座.md)（源文件词法与依赖隐私门禁）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R26] 每条DEP/PRIV规则至少正反例各1：注释/字符串无误报，真实违规返回1并带正确行号；语法损坏返回2；ctx.http正例通过、ports.http反例失败、不可判定.http为warning且生成checklist。
- [R20] CI和本地同一输入Finding字节相同；四份policy缺失、未知字段/版本、重复或非法行均返回2，不忽略白名单缺失；普通/前缀import别名与Cargo package alias正反例覆盖。
- [R18] DEP-1正反例覆盖fml-error/fml-ast取消例外、server→sync-proto、pack→store（PackCatalog只读适配）、store→sync允许；server→store/ffi、store→pack、sync→store及其他领域→store拒绝、dev/build/target边及Cargo alias不能绕过；仅预留但尚未实现的包不产生缺包错误。DEP-6精确op调用字符串/type token被拦，注释和普通说明字符串不拦；无法证明的间接封装输出warning和人工项，不作为自动通过。
