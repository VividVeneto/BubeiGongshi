# 附录 D：编码就绪检查记录 v5.1

> 版本：v5.1 ｜ 检查日期：2026-10-18（2026-10-19 补充 Q11、Q12 确认后的修订） ｜ 效力：说明性（规范性要求以 README 与 01～03 的模块卡为准）。
> 关联文档：[README](README.md)（§8.5 就绪定义、§6 待确认事项）、[01 公共核心](01-公共核心-v5.md)、[02 Android 端](02-Android端-v5.md)、[03 Windows 端](03-Windows端-v5.md)、[附录 A](附录A-架构决策与评审记录.md)（ADR-V5-12～22）。

## D.1 检查方法

- 对象：v5 的 69 张模块卡（CORE-01～44、AND-01～12、WIN-01～13），以及本次拆卡新增的卡。
- 清单：README §8.5 的 a～g 七项（结构与规模、依赖闭合、契约唯一、契约可编码、验收可测、追踪一致、外部前提）。
- 机械项（字段齐全与顺序、规模上限与构建单元、依赖编号方向、依赖与依赖图及模块索引一致、依赖无环、实施阶段覆盖与先后、README §5 与卡内 [Rxx] 双向一致）用一次性脚本检查，脚本不入库。修订前共发现 51 项问题；修订后 74 张卡、0 项问题。
- 语义项（类型与错误码可追溯、DTO 与表结构完整、验收可执行、外部前提）逐卡人工判断。
- 结论口径：**就绪** = 未修改即满足就绪定义；**已修订** = 修订后满足就绪定义；**待确认阻塞** = 缺信息且无法合理推断，暂不能编码。按 README §6 Q11～Q15 暂行默认值撰写的卡不算阻塞（Q11、Q12 已于 2026-10-19 确认；Q16 由 Q11 拆出，仍待确认），在“遗留问题”中注明。

## D.2 统计

| 文档 | 卡数（含撤销） | 就绪 | 已修订 | 新增卡 | 已撤销 | 待确认阻塞 |
| --- | --- | --- | --- | --- | --- | --- |
| 01 公共核心 | 52 | 0 | 44 | 8 | 0 | 0 |
| 02 Android 端 | 12 | 0 | 11 | 0 | 1 | 0 |
| 03 Windows 端 | 14 | 0 | 12 | 1 | 1 | 0 |

- 新增卡（9 张）：CORE-45 邮箱验证码与发信（自 CORE-22 拆出）、CORE-46 同步与升级协调器（自 CORE-26 拆出）、CORE-47 设置页与账户安全界面（自 CORE-36 拆出）、CORE-48 计算器、代入与计算链界面（自 CORE-38 拆出）、CORE-49 学习统计、提醒设置与自建书界面（自 CORE-39 拆出）、CORE-50 识别结果、云端确认与识别历史界面（自 CORE-40 拆出）、CORE-51 资源包下载、导入与管理界面（自 AND-10、WIN-11 抽出两端共用部分）、CORE-52 公式复制格式与富格式导出（2026-10-19 按 README §6 Q12 确认新增）、WIN-14 快捷键自定义（2026-10-19 按 README §6 Q11 确认新增）。
- 撤销卡：AND-10、WIN-11。两卡的内容是两端相同的 Dart 行为，并入 CORE-50、CORE-51，平台差异只剩端口实现（ADR-V5-19（待定））。编号不复用。
- 现行卡数：74 张（公共核心 51、Android 11、Windows 12）。

## D.3 共性修订

1. 组装层与平台接缝：CORE-04 增加 `composition/`（`FeatureRegistry`、`CompositionContext`、`Installer`、`entry.dart` 的 `runPlatformApp`），`PlatformPorts.platformInstallers` 供平台卡登记接缝实现；CORE-36 增加 `composeApp`、门面、启动钩子顺序表、路由归属表与外壳扩展接缝；平台卡不修改共享界面文件。
2. 每张卡补错误码表（错误码 / 级别 / 可重试 / 触发条件），级别统一为 error、warning、info。
3. 性能类验收只引用 CORE-01 全局资源预算表的行名；预算表补“本地模型识别”“本地模型首次加载”两行。
4. 验收标签统一为方括号形式，功能近似条款写作 `[R04][R04.h]`；README §5 最后一列按各卡验收标签重新生成。
5. 规模超出或跨多个构建单元的卡：拆卡，或在规模中写明主包与附属的行数（README §8.5 a）。
6. 外部前提统一写在“实现约束”末条；版本号在 M0 按 ADR-V5-15（待定）锁定，文档不写未核实的版本号。
7. 新发现的产品取舍列为 README §6 Q11～Q15（待确认），纯工程选择列为 ADR-V5-12～20（待定）。

## D.4 公共核心

