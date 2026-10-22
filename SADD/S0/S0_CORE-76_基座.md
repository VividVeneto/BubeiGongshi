### CORE-76 现行评级统计与就绪证据核对

**目标**：从独立复核记录计算现行等级与就绪数，拒绝仅有表格字样而无证据的就绪声明。

**范围**
- 包含：tools/sadd/current.mjs/current.test.mjs、stats.mjs、audit.mjs与逐卡复核机器记录；从CORE-57拆出统计职责。仓库中已有的这三份脚本即本卡先行实现，编码会话在其上按本契约补齐退出码、验收测试与夹具并签核，不重写；它们是模块卡实现（需整卡复核与评级），不同于README §7.1列出的文档工具项。
- 不包含：材料选择、业务检查与自动语义评级；等级必须由非作者提供。

**依赖**：CORE-01、CORE-02、CORE-57

**接口契约**
node tools/sadd/stats.mjs [--check]只生成D中bounded stats区块，--check遇漂移退出1；audit.mjs [--sadd <dir>] [--out <file>]逐卡pack并报告materials/warnings/errors/stats，默认build/sadd/audit.json，输出目录可覆盖，不覆盖旧版本快照。输入D.10现行ID集合必须与有效卡精确相等，重复/未知/遗漏/非法等级失败；等级列取最右vX.Y.Z复核，不硬编码旧版本。
stats 区块固定为三行表（CORE/AND/WIN 的有效卡数与历史撤销）加一行总计，内容只由现行卡与 D.10 生成，不带实现或真机结论。audit 报告固定 {version: 1, toolchain: {node: process.version, sadd: <--sadd 解析后的路径>}, stats: {cards, CORE, AND, WIN, currentRows, ready, grades}, errors: string[], warnings: [{id, kind, evidence}], materials: [{id, chars, segments, overLimit}]}：warnings 的 kind 为闭集 outside-closure | missing-local-definition | sdk-unknown | q-drift（前两类 evidence 带 missingFromMaterials，第三类带 undefinedIdentifiers，q-drift 带 q 编号与 affected/mentioned 布尔）；materials 按 chars 降序，overLimit 为 chars>80000 的布尔值；errors 每条以 SADD-12: 开头；JSON 以 2 空格缩进写出，写出前不读旧快照、也不改写 SADD/reports/ 下任何文件。现实现缺 version/toolchain、kind 与 overLimit（见“实现约束”），编码会话按本表补齐。

导出与退出码：current.mjs导出`reviewColumn(columns: string[]): number`（表头中最右一个匹配`vX.Y.Z 复核`的列下标，无则-1）与`validateCurrent(rows: string[], columns: string[], cards, reviews, appendix = ''): string[]`（rows为D.10数据行原文，columns为表头去空白单元格，cards为pack.mjs load()返回的卡号→卡对象Map，reviews为复核机器记录根对象，appendix为附录D全文；返回错误字符串数组，每条以`SADD-12: `开头，空数组表示通过，不抛异常）。stats.mjs与audit.mjs退出码：0无错误；1为validateCurrent错误、统计漂移（stderr `SADD stats drift`）或D.10行数与卡数不等；2为读写/解析错误（附录D或reviews文件不可读、JSON损坏、缺统计区块`Missing stats block`）。现有实现以未捕获异常退出1，编码会话按本表把解析类改为2。统计区块以`<!-- sadd-current-stats:start -->`与`<!-- sadd-current-stats:end -->`为界，stats.mjs不带--check时只改写两标记之间的内容。复核机器记录路径为`SADD/reports/<v>-reviews.json`，<v>取D.10最右复核列的版本号（如v5.3.3），不硬编码；文件不存在时按`{version:1,entries:[]}`处理，任何非—等级随之失败。 stats 与 audit 的全部读写与解析必须包在 try/catch 中：附录 D、reviews 文件、README 任一不可读或 JSON.parse 失败，一律 stderr 输出一行含原因（缺统计区块时含 Missing stats block）并以 2 退出，不得以未捕获异常退出 1；validateCurrent 返回非空时以 1 退出。

