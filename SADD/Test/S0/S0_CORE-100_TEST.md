# CORE-100 测试方案

> 来源卡：[S0_CORE-100_基座.md](../../S0/S0_CORE-100_基座.md)（DTO schema编译类型图与严格校验）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**
- [R18][R19] 对象/可选/enum/互斥oneOf/tuple/有类型map/公共与递归$ref全部建立有限闭合图，title跨文件唯一、request/ok外包装title不丢失；未知关键字/重叠union/命名冲突/外部引用/断链拒绝。
- [R19] uuid/date-time/int64/uint64/int128/positive-int128/decimal/base64逐项正反例，整数精确范围、前导零/-0及非有限number拒绝；敏感JSON Pointer从/body或/ok根开始，与manifest和x-sensitive/writeOnly严格一致。
- [R18][R19] required-stage S2要求早期全部ready，后期pending显式SKIP不计通过，release任何pending失败；ready缺schema/例子、pending缺blocked_reason、非法mode/scope/重复op失败；图编译不写Dart文件、不调用CORE-67。
- [R19] manifest反例：derive/units漏业务码、engine.export漏PARSE_UNICODE_NOT_EXPORTABLE、calc.evaluate漏EVAL_DOMAIN、store.open漏STORE_BUSY、create_registered漏AUTH_PROFILE_EXISTS均失败；错误未注册/重复归属、core.log_init混入网络守卫码失败，依赖快照op按CORE-56叠加ENGINE_UNAVAILABLE但generation/wait_generation不叠加。
- [R19] examples/default符合字段schema；格式子集与有类型map不能退化任意JSON；schema maxLength不当UTF8字节上限，领域语义仍由各owner额外校验。
- [R18][R19] typed返回协议：最小fixture.echo读取bundle.ready唯一ReadySchemaOp，以request/ok→node(ref)取得两个各具title的object包装；字段text的wire_name/dart_name/required/value及string节点完整，不读取原始JSON即可确定生成FixtureEchoRequest/FixtureEchoOk和严格codec；bundle/node集合均只读，不允许Any或任意JSON字段兜底。
- [R18][R19] 有限递归图：FormulaNode自引用、两个类型互引、匿名union/tuple子节点都仅以SchemaRef边连接；相同文件+Pointer只建一节点，named只含title节点；$ref外层request/ok的title仍存在，node(ref)对未知id抛KeyError且不补节点。调整文件遍历顺序后，ready/pending/nodes/named/fields/diagnostics逐项相同，tuple位置与cases/enum声明顺序不变。
- [R18][R19] 节点访问覆盖object必填/可选与nullable相互独立、array、固定tuple(items=false)、Diagnostic.args的typed string map、ref包装，以及field_const/external_key/scalar_enum三种union判别；通过SchemaCase的key/values/branch可穷举匹配，重叠分支拒绝；null常量与缺const、无enum与枚举集合不得混淆；limits和format保持精确int/Decimal及原约束。
- [R18][R19] invalid禁止部分生成：坏JSON、缺ready schema、外部/断链ref、命名冲突/重叠分支、例子/default错误、stage所需pending与release任意pending均返回valid=false、非空定位error诊断，ready/nodes/named全空；已识别pending仍展示且不算通过；构造有效部分+无效部分混合输入验证不得返回可用半图。
- [R19] 成功/失败边界：valid=true时仅ready生成所需图，后期pending为info+SKIP且不生成；required_stage所需pending与release pending为error；SchemaDiagnostic给出稳定code/相对source/Pointer/op/无秘密message。清单读取权限等OSError与内部故障分别保留为工具错误，不返回伪valid bundle；CORE-100不写Dart或退出进程，以CORE-67同协议替身核对invalid→1、工具错误→2、可用图→后续生成/漂移判断，不宣称CORE-67产品实现已运行。
