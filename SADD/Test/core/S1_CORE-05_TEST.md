# CORE-05 测试方案

> 来源卡：[S1_CORE-05_引擎.md](../../core/S1_CORE-05_引擎.md)（公式 AST 与修订模型）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**

以下为编码阶段自动化验收计划，不是当前已通过的产品测试。fixture/schema/向量必须与实现同阶段交付，预期值不得由被测函数生成。

## 阶段①：模型、遍历、上限与取消
- [R11] 编译期trait断言：FormulaRevision/FormulaItem/SymbolEnv/TypeDecl/Validation/Provenance/Derivation及AST所有子类型满足源卡能力表；ID可Copy/Eq/Hash/Ord，CancelFlag仅Clone/Debug；不得为AtomicBool伪造值相等或serde。修订更新fixture使用调用方给定的新旧UUID和时间，验证parents指旧修订、head移动而旧内容逐字段不变；测试不调用OS时钟/随机源。
- [R19] walk固定前序与node_at：对所有变体构造带唯一叶标记的树，逐一断言路径/顺序/回取值；根为NodePath([])，根仅回调一次；Integral仅upper存在时仍在槽2，SumOrLimit无上下界时body仍在槽2；Matrix 2×2路径0..3，Piecewise值/条件槽2i/2i+1，缺省条件路径不存在；非法/越界路径返回None。随机合法AST全部路径唯一、每个节点均可取回。
- [R19] 节点边界使用Vector根+4095/4096个叶，分别4096通过/4097返回Nodes(4097)；深度用63/64层Unary边加叶，分别根深度64通过/65返回Depth(65)；不以边数代替深度。64×16矩阵通过，65×1返回MatrixDim(65,1)，33×32返回MatrixElems(1056)；多违例遵守源卡优先次序，超深恶意输入不得栈溢出或panic。
- [R19] check_source_len(65536)通过、65537返回SourceBytes(65537)；以21845个汉字+1个ASCII（65536字节）通过，再加ASCII失败，证明不是Unicode字符数。check_limits本身不产生SourceBytes；解析/构造边界先检查source字节数，再检查树；错误映射均PARSE_LIMIT_EXCEEDED。
- [R19] CancelFlag::new为false，克隆后任一实例cancel使全部is_cancelled为true，重复cancel幂等；用线程共享flag验证取消可见性，不靠sleep/实时时钟作为正确性判据。

## 阶段②：严格codec、schema、哈希与ID
- [R10] proptest只生成满足结构/NFC/限额的AST：canonical_json→from_canonical_json→再序列化逐字节一致且AST相等；canonical_hash等于独立BLAKE3对固定规范字节的结果。AST-01～15逐字节固定，不从产品实现回填fixture；变体/字段/sig_digits缺省与显式值分别覆盖。
- [R10] 编码转义固定期望：U+0001→反斜杠u0001、换行→反斜杠n，引号/反斜杠/所有控制字符按源卡；组合字形先NFC，非ASCII直接UTF-8，斜杠不转义。Number.text的`+.5`、`100.`、`1.00e+0`原样保存，NaN/Inf和畸形指数拒绝；不把Number解析成f64或补sig_digits。
- [R19] JSON Schema 2020-12（显式启用formats）与本卡语义双重检查：AST-01～15通过；正确对象分支`{"k":"piecewise","branches":[{"value":{"k":"number","text":"1"}}]}`通过；错误tuple分支`{"k":"piecewise","branches":[[{"k":"number","text":"1"}]]}`必须拒绝，不能只断言某个未列出的“tuple”fixture失败。Integral.multiple的1/3通过，0/4拒绝；空矩阵、空行、参差行、非末支省略condition拒绝；前两项schema可检查，其余跨字段由codec检查。
- [R19] 拒绝未知k/op/kind/字段、缺必填、显式null、重复对象key、u8=256/u16=65536/u32=4294967296、负ID、尾随JSON、非法UTF-8入口；均AST_JSON_INVALID。合法树但超节点/深度/矩阵尺寸为PARSE_LIMIT_EXCEEDED；只含AST JSON的输入不把JSON字符串长度当source_latex字节数。
- [R11] 存储serde固定shape：FormulaNode用k对象而非默认enum外部标签；ID与UnitRef/FunctionId透明；SymbolEnv按id顺序；Validation的verified和verified_polymorphic、Provenance各有/无载荷、MathKind的scalar/vector(null)/matrix([null,2])/function(2)、Derivation.var_map恰两项数组全覆盖。NodePath根序列化`""`，路径`"0.2.1"`；拒绝空段/超u16/数组形式。Page<FormulaRevision>编译期Clone/Debug/Eq/serde断言，空items、total=0、page=0、page_size=50往返；page_size=0/201由调用方参数边界拒绝，不让纯Page擅自发业务错误。
- [R11] 在完整合法FormulaRevision和ConfirmRecord fixture中分别替换时间token为-9223372036854775808及9223372036854775807，通过；-9223372036854775809及9223372036854775808拒绝。Rust serde直接整数token与schema验证必须有精确整数断言；禁止用JS JSON.parse/Number或f64展示近似值再声称上下界通过。source_latex含分解Unicode与空白仍逐字节保持。
- [R10] contracts/vectors/ids-v1.json原样交付源卡全部固定值：三namespace、pack_item_id、pack_template_id、card_id空模板、pack_cache_revision_id、merge_choice_id去重排序、question_seed（含完整SHA-256/小端u64）。R1/R2/P/C按源卡；确认seed=14916561557260356800不能经JS Number舍入。另断言更换字段改变ID、头顺序/重复不改变merge ID、NFC等价输入同ID、question_index按BE32且首8摘要按LE64解释。
- [R19] ID边界拒绝计划：NUL/空pack字段、非法card_type、非64小写hex在FFI适配先FFI_BAD_ARG，包源字段在内容工具先CONTENT_FIELD_INVALID；mock记录helper未被调用且无panic/无catch_unwind。去重后单头集合不生成merge_choice；内部违规assert只作为编程错误独立测试，不混作用户输入拒绝证据。这些跨卡适配测试由相应消费者补齐，本卡只交付纯helper/前置条件，未实现时保持残余门禁。
- [R10] 外部前提与独立性：编码时锁uuid(v5/serde)、sha2、unicode-normalization、serde/serde_json、blake3、proptest与2020-12 validator；无锁/向量缺失标未执行。UUIDv7/时间来源和ChaCha8序列归调用方验证，fml-ast测试不得引入领域层时钟/随机依赖。