reports/<v>-reviews.json（本轮为v5.3.3）固定version=1、entries每卡{record:"P2-<card>",card,grade:A|B|C,reviewer,date:YYYY-MM-DD,materialChars,segments,checks:{a,b,c,d,e,f,g,S1,S2,S3,S4,S5,S6},conclusion:pass|fail|pending,blockers:string[],consumerConfirmation:string|null}。checks每项pass/fail/pending；grade与D.10最新列必须一致，材料字符数非负整数/段数≥1。每个非—等级须有独立记录。当前状态写就绪时还须A/B、全部checks=pass、conclusion=pass；被直接依赖的CORE公共卡另须consumerConfirmation，不可拿其他卡历史通过记录代替。本轮记录与D.12可读表一一对应，日期/复核人/理由不能省略；脚本不证明复核人独立，lead人工签核身份。
audit将闭包外、本地缺定义、SDK未知、Q关联差异分项保留来源。超80000只计材料超量，不自动降级或偷偷裁剪；最终整卡复核须判定是否阻断。D.10/D.12/报告应同步，CORE-70（下游说明，非契约）发布完整性检查要求所有现行卡有记录；未完成独立复核不填假等级。

D.12 的 P2 记录固定列（表头逐字）：`| 记录 | 卡 | 复核人 / 日期 | 复核输入字符 / 段 | a～g | S1～S6 | 发现、处理及调用方确认 | conclusion |`，record 必须为 P2-<card>，卡列等于 record 的卡号。解析协议固定：用 `## D.12 ` 起、`## D.13 ` 止（无 D.13 则到附录文末）截出复核区块；只对以 | 开头且不以 | --- 开头的行按 | 切分，丢弃首尾空串并 trim；表头行（首格为“记录”）只用于宽度校验，字段名改名即失败，不得按位置猜列；record 不匹配 ^P2-(CORE|AND|WIN)-d+$ 的行（如 D.12 早期序号表）整行忽略；单元格内出现 | 会导致行宽不符，按失败处理；同一 record 出现两次失败。旗标 P=pass/F=fail/?=pending，13 位齐全且顺序为 a～g、S1～S6。validateCurrent接收附录全文，逐项核对机器记录的ID/复核人/日期/字符/分段/13旗标/conclusion及重复record；报告version必须1。所有以“就绪”开头的状态必须精确等于“就绪（D.12 P2-<card>）”，否则失败。就绪字符串的唯一来源是本卡：README §8.5.1 原文的“就绪（D.12 第 n 行）”已废弃并由 CO-43 改为同一写法，任何前缀匹配（如 /^就绪（/）都不算就绪；audit.stats.ready 只统计与该字符串精确相等的行。裸就绪、其他引用、未知版本、缺D.12或不一致不能绕过。

**实现约束**
- Node标准库；Node版本读CORE-01的tools/toolchain.versions中node=，锁版前保留先行设计工具身份并在报告记录实际版本。历史v5.3.2报告只读保留，P2另存；audit默认只写build/sadd/audit.json，--out指定新路径，不改写SADD/reports/下既有快照。
- 迁移计划（只列计划，本轮不重建历史）：SADD/reports/v5.3.3-reviews.json 实际已含 v5.3.4 数据（D.10 把 29 卡重登记为 v5.3.4，复核列名仍为 v5.3.3），因此不存在 v5.3.4-reviews.json。下一轮开工前只读复制 v5.3.3-reviews.json 为 v5.3.4-reviews.json，按 record 补记 v5.3.4 结论，再把 D.10 复核列改名为 v5.3.4 列；v5.3.3 与其它历史快照字节不变，不重建、不改写、不追溯评级。迁移完成前 audit 以 warning 记录“复核列版本与 reports 文件名不一致”，不自动改列名。
- 现实现与本节的差距（属编码交付，不是设计缺口）：stats.mjs/audit.mjs 存在未捕获异常（退出 1 而非 2）、无 stats.test.mjs 与 audit.test.mjs、无 tools/sadd/fixtures/core76/；audit 未写 version/toolchain、warnings 未分 kind、materials 无 overLimit、ready 用前缀匹配；current.test.mjs 只测 validateCurrent，未测 reviewColumn。
- 依赖CORE-02只是全卡通用前提（错误码与提交约定），本卡不使用FmlError、不新增错误码；依赖CORE-57为调用pack()取得材料字符数与warning。
- 当前评级是文档可编码性，不代表实现或设备测试完成；外部门槛与独立消费确认缺失不得生成就绪。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-76_TEST.md](../Test/S0/S0_CORE-76_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约190行；tools/sadd/current.mjs、stats.mjs、audit.mjs及本卡编写的CLI/聚合接入行；不计自测、tools/sadd/fixtures/core76/夹具、审计记录/卡片数据与生成报告；不含README §7.1排除的layout/split/split-tests/cardiff及tools/DTOcheck/。

