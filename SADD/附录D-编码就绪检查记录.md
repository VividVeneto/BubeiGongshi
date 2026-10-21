# 附录 D：编码就绪检查记录 v5.3.3

> 版本：v5.3.3 ｜ 检查日期：2026-10-20 ｜ 效力：说明性；历史批次见D.4～8，v5.3 P0处理/证据见D.9，当前106卡就绪状态见D.10，v5.3复核与v5.3.1修订见D.11，整卡语义复核见D.12，v5.3.3独立复核/修订及P2见D.13；规范性要求以README与01～03模块卡为准。
> 关联文档：[README](README.md)（§8.5 就绪定义、§6 已确认与待确认事项）、[01 公共核心](core/00-总览.md)、[02 Android 端](and/00-总览.md)、[03 Windows 端](win/00-总览.md)、[S0 卡片](S0/)、[附录 A](附录A-架构决策与评审记录.md)（ADR-V5-12～40）。

## D.1 检查方法

- 当前对象：106 张有效卡（CORE 76、AND 14、WIN 16）；AND-10、WIN-11 已撤销，不计有效卡。早期69/74张是历史检查批次，不再用于当前就绪统计。
- 清单：README §8.5 的 a～g 七项（结构与规模、依赖闭合、契约唯一、契约可编码、验收可测、追踪一致、外部前提）。
- 机械项：七字段、声明的规模与构建单元、依赖与索引/图、无环及前置阶段不晚于本卡、需求双向追踪由临时脚本检查。0项只说明所覆盖的机械规则未发现问题，不等于接口、规模可行性或平台API已验证；脚本是辅助证据，不签发开工许可。
- 语义项（类型与错误码可追溯、DTO 与表结构完整、验收可执行、外部前提）逐卡人工判断。
- 结论口径：历史表“已修订/新增”只记录改动，不能推导符合README §8.5。当前评级与状态唯一看D.10：C为未就绪、按D.14先修现行阻断；A/B卡仍须完成整卡语义复核。未复核不得写“就绪”。产品Q32～Q40保持暂行默认、待甲方确认；Q1～Q31历史确认不变。

## D.2 统计

<!-- sadd-current-stats:start -->
由 `node tools/sadd/stats.mjs` 从现行卡与D.10生成；不代表实现或真机验收通过。

| 文档 | 当前有效卡 | 历史撤销 |
| --- | --- | --- |
| CORE | 78 | 无 |
| AND | 14 | AND-10 |
| WIN | 16 | WIN-11 |

总计108卡；当前独立复核等级：B=84、C=24；就绪=0。
<!-- sadd-current-stats:end -->

v5.3.1（2026-10-20）：§D.10 第6列 A=2、B=54、C=11、未复核=16，就绪=0（尚无 §D.12 复核通过记录）。以下为 v5.3 历史统计：原评审逐行统计 A=4、B=47、C=30（81卡）；core-a尾注自报B10/C8与其逐卡表B11/C7不一致，本表按逐卡行计数。本轮修订后P0复核 B=37、C=23（其中3张保持原C、P0未涉及），其余未复核=23；新卡无原评审等级。未完成83卡整卡语义复核，不宣称全部就绪；实现/真机证据另在编码与交付阶段提供。

- 历史拆分/新增记录（以下11张为早期批次，不是当前新增统计）：CORE-45 邮箱验证码与发信（自 CORE-22 拆出）、CORE-46 同步与升级协调器（自 CORE-26 拆出）、CORE-47 设置页与账户安全界面（自 CORE-36 拆出）、CORE-48 计算器、代入与计算链界面（自 CORE-38 拆出）、CORE-49 学习统计、提醒设置与自建书界面（自 CORE-39 拆出）、CORE-50 识别结果、云端确认与识别历史界面（自 CORE-40 拆出）、CORE-51 资源包下载、导入与管理界面（自 AND-10、WIN-11 抽出两端共用部分）、CORE-52 公式复制格式与富格式导出（2026-10-19 按 README §6 Q12 确认新增）、CORE-53 LaTeX 命令补全、CORE-54 公式库批量选择与批量操作（2026-10-19 按 README §6 Q16 确认新增）、WIN-14 快捷键自定义（2026-10-19 按 README §6 Q11 确认新增）。
- 撤销卡：AND-10、WIN-11。两卡的内容是两端相同的 Dart 行为，并入 CORE-50、CORE-51，平台差异只剩端口实现（ADR-V5-19）。编号不复用。
- v5.3.1历史卡数83；v5.3.3当前卡数由上述生成块与D.10共同核对，历史批次不覆盖。

## D.3 共性修订

1. 组装层与平台接缝：CORE-04 增加 `composition/`（`FeatureRegistry`、`CompositionContext`、`Installer`、`entry.dart` 的 `runPlatformApp`），`PlatformPorts.platformInstallers` 供平台卡登记接缝实现；CORE-36 增加 `composeApp`、门面、启动钩子顺序表、路由归属表与外壳扩展接缝；平台卡不修改共享界面文件。
2. 每张卡补错误码表（错误码 / 级别 / 可重试 / 触发条件），级别统一为 error、warning、info。
3. 性能类验收只引用 CORE-01 全局资源预算表的行名；预算表补“本地模型识别”“本地模型首次加载”两行。
4. 验收标签统一为方括号形式，功能近似条款写作 `[R04][R04.h]`；README §5 最后一列按各卡验收标签重新生成。
5. 规模超出或跨多个构建单元的卡：拆卡，或在规模中写明主包与附属的行数（README §8.5 a）。
6. 外部前提统一写在“实现约束”末条；版本号在 M0 按 ADR-V5-15锁定，文档不写未核实的版本号。
7. 新发现的产品取舍列为 README §6 Q11～Q15（2026-10-19 均已确认），纯工程选择当时列为 ADR-V5-12～20；当前采纳/待定状态以附录A §A.4为准。

## D.4 公共核心

| 编号 | 名称 | 历史改动结论 | 评审等级（2026-10-19） | 修订后等级（本轮） | 修改摘要 | 历史遗留（当前见D.10） |
| --- | --- | --- | --- | --- | --- | --- |
| CORE-01 | 仓库骨架与工程约定 | 已修订 | B | B | 补命名约定与提交约定（type(模块编号): 摘要）；外部前提（工具链版本按 ADR-V5-15 M0 锁定）；验收补 [R23] | — |
| CORE-02 | 错误码注册表与诊断模型 | 已修订 | B | B | 注册表字段表（code/namespace/severity/message_key/retryable/since/deprecated_since/http_status）与取值规则；FmlError JSON 形态（FFI 与服务端共用）；规模拆分主包与附属；新增 JSON 往返验收 | — |
| CORE-03 | C ABI 与 Dart 绑定 | 已修订 | B | — | FFI 返回码表（-1～-6 含触发条件）、fml_cancel 语义、回调线程与并发上限 64、capabilities 示例、DTO 映射规则（全局适用）；Dart CancelToken/FfiException/FfiCancelled 定义；CoreBinding.open(CoreLibrarySpec) 与 spec（多 isolate）、fml_call 线程安全、Dart DTO 归属规则 | — |
| CORE-04 | 平台端口契约 | 已修订 | B | B | （追加）组装原语 FeatureRegistry、CompositionContext、Installer、StartupHook，使各卡安装点不依赖编号更大的 CORE-36；规模 440 | — |
| CORE-05 | 公式 AST 与修订模型 | 已修订 | C | B | 补全 AST 辅助类型（NumberLiteral、UnitRef、各运算枚举、FunctionId 规范名）；从 CORE-07/09 迁入存储形类型 SymbolEnv/SymbolDecl/TypeDecl/MathKind/Validation/ConfirmRecord 以消除前向引用；CancelFlag；check_limits、from_canonical_json；规范 JSON 规则与 AST-01～05 向量；错误码表；FormulaItem 增 course，FormulaRevision 增 draft（CORE-14 需要）；FormulaNode 增 Hole(u16)（ADR-V5-17） | — |
| CORE-06 | LaTeX 子集解析与导出 | 已修订 | B | B | RawSymbol/RawHint 定义；engine.parse/engine.export DTO；错误码触发条件表；LX-01～10 往返向量；性能项改引 CORE-01 预算行；外部前提 cargo-fuzz nightly；白名单增 \fmlhole、错误码 PARSE_HOLE_UNFILLED、向量 LX-11 | — |
| CORE-07 | 符号表、记号方案与常数集 | 已修订 | C | C | SymbolEnv 等存储形类型迁至 CORE-05，本卡保留绑定与常数逻辑 | — |
| CORE-08 | 量纲与单位 | 已修订 | C | B | 量纲文本语法与 parse/to_text；UnitRegistryMut、UnitDefinition 定义；错误码触发条件（新增 UNIT_DIM_SYNTAX、UNIT_IN_USE、UNIT_DUPLICATE）；新增量纲文本验收；新增 units.list_user、units.delete_user（单位页需要） | — |
| CORE-09 | 类型推断与量纲校验 | 已修订 | B | B | MathKind、Validation 迁至 CORE-05；补 TypeDecl 量纲文本的解析规则；Hole 按未知类型处理，状态至多 Unresolved | — |
| CORE-10 | 计算器与数值求解 | 已修订 | B | B | DisplayPrecision、SolveCapability 定义；数值约定（f64、Brent 容差与迭代上限、自动 bracket 参数、一阶最坏情况误差传播）；CX-01～10 计算向量；错误码触发条件，新增 EVAL_TIMEOUT | — |
| CORE-11 | 公式间代入、推导链与计算链 | 已修订 | B | — | MatchLevel、RevisionSnapshot、AncestryLookup、RevisionLookup 定义；rank_candidates 增 include_cross_kind 参数；错误码触发条件 | — |
| CORE-12 | 排版 DisplayList | 已修订 | B | B | 补 WrapMode、Rect、PathSeg、DrawCmd 定义与 layout_version；明确 typeset.load_fonts/layout 请求响应，hit_test 改为 Flutter 侧按 hit_regions 判定；错误码触发条件；性能验收引用 CORE-01 预算行；Hole 虚线框；新增 op typeset.glyph_outlines（Flutter 无法按字形 ID 绘制）；2026-10-19：公开 glyph_outline 供 CORE-52 SVG 导出 | 数学字体最终选型待附录 C 许可审查；开发期用 Latin Modern Math |
| CORE-13 | 本地库 Schema、单写者与迁移 | 已修订 | B | B | 补 WriteTx/ReadTx、OutboxOp、IntegrityReport；迁移文件命名与序号规则；基础设施表 DDL；业务表归属清单（DDL 下放到归属卡）；错误码触发条件；外部前提 rusqlite/SQLCipher | — |
| CORE-14 | 公式库仓储 | 已修订 | C | B | 复用 CORE-05 的条目/修订类型，补 NewRevision、ItemView、Page、RevisionDiff 等；搜索语义；8 张业务表与 FTS5 列定义；新增 library.substitution_pool（CORE-11 引用）与 LIB_IMPORT_TOO_LARGE；CSV 细则；验收补 [R04.j] 标签与可测数值；mastery_cache 表归属移至本卡（CORE-14 搜索需按掌握度筛选），MasteryState 统一为 CORE-20 原有四态；calculation_plan 表归属移至 CORE-48；补脱离规则；2026-10-19（Q16）：新增 ItemMeta 与 update_meta（library.update_meta；原契约中编辑页的标签与课程无处保存）、SearchQuery.trashed（回收站页原无查询入口）、LIB_META_INVALID（规模仍约 500，搜索语义段压缩表述） | — |
| CORE-15 | 资源包格式、验签与安装 | 已修订 | C | C | 补 Manifest、ManifestEntry、EntryReader、SecurityState、UpdateMetadata、PackOffer；各 op 请求响应；installed_pack 表；11 个错误码触发条件表；外部前提（ed25519-dalek、zip、tough 等）；元数据验收 | 首个签名 key_id 须在发布前登记（CORE-16/43） |
| CORE-16 | 内容管线与课程内容包 | 已修订 | C | C | 补条目主要字段类型与取值表（考试范围、要求层级改用拼音代号）、命令退出码与报告 JSON、CONTENT_ 错误码、签名私钥格式；验收补 [R39] 独立条目与 [R04.f][R04.g] 标签；外部前提（YAML crate、离线签名机） | 各课程包内容按批次作为数据任务编写 |
| CORE-17 | 卡片生成与 FSRS 排程 | 已修订 | C | B | 补 EventFlags、RequirementLevel、FsrsParams、CardSchedule、DailyCaps、DueQueue、OptimizeOutcome；各 op 请求响应；study_card/review_event 表；重放顺序；错误码触发条件；FS-01～FS-08 样例；fsrs 版本核实为 6.6.2；评分映射明确归 CORE-19；规模声明附属 | — |
| CORE-18 | 三层判分器 | 已修订 | B | B | 以 GradeTarget/GradeAnswer 取代对 CORE-17 CardType 的引用（避免反向依赖）；补 RequiredForm、SamplePoint；抽样参数（点数、区间、容差、ChaCha8）；错误码触发条件；验收补 [R04.c][R04.e] 标签与预算行引用 | — |
| CORE-19 | 学习会话与组学习循环 | 已修订 | C | B | 补 BookSource、Chapter、AnswerMode、QuestionDto、QuestionSource、Distractor、RatingMap、GroupSummary、GroupState；计划字段取值范围；重现位置；各 op 请求响应；5 张表；错误码触发条件；验收补子需求标签、续学边界与自建书（R04.j）；新增界面边界 DTO（UiAnswer、AnswerSubmission、SessionInput、QuestionView 不含标准答案、UiCommand 含 Feedback/NeedSelfRate、RelatedFormula、TodayInfo）、Attempt.self_knew、op 表（books.get/update/delete、plan.get、today）、错误码 STUDY_BOOK_READ_ONLY、STUDY_INPUT_INVALID；Undetermined 自评流程明确 | — |
| CORE-20 | 学习统计、掌握度与本地提醒 | 已修订 | C | B | 补 Granularity、DayStat、MasteryDistribution、StatsCache；指标口径；新增 stats.due_count 与 STUDY_STATS_RANGE_INVALID；stats_cache 表；验收补 [R04.d][R04.i]；规模声明跨语言附属；新增安装点说明（installers.dart 追加一行） | — |
| CORE-21 | 密钥体系与加密原语 | 已修订 | B | B | 补 KeyPurpose/HKDF info、Sealed 字节格式、AAD CBOR 规则、恢复码改为 26 位数据 + 1 位 Crockford mod-37 校验（27 位）、口令策略、KdfParams 默认值、错误触发条件、KV-01～07 测试向量与外部前提 | — |
| CORE-22 | 服务端骨架与身份认证 | 已修订（拆分） | C | C | 原卡约 700 行超限：验证码与发信拆为 CORE-45；补全端点请求/响应、令牌有效期、EmailCodeService 端口、Dart ApiClient/TokenStore、表结构、错误码触发条件表；身份服务形态记 ADR-V5-14；新增 GET /v1/devices（设备管理界面需要） | ADR-V5-14 M0 定案 |
| CORE-23 | 账户状态、登录边界与本机解锁 | 已修订 | C | C | 补 GuestLocked 状态与启动规则、device_registry 表、BlobKind 与平台密钥别名约定（与 AND-03 一致）、op 请求/响应表、注册/找回口令/验证码用例、TokenStore 实现、错误码触发条件；去掉应用自有 PIN（改由系统认证），附属声明 | AND-03/WIN-04 须提供 fml://auth/callback 深链 |
| CORE-24 | 游客转注册与游客并入 | 已修订 | C | C | 补 UpgradeMode/AccountKeyMaterial/StepInput/KeyOutput、abandon、步骤完成条件与重入表、upgrade_journal/account_key_wrap/account_key 表、MergeInto 两种本地情形、UUIDv5 命名空间与 name 编码、op、错误码触发条件；原 UpgradeIo 回调改为“调用方传入网络结果”的纯本地步进（核心无 Rust→Dart 网络回调），联网协调归新卡 CORE-46 | — |
| CORE-25 | 服务端同步存储与账户删除 | 已修订 | B | B | 补全端点请求/响应（新增 sync/reset、keys/min-version、删除状态查询）、Envelope 字段类型表、游标格式、表结构、配额数值、删除状态机、错误码触发条件表与外部前提；验收补快照、重置、越权 | 对象存储产品随 CORE-43 选定 |
| CORE-26 | 同步引擎（加密、合并与隔离） | 已修订 | C | C | 改名“同步引擎（加密、合并与隔离）”：核心无 Rust→Dart 网络回调，原 SyncTransport 改为 prepare_push/ack/apply_pull 等本地步进 op；补实体类型与 KeyPurpose 映射、负载 CBOR 与 AAD、字段逻辑时钟、merge_choice 确定性 ID、0026_sync.sql 表、错误码触发条件；依赖补 CORE-19 | 网络协调见 CORE-46 |
| CORE-27 | 备份导出与恢复 | 已修订 | B | B | 补 .fmlbackup 字节格式（头、WrapRecord、1 MiB 分块 AEAD、末块标记）、范围→表映射与永不导出表、两阶段恢复（prepare/commit/discard + token）、Merge/Replace 逐表规则、replay 与缓存处理、FFI op、7 码错误表；去掉与 CORE-13 重复的迁移前快照；识别历史不导出（资产归 CORE-32）；依赖补 CORE-17 | — |
| CORE-28 | 隐私守卫、日志与复现包 | 已修订 | C | C | HttpRequestSpec 改为 CORE-04 的 HttpRequestDto；放行规则表（状态×用途）；ConsentVerifier 接口反转对 CORE-34 的依赖；GuardContext；LogValue 类型层面禁止文本；Rust 日志与 core.log_init；复现包移到 Dart（合成源码重排版）+ 脱敏扫描规则；V1 不提供诊断上报（diagnostics 恒拦截）；错误码表；依赖补 CORE-03；规模主包/附属；新增安装点说明（installers.dart 追加一行） | 组装层（CORE-36/平台 composition）须实现 GuardContext 并只暴露 NetworkGuard |
| CORE-29 | 识别契约与后端注册 | 已修订 | A | — | PreparedImage（CORE-30 产物，反向依赖）改为本卡 RecogImage；补 AccountKind/InputKind/CorrectionHint/AlignSpan，expected_type 改为 CORE-05 MathKind；Registry 分本地后端与远程描述符，run 检查顺序；墨迹渲染参数（tiny-skia+png 确定性）；FFI op recog.backends/register_remote/run；错误表 | — |
| CORE-30 | 图片解码与预处理 | 已修订 | B | — | 补 ImageFormat/ImageInfo/WorkingImage；FFI op 改为暂存区文件路径进出（不经 JSON 传图）；8 码错误触发表；外部前提 image/zune-jpeg/image-webp/kamadak-exif 与 fuzz 目标；性能验收引用 CORE-01 预算行 | — |
| CORE-31 | 识别候选后处理与忠实转写 | 已修订 | B | — | 依赖补 CORE-08（UnitRegistry）；评分公式；FFI op recog.postprocess/correct/final_check；白名单过滤规则；错误表新增 RECOG_SPAN_INVALID | — |
| CORE-32 | 识别会话状态机与历史 GC | 已修订 | C | C | 补 SessionState/InputSource/AssetKind/TransitionPayload/PendingCloudJob/SessionSummary/GcPlan/GcReport/RecoveryReport/HistoryFs；五张表 DDL（0032_recognition.sql，history_key 存于 recognition_counter）；状态转换合法表；FFI op 请求响应；错误表（新增 RECOG_TRANSITION_INVALID）；删除“另存为公式附件”（V1 用 Pin 代替）；规模主包/附属；CORE-13 归属清单补 recognition_counter、pending_cloud_job；新增 recog.settings.get/set op 与 recognition_counter 的 keep_last、history_disk_cap_mb 列 | — |
| CORE-33 | 服务端云识别网关与 worker | 已修订 | C | C | 新增 GET /v1/recognition/policy 与 POST /v1/recognition/consents（含监护人确认）；jobs 请求改带 consent_id + policy_version；取消语义；ProviderPrompt/ProviderOutput/ProviderError 定义；五张表 DDL；worker 取任务方式；配置键与默认配额；12 行错误表；外部前提；同意与哈希验收；规模改 480 | ADR-V5-16（待定） 云识别供应商（待定，M0 定案） |
| CORE-34 | 云识别客户端与授权回执 | 已修订 | B | B | 与 CORE-33 新接口对齐（policy/consents/jobs）；同意改由服务端记录（删除本地 consent_receipt 表）；年龄自我声明 + 监护人确认；实现 ConsentVerifier 并给出校验规则；幂等键用 UUIDv5(session, imageHash) 免持久化；recog.register_remote 登记时机；状态映射表含会话状态；错误表（新增 CLOUD_TOKEN_EXPIRED、CLOUD_PREVIEW_STALE）；外部前提；新增安装点说明（installers.dart 追加一行） | 监护人身份不核验，按 README §6 Q14（待确认）暂行默认撰写 |
| CORE-35 | 本地识别模型后端 | 已修订 | B | B | 模型扩展字段从 manifest 移到包内 model/model.json（原写法与 CORE-15“未知字段拒绝”冲突）；给出 model.json 全字段；InferenceEngine 内部抽象 + FakeEngine，使运行时未定案也可编码；预处理与束搜索流程；FFI op recog.local.register/unregister/unload_all；错误表；卸载时机；CORE-01 预算表新增两行 | ADR-V5-13（待定） 推理运行时（待定）；实际模型与许可待附录 B/C 实验结论 |
| CORE-36 | 应用壳、组装层、账户入口与导航 | 已修订（拆分） | C | C | 改名“应用壳、组装层、账户入口与导航”；新增组装层 composeApp 与 installers.dart 安装点机制（后续卡各追加一行）、AppDeps、SyncFacade/UpgradeFacade 门面及 Disabled 实现（原 CORE-46 引用但未定义）、启动钩子 order 表与登记者、账户入口含邮箱验证码与找回口令路由；依赖加 CORE-22；设置页拆到新卡 CORE-47 | — |
| CORE-37 | 公式渲染组件与编辑器 | 已修订 | C | C | 重写：源码为唯一事实、UTF-8/UTF-16 换算、停靠点导航、空位 \fmlhole 与 15 种模板片段、删除/撤销/粘贴/模式切换规则、EditorWorker 后台 isolate、字形路径绘制、错误码与界面行为表；依赖去掉 CORE-36，加 CORE-04、CORE-08；新增 EditorWorker.layoutStatic 与 MathText（只读公式显示，供 38/39/48/49 使用）；2026-10-19：去掉 FormulaRichCopy，改为 FormulaCopyFormat、FormulaCopier 接缝与共享 FormulaCopyButton（“复制为”菜单）；2026-10-19（Q16）：新增 LatexSourceAssist / LatexSourceSession 接缝，LaTeX 源码框可由 CORE-53 包裹 | 默认输入模式不保存偏好，按 README §6 Q13（待确认）暂行默认撰写 |
| CORE-38 | 公式库界面 | 已修订（拆分） | C | C | 原卡含公式库+计算器+代入+计算链，超出 500 行；本卡只保留公式库界面：路由、LibraryVm/FormulaDetailVm/FormulaEditVm(SaveOutcome)/ImportWizardVm/UserUnitsVm；附属草稿仓储与 formula_draft 表及 library.draft_* op；修正原卡错误 op 名；错误码与界面行为表；验收补 [R04.j]、[R08]、[R15]；新建页接受 NewFormulaArgs 预填 LaTeX 并以 Saved 作为返回值（供 CORE-50）；2026-10-19：详情页与列表菜单加入复制公式（CORE-37 FormulaCopyButton）；`/library?search=1` 聚焦搜索框（供 WIN-08 查找快捷键）；2026-10-19（Q16）：LibraryQuery.trashed、LibraryListDecorator 接缝（CORE-54 多选）、保存时调用 library.update_meta，规模约 500 | — |
| CORE-39 | 学习会话界面 | 已修订（拆分） | B | B | 原卡含统计、提醒与自建书且依赖 CORE-40（违反依赖方向）；改为学习会话界面：路由、StudyHomeVm/BookshelfVm/PlanSettingsVm/SessionVm（SessionScreen 由 UiCommand 驱动）、AnswerInputRegistry 扩展点（手写由 CORE-40 注册，依赖倒置）；错误码与界面行为表；验收补 R04.a/d/e/f/g/h 方括号标签 | — |
| CORE-40 | 识别流程编排、手写画布与图片预处理界面 | 已修订（拆分） | C | C | 原卡页面类只有空壳且无流程定义；改为 RecognitionFlow 流程控制器（sealed RecognitionStep，逐步对应 CORE-32 合法转换与 op 调用）、InkController/InkCanvas、CropEnhancePage、HandwritingAnswerInput（注册到 CORE-39 扩展点）、installRecognition；错误码与界面行为表；验收覆盖 R06/R31/R32/R33/R40/R26/R04.e/R03 | 缩略图资产（AssetKind::Thumbnail）的生成方未定义，暂由 Confirmed 图兼用 |
| CORE-41 | CI 门禁与可维护性度量 | 已修订 | C | C | 补检查脚本的命令行、输出格式与退出码、规则编号表；新增 check_unsafe（与 CORE-01 允许清单一致，修正原文“只允许 fml-ffi”）、check_sadd（就绪定义机检）、run_all；工作流只编排；规模声明主包与附属 | Dart 圈复杂度只能近似统计 |
| CORE-42 | 发布流水线、版本矩阵与回滚 | 已修订 | B | — | 补脚本命令行；新增 size_gate、scan_secrets、repro_check；可复现范围收窄为 Rust 核心库与资源包；回滚改为 roll-forward（两端不支持降级安装）；依赖补 CORE-13 | — |
| CORE-43 | 服务端部署、资源分发与监控 | 已修订 | B | — | 重写：部署清单文件逐个定义（Dockerfile/compose/config.example.toml/required_keys.txt+preflight.py/backup/restore/alerts.yaml/keys.md/tuf/refresh.sh）；新增 server/src/ops/ 指标与健康检查；指标与告警阈值表；依赖补 CORE-45；签名密钥保管落到 keys.md；部署地域与产品选型引 ADR-V5-18（待定）；发信计数改由 CORE-45 经 metrics 门面上报，避免 CORE-43→CORE-45 反向依赖 | 云厂商与对象存储产品待 ADR-V5-18（待定） 定案；发信与云识别供应商账号由甲方开通 |
| CORE-44 | 鸿蒙预留与 C 头文件消费者验证 | 已修订 | A | — | build.sh 参数与退出码；consumer.c 五步检查（去掉需要字体的 DisplayList 步骤，改为 engine.check 与未知 op 错误路径）；端口对应表覆盖 CORE-04 全部 12 个端口；CI 作业与依赖准入规则 | OpenHarmony SDK 版本与下载账号在 M0 办理；鸿蒙目标只编译不运行 |
| CORE-45 | 邮箱验证码与发信 | 已修订（新增卡） | B | B | 自 CORE-22 拆出：邮箱验证码生成/存储/限流、/v1/auth/email-codes、EmailSender 与阿里云/腾讯云/Fake 实现、主备切换；README §5 R24 与附录 A ADR-V5-11 同步 | 发信账号与域名由 CORE-43 部署注入 |
| CORE-46 | 同步与升级协调器 | 已修订（新增卡） | B | B | 自原 CORE-26 拆出 Dart 侧网络协调：SyncApi、SyncCoordinator、UpgradeCoordinator、KeyService；异常处理表；实现 CORE-36 定义的 SyncFacade/UpgradeFacade；SyncStatus 等类型移至 CORE-36 facades.dart，UpgradeCoordinator.run 改用门面类型；新增安装点 installSync | CORE-36 须定义 SyncFacade/UpgradeFacade；平台组装（AND/WIN composition）须注入实现 |
| CORE-47 | 设置页与账户安全界面 | 已修订（新增卡） | B | B | 设置页与账户安全界面（从 CORE-36 拆出）：设置子路由、同步状态、升级向导、恢复码一次性展示、设备管理、导出/恢复、keep_last；视图模型可单测 | — |
| CORE-48 | 计算器、代入与计算链界面 | 已修订（新增卡） | B | B | 由 CORE-38 拆出：计算器（6 步数值求根）、代入向导、计算链；附属 calculation_plan 表（归属自 CORE-14 移入）与 library.plan_* op；op 名按 CORE-10/11 实际契约；2026-10-19：代入结果保存按 CORE-14 新 library.create 请求填写 meta | — |
| CORE-49 | 学习统计、提醒设置与自建书界面 | 已修订（新增卡） | B | B | 由 CORE-39 拆出：统计页（自绘图表、热力图分档）、提醒设置（device.reminder_time）、自建书编辑器 | — |
| CORE-50 | 识别结果、云端确认与识别历史界面 | 已修订（新增卡） | B | B | 由 CORE-40 拆出：RecognizePage 与路由、CandidateVm（逐符号校正、经 CORE-38 新建页保存后 recog.adopt）、CloudConsentPage、UploadPreviewPage、HistoryVm；2026-10-19：候选页“复制 LaTeX”改为复制公式（FormulaCopyButton） | — |
| CORE-51 | 资源包下载、导入与管理界面 | 已修订（新增卡） | B | B | 从撤销的 AND-10、WIN-11 中抽出两端共用的资源包下载、断点续传、离线导入、更新检查与管理界面：PackService（offers/installed/checkUpdates/download/importFile/uninstall）、PackTaskState、PacksVm、installPacks；空间检查 PACK_STORAGE_LOW 与 PACK_DOWNLOAD_INCOMPLETE；调用 CORE-15 pack.install（带 expected_size/expected_blake3） | — |
| CORE-52 | 公式复制格式与富格式导出 | 已修订（新增卡，2026-10-19） | B | B | 按 Q12 确认新增：fml-export（MathML Core、SVG）、op export.formula、DefaultFormulaCopier（格式组合表、PNG 经 paintDisplayList、HTML 片段、16 项缓存、无写入器降级）、FormulaClipboardWriter 接缝、错误码 EXPORT_NOT_RENDERABLE / EXPORT_TOO_LARGE | 新错误码须先写入 contracts/errors/registry.yaml；Office 对 MathML 剪贴板格式的识别在 M0 验证（WIN-05） |
| CORE-53 | LaTeX 命令补全 | 已修订（新增卡，2026-10-19） | A | — | 按 Q16 确认新增：latex_commands.json（CORE-06 白名单子集）、contextAt/rankCandidates/applyCandidate 纯函数、补全弹层与按键（↑/↓、Tab/Enter、Esc，不占用 Ctrl+Space）、空位选中、独立撤销步、组合输入期间不弹出；经 CORE-37 LatexSourceAssist 接入 | — |
| CORE-54 | 公式库批量选择与批量操作 | 已修订（新增卡，2026-10-19） | B | B | 按 Q16 确认新增：SelectedIds/AllMatching 选择模型、键盘鼠标触控交互表、编辑标签对话框、移入回收站撤销；附属 library.batch（单事务、可取消回滚、≤ 10000 条）；新错误码 LIB_BATCH_TOO_LARGE、LIB_TAGS_LIMIT、LIB_BATCH_CANCELLED；经 CORE-38 LibraryListDecorator 接入 | 新错误码须先写入 registry.yaml |

## D.5 Android 端

| 编号 | 名称 | 历史改动结论 | 评审等级（2026-10-19） | 修订后等级（本轮） | 修改摘要 | 历史遗留（当前见D.10） |
| --- | --- | --- | --- | --- | --- | --- |
| AND-01 | 工程与构建 | 已修订 | B | — | 入口改为 runPlatformApp(CoreLibrarySpec)；ports_android 初始全 Fake、各卡逐行替换；platformInstallers 接缝；工具链锁定文件；仅 arm64；16 KB 对齐 | armeabi-v7a 是否开启待 AND-12 真机矩阵数据 |
| AND-02 | 权限与清单 | 已修订 | C | C | PermissionService 契约与通道；allowBackup=false；清单白名单检查脚本作为附属 | — |
| AND-03 | 相册、文件导入与导出 | 已修订 | C | C | 去掉对 AND-06、CORE-30 的依赖（LocalFileStore 经接口注入）；补 DocumentPicker；通道协议、HEIC→JPEG、20 MiB 规则、错误码；2026-10-19：新增 AndroidFormulaClipboard（text/plain、text/html、经 FileProvider 的 image/png），依赖加 CORE-52，规模约 500 | 接收方对剪贴板 content URI 的读取授权与图片粘贴支持在 M0 真机验证 |
| AND-04 | 相机 | 已修订 | B | — | 改为原生 CameraActivity；提示阈值；EXIF GPS 去除；依赖收敛为 CORE-04、AND-02 | 提示阈值需 AND-12 真机标定 |
| AND-05 | 生命周期、进程恢复与运行时信息 | 已修订 | B | B | 生命周期与运行时信息实现；trimMemory 映射；进程恢复验收移至 AND-12 | — |
| AND-06 | 本地存储、Keystore 与生物识别 | 已修订 | C | C | Keystore 包装格式、StoreArea 目录、别名、安全级别降级与异常映射 | — |
| AND-07 | 手写与编辑器的 Android 适配 | 已修订 | A | — | 删除不存在的 InkPointerAdapter/EditorActions；改为实现 CORE-37 EditorPlatformBindings 与 CORE-40 InkInputPolicy 接缝，经 platformInstallers 登记；去掉对 AND-05 依赖 | 手掌半径阈值需真机标定；V1 不做原生历史采样 |
| AND-08 | 本地通知与提醒自检 | 已修订 | B | — | NotificationScheduler 增加 taps()（CORE-04）；ReminderSelfCheck 接缝定义在 CORE-20、界面在 CORE-49；AlarmManager 非精确闹钟与重排规则；ROM 跳转表 | 应用多日未打开时正文沿用上次数量 |
| AND-09 | 网络传输 | 已修订 | B | — | 改为纯传输实现（dart:io HttpClient、系统代理、续传、取消、异常映射）；云识别前后台行为移至 CORE-34 | — |
| AND-10 | 资源包获取与识别历史平台存储 | 已撤销 | 未评审 | — | 资源包下载与管理并入 CORE-51，存储紧张清理并入 CORE-50；两端共用同一 Dart 实现，避免重复；编号不复用 | — |
| AND-11 | 打包、签名与发布 | 已修订 | B | — | 脚本参数、签名环境变量、检查项、符号归档、上架材料清单；build.gradle release 段为附属 | 应用备案号与软著登记号待甲方提供 |
| AND-12 | 性能、能耗与真机矩阵 | 已修订 | C | C | 测量项引用 CORE-01 预算表行名；脚本退出码；进程恢复与跨端一致性联测；依赖改为 AND-03/09 | 真机矩阵设备到位情况待确认 |

