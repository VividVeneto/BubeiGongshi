### CORE-76 现行评级统计与就绪证据核对

**目标**：从独立复核记录计算现行等级与就绪数，拒绝仅有表格字样而无证据的就绪声明。

**范围**
- 包含：current.mjs/current.test.mjs、stats.mjs、audit.mjs与逐卡复核机器记录；从CORE-57拆出统计职责。
- 不包含：材料选择、业务检查与自动语义评级；等级必须由非作者提供。

**依赖**：CORE-01、CORE-02、CORE-57

**接口契约**
node tools/sadd/stats.mjs [--check]只生成D中bounded stats区块，--check遇漂移退出1；audit.mjs [--sadd <dir>] [--out <file>]逐卡pack并报告materials/warnings/errors/stats，默认build/sadd/audit.json，输出目录可覆盖，不覆盖旧版本快照。输入D.10现行ID集合必须与有效卡精确相等，重复/未知/遗漏/非法等级失败；等级列取最右vX.Y.Z复核，不硬编码旧版本。
reports/v5.3.3-reviews.json固定version=1、entries每卡{record:"P2-<card>",card,grade:A|B|C,reviewer,date:YYYY-MM-DD,materialChars,segments,checks:{a,b,c,d,e,f,g,S1,S2,S3,S4,S5,S6},conclusion:pass|fail|pending,blockers:string[],consumerConfirmation:string|null}。checks每项pass/fail/pending；grade与D.10最新列必须一致，材料字符数非负整数/段数≥1。每个非—等级须有独立记录。当前状态写就绪时还须A/B、全部checks=pass、conclusion=pass；被直接依赖的CORE公共卡另须consumerConfirmation，不可拿其他卡历史通过记录代替。本轮记录与D.12可读表一一对应，日期/复核人/理由不能省略；脚本不证明复核人独立，lead人工签核身份。
audit将闭包外、本地缺定义、SDK未知、Q关联差异分项保留来源。超80000只计材料超量，不自动降级或偷偷裁剪；最终整卡复核须判定是否阻断。D.10/D.12/报告应同步，CORE-70（下游说明，非契约）发布完整性检查要求所有现行卡有记录；未完成独立复核不填假等级。

D.12的P2记录固定列record/card/复核人与日期/材料字符与段数/a～g旗标/S1～6旗标/理由/conclusion，record必须P2-<card>。旗标P=pass/F=fail/?=pending。validateCurrent接收附录全文，逐项核对机器记录的ID/复核人/日期/字符/分段/13旗标/conclusion及重复record；报告version必须1。所有以“就绪”开头的状态必须精确等于“就绪（D.12 P2-<card>）”，否则失败。裸就绪、其他引用、未知版本、缺D.12或不一致不能绕过。

**实现约束**
- Node标准库，锁版前保留先行设计工具身份；实际Node版本见报告。历史v5.3.2报告只读保留，P2另存。
- 当前评级是文档可编码性，不代表实现或设备测试完成；外部门槛与独立消费确认缺失不得生成就绪。

**验收标准**
- [R18] ID数相同但替换未知/重复/遗漏均失败；等级读取最右复核列，旧列不覆盖新列。
- [R18] 就绪缺独立记录、S2非pass、conclusion非pass或公共消费者确认缺失均失败；全部证据满足夹具通过；--check拒绝手工改统计数字。

- [R18] 状态表头改名、缺失或重复（须恰有一个“当前状态”和一个“编号”列），以及数据行宽与表头不等，均失败，不得借此跳过就绪证据检查（T1-F10）。

**规模**：约 380 行；主包tools/sadd/（current100、stats60、audit70、测试150）；复核JSON与Markdown是数据。

