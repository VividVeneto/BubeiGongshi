# CORE-74 测试方案

> 来源卡：[S0_CORE-74_基座.md](../../S0/S0_CORE-74_基座.md)（unsafe、ABI与错误注册表门禁）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R19] 每个规则有正反例：非白名单crate出现unsafe报UNSAFE-1（1）；`// SAFETY:`缺失、内容为空或仅标点报UNSAFE-2（1）；头删除函数、改struct字段顺序或类型文本、删除宏而未升ABI_MAJOR均报ABI-1（1），新增函数未升MINOR报ABI-1（1）；生成物与registry一致退出0，任一投影漂移或生成物缺失报ERR-1（1），未注册字面量ERR-2、同code重复或owner不一致ERR-3；FML_THEME_MISSING不误报；未知C语法、registry或生成物不可解析退出2；registry未创建时ERR-4输出“实现注册表未启用”并退出2。
- [R23] ABI主版本提升并有ADR时不报ABI-1；`--base-ref`指向`sadd-v*`/`archive/*`文档标签或不可解析ref退出2；无`abi-v*`基准且未标首发退出2，`--first-release`输出`ABI baseline: first-release`且只做自包含fixture；浅clone（is-shallow-repository=true）且未给`--base-ref`退出2。