## D.6 Windows 端

| 编号 | 名称 | 历史改动结论 | 评审等级（2026-10-19） | 修订后等级（本轮） | 修改摘要 | 历史遗留（当前见D.10） |
| --- | --- | --- | --- | --- | --- | --- |
| WIN-01 | 工程与构建 | 已修订 | B | — | 入口改为 CORE-04 runPlatformApp + CoreLibrarySpec（ABI 校验与“核心不可用”页归 CORE-04）；明确 CMake/cargo 集成、通道注册约定（每卡一行，前缀 fml/windows/）、ports_windows 先 Fake 后逐行替换、+crt-static 与 /Brepro；验收加可复现与无 VC 运行库依赖 | — |
| WIN-02 | 安装器与卸载 | 已修订 | C | B | 安装器定为 Inno Setup 6（ADR-V5-12）；定义版本子目录与 current.txt/pending.txt 布局、ISCC 参数、AppMutex、/UPDATE=1 更新模式、降级拦截、空间检查、卸载窗体与清理范围；依赖由 WIN-07 改为 WIN-01（消除平台依赖方向违例） | AppId GUID 在 M0 生成 |
| WIN-03 | 自更新与启动器 | 已修订 | C | C | 原卡缺更新清单格式、校验与回滚机制：新增 update.json 格式、WindowsUpdater 状态机与签名者校验、退出时安装、固定路径启动器（首启 120 s 健康确认、数据库备份与回滚、保留 2 个版本）；启动器为附属构建单元（installer/windows/launcher） | 签名证书主体 CN（kExpectedPublisher）在 M0 登记 |
| WIN-04 | 文件导入、拖拽与导出 | 已修订 | B | — | 依赖去掉 CORE-30、WIN-07（LocalFileStore 注入）；新增 DocumentPicker 实现与 ImageDropSource 接缝实现；定义通道方法、超限与 HEIC（WIC）规则、文件夹一层扫描确认、导出 .fmlpart 原子改名 | HEIC 依赖用户安装 HEIF 扩展 |
| WIN-05 | 剪贴板与多格式复制 | 已修订 | B | — | 实现 CORE-04 ClipboardAdapter 与 CORE-52 FormulaClipboardWriter（2026-10-19 按 Q12 确认改写）：一次写入 MathML（三种格式名）、CF_HTML、image/svg+xml、PNG、CF_DIB、CF_UNICODETEXT、text/x-latex；粘贴图片读 PNG/CF_DIBV5/CF_DIB；修正错误码名为 PARSE_FORBIDDEN_COMMAND | Office 识别 MathML 剪贴板格式名的行为在 M0 用 Microsoft 365 验证；手动粘贴矩阵结果待记入 |
| WIN-06 | 窗口、DPI、生命周期与单实例 | 已修订 | B | B | 补全通道契约、paused/resumed 判定、低内存通知、关闭流程（closeRequested → 托盘或退出）、单实例与窗口位置规则；新增 WindowsPrefs、TrayPresence 接缝、WindowsShell.exitApp 与设置区；布局断点与深色模式归共享界面 | 关闭窗口默认退出、首次关闭不询问，按 README §6 Q15（待确认） |
| WIN-07 | 本地存储、DPAPI 与 Windows Hello | 已修订 | B | — | 定义 DPAPI 包装格式、.applock 的 Windows Hello 签名派生第二层、StoreArea 目录表、受保护 DACL、错误映射与“安全说明”设置区；依赖加 CORE-36 | — |
| WIN-08 | 编辑器快捷键、输入法与笔输入 | 已修订 | B | — | 改为经 CORE-36/37/40 接缝实现：编辑器与全局快捷键、笔输入策略；原卡引用的 EditorActions 不存在，已删除；2026-10-19 按 Q11 确认：默认键位改为贴近 Word 与 LaTeX 编辑器（上标 Ctrl+Shift+=、下标 Ctrl+=、插入公式 Alt+=、查找 Ctrl+F、重做 Ctrl+Shift+Z），新增 ShortcutCommand、KeyChord、Keymap、defaultKeymap、保留键规则与 KeymapHolder，只读帮助区移交 WIN-14，规模约 360 | Q16 确认后补全与批量操作由 CORE-53、CORE-54 在共享界面实现，本卡把其按键列为保留（Ctrl+T、Shift+F10 不可分配）；Flutter Windows 笔事件上报需 M0 验证；v5.2 修订见 D.7 |
| WIN-09 | 应用内提醒、托盘与开机自启 | 已修订 | B | B | 定义应用内定时规则（同日一次、时间变化与睡眠唤醒补发窗口 2 h）、托盘通道与菜单、通知点击、关闭到托盘与开机自启；不再使用 Toast COM 激活 | 应用完全退出时不提醒（设置区说明） |
| WIN-10 | 网络传输 | 已修订 | B | — | 改为纯传输实现（与 AND-09 同构，dart:io HttpClient、静态系统代理、续传、取消、异常映射）；云识别调用移至 CORE-34；移到 S2 | PAC 自动代理不支持 |
| WIN-11 | 资源包获取与识别历史平台存储 | 已撤销 | 未评审 | — | 资源包下载与管理并入 CORE-51，存储检查与历史清理并入 CORE-50、CORE-32；两端共用同一 Dart 实现；编号不复用 | — |
| WIN-12 | 代码签名与发布检查 | 已修订 | B | — | 定义 build_release.ps1 编排、sign.ps1（硬件令牌或云签名）、签名者核对、制品门禁、PDB 归档与 update.json 生成；MSIX 不采用（ADR-V5-12）；依赖加 WIN-03 | 签名证书与时间戳服务由甲方在 S7 前提供 |
| WIN-13 | 性能与环境矩阵 | 已修订 | C | C | 测量项按 CORE-01 预算表行名对应，预算值只在 CORE-01 维护；定义测试、脚本、环境矩阵与报告模板；tools/perf/windows 为附属 | — |
| WIN-14 | 快捷键自定义 | 已修订（新增卡，2026-10-19） | B | — | 按 Q11 确认新增：设置页“快捷键”区、录制对话框（录制期间暂停分发）、冲突检测与替换、保留键拒绝、单项与全部恢复默认、偏好 keymap.v1（只存与默认不同的命令） | — |

## D.7 v5.2 界面设计修订（2026-10-19）

- 范围：新增 CORE-55、AND-13、WIN-15，联动修订界面卡与平台卡；检查方法同 D.1，依赖方向规则改为“无环且依赖卡阶段不晚于本卡”（README §8.5 b、01 §1）。
- 历史批次结果：81张卡机械检查0项，新增/已修订仅是改动记录，未覆盖本次评审发现的语义阻塞。Q21～Q30当时按默认确认不表示全部卡已就绪；当前以D.10为准。
- 本表仅保存历史修订；当前结论以D.10为准（如 WIN-08 的全局导航键位已改为 Ctrl+1 学习、Ctrl+2 公式库、Ctrl+3 识别、Ctrl+4 设置）。

| 编号 | 名称 | 历史改动结论 | 评审等级（2026-10-19） | 修订后等级（本轮） | 修改摘要 | 历史遗留（当前见D.10） |
| --- | --- | --- | --- | --- | --- | --- |
| CORE-55 | 界面设计系统与主题 | 新增 | C | C | 设计原则 P1～P6（对应甲方要求 1～4 与 R42.a～f）；令牌与 ThemeExtension；5 套原创预设主题色浅/深色值与 WCAG AA 对比度表（脚本验证全部通过）；固定语义色；外观偏好 appearance.v1 按设备保存；InputModality 与密度；宽度分档、矮高度与设备尺寸表（含平板最短边 ≥ 600 dp、Windows 最小 600×500）；核心组件；关键页面分档布局；流畅性规则；无障碍；AND-13、WIN-15 需实现/登记的接缝清单；平台无关命令接缝 FmlCommandScope / FmlCommands 与可选 ShortcutLabelSource（ShortcutHint、AnswerOption 按命令 ID 显示键位） | 界面性能预算数值按 ADR-V5-25已采纳预算机制，数值由M0实测校准；产品取舍见 README §6 Q21–Q24、Q27（已按默认确认） |
| CORE-01 | 仓库骨架与工程约定 | 已修订 | B | B | 全局资源预算表新增界面性能 5 行（点击到可见反馈、作答到判定反馈、转场与动效、旋转与窗口尺寸变化、主题切换），口径不变（ADR-V5-25） | 历史待定已于本轮采纳V5-25预算机制，M0仍须真机校准（AND-12、WIN-13 已加测这 5 行） |
| CORE-36 | 应用壳、组装层、账户入口与导航 | 已修订 | C | C | 主题移交 CORE-55，只留接入；主导航顺序改为学习、公式库、识别、设置，落地 /study；installDesign 列为第一个安装点；mainCommon 先加载外观偏好；依赖加 CORE-55；新增 R42.a/e 验收 | 产品取舍见 README §6 Q21、Q26（已按默认确认） |
| CORE-37 | 公式渲染组件与编辑器 | 已修订 | C | C | 依赖加 CORE-55；控件密度、公式颜色取令牌；defaultEditorMode 为平台判断唯一例外（Q13）；新增 R42.d 验收 | — |
| CORE-38 | 公式库界面 | 已修订 | C | C | 依赖加 CORE-55；expanded 下 TwoPane 列表与详情并排；骨架屏；新增 R42.e 验收 | — |
| CORE-39 | 学习会话界面 | 已修订 | B | B | 依赖加 CORE-55；作答选项、判定条、单主按钮、触感接缝；新增 R42.a/b/c/e 验收；学习命令 ID 表 StudyCommands（study.primary、option1～4、rateKnew/rateForgot、skip、pause、appeal、prevQuestion/nextQuestion），各状态以 FmlCommandScope 声明，新增 R42.b 命令验收 | — |
| CORE-40 | 识别流程编排、手写画布与图片预处理界面 | 已修订 | C | C | 依赖加 CORE-55；画布放入输入区、深色墨迹、stylus 不滚动、长等待可取消；新增 R42.d 验收 | — |
| CORE-47 | 设置页与账户安全界面 | 已修订 | B | B | 依赖加 CORE-55；新增外观子页 /settings/appearance（AppearancePicker），设置首页第一组“外观”；新增 R42.f 验收 | — |
| CORE-48 | 计算器、代入与计算链界面 | 已修订 | B | B | 依赖加 CORE-55；/calc 无 revision 时为空状态并跳转 /library；新增 R42.e 验收 | — |
| CORE-49 | 学习统计、提醒设置与自建书界面 | 已修订 | B | B | 依赖加 CORE-55；掌握度四色与热力图五档改取 FmlSemanticColors；新增 R42.f 验收 | — |
| CORE-50 | 识别结果、云端确认与识别历史界面 | 已修订 | B | B | 依赖加 CORE-55；实现约束加视觉与交互遵守 CORE-55 与 expanded 布局 | — |
| CORE-51 | 资源包下载、导入与管理界面 | 已修订 | B | B | 依赖加 CORE-55；进度与失败提示改用 CORE-55 组件 | — |
| CORE-52 | 公式复制格式与富格式导出 | 已修订 | B | B | 依赖加 CORE-55；界面元素用 CORE-55 组件 | — |
| CORE-53 | LaTeX 命令补全 | 已修订 | A | — | 依赖加 CORE-55；弹层表面、阴影与行高取令牌 | — |
| CORE-54 | 公式库批量选择与批量操作 | 已修订 | B | B | 依赖加 CORE-55；长按增加可见“选择”按钮等价；撤销提示条用 showFmlToast；新增 R42.b 验收 | — |
| AND-13 | Android 触摸交互与横竖屏适配 | 新增 | B | B | 实现 CORE-55 接缝：InputModalitySource 恒 touch、UiFeedbackSink 触感（performHapticFeedback，应用内 haptics 开关与系统触摸振动设置同时为开才触发，同 kind 80 ms 节流，触感映射表含 API 26～29 降级）、MotionScaleSource（ANIMATOR_DURATION_SCALE 与变化监听）；不登记 DevicePrefStore（用默认 FileDevicePrefStore，位于 noBackupFilesDir 排除备份）；AndroidSystemBars 订阅 resolvedChanges 统一系统栏与 edge-to-edge；MainActivity 窗口属性表（不锁方向、resizeableActivity、configChanges 含 uiMode/fontScale、adjustResize、预测性返回）为唯一定义；启动主题、shortEdges 挖孔模式、内边距与软键盘表、系统返回对照表（均有可见按钮等价）、屏幕方向表；旋转与分屏不重建、清单外变化走 AND-05 恢复；依赖 CORE-01、02、04、36、55，AND-01、02、05，阶段 S2，约 380 行 | 横屏时输入法不进入全屏提取界面为外部前提（M0 核实）；产品取舍见 README §6 Q22、Q25～Q27（已按默认确认） |
| AND-02 | 权限与清单 | 已修订 | C | C | 范围加入 AND-13 窗口属性的写入与审计；清单固定项加窗口属性（不声明 screenOrientation、resizeableActivity=true、configChanges 与 AND-13 一致，CameraActivity 同样不锁方向）；审计脚本增加窗口属性违规检查；新增 R42.e 验收；规模 230 → 245 行 | — |
| AND-04 | 相机 | 已修订 | B | — | CameraActivity 由“竖屏锁定”改为跟随系统旋转（Q17）：旋转不重建不重绑相机，PreviewView 自动校正，OrientationEventListener 设 targetRotation（锁定竖屏横持拍摄仍正立，只写 EXIF 由 CORE-30 修正），快门竖屏在底部、横屏在右侧，触控目标 ≥ 48 dp；新增 R42.e 验收；规模 400 → 420 行 | — |
| AND-05 | 生命周期、进程恢复与运行时信息 | 已修订 | B | B | 系统栏、edge-to-edge 与启动主题移交 AND-13（原“由共享主题调用 setSystemUIOverlayStyle”删除）；configChanges 改为引用 AND-13 属性表；写明与 AND-13 的两条状态保持路径衔接；新增“不保留活动”重建回原路由的 R42.e 验收 | — |
| AND-07 | 手写与编辑器的 Android 适配 | 已修订 | A | — | TemplateBar 高 44 → 48 dp（CORE-55 触摸最小目标）；横屏软键盘下快捷栏表现；触控笔由 CORE-55 InputModalityScope 切换、画布不设手势排除区（引用 AND-13）；新增 R42.b、R42.e 验收 | — |
| AND-12 | 性能、能耗与真机矩阵 | 已修订 | C | C | 依赖加 AND-13；测量表新增 CORE-01 界面 5 行（点击到可见反馈、作答到判定反馈、转场与动效、旋转与窗口尺寸变化、主题切换）及对应测试文件；结果 JSON 加 orientation；真机矩阵要求至少一台手机与一台平板各测竖屏与横屏、一台挖孔屏、手势与三键导航；新增 R42.c、R42.e 验收；规模 420 → 490 行 | README §6 Q17 影响卡可补 AND-12 |
| WIN-15 | Windows 桌面交互与窗口适配 | 新增 | C | C | 实现 CORE-55 接缝：WindowsInputModalitySource（pointer；Windows 10 平板模式或二合一平板姿态 SM_CONVERTIBLESLATEMODE=0 时 touch，WM_SETTINGCHANGE 事件切换密度）、WindowsMotionScale（SPI_GETCLIENTAREAANIMATION）、WindowsDevicePrefStore（映射 WIN-06 WindowsPrefs，appearance.v1 含 haptics 原样保存）、WindowsShortcutLabels（ShortcutLabelSource）；不登记 UiFeedbackSink（外观页不显示触感开关）；全应用唯一 ShellKeyHandler WindowsKeyRouter（WIN-08 WindowsShellKeys 经 attach 挂入）；KeyChord 自 WIN-08 移入；学习流程键盘命令表 StudyCommand（ID 逐字等于 CORE-39 StudyCommands：Ctrl+Enter 主操作、1～4/A～D 选项、Y/N 自评、Ctrl+Shift+S/P/M 跳过/暂停/记错了、Ctrl+PageUp/PageDown 默写换题）及分发规则（焦点在文本框或输入法组合中不分发无修饰键、按住重复不触发）；WindowsTitleBar 跟随 resolvedChanges（DWMWA 19/20，Win11 底色与文字色，高对比度交还系统）；最小窗口 600×500 逻辑像素按 DPI 换算并受工作区约束；Windows 窗口尺寸与 CORE-55 分档对照表；焦点、悬停、右键菜单、滚轮与精确式触摸板、触屏、深浅色、高对比度、文本大小、DPI 对照验收表；原生 interaction_channel.cpp；依赖 CORE-01、02、04、36、55，WIN-01、06，阶段 S2，约 440 行 | 高对比度、文本大小、PointerPanZoom 与滚轮行数经 Flutter Windows 嵌入层上报为外部前提（M0 核实）；CORE-39 StudyCommands 与本卡 a 表 ID 逐字对应，由两卡各自的表测试保证（本卡在 S2，不依赖 S4 的 CORE-39） |
| WIN-06 | 窗口、DPI、生命周期与单实例 | 已修订 | B | B | “不包含”中布局断点、深色模式、高对比度与字体缩放改指 CORE-55，最小窗口、标题栏深浅色、输入方式与设备偏好接缝改指 WIN-15；设备级偏好列表加入外观 appearance.v1 | — |
| WIN-08 | 编辑器快捷键、输入法与笔输入 | 已修订 | B | — | KeyChord 定义移交 WIN-15（本卡引用）；WindowsShellKeys 不再登记为 ShellKeyHandler，改为挂入 WIN-15 WindowsKeyRouter；全局导航由 Ctrl+1～5（公式库/计算/学习/识别/设置）改为 Ctrl+1～4（学习/公式库/识别/设置，同 CORE-36 新导航顺序），删除 goCalc，Ctrl+5 默认不分配；依赖加 WIN-15；R19 验收改为 Ctrl+1→/study 等；规模 360 → 340 行 | — |
| WIN-14 | 快捷键自定义 | 已修订 | B | — | 依赖加 WIN-15；新增 BindableCommand（AppCommand / StudyKeyCommand）与 KeymapSet，学习命令并入 keymap.v1（持久化键为命令 ID，如 study.pause）；设置区分“编辑器”“全局”“学习”三组；规则 ② 增加 unmodifiedAllowed 学习命令可用无修饰字母与数字的例外；录制时同时暂停 KeymapHolder 与 WindowsKeyRouter；新增学习键位冲突与持久化 R42.b 验收，录制期按 Ctrl+1 不导航；规模 300 → 340 行 | — |
| WIN-13 | 性能与环境矩阵 | 已修订 | C | C | 依赖加 WIN-15；测量表新增 CORE-01 界面 5 行（点击到可见反馈、作答到判定反馈、转场与动效、旋转与窗口尺寸变化、主题切换）；列表滚动与窗口尺寸变化覆盖 DPI 100%～200%（含 125%、175%）与跨显示器；环境矩阵加二合一平板姿态切换与系统对比度主题冒烟；新增 R42.c、R42.e、R42.f 验收；规模 400 → 430 行 | — |

## D.8 v5.2.1 Windows 外接数位板补充（2026-10-19）

- 起因：甲方询问 Windows 端是否规划接入数位板；原稿只覆盖二合一设备的屏上笔，未写驱动模式前提，测试矩阵无外接数位板，且 WIN-08（侧键 = 擦除）与 WIN-15（触控笔按钮 = 右键菜单）对笔侧键的规定不一致。
- 支持方式列为 README §6 Q31，正文按暂行默认值撰写：只支持 Windows Ink，不接入 WinTab；甲方同日确认按默认。

| 编号 | 名称 | 历史改动结论 | 评审等级（2026-10-19） | 修订后等级（本轮） | 修改摘要 | 历史遗留（当前见D.10） |
| --- | --- | --- | --- | --- | --- | --- |
| WIN-08 | 编辑器快捷键、输入法与笔输入 | 已修订 | B | — | 目标与范围加入外接数位板；统一笔侧键规则（书写区内按住侧键落笔为擦除，书写区外点按为右键菜单，笔长按不模拟右键）；修正 isEraser：Flutter 中第一侧键为 kPrimaryStylusButton，原稿只判 kSecondaryStylusButton；新增 PenDevice、PenStatus、WindowsPenStatus 与通道 fml/windows/pen（GetPointerDevices 枚举、Wintab32.dll 存在检测、WM_POINTERDEVICECHANGE）；关闭系统长按右键与笔势；设置区“笔与数位板”（order 65）显示设备与开启 Windows Ink 提示；新增 1 条 Widget 测试与 2 条数位板手动验收；规模 340 → 460 行 | 书写区外侧键点按能否上报为次键点击须 M0 核实，不满足时经“更多”按钮打开菜单；手写页内不主动弹出开启提示（需 CORE-40 新增接缝，本次未做），提示只在设置区 |
| WIN-15 | Windows 桌面交互与窗口适配 | 已修订 | C | C | d 表“右键菜单”改为笔侧键点按（书写区外）并引用 WIN-08 侧键规则；新增“触控笔与数位板”行；新增外接数位板输入方式切换手动验收 | — |
| WIN-13 | 性能与环境矩阵 | 已修订 | C | C | 环境矩阵加外接数位板（Windows Ink 开与关各一轮，含双显示器映射）；新增 [R06] 验收：数位板上测“手写墨迹上屏”并勾选 WIN-08 数位板手动项 | — |

## D.9 v5.3～v5.3.2 评审意见处理记录

处理状态描述本轮意见，不代表整卡就绪；逐卡当前结论见 §D.10。

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| U-F07 | 阻断 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | ADR-V5-15；README §8.3 | 采纳锁定机制，S0 开工当天核实兼容稳定版 |
| U-F08 | 高 | 已修订 | 附录 A §A.4.2/4；README §8.3 | 区分已采纳与 Fake 可先行、真实交付门槛 |
| B-F-04 | 阻断 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-22；ADR-V5-14 | Casdoor 唯一凭据与令牌所有者，注册不再返回授权码 |
| B-F-13 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-22、25 | 拆分客户端重登与服务端近期认证；定义 auth_time |
| U-F15 | 阻断 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-35；附录 C §C.5.1 | Fake 编码验收，真实模型保留 M-MODEL 交付门槛 |
| A-1 | 阻断 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-56；01 §2 | S1 内置数据与上下文，S4 仅补充 |
| A-2 | 阻断 | 已修订 | CORE-05、09、10、56；AGENTS | 常数纯数据下沉，FFI 编排保留严格领域依赖 |
| B-F-11 | 高 | 已修订 | CORE-28；01 §2 | 整体前移 S2，GuardContext 延迟注入消除账户反向依赖 |
| B-F-12 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-15、36、46 | 后续功能自登记钩子 |
| C-F-05 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-55；36/38/39/47/48 | 设计卡 gallery 验收，页面断言落对应卡 |
| AN-F02 | 高 | 已修订 | AND-02、05、13 | 窗口表归 AND-02，计数归 AND-05 |
| U-F01 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 部分修订（材料生成器转P1）（见 §D.11） | README §8.1；AGENTS | 材料补正文相关契约，编译依赖仍须声明 |
| U-F03 | 高 | 已修订 | README §8.1；AGENTS | 按 §6 影响模块卡机械附行 |
| A-3 | 高 | 已修订 | CORE-02 | 登记 AST_/CONTENT_ 命名空间 |
| A-4 | 高 | 已修订 | CORE-05 | 穷举全部变体、规范化规则与黄金 JSON |
| A-5 | 高 | 已修订 | CORE-14；Q32 | Validation/Severity/Filter 分离，逐状态映射 |
| A-6 | 高 | 已修订 | CORE-08；ADR-V5-27 | i128 与十进制字符串 DTO；eV/N_A/u 向量 |
| B-F-01 | 阻断 | 已修订 | CORE-21、25 | CBOR 键表、严格解码、格式向量，服务端只存不透明 base64 |
| B-F-10 | 高 | 已修订 | CORE-33、34、40 | Rust 定义 RecognitionMode；HTTP 值唯一 |
| B-F-02 | 阻断 | 已修订 | CORE-24、23 | 档案库事务真值 + journal补写设备注册表 |
| B-F-03 | 阻断 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-13、14、17、19、26 | 单事务统一分配Lamport与outbox，合并不回声 |
| B-F-08 | 高 | 已修订 | CORE-20 | 移除全局事件序，变更代数失效后全量重算 |
| B-F-09 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-21、32 | 平台槽位保存历史密钥，SessionKey独立随机并seal |
| A-7 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-14、56 | UnitRepo与持久化/加载/刷新时序 |
| A-9 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（方案调整）（见 §D.11） | CORE-13、15、56 | 全设备包库、安全高水位与无账户离线来源 |
| A-10 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-14、15、16 | 构建schema与只读可重建投影责任 |
| A-11 | 高 | 已修订 | CORE-14 | trigram能力探针，短查询LIKE与中文子串向量 |
| A-8 | 高 | 已修订 | CORE-17 | 显式now_ms/StudyDay，due_queue不再收plan_id |
| A-12 | 高 | 已修订 | CORE-18、06 | 单侧域失败给反例、固定负点、矩阵边界纠正 |
| A-13 | 高 | 已修订 | CORE-17；ADR-V5-29 | 核实fsrs6.6.2；Burn仅开发依赖的怀疑不采纳，补项目状态机与独立期望来源 |
| B-F-05 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（Q33 向量转P1）（见 §D.11） | CORE-19；Q33 | 来源排序配额及固定向量 |
| B-F-06 | 高 | 已修订 | CORE-19 | RecentStats由调用层查询并注入step |
| B-F-07 | 高 | 已修订 | CORE-20 | StatsInput补书卡时间与学习日，缓存全量重算 |
| U-F12 | 高 | 已修订 | CORE-16、19；README §5 | 干扰项审校来源与可复现出题验收 |
| C-F-01 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-01、37～55、41；AGENTS | Widget与用例路径/绑定分离，DEP-5覆盖 |
| C-F-02 | 高 | 已修订 | CORE-01、28、41；AND-09/WIN-10 | 网络构造白名单单一来源，仅平台net目录 |
| C-F-03 | 高 | 已修订 | CORE-55 | 显式FmlTokens/FmlTheme、of签名与缺省错误 |
| U-F20 | 高 | 已覆盖 | CORE-55 | 与C-F-03同一缺口，一并补类型/用法/验收 |
| W-1 | 阻断 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-04/36、WIN-03/16 | 首帧路由就绪后独立健康确认，早于解锁/同步，nonce 防旧标记。 |
| W-2 | 阻断 | 已修订 | WIN-02/03/16、阶段与索引 | 启动器拆为 WIN-16 S7，安装器单向消费，独立构建。 |
| W-3 | 阻断 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | WIN-13、ADR-V5-31 | Profile 集成驱动，Release 外部冒烟/采样；禁 GPU 走系统矩阵，删除无依据环境变量。 |
| W-4 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | WIN-06/16 | Launcher mutex、并发仅激活、转发退出码10不触发回滚。 |
| W-5 | 高 | 已修订 | WIN-02/03/16 | 启动器 armed 后等进程句柄退出再运行 Inno，30 s 超时保留 C。 |
| W-6 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | WIN-16 | 原子单文件与 journal、终止后等待、rename 重试、恢复失败救援。原建议直接启动旧版仅在原库恢复核验后采纳。 |
| W-9 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | CORE-36、WIN-06/09 | 托盘 firstFrameHooks 先于解锁，失败显示窗口；最小化不影响健康。 |
| U-F09 | 高 | 已修订；v5.3 复核：部分解决 → v5.3.1 已修订（见 §D.11） | 附录D §D.1/2/4～10；README §8.5 | 历史修订不再等于语义就绪；逐行提取81卡原评审等级，加新2卡当前汇总，C卡标未就绪、其他未完整复核不授予就绪。 |

本轮46条：已修订45、已覆盖1（U-F20与C-F-03同项）；部分修订/不采纳/转P1均为0。2026-10-20 的 v5.3 复核认定其中21条只部分解决（结论列已标注），v5.3.1 已逐条处理，处理记录见 §D.11。这里统计的是P0意见落点，不表示原报告其余P1问题也已修完；A-13中“Burn必然拖大发行包”的推测核实后未采纳，该条其余状态机缺口已修。

| 任务组 | 已修订 | 已覆盖 | 本地提交 |
| --- | --- | --- | --- |
| G0 决策与门槛 | 5 | 0 | 8459cc3 |
| G1 阶段与依赖 | 8 | 0 | 8c535b7 |
| G2 共享格式 | 6 | 0 | bde96e7 |
| G3 持久化与同步 | 8 | 0 | c230f4a |
| G4 算法输入与参照 | 7 | 0 | 0c9fe96 |
| G5 Dart与设计系统 | 3 | 1 | 8c8727f |
| G6 Windows启动链 | 7 | 0 | da070f6 |
| G7 当前就绪纠正 | 1 | 0 | 7f2d727 |

### D.9.P1 本轮P1及继承/独立复核处理

