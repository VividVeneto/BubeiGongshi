### CORE-56 内置引擎数据与上下文编排

**目标**：在 S1 提供可断网验收的内置引擎数据与线程安全的引擎上下文，统一 FFI 侧解析、绑定、检查、计算与排版的编排，并定义内置、资源包、用户三层引擎数据的叠加规则（ADR-V5-26）。

**范围**
- 包含：`fml-ffi` 的 `EngineContext` 与纯函数叠加 `compose`；内置只读数据 `assets/engine-v1/` 及引擎数据 JSON 格式；`engine.check`、`calc.evaluate`、`calc.solvable_targets`、`typeset.layout`、`typeset.glyph_outlines` 五个 op 的 DTO 与处理编排（`crates/fml-ffi/src/ops/{engine,calc,typeset}.rs`）；CORE-07 `notation.*`、`constants.resolve` 与 CORE-08 `units.compatible`、`units.convert` 的快照读取适配（`ops/{notation,units}.rs`，DTO 由领域卡定义）；字体字节的哈希与 MATH 表校验及向 CORE-12 注入。
- 不包含：领域算法（CORE-06～12）；用户单位持久化与 `units.*_user` op（CORE-14，推送 User 层）；资源包验签、安装与 `pack.*` op（CORE-95/96，下游说明，推送 Pack 层）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-06、CORE-07、CORE-08、CORE-09、CORE-10、CORE-12、CORE-92、CORE-93、CORE-94

**接口契约**

```rust
// crates/fml-ffi/src/engine_context.rs；仅本 crate 做领域编排与数据注入
pub struct EngineData { pub units: Vec<Unit>, pub kinds: Vec<QuantityKind>, pub profiles: Vec<NotationProfile>,
                        pub constants: Vec<ConstantSet>, pub fonts: Vec<FontData> }
pub enum LayerSource { Embedded, Pack { pack_id: String, pack_version: String }, User { profile_id: String } }
pub struct DataLayer { pub source: LayerSource, pub data: EngineData }
pub struct EngineSnapshot { pub generation: u64, pub unavailable: Option<ErrorCode>, pub data: EngineData,
    pub base_units: Vec<Unit>, pub base_kinds: Vec<QuantityKind> } // 同代Embedded+Pack投影，严格排除User层
pub fn compose(layers: &[DataLayer]) -> Result<EngineData, FmlError>;   // 纯函数，规则见下
// crates/fml-ffi/src/analysis.rs；Rust 内部复用，不新增 FFI DTO 或存储依赖
pub struct AnalysisResult { pub ast: Option<FormulaNode>, pub source_map: SourceMap,
    pub raw_symbols: Vec<RawSymbol>, pub symbols: SymbolEnv, pub check_result: CheckResult }
pub fn analyze_source(source: &str, opts: &ParseOptions, profile: &NotationProfile,
    user_decls: &[SymbolDecl], units: &dyn UnitRegistry, empirical: bool,
    cancel: &CancelFlag) -> AnalysisResult;
pub struct EngineContext { /* RwLock<Arc<EngineSnapshot>> + 写者 Mutex<Vec<DataLayer>> */ }
impl EngineContext {
    pub fn global() -> &'static EngineContext;                         // 首次调用以 Embedded 层构造，generation = 0
    pub fn snapshot(&self) -> Result<Arc<EngineSnapshot>, FmlError>; // exhausted时拒绝；可用性由Arc.unavailable判断
    pub fn generation_status(&self) -> (u64, bool); // 最后代数与available；同锁读取exhausted/unavailable
    pub fn set_layer(&self, layer: DataLayer) -> Result<u64, FmlError>;   // 按逻辑身份新增/替换层：Embedded单例、Pack只按pack_id、User只按profile_id；version仅元数据，返回新 generation
    pub fn remove_layer(&self, source: &LayerSource) -> Result<u64, FmlError>;
    pub fn mark_unavailable(&self, reason: ErrorCode) -> Result<u64, FmlError>;          // 发布 unavailable 快照，generation + 1
}
```