| 编号 | 名称 | 结论 | 修改摘要 | 遗留问题 |
| --- | --- | --- | --- | --- |
| CORE-01 | 仓库骨架与工程约定 | 已修订 | 补命名约定与提交约定（type(模块编号): 摘要）；外部前提（工具链版本按 ADR-V5-15（待定） M0 锁定）；验收补 [R23] | — |
| CORE-02 | 错误码注册表与诊断模型 | 已修订 | 注册表字段表（code/namespace/severity/message_key/retryable/since/deprecated_since/http_status）与取值规则；FmlError JSON 形态（FFI 与服务端共用）；规模拆分主包与附属；新增 JSON 往返验收 | — |
| CORE-03 | C ABI 与 Dart 绑定 | 已修订 | FFI 返回码表（-1～-6 含触发条件）、fml_cancel 语义、回调线程与并发上限 64、capabilities 示例、DTO 映射规则（全局适用）；Dart CancelToken/FfiException/FfiCancelled 定义；CoreBinding.open(CoreLibrarySpec) 与 spec（多 isolate）、fml_call 线程安全、Dart DTO 归属规则 | — |
| CORE-04 | 平台端口契约 | 已修订 | （追加）组装原语 FeatureRegistry、CompositionContext、Installer、StartupHook，使各卡安装点不依赖编号更大的 CORE-36；规模 440 | — |
| CORE-05 | 公式 AST 与修订模型 | 已修订 | 补全 AST 辅助类型（NumberLiteral、UnitRef、各运算枚举、FunctionId 规范名）；从 CORE-07/09 迁入存储形类型 SymbolEnv/SymbolDecl/TypeDecl/MathKind/Validation/ConfirmRecord 以消除前向引用；CancelFlag；check_limits、from_canonical_json；规范 JSON 规则与 AST-01～05 向量；错误码表；FormulaItem 增 course，FormulaRevision 增 draft（CORE-14 需要）；FormulaNode 增 Hole(u16)（ADR-V5-17（待定）） | — |
| CORE-06 | LaTeX 子集解析与导出 | 已修订 | RawSymbol/RawHint 定义；engine.parse/engine.export DTO；错误码触发条件表；LX-01～10 往返向量；性能项改引 CORE-01 预算行；外部前提 cargo-fuzz nightly；白名单增 \fmlhole、错误码 PARSE_HOLE_UNFILLED、向量 LX-11 | — |
| CORE-07 | 符号表、记号方案与常数集 | 已修订 | SymbolEnv 等存储形类型迁至 CORE-05，本卡保留绑定与常数逻辑 | — |
| CORE-08 | 量纲与单位 | 已修订 | 量纲文本语法与 parse/to_text；UnitRegistryMut、UnitDefinition 定义；错误码触发条件（新增 UNIT_DIM_SYNTAX、UNIT_IN_USE、UNIT_DUPLICATE）；新增量纲文本验收；新增 units.list_user、units.delete_user（单位页需要） | — |
| CORE-09 | 类型推断与量纲校验 | 已修订 | MathKind、Validation 迁至 CORE-05；补 TypeDecl 量纲文本的解析规则；Hole 按未知类型处理，状态至多 Unresolved | — |
| CORE-10 | 计算器与数值求解 | 已修订 | DisplayPrecision、SolveCapability 定义；数值约定（f64、Brent 容差与迭代上限、自动 bracket 参数、一阶最坏情况误差传播）；CX-01～10 计算向量；错误码触发条件，新增 EVAL_TIMEOUT | — |
| CORE-11 | 公式间代入、推导链与计算链 | 已修订 | MatchLevel、RevisionSnapshot、AncestryLookup、RevisionLookup 定义；rank_candidates 增 include_cross_kind 参数；错误码触发条件 | — |
| CORE-12 | 排版 DisplayList | 已修订 | 补 WrapMode、Rect、PathSeg、DrawCmd 定义与 layout_version；明确 typeset.load_fonts/layout 请求响应，hit_test 改为 Flutter 侧按 hit_regions 判定；错误码触发条件；性能验收引用 CORE-01 预算行；Hole 虚线框；新增 op typeset.glyph_outlines（Flutter 无法按字形 ID 绘制）；2026-10-19：公开 glyph_outline 供 CORE-52 SVG 导出 | 数学字体最终选型待附录 C 许可审查；开发期用 Latin Modern Math |
| CORE-13 | 本地库 Schema、单写者与迁移 | 已修订 | 补 WriteTx/ReadTx、OutboxOp、IntegrityReport；迁移文件命名与序号规则；基础设施表 DDL；业务表归属清单（DDL 下放到归属卡）；错误码触发条件；外部前提 rusqlite/SQLCipher | — |
| CORE-14 | 公式库仓储 | 已修订 | 复用 CORE-05 的条目/修订类型，补 NewRevision、ItemView、Page、RevisionDiff 等；搜索语义；8 张业务表与 FTS5 列定义；新增 library.substitution_pool（CORE-11 引用）与 LIB_IMPORT_TOO_LARGE；CSV 细则；验收补 [R04.j] 标签与可测数值；mastery_cache 表归属移至本卡（CORE-14 搜索需按掌握度筛选），MasteryState 统一为 CORE-20 原有四态；calculation_plan 表归属移至 CORE-48；补脱离规则 | — |
| CORE-15 | 资源包格式、验签与安装 | 已修订 | 补 Manifest、ManifestEntry、EntryReader、SecurityState、UpdateMetadata、PackOffer；各 op 请求响应；installed_pack 表；11 个错误码触发条件表；外部前提（ed25519-dalek、zip、tough 等）；元数据验收 | 首个签名 key_id 须在发布前登记（CORE-16/43） |
| CORE-16 | 内容管线与课程内容包 | 已修订 | 补条目主要字段类型与取值表（考试范围、要求层级改用拼音代号）、命令退出码与报告 JSON、CONTENT_ 错误码、签名私钥格式；验收补 [R39] 独立条目与 [R04.f][R04.g] 标签；外部前提（YAML crate、离线签名机） | 各课程包内容按批次作为数据任务编写 |
| CORE-17 | 卡片生成与 FSRS 排程 | 已修订 | 补 EventFlags、RequirementLevel、FsrsParams、CardSchedule、DailyCaps、DueQueue、OptimizeOutcome；各 op 请求响应；study_card/review_event 表；重放顺序；错误码触发条件；FS-01～FS-08 样例；fsrs 版本核实为 6.6.2；评分映射明确归 CORE-19；规模声明附属 | — |
| CORE-18 | 三层判分器 | 已修订 | 以 GradeTarget/GradeAnswer 取代对 CORE-17 CardType 的引用（避免反向依赖）；补 RequiredForm、SamplePoint；抽样参数（点数、区间、容差、ChaCha8）；错误码触发条件；验收补 [R04.c][R04.e] 标签与预算行引用 | — |
| CORE-19 | 学习会话与组学习循环 | 已修订 | 补 BookSource、Chapter、AnswerMode、QuestionDto、QuestionSource、Distractor、RatingMap、GroupSummary、GroupState；计划字段取值范围；重现位置；各 op 请求响应；5 张表；错误码触发条件；验收补子需求标签、续学边界与自建书（R04.j）；新增界面边界 DTO（UiAnswer、AnswerSubmission、SessionInput、QuestionView 不含标准答案、UiCommand 含 Feedback/NeedSelfRate、RelatedFormula、TodayInfo）、Attempt.self_knew、op 表（books.get/update/delete、plan.get、today）、错误码 STUDY_BOOK_READ_ONLY、STUDY_INPUT_INVALID；Undetermined 自评流程明确 | — |
| CORE-20 | 学习统计、掌握度与本地提醒 | 已修订 | 补 Granularity、DayStat、MasteryDistribution、StatsCache；指标口径；新增 stats.due_count 与 STUDY_STATS_RANGE_INVALID；stats_cache 表；验收补 [R04.d][R04.i]；规模声明跨语言附属；新增安装点说明（installers.dart 追加一行） | — |
| CORE-21 | 密钥体系与加密原语 | 已修订 | 补 KeyPurpose/HKDF info、Sealed 字节格式、AAD CBOR 规则、恢复码改为 26 位数据 + 1 位 Crockford mod-37 校验（27 位）、口令策略、KdfParams 默认值、错误触发条件、KV-01～07 测试向量与外部前提 | — |
| CORE-22 | 服务端骨架与身份认证 | 已修订（拆分） | 原卡约 700 行超限：验证码与发信拆为 CORE-45；补全端点请求/响应、令牌有效期、EmailCodeService 端口、Dart ApiClient/TokenStore、表结构、错误码触发条件表；身份服务形态记 ADR-V5-14（待定）；新增 GET /v1/devices（设备管理界面需要） | ADR-V5-14（待定） M0 定案 |
| CORE-23 | 账户状态、登录边界与本机解锁 | 已修订 | 补 GuestLocked 状态与启动规则、device_registry 表、BlobKind 与平台密钥别名约定（与 AND-03 一致）、op 请求/响应表、注册/找回口令/验证码用例、TokenStore 实现、错误码触发条件；去掉应用自有 PIN（改由系统认证），附属声明 | AND-03/WIN-04 须提供 fml://auth/callback 深链 |
| CORE-24 | 游客转注册与游客并入 | 已修订 | 补 UpgradeMode/AccountKeyMaterial/StepInput/KeyOutput、abandon、步骤完成条件与重入表、upgrade_journal/account_key_wrap/account_key 表、MergeInto 两种本地情形、UUIDv5 命名空间与 name 编码、op、错误码触发条件；原 UpgradeIo 回调改为“调用方传入网络结果”的纯本地步进（核心无 Rust→Dart 网络回调），联网协调归新卡 CORE-46 | — |
| CORE-25 | 服务端同步存储与账户删除 | 已修订 | 补全端点请求/响应（新增 sync/reset、keys/min-version、删除状态查询）、Envelope 字段类型表、游标格式、表结构、配额数值、删除状态机、错误码触发条件表与外部前提；验收补快照、重置、越权 | 对象存储产品随 CORE-43 选定 |
| CORE-26 | 同步引擎（加密、合并与隔离） | 已修订 | 改名“同步引擎（加密、合并与隔离）”：核心无 Rust→Dart 网络回调，原 SyncTransport 改为 prepare_push/ack/apply_pull 等本地步进 op；补实体类型与 KeyPurpose 映射、负载 CBOR 与 AAD、字段逻辑时钟、merge_choice 确定性 ID、0026_sync.sql 表、错误码触发条件；依赖补 CORE-19 | 网络协调见 CORE-46 |
| CORE-27 | 备份导出与恢复 | 已修订 | 补 .fmlbackup 字节格式（头、WrapRecord、1 MiB 分块 AEAD、末块标记）、范围→表映射与永不导出表、两阶段恢复（prepare/commit/discard + token）、Merge/Replace 逐表规则、replay 与缓存处理、FFI op、7 码错误表；去掉与 CORE-13 重复的迁移前快照；识别历史不导出（资产归 CORE-32）；依赖补 CORE-17 | — |
| CORE-28 | 隐私守卫、日志与复现包 | 已修订 | HttpRequestSpec 改为 CORE-04 的 HttpRequestDto；放行规则表（状态×用途）；ConsentVerifier 接口反转对 CORE-34 的依赖；GuardContext；LogValue 类型层面禁止文本；Rust 日志与 core.log_init；复现包移到 Dart（合成源码重排版）+ 脱敏扫描规则；V1 不提供诊断上报（diagnostics 恒拦截）；错误码表；依赖补 CORE-03；规模主包/附属；新增安装点说明（installers.dart 追加一行） | 组装层（CORE-36/平台 composition）须实现 GuardContext 并只暴露 NetworkGuard |
| CORE-29 | 识别契约与后端注册 | 已修订 | PreparedImage（CORE-30 产物，反向依赖）改为本卡 RecogImage；补 AccountKind/InputKind/CorrectionHint/AlignSpan，expected_type 改为 CORE-05 MathKind；Registry 分本地后端与远程描述符，run 检查顺序；墨迹渲染参数（tiny-skia+png 确定性）；FFI op recog.backends/register_remote/run；错误表 | — |
| CORE-30 | 图片解码与预处理 | 已修订 | 补 ImageFormat/ImageInfo/WorkingImage；FFI op 改为暂存区文件路径进出（不经 JSON 传图）；8 码错误触发表；外部前提 image/zune-jpeg/image-webp/kamadak-exif 与 fuzz 目标；性能验收引用 CORE-01 预算行 | — |
| CORE-31 | 识别候选后处理与忠实转写 | 已修订 | 依赖补 CORE-08（UnitRegistry）；评分公式；FFI op recog.postprocess/correct/final_check；白名单过滤规则；错误表新增 RECOG_SPAN_INVALID | — |
| CORE-32 | 识别会话状态机与历史 GC | 已修订 | 补 SessionState/InputSource/AssetKind/TransitionPayload/PendingCloudJob/SessionSummary/GcPlan/GcReport/RecoveryReport/HistoryFs；五张表 DDL（0032_recognition.sql，history_key 存于 recognition_counter）；状态转换合法表；FFI op 请求响应；错误表（新增 RECOG_TRANSITION_INVALID）；删除“另存为公式附件”（V1 用 Pin 代替）；规模主包/附属；CORE-13 归属清单补 recognition_counter、pending_cloud_job；新增 recog.settings.get/set op 与 recognition_counter 的 keep_last、history_disk_cap_mb 列 | — |
| CORE-33 | 服务端云识别网关与 worker | 已修订 | 新增 GET /v1/recognition/policy 与 POST /v1/recognition/consents（含监护人确认）；jobs 请求改带 consent_id + policy_version；取消语义；ProviderPrompt/ProviderOutput/ProviderError 定义；五张表 DDL；worker 取任务方式；配置键与默认配额；12 行错误表；外部前提；同意与哈希验收；规模改 480 | ADR-V5-16（待定） 云识别供应商（待定，M0 定案） |
| CORE-34 | 云识别客户端与授权回执 | 已修订 | 与 CORE-33 新接口对齐（policy/consents/jobs）；同意改由服务端记录（删除本地 consent_receipt 表）；年龄自我声明 + 监护人确认；实现 ConsentVerifier 并给出校验规则；幂等键用 UUIDv5(session, imageHash) 免持久化；recog.register_remote 登记时机；状态映射表含会话状态；错误表（新增 CLOUD_TOKEN_EXPIRED、CLOUD_PREVIEW_STALE）；外部前提；新增安装点说明（installers.dart 追加一行） | 监护人身份不核验，按 README §6 Q14（待确认）暂行默认撰写 |
| CORE-35 | 本地识别模型后端 | 已修订 | 模型扩展字段从 manifest 移到包内 model/model.json（原写法与 CORE-15“未知字段拒绝”冲突）；给出 model.json 全字段；InferenceEngine 内部抽象 + FakeEngine，使运行时未定案也可编码；预处理与束搜索流程；FFI op recog.local.register/unregister/unload_all；错误表；卸载时机；CORE-01 预算表新增两行 | ADR-V5-13（待定） 推理运行时（待定）；实际模型与许可待附录 B/C 实验结论 |
| CORE-36 | 应用壳、组装层、账户入口与导航 | 已修订（拆分） | 改名“应用壳、组装层、账户入口与导航”；新增组装层 composeApp 与 installers.dart 安装点机制（后续卡各追加一行）、AppDeps、SyncFacade/UpgradeFacade 门面及 Disabled 实现（原 CORE-46 引用但未定义）、启动钩子 order 表与登记者、账户入口含邮箱验证码与找回口令路由；依赖加 CORE-22；设置页拆到新卡 CORE-47 | — |
| CORE-37 | 公式渲染组件与编辑器 | 已修订 | 重写：源码为唯一事实、UTF-8/UTF-16 换算、停靠点导航、空位 \fmlhole 与 15 种模板片段、删除/撤销/粘贴/模式切换规则、EditorWorker 后台 isolate、字形路径绘制、错误码与界面行为表；依赖去掉 CORE-36，加 CORE-04、CORE-08；新增 EditorWorker.layoutStatic 与 MathText（只读公式显示，供 38/39/48/49 使用）；2026-10-19：去掉 FormulaRichCopy，改为 FormulaCopyFormat、FormulaCopier 接缝与共享 FormulaCopyButton（“复制为”菜单） | 默认输入模式不保存偏好，按 README §6 Q13（待确认）暂行默认撰写 |
| CORE-38 | 公式库界面 | 已修订（拆分） | 原卡含公式库+计算器+代入+计算链，超出 500 行；本卡只保留公式库界面：路由、LibraryVm/FormulaDetailVm/FormulaEditVm(SaveOutcome)/ImportWizardVm/UserUnitsVm；附属草稿仓储与 formula_draft 表及 library.draft_* op；修正原卡错误 op 名；错误码与界面行为表；验收补 [R04.j]、[R08]、[R15]；新建页接受 NewFormulaArgs 预填 LaTeX 并以 Saved 作为返回值（供 CORE-50）；2026-10-19：详情页与列表菜单加入复制公式（CORE-37 FormulaCopyButton）；`/library?search=1` 聚焦搜索框（供 WIN-08 查找快捷键） | — |
| CORE-39 | 学习会话界面 | 已修订（拆分） | 原卡含统计、提醒与自建书且依赖 CORE-40（违反依赖方向）；改为学习会话界面：路由、StudyHomeVm/BookshelfVm/PlanSettingsVm/SessionVm（SessionScreen 由 UiCommand 驱动）、AnswerInputRegistry 扩展点（手写由 CORE-40 注册，依赖倒置）；错误码与界面行为表；验收补 R04.a/d/e/f/g/h 方括号标签 | — |
| CORE-40 | 识别流程编排、手写画布与图片预处理界面 | 已修订（拆分） | 原卡页面类只有空壳且无流程定义；改为 RecognitionFlow 流程控制器（sealed RecognitionStep，逐步对应 CORE-32 合法转换与 op 调用）、InkController/InkCanvas、CropEnhancePage、HandwritingAnswerInput（注册到 CORE-39 扩展点）、installRecognition；错误码与界面行为表；验收覆盖 R06/R31/R32/R33/R40/R26/R04.e/R03 | 缩略图资产（AssetKind::Thumbnail）的生成方未定义，暂由 Confirmed 图兼用 |
| CORE-41 | CI 门禁与可维护性度量 | 已修订 | 补检查脚本的命令行、输出格式与退出码、规则编号表；新增 check_unsafe（与 CORE-01 允许清单一致，修正原文“只允许 fml-ffi”）、check_sadd（就绪定义机检）、run_all；工作流只编排；规模声明主包与附属 | Dart 圈复杂度只能近似统计 |
| CORE-42 | 发布流水线、版本矩阵与回滚 | 已修订 | 补脚本命令行；新增 size_gate、scan_secrets、repro_check；可复现范围收窄为 Rust 核心库与资源包；回滚改为 roll-forward（两端不支持降级安装）；依赖补 CORE-13 | — |
| CORE-43 | 服务端部署、资源分发与监控 | 已修订 | 重写：部署清单文件逐个定义（Dockerfile/compose/config.example.toml/required_keys.txt+preflight.py/backup/restore/alerts.yaml/keys.md/tuf/refresh.sh）；新增 server/src/ops/ 指标与健康检查；指标与告警阈值表；依赖补 CORE-45；签名密钥保管落到 keys.md；部署地域与产品选型引 ADR-V5-18（待定）；发信计数改由 CORE-45 经 metrics 门面上报，避免 CORE-43→CORE-45 反向依赖 | 云厂商与对象存储产品待 ADR-V5-18（待定） 定案；发信与云识别供应商账号由甲方开通 |
| CORE-44 | 鸿蒙预留与 C 头文件消费者验证 | 已修订 | build.sh 参数与退出码；consumer.c 五步检查（去掉需要字体的 DisplayList 步骤，改为 engine.check 与未知 op 错误路径）；端口对应表覆盖 CORE-04 全部 12 个端口；CI 作业与依赖准入规则 | OpenHarmony SDK 版本与下载账号在 M0 办理；鸿蒙目标只编译不运行 |
| CORE-45 | 邮箱验证码与发信 | 已修订（新增卡） | 自 CORE-22 拆出：邮箱验证码生成/存储/限流、/v1/auth/email-codes、EmailSender 与阿里云/腾讯云/Fake 实现、主备切换；README §5 R24 与附录 A ADR-V5-11 同步 | 发信账号与域名由 CORE-43 部署注入 |
| CORE-46 | 同步与升级协调器 | 已修订（新增卡） | 自原 CORE-26 拆出 Dart 侧网络协调：SyncApi、SyncCoordinator、UpgradeCoordinator、KeyService；异常处理表；实现 CORE-36 定义的 SyncFacade/UpgradeFacade；SyncStatus 等类型移至 CORE-36 facades.dart，UpgradeCoordinator.run 改用门面类型；新增安装点 installSync | CORE-36 须定义 SyncFacade/UpgradeFacade；平台组装（AND/WIN composition）须注入实现 |
| CORE-47 | 设置页与账户安全界面 | 已修订（新增卡） | 设置页与账户安全界面（从 CORE-36 拆出）：设置子路由、同步状态、升级向导、恢复码一次性展示、设备管理、导出/恢复、keep_last；视图模型可单测 | — |
| CORE-48 | 计算器、代入与计算链界面 | 已修订（新增卡） | 由 CORE-38 拆出：计算器（6 步数值求根）、代入向导、计算链；附属 calculation_plan 表（归属自 CORE-14 移入）与 library.plan_* op；op 名按 CORE-10/11 实际契约 | — |
| CORE-49 | 学习统计、提醒设置与自建书界面 | 已修订（新增卡） | 由 CORE-39 拆出：统计页（自绘图表、热力图分档）、提醒设置（device.reminder_time）、自建书编辑器 | — |
| CORE-50 | 识别结果、云端确认与识别历史界面 | 已修订（新增卡） | 由 CORE-40 拆出：RecognizePage 与路由、CandidateVm（逐符号校正、经 CORE-38 新建页保存后 recog.adopt）、CloudConsentPage、UploadPreviewPage、HistoryVm；2026-10-19：候选页“复制 LaTeX”改为复制公式（FormulaCopyButton） | — |
| CORE-51 | 资源包下载、导入与管理界面 | 已修订（新增卡） | 从撤销的 AND-10、WIN-11 中抽出两端共用的资源包下载、断点续传、离线导入、更新检查与管理界面：PackService（offers/installed/checkUpdates/download/importFile/uninstall）、PackTaskState、PacksVm、installPacks；空间检查 PACK_STORAGE_LOW 与 PACK_DOWNLOAD_INCOMPLETE；调用 CORE-15 pack.install（带 expected_size/expected_blake3） | — |
| CORE-52 | 公式复制格式与富格式导出 | 已修订（新增卡，2026-10-19） | 按 Q12 确认新增：fml-export（MathML Core、SVG）、op export.formula、DefaultFormulaCopier（格式组合表、PNG 经 paintDisplayList、HTML 片段、16 项缓存、无写入器降级）、FormulaClipboardWriter 接缝、错误码 EXPORT_NOT_RENDERABLE / EXPORT_TOO_LARGE | 新错误码须先写入 contracts/errors/registry.yaml；Office 对 MathML 剪贴板格式的识别在 M0 验证（WIN-05） |

