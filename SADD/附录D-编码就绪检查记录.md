# 附录 D：编码就绪检查记录 v5.3.1

> 版本：v5.3.1 ｜ 检查日期：2026-10-20 ｜ 效力：说明性；历史批次见D.4～8，v5.3 P0处理/证据见D.9，当前96卡就绪状态见D.10，v5.3 复核与 v5.3.1 修订见D.11，整卡语义复核记录见D.12；规范性要求以README与01～03模块卡为准。
> 关联文档：[README](README.md)（§8.5 就绪定义、§6 已确认与待确认事项）、[01 公共核心](01-公共核心-v5.md)、[02 Android 端](02-Android端-v5.md)、[03 Windows 端](03-Windows端-v5.md)、[附录 A](附录A-架构决策与评审记录.md)（ADR-V5-12～34）。

## D.1 检查方法

- 当前对象：96 张有效卡（CORE 68、AND 13、WIN 15）；AND-10、WIN-11 已撤销，不计有效卡。早期69/74张是历史检查批次，不再用于当前就绪统计。
- 清单：README §8.5 的 a～g 七项（结构与规模、依赖闭合、契约唯一、契约可编码、验收可测、追踪一致、外部前提）。
- 机械项：七字段、声明的规模与构建单元、依赖与索引/图、无环及前置阶段不晚于本卡、需求双向追踪由临时脚本检查。0项只说明所覆盖的机械规则未发现问题，不等于接口、规模可行性或平台API已验证；脚本是辅助证据，不签发开工许可。
- 语义项（类型与错误码可追溯、DTO 与表结构完整、验收可执行、外部前提）逐卡人工判断。
- 结论口径：历史表“已修订/新增”只记录改动，不能推导符合README §8.5。当前评级与状态唯一看D.10：C为未就绪、待P1修订；只复核P0的A/B卡仍须补全整卡语义复核。未复核不得写“就绪”。产品Q32～Q37保持暂行默认、待甲方确认；Q1～Q31历史确认不变。

## D.2 统计

<!-- sadd-current-stats:start -->
由 `node tools/sadd/stats.mjs` 从现行卡与D.10生成；不代表实现或真机验收通过。

| 文档 | 当前有效卡 | 历史撤销 |
| --- | --- | --- |
| CORE | 68 | 无 |
| AND | 13 | AND-10 |
| WIN | 15 | WIN-11 |

总计96卡；当前独立复核等级：未独立复核=96；就绪=0。
<!-- sadd-current-stats:end -->

v5.3.1（2026-10-20）：§D.10 第6列 A=2、B=54、C=11、未复核=16，就绪=0（尚无 §D.12 复核通过记录）。以下为 v5.3 历史统计：原评审逐行统计 A=4、B=47、C=30（81卡）；core-a尾注自报B10/C8与其逐卡表B11/C7不一致，本表按逐卡行计数。本轮修订后P0复核 B=37、C=23（其中3张保持原C、P0未涉及），其余未复核=23；新卡无原评审等级。未完成83卡整卡语义复核，不宣称全部就绪；实现/真机证据另在编码与交付阶段提供。

- 历史拆分/新增记录（以下11张为早期批次，不是当前新增统计）：CORE-45 邮箱验证码与发信（自 CORE-22 拆出）、CORE-46 同步与升级协调器（自 CORE-26 拆出）、CORE-47 设置页与账户安全界面（自 CORE-36 拆出）、CORE-48 计算器、代入与计算链界面（自 CORE-38 拆出）、CORE-49 学习统计、提醒设置与自建书界面（自 CORE-39 拆出）、CORE-50 识别结果、云端确认与识别历史界面（自 CORE-40 拆出）、CORE-51 资源包下载、导入与管理界面（自 AND-10、WIN-11 抽出两端共用部分）、CORE-52 公式复制格式与富格式导出（2026-10-19 按 README §6 Q12 确认新增）、CORE-53 LaTeX 命令补全、CORE-54 公式库批量选择与批量操作（2026-10-19 按 README §6 Q16 确认新增）、WIN-14 快捷键自定义（2026-10-19 按 README §6 Q11 确认新增）。
- 撤销卡：AND-10、WIN-11。两卡的内容是两端相同的 Dart 行为，并入 CORE-50、CORE-51，平台差异只剩端口实现（ADR-V5-19）。编号不复用。
- v5.3.1历史卡数83；v5.3.2当前卡数由下列生成块与D.10共同核对，历史批次不覆盖。

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

## D.9 v5.3 评审意见处理记录

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

| U-F02 | 高 | 已修订 | CORE-57；README §8.1 | 入库生成器；间接契约符号闭合、直接契约完整保留，超量无损分段并记录。 |
| H1/继承 U-F01、core-ui:N12 | 高 | 已修订 | CORE-41、CORE-57 | 定义 warning 与 error 边界；保留未知符号人工复核，不声称启发式等于语义通过。 |

| B-F-14 | 高 | 已覆盖（v5.3.1） | CORE-22、CORE-25、CORE-45 | 核实 AUTH_RATE_LIMITED 仅 CORE-22 定义，其他卡复用；本轮统一其余表格。 |
| B-F-15 | 中 | 已覆盖（v5.3.1） | CORE-02、CORE-23、CORE-29、CORE-34、CORE-50 | 消费者引用所有者，未重复声明 severity/retryable。 |
| B-F-16 | 中 | 已修订 | CORE-19、CORE-20、CORE-21、CORE-25、CORE-39、CORE-45、CORE-49 | 行内清单改标准定义表；界面错误处理表改三列引用表，HTTP 表补级别。 |
| H2/继承 fix-core-b 错误表遗留 | 中 | 已修订 | CORE-02、CORE-41 | 明确首定义、消费者表及注册表未创建时的门禁边界。 |

