### CORE-67 Dart DTO 生成与漂移门禁

**目标**：统一 FFI schema、JSON向量与生成的 Dart DTO，禁止多卡手写序列化口径漂移。

**范围**
- 包含：消费CORE-100编译类型图、Dart不可变类型/严格codec/密封变体生成、gen_dto CLI与漂移门禁。
- 不包含：schema manifest/受限引用/格式/敏感路径与错误集合校验内核（CORE-100）；业务 DTO 字段与 op 实现（由各领域卡定义），FFI运行时（CORE-03，下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-100

**接口契约**
`tools/ci/gen_dto.py --check`：读取 `contracts/dto/manifest.json`，固定路径输出 `app/lib/binding/dto/<domain>.g.dart`（生成代码不计规模）；0一致/1漂移或schema无效/2工具错误。每条 `{op,owner,scope:"none"或"device"或"profile",status:"ready"或"pending",mode:ready为"call"或"submit"，pending可为null,schema,error_codes:[],sensitive_paths:[]}`，op唯一；ready的schema必存在，pending的schema必须为null并含非空blocked_reason；pending不生成类型；日常 `--check` 对每条 pending 输出 `SKIP pending <op>: <blocked_reason>` 并写入报告，不计失败、也不记为通过（与 CORE-41 的 pending 规则一致，main 保持可构建）；发布门禁 `--check --release` 遇 pending 返回1；ready、$ref闭合且不得越出contracts；`schema`为相对目录文件名，`owner`为现行卡号。文件必须提供 `$defs.request`（body）、`$defs.ok`（ok负载）、examples（request/response各≥1），共有信封引用CORE-03规则，错误引用CORE-02。

所有 op 由所属实现卡在首次实现时追加 manifest/schema/vector，Rust处理签名与Dart生成类型共同消费；不允许空object/允许任意字段代替未定义类型。检查输入/输出样例、缺字段、未知变体、敏感字段记录策略。S0以自包含fixture验收生成器；设计修订已提交contracts/dto/的S0～S2 schema数据（清单status=ready代表字段设计闭合，绝不代表业务实现/生成器验收通过）。S3～S6仍pending并逐条给owner/blocked_reason，不能进入这些op的编码。日常不因后来阶段pending阻塞S0：gen_dto.py --check --required-stage S2只要求该阶段及以前op为ready；--release要求全部ready。pending的mode允许null表示尚待核对，不能猜成submit，status未变ready前不得注册运行时op。

生成完整冻结子集由CORE-100定义并验证，不能删减；本卡消费其类型图生成object/optional/enum/互斥oneOf密封变体、tuple/有类型map与递归$ref；schema title决定PascalCase类型名，wire snake_case转lowerCamelCase并保留JsonKey，冲突失败。FixtureEchoRequest/FixtureEchoOk各含String text及fromJson/toJson，示例数据不代表已运行产物。

本卡先消费CORE-100的递归类型图再生成，不无限展开；request/ok包装title不得丢失。i64边界与宽整数必须无损输出，禁止经IEEE754中转再写回；语义约束由各所有者处理器额外校验，schema maxLength不当UTF8字节上限。共享types.schema.json各领域字段所有权仍不变。

逐op业务与diagnostics错误集合、ENGINE_UNAVAILABLE快照叠加规则及sensitive_paths唯一校验归CORE-100；本卡不按severity过滤批量复制错误集合。CLI报告展示其校验结果，生成代码不另造schema规则。

**实现约束**
- 生成器只负责格式，不推测领域默认值；oneOf为密封变体，enum固定字符串，int64映射Dart int、decimal/uint64/int128/positive-int128映射String、base64映射Uint8List；类型名冲突失败。
- 共享 DTO 放生成目录；ui可import纯数据生成文件，不得持CoreBinding。schema变更走README8.4契约变更流程。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-67_TEST.md](../Test/S0/S0_CORE-67_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约495行；主包 `tools/ci/dto_emit.py`455行（不可变类型180、codec140、递归/密封变体135），`tools/ci/gen_dto.py`及本卡CI接入40行；依赖CORE-100校验类型图。单阶段独立构建/测试Dart生成、同fixture读写与漂移CLI；contracts/dto数据、生成*.g.dart与自测不计。原960行另465归CORE-100。