原123条每项一行；H1～H7与继承、新发现另行登记。状态表示文档修订程度，真实交付与整卡就绪另见D.10～13。

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| U-F02 | 高 | 部分修订 | CORE-57；README §8.1 | 入库生成器；间接契约符号闭合、直接契约完整保留，超量无损分段并记录。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| H1/继承 U-F01、core-ui:N12 | 高 | 已修订 | CORE-41、CORE-57 | 定义 warning 与 error 边界；保留未知符号人工复核，不声称启发式等于语义通过。 |
| B-F-14 | 高 | 已覆盖（v5.3.1） | CORE-22、CORE-25、CORE-45 | 核实 AUTH_RATE_LIMITED 仅 CORE-22 定义，其他卡复用；本轮统一其余表格。 |
| B-F-15 | 中 | 已覆盖（v5.3.1） | CORE-02、CORE-23、CORE-29、CORE-34、CORE-50 | 消费者引用所有者，未重复声明 severity/retryable。 |
| B-F-16 | 中 | 已修订 | CORE-19、CORE-20、CORE-21、CORE-25、CORE-39、CORE-45、CORE-49 | 行内清单改标准定义表；界面错误处理表改三列引用表，HTTP 表补级别。 |
| H2/继承 fix-core-b 错误表遗留 | 中 | 已修订 | CORE-02、CORE-41 | 明确首定义、消费者表及注册表未创建时的门禁边界。 |
| C-F-04 | 高 | 已修订 | CORE-55、CORE-58 | 拆组件、命令、外观入口与预热；原卡保留主题/布局规范，S2 外观路由可达。 |
| C-F-06 | 高 | 已修订 | CORE-37、CORE-59 | 只读渲染/worker 与编辑输入分开，原编辑行为/验收随职责迁移。 |
| C-F-07 | 高 | 已修订 | CORE-38、CORE-60、CORE-61、CORE-48 | 导入单位界面与 Rust 草稿各单独卡；单位页断言改核心查询，下拉归计算页。 |
| B-F-28 | 中 | 部分修订 | CORE-22、CORE-23、CORE-26、CORE-36、CORE-62、CORE-63、CORE-65、CORE-66 | 服务端/客户端、档案/账户控制器、壳/账户表单、合并/快照轮换分开。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| H3/继承 CORE-40 规模 | 高 | 已修订 | CORE-40、CORE-64 | 墨迹采集控制器/画布与识别编排拆开，均保持 S5。 |
| AN-F01 | 高 | 部分修订 | AND-02 | 白名单补通知/网络/生物识别与 AndroidX 动态接收器权限；按阶段审计启用项。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| AN-F03 | 高 | 部分修订 | AND-06；ADR-V5-36 | 26–29 非加密认证+时效密钥；30+组合保留 M0 探针，KeyProperties 与认证器常量分清。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| AN-F04 | 高 | 已修订 | CORE-04、AND-03 | 批次结束为下次选择开始或 expiresAt；调用方接管字节再结束，清理幂等。 |
| AN-F05 | 高 | 已修订 | AND-12 | 性能 release 与采样数量统一引用 CORE-01。 |
| AN-F06 | 高 | 已修订 | CORE-04、AND-01 | 正式 Unsupported 桩位于 lib，test Fake 不进发布组装。 |
| H4/平台内联与共享文件 | 高 | 已修订 | AND-01；CORE-04；两平台内联 | 逐字同步完整接口注释，MainActivity 模块化，清单归 AND-02。 |
| W-7 | 高 | 已修订 | CORE-36、WIN-08/15 | 采用 FocusManager early handler，清理根 Focus 前提，定义文本焦点判定。 |
| W-8 | 高 | 已修订 | WIN-01 | 集中平台线程队列、消息委托、子视图及退出协议。 |
| W-10 | 高 | 已修订 | WIN-08 | 补注册、子视图属性与可移除子类化；设备行为需 M0。 |
| W-11 | 高 | 已修订 | WIN-01/12 | Release PDB编译链接、Rust debug与符号缺失失败。 |
| W-12 | 高 | 已修订 | WIN-03/12 | 固定证书指纹与桥接轮换，供应方PE按来源哈希/签名校验，禁止重签。 |
| H6 | 系统性 | 部分修订 | CORE-02/03/07/13/67 | 统一信封/回调/句柄/生成策略，补07/13字段；全量业务schema（typed AST/复合op）尚未实体化，不能宣称逐op闭合，独立复核继续列缺项。 |
| H7 | 系统性 | 已修订 | CORE-41、CORE-37/55/58、AND-12、WIN-13 | 定义逐验收环境清单、pending/发布门禁；固定主机黄金图，设备生命周期与性能归平台主机作业。框架实现随原阶段交付，不把规范当运行结果。 |
| A-14 | 中 | 已修订 | CORE-02 | args改BTreeMap/domain改String，往返语义与规范字节比较分开。 |
| A-15 | 中 | 已修订 | CORE-03 | NativeCallable.listener与排空释放时序。 |
| A-16 | 中 | 已修订 | CORE-03 | 成功/业务错误/FFI错误共用排他信封。 |
| A-17 | 中 | 部分修订 | CORE-03/13 | store.open产生handle，free返回状态且allocation_id防ABA。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| A-18 | 中 | 已修订 | CORE-03 | C头文件include与C++ linkage守卫。 |
| A-19 | 中 | 部分修订 | CORE-07/56/67 | 补字段表与快照查找；复杂共享类型schema尚未实体化，见H6。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| A-20 | 中 | 部分修订 | CORE-09/56 | 明确CheckResult和单位快照；具体完整schema/真实向量仍需复核，不以散文闭合。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| A-21 | 中 | 已覆盖（v5.3.1） | CORE-05/16 | 哈希只依赖规范AST；内容去重的附加元数据另比较。 |
| A-22 | 中 | 已覆盖（v5.3.1） | CORE-06 | 32×32通过，33×32及65×1拒绝；无64×64通过保证。 |
| A-23 | 中 | 已修订 | CORE-13 | 一次升级全部迁移一个事务。 |
| A-24 | 中 | 部分修订 | CORE-03/13 | 补store DTO/mode/handle、敏感字段与副本安全边界。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| A-25 | 中 | 已修订 | CORE-12 | 字体索引已修；补整体Err携NodePath，不返回部分布局。 |
| A-26 | 中 | 已修订 | CORE-11 | substitute/run_plan补单位与取消参数。 |
| A-27 | 中 | 已覆盖（v5.3.1） | CORE-05 | NS_PACK与拼接字节、pack_item_id唯一定义。 |
| A-28 | 中 | 已覆盖（v5.3.1） | CORE-05/14/17 | requirement_level持久化和缺省Q35、card_id规则已存在。 |
| A-29 | 中 | 已覆盖（v5.3.1） | CORE-17 | duplicate只在重放派生，不更新事件。 |
| A-30 | 中 | 已修订 | CORE-18 | 按期望环境/方案绑定，补profile参数、choice示例及parse失败Result语义。 |
| A-31 | 中 | 已修订 | CORE-04/28 | 底层只传输，守卫唯一策略，Fake未准备请求用StateError。 |
| A-32 | 中 | 部分修订 | CORE-15 | tough时钟/datastore适配待官方源码与M0fixture验证，明确在线更新阻断，禁止冒充纯函数已闭合。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| B-F-17 | 中 | 部分修订 | CORE-65 | 邮件契约依赖45已在闭包；补Dart AccountState及wire映射。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| B-F-18 | 中 | 已修订 | CORE-23/24 | 明确交互单库与升级专用双库，源只读目标单写者。 |
| B-F-19 | 中 | 已修订 | CORE-24/26/66 | Store API归fml-store，fml-sync只纯合并，修正路径/规模/索引。 |
| B-F-20 | 中 | 部分修订 | CORE-24/67 | op表已有，StepInput/KeyOutput明确；全量schema仍随H6未闭合。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| B-F-21 | 中 | 已修订 | CORE-25/26/68 | 新增共享proto卡，端/服务同一Rust结构和向量。 |
| B-F-22 | 中 | 已覆盖（v5.3.1） | CORE-05/26 | NS_MERGE、UUID网络字节排序/拼接已定义。 |
| B-F-23 | 中 | 已覆盖（v5.3.1） | CORE-21/24/25/46 | 线上名两种与CBOR record_base64已统一。 |
| B-F-24 | 中 | 已修订 | CORE-46 | 推送删除多余幂等头，保留op_id服务端幂等。 |
| B-F-25 | 中 | 已修订 | CORE-46 | restoreOnNewDevice统一KeySecretInput。 |
| B-F-26 | 中 | 已覆盖（v5.3.1） | CORE-21 | wrap_with_params接kdf/salt，随机盐和默认参数已有。 |
| B-F-27 | 中 | 已修订 | CORE-62 | NetEvent与events流、重登/426订阅语义。 |
| B-F-29 | 中 | 部分修订 | CORE-31 | Result签名、显式symbols、final_check形状，固定submit。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| B-F-30 | 中 | 已修订 | CORE-05/14/32 | Page下沉纯数据；pending_cloud字段表。 |
| B-F-31 | 中 | 已修订 | CORE-33 | 预占/结算/退还/未知跨日对账，预算缺省关闭、配额CAS与输出过滤。 |
| B-F-32 | 中 | 已修订 | CORE-19 | 内容依赖16与QuestionSource映射，派生来源14。 |
| B-F-33 | 中 | 已覆盖（v5.3.1） | CORE-05/19 | question_seed完整字节规则已有，消费者只调用。 |
| B-F-34 | 中 | 已修订 | CORE-19 | BookSummary/BookDraft，create不收id。 |
| B-F-35 | 中 | 已修订 | CORE-20/23 | 提醒键与重排输入；calibration口径/op/边界验收。 |
| B-F-36 | 中 | 部分修订 | CORE-30、README Q38 | 旋转算法/阈值明确；自动透视范围调整待产品确认。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| C-F-08 | 中 | 已修订 | CORE-01/41/55 | 共用平台符号表，无defaultEditorMode例外；DEP5/6保持。 |
| C-F-09 | 中 | 已修订 | CORE-28及消费者 | 28已S2，补AppLog各调用者依赖。 |
| C-F-10 | 中 | 已修订 | CORE-51 | NetworkGuard/AppLog依赖闭合，阶段S2≤S4。 |
| C-F-11 | 中 | 已修订 | CORE-48/46 | S3验outbox，S6验跨设备。 |
| C-F-12 | 中 | 已修订 | CORE-43/45 | 邮件配置/告警/演练归45，43只运维通用能力。 |
| C-F-13 | 中 | 已修订 | CORE-04/47、AND-13、WIN-15 | 可选ScreenSecurity接缝与生命周期，无能力猜测。 |
| C-F-14 | 中 | 已修订 | CORE-27/47 | 备份导出写文件前Rust校验口令，界面处理弱口令码。 |
| C-F-15 | 中 | 已修订 | CORE-54/58、AND-13、WIN-15 | 语义命令与实体键位分离。 |
| C-F-16 | 中 | 已修订 | CORE-37/52 | paintDisplayList归非ui render目录。 |
| C-F-17 | 中 | 部分修订 | CORE-03/37/67 | 统一生成目录/所有者；全量schema尚未实体化。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| C-F-18 | 中 | 部分修订 | CORE-48/51/61 | 补草稿/计划响应字段，复杂schema仍需H6补齐。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| C-F-19 | 中 | 已修订 | CORE-41/58、AND-12、WIN-13 | H7固定主机黄金图，真机布局对照另验。 |
| C-F-20 | 中 | 已修订 | CORE-42 | build/revision显式公式与边界、递增及示例。 |
| C-F-21 | 中 | 已修订 | CORE-14/54 | 标签唯一约束与错误码归14，批量复用。 |
| C-F-22 | 中 | 已修订 | CORE-43、D.10 | 本地替身验收；真实云部署为外部前提阻断。 |
| C-F-23 | 中 | 已修订 | CORE-41 | H7明确S0作业定义/后期目标SKIP与发布禁止pending。 |
| AN-F07 | 中 | 已覆盖（本轮H4） | AND-06 | 取消新增指纹必使时效/设备凭据密钥失效的错误保证。 |
| AN-F08 | 中 | 已修订 | AND-05 | 排除UI_HIDDEN，API34回调前提明确。 |
| AN-F09 | 中 | 部分修订 | AND-12 | 主机驱动kill/旋转与进程内断言分工，框架P2。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| AN-F10 | 中 | 部分修订 | AND-01 | AndroidChannelModule逐卡扩展与统一生命周期转发。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| AN-F11 | 中 | 已修订 | 02 §4 | 删除WorkManager矛盾。 |
| AN-F12 | 中 | 已覆盖（本轮H4） | AND-08 | NotificationScheduler完整语义注释已同步。 |
| AN-F13 | 中 | 已修订 | AND-08 | 不可变PendingIntent、singleTop/onNewIntent与tap去重。 |
| AN-F14 | 中 | 不采纳 | AND-08 | 未经核实OEM私有组件不当契约；公共应用详情兜底，ROM实测后才引入候选表。 |
| AN-F15 | 中 | 已修订 | AND-08 | detail字段及标题/说明映射，无法检测不伪称错误。 |
| AN-F16 | 中 | 已修订 | AND-09 | CORE-28已S2且本轮补显式依赖。 |
| AN-F17 | 中 | 已修订 | AND-09 | SecurityContext测试注入，Release运行时拒绝、禁badCertificateCallback。 |
| AN-F18 | 中 | 部分修订 | AND-03 | 单选/多选分支与系统上限返回后校验。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| AN-F19 | 中 | 部分修订 | AND-12 | 选adb主机uiautomator dump，非进程内假接口。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| AN-F20 | 中 | 已修订 | AND-03/14 | 独立剪贴板/FileProvider卡并同步安装点。 |
| AN-F21 | 中 | 已修订 | AND-04/CORE-30 | 统一Laplacian单位/初值100，平台标定。 |
| AN-F22 | 中 | 已修订 | AND-04 | 私有pending文件/原子ready与重建恢复/过期清理。 |
| AN-F23 | 中 | 已修订 | AND-13 | 移除Activity补EditorInfo假设，外部前提失败走ADR。 |
| AN-F24 | 中 | 已修订 | AND-12 | 100图系统路径主机夹具；Fake只诊断，不伪造端到端。 |
| AN-F25 | 中 | 已修订 | AND-12/13 | S2替身页面，S7业务跨阶段真机统一执行。 |
| AN-F26 | 中 | 部分修订 | AND-01、ADR-V5-15 | Kotlin DSL与锁文件分工已明确；SDK/AGP/NDK等具体兼容版本尚未实测锁定，S0外部前提阻断。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| AN-F27 | 中 | 已修订 | CORE-03、AND-01 | 独立test-only ABI bump机制，发布拒绝。 |
| W-13 | 中 | 已修订 | WIN-06 | 窗口未创建重试10×100ms，超时退出10不打开第二库。 |
| W-14 | 中 | 已修订 | WIN-15 | 先判触点；Win11不读TabletMode；官方指标已核实。 |
| W-15 | 中 | 已覆盖（本轮H5） | CORE-58/WIN-15 | StudyCommand唯一定义58。 |
| W-16 | 中 | 已覆盖（本轮M-C） | WIN-08/14/15 | AppLog显式依赖28，28在S2。 |
| W-17 | 中 | 已修订 | WIN-01/16 | 测试define由main_windows读取，nonce首启compose前exit3，正式发布拒绝。 |
| W-18 | 中 | 已修订 | WIN-03/CORE-28 | 补依赖，updateCheck含用户触发下载，沿用显式下载计量网络策略。 |
| W-19 | 中 | 部分修订 | WIN-04 | 所有WIC解码步骤失败统一unsupported；扩展组合真实设备为M0。 |
| W-20 | 中 | 已修订 | CORE-50/WIN-04 | 共享确认回调在复制前执行；编译期注入且正式发布拒绝。 |
| W-21 | 中 | 已修订 | WIN-01/06/09 | ports构造唯一prefs并闭包传安装点。 |
| W-22 | 中 | 已修订 | WIN-06/09 | 正式destroy接缝、800ms总退出预算，TaskbarCreated重建/失败显示窗口。 |
| W-23 | 中 | 已修订 | CORE-04/WIN-10/AND-09 | lifecycle注入、自包含步骤、identity与ContentRange验证、测试CA隔离，守卫唯一策略。 |
| W-24 | 中 | 已覆盖（v5.3.1） | WIN-01/ADR-V5-12/15 | Rust/Flutter单源，Windows锁含inno；已采纳状态保持。 |
| W-25 | 中 | 已修订 | WIN-01 | 完整最终顺序及阶段启用、端口构造/安装点分工。 |
| W-26 | 中 | 已修订 | WIN-14/15 | 规范修饰顺序/11位小写hex与值相等。 |
| W-27 | 中 | 部分修订 | WIN-07/ADR-V5-37 | 不采未经证实的IKeyCredentialManagerInterop；Hello签名稳定KDF移除，M0/ADR闭合前.applock阻断，不降安全。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| W-28 | 中 | 已修订 | WIN-13/D10 | 按实际闭包覆盖02/03/06/07，补14并消除旧矛盾。 |
| W-29 | 中 | 已修订 | WIN-06/13 | S2用Fake，学习恢复联测归S7。 |
| W-30 | 中 | 已修订 | WIN-06/09 | 窗口控件/偏好默认/Placement行为唯一归属。 |
| U-F04 | 中 | 已覆盖（本轮H1） | README8.1/CORE-57 | 需求、Q、ADR及补充全文进入材料。 |
| U-F05 | 中 | 已修订 | README8.1/8.6 | 删除反向依赖必需契约矛盾；消费片段可显式追加。 |
| U-F06 | 中 | 已覆盖（v5.3.1） | README8.2 | run_all与标题模块编号模板已一致。 |
| U-F10 | 中 | 已修订 | D1/D2/tools/sadd/stats.mjs | 当前96卡由工具生成，历史83保留。 |
| U-F13 | 中 | 部分修订 | CORE-16/C8/Q40 | 工具用夹具验行为；真实四包覆盖/审校归M-CONTENT并列冻结前提。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| U-F14 | 中 | 已修订 | README5/8、CORE-41、AND-12/WIN-13 | 验证方式列/环境矩阵与责任分工，未运行pending。 |
| U-F16 | 中 | 已覆盖（v5.3.1） | CORE-01 | 共享UI不得平台判断已在权威规则。 |
| U-F17 | 中 | 已覆盖（v5.3.1） | CORE-01/AND-01/WIN-01 | Flutter只app/.flutter-version、Rust只rust-toolchain.toml。 |
| U-F21 | 中 | 已覆盖（本轮H3） | CORE-58 | S2独立外观入口，S6设置只链接。 |
| U-F22 | 中 | 已修订 | README8.4/CORE-02 | 共享文件单写，逐code owner登记，安装点各自文件/聚合由lead。 |
| U-F23 | 中 | 已修订 | README8.4 | 变更单→owner/ADR→消费者→重生成材料→D复检→关闭回流。 |
| U-F24 | 中 | 部分修订 | Q39/C8 | 发布许可证产品决策待确认；数据许可未获书面证据，分配角色与截止，不伪称完成。；独立复核后仍有P2/锁版/真实交付门槛，见D.13。 |
| 继承/core-b:N-03（payload 只有一个 lamport） | 中 | 已覆盖（v5.3.1） | CORE-26 | 纠正旧转交记录：CORE-26负载键5早已逐字段clocks，另有core-b已修订行。 |
| 继承/core-b:B-F-05 残留（Q33） | — | 转P2 | README §6 Q33 | 等待Q33产品确认后更新SELECT向量，不能自行改变暂行默认。 |
| 继承/core-b:错误码行内清单（CORE-19/20/21/45） | 低 | 已修订 | CORE-19、20、21 | 本轮按相应H/M组处理，仍须独立复核；不据此提升卡等级。 |
| 继承/core-c:VC-N06 / C-F-05② | 低 | 已修订 | CORE-36 | 本轮按相应H/M组处理，仍须独立复核；不据此提升卡等级。 |
| 继承/core-ui:N6 | 中 | 已修订 | 01 CORE-16 formula_items（distractors 元素 schema、reviewed_at 格式与毫秒换算） | 本轮按相应H/M组处理，仍须独立复核；不据此提升卡等级。 |
| 继承/core-ui:N8（卡内引用 ADR） | 低 | 已修订 | 01 CORE-56 目标引用 ADR-V5-26 | 本轮按相应H/M组处理，仍须独立复核；不据此提升卡等级。 |
| 继承/core-ui:N7 | 中 | 部分修订 | CORE-35；附录C（lead） | M-MODEL有负责角色/期限，实名及真实许可/模型未交付，保持外部门槛。 |
| 继承/core-ui/附录D:CORE-55 单卡规模超限 | 中 | 已修订 | CORE-55 f、规模；01 §3 索引 | 本轮按相应H/M组处理，仍须独立复核；不据此提升卡等级。 |
| 继承/core-ui:WIN-16 会话材料约 120k | 中 | 部分修订 | — | 已入库生成器及无损分段，但总量超8万仍需逐卡登记和全段阅读。 |
| 继承/core-ui:U-F01 残留（闭包外引用） | 高 | 部分修订 | README §8.1 第3、6项；附录D §D.12 | 已入库生成器及无损分段，但总量超8万仍需逐卡登记和全段阅读。 |
| 继承/core-ui:N12 | 高 | 部分修订 | README §8.1 第6项；附录D §D.10.1 | 已入库生成器及无损分段，但总量超8万仍需逐卡登记和全段阅读。 |
| 继承/P0 U-F01 | 高 | 部分修订 | CORE-57/README8.1 | 材料生成器已做；总量仍超8万，D列全量分段处理，不声称体量已达标。 |
| 继承/P0 B-F-05 Q33 | 高 | 转P2 | CORE-19/README Q33 | 按0A.3保留现行默认；待产品确认再改SELECT向量。 |
| 继承/D10.1 S0整卡 | 系统性 | 待独立复核 | D12 | 本轮串行六范围执行，结论由复核人给出，未通过不授予就绪。 |
| 复核/PA-N01 | 高 | 已修订 | CORE-02/13 | NOTATION命名空间、STORE_CORRUPT改error，业务错误表仍需完整门禁取证。 |
| 复核/PA-N02 | 高 | 已修订 | CORE-01 | 移除不存在的Clock端口，调用方一次取时后按显式op输入注入，领域禁读钟。 |
| 复核/PA-N03 | 高 | 已修订 | CORE-03 | const只读、清零归调用者，dispose取消/排空/NULL注销协议，保持DLL进程寿命。 |
| 复核/PA-N04 | 高 | 转P2 | CORE-13/H6 | 仓储handle账户持有/注入/关闭未设计完整；撤销统一已闭合的暗示，禁止隐式全局方案。 |
| 复核/PA-N05 | 高 | 已修订 | CORE-56 | Pack身份仅pack_id，版本元数据；失败快照不动/升级向量。 |
| 复核/PA-N06 | 高 | 已修订 | CORE-05/16 | content_hash排除自身及派生revision.id，先hash后派生ID。 |
| 复核/PA-N07 | 高 | 已修订 | CORE-17 | Card携当前epoch，新卡0，空新epoch仍忽略旧事件向量。 |
| 复核/PA-N08 | 中 | 部分修订 | CORE-67 | ready/pending及受支持子集/命名/示例补齐；真实业务schema仍H6/P2。 |
| 复核/PA-N09 | 中 | 已修订 | README8.3 | 显式67→03→04/41并列57。 |
| 复核/PA-N10 | 中 | 已修订 | CORE-08/09 | Rational对象与DimensionFull结构体唯一，文本声明单独解析。 |
| 复核/PA-N11 | 中 | 已修订 | CORE-04 | Fake未预置请求StateError。 |
| 复核/PA-N12 | 中 | 部分修订 | CORE-12/37 | 纯排版缓存纳入symbols/font字节哈希；Dart generation通知未闭合前禁用缓存，查询/通知契约P2。 |
| 复核/PB-N01 | 高 | 转P2 | CORE-13/23/24/26/32 | d4583cd已明确H6阻断，禁止隐式全局账户 |
| 复核/PB-N02 | 高 | 部分修订 | CORE-28/34/62 | 补显式用途与令牌参数；上传401不自动重发，返回预览重新确认；跨重试授权仍转P2 |
| 复核/PB-N03 | 高 | 部分修订 | CORE-26/46/66 | 归属与依赖同步；具体handle及敏感密钥加载schema随H6转P2 |
| 复核/PB-N04 | 中 | 已修订 | CORE-31 | 唯一表及units输入，由处理层提供快照 |
| 复核/PB-N05 | 高 | 已修订 | CORE-27 | 备份文件包装版本统一1；块AAD版本1；旧0格式不得导出 |
| 复核/PB-N06 | 中 | 已修订 | CORE-22/62 | 统一JSON semver，缺失事件minimumVersion=null且停止写入 |
| 复核/PB-N07 | 低 | 已覆盖 | CORE-02 | d4583cd已改68 |
| 复核/PB-N08 | 中 | 已修订 | CORE-33 | 原子spent+reserved+max检查；实际超预占据实记账并熔断 |
| 复核/PB-N09 | 中 | 已修订 | CORE-20/47 | 显式resume/cancel/reschedule三方法与保存顺序 |
| 复核/PC-N01 | 高 | 已修订 | CORE-58/54/AND-13/WIN-15 | 改无参独立方向ID并同步平台映射和Fake验收 |
| 复核/PC-N02 | 高 | 已修订 | CORE-37/59/36 | 59只引用37计算/绘制规则；唯一installEditorInput加入安装表 |
| 复核/PC-N03 | 中 | 已修订 | CORE-47/58/36 | 47仅导航；58拥有页面/触感；36聚合路由 |
| 复核/PC-N04 | 中 | 已修订 | CORE-38/60/61 | 移除越权op/验收；Rust None与FFI {}分别断言 |
| 复核/PC-N05 | 中 | 已修订 | CORE-39/40/49 | 统一binding/dto；特性dto只re-export或页面状态 |
| 复核/PC-N06 | 中 | 已修订 | CORE-04/AND-13/WIN-15 | owner定义setScreenSecure/{enabled}/bool，失败false，重建/嵌套测试 |
| 复核/PC-N07 | 中 | 已修订 | CORE-38/40/48/59 | 消费表三列且只引用owner，不重写级别/重试 |
| 复核/PC-N08 | 中 | 已修订 | CORE-37/64 | 固定Linux黄金图，Fake交互不计性能，真机归平台预算 |
| 复核/PC-N09 | 高 | 转P2 | CORE-41 | 实施前按门禁族拆卡/补复用估算，S0不通过，禁止凭行数开工 |
| 复核/PAN-N01 | 高 | 部分修订 | AND-01/02/06 | 统一FlutterFragmentActivity及模块参数；主干官方证据不替代锁版M0编译/认证探针 |
| 复核/PAN-N02 | 高 | 已修订 | AND-01 | S0冒烟runtime显示固定未实现提示；不调用Unsupported抛异常 |
| 复核/PAN-N03 | 高 | 已修订 | AND-03/04 | picker与camera隔离目录；清理等待完成；相机先恢复pending再GC |
| 复核/PAN-N04 | 中 | 已修订 | AND-02 | 新增launchMode及审计向量 |
| 复核/PAN-N05 | 高 | 转P2 | AND-12 | M-HOST外部门槛；框架另卡/规模待定前AND12不得就绪，移除虚构Instrumentation注入 |
| 复核/PAN-N06 | 中 | 已修订 | AND-08 | 补稳定ID标题/detail与未知ID失败测试 |
| 复核/PAN-N07 | 中 | 已修订 | AND-13 | 仅引用AND02唯一表，范围/规模/验收同步 |
| 复核/PAN-N08 | 中 | 已修订 | AND-02/07/11/14 | FileProvider/clipboard归14，所有.gradle改.kts |
| 复核/PAN-N09 | 中 | 已修订 | AND-14 | 复制前20MiB，限JPEG/PNG/WebP，其余拒绝、不谎标mime |
| 复核/PAN-N10 | 中 | 部分修订 | AND-06 | available复用相同API分档；26–29及CryptoObject锁版ROM矩阵仍M0阻断 |
| 复核/PB-N02补正 | 高 | 部分修订 | CORE-04/28/62 | 不使用未定义api用途；新增cloudControl并限制非上传识别路由，H6/重试授权仍P2。 |
| 复核/PW-N01 | 高 | 已修订 | CORE-04/WIN-01 | 公共smokeEntry明确Unsupported提示，不冒充快照 |
| 复核/PW-N02 | 高 | 部分修订 | WIN-07 | 删除未证实可编码方案；applock不支持，真实持久化保护仍P2/M0阻断 |
| 复核/PW-N03 | 中 | 已修订 | WIN-04/10 | 补WIN01依赖，05经04获得 |
| 复核/PW-N04 | 低 | 已修订 | WIN-14 | 统一11hex并将完整JSON作往返fixture |
| 复核/PW-N05 | 中 | 已修订 | WIN-13 | 按manifest选择call/submit，分列FFI与算法耗时 |
| 复核/PW-N06 | 中 | 已修订 | WIN-15 | 内层全局/编辑器→库scope→学习→ignored，文本/repeat策略及Fake测试 |
| 复核/PW-N07 | 低 | 已修订 | WIN-05 | 以明确九个格式名为准 |
| 复核/PU-N01 | 中 | 已修订 | tools/sadd/pack.mjs | 补两平台锁文件及依赖契约文件，存在/缺失双测试 |
| 复核/PU-N02 | 中 | 已修订 | tools/sadd/pack.mjs | 材料内定义与全仓库未收录本地定义分开，后者给owner与warning；不冒充SDK已核实 |
| 复核/PU-N03 | 中 | 已修订 | tools/sadd/current.mjs/stats/audit | ID集合拒重复/未知/遗漏，等级枚举，当前状态列计就绪；加同数量缺卡回归测试 |
| 复核/PU-N04 | 中 | 已修订 | README8.1/8.2/AGENTS | 直接完整、间接按符号固定点选择，全部分段读完，消除旧闭包全文要求 |
| 复核/PU-N05 | 低 | 已修订 | 附录C | 交付台账改C.9，来源章节C.8保留，同步首注 |
| 复核/PU-N06 | 低 | 已修订 | 附录A | 35～37行合回完整ADR表，删除中间空行 |

### D.9.P2-L-A（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| A-33 | 低 | 已覆盖 | 01 §0 | 现行正文已与README8.4一致：撤销删除正文、索引注明，编号不复用。 |
| A-34 | 低 | 已覆盖 | CORE-07/56/16 | 旧packs/bootstrap/notation路径已不存在；S1编译期数据归56，S4源包bootstrap-pack。 |
| A-35 | 低 | 已修订 | CORE-06 LX-04 | wire hint统一bound_index；Rust枚举名BoundIndex保留。 |
| A-36 | 低 | 已修订 | CORE-06 | 预算只在信封，body重复字段拒绝。 |
| A-37 | 低 | 已修订 | CORE-10 | 每侧200点、先正后负、绝对值升序、极点/零值/区间顺序明确。 |
| A-38 | 低 | 已修订 | CORE-02/03/04/36 | 主包/附属/行数补齐，composition和entry按文件分所有者，不再由目录重叠推测。 |

### D.9.P2-L-B（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| B-F-37 | 低 | 已修订 | CORE-35 | 补InputSpec/NormalizeSpec，严格对应现有JSON及张量布局/校验，不照抄不匹配字段。 |
| B-F-38 | 低 | 已修订 | CORE-28/56 | DebugInfoSource已覆盖，补56编排的直接依赖。 |
| B-F-39 | 低 | 已修订 | CORE-20/30/33 | 统计页49；纯Rust图片只消费字节；symbol_hints统一50。 |
| B-F-40 | 低 | 已修订 | CORE-20/21/35 | 试点原已标手动M3，模型原已分M-MODEL；T-UNLOCK补真机benchmark责任，不冒充单测。 |
| 继承/core-b:B-F-05 残留（Q33） | 高 | 部分修订 | README Q33/CORE-19 | 当前SELECT默认保持；产品确认后按变更单更新向量，不能自行确认。 |
| 继承/P0 B-F-05 Q33 | 高 | 部分修订 | README Q33 | 与上一条同一外部产品决策，追踪保留。 |

### D.9.P2-L-C（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| C-F-24 | 低 | 已修订 | CORE-40 | 补全probe全失败返回入口及清理；未建会话不转状态。 |
| C-F-25 | 低 | 已覆盖 | CORE-64 | P1拆卡后Fake只断言顺序，延迟归AND12/WIN13真机。 |
| C-F-26 | 低 | 已修订 | CORE-37/55/58 | 性能自动采样与S7真机预算分开，ADR25已采纳不退回待定。 |
| C-F-27 | 低 | 已覆盖 | CORE-41 | 提交示例已小写。 |
| C-F-28 | 低 | 已覆盖 | CORE-41 | header已为contracts/include/fmlcore.h。 |
| C-F-29 | 低 | 已修订 | CORE-41 | 定义近似计数规则及正反例，PR annotation/weekly归档。 |
| C-F-30 | 低 | 已修订 | CORE-42 | 初始扫描模式/输入编码/安全输出及供应商扩充门槛。 |
| C-F-31 | 低 | 已修订 | CORE-42 | 回滚执行归S7平台主机+checklist。 |
| C-F-32 | 低 | 已修订 | CORE-43/33 | 指定DDL/UTC采样口径与gauge，迁移契约测试。 |
| C-F-33 | 低 | 已覆盖 | CORE-55/58 | DesignWarmup已在58，55无AndroidSystemBars反向类型。 |
| C-F-34 | 低 | 已修订 | CORE-49 | Dart GranularityDto.week/wire week。 |
| C-F-35 | 低 | 已覆盖 | CORE-50 | 已为消费者三列引用表。 |
| C-F-36 | 低 | 已修订 | CORE-47 | 统一消息映射/Facade消费，无需依赖46实现。 |

### D.9.P2-H（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| P2H-01（PA-N04/PB-N01/PB-N03/A-17/A-24） | 高 | 部分修订 | CORE-03/13/23/24/26/32/65/66、ADR-V5-39 | 显式handle/路由/租约排空/密钥快照与成功例已补；CORE-66分批快照仍由该卡维护者补协议，晚期op schema仍pending。 |
| P2H-02（H6/A-19/A-20/B-F-20/B-F-29/C-F-17/C-F-18/PA-N08） | 高 | 部分修订 | CORE-67、contracts/dto/ | 34个S0～S2 op设计ready，结构断言251通过；晚期schema/pending mode尚未闭合，生成器未实现，不宣称业务可运行。 |
| P2H-03（PA-N12） | 高 | 已修订 | CORE-03/11/37/52/56/59/73 | 新增query/wait、预期代数验证、u64无损通知、缓存失效及重试向量；未把通知等同每次更新重放。 |
| P2H-04（PC-N09） | 高 | 已修订 | CORE-41/69/70/71/74 | 按门禁族拆卡，聚合器300行；仍须独立整卡语义复核，不自动就绪。 |
| P2H-05（B-F-28/D.10.1） | 高 | 已修订 | CORE-22/23/26/33/36/72 | 逐职责重估；33运维220行移72；23为460、26为490；实现越预算先拆卡。 |
| P2H-06（PAN-N05/AN-F09/AN-F19） | 高 | 部分修订 | PR1接续 | 主机框架将在AND-15/WIN-17定义，P2H组不冒称框架已交付。 |
| P2H-07（U-F01/U-F02/N12） | 高 | 部分修订 | CORE-57、README §8.1 | 增加预算失败开关、证据分类、缩小普通字段误扩展与无关ADR；直接契约超量和本地/SDK/Q warnings尚未全部关闭，责任CORE-57及各契约维护者，最终逐卡报告保留。 |
| P2H-08（PB-N02） | 高 | 已修订 | CORE-28/34/62 | POST不自动重试；重新确认签新一次性令牌，未换图/会话保留幂等键；401/超时/重启反例。 |
| P2H-09（AN-F01/10/18/26、PAN-N01） | 高 | 部分修订 | L-AN接续 | 权限向量/生命周期/选择器分支在平台组补；锁定FlutterFragmentActivity/ActivityResult探针仍M0外部前提。 |
| P2H-10（W-19） | 高 | 已覆盖 | WIN-04 | 明确HEIF/HEVC依设备扩展和许可，M0未实测不保证解码成功。 |
| P2H-11（A-32/U-F13/U-F24/N7） | 高 | 部分修订 | CORE-15/16/35、附录C | tough在线适配、真实包/模型/数据与发行许可、实名负责人仍未提供；保留M0/M-CONTENT/M-MODEL外部门槛，甲方/各资源负责人接续。 |
| P2H-12（B-F-05/B-F-36） | 高 | 部分修订 | README §6 Q32～Q40 | 产品待确认，暂行默认不变；Q33确认后CORE-19补SELECT向量，甲方决策。 |
| P2H-13 | 高 | 部分修订 | D.14接续 | 独立复核范围明确含aa3fbdb及5e7ae86；待全组提交后执行。 |
| P2H-14 | 中 | 部分修订 | PR6接续 | v5.3.2报告保留历史快照；最终新版本报告另存。 |
| P2H-15 | 高 | 部分修订 | CORE-57、PR6接续 | 保留先行工具但不宣称实现验收；Node锁文件仍未建立，独立复核后记录D.12。 |
| P2H-16 | 高 | 部分修订 | PR6接续 | 新增S0门禁卡并入复核；独立复核不通过仍保持未就绪。 |
| AN-F03/PAN-N10/W-27/PW-N02、AN-F01生物识别部分 | 继承 | 不采纳 | ADR-V5-38 | 不适用：甲方已撤销应用锁/生物识别/Hello/防截屏，历史条目不恢复。 |

