### CORE-57 会话材料生成与文档统计工具

**目标**：确定性组装 README §8.1 材料，报告裁剪与超量，避免缺失依赖时猜测实现。

**范围**
- 包含：`tools/sadd/pack.mjs`、测试；材料清单、缺失文件报告、符号选择与无损分段；文档统计入口转CORE-76（下游说明，非契约）。
- 不包含：业务代码、就绪评级与自动语义认证。

**依赖**：CORE-01、CORE-02

**接口契约**

`node tools/sadd/pack.mjs <卡号> [--out <目录>] [--sadd <SADD目录>] [--file <已有实现或契约文件>] [--with-tests] [--check-budget]`。
测试方案（2026-10-21 起，README §8.1 第 7 项）：默认不收录 `Test/`，材料中所有卡的“验收标准”只保留引用行，头部说明目标卡测试方案路径，report.tests 为 `"excluded"`；`--with-tests` 时按引用把测试方案拼回各卡（report.tests 为 `"included"`），用于原卡变更或按卡写测试的编码会话。导出函数 `load(sadd, {tests})`、`pack(id, {withTests})` 同此语义。
导出签名（`tools/sadd/pack.mjs` 的公开面；编码会话不得改名、增删或调换形参顺序）：`ROOT: string`（仓库根）；`FILES`（自 `layout.mjs` 再导出）；`load(sadd = ROOT/SADD, {tests = true} = {}): Map<卡号, {id, doc, file, line, body, contract, deps, testFile?}>`；`pack(id, {sadd = ROOT/SADD, extra = [], withTests = false} = {}): {text, chunks, report}`；`segment(text, limit = 80000): string[]`；`blocks(text): string[]`；`definedSymbols(text): Set<string>`；`schemaRefs(value, out = []): string[]`；`jsonItems(text, key): string[]`；`filterJsonArray(text, key, predicate): {text, kept, total}`；`filterJsonObject(text, key, predicate): {text, kept, total}`；`writeOutput(out, result, extra = {}): {parts, removedStaleParts}`。`listContracts`、`skipString`、`skipValue`、`members`、`rebuild`、`selectAdr` 为内部函数，不导出。消费者（签名或行为变更须同步并回归）：tools/sadd/audit.mjs（load、pack、ROOT）、tools/sadd/stats.mjs（load、ROOT）、tools/sadd/reservations.mjs（load、ROOT）、tools/DTOcheck/lib.mjs（load、ROOT、FILES）、tools/DTOcheck/layout.test.mjs（load）；回归入口 node --test tools/sadd/pack.test.mjs tools/sadd/current.test.mjs tools/sadd/reservations.test.mjs tools/DTOcheck/layout.test.mjs 与 node tools/DTOcheck/run.mjs --strict。注意 load() 默认 tests=true、pack() 默认 withTests=false，两者不是同一开关。`pack()` 在卡号不存在、卡文件缺失、依赖环、路径越界、外部或越出 contracts/ 的引用时抛错；CLI 捕获后按 :19 的退出码分类退出（契约或用法错误 2、未预期内部异常 3），进程非零退出且不写出半成品材料。
输出 `material.md`（总材料）、`report.json`（字段见下）、`part-N.md`（按段落、表格、完整代码块无损分段；编号自 1 连续，目录内其它 `part-*.md` 写出前删除）。字符数按 Unicode code point。两个阈值分开执行，不得合并成“超限即失败”：①单段上限 80000——每段必须 ≤80000，唯一失败原因是某个不可分块自身超过 80000（抛错、非零退出、不写出残缺材料，须拆卡或拆块）；②总量 80000——`chars > 80000` 时仍完整写出 `material.md`、全部 `part-N.md` 与 `report.json`，置 `overLimit=true` 并在 warnings 与 stdout 报警，不丢块、不截断、不改写原文；单个分段不能当作完整材料。只有显式 `--check-budget` 才在总量超限时另以退出码 1 报告（见“P2材料控制”）。
`report.json` 固定字段（顺序即写出顺序）：`id, chars, overLimit, segments, tests, closure, related, manifest, files, filteredFiles, adr, missing, warnings, missingFromMaterials, undefinedIdentifiers, classifiedReferences, excludedSupplements`，另加 `reading`（说明 material.md 与 part-N.md 内容相同、二者择一阅读）、`removedStaleParts`（被清理的旧分件名数组）与 `node`（写材料时的 `process.version`）。`closure` 为直接依赖卡号，`related` 为目标卡加闭包；`manifest` 每项 `{card, mode: target | full-contract | outside-context | symbols, before, after, retained, mentionOnly?}`；`files` 为全文收录的 contracts 路径；`filteredFiles` 每项 `{path, mode: filtered | sliced | listed, originalBytes, includedBytes, reason, sha256, kept?, total?, entries?}`；`missing` 为明确引用但未创建的文件；`warnings` 为字符串数组，闭包外引用、本地缺定义、卡引用缺失由本卡 owner 处理，SDK/第三方未知标识符须复核人核实来源（Q 关联差异由 CORE-76 的 audit 统计，不在本卡；下游说明，非契约）；`classifiedReferences` 每项 `{card, kind, evidence}`；`excludedSupplements` 为按标题排除的附录 A 补充章节。
目标全文、直接依赖及 CORE-01/02 完整契约不裁剪。间接依赖只选择“定义”了所需标识符的完整代码块/表格/段落（struct/enum/class/trait/type/typedef/interface/mixin/union/mod 声明、impl/extension 块、const、表格首列、行首 op 名），新收块中的标识符继续传递，递归到不再增加符号；绝不剪开定义；只提到所需标识符而不定义它的块不收录，report.manifest[].mentionOnly 记其块数。目标显式引用的闭包外卡默认取完整契约并报警；只有每一处引用所在行均明确标“下游说明，非契约”或“只读样本”时，才保留目标原行而不反向展开该卡契约，report.classifiedReferences记录证据。同卡还有未分类引用时仍保守收全。README §5 需求行、§6 影响行/引用行、锁文件、`--file` 指定的现有实现一并收录；附录 A 只收录目标卡与直接依赖收录文本引用的 ADR 行、“模块卡”列含目标卡的 ADR 行（附表头）及引用目标卡或这些 ADR 的补充章节全文；缺文件明确列未创建。
未定义标识符启发式扫描只给 warning：SDK 与第三方符号必须由复核人核实来源，不允许自动当成已定义。卡不存在、循环依赖、目录穿越、单个不可分块超过 80000 时非零退出。退出码分配（消除一码两义）：0=正常，含总量超 80000 但未带 --check-budget；1=带了 --check-budget 且总量超限；2=用法或契约错误（无卡号、卡不存在、缺失卡文件、依赖环、路径越界、单个不可分块超 80000），须给出简短原因且不写出半成品材料；3=未预期内部异常。CLI 须捕获错误并按上述分类退出，不得让未捕获异常落到 1。
文档统计从卡标题、阶段与附录 D 当前状态逐行计算；历史评级不自动提升。CORE-41（下游说明，非契约）接入本工具与检查报告。

