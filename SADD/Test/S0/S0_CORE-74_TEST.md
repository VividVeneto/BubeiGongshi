# CORE-74 测试方案

> 来源卡：[S0_CORE-74_基座.md](../../S0/S0_CORE-74_基座.md)（unsafe、ABI与错误注册表门禁）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R19] 每个规则有正反例：非白名单crate出现unsafe报UNSAFE-1（1），白名单夹具断言恰好fml-ffi/fml-imgproc/fml-recognize-local三名（缺一或多一即失败）；`// SAFETY:` 缺失、内容为空、仅标点、去空白后不足8字符或不含字母报UNSAFE-2（1），起始行前3行内合规注释不报；头删除函数、改struct字段顺序或类型文本、删除宏而未升ABI_MAJOR均报ABI-1（1），新增函数未升MINOR报ABI-1（1），`NMAJ==BMAJ` 且MINOR下降报ABI-1（1），`NMAJ>BMAJ` 时MINOR下降不报（允许重置）；ERR-1按 `python tools/ci/gen_errors.py --check` 的退出码转发（1→ERR-1、2→GATE-1报2），生成物与registry一致退出0；ERR-2按首段领域前缀判未注册字面量（同前缀且不在registry报），`FML_THEME_MISSING` 与 `FML_*` 宏不报，`/tests/`、`contracts/`、`SADD/`、`*.g.dart`、`codes.rs` 不扫；同code重复或同message_key多码ERR-3，owner与ownership.yaml不一致按ERR-1（不报ERR-3）；未知C语法、registry或生成物不可解析退出2；registry未创建时ERR-4输出“实现注册表未启用”并退出2。
- [R23] ABI主版本提升并有ADR时不报ABI-1；`--base-ref` 指向 `sadd-v*`/`archive/*` 文档标签、不可解析ref、或非HEAD祖先的ref均退出2；无 `abi-v*` 基准且未标首发退出2，`--first-release` 输出 `ABI baseline: first-release` 且只做自包含fixture，存在可达 `abi-v*` 时再给 `--first-release` 退出2（停用时机）；浅clone（is-shallow-repository=true）且未给 `--base-ref` 退出2；本卡自测命令 `python -m unittest discover -s tools/ci/tests -p "test_gate74_*.py"` 在CORE-41聚合前记为未接入、未执行。