### D.9.P2-AN（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| AN-F28 | 低 | 已修订 | AND-03/06/07/08/09/14内联 | 从CORE原文复制abstract interface声明，含方法和行尾注释。 |
| AN-F32 | 低 | 已修订 | AND-09 | 全部3xx原样返回；版本取FML_APP_VERSION。 |
| AN-F33 | 低 | 已修订 | CORE-20/49、AND-08 | 公共契约同步为ok/warn/unknown，未知不计红项。 |
| AN-F34 | 低 | 已修订 | AND-13 | 不读私有键，默认unknown；保留M0设备验证。 |
| AN-F35 | 低 | 已修订 | CORE-04/AND-06 | 真实路径越界ArgumentError与契约反例同步。 |
| AN-F36 | 低 | 已修订 | AND-06/CORE-65/47 | 平台仅报告等级，共享账户/安全页呈现提示。 |
| AN-F37 | 低 | 已修订 | AND-11 | strip前Rust库归档、build-id及打包来源区分；扫描标签改R26/R20。 |
| AN-F38 | 低 | 已修订 | AND-13/AND-12 | 性能移交S7统一验收，不阻塞S2。 |
| AN-F29 | 低 | 已覆盖 | AND-01 | 当前安装顺序13→07→14→08；剪贴板已迁14，不恢复过时03安装。 |
| AN-F30 | 低 | 已覆盖 | AND-01 | 撤销AND-10已明确，现02～09及13/14。 |
| AN-F31 | 低 | 已覆盖 | AND-01 | 已含cargo ndk --platform26与源提交Unix时间SOURCE_DATE_EPOCH。 |
| P2H-09补充 | 高 | 部分修订 | AND-01/02/03 | 权限正反向量/模块生命周期/单多选补齐；M0锁版ActivityResult时序探针仍须Android维护者实测，不冒称通过。 |

### D.9.P2-W（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| W-31 | 低 | 已修订 | WIN-15 | DWM后FRAMECHANGED及非客户区重绘，不改变激活/几何；1809/11实测仍外部前提。 |
| W-32 | 低 | 已覆盖 | WIN-05 | 现验收已列九个剪贴板格式。 |
| W-33 | 低 | 已覆盖 | WIN-01 | 端口字段现为camera，无cameras残留。 |
| W-34 | 低 | 已修订 | WIN端全部公共abstract interface摘录 | 从01复制完整声明，含注释；ImageDropSource保持原文行式。 |
| W-35 | 低 | 已修订 | CORE-36、WIN-03/09/14 | 12/85纳入顺序表；86/95明确保留为空，健康/托盘已迁独立首帧20/10，禁止恢复旧阻塞顺序。 |
| W-36 | 低 | 已覆盖 | 03 §1 | 依赖图从每卡依赖重生，含W03/06/07/09/14/15→C04及W15→W01。 |

### D.9.P2-U（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| U-F11 | 低 | 已覆盖 | D.10 | 现行逐卡表与历史批次区分，最终等级/就绪由PR6刷新。 |
| U-F18 | 低 | 已修订 | AGENTS.md | 补unsafe/SAFETY、短分支、文档告警、deny/llvm-cov、材料→模板→检查→提交；未创建检查不伪称通过。 |
| U-F19 | 低 | 已覆盖 | CORE-01目录布局 | 已含settings/calc/study_stats/books/packs/design及recognition，ui与用例层分开。 |
| U-F25 | 低 | 已覆盖 | 附录B、CORE-35、附录C | YOLO仅实验分支；运行时/真实模型许可仍M-MODEL门槛，不恢复主线依赖。 |

### D.9.P2-PR1（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| PR1（P2H-06/PAN-N05/AN-F09/AN-F19） | 流程 | 已修订 | AND-15/WIN-17、平台验收消费者 | S2框架/fixture、CLI/证据/取消/超时/CI与M0外部前提明确；未实现框架和未到设备仍阻断验收，不虚构主机通过。 |

### D.9.P2-PR2（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| PR2 | 流程 | 已修订 | README §5/§7验证责任 | 验证方式列已有，不重复增列；R42.a改人工签字，R05/R42.c分别归内容与平台矩阵，代码fixture不代替产品交付。 |

### D.9.P2-PR3（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| PR3（W-35） | 流程 | 已修订 | CORE-02/04/36/75、contracts/policies/shared-writes.json | 逐码/文件/安装点/路由/快捷键表/Settings及双序列order预分配；设计验证与实现回执分开，86/95未分配禁止占用。 |

### D.9.P2-PR4（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| PR4 | 流程 | 已修订 | README §8.3/§8.4 | 契约回流流程已有并核实保留；新增05/55/08真实会话试点门槛/问题台账/回写证据，尚未执行不冒称试点通过。 |

### D.9.P2-PR5（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| PR5（U-F18） | 流程 | 已修订 | AGENTS、README §8.2～§8.5、CORE-41 | 模板给具体变更单字段、全量检查与证据；S0十四卡按新依赖推进；41只测编排不重复69/70/71/74规则。 |
| L-A/L-B/L-C接续复核 | 低 | 已覆盖 | c765274/7bf12ad/5d015fe落点 | 逐项核对A33～38/B37～40/C24～36的名称、扫描初始清单、模型分层、目录、错误引用/注释与性能归属仍成立；41职责拆分后规则移69/71/74，非恢复旧大卡。 |

### D.9.P2-PR6（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| PR6（P2H-14/15/16） | 流程 | 部分修订 | CORE-57/70/76、D.10/D.12、reports/ | 统计和证据校验已脚本化，旧快照保留；全卡最新评级等待本轮独立只读复核后填D.12，不能先自评为就绪。 |

### D.9.P2-FINAL-H（2026-10-20）

| 索引 | 严重度 | 结论 | 落点 | 说明 |
| --- | --- | --- | --- | --- |
| P2H-01 | 高 | 部分修订 | CORE-03/13/23/24/26/32/65/66 | 显式handle/租约/密钥加载已补，late DTO/同步快照和全量消费确认未齐；owner按D.14遗留先修。 |
| P2H-02（A-19/A-20/B-F-20/B-F-29/C-F-17/C-F-18） | 高 | 部分修订 | CORE-67及op所有者 | 34 ready/105 pending；修AST/i64/逐op错误镜像并实测结构，未实现生成器和后期协议，不把ready等同语义通过。 |
| P2H-03 | 高 | 部分修订 | CORE-56/73/37/52/59 | 查询/通知、耗尽Result与可用性、userDecls复制输入已补；独立评级保留，真实实现/消费确认/并发向量待执行。 |
| P2H-04 | 高 | 部分修订 | CORE-41/69/70/71/74/76 | 拆卡及76依赖、LCOV门禁协议已补；锁版与实际门禁未完成，S0仍不通过。 |
| P2H-05（B-F-28） | 中 | 部分修订 | CORE-22/23/26/33/36/72 | 33运维拆72，其他职责重估；32/66/09等全量规模证据仍缺，owner须先拆超限卡。 |
| P2H-06 / PR1 | 中 | 部分修订 | AND-15/WIN-17 | 新增主机框架卡与自包含目标、制品/握手/隔离设计；框架未实现，真机/交互桌面未到，不宣称运行通过。 |
| P2H-07（U-F01/U-F02/N12） | 高 | 部分修订 | CORE-57/76及各owner | 收齐manifest.schema和裸路径、关闭显式Q关联差异；仍多数超量、三类符号/闭包warning和全部材料复核未闭合；不声称优化成功。 |
| P2H-08 | 中 | 已修订 | CORE-28/34/62 | 401后旧token废弃，用户重新确认签新token，原session/image同幂等键；namespace派生和黄金文件补齐，真实业务向量待实现。 |
| P2H-09 | 高 | 部分修订 | AND-01/02/03/13 | 权限/ActivityResult/模块协议及输入所有者已补；锁版探针与真机仍M0，Android owner执行。 |
| P2H-10 | 中 | 已覆盖 | WIN-04 | 仅声明HEIF/HEVC扩展组合待M0，不承诺安装单一扩展必然可用。 |
| P2H-11（A-32/U-F13/U-F24） | 高 | 部分修订 | CORE-15/16/35、附录C | 外部tough适配、内容/模型/许可与实名负责人尚缺，甲方及对应owner接续。 |
| P2H-12 | 中 | 部分修订 | README §6 Q32～40 | 暂行默认保持，逐项待甲方确认；Q41已确认不恢复。 |
| P2H-13 | 中 | 已修订 | D.14与三份独立报告 | aa3fbdb/5e7ae86相关现行卡纳入只读复核，移除锁残留与11端口遗漏修复；没有补造通过。 |
| P2H-14 | 中 | 已修订 | reports/v5.3.3-audit.json | 另存当前快照，v5.3.2报告保持历史，不把旧数当当前。 |
| P2H-15 | 高 | 部分修订 | CORE-57/76 | 保留先行设计工具，回归/证据核对补强；tools/toolchain.versions缺失、锁版/完整消费确认仍阻断。 |
| P2H-16 / PR6 | 高 | 部分修订 | D.10/D.12、CORE-76 | 106卡全部独立复评、证据校验及统计；0就绪，未达到整卡通过条件，不能授予开工许可。 |
| PR2 | 流程 | 已修订 | README §5、CORE-41/70 | 补R23主机回滚/manual、R40真实Key轮换；验证类别与责任同步，未执行不计通过。 |
| PR3（W-35） | 流程 | 已修订 | CORE-36/75、shared-writes | 补漏安装点/路由/逐码；参数段、根路由、最长归属与单写统一，design通过不冒充实现回执。 |
| PR4 | 流程 | 部分修订 | README §8.3/8.4 | 契约回流、试点入口/证据已写；CORE-05/55/WIN-08真实试点尚未执行，先关闭S0外部门槛。 |
| PR5（U-F18） | 流程 | 已修订 | AGENTS与模板 | 检查职责补reservation tests、覆盖率固定输入，规则同步；运行命令不存在时须pending，不能填通过。 |
| AN-F28 / W-34 | 低 | 已修订 | AND-03/06、WIN-04/07/09 | 一轮修复补类前///与TrayPresence完整注释；独立报告中的部分结论保留历史，未二次独立提级。 |
| B-F-09 | 高 | 部分修订 | CORE-32 | 历史密钥包装方向已修，但Purged保留元数据与NOT NULL包装DDL矛盾尚未解决；owner修DDL/状态后复检。 |
| C-F-03 | 高 | 部分修订 | CORE-55/58 | 补LocalFileStore显式注入与controller路由参数，AppearanceScope旧引用清除；全材料/消费确认未完成，不追认整卡通过。 |

### D.9.1 v5.3历史检查与证据边界（v5.3.2最终见D.13）

以下保留v5.3历史检查，不作v5.3.2最终数值。当时只修订设计文档，没有Rust/Flutter产品代码可运行。`check.mjs`、`xref.mjs`、`mat.mjs`用相同解析器重跑修订前快照和当前文档；未修改基线或原评审。交叉引用是启发式，不能把计数当完整性证明。重复错误码的消费者改列“错误码引用/唯一定义卡/本卡处理”，唯一所有者仍保留标准定义表；op按已有契约逐行列出，未以删引用或修改解析器降低指标。

| 脚本/指标 | v5.2.1基线 | v5.3历史结果 |
| --- | --- | --- |
| check：有效卡/问题/环 | 81 / 0 / 无 | 83 / 0 / 无 |
| xref：crossDep | 51 | 22 |
| xref：dupErr | 16 | 0 |
| xref：undefOps | 14 | 0 |
| xref：undefErr / undefTypes | 102 / 407 | 93 / 410 |
| xref：multiDefTypes | 26 | 27 |
| mat：平均字符 | 70138 | 89590 |
| mat：中位字符 | 52470 | 78485 |
| mat：最大字符（WIN-13） | 238521 | 276135 |

mat增加来自补全共享契约与新增前置数据/守卫/启动器，不是材料缩减成果；算法只算“本卡+闭包契约”，尚未包含README §8.1新增需求/Q/ADR等，故数字是材料下界。按80000字符警报继续P1 U-F02的符号级组装/拆卡，不能静默省略。undefTypes上升3与multi上升1保留为噪声/待复核证据，不宣称全部引用已闭合。

临时独立参照脚本使用SymPy1.14.0：54/54通过，覆盖GX数学/定义域、CX数值、精确SI与边界、15条AST JSON、ID拼接/CBOR长度；输出在temp/tools/out/p0-reference.json。此结果只验证文档期望，不是Rust判分、真实fsrs replay或跨平台实现测试。FS01～04实际输出须编码时从固定库与独立外围状态机生成；本轮未伪造黄金输出。Casdoor真实协议、模型ExpRate/许可与Windows故障恢复/矩阵仍待对应门槛验收。

## D.10 当前逐卡汇总（2026-10-21，v5.3.4；复核列名仍为 v5.3.3 复核，其中 29 张卡已登记 v5.3.4 整卡复核结果）

本节覆盖108张有效卡，是唯一当前状态；D.4～8与旧版本列保留历史。v5.3.2复核列来自六范围只读独立复核（多方取较低），不沿用修订方自评、不因lead修复提升。A/B/C不是开工许可；就绪只来自D.12通过记录。全部S0整卡不通过；修复后未再独立复检，故本轮就绪0。外部锁版/设备/模型/许可与Q32～40门槛按依赖继承。具体发现、修订和P2见D.13，不能用机械0项证明语义闭合。

