### CORE-100 DTO schema 编译、类型图与严格校验

**目标**：把受限JSON Schema 2020-12与manifest编译为可信类型图，统一schema/敏感路径/格式/错误索引的严格校验，供CORE-67消费。

**范围**
- 包含：manifest就绪/阶段/pending与op校验；受限路径$ref/递归图/全局title；冻结子集与互斥oneOf；精确format/数值边界；敏感Pointer/错误集合一致性。
- 不包含：gen_dto.py CLI、Dart类型/codec生成及漂移文件比较（CORE-67）；领域DTO定义/运行时处理；既有tools/DTOcheck文档工具。

**依赖**：CORE-01、CORE-02

**接口契约**

```python
# tools/ci/dto_schema.py；下层库，不调用CORE-67生成器。以下均为 frozen dataclass 的只读字段契约。
# Path/Decimal/dataclass/Literal来自Python标准库；数值在解码时保持int/Decimal，不先经float。
class SchemaRef:
    id: str  # contracts相对POSIX文件名 + "#" + 规范JSON Pointer；同一位置只建一个节点
class SchemaScalar:
    kind: Literal["string", "integer", "number", "boolean", "null"]
    value: str | int | Decimal | bool | None  # 与kind严格匹配；非任意JSON载荷
class SchemaLimits:
    minimum: int | Decimal | None; maximum: int | Decimal | None
    min_length: int | None; max_length: int | None; pattern: str | None
    min_items: int | None; max_items: int | None
    format: Literal["uuid", "date-time", "int64", "uint64", "int128", "positive-int128", "decimal", "base64"] | None
class SchemaField:
    wire_name: str; dart_name: str; value: SchemaRef; required: bool
class SchemaCase:
    branch: SchemaRef
    match: Literal["field_const", "external_key", "scalar_enum"]
    key: str | None; values: tuple[SchemaScalar, ...]
class SchemaNode:
    ref: SchemaRef; title: str | None; nullable: bool
    kind: Literal["object", "map", "array", "tuple", "union", "ref", "string", "integer", "number", "boolean", "null"]
    fields: tuple[SchemaField, ...]  # object；additionalProperties固定false
    item: SchemaRef | None  # array元素或map值；map只准Diagnostic.args的string值
    prefix: tuple[SchemaRef, ...]  # tuple按原位置，尾部items固定false
    cases: tuple[SchemaCase, ...]  # union；穷举且已证明互斥
    target: SchemaRef | None  # ref包装节点保留自己的title，仅此字段指向被引用节点
    enum_values: tuple[SchemaScalar, ...] | None  # None表示无enum，不以空tuple混淆
    const_value: SchemaScalar | None  # null常量用SchemaScalar(kind="null", value=None)，None表示无const
    limits: SchemaLimits
class ReadySchemaOp:
    op: str; owner: str; scope: Literal["none", "device", "profile"]
    mode: Literal["call", "submit"]; schema: str
    request: SchemaRef; ok: SchemaRef  # 指向$defs.request/$defs.ok包装节点，不丢外包装title
    error_codes: tuple[str, ...]; sensitive_paths: tuple[str, ...]
class PendingSchemaOp:
    op: str; owner: str; scope: Literal["none", "device", "profile"]
    mode: Literal["call", "submit"] | None; schema: None; blocked_reason: str
class SchemaDiagnostic:
    severity: Literal["info", "warning", "error"]; code: str
    source: str; pointer: str; op: str | None; message: str  # source为相对路径，无绝对主机路径或秘密
class SchemaBundle:
    valid: bool; ready: tuple[ReadySchemaOp, ...]; pending: tuple[PendingSchemaOp, ...]
    nodes: tuple[SchemaNode, ...]; named: tuple[SchemaRef, ...]; diagnostics: tuple[SchemaDiagnostic, ...]
    def node(self, ref: SchemaRef) -> SchemaNode: ...  # 只读按id索引，不创建未知节点
def compile_manifest(manifest_path: Path, required_stage: str | None = None, release: bool = False) -> SchemaBundle: ...
```