## D.5 Android 端

| 编号 | 名称 | 结论 | 修改摘要 | 遗留问题 |
| --- | --- | --- | --- | --- |
| AND-01 | 工程与构建 | 已修订 | 入口改为 runPlatformApp(CoreLibrarySpec)；ports_android 初始全 Fake、各卡逐行替换；platformInstallers 接缝；工具链锁定文件；仅 arm64；16 KB 对齐 | armeabi-v7a 是否开启待 AND-12 真机矩阵数据 |
| AND-02 | 权限与清单 | 已修订 | PermissionService 契约与通道；allowBackup=false；清单白名单检查脚本作为附属 | — |
| AND-03 | 相册、文件导入与导出 | 已修订 | 去掉对 AND-06、CORE-30 的依赖（LocalFileStore 经接口注入）；补 DocumentPicker；通道协议、HEIC→JPEG、20 MiB 规则、错误码；2026-10-19：新增 AndroidFormulaClipboard（text/plain、text/html、经 FileProvider 的 image/png），依赖加 CORE-52，规模约 500 | 接收方对剪贴板 content URI 的读取授权与图片粘贴支持在 M0 真机验证 |
| AND-04 | 相机 | 已修订 | 改为原生 CameraActivity；提示阈值；EXIF GPS 去除；依赖收敛为 CORE-04、AND-02 | 提示阈值需 AND-12 真机标定 |
| AND-05 | 生命周期、进程恢复与运行时信息 | 已修订 | 生命周期与运行时信息实现；trimMemory 映射；进程恢复验收移至 AND-12 | — |
| AND-06 | 本地存储、Keystore 与生物识别 | 已修订 | Keystore 包装格式、StoreArea 目录、别名、安全级别降级与异常映射 | — |
| AND-07 | 手写与编辑器的 Android 适配 | 已修订 | 删除不存在的 InkPointerAdapter/EditorActions；改为实现 CORE-37 EditorPlatformBindings 与 CORE-40 InkInputPolicy 接缝，经 platformInstallers 登记；去掉对 AND-05 依赖 | 手掌半径阈值需真机标定；V1 不做原生历史采样 |
| AND-08 | 本地通知与提醒自检 | 已修订 | NotificationScheduler 增加 taps()（CORE-04）；ReminderSelfCheck 接缝定义在 CORE-20、界面在 CORE-49；AlarmManager 非精确闹钟与重排规则；ROM 跳转表 | 应用多日未打开时正文沿用上次数量 |
| AND-09 | 网络传输 | 已修订 | 改为纯传输实现（dart:io HttpClient、系统代理、续传、取消、异常映射）；云识别前后台行为移至 CORE-34 | — |
| AND-10 | 资源包获取与识别历史平台存储 | 已撤销 | 资源包下载与管理并入 CORE-51，存储紧张清理并入 CORE-50；两端共用同一 Dart 实现，避免重复；编号不复用 | — |
| AND-11 | 打包、签名与发布 | 已修订 | 脚本参数、签名环境变量、检查项、符号归档、上架材料清单；build.gradle release 段为附属 | 应用备案号与软著登记号待甲方提供 |
| AND-12 | 性能、能耗与真机矩阵 | 已修订 | 测量项引用 CORE-01 预算表行名；脚本退出码；进程恢复与跨端一致性联测；依赖改为 AND-03/09 | 真机矩阵设备到位情况待确认 |

