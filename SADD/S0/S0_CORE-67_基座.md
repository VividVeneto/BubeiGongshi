### CORE-67 Dart DTO 生成与漂移门禁

**目标**：从 CORE-100 编译的类型图生成 Dart 不可变 DTO 与严格 codec，提供只读漂移检查与显式写盘两个入口，禁止多卡手写序列化口径漂移。

**范围**
- 包含：消费 CORE-100 类型图；Dart 不可变类型、codec、密封变体、tuple 与有类型 map 的生成；`gen_dto.py` 的 `--check`（只读）与 `--write`（写盘）入口、漂移报告格式与 0/1/2 退出码；在 `tools/ci/manifest.json` 追加本卡 CI 步骤条目（数据接入点）。
- 不包含：manifest 条目、阶段门禁、快照集合、受限引用、format、敏感路径与错误集合的校验内核（CORE-100）；业务 DTO 字段与 op 实现（各领域卡）；FFI 运行时与信封（CORE-03，下游说明，非本卡契约）；`tools/ci/run_all.py` 的实现与其 manifest 结构（CORE-41）。本卡不实现第二份 schema 语义，只消费类型图。

**依赖**：CORE-01、CORE-02、CORE-100

**接口契约**

```text
tools/ci/gen_dto.py --check [--manifest contracts/dto/manifest.json] [--out app/lib/binding/dto]
                            [--report build/dto/drift.json] [--required-stage S2] [--release]
tools/ci/gen_dto.py --write [--manifest contracts/dto/manifest.json] [--out app/lib/binding/dto]
                            [--required-stage S2]
```

- 两个入口互斥，同时给出或都不给出 → 2。`--check` 只读：不写 Dart 文件，唯一写动作是 `--report` 指定的报告文件（默认 `build/dto/drift.json`）。`--write` 只写 `<out>/<domain>.g.dart`，不写报告文件（只在 stdout 打印摘要）。`--required-stage`/`--release` 的判定由 CORE-100 完成，本卡只透传参数并展示其诊断。
- 退出码：0 = 生成结果与磁盘一致（`--check`）或全部文件写成功（`--write`）且无 error；1 = 存在漂移/缺失/多余生成文件、CORE-100 返回 valid=false（schema 或阶段门禁失败）、或生成被拒绝（类型名冲突、不支持的形状）；2 = 工具错误（参数错误、清单或报告 I/O 失败、CORE-100 抛 SchemaToolError、未预期内部异常）。错误不得从 2 降级为 1，也不得把 1 报成 0。
- 报告（仅 `--check --report` 写出）JSON 固定形状，稳定排序、无时间戳、无绝对主机路径：

```json
{"version": 1, "mode": "check", "manifest": "contracts/dto/manifest.json",
 "required_stage": "S2", "release": false,
 "ready": 36, "pending": 107, "skipped": ["account.import_account_key"],
 "files": [{"path": "app/lib/binding/dto/types.g.dart", "status": "match",
            "sha256": "…"}],
 "diagnostics": [{"severity": "info", "code": "DTO_PENDING_SKIP", "op": "account.import_account_key",
                  "file": null, "message": "SKIP pending account.import_account_key: …"}],
 "exit": 0}
```

  `required_stage` 缺省为 null；`files[].status` ∈ match/drift/missing/stale（stale 表示磁盘有本次不应存在的生成文件）；`files` 按 path 字节序，`skipped` 按 op 字节序，`diagnostics` 按 (file 或空串, code, op 或空串, message) 排序；同一输入重复运行报告逐字节相同。pending 的 `SKIP pending <op>: <blocked_reason>` 来自 CORE-100 的 info 诊断，本卡只展示：既定不失败、也不记为通过（与 CORE-41 的 pending 归档口径一致，main 保持可构建）。
- Dart 产物形状（冻结，属对外 API）：
  - object → `final class`，字段全 final、`const` 构造、`fromJson`/`toJson`；缺必填字段或类型不符抛 `FormatException`（Dart SDK 类型，本卡不新造错误类型）；toJson 只写声明字段，fromJson 忽略未声明的未知键且不因此失败（信封向前兼容）。
  - 可选/nullable → 字段类型加 `?`；缺键与显式 null 均映射 null；required 与 nullable 独立，required 且 nullable 的字段必须出现但可为 null。
  - enum → Dart `enum` + 固定 wire 字符串，映射用生成文件内的 `const Map<String, T>` 与 `switch` 实现（不依赖第三方注解包）；未知字符串抛 FormatException。
  - array → `List<T>` 的不可修改视图（`List.unmodifiable`）；tuple → Dart 3 record 类型 + 同文件 `typedef <Name> = (T1, T2, …);`，按 prefix 位置匹配，长度不符抛 FormatException。
  - 有类型 map（仅 Diagnostic.args）→ `Map<String, String>` 的 `Map.unmodifiable` 副本，所属 DTO 覆写 `==`/`hashCode` 使比较按内容相等。
  - union → `sealed class <UnionName>`，分支名由判别推导：field_const 用 const 值、external_key 用唯一必填键名、scalar_enum 用 enum 值，统一转 PascalCase 并加联合前缀（如 `FormulaNodeSymbol`、`PathSegMoveTo`、`MathKindReal`）；分支为 `final class <UnionName><Branch> extends <UnionName>`，载荷字段直取；未知判别抛 FormatException。派生名重复或与既有类型冲突 → 退出 1 并在 `diagnostics` 指出该分支。
  - 数值映射：int64 → `int`；decimal/uint64/int128/positive-int128 → `String`（原样十进制文本，不经 double，保证 i64 与宽整数无损）；base64 → `Uint8List`；uuid/date-time → `String`；number → `double`（非有限值拒绝）。
  - 不可变与隐私：集合字段深层不可修改；DTO 覆写 `==`/`hashCode` 按值比较；`toString` 对 `sensitive_paths` 命中的字段输出 `<redacted>`，不打印敏感值。