P2材料控制：间接符号选择只连接类型/错误码/op身份，不用profile_id等普通字段名扩大闭包；相关ADR补充章节全文保留，按本卡/其相关ADR关联，未选标题列report.excludedSupplements供语义复核。直接契约仍完整，不以压缩静默丢定义。--check-budget使总量>80000退出1，报告和无损分段仍写出；CI开工门禁必须用该开关，超限必须拆卡/修依赖/完成显式符号方案后复检，不能只登记分段视为关闭。闭包外、本地缺定义、SDK未知、Q差异分四类分别归owner处理，未分类项继续warning且阻止语义通过。P2尚未逐条关闭全部历史warning，H07结论为部分修订。`--check-budget` 的验收入口是自动化测试，不是人工试跑：编码会话在 `tools/sadd/pack.test.mjs` 用 `spawnSync(process.execPath, ['tools/sadd/pack.mjs', <超量卡号>, '--out', <临时目录>, '--check-budget'])` 断言退出码为 1、`report.json` 已写出且 `overLimit === true`、`material.md` 与全部分段齐全；对同一输入去掉该开关断言退出码为 0。现仓库内尚无此断言（先行实现缺口，见“现状”），不计作设计缺口。

已有contracts输入按明确完整路径收集，不要求Markdown反引号，只收录与“相关卡”（目标卡、直接依赖、CORE-01/02）相关的部分：DTO schema 在被 --file 指定、属于相关卡拥有的 op（以 manifest.json 的 owner 为准）、被相关卡收录文本按路径引用或被已收录 schema 经 $ref 引用时收录全文；types.schema.json 按 $defs 条目切片（$ref 引用、相关卡文本出现的类型名及其内部引用闭包），保留完整 JSON 结构与条目原文；manifest.json 与 shared-writes.json 只收录 owner ∈ 相关卡的条目，条目与原文件逐字节一致，头部写原文件 SHA-256 与条目数；但若某文件的单写维护者卡（policy 中 kind=file 且 key 为该文件路径的条目的 owner）在相关卡内，则该文件整文件收录并记 warning（CO-60-1/F-75-01）；owner 过滤结果为 0 条时同样记 warning、不静默；contracts/vectors 在相关卡正文或验收引用其文件名时收录；其余 contracts 文件在材料末尾清单中列名并给出字节数与 SHA-256。report.files列全文收录文件，report.filteredFiles列每个列名/切片/过滤文件的 path、mode、originalBytes、includedBytes、reason、sha256，report.reading说明 material.md 与 part-N.md 内容相同、二者择一阅读；写出前清理输出目录旧 part-*.md，分段各段拼接逐字节等于 material.md。missing列明确引用但未创建文件。未知路径/外部URL/越出contracts引用失败，不能静默忽略。