| C-F-04 | 高 | 已修订 | CORE-55、CORE-58 | 拆组件、命令、外观入口与预热；原卡保留主题/布局规范，S2 外观路由可达。 |
| C-F-06 | 高 | 已修订 | CORE-37、CORE-59 | 只读渲染/worker 与编辑输入分开，原编辑行为/验收随职责迁移。 |
| C-F-07 | 高 | 已修订 | CORE-38、CORE-60、CORE-61、CORE-48 | 导入单位界面与 Rust 草稿各单独卡；单位页断言改核心查询，下拉归计算页。 |
| B-F-28 | 中 | 已修订 | CORE-22、CORE-23、CORE-26、CORE-36、CORE-62、CORE-63、CORE-65、CORE-66 | 服务端/客户端、档案/账户控制器、壳/账户表单、合并/快照轮换分开。 |
| H3/继承 CORE-40 规模 | 高 | 已修订 | CORE-40、CORE-64 | 墨迹采集控制器/画布与识别编排拆开，均保持 S5。 |

| AN-F01 | 高 | 已修订 | AND-02 | 白名单补通知/网络/生物识别与 AndroidX 动态接收器权限；按阶段审计启用项。 |
| AN-F03 | 高 | 已修订 | AND-06；ADR-V5-36 | 26–29 非加密认证+时效密钥；30+组合保留 M0 探针，KeyProperties 与认证器常量分清。 |
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
| A-17 | 中 | 已修订 | CORE-03/13 | store.open产生handle，free返回状态且allocation_id防ABA。 |
| A-18 | 中 | 已修订 | CORE-03 | C头文件include与C++ linkage守卫。 |
| A-19 | 中 | 部分修订 | CORE-07/56/67 | 补字段表与快照查找；复杂共享类型schema尚未实体化，见H6。 |
| A-20 | 中 | 部分修订 | CORE-09/56 | 明确CheckResult和单位快照；具体完整schema/真实向量仍需复核，不以散文闭合。 |
| A-21 | 中 | 已覆盖（v5.3.1） | CORE-05/16 | 哈希只依赖规范AST；内容去重的附加元数据另比较。 |
| A-22 | 中 | 已覆盖（v5.3.1） | CORE-06 | 32×32通过，33×32及65×1拒绝；无64×64通过保证。 |
| A-23 | 中 | 已修订 | CORE-13 | 一次升级全部迁移一个事务。 |
| A-24 | 中 | 已修订 | CORE-03/13 | 补store DTO/mode/handle、敏感字段与副本安全边界。 |
| A-25 | 中 | 已修订 | CORE-12 | 字体索引已修；补整体Err携NodePath，不返回部分布局。 |
| A-26 | 中 | 已修订 | CORE-11 | substitute/run_plan补单位与取消参数。 |
| A-27 | 中 | 已覆盖（v5.3.1） | CORE-05 | NS_PACK与拼接字节、pack_item_id唯一定义。 |
| A-28 | 中 | 已覆盖（v5.3.1） | CORE-05/14/17 | requirement_level持久化和缺省Q35、card_id规则已存在。 |
| A-29 | 中 | 已覆盖（v5.3.1） | CORE-17 | duplicate只在重放派生，不更新事件。 |
| A-30 | 中 | 已修订 | CORE-18 | 按期望环境/方案绑定，补profile参数、choice示例及parse失败Result语义。 |
| A-31 | 中 | 已修订 | CORE-04/28 | 底层只传输，守卫唯一策略，Fake未准备请求用StateError。 |
| A-32 | 中 | 部分修订 | CORE-15 | tough时钟/datastore适配待官方源码与M0fixture验证，明确在线更新阻断，禁止冒充纯函数已闭合。 |

| B-F-17 | 中 | 已修订 | CORE-65 | 邮件契约依赖45已在闭包；补Dart AccountState及wire映射。 |
| B-F-18 | 中 | 已修订 | CORE-23/24 | 明确交互单库与升级专用双库，源只读目标单写者。 |
| B-F-19 | 中 | 已修订 | CORE-24/26/66 | Store API归fml-store，fml-sync只纯合并，修正路径/规模/索引。 |
| B-F-20 | 中 | 部分修订 | CORE-24/67 | op表已有，StepInput/KeyOutput明确；全量schema仍随H6未闭合。 |
| B-F-21 | 中 | 已修订 | CORE-25/26/68 | 新增共享proto卡，端/服务同一Rust结构和向量。 |
| B-F-22 | 中 | 已覆盖（v5.3.1） | CORE-05/26 | NS_MERGE、UUID网络字节排序/拼接已定义。 |
| B-F-23 | 中 | 已覆盖（v5.3.1） | CORE-21/24/25/46 | 线上名两种与CBOR record_base64已统一。 |
| B-F-24 | 中 | 已修订 | CORE-46 | 推送删除多余幂等头，保留op_id服务端幂等。 |
| B-F-25 | 中 | 已修订 | CORE-46 | restoreOnNewDevice统一KeySecretInput。 |
| B-F-26 | 中 | 已覆盖（v5.3.1） | CORE-21 | wrap_with_params接kdf/salt，随机盐和默认参数已有。 |
| B-F-27 | 中 | 已修订 | CORE-62 | NetEvent与events流、重登/426订阅语义。 |
| B-F-29 | 中 | 已修订 | CORE-31 | Result签名、显式symbols、final_check形状，固定submit。 |
| B-F-30 | 中 | 已修订 | CORE-05/14/32 | Page下沉纯数据；pending_cloud字段表。 |
| B-F-31 | 中 | 已修订 | CORE-33 | 预占/结算/退还/未知跨日对账，预算缺省关闭、配额CAS与输出过滤。 |
| B-F-32 | 中 | 已修订 | CORE-19 | 内容依赖16与QuestionSource映射，派生来源14。 |
| B-F-33 | 中 | 已覆盖（v5.3.1） | CORE-05/19 | question_seed完整字节规则已有，消费者只调用。 |
| B-F-34 | 中 | 已修订 | CORE-19 | BookSummary/BookDraft，create不收id。 |
| B-F-35 | 中 | 已修订 | CORE-20/23 | 提醒键与重排输入；calibration口径/op/边界验收。 |
| B-F-36 | 中 | 部分修订 | CORE-30、README Q38 | 旋转算法/阈值明确；自动透视范围调整待产品确认。 |