## D.6 Windows 端

| 编号 | 名称 | 结论 | 修改摘要 | 遗留问题 |
| --- | --- | --- | --- | --- |
| WIN-01 | 工程与构建 | 已修订 | 入口改为 CORE-04 runPlatformApp + CoreLibrarySpec（ABI 校验与“核心不可用”页归 CORE-04）；明确 CMake/cargo 集成、通道注册约定（每卡一行，前缀 fml/windows/）、ports_windows 先 Fake 后逐行替换、+crt-static 与 /Brepro；验收加可复现与无 VC 运行库依赖 | — |
| WIN-02 | 安装器与卸载 | 已修订 | 安装器定为 Inno Setup 6（ADR-V5-12（待定））；定义版本子目录与 current.txt/pending.txt 布局、ISCC 参数、AppMutex、/UPDATE=1 更新模式、降级拦截、空间检查、卸载窗体与清理范围；依赖由 WIN-07 改为 WIN-01（消除平台依赖方向违例） | AppId GUID 在 M0 生成 |
| WIN-03 | 自更新与启动器 | 已修订 | 原卡缺更新清单格式、校验与回滚机制：新增 update.json 格式、WindowsUpdater 状态机与签名者校验、退出时安装、固定路径启动器（首启 120 s 健康确认、数据库备份与回滚、保留 2 个版本）；启动器为附属构建单元（installer/windows/launcher） | 签名证书主体 CN（kExpectedPublisher）在 M0 登记 |
| WIN-04 | 文件导入、拖拽与导出 | 已修订 | 依赖去掉 CORE-30、WIN-07（LocalFileStore 注入）；新增 DocumentPicker 实现与 ImageDropSource 接缝实现；定义通道方法、超限与 HEIC（WIC）规则、文件夹一层扫描确认、导出 .fmlpart 原子改名 | HEIC 依赖用户安装 HEIF 扩展 |
| WIN-05 | 剪贴板与多格式复制 | 已修订 | 实现 CORE-04 ClipboardAdapter 与 CORE-52 FormulaClipboardWriter（2026-10-19 按 Q12 确认改写）：一次写入 MathML（三种格式名）、CF_HTML、image/svg+xml、PNG、CF_DIB、CF_UNICODETEXT、text/x-latex；粘贴图片读 PNG/CF_DIBV5/CF_DIB；修正错误码名为 PARSE_FORBIDDEN_COMMAND | Office 识别 MathML 剪贴板格式名的行为在 M0 用 Microsoft 365 验证；手动粘贴矩阵结果待记入 |
| WIN-06 | 窗口、DPI、生命周期与单实例 | 已修订 | 补全通道契约、paused/resumed 判定、低内存通知、关闭流程（closeRequested → 托盘或退出）、单实例与窗口位置规则；新增 WindowsPrefs、TrayPresence 接缝、WindowsShell.exitApp 与设置区；布局断点与深色模式归共享界面 | 关闭窗口默认退出、首次关闭不询问，按 README §6 Q15（待确认） |
| WIN-07 | 本地存储、DPAPI 与 Windows Hello | 已修订 | 定义 DPAPI 包装格式、.applock 的 Windows Hello 签名派生第二层、StoreArea 目录表、受保护 DACL、错误映射与“安全说明”设置区；依赖加 CORE-36 | — |
| WIN-08 | 编辑器快捷键、输入法与笔输入 | 已修订 | 改为经 CORE-36/37/40 接缝实现：编辑器与全局快捷键、笔输入策略；原卡引用的 EditorActions 不存在，已删除；2026-10-19 按 Q11 确认：默认键位改为贴近 Word 与 LaTeX 编辑器（上标 Ctrl+Shift+=、下标 Ctrl+=、插入公式 Alt+=、查找 Ctrl+F、重做 Ctrl+Shift+Z），新增 ShortcutCommand、KeyChord、Keymap、defaultKeymap、保留键规则与 KeymapHolder，只读帮助区移交 WIN-14，规模约 360 | LaTeX 命令补全与公式库批量键盘操作按 README §6 Q16（待确认）暂不做；Flutter Windows 笔事件上报需 M0 验证 |
| WIN-09 | 应用内提醒、托盘与开机自启 | 已修订 | 定义应用内定时规则（同日一次、时间变化与睡眠唤醒补发窗口 2 h）、托盘通道与菜单、通知点击、关闭到托盘与开机自启；不再使用 Toast COM 激活 | 应用完全退出时不提醒（设置区说明） |
| WIN-10 | 网络传输 | 已修订 | 改为纯传输实现（与 AND-09 同构，dart:io HttpClient、静态系统代理、续传、取消、异常映射）；云识别调用移至 CORE-34；移到 S2 | PAC 自动代理不支持 |
| WIN-11 | 资源包获取与识别历史平台存储 | 已撤销 | 资源包下载与管理并入 CORE-51，存储检查与历史清理并入 CORE-50、CORE-32；两端共用同一 Dart 实现；编号不复用 | — |
| WIN-12 | 代码签名与发布检查 | 已修订 | 定义 build_release.ps1 编排、sign.ps1（硬件令牌或云签名）、签名者核对、制品门禁、PDB 归档与 update.json 生成；MSIX 不采用（ADR-V5-12（待定））；依赖加 WIN-03 | 签名证书与时间戳服务由甲方在 S7 前提供 |
| WIN-13 | 性能与环境矩阵 | 已修订 | 测量项按 CORE-01 预算表行名对应，预算值只在 CORE-01 维护；定义测试、脚本、环境矩阵与报告模板；tools/perf/windows 为附属 | — |
| WIN-14 | 快捷键自定义 | 已修订（新增卡，2026-10-19） | 按 Q11 确认新增：设置页“快捷键”区、录制对话框（录制期间暂停分发）、冲突检测与替换、保留键拒绝、单项与全部恢复默认、偏好 keymap.v1（只存与默认不同的命令） | — |