- 引擎数据 JSON（schema=1，未知字段拒绝，字段按 CORE-03 snake_case 映射）：`units.json`、`kinds.json`、`profiles.json`、`constants.json` 均为 `{"schema": 1, "entries": [...]}`，元素为上面对应类型；`fonts.json` 为 `{"schema": 1, "entries": [{"id", "file", "blake3", "spdx", "license_file"}]}`，字体为同目录二进制文件，`blake3` 为小写十六进制；`manifest.json` 为 `{"schema": 1, "files": [{"path", "blake3"}]}`，列出除自身外的全部文件。内置数据在 `crates/fml-ffi/assets/engine-v1/`，编译期 `include_bytes!` 注入，不依赖账户、时钟或磁盘；资源包中的引擎数据（CORE-16 `engine` 目录）用同一格式。向量 `contracts/vectors/engine-data-v1/`。
- 最小单位：SI 七基本单位 m/kg/s/A/K/mol/cd，加 Hz/N/Pa/J/W/C/V/Ω、rad/deg、℃、温差 Δ℃、g、cm、km、min、h、eV；scale/offset 用 CORE-08 表示。cn-default/iso 的全部已声明别名及 Exact/Textbook 各一集合，至少 c、h、e、k_B、N_A 与教材 g=9.8；确切数值源与取得日期写数据记录，教材近似值不得标 Exact。
- 数学字体采用 Latin Modern Math（GUST Font License），固定文件与许可哈希；本卡校验字体字节的 BLAKE3 与 MATH 表后放入 `EngineData.fonts` 交 CORE-12，领域层不读文件；发行许可证核对见附录 C。字体不作为用户数据上传。
- 叠加规则（`compose`）：层序固定为 Embedded → Pack（按 pack_id 字节序）→ User（至多一层）；Embedded 只在构造时给出，`set_layer`/`remove_layer` 指向 Embedded 返回 `ENGINE_DATA_INVALID`。后层同 ID 覆盖前层：Pack 可替换内置单位但量纲与量的种类必须不变，方案与常数集整体替换，同 ID 字体替换字节并保留原位置；两个 Pack 层定义同一单位、种类、方案、常数集或字体 ID 时，后设置的层被拒绝（`ENGINE_DATA_CONFLICT`）；User 层只允许 `user:` 前缀单位，否则 `ENGINE_DATA_INVALID`，同 ID 重复按 CORE-08 `UNIT_DUPLICATE`。合成后整体校验引用、重复 ID、量纲、字体哈希与 MATH 表，且至少有一个含 MATH 表的字体，失败为 `ENGINE_DATA_INVALID`。字体顺序：内置字体在前，再按层序与 `fonts.json` 顺序；`Glyph.font` 下标与 `DisplayList.font_ids`（CORE-12）据此确定。
- 层身份不含Pack.pack_version；同pack_id升级先在副本替换整层再compose，不能保留新旧两层。remove_layer对Pack只匹配pack_id（忽略调用者携带版本），User只匹配profile_id；不存在时返回当前generation不发布。
- 同代基础投影：每个EngineSnapshot的base_units/base_kinds来自同一层副本中仅Embedded+Pack的compose结果，不是从完整data按ID前缀猜测删除，也不读取数据库。调用侧可用 `MemRegistry::from_parts(snapshot.base_units.clone(), snapshot.base_kinds.clone())` 拥有稳定base，再以事务内最新用户定义构造 `MemRegistry::with_user_definitions(&base, &defs)`；两个registry的借用均不得离开持有该快照的本次分析。当前data保留完整已发布User层供普通engine/calc调用；临时事务overlay只供事务分析，不能反向发布或修改Arc。这是S1内部Rust接缝，不增加profile/Store依赖或FFI字段。
- 发布：写者持 Mutex 在副本上分别compose完整层与Embedded+Pack基础投影，二者均成功后在写锁内一起替换同一个 Arc 并令 generation + 1；失败不改变快照与层集合。在途任务持旧 Arc，后续请求取新快照；读者只在读锁内克隆 Arc。`mark_unavailable` 发布 `unavailable = Some(reason)` 的快照，此后五个 op 均返回 `ENGINE_UNAVAILABLE`，直到下一次 `set_layer`/`remove_layer` 成功。
- 推送者：CORE-95 的安装/恢复/卸载 `pack.*` 处理（`crates/fml-ffi/src/ops/pack.rs`）在恢复、安装、卸载后设置或移除 Pack 层；CORE-14 的 `units.*_user` 处理（`crates/fml-ffi/src/ops/units_user.rs`）在打开档案和用户单位提交后设置 User 层，关闭档案时移除，提交后设置失败调用 `mark_unavailable`。bootstrap 包的引擎数据由 CORE-16 工具从同一 `assets/engine-v1/` 生成，CI 比对两者 BLAKE3；安装它只使 generation + 1，结果与内置一致。
- FFI op（本表为五个 op 的唯一登记；DTO 未列字段按 CORE-03 映射规则，坐标为 JSON 数值，保留 2 位小数）：

