# CORE-100 测试方案

> 来源卡：[S0_CORE-100_基座.md](../../S0/S0_CORE-100_基座.md)（DTO schema编译类型图与严格校验）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**
- [R18][R19] 对象/可选/nullable独立/enum/互斥oneOf/tuple/有类型map/公共与递归$ref建立有限闭合图，title跨文件唯一、request/ok外包装title不丢失；未知关键字/重叠或不可判别union/命名冲突/外部引用/断链引用均拒绝并给定位诊断。
- [R19] uuid/date-time/int64/uint64/int128/positive-int128/decimal/base64逐项正反例；int64与宽整数按精确范围校验（含i64最小/最大值、±2^127边界），前导零/-0/非有限number拒绝，校验过程不经float中转；敏感JSON Pointer从/body或/ok根开始，与manifest及x-sensitive/writeOnly严格一致。
- [R18][R19] 阶段门禁只以manifest的stage字段为来源：缺stage或值不在S0～S7失败；required_stage=S2时stage≤S2的pending为error、stage>S2的pending为info且SKIP不计通过；release下任意pending为error；ready条目阶段晚于required_stage不失败；在无SADD目录或卡文件不可读的环境下同一清单仍得到相同判定（证明库不读卡文件、不从文件名推断阶段）。
- [R19] 引擎快照集合双向一致：ready条目缺reads_engine_snapshot或非布尔失败；reads_engine_snapshot=true但error_codes不含ENGINE_UNAVAILABLE（及反向）失败；engine.generation/engine.wait_generation声明为false却含该码失败；pending条目出现该字段失败；以真实清单副本把calc.evaluate改成false、把engine.check改成true分别验证失败。
- [R18][R19] manifest条目键集冻结：出现未声明键、pending的mode/schema非null或缺失blocked_reason、ready缺reads_engine_snapshot、mode/scope越出枚举、op重复或不匹配<域>.<动作>、owner非现行卡号，均失败且诊断带相对source与Pointer。
- [R19] 错误集合只做结构与唯一归属检查，不做镜像自比：error_codes出现非字符串/重复/非字典序、含CORE-03归属的信封、句柄或取消码（FFI_*）时失败；删除某ready op的一个业务码后本库不报“缺码”（对象级归属由DTOcheck的DTO-06/DTO-18在卡与registry上判定，registry.yaml未创建前该比对记为未覆盖而非通过）；库不读SADD、不内置逐op期望表；改变输入清单的条目与键书写顺序后diagnostics逐项相同。
- [R19] examples/default符合字段schema，未知注解关键字被拒绝而非忽略；格式子集与有类型map不能退化任意JSON（typed map只允许Diagnostic.args的string值），schema maxLength不当UTF8字节上限，领域语义仍由各owner额外校验。
- [R18][R19] typed返回协议：最小fixture.echo读取bundle.ready唯一ReadySchemaOp，经request/ok→node(ref)取得两个各具title的object包装；字段text的wire_name/dart_name/required/value与string节点完整，不读原始JSON即可确定生成FixtureEchoRequest/FixtureEchoOk与严格codec；bundle与node集合只读，不允许Any或任意JSON兜底。
- [R18][R19] 有限递归图：FormulaNode自引用、两类型互引、匿名union/tuple子节点只经SchemaRef边连接；同文件+Pointer只建一节点，named恰为title节点；$ref外层request/ok的title仍存在；node(ref)对未知id抛Python内建KeyError且不补节点。调整文件遍历顺序后ready/pending/nodes/named/fields/diagnostics逐项相同，tuple位置与cases/enum声明顺序不变。
- [R18][R19] 节点访问覆盖object必填/可选与nullable相互独立、array、固定tuple(items=false)、Diagnostic.args的typed string map、ref包装，以及field_const/external_key/scalar_enum三种union判别；经SchemaCase的key/values/branch可穷举匹配；null常量与缺const、无enum与空enum集合不得混淆；limits与format保持精确int/Decimal。
- [R18][R19] invalid禁止部分生成：坏JSON、缺ready schema、外部或断链引用、命名冲突、重叠分支、examples/default错误、required_stage范围内pending、release任意pending，均返回valid=false、非空error诊断且ready/nodes/named全空；已识别pending仍显式列出但不算通过；有效与无效混合输入不得返回可用半图。SchemaDiagnostic给出稳定code/相对source/Pointer/op/无秘密message；清单权限等OSError原样上抛、内部故障抛SchemaToolError，两者都不写成valid=false。以CORE-67同协议替身核对invalid→1、工具错误→2、可用图→继续生成判断，不宣称CORE-67产品实现已运行。
