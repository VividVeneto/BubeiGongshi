# CORE-02 测试方案

> 来源卡：[S0_CORE-02_基座.md](../../S0/S0_CORE-02_基座.md)（错误码注册表与诊断模型）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**

> 阶段划分见来源卡“规模”与“接口契约”末段：阶段1 为本卡 Rust 核心、生成器与消息资源；阶段2 为 Dart 异常桥，须在 CORE-67 生成 `DiagnosticDto` 之后、CORE-03 开工前完成。第 6～9、11～13 条属阶段1；第 10 条的 Rust 部分属阶段1，第 10 条的 Dart 部分与第 14 条属阶段2，阶段门槛见第 15 条。

- [R19] 单元测试：生成器对样例注册表输出确定（两次生成逐字节一致）；重复 code、未知命名空间、缺 message_key 时生成失败；`fix_hint: true` 但 `errors_zh.arb` 缺 `<message_key>.fix` 键、或 arb 存在基键未登记的孤儿 `.fix` 键时同样失败。
- [R19] 构造：`FmlError::new(ErrorCode::UnitOverflow)` 的 domain 为 `"unit"`、retryable 与注册表一致、diagnostics 为空、trace_id 为零值；From<ErrorCode> 等价。with_diagnostic 只追加、保序、不改变外层 code；with_trace 对零值填入，对已有非零值不覆盖；公开 API 不存在覆盖 retryable/domain 的构造或方法（编译期 API 清单检查）。领域单测允许零值；FFI/HTTP 输出非零与关联一致的集成测试分别由 CORE-03、CORE-22/25 执行，本卡不依赖尚未交付的边界才能验收 Rust 核心。
- [R19] （阶段1）漂移检查：修改 `registry.yaml` 而未重新生成时 `tools/ci/gen_errors.py --check` 失败。
- [R20] `contracts/errors/README.md` 由生成器产出，含全部错误码、级别与是否可重试。
- [R19] 往返测试：`contracts/vectors/errors-v1.json` 顶层含 `schema`、`error_version`、`cases`；正例带唯一 `id`（`ERR-nn`）与 `canonical`，负例带 `id`（`ERR-NEG-nn`）、`valid:false` 与 `why`；正例至少 6 条（真实32位 trace_id/多诊断/空诊断/省略可选字段/args乱序各至少一条）、负例至少 7 条且覆盖 `why` 至少 7 种取值；编号不复用、删例留空号。正例经 Rust 反序列化再序列化与 `canonical` 逐字节相同（外层与 Diagnostic 字段顺序固定、args 按键排序、缺省可选字段不输出）；负例按 `why` 分类被拒绝且不 panic。（阶段2）工厂 FmlException.fromJson 在 CORE-67 `DiagnosticDto` 就绪后读出相同 code/trace_id/诊断及其字段；未就绪时明确 Dart 集成未执行，不复制生成类冒充通过。
- [R19] 注册表负例覆盖：缺 owner、无效卡号、重复 code、首段与 namespace 不符、message_key 非派生值、缺简中键、since/废弃版本越界、400–599 外/非整数 http_status、纯端侧码填写 http_status、未知字段（含把 `condition` 写进 registry）均失败；`recovery` 非 `message_key + ".fix"` 派生值、`fix_hint` 未声明却给出 `.fix` 键、`fix_hint: true` 缺 arb 键均失败；服务端缺省 HTTP 映射400。废弃条目保留生成与反序列化能力。缩写/数字段按本卡规则生成，任何变体名碰撞拒绝；as_str/domain/severity/retryable 与 registry 全量对照。
- [R19] 未知 ErrorCode 的 FromStr/TryFrom/serde 均返回错误不 panic；Display/Error 不包含诊断参数或敏感原文。公开字段被修改导致 domain/retryable 或 Diagnostic.severity 漂移时，Serialize/Deserialize 均拒绝；区间倒序/负数/溢出、未知字段/类型、trace 大写/非32位均拒绝；`recovery` 非派生键或对应码 `fix_hint` 为 false 时 Serialize/Deserialize 均拒绝。Dart 另拒绝零 trace 及根信封错误；Rust 领域零 trace 仍允许。
- [R19][R20] registry 是唯一输入：ownership、shared-writes.error、Rust/Dart/README 各投影与 registry 逐项相同；故意改任一镜像后 --check 失败且不写盘，非 error 的 shared-writes 项生成前后保持不变。registry 未创建时，现有 DTOcheck 只验证 SADD 与预分配表的 code/owner 缺项、重复、所有者不符及消费者重定义；预分配表没有 severity/retryable 字段，不作元数据比较通过声明。registry/生成器交付后再验 REG-01（DTOcheck 逐条比对所有者卡表的 owner/severity/retryable/http_status 与 registry）及镜像漂移；此前这部分测试明确未执行，不得以 DTOcheck 退出 0 视为已比对。初次全集必须包含 CORE-03/16/18 共16码。
- [R19] （阶段2）Dart 本地构造：FmlException('SYNC_NOT_AVAILABLE') 的 retryable 等于生成表值、traceId 为非零 32 位小写十六进制且两次构造不同；未登记 code 抛 ArgumentError；传入大写或全零 traceId 抛 ArgumentError；构造器无 retryable/domain 参数（源码扫描）。
- [R19] 阶段门槛：阶段2（`app/lib/binding/errors.dart` 手写桥）未交付时，交付记录与复核只写“阶段1 通过、阶段2 未执行”；在 CORE-67 生成 `DiagnosticDto` 之前以手写类代替生成类、或据此宣称整卡通过均视为本卡验收失败。