| op | 入参 → 出参 | 长任务？ |
| --- | --- | --- |
| `engine.check` | {source, notation_profile_id, user_decls, empirical} → {ast, source_map, symbols, check_result}（CORE-06/07/09 的 DTO） | 否 |
| `calc.evaluate` | {source, notation_profile_id, user_decls, empirical, assignments, target, output_unit?, interval?, given_constants, display} → CalcResult（CORE-10）；支持 `budget_ms`，默认 200 | 否 |
| `calc.solvable_targets` | {source, notation_profile_id, user_decls, empirical} → {targets: [{symbol, capability}]}（CORE-93 SolveCapability） | 否 |
| `typeset.layout` | {ast, symbols, options: LayoutOptions} → DisplayList（CORE-12） | 否 |
| `typeset.glyph_outlines` | {font_id, glyph_ids: [u16]} → {units_per_em, outlines: [{glyph_id, segs: [PathSeg]}]}，字体设计单位、y 轴向上 | 否 |

- 纯分析接缝：`analyze_source` 只消费显式传入的源码、CORE-06 ParseOptions、CORE-07 NotationProfile、CORE-05 SymbolDecl、CORE-08 UnitRegistry、empirical 与 CancelFlag，不读 EngineContext::global、档案、文件、数据库或时钟，不接收 Connection/Store。先 CORE-06 parse，保留原始 SourceMap/raw_symbols；ast=None 时不调用 bind/check，symbols 为 `SymbolEnv { decls: vec![] }`、typed=None、validation=Invalid，诊断保留解析结果，绝不伪造 Hole/空 AST。ast=Some 时用同一 AST/raw_symbols 调 CORE-07 bind，再调 CORE-09 check；check_result.diagnostics 按 parse、bind、check 顺序拼接，保留全部级别且不去重/改码。任一 Error 使最终 Invalid；无 Error 时保留检查器的 Invalid/Draft/Unresolved，检查器已验证但存在未绑定或 needs_confirm 诊断则降为 Unresolved，其余保留 Verified/VerifiedPolymorphic；Invalid 清空 typed。Hole 的解析 Error 不因检查器仅返回 Unresolved 而丢失。该结果只供 Rust 编排，已有 CheckResponse/ParseResult wire 形状不变。
- 接缝消费（下游说明，非契约）：CORE-31 逐候选注入适配可保留 ast=None 及 raw_symbols 用于评分；CORE-26/66 的 S6 fml-ffi 附属适配把事务只读数据构造为显式 profile/units 输入后调用本函数，再按 CORE-13 RemoteRevisionAnalyzer 契约映射失败或本地验证状态。trait 与事务类型归 CORE-13，具体存储适配归调用卡，不倒灌到本 S1 卡；CORE-56 不增加 CORE-13/26/31/66 依赖。conditions 是调用侧已有 AST，既不当源码重解析，也不在本 helper 中被悄悄删除或替换。
- 处理编排：`engine.check` 固定 parse → bind → check，注入同一快照的单位与方案；`calc.*` 在同一快照上重跑同一链路得到 `revision_ast`、`symbols`、`typed`（SymbolId 与 `engine.check` 一致）再构造 CORE-10 `CalcRequest`，校验结果不是 Verified/VerifiedPolymorphic 时返回 `EVAL_NOT_COMPUTABLE`；常数按 given → textbook → exact 解析。`typeset.layout` 传入快照的 `fonts`；`typeset.glyph_outlines` 的 `font_id` 不在快照中时返回 `TYPESET_NO_FONT`。上述链路复用 analyze_source；`engine.check` 的 ast=None 映射首条解析 Error 为 FmlError（保留诊断），不输出不符合 CheckResponse 的 null AST；ast=Some 的 Invalid/Unresolved 仍为成功 CheckResponse，不能因诊断 Error 改成外层失败。未知方案由处理层查同一 Arc 的 profiles 时按 `NOTATION_UNBOUND` 返回，不以默认方案替代；领域错误码沿用各领域卡，不新设重复码。

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `ENGINE_DATA_INVALID` | error | 否 | 层数据违反 schema、引用不存在、重复 ID、量纲或种类改变、字体哈希或 MATH 表校验失败、合成后无 MATH 字体；试图设置或移除 Embedded 层；User 层含非 `user:` 单位 |
| `ENGINE_DATA_CONFLICT` | error | 否 | 两个 Pack 层定义同一单位、种类、方案、常数集或字体 ID；后设置的层被拒绝 |
| `ENGINE_UNAVAILABLE` | error | 是 | 快照已被mark_unavailable标记、generation耗尽，或请求expected_generation与所取快照不一致；前两者恢复前拒绝，代数不一致由调用者重新查询后重试 |

