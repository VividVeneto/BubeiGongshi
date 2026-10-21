# CORE-57 测试方案

> 来源卡：[S0_CORE-57_基座.md](../../S0/S0_CORE-57_基座.md)（会话材料生成与文档统计工具）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R20] `node --test tools/sadd/pack.test.mjs` 遍历所有有效卡：目标与直接契约完整、分段不超过 80000 字符、拼回后无内容丢失；未知卡和越界路径失败。
- [R20] 对 WIN-13、AND-12、WIN-14、WIN-08、CORE-50 输出裁剪清单、总量和分段数；超量明确报警，未创建文件明确列出。

- [R18] 材料打包回归覆盖现存/缺失平台锁、依赖卡契约文件、仓库存在但材料缺少的本地类型（显示来源卡及warning）；统计ID集合即使行数相等也拒绝未知/遗漏/重复及非法等级，就绪只读当前状态列。

- [R18] --check-budget对超80000的夹具返回1并保留报告；仅明标下游的引用不展开，混合未分类引用仍全文收录；ADR无关章节排除且列标题、相关章节保留全文。不得用普通字段名触发间接整闭包。

- [R18] 真实材料对CORE-67的34份ready schema及types.schema.json、CORE-75的shared-writes.json均在 files 或 filteredFiles 中有记录，--file 可取回全文；无关 schema 只列名（大小与 SHA-256）、相关 schema 完整；manifest/shared-writes 过滤结果为合法 JSON 且条目与原文件逐字节一致；types 切片含内部引用闭包；旧 part-*.md 被清理；删除引用文件时列入missing；额外引用/$ref越界失败，所有分段拼接逐字节等于 material.md。

- [R18] 间接依赖夹具：定义所需符号的 struct、impl、const、错误码表行、op 行及其传递定义被收录，只提及符号的说明块与无关定义不收录，mentionOnly 计数正确。

- [R18] 测试方案默认不收录：默认材料中有测试方案的卡只保留“验收标准”引用行、头部说明目标卡测试方案路径且 report.tests 为 "excluded"；`--with-tests`（withTests）时目标卡正文含测试方案全文、report.tests 为 "included"；两种方式 testFile 路径相同。