| 编号 | 阶段 | 评审等级（2026-10-19） | v5.3 修订后 | v5.3 复核（2026-10-20） | v5.3.1 修订后（未独立复核） | v5.3.2 复核 | v5.3.3 复核 | 当前状态 | 待定ADR影响（含依赖闭包） | 遗留阻塞/未复核原因 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CORE-01 | S0 | B | B | B | B | C | B | 未就绪（D.12 P2-CORE-01；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I01；首卡验收依赖后卡，锁版与材料超量。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r1；s6-a，D.12 P2-CORE-01）：B/fail；阻断 R01-01 members 含 server 与本卡验收冲突（S0…；R01-02 交付文件清单缺失，deny.toml/lints 等 …；S6-CORE-01-01 DEP-1 允许表、dep6_symbo…；S6 pass。 CO-14附带：补Cargo workspace成员规则与fml-sync-proto目录（N-11）；lead修订后未复检，受影响条目须由非作者复检，不改等级。 |
| CORE-02 | S0 | B | B | B | B | C | B | 未就绪（D.12 P2-CORE-02；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-N03；机器错误集合、消费确认、完整材料。；lead修复见D.14，未重新提级。 CO-14：补TraceId/Severity/Diagnostic/FmlError derive与serde、ErrorCode生成方法、FmlError::new/with_trace构造、示例改“L T^-1”；lead修订后未复检，受影响条目须由非作者复检，不改等级。 v5.3.4整卡复核（2026-10-21，rev-r3；s6-a，D.12 P2-CORE-02）：B/fail；阻断 R3-02-01 FFI/HTTP 适配层 with_trace 填…；R3-02-02 生成物 API 欠规格（变体命名、未知 code …；R3-02-03 Dart FmlException.fromJso…；R3-02-04 所有权两处登记；按各卡错误表预登记会漏 FFI_/…；S6 pass。 |
| CORE-03 | S0 | B | — | B | B | C | B | 未就绪（D.12 P2-CORE-03；pending） | —（仍须开工锁版本/平台探针） | 独立发现：E-N01～04；handle改善，FFI规模与机器契约待闭合。；lead修复见D.14，未重新提级。 |
| CORE-04 | S0 | B | B | B | B | C | C | 未就绪（D.12 P2-CORE-04；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I13；同步Installer与异步editor不一致。；lead修复见D.14，未重新提级。 |
| CORE-05 | S1 | C | B | B | B | B | B | 未就绪（D.12 P2-CORE-05；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-N01/02/04；正文、黄金向量、schema不一致。；lead修复见D.14，未重新提级。 CO-14：MathKind补derive与serde外部标签约定；lead修订后未复检，受影响条目须由非作者复检，不改等级。 v5.3.4整卡复核（2026-10-21，rev-r1，D.12 P2-CORE-05）：B/fail；阻断 R05-01 核心类型 derive/serde 约定缺失（仅 Ma…；R05-02 外部前提缺 NFC、SHA-256、JSON Sche…；R05-03 ID/seed 函数无覆盖且期望值非独立；S6 pass。 |
| CORE-06 | S1 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-06；pending） | —（仍须开工锁版本/平台探针） | 独立发现：export漏码；schema/消费确认及规模待证。；lead修复见D.14，未重新提级。 |
| CORE-07 | S1 | C | C | B | B | C | B | 未就绪（D.12 P2-CORE-07；pending） | —（仍须开工锁版本/平台探针） | 独立发现：notation漏码；完整材料和消费确认未完成。；lead修复见D.14，未重新提级。 |
| CORE-08 | S1 | C | B | B | B | B | B | 未就绪（D.12 P2-CORE-08；fail） | —（仍须开工锁版本/平台探针） | 独立发现：units错误为空；AST机器修正与确认。；lead修复见D.14，未重新提级。 CO-14：PseudoDim补derive与serde；补checked运算与规范形单测；规模500；lead修订后未复检，受影响条目须由非作者复检，不改等级。 v5.3.4整卡复核（2026-10-21，rev-r1，D.12 P2-CORE-08）：B/fail；阻断 R08-01 Rational/Dimension/Dimensio…；R08-02 缺 UnitRegistry/UnitRegistry…；R08-03 π/角度换算无法用 Rational 精确表示，验收无…；R08-04 UNIT_AFFINE_MISUSE 无触发入口，温度…；S6 pass。 |
| CORE-09 | S1 | B | B | B | B | C | B | 未就绪（D.12 P2-CORE-09；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I02；500+150行未拆卡。；lead修复见D.14，未重新提级。T1后续（D.14.5）：已拆出CORE-77，规模改约480行，须重新整卡复核。 v5.3.4整卡复核（2026-10-21，rev-r1，D.12 P2-CORE-09）：B/fail；阻断 R09-01 运算规则表未在卡内枚举；R09-02 QuantityKind 与 MathKind 的推断…；R09-03 dx.yaml 输入与约定诊断映射未给出，验收不能直接…；S6 pass。 CO-13：TypedAst输出前resolve（⑥）、fresh上界（⑦）及typed规范形验收；lead修订后未复检，受影响条目须由非作者复检，不改等级。 |
| CORE-10 | S1 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-10；pending） | —（仍须开工锁版本/平台探针） | 独立发现：500行估算、AST/FFI机器契约需复核。；lead修复见D.14，未重新提级。 |
| CORE-11 | S1 | B | — | B | B | C | B | 未就绪（D.12 P2-CORE-11；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I03；排序输入不足，derive错误为空。；lead修复见D.14，未重新提级。 CO-13：DERIVE_TYPE_MISMATCH与rank按CORE-77跨来源协议两侧实例化，rank的Overflow候选省略并补验收；lead修订后未复检，受影响条目须由非作者复检，不改等级。 v5.3.4整卡复核（2026-10-21，rev-r1，D.12 P2-CORE-11）：B/fail；阻断 R11-01 substitute/rank 依赖的符号反解没有公开…；R11-02 substitute 的确定性规则缺失；R11-03 RevisionSnapshot.typed 与 Ca…；S6 pass。 |
| CORE-12 | S1 | B | B | C | B | C | B | 未就绪（D.12 P2-CORE-12；pending） | —（仍须开工锁版本/平台探针） | 独立发现：AST schema、字体/工具外部门槛。；lead修复见D.14，未重新提级。 |
| CORE-13 | S2 | B | B | B | B | C | B | 未就绪（D.12 P2-CORE-13；fail） | —（仍须开工锁版本/平台探针） | 独立发现：STORE_BUSY镜像遗漏，消费确认待完成。；lead修复见D.14，未重新提级。 CO-17：push_batch归属改CORE-78；迁移待执行判定与乱序补执行规则及验收；lead修订后未复检，受影响条目须由非作者复检，不改等级。 v5.3.4整卡复核（2026-10-21，rev-r2；s6-c，D.12 P2-CORE-13）：B/fail；阻断 F-01（高）缺全量重入队能力：OutboxEntityCodec …；F-02 op_id/device_id 随机来源未定义；F-03 外部前提缺 uuid、serde_json、blake3 …；F-04 迁移 checksum 不符、有记录无文件等规则与机器校验…；S6 pass。CO-22 后待复检。 |
| CORE-14 | S3 | C | B | B | B | C | C | 未就绪（D.12 P2-CORE-14；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I04；标签错误条件和后阶段批次表述。；lead修复见D.14，未重新提级。 |
| CORE-15 | S4 | C | C | C | B | C | C | 未就绪（D.12 P2-CORE-15；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I05；tough真实适配未闭合。；lead修复见D.14，未重新提级。 |
| CORE-16 | S4 | C | C | C | B | C | B | 未就绪（D.12 P2-CORE-16；pending） | —（仍须开工锁版本/平台探针） | 独立发现：真实内容/审校/许可、15适配与规模。；lead修复见D.14，未重新提级。 |
| CORE-17 | S4 | C | B | B | B | C | B | 未就绪（D.12 P2-CORE-17；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I06；review_event唯一键冲突。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r4；rev-r5，D.12 P2-CORE-17）：B/fail；阻断 F-01（高）FsrsParams 持久化/同步与 params_v…；F-02（高）pending_choice 由谁、何时置位未定义；F-03 规模≥650 行需拆卡（含 fml-ffi 附属未计）；R5-17-01（中）generate_cards 无 templa…；R5-17-02（中）CardType × RequirementL…；S6 pass。 |
| CORE-18 | S4 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-18；pending） | —（仍须开工锁版本/平台探针） | 独立发现：类型/数值边界、判分语料、500行与确认。；lead修复见D.14，未重新提级。 |
| CORE-19 | S4 | C | B | B | B | B | B | 未就绪（D.12 P2-CORE-19；pending） | —（仍须开工锁版本/平台探针） | 独立发现：继承17事务问题，Q33待确认。；lead修复见D.14，未重新提级。 |
| CORE-20 | S4 | C | B | B | B | C | B | 未就绪（D.12 P2-CORE-20；pending） | —（仍须开工锁版本/平台探针） | 独立发现：17事件前提、真实试点和材料。；lead修复见D.14，未重新提级。 |
| CORE-21 | S2 | B | B | B | B | C | B | 未就绪（D.12 P2-CORE-21；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I07；随机输入与失败返回不闭合。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r3；s6-a，D.12 P2-CORE-21）：B/fail；阻断 R3-21-01（高）SecretKey 无构造与取值接口（波及 C…；R3-21-02（高）RecoveryCode 无取文本接口，rec…；R3-21-04 KV-02～05 向量无法经公开函数验证；R3-21-05 CRYPTO_KEY_VERSION_UNKNOW…；S6 pass。CO-22 后待复检。 |
| CORE-22 | S2 | C | C | C | C | B | B | 未就绪（D.12 P2-CORE-22；pending） | —（仍须开工锁版本/平台探针） | 独立发现：Casdoor锁版、真实账号与规模。；lead修复见D.14，未重新提级。 |
| CORE-23 | S2 | C | C | C | C | C | B | 未就绪（D.12 P2-CORE-23；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-N04/错误镜像及消费确认。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r3；s6-d，D.12 P2-CORE-23）：B/fail；阻断 R3-23-01（高）登记 GuardContext 的 Dart …；R3-23-02（高）删除档案、更新 last_used_ms、se…；R3-23-03/04 OsRandom 无注入点、create_g…；S6-CORE-23-01（中）档案创建 op 漏列 RNG 失败透…；S6 pass。 |
| CORE-24 | S6 | C | C | C | C | C | C | 未就绪（D.12 P2-CORE-24；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-N06；撤销锁后仍保留解锁入口。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r3；s6-d，D.12 P2-CORE-24）：C/fail；阻断 R3-24-01（高）规模不可信，远超 500 行，需拆卡（merg…；R3-24-02（高）NewAccount 升级需更新注册表行，CO…；R3-24-03 同一 op 不能同时 call 与 submit；R3-24-04 随机/时间来源未注入；S6 fail：材料缺 CORE-05 pack_item_id/p…；S6 fail。CO-22 后待复检。 |
| CORE-25 | S6 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-25；fail） | V5-18：正式托管受阻 | 独立发现：26密文重发一致性与DB锁版。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r2；s6-b，D.12 P2-CORE-25）：B/fail；阻断 S6-CORE-25-01（高）BIGSERIAL 取号顺序不等于提…；F-01 越权 404、无快照 404、无令牌 401 未给错误码；F-02 sync_envelope.body 存什么未定义；F-05 规模约 500 行无分项、疑超 500；S6 pass。 |
| CORE-26 | S6 | C | C | C | B | C | B | 未就绪（D.12 P2-CORE-26；fail） | V5-18：正式托管受阻 | 独立发现：E-I08；密文持久字段与收敛规则缺口。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r2；s6-b，D.12 P2-CORE-26）：B/fail；阻断 S6-CORE-26-01（高）apply_pull 缺 11 类实…；F-01 CONFLICT 即判定整库回退与 ADR-V5-43/T…；F-02 负载 CBOR 无编码/解码契约；F-03 构造 Envelope 的字段映射未定义；F-04 on_epoch_changed 全量重建 outbox …；S6 pass。CO-22 后待复检。 CO-15/16：prepare_push改为接收WriteTx、陈旧批次Stale作废重建、max_bytes请求体口径、错误透传补全及T-STALE/并发/口径验收；lead修订后未复检，受影响条目须由非作者复检，不改等级。 |
| CORE-27 | S6 | B | B | — | B | C | C | 未就绪（D.12 P2-CORE-27；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I09；调用模式、引用闭包、格式不唯一。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r3；s6-d，D.12 P2-CORE-27）：C/fail；阻断 R3-27-01（高）规模约 730 行，需拆卡；R3-27-02（高）Replace 删除范围表与 RESTRICT…；R3-27-04 token 临时库为进程级全局表，与 ADR-V5…；R3-27-05 恢复模式在 prepare/commit 两侧不一…；S6 fail：材料缺 CORE-19/48 范围表列/外键/写入契…；S6 fail。 |
| CORE-28 | S2 | C | C | B | B | B | B | 未就绪（D.12 P2-CORE-28；pending） | —（仍须开工锁版本/平台探针） | 独立发现：完整依赖闭包及消费确认。；lead修复见D.14，未重新提级。 |
| CORE-29 | S5 | A | — | — | — | B | B | 未就绪（D.12 P2-CORE-29；pending） | —（仍须开工锁版本/平台探针） | 独立发现：识别后端前提与材料。；lead修复见D.14，未重新提级。 |
| CORE-30 | S5 | B | — | — | — | B | B | 未就绪（D.12 P2-CORE-30；fail） | —（仍须开工锁版本/平台探针） | 独立发现：图像标定/Q、消费确认。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r3；s6-c，D.12 P2-CORE-30）：B/fail；阻断 R3-30-02（高）核心侧无契约获知 StoreArea.stag…；R3-30-04 预处理流水线次序与坐标系未定义；R3-30-03 QualityReport 多个字段无公式；R3-30-06 规模恰在上限且带超出再拆保留语；S6 pass。 |
| CORE-31 | S5 | B | — | — | — | C | B | 未就绪（D.12 P2-CORE-31；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I10；内部纯函数输入/评分边界。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r4；rev-r5，D.12 P2-CORE-31）：B/fail；阻断 F-01（高）apply_correction 缺 units 与 …；R5-31-01（高）三个纯函数只收预构造 SymbolEnv，缺逐…；F-02 fml-recognize 内编排解析/绑定与 CORE-…；F-05 RECOG_OUTPUT_REJECTED 等错误语义无出…；S6 pass。 |
| CORE-32 | S5 | C | C | C | B | C | C | 未就绪（D.12 P2-CORE-32；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I11；包装删除与DDL冲突、归属/规模。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r3；s6-d，D.12 P2-CORE-32）：C/fail；阻断 R3-32-01（高）gc_execute 无 Store 参数却须…；R3-32-02（高）HistoryRepo 致 fml-recog…；R3-32-08（高）规模恰在 500 上限且未计 fml-ffi …；S6 fail：材料缺 Page<T> 定义（证实 R3-32-09…；S6 fail。CO-22 后待复检。 |
| CORE-33 | S5 | C | C | C | C | B | B | 未就绪（D.12 P2-CORE-33；pending） | V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：运维已拆；供应商/预算fixture及规模。；lead修复见D.14，未重新提级。 |
| CORE-34 | S5 | B | B | — | B | C | C | 未就绪（D.12 P2-CORE-34；fail） | V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：E-I12；NS_FML_CLOUD未冻结。；lead修复见D.14，未重新提级。 |
| CORE-35 | S5 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-35；pending） | V5-13：Fake可先行，真实模型受阻 | 独立发现：真实模型/运行时/许可/真机。；lead修复见D.14，未重新提级。 |
| CORE-36 | S2 | C | C | B | B | B | B | 未就绪（D.12 P2-CORE-36；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-N05/E-I13；单写、异步安装和重复注册。；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r4；rev-r5，D.12 P2-CORE-36）：B/fail；阻断 F-01（高）DefaultAccountController/To…；F-03 SYNC_NOT_AVAILABLE 的游客触发条件无人实…；F-04 errors.g.dart 不存在（CORE-02 实际生…；R5-36-01（中）NetworkGuard 所需 GuardCo…；S6 pass。CO-22 后待复检。 |
| CORE-37 | S2 | C | C | B | B | B | C | 未就绪（D.12 P2-CORE-37；fail） | —（仍须开工锁版本/平台探针） | 独立发现：E-I13；Worker未被等待，AST机器契约。；lead修复见D.14，未重新提级。 |
| CORE-38 | S3 | C | C | B | B | B | B | 未就绪（D.12 P2-CORE-38；pending） | —（仍须开工锁版本/平台探针） | 独立发现：ProfileSessionSource切换失效、单写和消费确认。；lead修复见D.14，未重新提级。 |
| CORE-39 | S4 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-39；pending） | —（仍须开工锁版本/平台探针） | 独立发现：M/L/H；L-I09；lead修复见D.14，未重新提级。 |
| CORE-40 | S5 | C | C | C | B | B | B | 未就绪（D.12 P2-CORE-40；fail） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M/L/H；L-I07/09；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r4；rev-r5，D.12 P2-CORE-40）：B/fail；阻断 F-01（高）installRecognition 构造 Histo…；F-06 规模约 370 行疑偏低；F-04/F-07 错误处理与验收只覆盖主路径；R5-40-01（中）启动钩子 50 recog.recover 为…；S6 pass。CO-22 后待复检。 |
| CORE-41 | S0 | C | C | B | B | C | B | 未就绪（D.12 P2-CORE-41；fail） | —（仍须开工锁版本/平台探针） | 独立发现：L-N05/06；M/L；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r1；s6-a，D.12 P2-CORE-41）：B/fail；阻断 R41-01 run_all 的 manifest、CLI 与归档格…；R41-02 范围与归属表矛盾，thresholds.yaml 归属…；S6-CORE-41-01 CORE-71 交给本卡的 core-s…；S6 pass。 |
| CORE-42 | S7 | B | — | B | B | B | B | 未就绪（D.12 P2-CORE-42；pending） | —（仍须开工锁版本/平台探针） | 独立发现：M/L；真实发布/回滚未执行；lead修复见D.14，未重新提级。 |
| CORE-43 | S7 | B | — | B | B | B | B | 未就绪（D.12 P2-CORE-43；pending） | V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M/L；真实托管/账号/轮换；lead修复见D.14，未重新提级。 |
| CORE-44 | S7 | A | — | A | A | A | B | 未就绪（D.12 P2-CORE-44；pending） | —（仍须开工锁版本/平台探针） | 独立发现：M/L；锁版SDK/C消费者；lead修复见D.14，未重新提级。 |
| CORE-45 | S2 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-45；pending） | —（仍须开工锁版本/平台探针） | 独立发现：M/L；供应商/域名；lead修复见D.14，未重新提级。 |
| CORE-46 | S6 | B | B | B | B | C | B | 未就绪（D.12 P2-CORE-46；fail） | V5-18：正式托管受阻 | 独立发现：M/L/H；66分批协议；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r4；rev-r5，D.12 P2-CORE-46）：B/fail；阻断 F-01（高）紧凑 JSON 字节约束与 ApiClient.cal…；F-02 依赖缺 CORE-03 与 CORE-78；F-06 游客/未开启同步三处行为不一致（disabled、SYNC…；R5-46-01（中）协调器无 ProfileSessionSour…；S6 pass。CO-22 后待复检。 CO-15/16：SYNC_BATCH_UNKNOWN按良性处理、紧凑JSON推送约束与验收；lead修订后未复检，受影响条目须由非作者复检，不改等级。 |
| CORE-47 | S6 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-47；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M/L/H；完整消费确认；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r4；rev-r5，D.12 P2-CORE-47）：B/fail；阻断 F-01（高）BackupVm.pickAndPrepare 无 m…；F-02（高）账户、提醒、隐私、关于、needsKey 等子页无 V…；F-06 规模约 480 行估算 600～750，疑超 500；R5-47-01（中）merge_choice 待选并发修订无界面卡…；S6 pass。CO-22 后待复检。 |
| CORE-48 | S3 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-48；pending） | —（仍须开工锁版本/平台探针） | 独立发现：M/L/H；计划DTO/同步；lead修复见D.14，未重新提级。 |
| CORE-49 | S4 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-49；pending） | —（仍须开工锁版本/平台探针） | 独立发现：M/L/H；L-N04；lead修复见D.14，未重新提级。 |
| CORE-50 | S5 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-50；pending） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M/L/H；识别DTO/平台接缝；lead修复见D.14，未重新提级。 |
| CORE-51 | S4 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-51；pending） | —（仍须开工锁版本/平台探针） | 独立发现：M/L/H；包schema/tough；lead修复见D.14，未重新提级。 |
| CORE-52 | S3 | B | B | B | B | B | C | 未就绪（D.12 P2-CORE-52；fail） | —（仍须开工锁版本/平台探针） | 独立发现：L-N02；L-I08/09；M/L；lead修复见D.14，未重新提级。 |
| CORE-53 | S3 | A | — | A | A | A | B | 未就绪（D.12 P2-CORE-53；pending） | —（仍须开工锁版本/平台探针） | 独立发现：L-I06/08/09；M/L；lead修复见D.14，未重新提级。 |
| CORE-54 | S3 | B | B | B | B | B | B | 未就绪（D.12 P2-CORE-54；pending） | —（仍须开工锁版本/平台探针） | 独立发现：L-I08/09；M/L/H；lead修复见D.14，未重新提级。 |
| CORE-55 | S2 | C | C | C | C | B | C | 未就绪（D.12 P2-CORE-55；fail） | —（仍须开工锁版本/平台探针） | 独立发现：L-I05；M/L；lead修复见D.14，未重新提级。 |
| CORE-56 | S1 | 新增/无原评级 | B | B | B | C | B | 未就绪（D.12 P2-CORE-56；fail） | —（仍须开工锁版本/平台探针） | 独立发现：L-N01；schema；M/L；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r1，D.12 P2-CORE-56）：B/fail；阻断 R56-01 缺少引擎数据 JSON → DataLayer 的加载…；R56-02 缺少非全局构造器与测试注入点；R56-03 验收覆盖缺口与夹具未给出；S6 pass。 |
| AND-01 | S0 | B | — | — | — | C | B | 未就绪（D.12 P2-AND-01；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；宿主锁版探针；lead修复见D.14，未重新提级。 |
| AND-02 | S2 | C | C | — | C | B | B | 未就绪（D.12 P2-AND-02；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-N01；权限合并；lead修复见D.14，未重新提级。 |
| AND-03 | S5 | C | C | — | C | C | B | 未就绪（D.12 P2-AND-03；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-I01；ActivityResult/选择器；lead修复见D.14，未重新提级。 |
| AND-04 | S5 | B | — | — | — | C | B | 未就绪（D.12 P2-AND-04；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-N01；CameraX/设备；lead修复见D.14，未重新提级。 |
| AND-05 | S2 | B | B | — | B | B | B | 未就绪（D.12 P2-AND-05；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-N01；生命周期恢复；lead修复见D.14，未重新提级。 |
| AND-06 | S2 | C | C | — | C | C | B | 未就绪（D.12 P2-AND-06；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-I01；TEE/备份迁移；lead修复见D.14，未重新提级。 |
| AND-07 | S5 | A | — | — | — | B | B | 未就绪（D.12 P2-AND-07；fail） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M；P-I05/06；笔设备；lead修复见D.14，未重新提级。 |
| AND-08 | S4 | B | — | — | — | B | B | 未就绪（D.12 P2-AND-08；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-N01；通知/OEM/重启；lead修复见D.14，未重新提级。 |
| AND-09 | S2 | B | — | — | — | B | B | 未就绪（D.12 P2-AND-09；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-N01；lead修复见D.14，未重新提级。 |
| AND-11 | S7 | B | — | — | — | B | B | 未就绪（D.12 P2-AND-11；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；签名/市场/工具链；lead修复见D.14，未重新提级。 |
| AND-12 | S7 | C | C | — | C | C | C | 未就绪（D.12 P2-AND-12；fail） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M；P-N01；真机/模型；lead修复见D.14，未重新提级。 |
| AND-13 | S2 | B | B | — | B | B | C | 未就绪（D.12 P2-AND-13；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-N03；输入法/系统栏；lead修复见D.14，未重新提级。 |
| WIN-01 | S0 | B | — | B | B | C | B | 未就绪（D.12 P2-WIN-01；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-N04；工具链/runner；lead修复见D.14，未重新提级。 |
| WIN-02 | S7 | C | B | B | B | B | B | 未就绪（D.12 P2-WIN-02；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-N01；Inno/AppId/签名；lead修复见D.14，未重新提级。 |
| WIN-03 | S7 | C | C | C | C | B | B | 未就绪（D.12 P2-WIN-03；fail） | V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M；P-I05；P-N01；恢复联测；lead修复见D.14，未重新提级。 |
| WIN-04 | S5 | B | — | — | — | B | C | 未就绪（D.12 P2-WIN-04；fail） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M；P-N02；P-I01；HEIF/HEVC；帧预算；lead修复见D.14，未重新提级。 |
| WIN-05 | S5 | B | — | — | — | B | C | 未就绪（D.12 P2-WIN-05；fail） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M；P-N02/07；Office/剪贴板；lead修复见D.14，未重新提级。 |
| WIN-06 | S2 | B | B | B | B | B | B | 未就绪（D.12 P2-WIN-06；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-I05；单实例/双DPI/退出；lead修复见D.14，未重新提级。 |
| WIN-07 | S2 | B | — | — | — | C | B | 未就绪（D.12 P2-WIN-07；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-I01；DPAPI/ACL跨用户；lead修复见D.14，未重新提级。 |
| WIN-08 | S5 | B | — | — | — | B | B | 未就绪（D.12 P2-WIN-08；fail） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M；P-I05/06；笔/输入法；lead修复见D.14，未重新提级。 |
| WIN-09 | S4 | B | B | B | B | B | B | 未就绪（D.12 P2-WIN-09；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-I01；Explorer/托盘/自启；lead修复见D.14，未重新提级。 |
| WIN-10 | S2 | B | — | — | — | B | B | 未就绪（D.12 P2-WIN-10；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-N01；静态代理；lead修复见D.14，未重新提级。 |
| WIN-12 | S7 | B | — | — | — | B | B | 未就绪（D.12 P2-WIN-12；fail） | V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M；证书/PE/制品；lead修复见D.14，未重新提级。 |
| WIN-13 | S7 | C | C | C | B | C | C | 未就绪（D.12 P2-WIN-13；fail） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M；P-N01；跨端/设备/模型；lead修复见D.14，未重新提级。 |
| WIN-14 | S5 | B | — | — | — | B | C | 未就绪（D.12 P2-WIN-14；fail） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 独立发现：M；P-N06；P-I05；真实IME；lead修复见D.14，未重新提级。 |
| WIN-15 | S2 | C | C | — | C | B | B | 未就绪（D.12 P2-WIN-15；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；P-I05；UIA/标题栏/笔/双DPI；lead修复见D.14，未重新提级。 |
| WIN-16 | S7 | 新增/无原评级 | B | C | B | B | B | 未就绪（D.12 P2-WIN-16；fail） | —（仍须开工锁版本/平台探针） | 独立发现：M；500行规模待证；P-N01；恢复；lead修复见D.14，未重新提级。 |
| CORE-57 | S0 | 新增/无原评级 | — | — | — | B | B | 未就绪（D.12 P2-CORE-57；pending） | 按依赖闭包继承外部门槛 | 独立发现：L-N07；M/L；lead修复见D.14，未重新提级。 CO-18：pack 间接依赖改为只收定义块，contracts/附录A去噪规则写入接口契约与验收；实际规模约700行超阈值待拆卡决定；lead修订后未复检，不改等级。 CO-20：规模口径改为不计测试，按 pack.mjs 实际改为约420行，超阈值解除；layout/split/split-tests 归属待定。 |
| CORE-58 | S2 | 新增/无原评级 | — | — | — | C | C | 未就绪（D.12 P2-CORE-58；fail） | 按依赖闭包继承外部门槛 | 独立发现：L-I05；M/L；lead修复见D.14，未重新提级。 |
| CORE-59 | S2 | 新增/无原评级 | — | — | — | C | C | 未就绪（D.12 P2-CORE-59；fail） | 按依赖闭包继承外部门槛 | 独立发现：L-N02；L-I06/09；M/L；lead修复见D.14，未重新提级。 |
| CORE-60 | S3 | 新增/无原评级 | — | — | — | B | B | 未就绪（D.12 P2-CORE-60；pending） | 按依赖闭包继承外部门槛 | 独立发现：M/L/H；L-N04；lead修复见D.14，未重新提级。 |
| CORE-61 | S3 | 新增/无原评级 | — | — | — | B | B | 未就绪（D.12 P2-CORE-61；fail） | 按依赖闭包继承外部门槛 | 独立发现：M/L/H；草稿schema；lead修复见D.14，未重新提级。 CO-17附带：迁移文件序号0038改为0061（取归属卡编号）；lead修订后未复检，受影响条目须由非作者复检，不改等级。 v5.3.4整卡复核（2026-10-21，rev-r2；s6-c，D.12 P2-CORE-61）：B/fail；阻断 F-01 三个 op 均 call 与 Store 单写者事务及 C…；F-02 校验错误码未定义；F-03 测试方案仅一条；S6 pass。 |
| CORE-62 | S2 | 新增/无原评级 | — | — | — | C | B | 未就绪（D.12 P2-CORE-62；pending） | 按依赖闭包继承外部门槛 | 独立发现：M/L；完整消费者确认；lead修复见D.14，未重新提级。 |
| CORE-65 | S2 | 新增/无原评级 | — | — | — | C | B | 未就绪（D.12 P2-CORE-65；pending） | 按依赖闭包继承外部门槛 | 独立发现：M/L；生命周期确认；lead修复见D.14，未重新提级。 |
| CORE-63 | S2 | 新增/无原评级 | — | — | — | B | B | 未就绪（D.12 P2-CORE-63；pending） | 按依赖闭包继承外部门槛 | 独立发现：M/L；L-N04；lead修复见D.14，未重新提级。 |
| CORE-64 | S5 | 新增/无原评级 | — | — | — | B | B | 未就绪（D.12 P2-CORE-64；pending） | 按依赖闭包继承外部门槛 | 独立发现：M/L/H；平台输入/真机；lead修复见D.14，未重新提级。 |
| CORE-66 | S6 | 新增/无原评级 | — | — | — | C | B | 未就绪（D.12 P2-CORE-66；fail） | 按依赖闭包继承外部门槛 | 独立发现：快照分批协议缺失；H/M/L；lead修复见D.14，未重新提级。 v5.3.4整卡复核（2026-10-21，rev-r2；s6-c2，D.12 P2-CORE-66）：B/fail；阻断 F-01（高）快照内容与分片格式无定义（明文序列化、实体范围、分片边…；F-04（高）轮换重入队经 enqueue_outbox 会写新字段…；F-02 FFI 段新旧协议并存；F-03 路径校验无 staging 根输入；S6 pass。CO-22 后待复检。 |
| CORE-67 | S0 | 新增/无原评级 | — | — | — | C | C | 未就绪（D.12 P2-CORE-67；fail） | 按依赖闭包继承外部门槛 | 独立发现：E-N机器契约；L-N07；lead修复见D.14，未重新提级。 |
| CORE-68 | S6 | 新增/无原评级 | — | — | — | B | B | 未就绪（D.12 P2-CORE-68；fail） | 按依赖闭包继承外部门槛 | 独立发现：M/L；Envelope消费者；lead修复见D.14，未重新提级。 CO-16：新增to_canonical_json规范JSON；lead修订后未复检，受影响条目须由非作者复检，不改等级。 v5.3.4整卡复核（2026-10-21，rev-r2；s6-b，D.12 P2-CORE-68）：B/fail；阻断 F-01（高）边界校验无 API（无 validate/from_j…；F-04 entity_id=UUID 与 CORE-26 sett…；F-03 测试方案过薄且向量未创建；g 位外部前提缺 sha2/base64；S6-CORE-68-01 PushResult/PullPage …；S6 pass。 |
| AND-14 | S3 | 新增/无原评级 | — | — | — | B | B | 未就绪（D.12 P2-AND-14；fail） | 按依赖闭包继承外部门槛 | 独立发现：M；P-N05；URI接收方；P-I06；lead修复见D.14，未重新提级。 |
| CORE-69 | S0 | — | — | — | — | C | B | 未就绪（D.12 P2-CORE-69；pending） | 按本卡外部前提 | 独立发现：M/L；词法子集/消费者；lead修复见D.14，未重新提级。 |
| CORE-70 | S0 | — | — | — | — | C | C | 未就绪（D.12 P2-CORE-70；fail） | 按本卡外部前提 | 独立发现：L-N05；M/L；lead修复见D.14，未重新提级。 |
| CORE-71 | S0 | — | — | — | — | C | C | 未就绪（D.12 P2-CORE-71；fail） | 按本卡外部前提 | 独立发现：L-N06；M/L；lead修复见D.14，未重新提级。 |
| CORE-72 | S5 | — | — | — | — | C | B | 未就绪（D.12 P2-CORE-72；pending） | 按本卡外部前提 | 独立发现：M/L；DDL/运维账号；lead修复见D.14，未重新提级。 |
| CORE-73 | S1 | — | — | — | — | C | B | 未就绪（D.12 P2-CORE-73；pending） | 按本卡外部前提 | 独立发现：L-N01；M/L；lead修复见D.14，未重新提级。 |
| CORE-74 | S0 | — | — | — | — | C | B | 未就绪（D.12 P2-CORE-74；pending） | 按本卡外部前提 | 独立发现：M/L；ABI头/注册表/标签；lead修复见D.14，未重新提级。 |
| AND-15 | S2 | — | — | — | — | C | C | 未就绪（D.12 P2-AND-15；fail） | 按本卡外部前提 | 独立发现：P-N01；3warnings；UIAutomator；lead修复见D.14，未重新提级。 |
| WIN-17 | S2 | — | — | — | — | C | C | 未就绪（D.12 P2-WIN-17；fail） | 按本卡外部前提 | 独立发现：P-N01；4warnings；UIA/锁版/交互桌面；lead修复见D.14，未重新提级。 |
| CORE-75 | S0 | — | — | — | — | C | C | 未就绪（D.12 P2-CORE-75；fail） | 按本卡外部前提 | 独立发现：L-N04/07；L-I09；lead修复见D.14，未重新提级。 |
| CORE-76 | S0 | — | — | — | — | C | B | 未就绪（D.12 P2-CORE-76；fail） | 按本卡外部前提 | 独立发现：L-N03；M/L；lead修复见D.14，未重新提级。T1-F10已补状态表头/行宽校验，须重新整卡复核。 v5.3.4整卡复核（2026-10-21，rev-r1，D.12 P2-CORE-76）：B/fail；阻断 R76-01 验收覆盖缺口：audit.mjs 与 validate…；R76-02 current.mjs 接口签名与文件约定缺失；S6 pass。 |
| CORE-77 | S1 | — | — | — | — | — | B | 未就绪（D.12 P2-CORE-77；fail） | —（沿用CORE-05、CORE-08的外部前提） | 复检B/fail（reviewer-core77-r2，D.12 P2-CORE-77复检）：N-01 instantiate跨修订协议（高，CO-13）与P-01 CORE-09/11作者确认缺失为阻断；N-02～N-06中（CO-13/CO-14）；首检reviewer-core77 B/fail的F-01/02/05/07/14已闭合、其余部分闭合；修订须重新生成材料并由非作者复检。 CO-13/14：按P2-CORE-77复检N-01～N-12修订（instantiate_all/instantiate_types跨来源协议、to_text文法、DX字面序列、fresh上界、外部前提、规模400）；材料226433/4；lead修订后未复检，受影响条目须由非作者复检，不改等级。 v5.3.4整卡复核（2026-10-21，rev-r1，D.12 P2-CORE-77）：B/fail；阻断 R77-01 CORE-08 未声明 Rational/Dimens…；P-01 CORE-09/CORE-11 作者调用方确认缺失；S6 pass。 |
| CORE-78 | S6 | — | — | — | — | — | B | 未就绪（D.12 P2-CORE-78；pending） | 按依赖闭包继承（CORE-13） | D.14.5新增；首次独立复核B/fail（reviewer-core78-fresh，D.12 P2-CORE-78）：F-01/F-02/F-03高与P-01 CORE-26/66作者确认缺失为阻断，见CO-15～17；修订后须重新生成材料并由非作者复检。 CO-15/16/17：按P2-CORE-78 F-01～F-14修订（读写均接收WriteTx、至多一个批次、Stale作废、重复结算良性、长度前缀存储、外部前提、规模210）；材料242339/4；lead修订后未复检，受影响条目须由非作者复检，不改等级。 v5.3.4整卡复核（2026-10-21，rev-r2；s6-b，D.12 P2-CORE-78）：B/pending；复核人未列阻断，consumerConfirmation 缺（CORE-26/66 作者确认未取得）；S6 pass。CO-22 后待复检。 |

### D.10.1 v5.3.3当前阻断与接续

本节替换旧P1接续摘要；历史原结论见D.13，当前106卡独立记录见D.12/D.14。所有卡未就绪，lead一轮修复不追认独立通过。

- CORE-03/65已定义profile_handle、显式会话与密钥快照；34个S0～S2 op有设计ready schema，105个后期op仍pending；CORE-66快照分批协议、CORE-21随机输入、CORE-26密文重发字段/收敛、CORE-27恢复模式/格式、CORE-31内部纯函数输入、CORE-32包装删除DDL等仍有具体缺口，由相应owner先修契约。
- generation查询/等待与缓存声明输入已补，mark_unavailable返回Result、耗尽/可用性与异步Installer时序已统一；这替代旧“查询未定义/暂禁缓存”的说法。实际实现、全量消费确认及故障向量执行仍待完成。
- CORE-41已拆CORE-69/70/71/74，另75预分配、76统计/证据；覆盖率LCOV口径及阈值已写，真实门禁实现/锁版尚未齐。CORE-09的500+150行尚未拆卡；CORE-32/66、WIN-16等规模可行性仍需落实，不能用机械500行上限掩盖。
- AND-15/WIN-17已定义fixture构建/制品和run_id/boot握手，未实现或执行。Android锁版ActivityResult/权限/FlutterFragmentActivity，Windows HEIF/HEVC/Office/UIA/输入设备/交互桌面仍外部门槛。Q41已撤销应用锁/生物识别/Hello/防截屏，不恢复。
- 材料按完整直接契约/$ref/manifest收集后仍多数超80000；最终数量见v5.3.3-audit.json。分类warning未逐条语义关闭，全部闭包与直接消费作者确认未完成；分段和工具0错误不能关S6。
- tough在线适配、真实内容/审校/模型/训练数据许可、发布许可、实名负责人、账号/域名/证书/托管与设备矩阵仍需甲方及owner提供。Q32～40待确认，Q33确认后同步SELECT；三类真实编码试点待S0前提闭合后执行。
- v5.3.2交付报告/audit是历史标版快照，不覆盖；v5.3.3证据保留在SADD/reports/v5.3.3-*，v5.3.4当前证据另存SADD/reports/v5.3.4-*（独立复核JSON仍为v5.3.3-reviews.json，因复核列未变；2026-10-21 起其中29条为v5.3.4整卡复核结果，见D.12.1）。
- T1后续（2026-10-20，见D.14.5）：CORE-21随机端口、CORE-32 Purged数据模型、CORE-26批次持久化、CORE-27闭包与字节协议、CORE-66目录分片、CORE-30扩展名/取消已按契约变更单修订，CORE-09已拆出CORE-77；上文对应阻断与“CORE-09未拆卡”为历史记录，以本条与D.14.5为准。这些修订未经独立复核，不提升任何评级。

## D.11 v5.3 复核与 v5.3.1 修订记录（2026-10-20）

2026-10-20 对 v5.3 做了五份复核（core-a、core-b、core-c、plat-win、core-ui，报告在本地 temp/verify/，只读），随后各修订者按报告修订并写处理记录（temp/verify/fix-core-a.md、fix-core-b.md、fix-core-c.md、fix-plat-win.md、fix-core-ui.md）。本节按来源报告分组汇总，说明从略，以处理记录为准；“处理方”是实际修改者。处理记录共 112 行：已修订 97、转P1 5、部分修订 6、转他人处理 2、不采纳 2（同一条目由多人分段处理时各计一行）。v5.3.1 新增 ADR-V5-32～34（修订方决定）与 Q35～Q37；无新增或拆分模块卡。§D.10 第6列据此调整，仍未授予任何卡“就绪”。

### 来源：core-a 复核报告

| 来源（报告:编号） | 严重度 | 结论 | 落点 | 处理方 |
| --- | --- | --- | --- | --- |
| core-a:A-1 残留 / N1 | 高 | 已修订 | 01 CORE-12 范围、FontData 注释、Glyph.font、DisplayList.font_ids、glyph_outline、op 行、TYPESET_NO_FONT、验收 [R01]；CORE-56 | core-a |
| core-a:N2 | 中 | 已修订 | 01 CORE-56 Rust 契约、叠加规则、发布规则、错误表；CORE-14/15 推送者 | core-a |
| core-a:N3 / A-2 残留 | 中 | 已修订 | 01 CORE-56 op 表（engine.check、calc.evaluate、calc.solvable_targets、typeset.layout、typeset.glyph_outlines）；CORE… | core-a |
| core-a:N4 | 中 | 已修订 | 01 CORE-56 引擎数据格式；CORE-02 共享格式表新增“引擎数据 JSON”行；CORE-16 units/notation/constants/fonts 行 | core-a |
| core-a:N5 | 中 | 已修订 | 01 CORE-18 抽样参数 | core-a |
| core-a:N6 / A-13 | 低 | 已修订 | 01 CORE-17 实现约束；附录A ADR-V5-29 | core-a |
| core-a:N7 / lead:pack_meta.db 回滚 | 中 | 已修订 | 03 WIN-16 路径条；01 CORE-15 高水位段与验收 [R30] | core-a |
| core-a:N8 | 低 | 已修订 | 01 CORE-56 EngineContext 与实现约束 | core-a |
| core-a:N9 / A-4 残留 | 低 | 已修订 | 01 CORE-05 | core-a |
| core-a:A-4 残留（非模板卡 template_id） | 低 | 已修订 | 01 CORE-05 ID 规则 | core-a |
| core-a:A-5 残留 | 低 | 已修订 | 01 CORE-14 错误表（7 个 LIB 码）；CORE-37/38/54 改为引用表 | core-a |
| core-a:A-6 残留 | 低 | 已修订 | 01 CORE-08 op 行、CORE-56 范围（ops/units.rs）、CORE-14（ops/units_user.rs，§3 与 README §8.6 同步） | core-a |
| core-a:A-7 残留 | 中 | 已修订 | 01 CORE-14 UnitRepo | core-a |
| core-a:A-8 残留 | 中 | 已修订 | 01 CORE-17 srs.generate、EventFlags、CardSchedule、FS-04、实现约束；README §6.1 Q35 | core-a |
| core-a:A-9 残留 | 高 | 已修订（方案调整） | 01 CORE-15 高水位段、验收 [R30] | core-a |
| core-a:A-10 残留 | 高 | 已修订 | 01 CORE-05 pack_cache_revision_id；CORE-14 PackFormulaEntry、formula_item 新列、FTS 触发器；CORE-16 formula_items con… | core-a |
| core-a:A-11 残留 | 低 | 已修订 | 01 CORE-14 验收 [R11] | core-a |
| core-a:N7 / core-b:N-10 / core-c:VC-N04 | — | 不重复处理 | — | plat-win |

### 来源：core-b 复核报告

| 来源（报告:编号） | 严重度 | 结论 | 落点 | 处理方 |
| --- | --- | --- | --- | --- |
| core-b:B-F-12 / N-06 | 中 | 已修订 | 01 CORE-15 钩子条；CORE-36 钩子表 order 10；CORE-51 installPacks 注释与 ④' 条 | core-a |
| core-b:N-04 | 中 | 已修订 | 01 CORE-13 TxStamp/stamp()；CORE-26 device_seq 句 | core-a |
| core-b:N-17 | 中 | 已修订 | 01 CORE-13 OutboxEntityCodec、enqueue_outbox<C>、验收 [R28] | core-a |
| core-b:N-11 | 低 | 已修订 | 01 CORE-56 推送者段、验收；CORE-16 | core-a |
| core-b:B-F-08 低残留（CORE-13 未提派生更新） | 低 | 已修订 | 01 CORE-13 sync_outbox 段 | core-a |
| core-b:N-03（payload 只有一个 lamport） | 中 | 转P1 / 转 core-b → v5.3.2：已覆盖（v5.3.1）（见 §D.9） | CORE-26 | core-a |
| core-b:N-01 | 高 | 已修订 | CORE-32（主）；CORE-40、47、50（消费方）；01 §3 索引、README §8.6 | core-b |
| core-b:N-02（含 B-F-04②、B-F-13 残留、Casdoor 核实） | 高 | 已修订 | CORE-22、CORE-45；附录A ADR-V5-32、§A.4.4、新 §A.4.6 | core-b |
| core-b:N-03（core-a 转交；含 B-F-03①） | 中 | 已修订 | CORE-26 | core-b |
| core-b:N-04（B-F-03③） | 中 | 已修订（core-a） | CORE-13、CORE-26 | core-b |
| core-b:N-05（B-F-04①） | 中 | 已修订 | CORE-23 | core-b |
| core-b:N-06（B-F-12） | 中 | 已修订（core-a） | CORE-51、CORE-36 | core-b |
| core-b:N-07（B-F-05） | 中 | 已修订 | CORE-19 | core-b |
| core-b:N-08（B-F-07 新问题） | 中 | 已修订 | CORE-19、CORE-20 | core-b |
| core-b:N-09（B-F-02 残留） | 中 | 已修订 | CORE-24 | core-b |
| core-b:N-10 | 中 | 已修订 | CORE-26（主）、CORE-13；附录A ADR-V5-33 | core-b |
| core-b:N-11 | 低 | 已修订（core-a） | CORE-16、CORE-56 | core-b |
| core-b:N-12 | 低 | 已修订 | CORE-21、CORE-24、CORE-25 | core-b |
| core-b:N-13（B-F-13 残留） | 低 | 已修订 | CORE-25、CORE-22、CORE-45 | core-b |
| core-b:N-14（B-F-10 残留） | 低 | 已修订 | CORE-02 §共享格式表、CORE-29、CORE-33、CORE-34、CORE-40 | core-b |
| core-b:N-15 | 低 | 已修订 | CORE-22、ADR-V5-32 | core-b |
| core-b:N-16 | 低 | 已修订 | CORE-28 | core-b |
| core-b:N-17（B-F-03②） | 中 | 已修订（core-a） | CORE-13 | core-b |
| core-b:B-F-08 残留 | 低 | 已修订 | CORE-20 | core-b |
| core-b:B-F-05 残留（Q33） | — | 转P1 → v5.3.2：转P2（见 §D.9） | README §6 Q33 | core-b |
| core-b:错误码行内清单（CORE-19/20/21/45） | 低 | 转P1 → v5.3.2：已修订（见 §D.9） | CORE-19、20、21 | core-b |
| core-b 转交：ADR-V5-34 基础上续改 | 高 | 已修订 | CORE-39、40、49、50 | core-c |
| core-b/core-c：WIN-16 进 CI、AGENTS、版本同步 | 中 | 已修订 | 同 VC-N04 | core-c |

### 来源：core-c 复核报告

| 来源（报告:编号） | 严重度 | 结论 | 落点 | 处理方 |
| --- | --- | --- | --- | --- |
| core-c:CORE-01 目录布局陈旧 | 中 | 已修订 | 01 CORE-01 目录布局 | core-a |
| core-c:VC-N03 | 中 | 已修订 | 01 CORE-37 依赖（卡、§3、依赖图 C37-->C56）、op 行、字形缓存键 | core-a |
| core-c:VC-N02 | 高 | 已修订 | CORE-36（主）；CORE-38、39、40、47、48、49、50、51 路由落点；CORE-41 DEP-5 验收；附录A ADR-V5-34；README §5 R18 | core-b |
| core-c:VC-N06 / C-F-05② | 低 | 部分修订 → v5.3.2：已修订（见 §D.9） | CORE-36 | core-b |
| core-c:VC-N01 | 高 | 已修订 | CORE-39、40、49、50（01 代码块） | core-c |
| core-c:VC-N02 | 高 | 已修订（core-b 已改，本次确认并补充） | CORE-41 规则表 DEP-5 | core-c |
| core-c:VC-N03 | 中 | 已修订（core-a） | CORE-37 | core-c |
| core-c:VC-N04 | 中 | 已修订 | CORE-41 ci.yml、外部前提、[R23]；CORE-42 bump_version 与验收；AGENTS.md | core-c |
| core-c:VC-N05 | 中 | 已修订 | CORE-55 新增 j 节 | core-c |
| core-c:VC-N06 / core-b 转交 | 低 | 已修订 | CORE-38、39、47、48 验收 | core-c |
| core-c:VC-N07 | 低 | 不采纳（改为写明用途） | CORE-55 | core-c |
| core-c:VC-N08 | 低 | 已修订（core-a） | CORE-01 | core-c |
| core-c:VC-N09 | 低 | 已修订 | CORE-54、CORE-51 规模与契约 | core-c |
| core-c:VC-N10 | 低 | 已修订 | CORE-41 | core-c |
| core-c:C-F-01（部分解决的剩余部分） | 高 | 已修订 | 同 VC-N01、VC-N02；CORE-01:475 | core-c |
| core-c:C-F-01 子项 DEP-6 不可机械化 | 中 | 已修订 | CORE-41 规则表 | core-c |
| core-c:C-F-03 残留（FML_THEME_MISSING） | 低 | 已修订 | CORE-55 b 节说明；CORE-41 ERR-2 | core-c |
| core-c:C-F-05 残留（DesignGallery、CORE-28） | 中 | 已修订 | CORE-55 | core-c |
| core-c:AN-F02 残留（诊断通道是否进 release） | 低 | 已修订（范围外） | 02 AND-05 | core-c |

### 来源：plat-win 复核报告

| 来源（报告:编号） | 严重度 | 结论 | 落点 | 处理方 |
| --- | --- | --- | --- | --- |
| plat-win:N9 | 低 | 已修订（CORE-36 部分） | CORE-36 | core-b |
| plat-win:N1/N2 | 高/中 | 不在范围 | WIN-16 | core-b |
| plat-win:N1 | 高 | 已修订 | WIN-16 状态表、命令、实现约束、验收；WIN-03 confirmOpened | plat-win |
| plat-win:N2 | 中 | 已修订 | WIN-16 互斥条、状态表 | plat-win |
| plat-win:N3 | 中 | 已修订 | WIN-16 文本格式/journal/manifest/管道条；WIN-06 单实例 | plat-win |
| plat-win:N4 | 中 | 已修订 | WIN-02 [Code]、L288 条；WIN-16 `--register-install`、安装模式 | plat-win |
| plat-win:N5 | 中 | 已修订 | WIN-02 [Files]；WIN-16 构建条 | plat-win |
| plat-win:N6 / W-9 残留 | 低 | 已修订 | WIN-06 启动参数、TrayPresence、installWindowsShell；WIN-09 接口副本与钩子注释；01 CORE-36 首帧协议 | plat-win |
| plat-win:N7 | 低 | 已修订 | WIN-16 安装模式；WIN-03 安装/钩子；WIN-02 L288 条 | plat-win |
| plat-win:N8（WIN-01 旧引用） | 低 | 已修订 | WIN-01 不包含 | plat-win |
| plat-win:N8（WIN-12 旧引用） | 低 | 已修订 | WIN-12 实现约束 MSIX 条 | plat-win |
| plat-win:N8（WIN-13 远程桌面） / W-3 残留 | 低 | 已修订 | WIN-13 环境矩阵 | plat-win |
| plat-win:N8（WIN-13 依赖缺 WIN-02/03/16） | 低 | 不采纳 | — | plat-win |
| plat-win:N9 | 低 | 已修订 | WIN-03 接口注释、健康确认段、验收 | plat-win |
| plat-win:W-1 残留 | 高 | 已修订 | 同 N1 | plat-win |
| plat-win:W-2 残留 | 低 | 已修订 | WIN-16 布局块；WIN-02 布局块 | plat-win |
| plat-win:W-6 残留 | 中 | 已修订 | WIN-16 恢复行、rename 条 | plat-win |