| C-F-08 | 中 | 已修订 | CORE-01/41/55 | 共用平台符号表，无defaultEditorMode例外；DEP5/6保持。 |
| C-F-09 | 中 | 已修订 | CORE-28及消费者 | 28已S2，补AppLog各调用者依赖。 |
| C-F-10 | 中 | 已修订 | CORE-51 | NetworkGuard/AppLog依赖闭合，阶段S2≤S4。 |
| C-F-11 | 中 | 已修订 | CORE-48/46 | S3验outbox，S6验跨设备。 |
| C-F-12 | 中 | 已修订 | CORE-43/45 | 邮件配置/告警/演练归45，43只运维通用能力。 |
| C-F-13 | 中 | 已修订 | CORE-04/47、AND-13、WIN-15 | 可选ScreenSecurity接缝与生命周期，无能力猜测。 |
| C-F-14 | 中 | 已修订 | CORE-27/47 | 备份导出写文件前Rust校验口令，界面处理弱口令码。 |
| C-F-15 | 中 | 已修订 | CORE-54/58、AND-13、WIN-15 | 语义命令与实体键位分离。 |
| C-F-16 | 中 | 已修订 | CORE-37/52 | paintDisplayList归非ui render目录。 |
| C-F-17 | 中 | 部分修订 | CORE-03/37/67 | 统一生成目录/所有者；全量schema尚未实体化。 |
| C-F-18 | 中 | 部分修订 | CORE-48/51/61 | 补草稿/计划响应字段，复杂schema仍需H6补齐。 |
| C-F-19 | 中 | 已修订 | CORE-41/58、AND-12、WIN-13 | H7固定主机黄金图，真机布局对照另验。 |
| C-F-20 | 中 | 已修订 | CORE-42 | build/revision显式公式与边界、递增及示例。 |
| C-F-21 | 中 | 已修订 | CORE-14/54 | 标签唯一约束与错误码归14，批量复用。 |
| C-F-22 | 中 | 已修订 | CORE-43、D.10 | 本地替身验收；真实云部署为外部前提阻断。 |
| C-F-23 | 中 | 已修订 | CORE-41 | H7明确S0作业定义/后期目标SKIP与发布禁止pending。 |

| AN-F07 | 中 | 已覆盖（本轮H4） | AND-06 | 取消新增指纹必使时效/设备凭据密钥失效的错误保证。 |
| AN-F08 | 中 | 已修订 | AND-05 | 排除UI_HIDDEN，API34回调前提明确。 |
| AN-F09 | 中 | 已修订 | AND-12 | 主机驱动kill/旋转与进程内断言分工，框架P2。 |
| AN-F10 | 中 | 已覆盖（本轮H4） | AND-01 | AndroidChannelModule逐卡扩展与统一生命周期转发。 |
| AN-F11 | 中 | 已修订 | 02 §4 | 删除WorkManager矛盾。 |
| AN-F12 | 中 | 已覆盖（本轮H4） | AND-08 | NotificationScheduler完整语义注释已同步。 |
| AN-F13 | 中 | 已修订 | AND-08 | 不可变PendingIntent、singleTop/onNewIntent与tap去重。 |
| AN-F14 | 中 | 不采纳 | AND-08 | 未经核实OEM私有组件不当契约；公共应用详情兜底，ROM实测后才引入候选表。 |
| AN-F15 | 中 | 已修订 | AND-08 | detail字段及标题/说明映射，无法检测不伪称错误。 |
| AN-F16 | 中 | 已修订 | AND-09 | CORE-28已S2且本轮补显式依赖。 |
| AN-F17 | 中 | 已修订 | AND-09 | SecurityContext测试注入，Release运行时拒绝、禁badCertificateCallback。 |
| AN-F18 | 中 | 已修订 | AND-03 | 单选/多选分支与系统上限返回后校验。 |
| AN-F19 | 中 | 已修订 | AND-12 | 选adb主机uiautomator dump，非进程内假接口。 |
| AN-F20 | 中 | 已修订 | AND-03/14 | 独立剪贴板/FileProvider卡并同步安装点。 |
| AN-F21 | 中 | 已修订 | AND-04/CORE-30 | 统一Laplacian单位/初值100，平台标定。 |
| AN-F22 | 中 | 已修订 | AND-04 | 私有pending文件/原子ready与重建恢复/过期清理。 |
| AN-F23 | 中 | 已修订 | AND-13 | 移除Activity补EditorInfo假设，外部前提失败走ADR。 |
| AN-F24 | 中 | 已修订 | AND-12 | 100图系统路径主机夹具；Fake只诊断，不伪造端到端。 |
| AN-F25 | 中 | 已修订 | AND-12/13 | S2替身页面，S7业务跨阶段真机统一执行。 |
| AN-F26 | 中 | 部分修订 | AND-01、ADR-V5-15 | Kotlin DSL与锁文件分工已明确；SDK/AGP/NDK等具体兼容版本尚未实测锁定，S0外部前提阻断。 |
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
| W-27 | 中 | 部分修订 | WIN-07/ADR-V5-37 | 不采未经证实的IKeyCredentialManagerInterop；Hello签名稳定KDF移除，M0/ADR闭合前.applock阻断，不降安全。 |
| W-28 | 中 | 已修订 | WIN-13/D10 | 按实际闭包覆盖02/03/06/07，补14并消除旧矛盾。 |
| W-29 | 中 | 已修订 | WIN-06/13 | S2用Fake，学习恢复联测归S7。 |
| W-30 | 中 | 已修订 | WIN-06/09 | 窗口控件/偏好默认/Placement行为唯一归属。 |