**实现约束**
- Node 版本以 `tools/toolchain.versions` 的 `node=` 为准；该文件由 CORE-01 创建，创建前用当前 Node LTS 运行；`report.json` 记录实际 `process.version`。仅标准库；报告生成时间不参与正文内容或字符分段判断以外的契约选择。
- 裁剪清单与所有分段共同交给编码会话；需要未保留的符号时补材料并重跑，禁止推测。
- 超量卡在附录 D 记录总字符数与分段数。外部前提：已锁定的 Node。
- 现状：本工具已在 v5.3.2 的文档修订中先行入库（`tools/sadd/`），供文档修订与材料统计使用。它不因此视为本卡完成：本卡仍须按 README §8.5.1 通过整卡复核，并在 CORE-01 锁定 Node 版本后重跑验收；在此之前它的输出只作材料清单，不作就绪证据。先行实现与本节契约的已知差距只有两处，均由编码会话补齐、不影响设计成立：`tools/sadd/pack.test.mjs` 尚未覆盖 `--check-budget` 退出码与五张超量卡（WIN-13、AND-12、WIN-14、WIN-08、CORE-50；此处只作只读样本列举，非本卡契约依赖，pack 不因其展开这些卡的契约）的裁剪清单断言；`report.json` 字段虽已按上表写出，但导出签名尚未写进卡内（本节已补），编码会话须保证签名不再漂移。任何按“总量超 80000 即失败或裁剪”的实现都是违反本卡，须先改设计而非改验收。测试按文件运行（`node --test tools/sadd/pack.test.mjs tools/sadd/current.test.mjs`），不要把目录作为 `--test` 参数。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-57_TEST.md](../Test/S0/S0_CORE-57_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约430行；tools/sadd/pack.mjs及本卡自行编写的打包辅助/调用接入行；不计自测、夹具、卡片/契约/schema数据和打包生成物；README §7.1列明的layout/split/split-tests/cardiff及tools/DTOcheck/不归本卡、不计本卡规模。