快照通知接缝：每次成功set_layer/remove_layer/mark_unavailable在写锁外唤醒CORE-73（下游说明，非契约）的等待者；无变化不唤醒。快照发布和代数递增在同一锁内原子完成，u64耗尽返回ENGINE_UNAVAILABLE且不发布。CORE-03 expected_generation比对发生在取得Arc后、执行算法前，不匹配不运行；响应engine_generation来自该Arc。通知适配及Dart源的实现归CORE-73，发布接缝的20行预算和测试归CORE-73附属，本卡规模不重复计入。

FFI错误镜像（不重定义代码；通用信封错误见CORE-03；读取快照的适配另由CORE-56（下游说明，非契约）统一返回ENGINE_UNAVAILABLE）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| calc.evaluate | ENGINE_UNAVAILABLE、PARSE_SYNTAX、PARSE_FORBIDDEN_COMMAND、PARSE_UNSUPPORTED_COMMAND、PARSE_TIMEOUT、PARSE_HOLE_UNFILLED、PARSE_LIMIT_EXCEEDED、NOTATION_UNBOUND、NOTATION_AMBIGUOUS、NOTATION_LOG_BASE、TYPE_DIM_CONFLICT、TYPE_LOG_DIMENSIONED、TYPE_FUNC_ARG_DIMENSIONED、TYPE_MATHKIND_MISMATCH、TYPE_CROSS_DIM、TYPE_QK_MISMATCH、TYPE_UNKNOWN_DIM、TYPE_EMPIRICAL_COEFF、TYPE_AFFINE_MISUSE、UNIT_DIM_SYNTAX、EVAL_DIV_ZERO、EVAL_DOMAIN、EVAL_NAN_OR_INF、EVAL_OVERFLOW、EVAL_NO_CONVERGE、EVAL_NEEDS_INTERVAL、EVAL_NOT_COMPUTABLE、EVAL_LIMIT_EXCEEDED、EVAL_TIMEOUT、EVAL_MULTI_BRANCH、UNIT_UNKNOWN、UNIT_INCOMPATIBLE、UNIT_AFFINE_MISUSE、UNIT_OVERFLOW、NOTATION_CONSTANT_CONFLICT |
| calc.solvable_targets | ENGINE_UNAVAILABLE、PARSE_SYNTAX、PARSE_FORBIDDEN_COMMAND、PARSE_UNSUPPORTED_COMMAND、PARSE_TIMEOUT、PARSE_HOLE_UNFILLED、PARSE_LIMIT_EXCEEDED、NOTATION_UNBOUND、NOTATION_AMBIGUOUS、NOTATION_LOG_BASE、TYPE_DIM_CONFLICT、TYPE_LOG_DIMENSIONED、TYPE_FUNC_ARG_DIMENSIONED、TYPE_MATHKIND_MISMATCH、TYPE_CROSS_DIM、TYPE_QK_MISMATCH、TYPE_UNKNOWN_DIM、TYPE_EMPIRICAL_COEFF、TYPE_AFFINE_MISUSE、UNIT_DIM_SYNTAX、EVAL_NOT_COMPUTABLE、EVAL_LIMIT_EXCEEDED |
| engine.check | ENGINE_UNAVAILABLE、PARSE_SYNTAX、PARSE_FORBIDDEN_COMMAND、PARSE_UNSUPPORTED_COMMAND、PARSE_TIMEOUT、PARSE_HOLE_UNFILLED、PARSE_LIMIT_EXCEEDED、NOTATION_UNBOUND、NOTATION_AMBIGUOUS、NOTATION_LOG_BASE、TYPE_DIM_CONFLICT、TYPE_LOG_DIMENSIONED、TYPE_FUNC_ARG_DIMENSIONED、TYPE_MATHKIND_MISMATCH、TYPE_CROSS_DIM、TYPE_QK_MISMATCH、TYPE_UNKNOWN_DIM、TYPE_EMPIRICAL_COEFF、TYPE_AFFINE_MISUSE、UNIT_DIM_SYNTAX、UNIT_OVERFLOW |
| typeset.glyph_outlines | ENGINE_UNAVAILABLE、TYPESET_NO_FONT、TYPESET_MISSING_GLYPH |
| typeset.layout | ENGINE_UNAVAILABLE、AST_JSON_INVALID、PARSE_LIMIT_EXCEEDED、TYPESET_MISSING_GLYPH、TYPESET_DEPTH_EXCEEDED、TYPESET_NO_FONT |