### 来源：core-ui 复核报告

| 来源（报告:编号） | 严重度 | 结论 | 落点 | 处理方 |
| --- | --- | --- | --- | --- |
| core-ui:N1 | 高 | 已修订 | 01 CORE-01 实现约束/外部前提/验收/目录布局；01 中 7 处“版本 M0 锁定”及 CORE-02（PyYAML）、CORE-03（ffigen）、CORE-06（cargo-fuzz）与 tiny-s… | core-a |
| core-ui:N6 | 中 | 部分修订 → v5.3.2：已修订（见 §D.9） | 01 CORE-16 formula_items（distractors 元素 schema、reviewed_at 格式与毫秒换算） | core-a |
| core-ui:N8（卡内引用 ADR） | 低 | 部分修订 → v5.3.2：已修订（见 §D.9） | 01 CORE-56 目标引用 ADR-V5-26 | core-a |
| core-ui:N6 | 中 | 已修订 | CORE-19 | core-b |
| core-ui:N7 | 中 | 部分修订 → v5.3.2：部分修订（见 §D.9） | CORE-35；附录C（lead） | core-b |
| core-ui:N9 安装器 C++ 构建单元不在构建清单 | 低 | 已修订（范围外） | README §8.5a；CORE-41 | core-c |
| core-ui:CORE-55 DesignGallery 定义 | 中 | 已修订 | CORE-55 j | core-c |
| core-ui:CORE-55 DesignWarmup 不是完整契约 | 中 | 已修订 | CORE-55 h、j；CORE-36 启动钩子表 | core-c |
| core-ui/附录D:CORE-55 单卡规模超限 | 中 | 部分修订（转P1观察） → v5.3.2：已修订（见 §D.9） | CORE-55 f、规模；01 §3 索引 | core-c |
| core-ui:N8（WIN-16 未引用 ADR-V5-31） | 低 | 已修订 | WIN-16 接口契约首句、不包含、实现约束 | plat-win |
| core-ui:WIN-16 会话材料约 120k | 中 | 转P1 → v5.3.2：部分修订（见 §D.9） | — | plat-win |
| core-ui:U-F01 残留（闭包外引用） | 高 | 部分修订 → v5.3.2：部分修订（见 §D.9） | README §8.1 第3、6项；附录D §D.12 | core-ui |
| core-ui:U-F03 残留（§6.1 空行） | 中 | 已修订（core-a） | README §6.1 | core-ui |
| core-ui:U-F07 残留（工具链未同步） | 阻断→高 | 已修订（core-a） | CORE-01、AND-01、WIN-01；README §8.3 S0 行；ADR-V5-15 | core-ui |
| core-ui:U-F09 残留（附录D 就绪口径） | 高 | 已修订 | 附录D §D.1、D.2、D.9～D.12；README §8.5.1 | core-ui |
| core-ui:U-F12 残留（用户易混组） | 中 | 已修订（core-b、core-a） | CORE-16、CORE-19 | core-ui |
| core-ui:U-F15 残留（范围、fake、负责人） | 阻断→中 | 已修订 | CORE-35（core-b）；附录C §C.5.1；README §6.1 Q37 | core-ui |
| core-ui:N1 | 高 | 已修订（core-a、plat-win） | CORE-01、AND-01、WIN-01；README §8.3 | core-ui |
| core-ui:N2 | 中 | 已修订 | README §8.2 | core-ui |
| core-ui:N3 | 中 | 已修订（core-a） | README §6.1 | core-ui |
| core-ui:N4 | 高 | 已修订 | README §8.5（h 引用）、新 §8.5.1、§8.3 S0 说明；附录D §D.12 | core-ui |
| core-ui:N5 | 中 | 已修订 | 附录D §D.10 | core-ui |
| core-ui:N6 | 中 | 已修订（core-a、core-b） | CORE-16、CORE-19 | core-ui |
| core-ui:N7 | 中 | 已修订 | CORE-35（core-b）；附录C §C.5.1；README Q37 | core-ui |
| core-ui:N8 | 低 | 已修订 | 附录A §A.4 说明与 A.4.1/A.4.2 模块卡列；CORE-56（core-a）、WIN-16（plat-win） | core-ui |
| core-ui:N9 | 低 | 已修订（core-c） | README §8.5a；CORE-41 CI；AGENTS | core-ui |
| core-ui:N10 | 低 | 已修订 | 附录A §A.4 状态说明、A.4.2 标题、V5-26～31 状态；README §6.2 | core-ui |
| core-ui:N11 | 低 | 已修订 | 附录D §D.10 说明 | core-ui |
| core-ui:N12 | 高 | 转P1（暂行做法已写） → v5.3.2：部分修订（见 §D.9） | README §8.1 第6项；附录D §D.10.1 | core-ui |

### 来源：其他（附录D/跨报告）

| 来源（报告:编号） | 严重度 | 结论 | 落点 | 处理方 |
| --- | --- | --- | --- | --- |
| （自查）CORE-13 错误码散文 | 低 | 已修订 | 01 CORE-13 错误表（6 码，四列）；CORE-32 删除重复 STORE_DISK_FULL 行改为文字引用 | core-a |

## D.12 整卡语义复核记录

2026-10-20串行独立复核。✓通过所核部分、△部分/前提未完成、×不满足；a～g和S1～S6顺序严格按README8.5/8.5.1。下列为独立复核时结论；lead已修一轮但未再次独立复检，均不授予就绪。最终材料数见D.13材料清单，数字更新不等于复核人重读或签字。

| 序号 | 卡 | 复核人/日期 | 复核时材料 / 分段 | a～g | S1～S6 | 发现、处理及调用方确认 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CORE-01 | review_core_a / 2026-10-20 | 78255 / 1；S6未全关闭 | △×✓××✓△ | ✓××△△△ | PA02移除不存在Clock；依赖/首卡验收及锁版证据待复检 | 不通过 |
| 2 | CORE-02 | review_core_a / 2026-10-20 | 55842 / 1；S6未全关闭 | ✓✓××✓✓△ | ✓×✓△△△ | PA01命名空间与fatal冲突已改；真实注册表/生成物与消费确认未完成 | 不通过 |
| 3 | CORE-03 | review_core_a / 2026-10-20 | 54024 / 1；S6未全关闭 | △✓××△✓△ | ✓×△△△△ | PA03 const/dispose已改；PB调用方不签完整可消费，handle/业务schema阻断；非产品测试通过 | 不通过 |
| 4 | CORE-04 | review_core_a / 2026-10-20 | 88189 / 2；S6未全关闭 | △×✓××✓△ | ✓××△△△ | Fake/ScreenSecurity/Unsupported冒烟已改；PB/PC消费接缝仅局部核对，平台线格式尚无实现证据 | 不通过 |
| 5 | CORE-41 | review_core_c / 2026-10-20 | 99469 / 2；11闭包warning及符号warning | △△△△△待最终对账△ | ✓△△×△△ | PC07表格已改；PC09规模阻断转P2；最终机械追踪0不追认独立f项通过 | 不通过 |
| 6 | AND-01 | review_core_a / 2026-10-20 | 72032 / 1；warnings未关闭 | ✓△△××✓△ | ✓××△△△ | PAN01/02宿主/冒烟已改；锁版编译、认证/设备/完整材料仍待验证 | 不通过 |
| 7 | WIN-01 | review_core_b / 2026-10-20 | 114194 / 2；17warnings、缺6工程锁定文件 | ✓△✓×△✓△ | ✓××△△△ | PW01冒烟已改；复核人明确未读完全部114194字符，S6未通过，不能写整卡完成 | 不通过 |
| 8 | CORE-67（新增S0） | review_core_a / 2026-10-20 | 24884 / 1；S6未全关闭 | △✓△×△✓△ | ✓×△△△△ | 生成子集/ready/pending已补；真实业务schema和生成器未交付，H6阻断 | 不通过 |
| 9 | CORE-57（新增S0） | review_core_c / 2026-10-20 | 最终数见D.13 | 未逐项整卡复核 | 未逐项整卡复核 | 独立局部等级B；工具回归通过不代替a～g/语义签字 | 未完成，不授予就绪 |

### D.12.1 P2独立复核（修复前基线2c04125）

以下106行来自三位非本范围修订者的串行只读复核；13旗标P/F/?分别pass/fail/pending。材料列是复核输入快照，最终pack结果另列D.14/审计，不能声称复核人已读最终闭包。公共consumerConfirmation均null。lead身份核对：三位reviewer未参与本轮对应范围修订，只读报告由lead保存，未启动第二轮。 2026-10-21 起，CORE-01、02、05、08、09、11、13、17、21、23～27（不含22）、30、31、32、36、40、41、46、47、56、61、66、68、76、77、78 共 29 行就同一 record 更新为 v5.3.4 整卡复核与 S6 补读结果：复核人列为“整卡复核人；S6 补读人”（同一人读完 S6 时只写一人），材料列为复核时材料值（CO-22 之前），S6 位按补读判定、其余位按整卡复核判定，成员改判建议只写入理由；报告在本地 temp/review/（未入库），汇总见 temp/review/S6补读-核对与汇总.md。29 张等级 B26/C3、结论 fail28/pending1，无 pass，不授予就绪。

| 记录 | 卡 | 复核人 / 日期 | 复核输入字符 / 段 | a～g | S1～S6 | 发现、处理及调用方确认 | conclusion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P2-CORE-01 | CORE-01 | rev-r1；s6-a / 2026-10-21 | 88102 / 2 | PPPFFPP | PPP?PP | 复检（v5.3.4，rev-r1/CORE-01复核.md、s6-a/CORE-01-S6补读.md）：主要阻断 R01-01 members 含 server 与本卡验收冲突（S0 时 server 不存在）；R01-02 交付文件清单缺失，deny.toml/lints 等 AGENTS.md 要求的检查无卡拥有；S6-CORE-01-01 DEP-1 允许表、dep6_symbols.txt、platform-check-patterns.json 三份机器可读策略文件无定义者；S6 补读（s6-a）pass，新增中1/低2（S6-CORE-01-01～03）；成员建议 c 位 P→△/F（只记建议，正式位仍 P）；前次：C/fail（/root/p2_core_early 86554/2，E-I01；首卡验收依赖后卡，锁版与材料超量） | fail |
| P2-CORE-02 | CORE-02 | rev-r3；s6-a / 2026-10-21 | 63027 / 1 | PPPFPPP | PFFPPP | 复检（v5.3.4，rev-r3/CORE-02-复核.md、s6-a/CORE-02-S6补读.md）：主要阻断 R3-02-01 FFI/HTTP 适配层 with_trace 填入 trace_id 的义务无卡接下；R3-02-02 生成物 API 欠规格（变体命名、未知 code 反序列化）；R3-02-03 Dart FmlException.fromJson 与 DiagnosticDto 来源未定；R3-02-04 所有权两处登记；按各卡错误表预登记会漏 FFI_/CONTENT_/GRADE_ 等 16 个码；S6 补读（s6-a）pass，新增低3（S6-CORE-02-01～03）；无高级发现；前次：B/pending（/root/p2_core_early 60605/1，E-N03；机器错误集合、消费确认、完整材料） | fail |
| P2-CORE-03 | CORE-03 | /root/p2_core_early / 2026-10-20 | 101772 / 2 | PPPPPP? | PPP?P? | E-N01～04；handle改善，FFI规模与机器契约待闭合。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-04 | CORE-04 | /root/p2_core_early / 2026-10-20 | 133394 / 2 | PPFFFP? | PFF?P? | E-I13；同步Installer与异步editor不一致。；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-05 | CORE-05 | rev-r1 / 2026-10-21 | 105761 / 2 | PPPFFPF | PPP?PP | 复检（v5.3.4，rev-r1/CORE-05复核.md）：主要阻断 R05-01 核心类型 derive/serde 约定缺失（仅 MathKind 完整）；R05-02 外部前提缺 NFC、SHA-256、JSON Schema 校验库；R05-03 ID/seed 函数无覆盖且期望值非独立；S6 由整卡复核人读完材料，S4 记 pending；前次：C/fail（/root/p2_core_early 116148/2，E-N01/02/04；正文、黄金向量、schema 不一致） | fail |
| P2-CORE-06 | CORE-06 | /root/p2_core_early / 2026-10-20 | 89315 / 2 | PPPPPP? | PPP?P? | export漏码；schema/消费确认及规模待证。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-07 | CORE-07 | /root/p2_core_early / 2026-10-20 | 79929 / 2 | PPPPPP? | PPPPP? | notation漏码；完整材料和消费确认未完成。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-08 | CORE-08 | rev-r1 / 2026-10-21 | 88553 / 2 | PPPFFPF | PFF?PP | 复检（v5.3.4，rev-r1/CORE-08复核.md）：主要阻断 R08-01 Rational/Dimension/DimensionFull/Unit/UnitKind/QuantityKind/UnitDefinition 未声明 serde 与 derive；R08-02 缺 UnitRegistry/UnitRegistryMut 的具体实现与构造符号；R08-03 π/角度换算无法用 Rational 精确表示，验收无期望值；R08-04 UNIT_AFFINE_MISUSE 无触发入口，温度点相加被拒无可调用 API；S6 由整卡复核人读完材料，S4 记 pending；前次：B/pending（/root/p2_core_early 98093/2，units 错误为空；AST 机器修正与确认） | fail |
| P2-CORE-09 | CORE-09 | rev-r1 / 2026-10-21 | 120222 / 2 | PPPFFPF | PPF?PP | 复检（v5.3.4，rev-r1/CORE-09复核.md）：主要阻断 R09-01 运算规则表未在卡内枚举；R09-02 QuantityKind 与 MathKind 的推断/传播规则缺失；R09-03 dx.yaml 输入与约定诊断映射未给出，验收不能直接落成测试；S6 由整卡复核人读完材料，S4 记 pending；前次：C/fail（/root/p2_core_early 111733/2，E-I02；500+150 行未拆卡，后拆出 CORE-77） | fail |
| P2-CORE-10 | CORE-10 | /root/p2_core_early / 2026-10-20 | 103131 / 2 | PPPPPP? | PPP?P? | 500行估算、AST/FFI机器契约需复核。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-11 | CORE-11 | rev-r1 / 2026-10-21 | 138717 / 2 | PPPFFPF | PFF?PP | 复检（v5.3.4，rev-r1/CORE-11复核.md）：主要阻断 R11-01 substitute/rank 依赖的符号反解没有公开函数；R11-02 substitute 的确定性规则缺失；R11-03 RevisionSnapshot.typed 与 Candidate.output_type 无人生成或存储；S6 由整卡复核人读完材料，S4 记 pending；前次：C/fail（/root/p2_core_early 103194/2，E-I03；排序输入不足，derive 错误为空） | fail |
| P2-CORE-12 | CORE-12 | /root/p2_core_early / 2026-10-20 | 105328 / 2 | PPPPPP? | PPP??? | AST schema、字体/工具外部门槛。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-13 | CORE-13 | rev-r2；s6-c / 2026-10-21 | 184475 / 3 | PPPPPPF | PPPPPP | 复检（v5.3.4，rev-r2/CORE-13复核.md、s6-c/CORE-13-S6补读.md）：主要阻断 F-01（高）缺全量重入队能力：OutboxEntityCodec 无实体枚举、enqueue_outbox 重推会写新字段时钟（阻断 CORE-24/26/66）；F-02 op_id/device_id 随机来源未定义；F-03 外部前提缺 uuid、serde_json、blake3 与 build.rs 构建依赖；F-04 迁移 checksum 不符、有记录无文件等规则与机器校验缺；S6 补读（s6-c）pass，新增低1；复核后 CO-22 已修订store.open 示例注明 schema_version 为夹具值，待复检；前次：B/pending（/root/p2_core_early 187505/3，STORE_BUSY 镜像遗漏，消费确认待完成） | fail |
| P2-CORE-14 | CORE-14 | /root/p2_core_early / 2026-10-20 | 171918 / 3 | PFFFFP? | PFF?P? | E-I04；标签错误条件和后阶段批次表述。；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-15 | CORE-15 | /root/p2_core_early / 2026-10-20 | 171497 / 3 | PP?F?P? | P???F? | E-I05；tough真实适配未闭合。；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-16 | CORE-16 | /root/p2_core_early / 2026-10-20 | 176161 / 3 | PPPPPP? | PPP??? | 真实内容/审校/许可、15适配与规模。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-17 | CORE-17 | rev-r4；rev-r5 / 2026-10-21 | 168268 / 3 | FPPFPPF | PFFFPP | 复检（v5.3.4，rev-r4/CORE-17-report.md、rev-r5/CORE-17-S6补读.md）：主要阻断 F-01（高）FsrsParams 持久化/同步与 params_version、rating_map_version 未定义；F-02（高）pending_choice 由谁、何时置位未定义；F-03 规模≥650 行需拆卡（含 fml-ffi 附属未计）；R5-17-01（中）generate_cards 无 template_id 入参；R5-17-02（中）CardType × RequirementLevel 映射与出卡前置条件缺；S6 补读（rev-r5）pass，新增中2/低1（R5-17-01～03）；前次：C/fail（/root/p2_core_early 173472/3，E-I06；review_event 唯一键冲突） | fail |
| P2-CORE-18 | CORE-18 | /root/p2_core_early / 2026-10-20 | 111943 / 2 | PPPPPP? | PPP??? | 类型/数值边界、判分语料、500行与确认。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-19 | CORE-19 | /root/p2_core_early / 2026-10-20 | 182846 / 3 | PPPPPP? | PPP??? | 继承17事务问题，Q33待确认。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-20 | CORE-20 | /root/p2_core_early / 2026-10-20 | 186884 / 3 | PPPPPP? | PPP??? | 17事件前提、真实试点和材料。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-21 | CORE-21 | rev-r3；s6-a / 2026-10-21 | 84884 / 2 | PPPFFP? | PFFPPP | 复检（v5.3.4，rev-r3/CORE-21-复核.md、s6-a/CORE-21-S6补读.md）：主要阻断 R3-21-01（高）SecretKey 无构造与取值接口（波及 CORE-13/23/24/26/32）；R3-21-02（高）RecoveryCode 无取文本接口，recovery_key 的 HKDF 输入未定义；R3-21-04 KV-02～05 向量无法经公开函数验证；R3-21-05 CRYPTO_KEY_VERSION_UNKNOWN 无产生函数；S6 补读（s6-a）pass，新增低4（S6-CORE-21-01～04），证实 R3-21-01/02 仍在；成员建议 g 位 ?→F/△（只记建议，正式位仍 ?）；复核后 CO-22 已修订wrap_with_params 补 rng 参数（R3-21-03）、密钥层次补 SyncSnapshot 用途，待复检；前次：C/fail（/root/p2_core_early 114877/2，E-I07；随机输入与失败返回不闭合） | fail |
| P2-CORE-22 | CORE-22 | /root/p2_core_early / 2026-10-20 | 100823 / 2 | PPPPPP? | PPP??? | Casdoor锁版、真实账号与规模。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-23 | CORE-23 | rev-r3；s6-d / 2026-10-21 | 185032 / 3 | PPPFFP? | PFFPPP | 复检（v5.3.4，rev-r3/CORE-23-复核.md、s6-d/CORE-23-S6补读.md）：主要阻断 R3-23-01（高）登记 GuardContext 的 Dart 安装点无卡拥有；R3-23-02（高）删除档案、更新 last_used_ms、set_sync_enabled 无 Rust 接口或 FFI op；R3-23-03/04 OsRandom 无注入点、create_guest/create_registered 无 rng 参数；S6-CORE-23-01（中）档案创建 op 漏列 RNG 失败透传；S6 补读（s6-d）pass，新增中1（S6-CORE-23-01）；前次：B/pending（/root/p2_core_early 187652/3，E-N04/错误镜像及消费确认） | fail |
| P2-CORE-24 | CORE-24 | rev-r3；s6-d / 2026-10-21 | 146636 / 2 | FFPFFPP | PFFFPF | 复检（v5.3.4，rev-r3/CORE-24-复核.md、s6-d/CORE-24-S6补读.md）：主要阻断 R3-24-01（高）规模不可信，远超 500 行，需拆卡（merge_guest 等）；R3-24-02（高）NewAccount 升级需更新注册表行，CORE-23 DeviceRegistry 无转换/投影接口；R3-24-03 同一 op 不能同时 call 与 submit；R3-24-04 随机/时间来源未注入；S6 fail：材料缺 CORE-05 pack_item_id/pack_template_id/card_id 定义块（证实 R3-24-08）；S6 补读（s6-d）fail：材料全部读完，但缺 CORE-05 pack_item_id/pack_template_id/card_id 定义块（证实 R3-24-08，不计新增）；复核后 CO-22 已修订补依赖 CORE-05（pack_item_id 等，对应 S6 fail 原因 R3-24-08），重生成材料已收入该定义块，待复检；前次：C/fail（/root/p2_core_early 168998/3，E-N06；撤销锁后仍保留解锁入口） | fail |
| P2-CORE-25 | CORE-25 | rev-r2；s6-b / 2026-10-21 | 79126 / 1 | PPPFPPP | PPPFPP | 复检（v5.3.4，rev-r2/CORE-25复核.md、s6-b/CORE-25-S6补读.md）：主要阻断 S6-CORE-25-01（高）BIGSERIAL 取号顺序不等于提交顺序，游标越过后提交的小序号永久漏同步；F-01 越权 404、无快照 404、无令牌 401 未给错误码；F-02 sync_envelope.body 存什么未定义；F-05 规模约 500 行无分项、疑超 500；S6 补读（s6-b）pass，新增高1/中2/低1（S6-CORE-25-01～04）；前次：B/pending（/root/p2_core_early 114016/2，26 密文重发一致性与 DB 锁版） | fail |
| P2-CORE-26 | CORE-26 | rev-r2；s6-b / 2026-10-21 | 231566 / 3 | PPPFPPP | PFPPPP | 复检（v5.3.4，rev-r2/CORE-26复核.md、s6-b/CORE-26-S6补读.md）：主要阻断 S6-CORE-26-01（高）apply_pull 缺 11 类实体的写侧应用契约、实体 JSON 形状与校验注入路径；F-01 CONFLICT 即判定整库回退与 ADR-V5-43/T-STALE 自相矛盾；F-02 负载 CBOR 无编码/解码契约；F-03 构造 Envelope 的字段映射未定义；F-04 on_epoch_changed 全量重建 outbox 无实体枚举契约；S6 补读（s6-b）pass，新增高1/中4/低3（S6-CORE-26-01～08）；成员建议 S4 P→?（待写侧契约归属与规模方案，只记建议，正式位仍 P）；复核后 CO-22 已修订补依赖 CORE-68（Envelope，F-06）、规模行改写为测试不计，待复检；前次：C/fail（/root/p2_core_early 243292/4，E-I08；密文持久字段与收敛规则缺口） | fail |
| P2-CORE-27 | CORE-27 | rev-r3；s6-d / 2026-10-21 | 188943 / 3 | FFPFFPP | PFFFPF | 复检（v5.3.4，rev-r3/CORE-27-复核.md、s6-d/CORE-27-S6补读.md）：主要阻断 R3-27-01（高）规模约 730 行，需拆卡；R3-27-02（高）Replace 删除范围表与 RESTRICT 外键及未选范围引用规则缺；R3-27-04 token 临时库为进程级全局表，与 ADR-V5-39 冲突；R3-27-05 恢复模式在 prepare/commit 两侧不一致（CORE-47）；S6 fail：材料缺 CORE-19/48 范围表列/外键/写入契约（证实 R3-27-09）；S6 补读（s6-d）fail：材料全部读完，但缺 CORE-19/48 归属的 calculation_plan、book、study_session 等范围表的列/外键/写入契约（证实 R3-27-09，不计新增），CO-22 未修；前次：C/fail（/root/p2_core_early 204615/3，E-I09；调用模式、引用闭包、格式不唯一） | fail |
| P2-CORE-28 | CORE-28 | /root/p2_core_early / 2026-10-20 | 130137 / 2 | PPPPPP? | PPP?P? | 完整依赖闭包及消费确认。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-29 | CORE-29 | /root/p2_core_early / 2026-10-20 | 107553 / 2 | PPPPPP? | PPPP?? | 识别后端前提与材料。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-30 | CORE-30 | rev-r3；s6-c / 2026-10-21 | 77885 / 1 | FFPFFP? | PFFFPP | 复检（v5.3.4，rev-r3/CORE-30-复核.md、s6-c/CORE-30-S6补读.md）：主要阻断 R3-30-02（高）核心侧无契约获知 StoreArea.staging 根目录，IMG_PATH_INVALID 无法实现；R3-30-04 预处理流水线次序与坐标系未定义；R3-30-03 QualityReport 多个字段无公式；R3-30-06 规模恰在上限且带超出再拆保留语；S6 补读（s6-c）pass，新增低1；前次：B/pending（/root/p2_core_early 65784/1，图像标定/Q、消费确认） | fail |
| P2-CORE-31 | CORE-31 | rev-r4；rev-r5 / 2026-10-21 | 152653 / 2 | PFPFFPP | PFFPPP | 复检（v5.3.4，rev-r4/CORE-31-report.md、rev-r5/CORE-31-S6补读.md）：主要阻断 F-01（高）apply_correction 缺 units 与 cancel 参数，无法重做量纲推导；R5-31-01（高）三个纯函数只收预构造 SymbolEnv，缺逐候选 bind 所需 NotationProfile 与 user_decls；F-02 fml-recognize 内编排解析/绑定与 CORE-01 规则 1 冲突；F-05 RECOG_OUTPUT_REJECTED 等错误语义无出口；S6 补读（rev-r5）pass，新增高1/低1（R5-31-01～02）；前次：C/fail（/root/p2_core_early 113143/2，E-I10；内部纯函数输入/评分边界） | fail |
| P2-CORE-32 | CORE-32 | rev-r3；s6-d / 2026-10-21 | 185304 / 3 | FFPFPPP | PFFFPF | 复检（v5.3.4，rev-r3/CORE-32-复核.md、s6-d/CORE-32-S6补读.md）：主要阻断 R3-32-01（高）gc_execute 无 Store 参数却须写库；R3-32-02（高）HistoryRepo 致 fml-recognize 与 fml-store 循环依赖；R3-32-08（高）规模恰在 500 上限且未计 fml-ffi 适配；S6 fail：材料缺 Page<T> 定义（证实 R3-32-09）；S6 补读（s6-d）fail：材料全部读完，但 HistoryRepo::list 返回的 Page<SessionSummary> 缺 Page<T> 定义（证实 R3-32-09，不计新增）；复核后 CO-22 已修订补依赖 CORE-05（Page<T>，对应 S6 fail 原因 R3-32-09），重生成材料已收入该定义块，待复检；前次：C/fail（/root/p2_core_early 182359/3，E-I11；包装删除与 DDL 冲突、归属/规模） | fail |
| P2-CORE-33 | CORE-33 | /root/p2_core_early / 2026-10-20 | 106647 / 2 | PPPPPP? | PPP??? | 运维已拆；供应商/预算fixture及规模。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-34 | CORE-34 | /root/p2_core_early / 2026-10-20 | 181972 / 3 | PPPFFP? | PFF?P? | E-I12；NS_FML_CLOUD未冻结。；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-35 | CORE-35 | /root/p2_core_early / 2026-10-20 | 153547 / 2 | PPPPPP? | PPP??? | 真实模型/运行时/许可/真机。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-36 | CORE-36 | rev-r4；rev-r5 / 2026-10-21 | 334650 / 5 | PFPFPPP | PFFPPP | 复检（v5.3.4，rev-r4/CORE-36-report.md、rev-r5/CORE-36-S6补读.md）：主要阻断 F-01（高）DefaultAccountController/TokenStore 无实现类，ProfileSessionSource 注入无契约；F-03 SYNC_NOT_AVAILABLE 的游客触发条件无人实现；F-04 errors.g.dart 不存在（CORE-02 实际生成 error_codes.g.dart 与 errors_zh.arb）；R5-36-01（中）NetworkGuard 所需 GuardContext/ConsentVerifier 在 composeApp 步骤② 无提供者；S6 补读（rev-r5）pass，新增中1/低3（R5-36-01～04）；复核后 CO-22 已修订规模 380→280（测试不计）、DEP-5 归 CORE-69 的引用改正并同步 Test，待复检；前次：C/fail（/root/p2_core_early 308845/4，E-N05/E-I13；单写、异步安装和重复注册） | fail |
| P2-CORE-37 | CORE-37 | /root/p2_core_early / 2026-10-20 | 158641 / 3 | PPFFFP? | PFF?P? | E-I13；Worker未被等待，AST机器契约。；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-38 | CORE-38 | /root/p2_core_early / 2026-10-20 | 228178 / 3 | PPPPPP? | PPP?P? | ProfileSessionSource切换失效、单写和消费确认。；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-39 | CORE-39 | /root/p2_core_late / 2026-10-20 | 273864 / 4 | P?P?PP? | P?P??F | M/L/H；L-I09；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-40 | CORE-40 | rev-r4；rev-r5 / 2026-10-21 | 239823 / 4 | PFPFPPP | PFFFPP | 复检（v5.3.4，rev-r4/CORE-40-report.md、rev-r5/CORE-40-S6补读.md）：主要阻断 F-01（高）installRecognition 构造 HistoryKeyUnlocker/RecognitionFlow 拿不到档案 scopedTo 视图（ProfileSessionSource）；F-06 规模约 370 行疑偏低；F-04/F-07 错误处理与验收只覆盖主路径；R5-40-01（中）启动钩子 50 recog.recover 为 profile 作用域 op，无重跑契约；S6 补读（rev-r5）pass，新增中1/低2（R5-40-01～03）；复核后 CO-22 已修订补依赖 CORE-59（F-03）、CLOUD_* 引用行改为定义卡、InkDocument 改为 InkStrokesDto，待复检；前次：B/pending（/root/p2_core_late 281558/4，M/L/H；L-I07/09） | fail |
| P2-CORE-41 | CORE-41 | rev-r1；s6-a / 2026-10-21 | 64805 / 1 | PPFFFPF | PPPPPP | 复检（v5.3.4，rev-r1/CORE-41复核.md、s6-a/CORE-41-S6补读.md）：主要阻断 R41-01 run_all 的 manifest、CLI 与归档格式未定义；R41-02 范围与归属表矛盾，thresholds.yaml 归属不清；S6-CORE-41-01 CORE-71 交给本卡的 core-sources.json 生成器无交付与验收；S6 补读（s6-a）pass，新增中1/低5（S6-CORE-41-01～06）；前次：C/fail（/root/p2_core_late 89438/2，L-N05/06；M/L） | fail |
| P2-CORE-42 | CORE-42 | /root/p2_core_late / 2026-10-20 | 123058 / 2 | P?PPPP? | P?P?PF | M/L；真实发布/回滚未执行；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-43 | CORE-43 | /root/p2_core_late / 2026-10-20 | 126129 / 2 | P?PPPP? | P?P?PF | M/L；真实托管/账号/轮换；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-44 | CORE-44 | /root/p2_core_late / 2026-10-20 | 84549 / 2 | P?PPPP? | P?PPPF | M/L；锁版SDK/C消费者；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-45 | CORE-45 | /root/p2_core_late / 2026-10-20 | 87164 / 2 | P?PPPP? | P?P?PF | M/L；供应商/域名；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-46 | CORE-46 | rev-r4；rev-r5 / 2026-10-21 | 170711 / 3 | PFPFPPP | PFFPPP | 复检（v5.3.4，rev-r4/CORE-46-report.md、rev-r5/CORE-46-S6补读.md）：主要阻断 F-01（高）紧凑 JSON 字节约束与 ApiClient.call(json:) 不闭合（无已编码字节入口）；F-02 依赖缺 CORE-03 与 CORE-78；F-06 游客/未开启同步三处行为不一致（disabled、SYNC_DISABLED、SYNC_NOT_AVAILABLE）；R5-46-01（中）协调器无 ProfileSessionSource，profile 作用域调用无句柄；S6 补读（rev-r5）pass，新增中1/低2（R5-46-01～03）；复核后 CO-22 已修订补依赖 CORE-03、CORE-78（F-02），待复检；前次：B/pending（/root/p2_core_late 240396/4，M/L/H；66 分批协议） | fail |
| P2-CORE-47 | CORE-47 | rev-r4；rev-r5 / 2026-10-21 | 213173 / 3 | PFPFPPP | FFFFPP | 复检（v5.3.4，rev-r4/CORE-47-report.md、rev-r5/CORE-47-S6补读.md）：主要阻断 F-01（高）BackupVm.pickAndPrepare 无 mode，与 CORE-27 prepare_restore 签名不闭合；F-02（高）账户、提醒、隐私、关于、needsKey 等子页无 VM/符号契约；F-06 规模约 480 行估算 600～750，疑超 500；R5-47-01（中）merge_choice 待选并发修订无界面卡与 SyncFacade 方法；S6 补读（rev-r5）pass，新增中1/低1（R5-47-01～02）；复核后 CO-22 已修订错误来源补 CORE-21 透传码，待复检；前次：B/pending（/root/p2_core_late 231320/3，M/L/H；完整消费确认） | fail |
| P2-CORE-48 | CORE-48 | /root/p2_core_late / 2026-10-20 | 207414 / 3 | P?P?PP? | P?P??F | M/L/H；计划DTO/同步；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-49 | CORE-49 | /root/p2_core_late / 2026-10-20 | 256786 / 4 | P?P?PP? | P?P?PF | M/L/H；L-N04；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-50 | CORE-50 | /root/p2_core_late / 2026-10-20 | 294230 / 4 | P?P?PP? | P?P?PF | M/L/H；识别DTO/平台接缝；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-51 | CORE-51 | /root/p2_core_late / 2026-10-20 | 217526 / 3 | P?P?PP? | P?P?PF | M/L/H；包schema/tough；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-52 | CORE-52 | /root/p2_core_late / 2026-10-20 | 179825 / 3 | P?PFFP? | PFF?PF | L-N02；L-I08/09；M/L；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-53 | CORE-53 | /root/p2_core_late / 2026-10-20 | 171756 / 3 | P?PPFP? | P?F?PF | L-I06/08/09；M/L；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-54 | CORE-54 | /root/p2_core_late / 2026-10-20 | 218782 / 3 | P?P?FP? | P?F?PF | L-I08/09；M/L/H；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-55 | CORE-55 | /root/p2_core_late / 2026-10-20 | 177133 / 3 | P?PFPP? | PF??PF | L-I05；M/L；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-56 | CORE-56 | rev-r1 / 2026-10-21 | 159841 / 3 | PPPFFPF | PPF?PP | 复检（v5.3.4，rev-r1/CORE-56复核.md）：主要阻断 R56-01 缺少引擎数据 JSON → DataLayer 的加载/构造函数；R56-02 缺少非全局构造器与测试注入点；R56-03 验收覆盖缺口与夹具未给出；S6 由整卡复核人读完材料，S4 记 pending；前次：C/fail（/root/p2_core_late 125289/2，L-N01；schema；M/L） | fail |
| P2-CORE-57 | CORE-57 | /root/p2_core_late / 2026-10-20 | 46647 / 1 | P?PF?P? | P??PP? | L-N07；M/L；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-58 | CORE-58 | /root/p2_core_late / 2026-10-20 | 183910 / 3 | PFPF?P? | PF??PF | L-I05；M/L；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-59 | CORE-59 | /root/p2_core_late / 2026-10-20 | 171190 / 3 | P?PF?P? | PF??PF | L-N02；L-I06/09；M/L；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-60 | CORE-60 | /root/p2_core_late / 2026-10-20 | 190532 / 3 | P?P?PP? | P?P?PF | M/L/H；L-N04；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-61 | CORE-61 | rev-r2；s6-c / 2026-10-21 | 129136 / 2 | PPPFFPP | PPPPPP | 复检（v5.3.4，rev-r2/CORE-61复核.md、s6-c/CORE-61-S6补读.md）：主要阻断 F-01 三个 op 均 call 与 Store 单写者事务及 CORE-03 call 时限冲突；F-02 校验错误码未定义；F-03 测试方案仅一条；S6 补读（s6-c）pass，新增低1；复核确认迁移序号 0061 正确；前次：B/pending（/root/p2_core_late 138647/2，M/L/H；草稿 schema） | fail |
| P2-CORE-62 | CORE-62 | /root/p2_core_late / 2026-10-20 | 90237 / 2 | P?PPPP? | P?PPPF | M/L；完整消费者确认；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-63 | CORE-63 | /root/p2_core_late / 2026-10-20 | 174904 / 3 | P?P?PP? | P?P?PF | M/L；L-N04；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-64 | CORE-64 | /root/p2_core_late / 2026-10-20 | 165993 / 3 | P?P?PP? | P?P?PF | M/L/H；平台输入/真机；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-65 | CORE-65 | /root/p2_core_late / 2026-10-20 | 162898 / 3 | P?PPPP? | P?P?PF | M/L；生命周期确认；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-66 | CORE-66 | rev-r2；s6-c2 / 2026-10-21 | 167514 / 3 | PPPFPPP | PFPFPP | 复检（v5.3.4，rev-r2/CORE-66复核.md、s6-c2/CORE-66-S6补读.md）：主要阻断 F-01（高）快照内容与分片格式无定义（明文序列化、实体范围、分片边界、每片 AAD）；F-04（高）轮换重入队经 enqueue_outbox 会写新字段时钟、制造虚假字段更改，实体枚举/重入队算法缺；F-02 FFI 段新旧协议并存；F-03 路径校验无 staging 根输入；S6 补读（s6-c2）pass，新增中1/低3（S6-CORE-66-01 cleanup_snapshot_dirs 无 FFI op 等）；成员提示漏收 CORE-68 Envelope 块及 D.14.4 登记差 82 字符，仍判 S6=pass；复核后 CO-22 已修订补依赖 CORE-68（Envelope，S6-CORE-66-04），待复检；前次：C/fail（/root/p2_core_late 205728/3，快照分批协议缺失；H/M/L） | fail |
| P2-CORE-67 | CORE-67 | /root/p2_core_late / 2026-10-20 | 65195 / 1 | P?FF?P? | PF??PF | E-N机器契约；L-N07；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-68 | CORE-68 | rev-r2；s6-b / 2026-10-21 | 80920 / 2 | PPPFFPF | PFPPPP | 复检（v5.3.4，rev-r2/CORE-68复核.md、s6-b/CORE-68-S6补读.md）：主要阻断 F-01（高）边界校验无 API（无 validate/from_json）与错误映射；F-04 entity_id=UUID 与 CORE-26 setting 键冲突；F-03 测试方案过薄且向量未创建；g 位外部前提缺 sha2/base64；S6-CORE-68-01 PushResult/PullPage 等同步线格式无所有者；S6 补读（s6-b）pass，新增中2/低1（S6-CORE-68-01～03）；前次：B/pending（/root/p2_core_late 91124/2，M/L；Envelope 消费者） | fail |
| P2-CORE-69 | CORE-69 | /root/p2_core_late / 2026-10-20 | 57449 / 1 | P?PPPP? | P?P?P? | M/L；词法子集/消费者；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-70 | CORE-70 | /root/p2_core_late / 2026-10-20 | 45885 / 1 | PFFF?P? | PF??P? | L-N05；M/L；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-71 | CORE-71 | /root/p2_core_late / 2026-10-20 | 51685 / 1 | P?PFFP? | PFF?P? | L-N06；M/L；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-72 | CORE-72 | /root/p2_core_late / 2026-10-20 | 70898 / 1 | P?PPPP? | P?PPP? | M/L；DDL/运维账号；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-73 | CORE-73 | /root/p2_core_late / 2026-10-20 | 84568 / 2 | P?PPPP? | P?P?PF | L-N01；M/L；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-74 | CORE-74 | /root/p2_core_late / 2026-10-20 | 52288 / 1 | P?PPPP? | P?P?P? | M/L；ABI头/注册表/标签；lead处理见D.14，消费确认未完成 | pending |
| P2-CORE-75 | CORE-75 | /root/p2_core_late / 2026-10-20 | 10567 / 1 | P?FFFP? | PFFPPF | L-N04/07；L-I09；lead处理见D.14，消费确认未完成 | fail |
| P2-CORE-76 | CORE-76 | rev-r1 / 2026-10-21 | 27153 / 1 | PPPFFPP | PPPPPP | 复检（v5.3.4，rev-r1/CORE-76复核.md）：主要阻断 R76-01 验收覆盖缺口：audit.mjs 与 validateCurrent 的多项规则无用例；R76-02 current.mjs 接口签名与文件约定缺失；S6 由整卡复核人读完材料，判 pass；前次：C/fail（/root/p2_core_late 11724/1，L-N03；M/L） | fail |
| P2-CORE-77 | CORE-77 | rev-r1 / 2026-10-21 | 68066 / 1 | PPPFPPP | PPPPPP | 复检（v5.3.4，rev-r1/CORE-77复核.md）：主要阻断 R77-01 CORE-08 未声明 Rational/Dimension/DimensionFull 的 serde，DimExpr/TypeExpr 的 JSON 无法凭契约实现；P-01 CORE-09/CORE-11 作者调用方确认缺失；S6 由整卡复核人读完材料，判 pass；前次：B/fail（reviewer-core77-r2 225619/4，N-01 跨修订 instantiate 协议高，已按 CO-13/14 修订） | fail |
| P2-CORE-78 | CORE-78 | rev-r2；s6-b / 2026-10-21 | 71039 / 1 | PPPPPPP | PPPPPP | 复检（v5.3.4，rev-r2/CORE-78复核.md、s6-b/CORE-78-S6补读.md）：主要阻断 复核人未列阻断项；consumerConfirmation 缺：CORE-26/66 作者调用方确认未取得；contracts/errors/registry.yaml 未创建，pending_batch 读出损坏行的错误码未写（低）；S6 补读（s6-b）pass，新增低3（S6-CORE-78-01～03），更正 S4 实现估算约 120 行（原写 90 为误读）；复核后 CO-22 已修订规模行改写（测试不计）、settle 空 settled 的 SettleReport 返回值写全并同步 Test，待复检；前次：B/fail（reviewer-core78-fresh 243316/4，F-01/F-02/F-03 高与 P-01，已按 CO-15～17 修订） | pending |
| P2-AND-01 | AND-01 | /root/p2_platform / 2026-10-20 | 110580 / 2 | P?PPPP? | P?PP?F | M；宿主锁版探针；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-02 | AND-02 | /root/p2_platform / 2026-10-20 | 109362 / 2 | P?PPPP? | P?PP?F | M；P-N01；权限合并；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-03 | AND-03 | /root/p2_platform / 2026-10-20 | 96292 / 2 | P?FPPP? | P?PP?F | M；P-I01；ActivityResult/选择器；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-04 | AND-04 | /root/p2_platform / 2026-10-20 | 99434 / 2 | P?PPPP? | P?P??F | M；P-N01；CameraX/设备；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-05 | AND-05 | /root/p2_platform / 2026-10-20 | 212878 / 3 | P?PPPP? | P?PP?F | M；P-N01；生命周期恢复；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-06 | AND-06 | /root/p2_platform / 2026-10-20 | 141071 / 2 | P?FPPP? | P?PP?F | M；P-I01；TEE/备份迁移；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-07 | AND-07 | /root/p2_platform / 2026-10-20 | 293425 / 4 | P?PPPP? | P?PP?F | M；P-I05/06；笔设备；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-08 | AND-08 | /root/p2_platform / 2026-10-20 | 180481 / 3 | P?PPPP? | P?P??F | M；P-N01；通知/OEM/重启；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-09 | AND-09 | /root/p2_platform / 2026-10-20 | 143484 / 2 | P?PPPP? | P?PP?F | M；P-N01；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-11 | AND-11 | /root/p2_platform / 2026-10-20 | 110124 / 2 | P?PPPP? | P?PP?F | M；签名/市场/工具链；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-12 | AND-12 | /root/p2_platform / 2026-10-20 | 322836 / 5 | ??PPFP? | P?F??F | M；P-N01；真机/模型；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-13 | AND-13 | /root/p2_platform / 2026-10-20 | 232151 / 3 | P?PFFP? | PFFP?F | M；P-N03；输入法/系统栏；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-14 | AND-14 | /root/p2_platform / 2026-10-20 | 159905 / 3 | PFPPPP? | PFPP?F | M；P-N05；URI接收方；P-I06；lead处理见D.14，消费确认未完成 | fail |
| P2-AND-15 | AND-15 | /root/p2_platform / 2026-10-20 | 66293 / 1 | ??PFFP? | PFF??? | P-N01；3warnings；UIAutomator；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-01 | WIN-01 | /root/p2_platform / 2026-10-20 | 155137 / 2 | P?PPFP? | P?F??F | M；P-N04；工具链/runner；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-02 | WIN-02 | /root/p2_platform / 2026-10-20 | 205252 / 3 | P?PPPP? | P?PP?F | M；P-N01；Inno/AppId/签名；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-03 | WIN-03 | /root/p2_platform / 2026-10-20 | 222341 / 3 | P?PPPP? | P?P??F | M；P-I05；P-N01；恢复联测；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-04 | WIN-04 | /root/p2_platform / 2026-10-20 | 293787 / 4 | P?FPFP? | PFF??F | M；P-N02；P-I01；HEIF/HEVC；帧预算；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-05 | WIN-05 | /root/p2_platform / 2026-10-20 | 297469 / 4 | P?PPFP? | PFF??F | M；P-N02/07；Office/剪贴板；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-06 | WIN-06 | /root/p2_platform / 2026-10-20 | 220551 / 3 | P?PPPP? | P?P??F | M；P-I05；单实例/双DPI/退出；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-07 | WIN-07 | /root/p2_platform / 2026-10-20 | 213698 / 3 | P?FPPP? | P?PP?F | M；P-I01；DPAPI/ACL跨用户；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-08 | WIN-08 | /root/p2_platform / 2026-10-20 | 325009 / 5 | P?PPPP? | P?P??F | M；P-I05/06；笔/输入法；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-09 | WIN-09 | /root/p2_platform / 2026-10-20 | 241671 / 4 | P?FPPP? | P?PP?F | M；P-I01；Explorer/托盘/自启；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-10 | WIN-10 | /root/p2_platform / 2026-10-20 | 100658 / 2 | P?PPPP? | P?PP?F | M；P-N01；静态代理；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-12 | WIN-12 | /root/p2_platform / 2026-10-20 | 217187 / 3 | P?PPPP? | P?PP?F | M；证书/PE/制品；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-13 | WIN-13 | /root/p2_platform / 2026-10-20 | 372863 / 5 | ??PPFP? | P?F??F | M；P-N01；跨端/设备/模型；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-14 | WIN-14 | /root/p2_platform / 2026-10-20 | 311388 / 4 | P?PFFP? | PFFP?F | M；P-N06；P-I05；真实IME；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-15 | WIN-15 | /root/p2_platform / 2026-10-20 | 234463 / 3 | P?PPPP? | P?P??F | M；P-I05；UIA/标题栏/笔/双DPI；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-16 | WIN-16 | /root/p2_platform / 2026-10-20 | 205210 / 3 | ??PPPP? | P?P??F | M；500行规模待证；P-N01；恢复；lead处理见D.14，消费确认未完成 | fail |
| P2-WIN-17 | WIN-17 | /root/p2_platform / 2026-10-20 | 73787 / 1 | ??PFFP? | PFF??? | P-N01；4warnings；UIA/锁版/交互桌面；lead处理见D.14，消费确认未完成 | fail |

