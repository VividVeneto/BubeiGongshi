# CORE-76 测试方案

> 来源卡：[S0_CORE-76_基座.md](../../S0/S0_CORE-76_基座.md)（现行评级统计与就绪证据核对）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18] ID数相同但替换未知/重复/遗漏均失败；等级读取最右复核列，旧列不覆盖新列。
- [R18] 就绪缺独立记录、S2非pass、conclusion非pass或公共消费者确认缺失均失败；全部证据满足夹具通过；--check拒绝手工改统计数字。
- [R18] 状态表头改名、缺失或重复（须恰有一个“当前状态”和一个“编号”列），以及数据行宽与表头不等，均失败，不得借此跳过就绪证据检查（T1-F10）。
- [R18] 夹具放tools/sadd/fixtures/core76/：pass/（三张假卡的最小SADD目录，含D.10、D.12与reports/v9.9.9-reviews.json，其中一卡就绪且证据齐全、一卡B、一卡—）为通过基准；其余反例各自只改基准的一处。
- [R18] validateCurrent逐项反例各返回含`SADD-12: `的错误：重复record、reviews.version为2、materialChars为-1、segments为0、grade与D.10最新列不一致、D.12行的复核人/日期/字符/分段/a～g或S1～S6旗标与JSON任一不符；状态为裸“就绪”、“就绪（D.12 P2-其他卡）”或最右复核列为未知版本导致找不到记录时均失败；基准返回空数组且不抛异常。
- [R18] stats.mjs：基准下--check退出0；手改区块内就绪数退出1并输出`SADD stats drift`；删除起止标记退出2且stderr含`Missing stats block`；reviews JSON损坏退出2；不带--check只改写两标记之间内容，区块外字节不变。
- [R18] audit.mjs：对基准目录用--sadd与--out运行，输出含stats/errors/warnings/materials且每卡一条材料记录；不传--out时写build/sadd/audit.json；运行前后SADD/reports/下既有文件字节不变；一张假卡材料超80000时只计入overLimit，等级、errors与退出码不变；任一validateCurrent错误时退出1。
- [R18] 就绪字符串唯一：仅 就绪（D.12 P2-<card>） 精确匹配才计入就绪；就绪（D.12 第 3 行）、裸 就绪、就绪（D.12 P2-其他卡）均失败，且 audit.stats.ready 不把它们计入（不得用前缀匹配计数）。
- [R18] D.12 解析协议反例：单元格内含 |（行宽不符）、表头字段改名、缺表头、同一 record 两次均失败；D.12 早期序号表（record 列非 P2-<card>）整行忽略而不报错；## D.12 到 ## D.13 之外的内容不参与匹配。
- [R18] audit 报告字段：version===1、toolchain.node 等于 process.version、toolchain.sadd 等于 --sadd 解析值、stats 含 cards/CORE/AND/WIN/currentRows/ready/grades、materials 每卡一条且按 chars 降序并含 overLimit 布尔、warnings 每项 kind 属于 outside-closure/missing-local-definition/sdk-unknown/q-drift 且带对应 evidence、errors 每条以 SADD-12: 开头。
- [R18] 历史快照只读：预置 SADD/reports/ 下旧版本文件，stats（带与不带 --check）与 audit 运行后其内容哈希不变；v5.3.3-reviews.json 含 v5.3.4 记录时只报版本不一致 warning，不重建、不改写、不改列名。
- [R18] reviewColumn：表头含多列 vX.Y.Z 复核 时返回最右列下标，无匹配返回 -1，与 validateCurrent 的等级列选择一致。
