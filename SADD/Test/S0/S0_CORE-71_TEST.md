# CORE-71 测试方案

> 来源卡：[S0_CORE-71_基座.md](../../S0/S0_CORE-71_基座.md)（可维护性度量与阈值报告）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R20] 注释/字符串/嵌套闭包/三元表达式夹具给固定期望复杂度，文件与Rust阈值反例返回1；PR有annotation、weekly有对比、两者均不发评论；报告含files/unsafe/ffi/coverage/violations五部分，`*.g.dart`排除、`crates/fml-error/src/codes.rs`计入并标generated:true。
- [R18] 相同输入重复运行结果字节一致；缺上周报告只标baseline；阈值装配：未知键、缺键、类型或范围不符（int>0、0<x≤1、bool）、YAML损坏各退出2；把core_line_coverage改为2/3后同一LCOV夹具的退出码随配置变化；dart_ccn_warn_only为true时Dart超阈值只warning、为false时退出1。
- [R18][R20] LCOV夹具4/5=80%通过、3/5退出1；缺核心SF、空报告、缺参数、DA重复/负计数、LF/LH不符、越界路径退出2；集合外高覆盖文件不抬高比例，零分母拒绝；重跑稳定；SF存在但无DA的文件视为0可执行行，不参与分子分母且不判失败；`--previous`文件损坏、version非1、缺必需字段均退出2（不降级为baseline）。
