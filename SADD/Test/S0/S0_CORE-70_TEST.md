# CORE-70 测试方案

> 来源卡：[S0_CORE-70_基座.md](../../S0/S0_CORE-70_基座.md)（SADD结构与验收索引门禁）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R20][R19] 每类增量规则有独立正反例：缺七字段、章节顺序颠倒、范围缺“不包含”、卡内断链、[Rxx]未在§5、§5有未被引用的需求、错误表列序错误、尾列不以“触发条件”开头、级别/可重试取值非法、Q影响列与正文不符，各退出1；保持行数不变而替换未知卡ID仍退出1；SADD-9在未给`--material`时打印`SKIP pending SADD-9`且不判通过，目录缺文件或报告损坏退出2；被“范围”列为复用的规则（卡ID唯一、依赖无环、阶段、索引/依赖图、错误码跨卡唯一）本卡不输出finding，由文档工具步骤负责；代码围栏/HTML注释内出现的字段字样不算字段；每条finding的`file`/`line`指向卡片文件中该字段或断链所在行。
- [R18] 缺验收目标输出pending，存在目标失败为error；`--release`固定stage=S7：rows无stage=S7行、S7集合内任一行pending-target、active行target不存在均退出1；不带`--release`时同一清单有效（pending-target合法）；`path:`目标为目录或断链符号链接算不存在，`job:`目标在ci.yml中无该jobs键算不存在，缺前缀或前缀非法退出1。
- [R18] D.10声称就绪但D.12缺完整通过记录、复核人reviewer为空、reviewer与同卡上一条有效记录相同、复核date早于该卡当前版本日期，退出1（作者身份不在脚本可判范围，列入manual checklist）；SADD-12的findings与CORE-76 validateCurrent输出逐条同源，本卡不另判等级/旗标。
- [R18] acceptance_jobs.json为{version:1,rows:[]}时有效；version为2、顶层缺rows或JSON损坏退出2；两行(card,criterion,environment)相同、行缺status、environment或stage取未列值、stage与00-总览§2阶段表不符、criterion不是从1起的序号字符串，退出1；structure.json忽略时间字段后两次运行字节相同且不含绝对路径。