- 域推导与文件布局：`op` 的第一段为域（`account.*`→account、`engine.*`→engine、`calc.*`→calc、`store.*`→store 等），写到 `<out>/<domain>.g.dart`；共享 `types.schema.json`→`<out>/types.g.dart`，`ast.schema.json`→`<out>/ast.g.dart`。同域多 op 与共享类型按 (域, op 或 title) 字节序合并进同一文件；每个文件头写 `// GENERATED CODE - DO NOT MODIFY BY HAND.`、来源 manifest/schema 文件名与 `// generator: CORE-67 v1`（文本常量，不含时间戳/版本库状态），使漂移比较确定。全局唯一 title 只生成一次并放在其声明域文件，生成文件之间用相对 `import` 互相引用。
- 写盘安全与漂移判定：`--write` 先写同目录临时文件再原子 rename；只删除并重写本卡在 `<out>` 内应存在的 `<domain>.g.dart`，不触碰目录外文件，遇同名非生成文件（无 GENERATED 头）拒绝覆盖并以 1 退出；`--check` 以 sha256 比较期望内容与磁盘内容，缺失记 missing，多余生成文件记 stale。
- 输入边界：默认读 `contracts/dto/manifest.json` 与其中引用的 `contracts/dto/*.schema.json`；fixture 的 manifest/schema 放在 `tools/ci/tests/fixtures/`，必须用 `--manifest` 显式指定，不得写入 `contracts/dto/`。S0 自包含 fixture（fixture.echo）用于验收生成器形状，真实清单 36 ready/107 pending 只做结构与漂移验收；`status=ready` 仅表示字段设计闭合，不代表业务实现完成、也不代表消费者已签认。
- pending 不生成类型：pending 条目无 mode/schema，本卡不生成、不猜字段，只在报告 `skipped` 中列出。

**实现约束**
- 生成器只负责格式，不推测领域默认值、不从 schema 猜业务语义；只消费 CORE-100 的类型图与 manifest 文本，不读 SADD、不 import CORE-56/CORE-03 的运行时代码。
- Dart 产物只放 `app/lib/binding/dto/`；`ui/` 可只读 import 纯数据生成文件但不得持 CoreBinding（CORE-01 的 Dart 分层）；只用 dart:convert 等 SDK，不引入第三方 JSON 框架，不手写业务 DTO。
- 数据边界而非依赖：CORE-03（信封）、CORE-56（引擎数据）、CORE-41（CI 聚合）只消费或调用本卡产物/入口。把它们写进“依赖”会形成 CORE-41→CORE-67→CORE-41 与 CORE-03→CORE-67→CORE-100→CORE-03 环（CORE-01 依赖方向、CARD-10），故本卡只在正文声明接入点：CI 侧由 CORE-41 的 manifest 步骤条目调用本卡 CLI，本卡不 import 其实现、不修改其 manifest 结构（沿用 CORE-41 已冻结的 `{version:1,steps:[{id,owner,argv,release_args?}]}` 追加一行）。
- 契约变更按 README §8.4：新增/更改字段先改所有者卡与 schema，再重生成；本卡不改 type/properties 语义。schema 变更须同一提交内重跑 `--write`，main 上 `--check` 必须为 0。
- 生成文件中的类型名与文件布局一旦发布即为对外 API（Flutter 界面只读 import），改名或移动属契约破坏性变更，须 ADR 与消费者通知；本卡不自建第二套命名规则。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-67_TEST.md](../Test/S0/S0_CORE-67_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约540行，分阶段。`tools/ci/dto_emit.py` 340（阶段1 180：不可变类型与严格 codec；阶段2 160：密封变体、tuple、有类型 map、递归与共享合并）、`tools/ci/gen_dto.py` 170（阶段1 100：CLI 参数、域推导、报告、退出码；阶段2 70：逐文件漂移与写盘安全）、本卡 CI 接入 30（manifest 步骤条目与生成目录约定）。阶段1 = 类型图消费 + 不可变类型 + codec + CLI/报告骨架，可独立构建与测试；阶段2 = 密封变体/tuple/typed map/递归合并/逐文件漂移，可独立构建与测试。contracts/dto 数据、生成的 `*.g.dart` 与自测不计；原960行另465归CORE-100，manifest/schema/阶段校验内核不在本卡。