所有读取本卡快照的FFI适配（含notation/units/derive消费方）在available=false时返回ENGINE_UNAVAILABLE；该检查在snapshot()?取得Arc后、领域调用前完成。ENGINE_DATA_INVALID/CONFLICT只用于层变更，不混入只读op错误镜像。成功diagnostics保留领域warning/info，不能按severity过滤掉。

generation耗尽的故障语义：所有发布入口均返回Result，mark_unavailable亦然。达到u64::MAX后不回绕、不发布新Arc、不发通知；保留的旧Arc只供已在途读者完成，EngineContext另置不可逆exhausted标志，snapshot()及后续FFI算法请求返回ENGINE_UNAVAILABLE，查询/等待可读最后代数及available=false；重新创建引擎实例才恢复。提交后set_layer失败的适配必须处理mark_unavailable的Err，不回滚已提交Store，不继续发布可用业务会话。该标志和快照读取在同一锁下判定。

**实现约束**
- 所需输入：编译期数据、调用方已读入并构造好的 `DataLayer`、请求 DTO、取消标志；本卡不读资源包文件或数据库，领域 crate 不读本上下文的全局单例。S1 通过测试用 fml_call 接入，不要求平台层提前实现 S2。
- 并发只用标准库 `RwLock`/`Mutex`/`Arc`；写锁内不做 I/O、不调用回调，持锁时间只覆盖指针替换。
- 外部前提：字体官方分发与许可 https://www.gust.org.pl/projects/e-foundry/lm-math；数值依据 BIPM SI 定义与 NIST CODATA 2022。首次构建记录字体和数据哈希。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-56_TEST.md](../Test/core/S1_CORE-56_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 575 行；主包 `crates/fml-ffi/`（`engine_context.rs`、`analysis.rs` 与 `ops/{engine,calc,typeset,notation,units}.rs`）；assets/engine-v1/ 数据与字体不计，发布接缝由 CORE-73 计。分阶段：① 引擎数据与上下文（类型、compose、字体校验、数据加载、EngineContext、可用性检查、notation/constants/units 六个 op、错误，同代基础投影与一致性约20，合计约410）；② 引擎编排 op（engine.check、calc.*、typeset.* 五个 op，含可复用的 parse→bind→check 分析函数，诊断状态收敛与可选AST接缝约20，合计约165）。

