# CORE-67 测试方案

> 来源卡：[S0_CORE-67_基座.md](../../S0/S0_CORE-67_基座.md)（DTO schema 编译与漂移检查）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R19] fixtures覆盖对象、可选、enum、oneOf、数组、公共$ref；Rust/Dart读同一fixture字段一致；两次生成字节相同；删字段/破坏$ref/手改生成文件均使--check失败。
- [R19] x-sensitive路径出现于日志模板的反例失败；有效业务op缺schema或例子时门禁失败，pending显式报告。

- [R18][R19] --required-stage S2核对S0～S2每个op的owner/mode/scope/字段/$ref与examples均ready，删除任一schema/例子或制造外部$ref失败；后期pending清单独立输出且不伪造通过。递归AST、外部标记枚举、typed AST有非空成功及未知变体/整数越界反例。

- [R19] manifest反例：derive/units漏业务码、engine.export漏PARSE_UNICODE_NOT_EXPORTABLE、calc.evaluate漏EVAL_DOMAIN、store.open漏STORE_BUSY、create_registered漏AUTH_PROFILE_EXISTS均使镜像核对失败；错误码未注册或重复归属失败；core.log_init不得混入网络守卫错误。
