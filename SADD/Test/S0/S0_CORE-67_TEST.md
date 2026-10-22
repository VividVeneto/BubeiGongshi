# CORE-67 测试方案

> 来源卡：[S0_CORE-67_基座.md](../../S0/S0_CORE-67_基座.md)（Dart DTO生成与漂移门禁）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R19] 形状覆盖fixture（object、可选与nullable独立、enum、array、tuple、Diagnostic.args的typed map、三种union判别、公共与递归$ref）：生成文件含固定头“GENERATED CODE - DO NOT MODIFY BY HAND”、来源与generator文本常量且无时间戳；连续两次--write字节相同；DTO覆写==/hashCode按值比较、集合为不可修改视图、toString对sensitive_paths命中字段输出<redacted>。
- [R19] 数值与codec边界：int64映射int，decimal/uint64/int128/positive-int128映射String并保留原始十进制文本（含i64最小/最大值与2^127边界，不经double往返），base64映射Uint8List，number非有限值拒绝；缺必填字段、类型不符、未知enum wire值、未知union判别、tuple长度或位置不符均抛FormatException；fromJson忽略未声明未知键、toJson只写声明字段。
- [R18][R19] 域推导与布局：op第一段推导<domain>并写入<out>/<domain>.g.dart，types→types.g.dart、ast→ast.g.dart；同域多op与共享类型按字节序合并进同一文件；全局唯一title只生成一次且跨文件import可编译；分支派生名与既有类型冲突时退出1并在diagnostics指出该分支。
- [R18][R19] --check与--write语义分离：--check不改动任何Dart文件（运行前后hash/mtime相同），唯一写动作是--report指定的报告；--write不写报告文件、只写<out>/<domain>.g.dart并先写临时文件后原子rename；手改生成文件后--check退出1且status=drift，删除生成文件为missing，<out>中多余生成文件为stale；<out>内同名文件无GENERATED头时--write拒绝覆盖并退出1。
- [R19] 退出码与工具错误：一致且无error为0；漂移、CORE-100返回valid=false、required_stage范围内pending、release遇pending、命名冲突均为1；--check与--write同时给出或都不给出、--report不可写、清单读取失败、CORE-100抛SchemaToolError、未预期异常均为2，且不得从2降级为1或把1报成0。
- [R18][R19] 报告格式冻结：字段集为version/mode/manifest/required_stage/release/ready/pending/skipped/files/diagnostics/exit；files按path、skipped按op、diagnostics按(file,code,op,message)字节序；同一输入两次运行报告逐字节相同，无时间戳、无绝对主机路径；pending的SKIP行来自CORE-100的info诊断，既不计失败也不记为通过。
- [R18][R19] 阶段与pending：--required-stage S2且stage≤S2全ready时退出0；把S2内一条改为pending则为1并出现在diagnostics；仅有S3～S6 pending时只进skipped且退出0；--release遇任意pending为1；pending不生成类型（生成文件中不含该op的类型）；对真实contracts/dto/manifest.json运行--check时36个ready全部生成、107个pending全部列入skipped，退出0或仅因未写盘而报漂移（1），不宣称消费方已签认或业务op已实现。
- [R18][R19] 只消费类型图、不复制schema规则：以CORE-100替身返回构造好的SchemaBundle时，生成结果只由图与manifest决定；把原始schema文件移出可读路径而类型图仍有效时生成不变（证明未二次解析schema）；生成器不读SADD、不import CORE-56/CORE-03实现。
- [R19] CI接入与边界：tools/ci/manifest.json的dto-drift步骤条目形状合法（id唯一、owner为CORE-67、argv以python tools/ci/gen_dto.py --check开头、release_args含--release），保持CORE-41已冻结的{version:1,steps:[{id,owner,argv,release_args?}]}结构且不引入反向依赖；用替身聚合器验证该步骤退出1映射为fail、退出2映射为error；fixture的manifest/schema位于tools/ci/tests/fixtures/并以--manifest显式指定，不写入contracts/dto/。