- 图协议：所有边只用SchemaRef，不嵌套复制SchemaNode；nodes含ready入口可达的全部节点（含匿名字段/分支），引用闭合。同一ref.id只建一次，递归FormulaNode通过target回边；named恰为title非空节点，title跨文件全局唯一。CORE-67先遍历named建声明索引，再按node(ref)生成，禁止递归展开或回读原始schema猜字段。request/ok即使仅含$ref，也各自保留包装节点title。
- 节点不变量：kind只启用对应fields/item/prefix/cases/target，其余为()/None；object字段required与其value节点的nullable独立，required=false不等于允许null；nullable=true表示允许额外的JSON null，不抹去非null的kind/载荷，单独null节点kind="null"且nullable=false。union的field_const以key字段的values匹配（如k），external_key以唯一必填key匹配（values为空），scalar_enum以原始标量values匹配（key=None）；branch保留完整载荷，编译器拒绝重叠/缺判别分支。enum/const和limits已规范化且仍逐项验证；format未指定为None。examples/default注解在本库校验，不作为任意JSON透传给生成器；wire名与dart名转换冲突在入图前拒绝。
- 稳定访问：ready/pending按op的UTF-8字节序；nodes按ref.id字节序；named按title字节序；fields按wire_name字节序；prefix保持tuple位置，cases保持schema分支顺序，enum_values保持schema声明顺序，error_codes/sensitive_paths排序去重。diagnostics按(source,pointer,op或空串,code,severity,message)排序；同输入与文件枚举顺序无关。所有集合只读，node(ref)不写文件/触发编译；不存在的ref.id抛Python内建KeyError（不是项目自定义类型）。
- invalid策略：schema/manifest解析、规则、例子、阶段或引用校验失败均返回valid=false及非空error诊断；不返回可供生成的半张图（ready/nodes/named必须为空）。可识别的pending仍原样显式列出，但不是已通过。valid=true当且仅当无error；日常允许的后期pending产生info/SKIP记录，required_stage要求范围内pending或release下任意pending产生error并valid=false。invalid时CORE-67不生成/覆盖Dart并映射退出1；valid时仅ready生成、pending展示SKIP而不计通过。清单本身无法读取、权限/其他系统I/O失败抛OSError，非输入错误的内部故障向CLI传播为工具错误退出2，不伪装schema invalid。库本身不写Dart、不设置进程退出码，也不提供第二CLI。

每条 `{op,owner,scope:"none"或"device"或"profile",status:"ready"或"pending",mode:ready为"call"或"submit"，pending可为null,schema,error_codes:[],sensitive_paths:[]}`，op唯一；ready的schema必存在，pending的schema必须为null并含非空blocked_reason；pending不生成类型；日常 `--check` 对每条 pending 输出 `SKIP pending <op>: <blocked_reason>` 并写入报告，不计失败、也不记为通过（与 CORE-41 的 pending 规则一致，main 保持可构建）；发布门禁 `--check --release` 遇 pending 返回1；ready、$ref闭合且不得越出contracts；`schema`为相对目录文件名，`owner`为现行卡号。文件必须提供 `$defs.request`（body）、`$defs.ok`（ok负载）、examples（request/response各≥1），共有信封引用CORE-03规则，错误引用CORE-02。

所有 op 由所属实现卡在首次实现时追加 manifest/schema/vector，Rust处理签名与Dart生成类型共同消费；不允许空object/允许任意字段代替未定义类型。检查输入/输出样例、缺字段、未知变体、敏感字段记录策略。S0以自包含fixture验收生成器；设计修订已提交contracts/dto/的S0～S2 schema数据（清单status=ready代表字段设计闭合，绝不代表业务实现/生成器验收通过）。S3～S6仍pending并逐条给owner/blocked_reason，不能进入这些op的编码。日常不因后来阶段pending阻塞S0：gen_dto.py --check --required-stage S2只要求该阶段及以前op为ready；--release要求全部ready。pending的mode允许null表示尚待核对，不能猜成submit，status未变ready前不得注册运行时op。