## D.13 v5.3.2 独立复核与修订记录

本轮13任务组与六范围复核均已执行；原123意见（高15/中108）、H1～H7和0A.3继承记录在D.9对账无缺。仅做一轮复核修复，新问题未闭合的转P2，不循环复核。版本号在六范围报告完成后才同步。所有报告由未参与该范围修订的代理只读产生，SADD及处理记录始终lead单写；同一时间仅一个代理。

| 范围 / 复核人 | 基线 | 评分 | 原123中已解决/部分 | 新问题高/中/低 | 一轮修复提交 | 独立等级A/B/C |
| --- | --- | --- | --- | --- | --- | --- |
| core-a / review_core_a | f99a5c8 | 6.5 | 14/5 | 7/5/0 | d4583cd | 0/5/15 |
| core-b / review_core_b | 5c151ec | 6.5 | 15/8 | 4/4/1 | 5c6d133 | 0/11/13 |
| core-c / review_core_c | d4583cd | 7.2 | 10/9 | 3/6/0 | 085d4e9 | 2/18/3 |
| plat-and / review_core_a | d4583cd及当时工作区，02未变 | 7.0 | 15/11 | 4/6/0 | b76bd65 | 0/8/5 |
| plat-win / review_core_b | 085d4e9 | 7.0 | 20/3 | 2/3/2 | d18d5d5 | 0/12/3 |
| core-ui / review_core_c | b76bd65及当时CORE04/28/62工作区 | 7.3 | 10/3 | 0/4/2 | 32dd216 | 0/1/0 |

逐行重计：原123条独立结论已解决84、部分39；新发现53（高20/中28/低5）；lead一轮处理41已修订、1已覆盖、7部分修订、4转P2，部分项仍保留其阻断。core-a原口算B6/C14及15/4、plat-and原14/12均与逐行表不符，以上按逐行表纠正，未改任何卡等级或逐条结论。独立评级96卡A2/B55/C39；v5.3.1的83卡修订方自评A2/B54/C11/未复核16不可直接当同口径提升率。就绪仍0，S0七卡与新增67不通过，57只做局部复核。

本地原报告/处理记录：temp/verify-p1/{core-a,core-b,core-c,plat-and,plat-win,core-ui}.md及fix-对应文件（temp不提交）。可持久理解的逐条新问题、处理与P2去向保留在D.9，以下审计/交付报告另入库，不能仅靠临时文件解释本轮结论。

调用方确认：core-b明确CORE-03/04消费接缝不完整，core-c只确认所核ScreenSecurity调用方向并沿用H6阻断；没有实际作者对全量契约签可消费，因此不补造公共契约通过记录。

待确认Q32～40均保留暂行默认：保存Unresolved、选卡策略、FSRS步长、自建要求层级、Windows恢复、模型负责人、图片透视范围、应用发布许可证、内容负责人。ADR35～37为修订方技术决定，不冒充产品确认。Q39未定阻断发布，Q37/40未实名阻断对应真实交付。

### D.13.1 最终检查、材料与P2证据

最终数值、逐卡超量/分段、逐warning处置、xref剩余列表及13组统计见[持久化审计与交付核对](reports/v5.3.2-交付核对.md)。每个超量卡全部分段合起来是同一次编码会话，不能把分段当独立卡；无损分段不等于材料缩量达标。P2先处理H6/handle/schema、门禁拆分、缓存generation、平台安全/主机测试，再处理材料warning与原低级意见；真实内容/模型/许可/设备门槛照常阻断，不借修订结论豁免。

最终机械结果：check96/0/无环；dupErr=0、undefOps=0、crossDep22→18；undefErr79→65、undefTypes419→428、multi26→26；实际pack均值132815/中位127932，64卡超8万，最大WIN13=333460/5段；audit0 error/682 warning；工具6/6、stats --check和diff --check通过。未运行产品cargo/flutter/真机。告警分类：闭包外引用待分类430、本地定义未收录96、SDK或未知标识符96、Q关联差异59、历史/缺失卡引用1，均逐项保留于持久化台账，未关闭项转P2。

| 超量卡 | 总字符 | 分段数 | 处理方式 |
| --- | --- | --- | --- |
| WIN-13 | 333460 | 5 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-08 | 285068 | 4 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| AND-12 | 282484 | 4 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-14 | 276049 | 4 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-36 | 266338 | 4 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-05 | 260776 | 4 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-04 | 260322 | 4 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-50 | 260186 | 4 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-40 | 250775 | 4 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| AND-07 | 247959 | 4 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-39 | 237121 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-49 | 222964 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-46 | 207922 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-09 | 205873 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-26 | 202553 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-47 | 195982 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-38 | 194220 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-15 | 186932 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-03 | 184197 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| AND-13 | 182912 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-51 | 181662 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-06 | 181580 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-54 | 180702 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-12 | 179515 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| AND-05 | 175422 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-07 | 175385 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-66 | 171461 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-48 | 170389 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-02 | 168447 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-16 | 167984 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-27 | 163533 | 3 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-20 | 154790 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-60 | 154119 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| AND-08 | 148542 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-19 | 147511 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-13 | 143283 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-63 | 139035 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-52 | 138662 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-16 | 137426 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-32 | 137324 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-34 | 136468 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-17 | 135198 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-53 | 134727 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-14 | 134398 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-55 | 134257 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-59 | 132695 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-15 | 132454 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-37 | 127932 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-58 | 125469 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| AND-14 | 125215 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-23 | 125156 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-35 | 118754 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| WIN-01 | 114338 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-24 | 112522 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-64 | 112262 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| AND-06 | 102240 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-61 | 100409 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-41 | 96585 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-65 | 96515 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-43 | 90369 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-04 | 90174 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-56 | 88587 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| AND-09 | 84890 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |
| CORE-42 | 80874 | 2 | 无损分段，全部读完，同一编码会话；warnings按台账转P2 |

### D.13.2 P1 补修（2026-10-20）

P1 交付后的审核发现：WIN-07 已把 `.applock` 改为一律不支持，但卡内目标、验收与 CORE-23 仍按 Windows Hello 应用锁书写，且没有登记产品取舍；lead 按六范围复核所做的一轮修复没有再复核，抽查到 Clock、CORE-37 旧归属、S0 卡数等残留；21 个提交的自查说明是同一段模板。本次补修按以下顺序进行：

1. 提交 `b8ee93d`：WIN-07 改为 Windows 11 上的 Hello 用户同意验证门（`.applock` 包装为 0x04 ‖ DPAPI，验证由 Dart `WindowsKeyStore` 在解包前执行），Windows 10 不提供应用锁；依据为 Microsoft 文档（`RequestVerificationForWindowAsync` 最低 build 22000，`RequestVerificationAsync` 仅 UWP）。新增 README §6 Q41（待确认），修订 ADR-V5-37；CORE-23、CORE-65、CORE-47（新增应用锁开关）同步；清理 Clock、粘贴归属、S0 卡数等残留；CORE-57 写明 `tools/sadd/` 是先行入库的文档工具、不作就绪证据。
2. 只读复核 `temp/verify-p1/recheck.md`（复核人 recheck-p1，未参与修订）：49 条 lead 修复中闭合 26、部分闭合 20、修复引入新问题 3，另有新问题 RC-01～19。
3. 提交 `61d94d1`：处理 RC-01～19 与文档层面的部分闭合项（stats op 的 now_ms、NOTATION_* 错误表、FFI_BUSY 与 dispose 验收、gen_dto 注解关键字与 pending 规则、Dart 量纲 DTO、缓存键含 generation、CORE-62 新码 `AUTH_UPLOAD_RECONFIRM_REQUIRED`、recog.* 请求体、识别预算熔断落表、提醒写入唯一入口、CORE-04 `unwrap` 增加不可用路径并三处逐字同步、两端 setScreenSecure 方法清单、AND-01 冒烟、相机目录、卡序与阶段表去重等）。
4. 只读复核 `temp/verify-p1/recheck-2.md`（同一复核人，只看 `61d94d1`）：42 条中闭合 38、部分闭合 4，新问题 RC2-01～05（中 2、低 3）。
5. 本提交：RecognitionFlow 与 CandidateVm 改为显式 `notationProfileId`/`userDecls`，CORE-31 列 fml-ffi 附属适配；AND-06 把认证器不可用类回调映射为 `PLATFORM_UNSUPPORTED` 并补验收（常量名依据 androidx 源码）；识别提交前检查熔断标记，解除熔断改为 CORE-33 运维 SQL 脚本；CORE-37 旧归属最后两处；CORE-34 透传行移入引用表，消费表表头统一。这一步没有再做第三轮复核，结论以本节为准。

本次补修不改变 §D.10 任何卡的独立等级，就绪数仍为 0；S0 九张卡仍需按 README §8.5.1 复核。修订期间另有会话在同一分支提交了 P2 的 L-A～L-C（`c765274`、`7bf12ad`、`5d015fe`），补修以当时的文件为基础，没有覆盖这些提交。

### D.13.3 移除应用锁、Windows Hello 与防截屏（2026-10-20）

甲方确认（README §2.2、§6 Q41）：“防截屏，应用锁和Windowshello相关内容去掉，不需要过强的保护”。按 ADR-V5-38 修订：

- CORE-04：删除 `BiometricPrompt` 端口（`PlatformPorts` 由 12 个端口减为 11 个）、`ScreenSecurity` 可选接缝与唯一线格式、`PLATFORM_AUTH_FAILED`；`KeySecurityLevel` 去掉 `dpapiWithHello`；`SecureKeyValueStore.unwrap` 注释改为“包装与解包都不要求用户认证”，01/02/03 三处逐字一致。
- CORE-23：只保留系统级解锁；删除 GuestLocked、`UnlockTier`、`account.set_unlock_tier`、`AUTH_APP_LOCK_FAILED`、`AUTH_APP_LOCK_BACKOFF` 与 `.applock` 别名；新增 `profile.logged_out` 与 `account.set_logged_out` 记录登出，已登出的注册档案启动时停在账户入口（RegisteredLocked），验收同步。CORE-28 `GuardAccountState` 去掉 guestLocked；CORE-65 删除 `unlock`/`appLockEnabled`/`setAppLock`，账户状态镜像改为五个；CORE-47 删除应用锁开关与恢复码页防截屏；CORE-36 首帧与 order 20 钩子措辞改为档案打开；CORE-32 删除 AUTH_FAILED 上抛；CORE-44 映射表删除 BiometricPrompt 行。
- AND-06 改名“本地存储与 Keystore”，删除生物识别实现、`biometric.*` 通道方法、`.applock` 别名与 API 分档约束及相关验收；AND-01 去掉 `biometric=` 锁版键与宿主认证探针；AND-02 权限白名单删除 USE_BIOMETRIC、USE_FINGERPRINT；AND-13 删除 setScreenSecure。
- WIN-07 改名“本地存储与 DPAPI”，只保留 DPAPI 包装（0x02）与安全说明；删除 Hello 通道方法、`.applock` 格式与相关验收；WIN-15 删除 setScreenSecure；WIN-09 验收改为“已登出停在账户入口 + --minimized”；WIN-03、WIN-16 的“解锁等待”措辞改为档案打开或账户入口等待。
- README §5 R25 行去掉 AND-06、WIN-07；§6 Q41 移入已确认表；附录 A：00 D-09 部分撤销，ADR-V5-15/36/37 去掉生物识别与 Hello 内容，新增 ADR-V5-38，相关历史段落标“已撤销”。

本节之前（D.9～D.13.2）关于应用锁、Hello、防截屏的记录保留为历史，不再代表现行设计。卡片独立等级不变，就绪数仍为 0。


本轮CORE-57工具编辑材料：2026-10-20生成，62585字符、1段，已全文读取；来源及缺失文件见temp/P2temp/materials/CORE-57/report.json。Node未锁，测试仅为设计修订回归，非整卡就绪证据。

CORE-75实现材料：10558字符/1段，已全文读取；预分配数据216项设计校验通过、3个正反测试通过；尚无业务构建回执，不能记implementation通过。

## D.14 v5.3.3 P2独立复核与一轮修复

顺序：P2全部任务组提交→三名成员串行只读复核（基线2c04125）→lead统一一轮修复→标版；无第二轮复核。按用户临时文件要求，报告/处理记录统一在temp/P2temp/verify-p2/，替代任务书原temp/verify-p2路径。持久化逐卡证据为reports/v5.3.3-reviews.json；修复不能自动提升其独立等级。

| 范围 | 评分 | A/B/C | 新问题（高/中/低） | 整卡通过 | 材料与确认 |
| --- | --- | --- | --- | --- | --- |
| CORE-01～38 / p2_core_early | 7.0 | 0/21/17 | 2/4/0 | 0 | 正文已读，35超量，全部闭包/消费确认未完成 |
| CORE-39～76 / p2_core_late | 7.4 | 0/26/12 | 5/3/0 | 0 | 正文已读，29超量，全部闭包/消费确认未完成 |
| Android/Windows / p2_platform | 6.8 | 0/22/8 | 3/3/1 | 0 | 30卡正文已读，28超量，全部闭包/消费确认未完成 |

合计106卡，A0/B69/C37，就绪0；21新增（高10/中10/低1）。平台原17条低意见独立结论15闭合/2部分；晚段PR2/3/6和H03/04/07/15/16仍部分；早段指出13项继承、晚段9组、平台7组有交叉，不能相加当新增。lead本轮对21项做设计/工具修复，E-N03仍部分，其他20项落正文或回归；这不是20项实现通过。

### D.14.1 新问题处理

| 编号 | 级别 | 卡 | lead处理结论 | 证据与限制 |
| --- | --- | --- | --- | --- |
| E-N01 | 高 | 05/67 | 已修订 | piecewise对象分支；AST08通过/tuple拒绝，AST01～15真校验。 |
| E-N02 | 中 | 05/67 | 已修订 | multiple1..3、矩阵双层非空；正反例实测。 |
| E-N03 | 高 | 02/67及owner | 部分修订 | 34op错误镜像和标准定义补齐，签名无Err的rank/compatible/display不伪加业务码；结构/唯一定义通过，算法透传向量与消费者未全部确认。 |
| E-N04 | 中 | 05/23/67 | 已修订 | Python无损i64写回，3字段上下界及越界1实测。 |
| E-N05 | 中 | 36/75及消费方 | 已修订 | 统一消费者片段+聚合owner单写，拒绝重复handler。 |
| E-N06 | 中 | 24 | 已修订 | 改成平台密钥可用/档案打开/ProfileSession有效，无应用认证入口。 |
| L-N01 | 高 | 56/73 | 已修订（契约） | mark_unavailable/snapshot返回Result；generation_status与exhausted规则及向量，尚无产品实现。 |
| L-N02 | 高 | 52/59/38/50 | 已修订（契约） | userDecls全链路参数与规范缓存键/复制验收。 |
| L-N03 | 高 | 76 | 已修订 | 版本/record/D12全部字段对应，裸就绪/错误引用/旗标反例拒绝，Node回归通过。 |
| L-N04 | 高 | 75/36 | 已修订 | 补269项预分配，根/参数路由及最长完整段归属测试通过。 |
| L-N05 | 中 | 70/41 | 已修订 | 70依赖76，职责表及索引同步。 |
| L-N06 | 高 | 71/41 | 已修订（契约） | LCOV输入/集合/分子分母/80%边界及缺失失败规则，真实maint工具待实现。 |
| L-N07 | 中 | 57/67/75 | 已修订 | 裸contracts路径、ops.schema和$ref递归，真实文件清单回归通过。 |
| L-N08 | 中 | README5 | 已修订 | R23/R40验证类别补齐。 |
| P-N01 | 高 | AND15/WIN17 | 已修订（契约） | 独立模板构建/制品SHA/入口/运行ID/boot/ready-probe传输；框架未执行。 |
| P-N02 | 高 | WIN04/05 | 已修订（契约） | picker/drop/clipboard分目录批次，await初始化，不异步清共同根；交错反例待实现。 |
| P-N03 | 高 | AND13 | 已修订（契约） | 唯一AndroidShellKeys、安装登记与文本/IME/repeat/handled规则。 |
| P-N04 | 低 | WIN01 | 已修订 | 11端口，与CORE04一致。 |
| P-N05 | 中 | AND14/阶段表 | 已修订 | 统一S3，Windows写入器仍S5。 |
| P-N06 | 中 | WIN14 | 已修订（契约） | resetCommand返回AssignResult、冲突不修改，跨组和保存失败规则。 |
| P-N07 | 中 | WIN05 | 已修订（契约） | 按格式分别校验字节/编码/偏移/白底DIB像素，不再全等原负载。 |

### D.14.2 继承与外部遗留

E-I01首卡验收边界、E-I03纯输入稳定排序、E-I04标签码、E-I06事件tx_index、E-I12云namespace、E-I13异步安装/重复登记；L-I05注入/路由参数、L-I06路径/平台默认值归属、L-I07墨迹职责、L-I08统一预算、L-I09/P-I05共享单写、P-I01类前注释均由lead补修设计。尚无二次独立通过，规模与真实故障/消费证据仍待。

| 编号 | 下一步责任 | 未闭合与先行条件 |
| --- | --- | --- |
| E-I02 | CORE-09 owner | 500+150行未拆，先拆卡再编程，不通过虚减估算解决。 |
| E-I05 | CORE-15 owner/甲方 | 锁版tough在线时钟/datastore sans-I/O适配未验证。 |
| E-I07 | CORE-21 owner | random_key/seal/new_recovery_code随机输入/失败签名不闭合；同步全部消费者后继续。 |
| E-I08 | CORE-26 owner | 跨重启逐字节重发的已加密envelope持久输入和部分收敛规则待冻结。 |
| E-I09 | CORE-27 owner | commit_restore模式、部分导出引用闭包、CBOR终块未唯一。 |
| E-I10 | CORE-31 owner | 内部纯函数profile/取消/评分边界待闭合。 |
| E-I11 | CORE-32 owner | Purged包装删除DDL与设置/规模需先统一。 |
| L-I03 | CORE-66/67及op owner | 105pending和快照分批协议仍阻断，禁止私造schema。 |
| L-I01/02/04、P-I02～04/07 | 各契约owner/甲方 | 完整闭包、warning、锁版、消费确认与真实外部证据缺失；不授予就绪。 |

