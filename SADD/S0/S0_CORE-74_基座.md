### CORE-74 unsafe、ABI与错误注册表门禁

**目标**：检查unsafe边界、公开头文件兼容和生成错误码漂移。

**范围**
- 包含：从CORE-41拆出的UNSAFE-1/2、ABI-1、ERR-1～4及测试。
- 不包含：词法共用层（CORE-69）、CI编排。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-69

**接口契约**
沿用CORE-69 Finding与0/1/2退出码。check_unsafe.py --root .：unsafe仅允许fml-ffi/fml-imgproc/fml-recognize-local，每块前3行内有// SAFETY:，注释内容为空不通过。check_abi.py --header contracts/include/fmlcore.h --base-ref <发布标签>：解析CORE-03固定C子集的函数名/参数/返回/struct字段及宏；删除或改签名/布局而未升ABI_MAJOR报ABI-1，新增函数须升MINOR；无历史标签显式baseline、不伪造比较通过，未知C语法返回2。check_errors.py --registry contracts/errors/registry.yaml：只扫描CORE-02前缀表对应大写字面量，FML_程序标签不纳入；生成物与registry完全一致为ERR-1，未注册字面量ERR-2，重复定义/所有者不一致ERR-3。ERR-4只在registry不存在阶段核对SADD唯一定义并输出“实现注册表未启用”，不能记产品门禁通过；消费卡错误表仅三列引用/所有者/本卡处理，定义表按CORE-02四列（服务端加HTTP）。

**实现约束**
- 不维护第二前缀表，ABI解析只支持公共头所用语法；版本主变更仍需BREAKING CHANGE及ADR。
- 逐文件估算：unsafe50、ABI110、errors90、正反例150，合计400；词法层复用CORE-69。
- 外部前提：锁定Python/PyYAML，基准Git标签；尚无标签时只有自包含基准fixture通过，不声称历史ABI兼容。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-74_TEST.md](../Test/S0/S0_CORE-74_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 400 行；主包 `tools/ci/`（含150行测试）。