生成子集冻结：type(object/string/integer/number/boolean/array/null)、properties/required/additionalProperties=false、items/prefixItems、min/max、minLength/maxLength/pattern、enum/const、$defs/$ref及互斥oneOf（AST用唯一k.const；serde枚举允许唯一字符串const/enum或恰一个唯一必填键的对象，生成密封变体；重叠分支拒绝）；注解关键字 title、description、examples、default（须符合本字段schema）只校验格式、不影响类型，writeOnly 与 x-sensitive 只允许布尔 true 并汇总到 manifest 的 sensitive_paths 校验；拒绝以上之外的未实现关键字，不静默忽略。schema title为唯一PascalCase类型名，wire字段snake_case→Dart lowerCamelCase保留JsonKey，冲突失败；format只支持uuid、date-time、int64、uint64、int128、positive-int128、decimal、base64且校验实现须有正反例，其他format失败。最小manifest例{"op":"fixture.echo","owner":"CORE-67","status":"ready","mode":"call","schema":"fixture-echo.schema.json","error_codes":[],"sensitive_paths":[]}；schema request/ok均为必填text:string且additionalProperties=false，生成FixtureEchoRequest/FixtureEchoOk各含String text及fromJson/toJson。实现本体仍为后续S0卡工作，规范示例不是已运行产物。

共享types.schema.json为各所有者在01中字段表的机器镜像，title在跨文件全局唯一；递归FormulaNode允许通过$ref回到自身，生成器先建立类型图再生成，不无限展开。数组tuple支持prefixItems+items=false+minItems/maxItems；仅Diagnostic.args允许additionalProperties为string schema的有类型map，不允许任意JSON。request/ok外层$ref包装不可丢掉title。特殊format检查范围：uint64≤2^64−1，int128为−2^127～2^127−1，positive-int128为1～2^127−1，拒绝前导零/-0；非有限number拒绝。语义约束（约分、Node数量/深度、引用闭合、维度排序、UTF8字节长度）由所有者处理器额外校验，schema的maxLength不能当字节上限。敏感路径用JSON Pointer从信封根开始（/body、/ok），schema的x-sensitive和manifest对应；二者不一致失败。

error_codes为该op可返回的业务错误及成功diagnostics代码并集，不含CORE-03统一信封/句柄/取消错误；处理器必须逐op声明自身与透传集合，不能从owner错误表过滤severity后批量复制。读取引擎快照的适配另叠加CORE-56 ENGINE_UNAVAILABLE，engine.generation/wait_generation不因available=false报该码。完整逐op集合以manifest机器镜像核对；同一源码的AST NumberLiteral原文语法与计算decimal format分开，i64边界必须无损输出，禁止经IEEE754中转再写回。

**实现约束**
- 复用成熟schema validator不免除本卡的冻结子集/判别互斥/格式/有类型map/图与Pointer校验；不支持关键字必须拒绝，禁止静默忽略或任意JSON兜底。
- 校验不推测领域默认值；返回的图和诊断顺序稳定，schema数据所有者仍归各领域卡，类型图不是公共字段的新所有者。
- required-stage只要求所选阶段及以前ready，后期pending显式报告而非pass；release任何pending失败；规则由本库判定，CLI由CORE-67展示。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-100_TEST.md](../Test/S0/S0_CORE-100_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约465行；主包 `tools/ci/dto_schema.py`：manifest55、受限引用/递归图与typed bundle记录90、schema子集/oneOf150、format100、敏感与错误集合70；schema/向量/fixture数据、生成物与自测不计。单阶段独立构建测试编译图与全部正反校验，先于CORE-67交付。