| U-F04 | 中 | 已覆盖（本轮H1） | README8.1/CORE-57 | 需求、Q、ADR及补充全文进入材料。 |
| U-F05 | 中 | 已修订 | README8.1/8.6 | 删除反向依赖必需契约矛盾；消费片段可显式追加。 |
| U-F06 | 中 | 已覆盖（v5.3.1） | README8.2 | run_all与标题模块编号模板已一致。 |
| U-F10 | 中 | 已修订 | D1/D2/tools/sadd/stats.mjs | 当前96卡由工具生成，历史83保留。 |
| U-F13 | 中 | 已修订 | CORE-16/C8/Q40 | 工具用夹具验行为；真实四包覆盖/审校归M-CONTENT并列冻结前提。 |
| U-F14 | 中 | 已修订 | README5/8、CORE-41、AND-12/WIN-13 | 验证方式列/环境矩阵与责任分工，未运行pending。 |
| U-F16 | 中 | 已覆盖（v5.3.1） | CORE-01 | 共享UI不得平台判断已在权威规则。 |
| U-F17 | 中 | 已覆盖（v5.3.1） | CORE-01/AND-01/WIN-01 | Flutter只app/.flutter-version、Rust只rust-toolchain.toml。 |
| U-F21 | 中 | 已覆盖（本轮H3） | CORE-58 | S2独立外观入口，S6设置只链接。 |
| U-F22 | 中 | 已修订 | README8.4/CORE-02 | 共享文件单写，逐code owner登记，安装点各自文件/聚合由lead。 |
| U-F23 | 中 | 已修订 | README8.4 | 变更单→owner/ADR→消费者→重生成材料→D复检→关闭回流。 |
| U-F24 | 中 | 部分修订 | Q39/C8 | 发布许可证产品决策待确认；数据许可未获书面证据，分配角色与截止，不伪称完成。 |

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

### D.9.1 检查与证据边界

本轮只修订设计文档，没有Rust/Flutter产品代码可运行。`check.mjs`、`xref.mjs`、`mat.mjs`用相同解析器重跑修订前快照和当前文档；未修改基线或原评审。交叉引用是启发式，不能把计数当完整性证明。重复错误码的消费者改列“错误码引用/唯一定义卡/本卡处理”，唯一所有者仍保留标准定义表；op按已有契约逐行列出，未以删引用或修改解析器降低指标。

| 脚本/指标 | v5.2.1基线 | 本轮结果 |
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

## D.10 当前逐卡汇总（2026-10-20，v5.3.1）

本节覆盖96张有效卡，是唯一当前状态；D.4～8保留历史。第3列原等级已逐行摘自 core-a/core-b/core-c/plat-and/plat-win 的“逐卡评级”表，本表即基线内的记录，本地 temp/base 报告只作出处；第5列取 2026-10-20 五份 v5.3 复核报告（core-a、core-b、core-c、plat-win、core-ui）的修订后等级，多份报告评级不同时取较低者，`—`为本轮未被复核；第6列在第5列基础上按 §D.11 的 v5.3.1 修订记录调整：引起 C 的问题已全部修订闭合的升为 B，仍有P1残留的保持 C，该列由修订方给出、未经独立复核，不构成就绪结论；A/B/C保留原含义。修订后评级只表示本轮对P0相关条文的复核，非完整实现认证。`—`表示未做本轮语义复核，不能沿用历史“已修订”作为就绪结论。C卡必须先完成所列P1修订，其他卡开工前也须完成README §8.5整卡检查；暂行Q及外部门槛按README执行。

