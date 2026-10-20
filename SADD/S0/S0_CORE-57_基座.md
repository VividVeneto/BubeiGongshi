### CORE-57 会话材料生成与文档统计工具

**目标**：确定性组装 README §8.1 材料，报告裁剪与超量，避免缺失依赖时猜测实现。

**范围**
- 包含：`tools/sadd/pack.mjs`、测试；材料清单、缺失文件报告、符号选择与无损分段；文档统计入口转CORE-76（下游说明，非契约）。
- 不包含：业务代码、就绪评级与自动语义认证。

**依赖**：CORE-01、CORE-02

**接口契约**

`node tools/sadd/pack.mjs <卡号> [--out <目录>] [--sadd <SADD目录>] [--file <已有实现或契约文件>]`。
输出 `material.md`（总材料）、`report.json`（字符数、依赖闭包、每卡裁剪前后、保留标识符、闭包外引用、未创建文件、待人工核实标识符）、`part-N.md`（按段落、表格、完整代码块无损分段）。字符数按 Unicode code point；单段上限 80000；总材料超限报警，不能把单个分段视为完整材料。
目标全文、直接依赖及 CORE-01/02 完整契约不裁剪。间接依赖只选择“定义”了所需标识符的完整代码块/表格/段落（struct/enum/class/trait/type/typedef/interface/mixin/union/mod 声明、impl/extension 块、const、表格首列、行首 op 名），新收块中的标识符继续传递，递归到不再增加符号；绝不剪开定义；只提到所需标识符而不定义它的块不收录，report.manifest[].mentionOnly 记其块数。目标显式引用的闭包外卡默认取完整契约并报警；只有每一处引用所在行均明确标“下游说明，非契约”或“只读样本”时，才保留目标原行而不反向展开该卡契约，report.classifiedReferences记录证据。同卡还有未分类引用时仍保守收全。README §5 需求行、§6 影响行/引用行、锁文件、`--file` 指定的现有实现一并收录；附录 A 只收录目标卡与直接依赖收录文本引用的 ADR 行、“模块卡”列含目标卡的 ADR 行（附表头）及引用目标卡或这些 ADR 的补充章节全文；缺文件明确列未创建。
未定义标识符启发式扫描只给 warning：SDK 与第三方符号必须由复核人核实来源，不允许自动当成已定义。卡不存在、循环依赖、目录穿越、单个不可分块超过 80000 时非零退出。
文档统计从卡标题、阶段与附录 D 当前状态逐行计算；历史评级不自动提升。CORE-41（下游说明，非契约）接入本工具与检查报告。

P2材料控制：间接符号选择只连接类型/错误码/op身份，不用profile_id等普通字段名扩大闭包；相关ADR补充章节全文保留，按本卡/其相关ADR关联，未选标题列report.excludedSupplements供语义复核。直接契约仍完整，不以压缩静默丢定义。--check-budget使总量>80000退出1，报告和无损分段仍写出；CI开工门禁必须用该开关，超限必须拆卡/修依赖/完成显式符号方案后复检，不能只登记分段视为关闭。闭包外、本地缺定义、SDK未知、Q差异分四类分别归owner处理，未分类项继续warning且阻止语义通过。P2尚未逐条关闭全部历史warning，H07结论为部分修订。

已有contracts输入按明确完整路径收集，不要求Markdown反引号，只收录与“相关卡”（目标卡、直接依赖、CORE-01/02）相关的部分：DTO schema 在被 --file 指定、属于相关卡拥有的 op（以 manifest.json 的 owner 为准）、被相关卡收录文本按路径引用或被已收录 schema 经 $ref 引用时收录全文；types.schema.json 按 $defs 条目切片（$ref 引用、相关卡文本出现的类型名及其内部引用闭包），保留完整 JSON 结构与条目原文；manifest.json 与 shared-writes.json 只收录 owner ∈ 相关卡的条目，条目与原文件逐字节一致，头部写原文件 SHA-256 与条目数；contracts/vectors 在相关卡正文或验收引用其文件名时收录；其余 contracts 文件在材料末尾清单中列名并给出字节数与 SHA-256。report.files列全文收录文件，report.filteredFiles列每个列名/切片/过滤文件的 path、mode、originalBytes、includedBytes、reason、sha256，report.reading说明 material.md 与 part-N.md 内容相同、二者择一阅读；写出前清理输出目录旧 part-*.md，分段各段拼接逐字节等于 material.md。missing列明确引用但未创建文件。未知路径/外部URL/越出contracts引用失败，不能静默忽略。

**实现约束**
- Node 版本以 `tools/toolchain.versions` 的 `node=` 为准；该文件由 CORE-01 创建，创建前用当前 Node LTS 运行；`report.json` 记录实际 `process.version`。仅标准库；报告生成时间不参与正文内容或字符分段判断以外的契约选择。
- 裁剪清单与所有分段共同交给编码会话；需要未保留的符号时补材料并重跑，禁止推测。
- 超量卡在附录 D 记录总字符数与分段数。外部前提：已锁定的 Node。
- 现状：本工具已在 v5.3.2 的文档修订中先行入库（`tools/sadd/`），供文档修订与材料统计使用。它不因此视为本卡完成：本卡仍须按 README §8.5.1 通过整卡复核，并在 CORE-01 锁定 Node 版本后重跑验收；在此之前它的输出只作材料清单，不作就绪证据。测试按文件运行（`node --test tools/sadd/pack.test.mjs tools/sadd/current.test.mjs`），不要把目录作为 `--test` 参数。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-57_TEST.md](../Test/S0/S0_CORE-57_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 380 行；主包 `tools/sadd/pack.mjs`（约220）与pack.test.mjs（约160）；current/stats/audit及其测试唯一归CORE-76（下游说明，非契约），本卡不重复实现。

