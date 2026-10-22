### CORE-100 DTO schema 编译、类型图与严格校验

**目标**：把受限 JSON Schema 2020-12 与 manifest 编译为可信类型图，统一 schema、敏感路径、format、错误索引、阶段与引擎快照集合的严格校验，供 CORE-67 消费。

**范围**
- 包含：manifest 条目形状与 `stage`/`reads_engine_snapshot` 字段校验；就绪/pending/op 与阶段门禁；受限路径 $ref、递归图与全局 title；冻结子集与互斥 oneOf；精确 format 与数值边界；敏感 Pointer 与错误集合结构一致性。
- 不包含：`gen_dto.py` 的两个入口（`--check`/`--write`）、Dart 类型/codec 生成及漂移比较（CORE-67）；领域 DTO 定义与运行时处理；既有 `tools/DTOcheck` 文档工具（它是本契约的只读检查器，其实现不并入本卡，本卡也不调用它）。

**依赖**：CORE-01、CORE-02

**接口契约**

```python
# tools/ci/dto_schema.py；下层库，不调用 CORE-67 生成器、不读 SADD/卡文件。以下均为 frozen dataclass 的只读字段契约。
# Path/Decimal/dataclass/Literal 来自 Python 标准库；数值在解码时保持 int/Decimal，不先经 float。
Stage = Literal["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"]  # manifest 唯一阶段字段的取值域
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
    op: str; owner: str; stage: Stage; scope: Literal["none", "device", "profile"]
    mode: Literal["call", "submit"]; schema: str
    request: SchemaRef; ok: SchemaRef  # 指向$defs.request/$defs.ok包装节点，不丢外包装title
    error_codes: tuple[str, ...]; sensitive_paths: tuple[str, ...]
    reads_engine_snapshot: bool  # 见“引擎快照集合”
class PendingSchemaOp:
    op: str; owner: str; stage: Stage; scope: Literal["none", "device", "profile"]
    mode: Literal["call", "submit"] | None; schema: None; blocked_reason: str
class SchemaDiagnostic:
    severity: Literal["info", "warning", "error"]; code: str
    source: str; pointer: str; op: str | None; message: str  # source为相对路径，无绝对主机路径或秘密
class SchemaToolError(Exception):
    """本库自身无法继续的内部故障（不是输入违反规则）。消费方必须映射为工具错误，不得转成valid=false。"""
class SchemaBundle:
    valid: bool; ready: tuple[ReadySchemaOp, ...]; pending: tuple[PendingSchemaOp, ...]
    nodes: tuple[SchemaNode, ...]; named: tuple[SchemaRef, ...]; diagnostics: tuple[SchemaDiagnostic, ...]
    def node(self, ref: SchemaRef) -> SchemaNode: ...  # 只读按id索引，不创建未知节点
def compile_manifest(manifest_path: Path, required_stage: Stage | None = None, release: bool = False) -> SchemaBundle: ...
```

