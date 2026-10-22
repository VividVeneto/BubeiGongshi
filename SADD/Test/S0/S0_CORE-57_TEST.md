# CORE-57 测试方案

> 来源卡：[S0_CORE-57_基座.md](../../S0/S0_CORE-57_基座.md)（会话材料生成与文档统计工具）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R20] `node --test tools/sadd/pack.test.mjs` 遍历所有有效卡：目标与直接契约完整、分段不超过 80000 字符、拼回后无内容丢失；未知卡和越界路径失败。
- [R18] 五张指定超量卡的裁剪清单与分段可机器断言（五卡在此只作只读样本枚举，非本卡契约依赖，不得因此把它们展开进材料）：对 WIN-13、AND-12、WIN-14、WIN-08、CORE-50 逐个调用 pack(id)，断言 report.chars 等于 material.md 的 Unicode code point 长度、report.segments 等于实际写出的 part-N.md 个数且编号自 1 连续、chars>80000 时 overLimit===true 且 warnings 含超量项、report.manifest 非空且每项含 card/before/after/retained、report.missing 含未创建的锁文件。断言不写死字符数（卡内容变化不应假失败）；实测值只记入复核记录：2026-10-22 基线 d09b4b1 测得 WIN-13 241254 字符/4 段、AND-12 202371/3、WIN-14 239787/4、WIN-08 257330/4、CORE-50 288314/4，五卡均 overLimit。

- [R18] 材料打包回归覆盖现存/缺失平台锁、依赖卡契约文件、仓库存在但材料缺少的本地类型（显示来源卡及warning）。
- [R18] 公开面稳定：从 ./pack.mjs 可导入并调用 ROOT、FILES、load、pack、segment、blocks、definedSymbols、schemaRefs、jsonItems、filterJsonArray、filterJsonObject、writeOutput；pack() 返回 {text, chunks, report} 且 report 字段集合等于卡内固定字段表所列 17 项加 reading、removedStaleParts、node 共 20 项（顺序同卡内固定字段表）；未知卡、缺失卡、路径越界分别抛错且 CLI 非零退出；writeOutput() 返回 {parts, removedStaleParts}。

- [R18] --check-budget 以子进程断言：spawnSync(process.execPath, ['tools/sadd/pack.mjs', <超量卡号>, '--out', <临时目录>, '--check-budget']) 的 status===1，且该目录下 report.json 的 overLimit===true、material.md 与 part-*.md 齐全；对同一输入去掉该开关断言 status===0。总量超限不得实现成拒绝或裁剪，只有单个不可分块超过 80000 才是错误。仅明标下游的引用不展开，混合未分类引用仍全文收录；ADR 无关章节排除且列标题、相关章节保留全文。不得用普通字段名触发间接整闭包。另断言无卡号调用 status===2（用法错误，不写出材料），与卡内退出码分配一致。

- [R18] 真实材料对CORE-67的34份ready schema及types.schema.json、CORE-75的shared-writes.json均在 files 或 filteredFiles 中有记录，--file 可取回全文；无关 schema 只列名（大小与 SHA-256）、相关 schema 完整；manifest/shared-writes 过滤结果为合法 JSON 且条目与原文件逐字节一致；types 切片含内部引用闭包；旧 part-*.md 被清理；删除引用文件时列入missing；额外引用/$ref越界失败，所有分段拼接逐字节等于 material.md。

- [R18] 间接依赖夹具：定义所需符号的 struct、impl、const、错误码表行、op 行及其传递定义被收录，只提及符号的说明块与无关定义不收录，mentionOnly 计数正确。

- [R18] 测试方案默认不收录：默认材料中有测试方案的卡只保留“验收标准”引用行、头部说明目标卡测试方案路径且 report.tests 为 "excluded"；`--with-tests`（withTests）时目标卡正文含测试方案全文、report.tests 为 "included"；两种方式 testFile 路径相同。