### D.14.3 分阶段抽样与开工许可

每阶段没有任何就绪卡，“抽1张就绪”均不适用；未就绪抽样如下，记录均在D.12，不能用B等级替代全部通过。

| 阶段 | 就绪卡抽样 | 未就绪抽样 |
| --- | --- | --- |
| S0 | 不适用（0卡） | CORE-01、CORE-70 |
| S1 | 不适用（0卡） | CORE-05 |
| S2 | 不适用（0卡） | CORE-55、AND-15 |
| S3 | 不适用（0卡） | CORE-38 |
| S4 | 不适用（0卡） | CORE-17 |
| S5 | 不适用（0卡） | CORE-30 |
| S6 | 不适用（0卡） | CORE-26 |
| S7 | 不适用（0卡） | WIN-13 |

### D.14.4 最终验证口径

检查实测见reports/v5.3.3-交付核对.md及v5.3.3-audit.json。复核输入材料保留pre-review-audit数，不以最终重生成替换为“复核人读过”。Node工具回归和schema结构断言不代表Rust/Flutter/生成器/主机框架或设备测试通过；未实现目标保留pending。真实编码三试点与M0/M-CONTENT/M-MODEL仍待，Q32～40逐项保持暂行默认。

最终实测：check106/0无环，Node13/13，schema513断言，reservation269项design；xref undefErr27/undefTypes422/crossDep16/multi25，重复错误/未定义op均0；audit errors0/warnings654（闭包外441/本地定义106/SDK未知106/Q0/其他1），材料平均294626/中位297622（沿用mat.mjs上中位数口径），105超量、最大WIN-13 518546字符/8段。原213最终148已修订/22部分/4不采纳/39已覆盖；105pending及完整材料/消费确认未关闭。验证仅针对已存在设计工具和schema，不等于业务/设备通过。 v5.3.4 当前材料登记（CO-22 之后，2026-10-21，HEAD b7b19ca，SADD/reports/v5.3.4-audit.json）：audit errors0/warnings665（闭包外449/本地定义107/SDK未知108/缺引用1），材料平均129,063、超80000 80张、≤110000 49张、分段总数229、最大CORE-36 335,869字符/5段；上列为v5.3.3历史值，各阶段对比见D.14.5材料登记。

### D.14.5 T1复核后续修订（2026-10-20，v5.3.4）

依据 temp/review/T1 复核报告的 F01～F10 与《改动方案》。均为设计文档修订，未实现代码、未经独立复核，评级不变；修订方不得自评通过。

| 变更单 | 问题 | 目标卡 | 处理 | ADR |
| --- | --- | --- | --- | --- |
| CO-01 | F02 随机输入 | CORE-21、23、24、26、27、32、66 | `SecureRandom` 端口；`random_key/seal_with_rng/wrap/new_recovery_code` 带 rng 且返回 Result；`seal` 显式 nonce；fml-crypto 去掉 getrandom；`OsRandom` 归 CORE-23 | V5-41 |
| CO-02 | F05 Purged 与 NOT NULL | CORE-32 | `session_key_wrap` 可空，CHECK 允许 Deleting/Purged；Purged 保留元数据并清空密文；设置越界验收改指 `recognition_counter` CHECK | V5-42 |
| CO-03 | F03 批次重发 | CORE-26、25 | `push_batch` 持久化已加密 Envelope；部分 ACK 改写批次；Conflict 视为同一修改删除、不进隔离区（不新增服务端哈希字段，因同 op_id 同字节必得 ACK）；epoch/密钥轮换作废批次；新增 T-RESEND | V5-43 |
| CO-04 | F04 备份 | CORE-27 | `commit_restore` 改 submit；外键闭包自动带出被引用父行，Replace 时闭包行按 Merge；Manifest 分块 0/末块的 CBOR 键、哈希区间、BK-V1 向量；新增 `BACKUP_SCOPE_INVALID` | V5-44 |
| CO-05 | F09 快照 | CORE-66、46 | 暂存目录分片文件 + `SnapshotManifest`；FFI 只传路径与清单；新增 `SYNC_PATH_INVALID`、`SYNC_SNAPSHOT_CORRUPT`；manifest.json 阻断原因更新 | V5-45 |
| CO-06 | F07 图片 | CORE-30 | `declared_ext` 由适配层传入；`decode_oriented/prepare/fit_for_upload` 带 `CancelFlag`；新增对 CORE-05 的依赖（`CancelFlag`） | V5-46 |
| CO-07 | F08 拆卡 | CORE-09、CORE-77 | 新增 CORE-77（`DimVar/DimExpr/TypeExpr/unify`，约170行）；CORE-09 规模约480行 | — |
| CO-08 | CORE-26 规模 | CORE-26、CORE-78、CORE-66 | 负责人确认现在拆：新增 CORE-78（`push_batch` 表、`save/pending/batched/settle/invalidate`、迁移 `0078_sync_batch.sql`），CORE-26 规模约440行；`SYNC_BATCH_UNKNOWN` 改由 CORE-78 定义；总卡数108 | V5-43 |
| CO-09 | Purged 保留期 | CORE-32 | 负责人确认 Purged 元数据保留 7 天（`PURGED_RETENTION_MS`，新增 `purged_ms`，`gc_plan/gc_execute` 增加 `now_ms`，`recog.gc` body `{ now_ms }`） | V5-42 |
| CO-10 | 消费方 | CORE-40、47、24、46 | 备份界面闭包提示与长任务提交、图片暂存扩展名与取消、`wrap_with_passphrase` 取 OsRandom、快照目录分片读写、`cleanup_snapshot_dirs` 默认 24 h | — |
| CO-11 | CORE-77 整卡复核 | CORE-77、08、09、11、01 | reviewer-core77 复核 B/fail（F-01～F-03 阻断）；lead 修订：UnifyError 加 Overflow、`instantiate`/`bindings`/`free_vars`/`to_text`、失败原子性、DimVar 分配顺序、MathKind 相容判定归 CORE-09、CORE-08 补 Rational/DimensionFull checked 运算与规范形、fml-type 骨架归 CORE-77、CORE-11 增加对 CORE-77 的依赖、CORE-01 规则1通用例外、engine.check 增加 UNIT_OVERFLOW；规模改约330行。修订后未复检；2026-10-20 reviewer-core77-r2 复检 B/fail（D.12 P2-CORE-77），遗留见CO-13/CO-14 | — |
| CO-12 | xref 未定义错误码 18 项逐条判断 | CORE-17、36、40、33、35；shared-writes.json | 8 个 CLOUD_*（CORE-33）本已在表中定义，原为工具对“`CODE`（HTTP 状态）”写法的误判；6 个 STUDY_*（CORE-17）与 SYNC_NOT_AVAILABLE（CORE-36）原只在散文中，改为标准错误码表（级别与可重试为补全，待所有者确认）；CORE-40 引用 RECOG_TIMEOUT/RECOG_OOM 写错，应为 CORE-35 定义的 RECOG_MODEL_TIMEOUT/RECOG_MODEL_OOM，并把 RECOG_MODEL_NOT_INSTALLED 的唯一定义卡改为 CORE-35；15 个码补登记（reservation 275→290项）；DTOcheck 新增 XREF-05（引用表声明的定义卡必须正确） | — |
| CO-13 | CORE-77复检N-01/N-06/N-09（2026-10-20 lead已修订，待非作者复检与CORE-09/11作者确认） | CORE-77、CORE-11、CORE-09 | 目标符号：`Subst::instantiate(&mut self, e: &DimExpr) -> Result<DimExpr, FmlError>`（01:7414）及7422、1875的跨修订合一协议。旧：合一前只对“其中一份/来源侧”typed实例化。新（二选一，由CORE-77所有者定）：(a)新建Subst后两侧都instantiate再unify；(b)增加`Subst::reserve_from(&mut self, e: &DimExpr)`等计数器推进接口，并定义多次调用间映射作用域（如`instantiate_all`或返回映射）。理由：两侧typed均为反序列化结果，无存活Subst，fresh从0编号会重号误合一。消费者：CORE-11（DERIVE_TYPE_MISMATCH、derive.rank pool≤200候选）、CORE-09（N-06：TypedAst中TypeExpr须为resolve后规范形并加验收）；CORE-11另写明rank路径Overflow按不匹配省略（N-09）。迁移风险：无已合入实现；签名若新增为非破坏。所需验收：两侧均自D0编号时按协议合一与手算同构；TypedAst resolve验收；修订后重生成CORE-77/09/11材料、非作者复检并取CORE-09/11作者确认 | — |
| CO-14 | CORE-77复检N-02/N-07（2026-10-20 lead已修订，待复检） | CORE-02、CORE-05、CORE-08（消费者CORE-77） | 目标符号：CORE-05 `MathKind`、CORE-08 `PseudoDim`、CORE-02 `FmlError`/`Diagnostic`/`TraceId`的derive集合与serde约定；领域crate（无I/O、无随机）构造`FmlError{code: UNIT_OVERFLOW}`的入口（trace_id取值规则）。旧：未声明，CORE-77 7393/7398的derive链与DimensionFull derive(Hash/Eq)及排序无法成立。新：由各所有者补derive/serde声明与构造方式；CORE-77 7423改为规范化溢出时反序列化失败的映射。消费者：CORE-77、CORE-09、CORE-11。迁移风险：无已合入实现。所需验收：CORE-08补checked_*、one、inverse、规范形单测（N-07）；修订后重生成材料并复检 | — |
| CO-15 | CORE-78复核F-01/F-02/F-05/F-14（2026-10-20 lead已修订，待非作者复检与CORE-26/66作者确认） | CORE-78、CORE-26、CORE-24（消费者CORE-46、CORE-66） | 目标符号：`pending_batch(&Store)`、`batched_op_ids(&Store)`、`save_batch(&mut WriteTx, &StoredBatch)`、`settle`、`invalidate_all(&mut WriteTx, InvalidateReason)`（01:7458-7462）与CORE-26 prepare_push（3548、3601）。旧：读函数只收&Store，无法与save_batch同事务；非轮换设备导入新密钥无作废路径，pending_batch不比较epoch/key_version；全额结算后重复settle返回SYNC_BATCH_UNKNOWN。新（由CORE-78/26所有者定）：增加事务内读取变体（如`pending_batch_tx(&WriteTx)`）并声明“至多一个未结算批次”不变量；prepare_push遇陈旧epoch/key_version同事务作废（或CORE-24导入新密钥事务调invalidate_all）；明确重复结算的良性结果；CORE-26补prepare_push/ack透传集合（SYNC_BATCH_INVALID、STORE_*）。理由：推送可永久卡死、竞态不可重试错误，ADR-V5-43作废语义未完整落实。迁移风险：无已合入实现；签名新增为非破坏，InvalidateReason若加变体需同步CORE-66。所需验收：A端旧批次+B端轮换后A导入新密钥旧批次被作废并以新版本推送成功；并发prepare_push不产生SYNC_BATCH_INVALID；重复settle期望确定；修订后重生成CORE-78/26/66材料、非作者复检并取CORE-26/66作者确认 | V5-43 |
| CO-16 | CORE-78复核F-03/F-06（2026-10-20 lead已修订，待复检） | CORE-78、CORE-26、CORE-68、CORE-25 | 目标符号：`StoredBatch.envelopes`元素字节编码与“envelopes ≤ 1 MiB”上限（01:7454、7465）、CORE-26 `max_bytes`、CORE-25推送请求体上限。旧：计量对象（CBOR blob/元素字节和/HTTP请求体）与“CORE-68确定性编码”未定义。新：由唯一所有者定义元素字节确切编码与单一上限常量及与HTTP请求体的换算，三卡引用同一常量；CORE-78补外部前提（CBOR库或改依赖CORE-21编码器，uuid/serde_json/rusqlite沿用CORE-13锁定）。理由：批次字节不可变，口径不一致会产生永远SYNC_PAYLOAD_TOO_LARGE的批次。迁移风险：无已合入实现。所需验收：恰好上限与上限+1字节边界向量；修订后重生成材料并复检 | — |
| CO-17 | CORE-78复核F-04/F-12（F-04已文字修正；F-12于2026-10-20 lead已修订，待复检） | CORE-13（消费者CORE-78、CORE-26及全部迁移归属卡） | F-04：CORE-13业务表归属清单（01:2043）原写`push_batch` → CORE-26，与CO-08拆卡结论冲突，lead按CO-08改为`push_batch` → CORE-78（仅归属文字，不改签名）。F-12：CORE-13未定义“待执行迁移”判定依据与乱序到达时user_version取值；0078必然先于0026合入，开发/测试库可能漏跑0026或user_version回退；迁移序号无机器预留/校验（CORE-61已用0038）。新：由CORE-13所有者补定判定规则（如以schema_migration缺失为准、user_version=已执行最大序号），并评估在DTOcheck/CORE-41增加迁移序号与归属卡一致性检查。迁移风险：无已合入实现。所需验收：乱序迁移到达用例；修订后CORE-13受影响条目复检 | — |
| CO-13～17处理 | 按用户指示直接修订（2026-10-20，lead） | CORE-01、02、05、08、09、11、13、26、46、61、68、77、78；附录A ADR-V5-43；DTOcheck xref基线 | CO-13：CORE-77 新增 `instantiate_all(&[&DimExpr]) -> Vec<DimExpr>`、`instantiate_types(&[TypeExpr]) -> Vec<TypeExpr>`，`instantiate` 改为不失败，跨来源须新建Subst并对每份来源各实例化一次；CORE-09 输出typed前resolve；CORE-11 substitute/rank按协议，rank的Overflow候选省略。CO-14：CORE-02 derive/serde、`FmlError::new/with_diagnostic/with_trace`、ErrorCode生成方法；CORE-05 MathKind、CORE-08 PseudoDim derive；CORE-77 to_text 空格文法与黄金文本、DX-05～11字面合一序列、fresh上界、反序列化溢出映射FFI_BAD_ARG、外部前提、规模400；CORE-08 补单测；CORE-01 workspace成员。CO-15：CORE-78 `pending_batch/settle` 改为接收WriteTx、删除 `batched_op_ids`、至多一个未结算批次、`InvalidateReason::Stale`、重复结算返回 `{0,0,true}`、UNKNOWN仅在批次作废且条目仍在outbox时；CORE-26 `prepare_push(tx: &mut WriteTx, …)` 在同一写事务读密钥、作废陈旧批次并落盘；CORE-46 UNKNOWN良性处理。CO-16：元素字节=CORE-68 `to_canonical_json`，`max_bytes`=请求体紧凑JSON字节数（16+Σ+(n−1)），CORE-78 只做元素字节和防御检查，envelopes改为u32大端长度前缀存储、无CBOR依赖。CO-17：CORE-13 待执行迁移按schema_migration缺失判定、user_version取最大序号、发布前允许补执行；CORE-61 迁移改0061。xref基线新增PartialEq/PartialOrd为derive名误报。未处理：N-10（pack材料噪声与分段空行差，属工具改进，另行处理）。DTOcheck、stats --check、node --test 均通过；材料重生成 CORE-77 226433/4、CORE-78 242339/4。均未独立复检，不改等级、不授予就绪 | V5-43 |
| 布局同步 | 拆分布局（2026-10-20）后的路径与链接 | core/and/win 的 00-总览.md、WIN-13 | 拆分无损核对（`readDocs` 拼回与 HEAD e195ba4 的 01/02/03 逐行比较）除 CO-13～17 外仅有以下差异，经用户确认（2026-10-20）作为拆分的同步修改：①三份 00-总览.md 的相对链接改为 `../README.md`、`../core/00-总览.md`、`../and/00-总览.md`、`../win/00-总览.md`、`../附录*.md`；②三份 00-总览.md 引言后各新增一段“拆分布局”说明（指向 README §7）；③core 总览 §3 索引同步 CO-14/16/17 的规模与迁移文件名（CORE-02 370、CORE-08 500、CORE-61 `0061_formula_draft.sql`、CORE-77 400、CORE-78 210）；④WIN-13 `summarize.py --budget` 参数由 `SADD/01-公共核心-v5.md` 改为 `SADD/S0/S0_CORE-01_基座.md`（原文件已删除）。不改卡片语义，不影响等级 | — |
| CO-18 | 材料体量（方案A，2026-10-20，用户确认） | CORE-57（README §8.1、§8.2 模板、AGENTS 同步） | 间接依赖由“块中出现所需标识符即收录”改为“块中定义了所需标识符才收录”：定义 = struct/enum/class/trait/type/typedef/interface/mixin/union/mod 声明、impl/extension 块、const、表格首列（错误码表等）、行首 op 名；新收块的标识符继续传递到不动点；只提及不定义的说明块不收录，`report.manifest[].mentionOnly` 记块数（108 卡合计 3733 块），复核/编码需要时用 --file 或直接读该卡文件补读。同时把 a6f7a7c 的 contracts/附录A 去噪规则写入 CORE-57 接口契约与验收（此前只在工具与本附录中）。目标卡、直接依赖与 CORE-01/02 仍全文收录，依赖闭包与闭包外引用处理不变。遗留：CORE-57 实际规模约 700 行（pack.mjs 421、pack.test.mjs 284），超过约 500 行的拆卡阈值；卡片“规模”仍写约 380 行（改写为实际值会被 DTOcheck CARD-06 拦截），须所有者决定拆卡（如把 contracts 过滤与 JSON 扫描拆为新卡）后改写规模。修订未经独立复检，不改等级 | — |
| CO-19 | 测试方案剥离（2026-10-21，用户指示） | 全部 108 张卡；README §7、AGENTS | 每张卡的“验收标准”字段全文移到 `SADD/Test/<S0|core|and|win>/S编号_卡号_TEST.md`（S0 15、core 65、and 13、win 15），卡片该字段改为一行引用“**验收标准**：测试方案全文见 [Test/…](../Test/…)”。`tools/sadd/layout.mjs` 读取时按引用原样拼回，剥离前后 `readDocs` 拼回的三份文档逐字节相同，卡片语义、等级、依赖与验收内容均不变；pack 材料只在材料头多一行测试方案来源（每卡 +79～82 字符，平均 128,371 → 128,452，CORE-56 分段 +1，超80000 仍 80 张，审计已重跑）。规则：改卡片功能时同一提交同步改测试方案，卡片改名时测试文件同步改名，DTOcheck LAYOUT-06/07 检查。剥离前卡片备份于 `backup/验收标准剥离前/`（不入库）。不改等级 | — |
| CO-20 | 规模不计测试（2026-10-21，用户确认） | README §8.4、§8.5 a、AGENTS；23 张卡的“规模”与 §3 索引 | 口径：规模只计本卡实现代码（含声明的附属），不计验证本卡实现的测试代码与夹具；以测试为交付物的卡（AND-12、WIN-13、AND-15、WIN-17）交付代码按实现计、自测不计。规模中单列了测试行数的卡按此扣除并同步 §3 索引：CORE-04 480→300、CORE-09 480→360、CORE-11 480→360、CORE-23 485→385（原合计漏算附属 FFI 40，按分项重算）、CORE-26 440→380、CORE-33 480→380、CORE-57 380→420（按 pack.mjs 实际行数，测试约 280 不计，CO-18 的超阈值问题随之解除）、CORE-65 460→360、CORE-67 480→360、CORE-69 430→310、CORE-70 440→340、CORE-73 320→240、CORE-74 400→250、CORE-75 220→100、CORE-76 380→230、CORE-77 400→230、CORE-78 210→120、AND-02 380→285、AND-13 380→330、AND-15 470→370、WIN-15 440→380、WIN-16 500→420、WIN-17 460→360。未改：写“含测试”但未单列行数的 CORE-08（单测与实现合计约 40）、CORE-28、41、58～64、66、71、72 共 13 张，其规模按新口径视为上界，待所有者复估；其余 70 张未提测试，视为只计实现。只改规模数字与说明，不改契约与验收，不改等级。遗留：`tools/sadd/layout.mjs`、`split.mjs`、`split-tests.mjs`（约 300 行）不在任何卡的规模范围内，待所有者决定归属（并入 CORE-57 会使其约 720 行超阈值） | — |
| CO-21 | 文档工具列为工具项（2026-10-21，用户确认） | README §7.1、§8.6；core/00-总览.md §3；AGENTS | `tools/sadd/layout.mjs`、`split.mjs`、`split-tests.mjs` 与 `tools/DTOcheck/` 单独列为工具项，不属于正式代码：不归任何模块卡、不计规模、不进产品构建、不做整卡复核与评级，改动用 `chore(sadd)` 提交并保持 DTOcheck 与 Node 测试通过。CORE-57 的代码位置由 `tools/sadd/` 收窄为 `tools/sadd/pack.mjs`（§3 索引与 §8.6 同步），避免整目录归属误读。解决 CO-20 遗留的三个工具归属问题；此前以 `chore(core-57)` 提交的 layout/split/split-tests 改动（041e098、227e70f）保留原提交，不改写历史。DTOcheck 与 CORE-70（SADD 结构门禁，计划中的 `tools/sadd/structure.mjs`）职责有重叠，是否以工具项替代或合并由 CORE-70 所有者决定 | — |
| CO-22 | v5.3.4 整卡复核与 S6 补读发现的简单文字问题（2026-10-21，用户指示“修复简单问题”；lead 修订，不改判、不提级） | CORE-13、21、22、24、26、32、36、40、46、47、66、78；AND-12；附录A（A.4.5 补充、ADR-V5-27、ADR-V5-34）；Test CORE-36、78；core/00-总览.md §3 与依赖图 | ① 规模按 CO-20 口径：CORE-22 460→280、CORE-36 380→280（原含测试 180/100），CORE-26/78 规模行改写为“测试约 N 行，按 §8.4 不计入”；② 补漏列的直接依赖（只补依赖、不改接口）：CORE-24、32 +CORE-05（pack_item_id 等、Page<T>，对应 S6-fail R3-24-08、R3-32-09），CORE-26、66 +CORE-68（Envelope，F-06、S6-CORE-66-04），CORE-46 +CORE-03、78（rev-r4 F-02），CORE-40 +CORE-59（F-03），重生成材料确认 CORE-24/26/32/66 已收入对应定义块；③ 陈旧引用与笔误：DEP-5 归 CORE-69（CORE-41 编排）于 ADR-V5-34、CORE-36 及其 Test；RecognitionMode 归 CORE-29 于 ADR-V5-27；A.4.5 补充 AccountController 归 CORE-65；CORE-21 wrap_with_params 漏写 rng 参数、密钥层次补 SyncSnapshot 用途；CORE-40 CLOUD_* 引用行定义卡、InkDocument 改为 InkStrokesDto；CORE-47 错误来源补 CORE-21 透传码；AND-12 预算行名改全名；CORE-13 store.open 示例注明 schema_version 为夹具值；④ CORE-78 settle 空 settled 的 SettleReport 返回值写全并同步 Test。涉及接口或设计选择的发现未改，留待所有者与 §8.4 变更单。上列卡修订后仍为“待复检”，评级不变 | — |
| 其他 | F01、F06、F10、文档漂移 | CORE-01、41、31、76、README、D.10 | 首卡锁文件验收移交 CORE-41；评分截断 1.0；`current.mjs` 表头/行宽校验；卡数口径 | — |

补充（2026-10-20）：原临时检查脚本（check/xref/mat 与 validate-dto）已清理，由 `tools/DTOcheck`（dto/cards/xref）取代；其 xref 新增“shared-writes.json 错误码登记与卡内定义一致”检查，补登记了 SYNC_BATCH_UNKNOWN 的 owner（CORE-78）、BACKUP_SCOPE_INVALID、SYNC_BATCH_INVALID、SYNC_PATH_INVALID、SYNC_SNAPSHOT_CORRUPT，以及此前漏登记的 AUTH_UPLOAD_RECONFIRM_REQUIRED（CORE-62）、LIB_TAGS_LIMIT（CORE-14）；reservation 由 269 项变为 275 项。

遗留：CORE-77/78 的单元与属性测试、各 op 的 DTO schema、BK-V1 与 T-RESEND 向量均未生成；CORE-09/21/23/26/27/30/32/46/66/77 材料须重生成并整卡复核；直接消费者（CORE-24 等）未取得作者确认。

材料登记（`node tools/sadd/audit.mjs --out SADD/reports/v5.3.4-audit.json`；当前值为 2026-10-21 在 HEAD b7b19ca（CO-22）之上重跑：108卡，errors=0、warnings=665，平均字符 129,063 / 超80000 80 张 / ≤110000 49 张 / 分段总数 229，见本节末“CO-22 之后”；以下各阶段对比为 2026-10-20 在 HEAD a6f7a7c 之上、按 CO-18 改为间接依赖只收定义块后重跑，108卡，errors=0、warnings=664）。三阶段对比（平均字符 / 超80000张数 / ≤110000张数 / 分段总数）：去噪前 303,349（db8a58c 登记值；同一 35e1bcf 内容为 306,545）/ 107 / — / 523 → contracts 与附录 A 去噪（a6f7a7c）161,922 / 85 / 40 / 272 → 间接依赖只收定义块（CO-18）128,371 / 80 / 49 / 227；CORE-78 242,339 → 80,744 → 70,965。去噪规则（`tools/sadd/pack.mjs`，“相关卡”= 目标卡、直接依赖与始终整份收录的 CORE-01/02）：①`contracts/dto/*.schema.json` 只在被 --file 指定、属于相关卡拥有的 op（以 manifest.json 的 owner 为准）、被相关卡收录文本按路径引用，或被已收录 schema 经 $ref 引用时收录全文；`types.schema.json` 按 $defs 条目切片（$ref 引用、相关卡文本出现的类型名及其内部引用闭包），保留完整 JSON 结构与条目原文，材料头注明“切片”及收录/未收录条目名；②`contracts/dto/manifest.json` 与 `contracts/policies/shared-writes.json` 只收录 owner ∈ 相关卡的条目，保持原 JSON 结构且条目与原文件逐字节一致，头部写原文件 SHA-256 与条目数 n/N；③`contracts/vectors/*` 在相关卡正文或验收引用其文件名时收录；④附录 A 只收录相关卡收录文本引用的 ADR 行、“模块卡”列含目标卡的 ADR 行（附表头）及引用目标卡或这些 ADR 的补充章节全文，ADR 表章节（A.4.1/A.4.2）不再整段收录；⑤其余 contracts 文件在材料末尾“contracts 清单”中列名并给出字节数与 SHA-256，--file 可取全文。report.json 新增 `filteredFiles`（每个被列名/切片/过滤文件的 path、mode、originalBytes、includedBytes、reason、sha256，过滤与切片另记 kept/total）、`related`、`adr` 与 `reading`（material.md 与 part-N.md 内容相同、二者择一阅读）；输出目录旧 part-*.md 先清理（`removedStaleParts`）；分段改为在围栏外空行处精确切分，各段拼接逐字节等于 material.md。间接依赖按符号收集、依赖闭包与 warning 集合不变（同一内容下去噪前后 108 卡的 closure/选块与 warnings 逐项相同，“未创建文件”清单相同）。间接依赖规则见 CO-18：只收定义了所需标识符的块，只提及的块不收录并计入 `mentionOnly`；同一内容下 CO-18 前后依赖闭包不变，warnings 665 → 664（WIN-08 的“本地定义缺失”消失），“定义不在材料中的符号”2,729 → 2,822，“未创建文件”清单因不再收录的间接依赖块而减少（29 张卡）。受影响卡（去噪前 → a6f7a7c → CO-18，字符/分段）：CORE-01 136923/2→88022/2→88022/2；CORE-08 246057/4→97858/2→88471/2；CORE-09 262747/4→129522/2→120135/2；CORE-11 251769/4→154215/2→138632/2；CORE-17 327397/5→190922/3→168186/3；CORE-21 257512/4→92766/2→84802/2；CORE-23 342707/5→207204/3→184947/3；CORE-24 323896/5→186834/3→146554/2；CORE-25 254856/4→90635/2→79044/1；CORE-26 408905/6→282168/4→231481/3；CORE-27 364534/6→240392/4→188861/3；CORE-30 230173/4→79746/1→77803/1；CORE-32 339230/5→216504/3→185222/3；CORE-36 467692/7→354480/5→334568/5；CORE-40 441553/7→306147/4→239741/4；CORE-46 402941/6→272739/4→170629/3；CORE-47 392003/6→262917/4→213091/3；CORE-66 371099/6→233882/3→167432/3；CORE-77 226433/4→77373/1→67986/1；CORE-78 242339/4→80744/2→70965/1。剩余体量主要来自直接依赖契约全文与闭包外未分类引用的契约（如 CORE-36 闭包外 29 张卡约 12.4 万字符；方案B“补下游说明标注”经用户决定不做）。去噪前的 pack、测试、审计与五张卡材料备份于 `backup/去噪前原始文件/`（不入库）。CORE-77 复核用材料为修订前版本（197247/3，未入库，留存于 temp/review/T1/evidence/CORE-77-material-pre-revision，已由 reviewer-core77 读完前606行并扫描其余，见复核报告§1）；修订后须重新 `pack.mjs CORE-77` 并复检。分类warning未逐条语义关闭，本登记不代表复核人已读完。

CO-19/20 之后（2026-10-21，HEAD 26e6981 之上重跑 `node tools/sadd/audit.mjs --out SADD/reports/v5.3.4-audit.json`，108卡，errors=0、warnings=664）：平均字符 128,453 / 超80000 80 张 / ≤110000 49 张 / 分段总数 228；最大 CORE-36 334,650（5 段）。与 CO-18（e038ebf 同一工具重跑：128,369 / 80 / 49 / 227 / warnings 664）相比，每卡仅增加 75～108 字符（合计 +9,039），来源是 pack 材料头新增的一行“目标卡验收标准取自测试方案 Test/…”；验收标准按引用拼回，正文与剥离前逐字节相同，因此体量不变。唯一的分段变化是 CORE-56 的 2 段 → 3 段（+83 字符越过分段边界）。CO-20（规模不计测试代码）只改规模行，不影响材料体量；warnings 664 → 664。待复核的 29 张卡（字符/分段）：CORE-01 88,102/2；CORE-02 63,027/1；CORE-05 105,761/2；CORE-08 88,553/2；CORE-09 120,222/2；CORE-11 138,717/2；CORE-13 184,475/3；CORE-17 168,268/3；CORE-21 84,884/2；CORE-23 185,032/3；CORE-24 146,636/2；CORE-25 79,126/1；CORE-26 231,566/3；CORE-27 188,943/3；CORE-30 77,885/1；CORE-31 152,653/2；CORE-32 185,304/3；CORE-36 334,650/5；CORE-40 239,823/4；CORE-41 64,805/1；CORE-46 170,711/3；CORE-47 213,173/3；CORE-56 159,841/3；CORE-61 129,136/2；CORE-66 167,514/3；CORE-68 80,920/2；CORE-76 27,153/1；CORE-77 68,066/1；CORE-78 71,039/1（合计 29 张，其中超 80000 的 22 张）。

CO-22 之后（2026-10-21，HEAD b7b19ca 之上重跑 `node tools/sadd/audit.mjs --out SADD/reports/v5.3.4-audit.json`，108卡，errors=0、warnings=665）：平均字符 129,063 / 超80000 80 张 / ≤110000 49 张 / 分段总数 229；最大 CORE-36 335,869（5 段）。与 CO-19/20（128,453 / 80 / 49 / 228 / warnings 664）相比：81 张卡材料字符变化，来源是 CO-22 补漏列直接依赖与改文字（如 CORE-24 146,636→163,667、CORE-46 170,711→196,935、CORE-32 185,304→195,224，CORE-24/26/32/66 已收入 pack_item_id 等、Page<T>、Envelope 定义块）；唯一的分段变化是 CORE-24 的 2 段 → 3 段；warnings +1 为新增“CORE-36 Outside dependency closure: CORE-69”（CO-22 改正的 DEP-5 归 CORE-69 引用，未加依赖）。复核记录（D.12）里的字符数是复核时的值，不随本次重跑修改。29 张复核卡当前（字符/分段）：CORE-01 88,133/2；CORE-02 63,108/1；CORE-05 105,855/2；CORE-08 88,594/2；CORE-09 120,222/2；CORE-11 138,717/2；CORE-13 184,637/3；CORE-17 168,321/3；CORE-21 85,018/2；CORE-23 185,178/3；CORE-24 163,667/3；CORE-25 79,228/1；CORE-26 232,890/3；CORE-27 189,138/3；CORE-30 77,957/1；CORE-31 152,715/2；CORE-32 195,224/3；CORE-36 335,869/5；CORE-40 241,154/4；CORE-41 64,827/1；CORE-46 196,935/3；CORE-47 213,329/3；CORE-56 159,841/3；CORE-61 129,189/2；CORE-66 168,800/3；CORE-68 80,960/2；CORE-76 27,153/1；CORE-77 68,066/1；CORE-78 71,207/1（其中超 80000 的 22 张）。