- manifest 条目（本卡是唯一定义处）：`{op,owner,stage,status,mode,scope,schema,error_codes,sensitive_paths}`，ready 追加 `reads_engine_snapshot`，pending 追加 `blocked_reason`；键集冻结，未知键判 error。`op` 唯一且为 `<域>.<动作>`（小写字母数字下划线）；`owner` 为现行卡号；`stage` 取 `Stage`；ready 的 `status` 只表示字段设计闭合，不代表业务实现或生成器验收通过。ready：mode 为 call|submit、schema 为 contracts/dto 下相对文件名且文件存在并含 $defs.request/$defs.ok/examples、reads_engine_snapshot 为布尔；pending：mode 为 null|call|submit、schema 必须为 null、blocked_reason 非空、不得出现 reads_engine_snapshot。
- 阶段判定：阶段只来自 manifest 的 `stage` 字段，本库不读卡文件、不从文件名或 SADD 推断。rank 按 S0→S7 顺序。`op.stage` 的 rank ≤ required_stage 且 status=pending → error；rank > required_stage 的 pending → info（显式 SKIP，不计通过）；`release=True` 时任意 pending → error；required_stage=None 且 release=False 只要求条目自身自洽、不把后期 pending 算失败。ready 条目即使阶段晚于 required_stage 也不因此失败。
- 引擎快照集合：`reads_engine_snapshot` 是该 op 是否读取 CORE-56 引擎快照的唯一机器字段。规则：ready 条目中它必须为布尔，且与“error_codes 是否含 ENGINE_UNAVAILABLE”双向一致，不一致即 error。集合的语义来源是各 op 所有者卡的错误表与 CORE-56 的五 op 清单；本库只校验这两个机器事实一致，不解析 CORE-56 卡、不另存全局清单。`engine.generation`/`engine.wait_generation` 查快照状态而非读快照数据，故为 false 且不得含该码。
- error_codes：为该 op 可返回的业务错误与成功 diagnostics 代码并集，不含 CORE-03 统一信封/句柄/取消码。逐 op 期望集合的唯一真源是 `contracts/errors/registry.yaml`（CORE-02 生成并维护）；registry 尚未创建，本库只校验条目自身结构（字符串、去重、字典序、不含 CORE-03 归属码），对象级比对（码是否已在卡/registry 注册、是否有第二所有者）归 DTOcheck 的 DTO-06/DTO-18。本库不把 manifest 与自身比对、不自建第二份逐 op 期望表、不读 SADD。同一源码的 AST NumberLiteral 原文语法与计算用 decimal format 分开，i64 边界必须无损输出，禁止经 IEEE754 中转再写回。
- 图协议：所有边只用 SchemaRef，不嵌套复制 SchemaNode；nodes 含 ready 入口可达的全部节点（含匿名字段/分支），引用闭合。同一 ref.id 只建一次，递归 FormulaNode 通过 target 回边；named 恰为 title 非空节点，title 跨文件全局唯一。CORE-67 先遍历 named 建声明索引，再按 node(ref) 生成，禁止递归展开或回读原始 schema 猜字段。request/ok 即使仅含 $ref，也各自保留包装节点 title。
- 节点不变量：kind 只启用对应 fields/item/prefix/cases/target，其余为 ()/None；object 字段 required 与其 value 节点的 nullable 独立，required=false 不等于允许 null；nullable=true 表示允许额外的 JSON null，不抹去非 null 的 kind/载荷，单独 null 节点 kind="null" 且 nullable=false。union 的 field_const 以 key 字段的 values 匹配（如 k），external_key 以唯一必填 key 匹配（values 为空），scalar_enum 以原始标量 values 匹配（key=None）；branch 保留完整载荷，编译器拒绝重叠/缺判别分支。enum/const 和 limits 已规范化且仍逐项验证；format 未指定为 None。examples/default 注解在本库校验，不作为任意 JSON 透传给生成器；wire 名与 dart 名转换冲突在入图前拒绝。
- 稳定访问：ready/pending 按 op 的 UTF-8 字节序；nodes 按 ref.id 字节序；named 按 title 字节序；fields 按 wire_name 字节序；prefix 保持 tuple 位置，cases 保持 schema 分支顺序，enum_values 保持 schema 声明顺序，error_codes/sensitive_paths 排序去重。diagnostics 按 (source,pointer,op 或空串,code,severity,message) 排序；同输入与文件枚举顺序无关。所有集合只读，node(ref) 不写文件/不触发编译；不存在的 ref.id 抛 Python 内建 KeyError（不是项目自定义类型）。
- invalid 策略：schema/manifest 解析、规则、例子、阶段或引用校验失败均返回 valid=false 及非空 error 诊断；不返回可供生成的半张图（ready/nodes/named 必须为空）。可识别的 pending 仍原样显式列出，但不是已通过。valid=true 当且仅当无 error；日常允许的后期 pending 产生 info/SKIP 记录，required_stage 范围内 pending 或 release 下任意 pending 产生 error 并 valid=false。invalid 时消费方（CORE-67）不得生成或覆盖 Dart 产物；库本身不写 Dart、不设置进程退出码、不提供 CLI，也不决定报告文件位置。
- 内部故障边界：清单无法读取或权限等系统 I/O 失败抛 OSError（原样上抛）；本库自身缺陷、依赖不可用等内部故障抛 SchemaToolError，两者都由消费方映射为工具错误，不写成 valid=false 诊断、不伪装 schema invalid。