| 编号 | 阶段 | 评审等级（2026-10-19） | v5.3 修订后 | v5.3 复核（2026-10-20） | v5.3.1 修订后（未独立复核） | 当前状态 | 待定ADR影响（含依赖闭包） | 遗留阻塞/未复核原因 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CORE-01 | S0 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | v5.3.1：锁定文件与 [R18] 验收已补（core-a）。依赖规则冲突已消除；预算、真实锁定与产物门禁尚未整卡复核。 |
| CORE-02 | S0 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | AST/CONTENT命名空间与共享格式清单已补；Diagnostic.args/domain 类型与JSON往返的原评审问题仍待P1。 |
| CORE-03 | S0 | B | — | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（core-a）遗留：8 个函数与返回码齐全；缺响应信封、Dart 回调机制，句柄 API 无产生者 |
| CORE-04 | S0 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | firstFrameHooks/分层与网络唯一名单已明示；端口全套、白名单执行归属仍待整卡复核。 |
| CORE-05 | S1 | C | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 14种节点与15条精确JSON、ID/seed边界已复核；文档参照通过，Rust/跨端黄金实现未运行。 |
| CORE-06 | S1 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 矩阵边界及判分域向量已修；诊断/源位置DTO、信封budget双入口仍待P1。 |
| CORE-07 | S1 | C | C | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 内置数据归CORE-56已解决；notation各op的请求/响应DTO仍不完整（core-a #19），不能直接开工。 |
| CORE-08 | S1 | C | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | i128/eV/N_A/u及UnitRepo归属已复核；实际注册表/持久化联测与边界实现未运行。 |
| CORE-09 | S1 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | parse编排移FFI、领域依赖已修；CheckResult/TypedAst完整线格式仍待P1。 |
| CORE-10 | S1 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 常数解析边界与独立数值参照已修；自动求根扫描细节、结果DTO尚待整卡复核。 |
| CORE-11 | S1 | B | — | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（core-a）遗留：签名缺 UnitRegistry/取消；SX 向量为文字描述 |
| CORE-12 | S1 | B | B | C | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | v5.3.1：N1 字体注入已改为只取 CORE-56 快照（core-a）。字体最早来源已由CORE-56补齐；字体下标稳定性、缺字形诊断返回形态仍待P1。 |
| CORE-13 | S2 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | v5.3.1：派生更新与 rotate_device_id 已补（core-a/core-b）。时钟/业务/outbox事务与payload真值已明确；Store.open DTO、密钥跨FFI敏感处理仍待P1。 |
| CORE-14 | S3 | C | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | Validation、短中文搜索、用户单位与包投影列/时序已对照；Q32仍待确认，实际SQL与缓存/同步联测未运行。 |
| CORE-15 | S4 | C | C | C | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | v5.3.1：order 10 钩子归 CORE-51、高水位改 security_state.json 镜像（core-a/core-b）。设备级元数据与安全水位已修；tough API与sans-I/O适配未锁定验证（core-a #32），仍未就绪。 |
| CORE-16 | S4 | C | C | C | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | v5.3.1：distractors 元素 schema 与 reviewed_at 格式统一（core-a）。CONTENT命名空间、EntryType schema、干扰项审校已补；真实内容覆盖/许可与代码卡验收混合问题仍待P1拆里程碑（core-ui F13）。 |
| CORE-17 | S4 | C | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 时间输入、外围状态表、fsrs6.6.2官方API已核实；Q34待确认，真实FS黄金输出与跨端重放实现待编码验收。 |
| CORE-18 | S4 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 定义域单侧失败与GX数学参照通过；答案符号绑定/Grade DTO仍待P1完整复核。 |
| CORE-19 | S4 | C | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | v5.3.1：effective_new_limit、dictation、干扰项来源已补（core-b）。选卡/配额/RecentStats/审校来源与错误返回已补；Q33待确认，完整学习会话与持久化实现尚未验收。 |
| CORE-20 | S4 | C | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | StatsInput与全量缓存失效已修；提醒设置及跨语言规模待整卡复核，30人30天效果试点为外部交付。 |
| CORE-21 | S2 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | WrapRecord字节/CBOR/KDF与时间输入已复核；随机源及加密I/O与领域约束尚需P1核对。 |
| CORE-22 | S2 | C | C | C | C | 未就绪（C：先修订） | —（仍须开工锁版本/平台探针） | v5.3.1：N-02 已修（ADR-V5-32 代理层令牌族表）；server+app 双构建单元规模仍待P1。Casdoor职责/授权流程/auth_time已明确；server+app范围仍偏大，供应版本PKCE/刷新轮换/验证码真实集成尚未通过，不得宣布认证上线。 |
| CORE-23 | S2 | C | C | C | C | 未就绪（C：先修订） | —（仍须开工锁版本/平台探针） | v5.3.1：N-05 注册注释、N-01 历史密钥已修；AccountState 定义待P1。S2隐私守卫前置与升级投影边界已修；Dart AccountState定义、CORE-45闭包和双构建单元规模仍待P1。 |
| CORE-24 | S6 | C | C | C | C | 未就绪（C：先修订） | —（仍须开工锁版本/平台探针） | v5.3.1：N-09 merge_guest 签名已补；fml-sync→fml-store 方向待P1。跨库journal补偿已修、op已逐项列行；fml-sync依赖fml-store违反领域方向、输入DTO完整性仍待P1。 |
| CORE-25 | S6 | B | B | B | B | 未就绪（待 §8.5.1 复核） | V5-18：正式托管受阻 | 近期认证码与WrapRecord wire唯一归属已修；wrap_kind/幂等细节、错误表列仍待P1复核。 |
| CORE-26 | S6 | C | C | C | B | 未就绪（待 §8.5.1 复核） | V5-18：正式托管受阻 | v5.3.1：负载改逐字段 clocks、device_seq 单一来源、rotate_device_id（core-b，ADR-V5-33）。字段时钟、确定性merge ID已修；Envelope Rust类型、同步/存储职责与领域无I/O边界仍待P1。 |
| CORE-27 | S6 | B | B | — | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | WrapRecord格式依赖已修；备份跨卡业务表清单、迁移与导入失败边界尚待整卡复核。 |
| CORE-28 | S2 | C | C | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 整体前移S2、GuardContext及网络名单已修；DebugInfoSource、复现包op闭包和日志规模仍待P1。 |
| CORE-29 | S5 | A | — | — | — | 未复核（无开工结论） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（core-b）遗留：契约、错误表、注册表语义完整；仅 `render_ink` 跨架构字节一致需注意浮点 |
| CORE-30 | S5 | B | — | — | — | 未复核（无开工结论） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（core-b）遗留：范围写“透视/倾斜校正”，契约只有 deskew 布尔且无算法；阈值依赖 M0 标定与外部标注集 |
| CORE-31 | S5 | B | — | — | — | 未复核（无开工结论） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（core-b）遗留：`postprocess`/`apply_correction` 返回值非 Result，却定义了 3 个错误码；`symbol_env_ref` 由 CORE-14 解析而 CORE-14 不在依赖 |
| CORE-32 | S5 | C | C | C | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | v5.3.1：历史密钥经既有别名包装（core-b）。历史密钥槽位/SessionKey随机包装已修；Page类型与pending_cloud op DTO仍待P1（core-b逐卡表）。 |
| CORE-33 | S5 | C | C | C | C | 未就绪（C：先修订） | V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | v5.3.1：配额与冻结状态待P1；V5-16/V5-18 待定。RecognitionMode wire已补；配额预占/退还、冻结状态、供应商预算仍待P1与V5-16真实交付门槛。 |
| CORE-34 | S5 | B | B | — | B | 未就绪（待 §8.5.1 复核） | V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 网络入口、模式DTO与错误码唯一所有者已修；symbol_hints 32/50上限冲突仍待P1。 |
| CORE-35 | S5 | B | B | B | B | 未就绪（待 §8.5.1 复核） | V5-13：Fake可先行，真实模型受阻 | v5.3.1：范围改为 InferenceEngine+FakeEngine，fake 仅测试构建；M-MODEL 负责人见 Q37。Fake管线验收与M-MODEL真实指标分开；InputSpec完整定义、运行时探针与模型许可/性能未交付。 |
| CORE-36 | S2 | C | C | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 跨阶段钩子与首帧健康时序已修；账户界面/壳/路由组合规模及根Focus按键前提仍待P1拆分修正。 |
| CORE-37 | S2 | C | C | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | Widget/VM与声明面板绑定分层已修；约500行含编辑器/worker/绘制/DTO规模仍不可信，黄金图CI落点未补。 |
| CORE-38 | S3 | C | C | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | ui分层与库错误所有权已修；列表/详情/diff/草稿/回收站/单位等范围仍需P1拆卡，DTO与跨阶段验收未完整复核。 |
| CORE-39 | S4 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 用例路径及选卡契约同步；键盘命令与平台消费方一致性、路由交互未整卡复核。 |
| CORE-40 | S5 | C | C | C | B | 未就绪（待 §8.5.1 复核） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | v5.3.1：RecognitionFlow/InkController 路径移出 ui/（core-c）。模式与用例层分离已修；4个子界面+编排规模、probe失败发生在session前的状态及真实墨迹时延仍待P1。 |
| CORE-41 | S0 | C | C | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | DEP-5/6和网络名单已补；S0验收越阶段、ABI头路径与提交信息格式等原评审问题仍待P1。 |
| CORE-42 | S7 | B | — | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（core-c）遗留：versionCode 公式有歧义（01:5166）；密钥扫描正则未给出（01:5170）；回滚演练需要真机，不能自动化（01:5189） |
| CORE-43 | S7 | B | — | B | B | 未就绪（待 §8.5.1 复核） | V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 未做整卡复核；原评审（core-c）遗留：声称不依赖 CORE-45（01:5199），但 `email.*` 配置被归到 CORE-22（01:5209），验收又要跑发信集成与发信告警（01:5247、5250）；ADR-V5-18 与甲方账号属外部前提（01:5239、5244） |
| CORE-44 | S7 | A | — | A | A | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（core-c）遗留：步骤、返回码、DTO 信封都与 CORE-03 一致（01:5276-5279 对 01:463、477、488）；退出码约定清楚；可以直接编码 |
| CORE-45 | S2 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | Casdoor与EmailSender所有权已理清；限流错误语义复用与供应邮件真实到达率仍待P1/集成。 |
| CORE-46 | S6 | B | B | B | B | 未就绪（待 §8.5.1 复核） | V5-18：正式托管受阻 | 延迟钩子与升级补偿对接已修；KeySecret Dart类型、轮换重包装与真实恢复尚待P1。 |
| CORE-47 | S6 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 用例/Widget路径已修；防截屏端口、口令策略调用与DTO来源等原评审仍待P1。 |
| CORE-48 | S3 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 用例路径与库错误引用已修；S3验收引用S6跨设备同步、DTO来源仍待P1。 |
| CORE-49 | S4 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 统计输入、用例路径与权限码复用已修；Dart测试Rust枚举写法与完整页面联测仍待P1。 |
| CORE-50 | S5 | B | B | B | B | 未就绪（待 §8.5.1 复核） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 模式/密钥消费与VM路径已修；UI错误只引用所有者，完整历史/云端交互尚未整卡复核。 |
| CORE-51 | S4 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | S2守卫可用、用例路径已修；下载/资源投影恢复与断点续传联测未整卡复核。 |
| CORE-52 | S3 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | S1字体来源已明确；用例反向依赖ui绘制函数与导出全格式仍待P1。 |
| CORE-53 | S3 | A | — | A | A | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（core-c）遗留：范围小（约 300 行）、错误码与依赖齐全；只有 `AppLog` 一处跨闭包（01:4655），影响很小 |
| CORE-54 | S3 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 用例路径已修；共享层键位硬编码与CORE-14标签约束一致性仍待P1。 |
| CORE-55 | S2 | C | C | C | C | 未就绪（C：先修订） | —（仍须开工锁版本/平台探针） | v5.3.1：DesignGallery 与 AppLog 用途已补，规模重估约 495 行；首次实现超 500 行先拆 f（core-c）。FmlTheme/FmlTokens与自身gallery验收已补；令牌/预设/组件/动效范围仍超单卡实际规模，DesignWarmup未成完整契约，待P1。 |
| CORE-56 | S1 | 新增/无原评级 | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 新增S1卡，内置数据/快照/编排契约已复核；字体实际固定hash/许可文件、资源向量与构建实现尚未交付。 |
| AND-01 | S0 | B | — | — | — | 未复核（无开工结论） | —（仍须开工锁版本/平台探针） | v5.3.1：toolchain.versions 已补（core-a），仍未复核。未做整卡复核；原评审（plat-and）遗留：生产组装引用 `app/test/fakes/` 中的 Fake（L168）；MainActivity 扩展方式未定义（L176）；targetSdk 没有数值（L187）；MAJOR+1 测试库的制作方法未给（L204） |
| AND-02 | S2 | C | C | — | C | 未就绪（C：先修订） | —（仍须开工锁版本/平台探针） | 窗口属性唯一所有者已前移；权限白名单仍与通知/biometric/网络依赖冲突（AN-F01），待P1。 |
| AND-03 | S5 | C | C | — | C | 未就绪（C：先修订） | —（仍须开工锁版本/平台探针） | P0未涉及，保留原C；原评审（plat-and）遗留：“导入会话结束时删除副本”（L494/L502）没有对应的 CORE-04 API；PickMultipleVisualMedia 不支持 maxCount=1（L469）；规模已到上限（L510） |
| AND-04 | S5 | B | — | — | — | 未复核（无开工结论） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（plat-and）遗留：清晰度阈值没有初值（L550）；拍摄期间进程被杀的结果回传未处理（L547） |
| AND-05 | S2 | B | B | — | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | createCount唯一来源已修；trimMemory语义/API34行为和设备内杀进程验收仍待P1。 |
| AND-06 | S2 | C | C | — | C | 未就绪（C：先修订） | —（仍须开工锁版本/平台探针） | P0未涉及，保留原C；原评审（plat-and）遗留：`BIOMETRIC_STRONG &#124; DEVICE_CREDENTIAL` 在 API 28-29 不受支持（L399）；API 26-29 使用 10 s 时效密钥，L409 的指纹变更失效验收必然失败 |
| AND-07 | S5 | A | — | — | — | 未复核（无开工结论） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 未做整卡复核；原评审（plat-and）遗留：签名与 CORE-37/40 一致，算法与阈值完整，验收可自动化；只是内联时省略了尾注释（低） |
| AND-08 | S4 | B | — | — | — | 未复核（无开工结论） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（plat-and）遗留：内联签名删掉了语义注释（L744-749）；PendingIntent 标志与热启动 onNewIntent 未规定（L776-779）；ROM 组件名未列出（L788）；通道没有 title/detail 字段（L774） |
| AND-09 | S2 | B | — | — | — | 未复核（无开工结论） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（plat-and）遗留：使用依赖闭包外的 AppLog（L713）；测试 CA 的信任方式与禁止 badCertificateCallback 矛盾，构造器也没有注入点（L711/L718/L689） |
| AND-11 | S7 | B | — | — | — | 未复核（无开工结论） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（plat-and）遗留：未裁剪 .so 的来源路径未给（L843）；`[R40]` 标签与 scan_secrets 不符（L860） |
| AND-12 | S7 | C | C | — | C | 未就绪（C：先修订） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | P0未涉及，保留原C；原评审（plat-and）遗留：采样口径与 CORE-01 L306 冲突（L896/L911）；引用了不存在的“AND-03 测试注入路径”（L918）；依赖闭包外的草稿恢复（L920） |
| AND-13 | S2 | B | B | — | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 属性表改引用AND-02，计数改AND-05；设备内adb、IME标志与后阶段返回行为仍待P1。 |
| WIN-01 | S0 | B | — | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | v5.3.1：toolchain.versions 已补（core-a/plat-win）。未做整卡复核；原评审（plat-win）遗留：toolchain.versions 键与 ADR-V5-15 的分工不一致（L197）；`cameras` 字段名错误（L182）；platformInstallers 清单漏了 WIN-14/15，顺序约束散落在各卡（L183）；未约定 C++ 通道的线程规则（L194） |
| WIN-02 | S7 | C | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 依赖解环、Inno选择、等待进程与原子版本文件已修；脚本与稳定启动器协议的真实安装/卸载验证未执行。 |
| WIN-03 | S7 | C | C | C | C | 未就绪（C：先修订） | V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | v5.3.1：confirmHealthy 1500 ms 上限已补（plat-win）；仅按 CN 验签（W-12）待P1。启动器拆卡、首帧健康及退出等待已修；更新仅CN验签风险仍在P1 W-12，签名轮换未定义，不得真实发布。 |
| WIN-04 | S5 | B | — | — | — | 未复核（无开工结论） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 未做整卡复核；原评审（plat-win）遗留：工作线程回调与 WM_DROPFILES 的 WndProc 挂接方式未说明（L557/L568）；HEIC 还需要 HEVC 扩展（L564/L587）；测试注入环境变量会留在 Release（L595） |
| WIN-05 | S5 | B | — | — | — | 未复核（无开工结论） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 未做整卡复核；原评审（plat-win）遗留：契约清楚；验收写“七种格式”实列 9 种（L675）；CF_* 写入的线程与 OpenClipboard 重试未说明 |
| WIN-06 | S2 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 转发退出码与最小化入口已补；前台激活竞态、线程池通知和S2验收借用学习页等仍待P1。 |
| WIN-07 | S2 | B | — | — | — | 未复核（无开工结论） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（plat-win）遗留：Win32 下 KeyCredentialManager 缺 hwnd 互操作，Hello 对话框可能出现在窗口后面（L469），需在 M0 验证 |
| WIN-08 | S5 | B | — | — | — | 未复核（无开工结论） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 未做整卡复核；原评审（plat-win）遗留：WM_POINTERDEVICECHANGE 需先 RegisterPointerDeviceNotifications；笔属性 SetProp 的目标窗口是 Flutter 子窗口还是顶层窗口不明（L788–790）；按键分发顺序依赖 CORE-36 的错误前提（L803） |
| WIN-09 | S4 | B | B | B | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | 独立首帧托盘与应用锁可达性已修；WindowsPrefs构造时机、TaskbarCreated和退出销毁挂钩仍待P1。 |
| WIN-10 | S2 | B | — | — | — | 未复核（无开工结论） | —（仍须开工锁版本/平台探针） | 未做整卡复核；原评审（plat-win）遗留：构造函数不接收 lifecycle，却要“resumed 后刷新代理”（L1129/L1141）；206 追加不校验 Content-Range（L1138）；“步骤同 AND-09”引用了依赖闭包外的卡（L1134） |
| WIN-12 | S7 | B | — | — | — | 未复核（无开工结论） | V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 未做整卡复核；原评审（plat-win）遗留：Release 默认不生成 PDB，符号归档会失败（L1274）；会给 Microsoft 运行库 DLL 重新签名，并按 CN 核对（L1263/L1269）；ADR-V5-12/15 待定 |
| WIN-13 | S7 | C | C | C | B | 未就绪（待 §8.5.1 复核） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | v5.3.1：禁 GPU 矩阵已修，依赖经闭包覆盖（plat-win，不加冗余依赖）。Profile/Release与禁GPU方法已修；v5.3.2核实02/03/06/07在闭包，补WIN-14；真实驱动/性能矩阵仍为外部前提。 |
| WIN-14 | S5 | B | — | — | — | 未复核（无开工结论） | V5-13：Fake可先行，真实模型受阻；V5-16：Fake可先行，真实云识别受阻；V5-18：正式托管受阻 | 未做整卡复核；原评审（plat-win）遗留：KeyChord.encode 示例的位宽与 WIN-15 定义不一致（L874 vs L941）；Conflict 相等性需要 ==/hashCode（L856）；规则①的理由依赖按键分发顺序（L888） |
| WIN-15 | S2 | C | C | — | C | 未就绪（C：先修订） | —（仍须开工锁版本/平台探针） | 删除本地lookup误写成op；根Focus分发机制、StudyCommand重复定义、平板检测原P1问题未修。 |
| WIN-16 | S7 | 新增/无原评级 | B | C | B | 未就绪（待 §8.5.1 复核） | —（仍须开工锁版本/平台探针） | v5.3.1：N1～N3 已修：opened 确认、恢复格式与 --register-install，备份含 pack_meta.db（plat-win/core-a）。新增S7独立C++卡，状态转换/原子写/进程等待/恢复失败路径已对照；实际故障注入和断电恢复尚未运行。 |
| CORE-57 | S0 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| CORE-58 | S2 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| CORE-59 | S2 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| CORE-60 | S3 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| CORE-61 | S3 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| CORE-62 | S2 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| CORE-65 | S2 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| CORE-63 | S2 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| CORE-64 | S5 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| CORE-66 | S6 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| CORE-67 | S0 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| CORE-68 | S6 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |
| AND-14 | S3 | 新增/无原评级 | — | — | — | 未复核（无开工结论） | 按依赖闭包继承外部门槛 | P1 拆分/新增；待独立复核，不由修订方提升等级。 |

