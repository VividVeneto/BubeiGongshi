### CORE-67 DTO schema 编译与漂移检查

**目标**：统一 FFI schema、JSON向量与生成的 Dart DTO，禁止多卡手写序列化口径漂移。

**范围**
- 包含：schema manifest、JSON Schema 2020-12 校验、Dart不可变类型生成与漂移门禁。
- 不包含：业务 DTO 字段与 op 实现（由各领域卡定义），FFI运行时（CORE-03，下游说明，非契约）。

**依赖**：CORE-01、CORE-02

**接口契约**
`tools/ci/gen_dto.py --check`：读取 `contracts/dto/manifest.json`，固定路径输出 `app/lib/binding/dto/<domain>.g.dart`（生成代码不计规模）；0一致/1漂移或schema无效/2工具错误。每条 `{op,owner,scope:"none"或"device"或"profile",status:"ready"或"pending",mode:ready为"call"或"submit"，pending可为null,schema,error_codes:[],sensitive_paths:[]}`，op唯一；ready的schema必存在，pending的schema必须为null并含非空blocked_reason；pending不生成类型；日常 `--check` 对每条 pending 输出 `SKIP pending <op>: <blocked_reason>` 并写入报告，不计失败、也不记为通过（与 CORE-41 的 pending 规则一致，main 保持可构建）；发布门禁 `--check --release` 遇 pending 返回1；ready、$ref闭合且不得越出contracts；`schema`为相对目录文件名，`owner`为现行卡号。文件必须提供 `$defs.request`（body）、`$defs.ok`（ok负载）、examples（request/response各≥1），共有信封引用CORE-03规则，错误引用CORE-02。

所有 op 由所属实现卡在首次实现时追加 manifest/schema/vector，Rust处理签名与Dart生成类型共同消费；不允许空object/允许任意字段代替未定义类型。检查输入/输出样例、缺字段、未知变体、敏感字段记录策略。S0以自包含fixture验收生成器；设计修订已提交contracts/dto/的S0～S2 schema数据（清单status=ready代表字段设计闭合，绝不代表业务实现/生成器验收通过）。S3～S6仍pending并逐条给owner/blocked_reason，不能进入这些op的编码。日常不因后来阶段pending阻塞S0：gen_dto.py --check --required-stage S2只要求该阶段及以前op为ready；--release要求全部ready。pending的mode允许null表示尚待核对，不能猜成submit，status未变ready前不得注册运行时op。

生成子集冻结：type(object/string/integer/number/boolean/array/null)、properties/required/additionalProperties=false、items/prefixItems、min/max、minLength/maxLength/pattern、enum/const、$defs/$ref及互斥oneOf（AST用唯一k.const；serde枚举允许唯一字符串const/enum或恰一个唯一必填键的对象，生成密封变体；重叠分支拒绝）；注解关键字 title、description、examples、default（须符合本字段schema）只校验格式、不影响类型，writeOnly 与 x-sensitive 只允许布尔 true 并汇总到 manifest 的 sensitive_paths 校验；拒绝以上之外的未实现关键字，不静默忽略。schema title为唯一PascalCase类型名，wire字段snake_case→Dart lowerCamelCase保留JsonKey，冲突失败；format只支持uuid、date-time、int64、uint64、int128、positive-int128、decimal、base64且校验实现须有正反例，其他format失败。最小manifest例{"op":"fixture.echo","owner":"CORE-67","status":"ready","mode":"call","schema":"fixture-echo.schema.json","error_codes":[],"sensitive_paths":[]}；schema request/ok均为必填text:string且additionalProperties=false，生成FixtureEchoRequest/FixtureEchoOk各含String text及fromJson/toJson。实现本体仍为后续S0卡工作，规范示例不是已运行产物。

共享types.schema.json为各所有者在01中字段表的机器镜像，title在跨文件全局唯一；递归FormulaNode允许通过$ref回到自身，生成器先建立类型图再生成，不无限展开。数组tuple支持prefixItems+items=false+minItems/maxItems；仅Diagnostic.args允许additionalProperties为string schema的有类型map，不允许任意JSON。request/ok外层$ref包装不可丢掉title。特殊format检查范围：uint64≤2^64−1，int128为−2^127～2^127−1，positive-int128为1～2^127−1，拒绝前导零/-0；非有限number拒绝。语义约束（约分、Node数量/深度、引用闭合、维度排序、UTF8字节长度）由所有者处理器额外校验，schema的maxLength不能当字节上限。敏感路径用JSON Pointer从信封根开始（/body、/ok），schema的x-sensitive和manifest对应；二者不一致失败。

error_codes为该op可返回的业务错误及成功diagnostics代码并集，不含CORE-03统一信封/句柄/取消错误；处理器必须逐op声明自身与透传集合，不能从owner错误表过滤severity后批量复制。读取引擎快照的适配另叠加CORE-56 ENGINE_UNAVAILABLE，engine.generation/wait_generation不因available=false报该码。完整逐op集合以manifest机器镜像核对；同一源码的AST NumberLiteral原文语法与计算decimal format分开，i64边界必须无损输出，禁止经IEEE754中转再写回。

**实现约束**
- 生成器只负责格式，不推测领域默认值；oneOf为密封变体，enum固定字符串，int64映射Dart int、decimal/uint64/int128/positive-int128映射String、base64映射Uint8List；类型名冲突失败。
- 共享 DTO 放生成目录；ui可import纯数据生成文件，不得持CoreBinding。schema变更走README8.4契约变更流程。

**验收标准**
- [R18][R19] fixtures覆盖对象、可选、enum、oneOf、数组、公共$ref；Rust/Dart读同一fixture字段一致；两次生成字节相同；删字段/破坏$ref/手改生成文件均使--check失败。
- [R19] x-sensitive路径出现于日志模板的反例失败；有效业务op缺schema或例子时门禁失败，pending显式报告。

- [R18][R19] --required-stage S2核对S0～S2每个op的owner/mode/scope/字段/$ref与examples均ready，删除任一schema/例子或制造外部$ref失败；后期pending清单独立输出且不伪造通过。递归AST、外部标记枚举、typed AST有非空成功及未知变体/整数越界反例。

- [R19] manifest反例：derive/units漏业务码、engine.export漏PARSE_UNICODE_NOT_EXPORTABLE、calc.evaluate漏EVAL_DOMAIN、store.open漏STORE_BUSY、create_registered漏AUTH_PROFILE_EXISTS均使镜像核对失败；错误码未注册或重复归属失败；core.log_init不得混入网络守卫错误。

**规模**：约 480 行；主包 `tools/ci/gen_dto.py`（图解析/校验140、类型生成130、序列化90、测试120），附属 `contracts/dto/` schema与向量（数据不计代码）。递归/枚举超此估算时先拆卡，不能删校验子集。