生成子集冻结：type(object/string/integer/number/boolean/array/null)、properties/required/additionalProperties=false、items/prefixItems、min/max、minLength/maxLength/pattern、enum/const、$defs/$ref 及互斥 oneOf（AST 用唯一 k.const；serde 枚举允许唯一字符串 const/enum 或恰一个唯一必填键的对象，生成密封变体；重叠分支拒绝）；注解关键字 title、description、examples、default（须符合本字段 schema）只校验格式、不影响类型，writeOnly 与 x-sensitive 只允许布尔 true 并汇总到 manifest 的 sensitive_paths 校验；拒绝以上之外的未实现关键字，不静默忽略。schema title 为唯一 PascalCase 类型名，wire 字段 snake_case→Dart lowerCamelCase 保留 JsonKey，冲突失败；format 只支持 uuid、date-time、int64、uint64、int128、positive-int128、decimal、base64 且校验实现须有正反例，其他 format 失败。S0 自包含 fixture（如 fixture.echo）放在 `tools/ci/tests/fixtures/`，其最小 manifest 条目为 `{"op":"fixture.echo","owner":"CORE-67","stage":"S0","status":"ready","mode":"call","scope":"none","schema":"fixture-echo.schema.json","error_codes":[],"sensitive_paths":[],"reads_engine_snapshot":false}`，request/ok 均为必填 text:string 且 additionalProperties=false，供生成器验收 FixtureEchoRequest/FixtureEchoOk 各含 String text 及 fromJson/toJson；该 fixture 不得写入 `contracts/dto/manifest.json`。实现本体仍为后续 S0 卡工作，规范示例不是已运行产物。

共享 types.schema.json 为各所有者在 01 中字段表的机器镜像，title 在跨文件全局唯一；递归 FormulaNode 允许通过 $ref 回到自身，生成器先建立类型图再生成，不无限展开。数组 tuple 支持 prefixItems+items=false+minItems/maxItems；仅 Diagnostic.args 允许 additionalProperties 为 string schema 的有类型 map，不允许任意 JSON。request/ok 外层 $ref 包装不可丢掉 title。特殊 format 检查范围：uint64≤2^64−1，int128 为 −2^127～2^127−1，positive-int128 为 1～2^127−1，拒绝前导零/-0；非有限 number 拒绝。语义约束（约分、Node 数量/深度、引用闭合、维度排序、UTF8 字节长度）由所有者处理器额外校验，schema 的 maxLength 不能当字节上限。敏感路径用 JSON Pointer 从信封根开始（/body、/ok），schema 的 x-sensitive 和 manifest 对应；二者不一致失败。

**实现约束**
- 复用成熟 schema validator 不免除本卡的冻结子集/判别互斥/格式/有类型 map/图与 Pointer 校验；不支持关键字必须拒绝，禁止静默忽略或任意 JSON 兜底。
- 校验不推测领域默认值；返回的图和诊断顺序稳定，schema 数据所有者仍归各领域卡，类型图不是公共字段的新所有者。
- 数据边界（不新增依赖）：CORE-03（信封）、CORE-56（引擎快照）、CORE-41（CI 聚合）、CORE-67（生成器）在正文里只是数据边界与消费者；本卡不 import、不读取它们的产物，也不读 SADD。CORE-03 依赖 CORE-67、CORE-67 依赖本卡，反向依赖会成环（CORE-01 依赖方向与 CARD-10）。
- 本库不生成 Dart、不写生成目录、不设置进程退出码、不提供第二个 CLI；CLI 入口、报告路径与 0/1/2 退出码归 CORE-67。阶段与 pending 的判定在本库，CLI 只传参与展示。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-100_TEST.md](../Test/S0/S0_CORE-100_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约495行；主包 `tools/ci/dto_schema.py`：manifest 条目/阶段/快照 65、受限引用/递归图与 typed bundle 记录 90、schema 子集与 oneOf 150、format 100、敏感路径与错误集合结构 90；schema/向量/fixture 数据、生成物与自测不计。单阶段独立构建测试编译图与全部正反校验，先于 CORE-67 交付。