### D.10.1 P1接续事项

- v5.3.1 后仍为 C 的卡：CORE-22（双构建单元规模）、CORE-23（AccountState）、CORE-24（fml-sync→fml-store 方向）、CORE-33（配额与冻结状态）、CORE-55（规模临界）、WIN-03（W-12 验签身份）、AND-02/03/06/12、WIN-15（本轮未复核，保留原 C）。
- 整卡语义复核按 README §8.5.1 进行，S0 七张卡（CORE-01、02、03、04、41、AND-01、WIN-01）优先；AND-01 尚未被任何复核覆盖。
- C卡首先处理规模与职责：CORE-36/37/38/40/55等先拆卡，不以“约500行”当完成证据；拆卡后同步阶段、索引、闭包与当前汇总。
- CORE-03响应信封/NativeCallable、CORE-07/09/23/24/26/32 DTO，以及CORE-02类型/JSON一致性继续按原评审；本轮逐op列行不等于DTO全部补全。
- Windows P1 W-7/8/10/11/12：按键分发、平台线程与WndProc、笔注册、PDB/可复现构建、签名公钥身份与轮换/第三方运行库排除仍需处理；不得把启动链P0通过等同真实发布安全。固定启动器协议为1，未来升级须专项ADR。
- Android P1 AN-F01/03/04等：合并清单权限、生物识别API26～29策略/失效规则、导入生命周期与测试注入仍保留，未借P0越界宣称修复。
- 材料体量、真实内容覆盖/许可、真机与人工验收拆里程碑继续按P1 U-F02/F13/F14；模型真实交付走M-MODEL。临时脚本未入库，正式CI与材料生成器由P1再设计。
- 材料体量（U-F01/N12）：README §8.1 第6项的暂行裁剪做法在 P1 材料生成器就绪前使用；CORE-19/20/21 行内错误码清单改表、Q33 确认后的向量更新转P1（§D.11）。
- Q32～Q37保持暂行默认，不擅改Q1～Q31；后续确认若改变行为须同步对应卡、ADR与测试向量。

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

按 README §8.5.1 记录。每次复核一行；结论为“通过”后，把 §D.10 该卡“当前状态”改为“就绪（D.12 第 n 行）”。依赖契约被修改后需重新复核的，另起一行，不改旧行。截至 2026-10-20 尚无记录，S0 七张卡（CORE-01、CORE-02、CORE-03、CORE-04、CORE-41、AND-01、WIN-01）待 lead 指派复核人。

| 序号 | 卡 | 复核人 | 日期 | 材料字符数 / 是否裁剪 | a～g 结论 | S1～S6 结论 | 发现与处理 | 结论（通过/不通过） |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
