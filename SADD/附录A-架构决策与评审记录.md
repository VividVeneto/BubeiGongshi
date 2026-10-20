# 附录 A：架构决策与评审记录 v5

> 版本：v5　修订日期：2026-10-19  
> 效力：§A.4 中状态为“采纳”的 ADR 为规范性内容；其余为评审记录，说明性。  
> 本附录收录：首次复审报告（§A.1）、v4 评审意见摘要（§A.2）、v4 意见判定表（§A.3）、全部 ADR（§A.4）、开发前冻结清单（§A.5）与试点、复测记录（§A.6）。

## A.1 首次复审报告（2026-10-10）

评审对象：甲方提供的《公式记忆App-架构设计方案》v1.4、《Android端实现方案》v1.0、《Windows桌面端实现方案》v1.0。

评审基线：甲方原始需求及 2026-10-10 的补充确认。高中数学、高中物理和使用云端 API 的 LLM 识别属于现有需求，纳入 V1 交付；本次复审纠正了此前把这些需求列入暂缓的判断。

每条结论后的“v5 落点”指出其在现行模块卡中的位置。

### A.1.1 总体判断

原方案的技术骨架是专业的：

- Rust 核心承载公式 AST、量纲、单位、计算、排版等必须跨端一致的领域，方向正确。
- Flutter 承载 Android 与 Windows UI，能减少双端重复开发。
- C ABI 让鸿蒙未来可以通过 NAPI 复用核心，预留成本较低。
- 静态资源包、版本化、签名校验、识别历史 GC 等设计已经考虑到发布与隐私风险。
- 对不可信 LaTeX、图片、模型包的输入限制意识较强。

主要问题不在“分层错了”，而在“同时做太多”和“关键契约不够硬”：

1. 社区公式库引入额外审核、版权和运维工作，需要独立排期。云同步、高中与大学内容、云端 LLM API 识别属于现有需求，不能作为范围膨胀项削减。
2. 端侧大模型及 YOLO 实验不能挤占现有云 API 识别的交付；识别后端应共享一套解析、校正和校验流程。
3. 部分资源包设计将必需资源完全外置，首次启动可能强制联网，削弱游客离线可用性。
4. 账户升级与端到端加密的密钥流转没有形成可实施的数据安全闭环。
5. 量纲、数学类型、物理语义和排版契约仍有会导致后期返工的缺口。

### A.1.2 阻断级问题

| 编号 | 问题 | 修订结论 | v5 落点 |
| --- | --- | --- | --- |
| A1 | 需求范围与交付优先级不清 | V1 实现云端 API 的 LLM 识别并交付高中与大学内容包；分包和分阶段验收不改变必交付属性；两端各有独立实现规范；社区后续扩展，鸿蒙仅预留接口 | README §3；CORE-16、CORE-33、CORE-34、CORE-44 |
| A2 | 识别技术路线与内存、隐私、账户约束冲突（3B 级端侧多模态模型超出 Android 内存预算；云端默认链路与游客不上云冲突） | 先交付稳定识别接口、图像预处理、候选解析、量纲重排和人工校正；本地轻量模型为可选模型包；云端 LLM 为 V1 必交付后端，仅注册用户逐次授权；供应商 API Key 只在服务端；补齐限额、超时、取消、幂等和候选校验；YOLO 只在实验分支；不规划端侧大参数 VLM | CORE-29～CORE-35；附录 B |
| A3 | 静态资源包缺少离线 bootstrap 策略 | 安装包内置签名校验后的 bootstrap-pack（最小字体、符号表、单位库、基础内容），扩展内容按需下载；资源包是独立逻辑单元，不等于必须远程下载 | CORE-15、CORE-16 |
| A4 | 量纲相同不等于物理量相同（力矩与能量、频率与角频率、比热容与比熵） | 类型三层 `TypeExpr = { Dimension, QuantityKind, MathKind }`：Dimension 决定合法性，QuantityKind 决定物理语义与推荐排序，MathKind 决定结构约束；跨 QuantityKind 的同量纲代入必须显式警告 | CORE-08、CORE-09、CORE-11 |
| A5 | 数学与单位规则不完整（微分、积分、极限、∇ 族、级数、场；温差、角度、经验系数） | 建立量纲判例库，每条规则有正例、反例和教学解释；经验公式显式标记并自动推断系数量纲 | CORE-09（DX 判例） |
| A6 | 排版引擎迁移风险（先 Dart 移植库再换 Rust 会改变渲染树、度量与 hit-test） | M0 起单一排版契约：Rust 布局输出 DisplayList 与 NodePath，Flutter 用嵌入字体光栅化；布局、hit-test、错误定位、朗读串同源；主线不保留第二套排版 | CORE-12、CORE-37；ADR-005、ADR-V5-04 |
| A7 | 游客与注册账户的数据安全闭环不足 | 游客用设备密钥加密本地库；私有同步端到端加密，服务端只见密文与元数据；授权云识别的图片由网关与供应商处理明文，须单独说明；提供恢复码、导出、备份、账户删除与本地清除；游客关闭诊断与云功能。原结论中“把游客数据密钥包装到账户密钥下并上传”一步已由 ADR-V5-05 取代：本机密钥从不上传 | CORE-21～CORE-28 |
| A8 | 同步冲突策略对复习日志不友好 | 按实体合并：公式不可变修订，冲突时提示选择；复习日志追加；学习状态由 FSRS 从完整日志重算；设备设置不合并；识别历史不同步 | CORE-26 |
| A9 | 识别历史 GC 有“假删除”风险 | GC 事务化清理图片、缩略图、缓存、数据库记录与临时目录；图片加密存储，删除时销毁对应密钥；测试验证无残留；保留 0–100 次，默认 5 次 | CORE-32 |

### A.1.3 重要非阻断问题

| 编号 | 问题 | 修订 | v5 落点 |
| --- | --- | --- | --- |
| S1 | 代码示例语法不完整或契约歧义 | 文档中的代码是契约示意，实现必须通过编译与测试 | 全部模块卡“接口契约” |
| S2 | 开源内容引入缺少许可门禁 | 来源登记、许可审查、许可清单与机器可读 provenance | CORE-16；附录 C |
| S3 | 云识别与图片隐私缺少最小化原则 | 默认上传裁剪后的增强图，不上传原图；逐次授权；游客禁用 | CORE-30、CORE-34 |
| S4 | 无障碍缺失 | DisplayList 同步输出朗读串和语义树，支持缩放与高对比度 | CORE-12、CORE-37 |
| S5 | 术语与符号映射不统一 | Unicode、LaTeX、MathML、朗读名、中文名映射表 | CORE-06、CORE-07 |
| S6 | 性能目标缺少自动门禁 | CI 增加基准、内存、启动和渲染回归测试 | CORE-01、CORE-41、AND-12、WIN-13 |
| S7 | 依赖供应链风险 | 锁定依赖、SBOM、cargo audit/deny、签名发布产物 | CORE-41、CORE-42 |
| S8 | 迁移与降级未覆盖资源包 | 数据库、ABI、资源包分别迁移和校验，可回滚到最近两个正式版本 | CORE-13、CORE-15、CORE-42 |
| S9 | 大图片处理容易 OOM | 两端流式读取并降采样，Rust 处理灰度与缩放 | CORE-30、AND-03、WIN-04 |
| S10 | 日志可能泄露学习内容 | 结构化日志不含公式正文和图片，脱敏后才能导出 | CORE-28 |

### A.1.4 保留的合理设计

- Rust + Flutter + C ABI 分层。
- SQLite 作为本地单文件数据库，配合加密和显式迁移。
- 资源包签名、版本、原子替换。
- FSRS 记忆算法使用成熟 Rust 实现，不自研调度器。
- 公式不可变修订与来源追踪。
- 手写候选先解析为 AST，再用量纲上下文重排。
- Android 使用 Photo Picker/SAF，避免申请宽泛存储权限。

### A.1.5 修订决策摘要（相对 v1.4）

| 决策 | v1.4 原方向 | 复审修订 |
| --- | --- | --- |
| V1 云服务 | 云同步、社区、云端识别进入主线 | 账户/同步及云端 API 的 LLM 识别为 V1；社区后续扩展 |
| 内容范围 | 高中与大学内容 | 高中数学、高中物理、高等数学、大学物理全部保留，内容包分阶段验收 |
| 平台规范 | 独立的输入与生命周期要求 | 两份独立实现规范，共用领域契约与验收标准 |
| 端侧识别 | 本地模型、云端 LLM、YOLO 多线并行 | 一条可插拔契约，本地轻量模型可选，云端显式授权，YOLO 实验分支 |
| 静态资源 | 全部外置，缺核心包则应用不可用 | 安装包内置 bootstrap-pack，扩展包按需下载 |
| 量纲 | 以 Dimension 为核心 | Dimension + QuantityKind + MathKind |
| 排版 | 存在迁移路线 | 单一 Rust 布局契约，无中途替换 |
| 游客 | 本地临时账户 | 设备密钥加密、禁云、可升级接管、支持清除 |
| 同步 | 冲突策略不完整 | 按实体类型分策略，复习日志不可覆盖 |
| 鸿蒙 | 预留接口 | 保持 C ABI/NAPI 预留，不进入 V1 排期 |

## A.2 v4 评审意见摘要

v4（标签 `archive/sadd-v4.0`，分支 `docs/sadd-v4`）是对上一基线的全面评审意见，不是现行基线。其意见主要集中在：

- 需求基线：逐字保存原需求与 2026-10-18 澄清，提出“功能近似条款”R04.a–R04.j；同时把高中内容与首版云识别重新解释为“历史扩展”，并重新编号需求。
- ADR-001～ADR-014：Flutter + Rust sans-I/O、不自研排版、服务端模块化单体与 OIDC、本机库密钥不上云、签名资源包、严格 N 的识别历史、可插拔识别与作答模式忠实转写、客观为主的背诵范式、Rust 状态机、单一绑定面、量纲多态、设备配对、鸿蒙双路线、自编内容。
- RV-01～RV-17：P0 级（严格 N、随机根密钥、逻辑删除不等于擦除、代入条件、Unknown 不等于无量纲与绝对温度、资源包安全、同步协议、游客本地识别路径）与 P1 级（非双射、避免自研 DisplayList、端口向内、考研拆分、性能基线设备、Windows 最低版本、识别通过不等于答对、开源调查、数据库检查与实验分支同步）。
- 专项契约：账户、加密、同步、识别生命周期与云识别（v4 11）；资源包与内容（v4 12）；需求追踪与验收口径（v4 13）；功能与代码模块映射（v4 14）。

逐条判定见 §A.3。

## A.3 v4 意见判定表

判定依据：甲方原始需求及书面确认 > 已确认的架构决策 > v4 意见。与需求基线冲突或缺乏依据的不采纳；无法判断的列入 README §6 交甲方确认。Q1–Q10 已于 2026-10-18 确认（Q2 改为同济第八版、Q9 改为只用邮箱，其余采用原现行默认），下表相关行的判定按确认结论更新。纯措辞与排版差异不列。

### A.3.1 需求基线（v4 00）

| v4 位置 | 意见摘要 | 判定 | 理由 | 落入的模块卡 |
| --- | --- | --- | --- | --- |
| 00 原需求记录 | 逐字保存原始需求与 2026-10-18 甲方澄清 | 采纳 | 甲方原文，是最高依据 | README §2.1、§2.2 |
| 00 冲突处理顺序 | 甲方 > 00 > 11/12 > 10 > 历史 | 部分采纳 | 保留“甲方优先”，其余改为“已确认决策 > 评审意见” | README §2.3 |
| 00 H01 | 高中内容是“历史扩展约束”，不是本次原文要求 | 不采纳 | 甲方 2026-10-10 书面确认高中内容为现有需求（R39） | CORE-16 |
| 00 H02 | 首版云识别是“历史扩展” | 不采纳 | 甲方 2026-10-10 书面确认首版交付（R40） | CORE-33、CORE-34 |
| 00 功能近似条款 | R04.a–R04.j：书与计划、分组学习、客观辨识、错题重现与掌握判据、组后默写、考试语境、关联记忆、FSRS 排程与改判、统计与坚持、自建与导入；默认组 10、K = 3、每日新学 10；不做组队打卡 | 采纳 | 是甲方“只需要功能近似”的可验收化，不扩大范围 | CORE-14、CORE-16、CORE-17、CORE-18、CORE-19、CORE-20、CORE-38、CORE-39 |
| 00 素材边界 | 不复制界面素材、图标、配色、文案、音效、商标与私有接口 | 采纳 | 甲方澄清“不需要使用其代码、直接的素材” | README §2.2 |
| 00 / 13 需求重新编号 | R01–R31 + H01/H02 + A01–A04 | 不采纳 | 与已有 R01–R41 同号异义，破坏追踪；沿用原编号，只新增 R04.a–R04.j | README §5 |
| 00 平台规范 | 平台要求并入总体设计的平台章节 | 不采纳 | 甲方确认两端规范独立说明（R41） | 02、03 |
| 00 游客“临时” | 游客数据保留到用户清除或升级，不在退出时删除 | 采纳 | 与原文“本地储存用户数据”一致 | CORE-23 |
| 00 ISO 字符 | Unicode 存储；ISO 80000-2 符号表分“可输入/可渲染/可计算”三级；不声称与 LaTeX 双射，保证语义往返 | 采纳 | 双射没有依据且不可测 | CORE-06、CORE-07 |
| 00 考研全范围 | 高数、线代、概率统计拆分，数一/数二/数三分别出覆盖矩阵 | 采纳 | 原文“考研数学全部范围” | CORE-16；附录 C |
| 00 D-17 | 教材基线改为同济第八版等 | 采纳 | 甲方确认采用同济第八版（附录 C 已按第八版整理），大纲与课标按发布当年现行版本（Q2） | CORE-16；附录 C |
| 00 版本控制 | 除工程 Git 外还提供用户公式修订历史的查看、比较、恢复 | 采纳 | 不可变修订已是既有设计，成本低；甲方确认工程 Git 与公式修订历史两者都做（Q10） | CORE-14、CORE-38 |
| 00 D-13 | 本地模型未安装或未达标时，游客识别入口明示不可用并引导手工输入，不返回假结果 | 采纳 | 与“游客不上云 + 本地模型可选包”一致 | CORE-29、CORE-40 |
| 00 D-01 | 商标与名称 | 采纳 | 甲方确认使用工作名“不背公式”，不使用不背单词的商标与素材（Q1） | README §6；CORE-36、AND-11、WIN-02 |
| 00 D-06 | 目标用户含未成年人，增加合规门禁 | 采纳 | 甲方确认按包含未成年人做合规准备（Q7） | CORE-34、CORE-36、CORE-42 |
| 00 D-09 | 本机解锁默认系统级，可选应用锁 | 采纳 | 不改变需求，提升本机安全且不增加首启负担 | CORE-23 |
| 00 D-10 | 云识别供应商与数据境内 | 采纳 | 甲方确认境内部署网关，供应商经 `VisionProvider` 可替换（Q8） | CORE-33、CORE-43 |
| 00 D-14 | 登录方式 | 采纳 | 甲方确认邮箱 + 口令，经 OIDC 授权码 + PKCE；暂不使用、不绑定手机号（无运营商支持，Q9） | CORE-22、CORE-23 |
| 00 D-16 | 只有 Verified 修订生成卡片 | 采纳 | 与“校验 Error 阻止正式保存”一致 | CORE-17 |
| 00 D-07 | 识别指标按任务（查询、作答）分别定义，在 M0 基线设备上测得 | 采纳 | 使验收可执行 | CORE-31、CORE-35 |

### A.3.2 ADR 与评审项（v4 09）

| v4 位置 | 意见摘要 | 判定 | 理由 | 落入的模块卡 |
| --- | --- | --- | --- | --- |
| ADR-001 | Flutter + Rust，领域层 sans-I/O | 采纳 | 与既有分层一致 | CORE-01、CORE-04 |
| ADR-002、RV-10 | MVP 不自研排版，改用源码/模板编辑 + Flutter 渲染库（flutter_math_fork） | 不采纳 | 与已确认的“单一 DisplayList 排版契约”冲突；该库 2025-05 后无新版本，依赖风险更高；双端快照一致、hit-test 与错误定位都依赖同一布局输出 | CORE-12；ADR-V5-04 |
| ADR-003 | 服务端模块化单体，OIDC 认证 | 采纳 | 云识别网关与同步都需要服务端，原基线未定义 | CORE-22、CORE-25、CORE-33、CORE-43；ADR-V5-03 |
| ADR-004 | 端到端加密，本机库密钥不上云 | 采纳 | 修正原升级流程中上传包装后本机密钥的风险 | CORE-21、CORE-24；ADR-V5-05 |
| ADR-005 | 签名资源包 | 采纳 | 与既有设计一致并细化 | CORE-15 |
| ADR-006、RV-01 | 严格 N：失败、取消也计数，不设置顶豁免，历史只存确认图 | 部分采纳 | 计数单位为识别会话、失败与取消计数采纳；置顶与已入库豁免保留（原需求未禁止，已确认设计含置顶）；甲方确认保留豁免、不采用严格 N（Q4） | CORE-32；ADR-V5-06 |
| ADR-007 | 识别可插拔；云端与本地分别验收；YOLO 不替代主线；作答模式忠实转写 | 采纳 | 与需求一致，并防止识别结果“帮用户答对” | CORE-29、CORE-31、CORE-35 |
| ADR-008、RV-15 | 背诵范式客观判定为主；识别通过或量纲通过不等于答对 | 采纳 | 由功能近似条款推出 | CORE-18、CORE-19；ADR-V5-07 |
| ADR-009 | 同步合并、升级日志、GC、识别会话等状态机放 Rust，sans-I/O | 采纳 | 双端一致、可单测 | CORE-19、CORE-24、CORE-26、CORE-32；ADR-V5-08 |
| ADR-010 | 单一绑定面，M0 在 flutter_rust_bridge 与 C ABI 中选择；短操作 P95 ≤ 30 ms，长任务完成回调 | 部分采纳 | 单一绑定面、预算与回调采纳；直接定为 C ABI + dart:ffi，鸿蒙复用同一头文件，无需 M0 再选 | CORE-03；ADR-V5-02 |
| ADR-011 | 量纲多态（幂、指数、导数等） | 采纳 | 高数公式严格量纲的必要条件 | CORE-09 |
| ADR-012 | 新设备默认以设备配对开通端到端加密，恢复码兜底，同步密语可选 | 不采纳 | 甲方确认以恢复码 + 可选同步密语开通，不以设备配对为默认（Q3） | CORE-21 |
| ADR-013 | M0 启动鸿蒙双路线验证 | 不采纳 | 原需求只要求预留接口；甲方确认 V1 只保留 C ABI 与编译冒烟（Q6） | CORE-44 |
| ADR-014 | 内容以自编为主，开源资源用于校验，排除 NC 与 CC BY-SA/GFDL | 采纳 | 降低版权风险 | CORE-16；附录 C |
| RV-02 | 账户根密钥随机生成，由口令或恢复码包装；本机库密钥不上传 | 采纳 | 同 ADR-004 | CORE-21、CORE-24 |
| RV-03 | 逻辑删除不等于闪存擦除，不作此承诺 | 采纳 | 事实正确，避免虚假承诺 | CORE-32 |
| RV-04 | 代入须检查等号方向、换名、定义域与分支条件 | 采纳 | 防止数学上错误的代入 | CORE-11 |
| RV-05 | Unknown 不等于无量纲；绝对温度换算为开尔文后可参与乘除（如 pV = nRT） | 采纳 | 修正原“温度点不得参与乘除”与理想气体公式的冲突 | CORE-08、CORE-09 |
| RV-06 | 资源包：签名 manifest 含哈希、长度与路径，先验签后解包，防路径穿越与压缩炸弹，受控回滚与安全序号，根密钥轮换 | 采纳 | 安全加固 | CORE-15；ADR-V5-09 |
| RV-07 | 同步：outbox、每账户序号、先持久化后 ACK、墓碑、纪元 | 采纳 | 保证幂等与可中断 | CORE-13、CORE-25、CORE-26；ADR-V5-10 |
| RV-08 | 游客必须有本地识别路径 | 采纳 | 并入 D-13 的处理 | CORE-29、CORE-40 |
| RV-09 | 不声称 ISO 与 LaTeX 双射 | 采纳 | 同 00 ISO 字符 | CORE-06 |
| RV-11 | 领域层不含 I/O，端口指向内层 | 采纳 | 与既有分层一致 | CORE-01、CORE-04 |
| RV-12 | 考研拆为数一/数二/数三 | 采纳 | 同 00 考研全范围 | CORE-16 |
| RV-13 | 性能按 P50/P95 在基线设备上测；检测器与端到端分开计 | 采纳 | 使预算可测 | CORE-01、AND-12、WIN-13 |
| RV-14 | Windows 以 Windows 11 为主，Windows 10 只兼容 22H2 | 不采纳 | 甲方确认最低支持 Windows 10 1809+，以 Windows 11 为主测环境（Q5） | WIN-01、WIN-13 |
| RV-16 | 系统调查开源公式库、数据集、模型与字体 | 采纳 | 原需求第 2 条 | 附录 C；CORE-16 |
| RV-17 | 数据库完整性检查改为迁移或异常后触发，不做周期 VACUUM；实验分支按阶段同步主线 | 采纳 | 降低能耗与 I/O | CORE-13；附录 B |

### A.3.3 总体设计（v4 10）

| v4 位置 | 意见摘要 | 判定 | 理由 | 落入的模块卡 |
| --- | --- | --- | --- | --- |
| 10 记号与常数 | 记号方案（国内默认/ISO）、常数集 exact/textbook/given，优先级 given → textbook → exact | 采纳 | 教材与考试记号差异是判分正确的前提 | CORE-07 |
| 10 输入限额 | 源码 64 KiB、节点 4096、深度 64、矩阵 64×64 且 ≤ 1024 元、求解 10 万步、100 ms | 采纳 | 防御不可信输入 | CORE-05、CORE-06、CORE-10 |
| 10 计算链 | 多个公式按变量依赖串联求值 | 采纳 | 是原需求“代入”的数值形态 | CORE-11 |
| 10 计算器 | V1 不做不确定度 | 不采纳 | 已确认设计支持带不确定度输入并显示传播区间，无删减理由 | CORE-10 |
| 10 图片输入 | 解码器白名单、HEIC 仅系统解码、20 MiB / 40 MP 上限、上传图缩放公式 | 采纳 | 安全与内存预算 | CORE-30 |
| 10 识别模式 | 查找模式可重排；作答模式忠实转写，不用上下文“纠正” | 采纳 | 防止判分作弊 | CORE-29、CORE-31 |
| 10 学习统计与个性化 | 统计口径、掌握判据、FSRS 个性化门槛 | 采纳 | R04.i 的可验收化 | CORE-17、CORE-20 |
| 10 错误码 | 注册表单一来源，生成 Rust、Dart 与文档，CI 检查漂移 | 采纳 | 可维护性 | CORE-02 |
| 10 可维护性 | 文档注释门禁、依赖图检查、CODEOWNERS、关键 crate 双人评审 | 采纳 | R18–R20 | CORE-01、CORE-41 |
| 10 服务端 API | `/v1` 前缀，加法演进，低版本返回 HTTP 426 | 采纳 | 版本控制可靠 | CORE-22 |
| 10 监控与恢复 | 不含内容的监控指标与告警阈值；RPO ≤ 24 h、RTO ≤ 8 h | 采纳 | 运维必需 | CORE-43 |
| 10 Android 平台 | 只申请 INTERNET、CAMERA、POST_NOTIFICATIONS；16 KB 页对齐；无 GMS 依赖 | 采纳 | 隐私与国内设备兼容 | AND-02、AND-11 |
| 10 能耗 | 无常驻服务、无周期轮询，前台或手动同步 | 采纳 | 与原基线一致并细化 | CORE-26、AND-12、WIN-13 |
| 10 进程恢复 | 草稿 500 ms 去抖保存，作答立即提交，重启后只查询云任务、不重复提交 | 采纳 | 防丢数据与重复计费 | CORE-34、CORE-37、AND-05、WIN-06 |
| 10 Windows 更新 | 签名更新清单、断点续传、安装前备份、自动回滚 | 采纳 | 原基线对自更新描述不足 | WIN-03 |
| 10 里程碑 | M0–M5 | 部分采纳 | 改为按模块卡的阶段 S0–S7，便于逐卡实施 | 01 §2 |
| 10 鸿蒙 | M0 双路线 | 不采纳 | 同 ADR-013 | CORE-44 |

### A.3.4 账户、加密、同步与识别生命周期（v4 11）

| v4 位置 | 意见摘要 | 判定 | 理由 | 落入的模块卡 |
| --- | --- | --- | --- | --- |
| 11 账户状态 | Uninitialized、GuestUnlocked、RegisteredUnlocked、RegisteredLocked、UpgradingGuest | 采纳 | 使“不登录不可用”可测试 | CORE-23 |
| 11 设备注册表 | 设备级小库保存档案与本机设置（keep_last 等） | 采纳 | 多账户本机隔离 | CORE-23 |
| 11 恢复码 | 128 位随机，26 位 Crockford Base32，含校验位，HKDF | 采纳 | 细化既有恢复码设计 | CORE-21 |
| 11 同步密语 | 仅客户端，Argon2id m ≥ 64 MiB、t = 3、p = 4，解锁 P95 ≤ 2 s | 采纳 | 替代“口令 + KDF”的模糊表述，且服务端可见的登录口令不作加密密钥 | CORE-21 |
| 11 AEAD | XChaCha20-Poly1305，随机 192 位 nonce | 采纳 | 随机 nonce 安全 | CORE-21 |
| 11 升级日志 | PREPARED → IDENTITY_READY → KEY_READY → LOCAL_COMMITTED → DONE，各步幂等 | 采纳 | 满足“升级失败游客数据可用” | CORE-24 |
| 11 游客并入 | 并入已有账户：UUIDv5 确定性 ID、事件去重、公式重复提示 | 采纳 | 原基线未覆盖 | CORE-24 |
| 11 同步协议 | Envelope v2、确定性 CBOR AAD、`(account_epoch, op_id)` 幂等、256 KiB/1 MiB/200 限额、快照 | 采纳 | 同 RV-07 | CORE-25、CORE-26 |
| 11 合并规则 | 修订 DAG 与“待选择”记录、事件排序键、三类纪元、墓碑防复活 | 采纳 | 细化按实体合并 | CORE-26 |
| 11 服务端可见元数据 | 列出并在隐私政策中披露 | 采纳 | 如实说明端到端加密的边界 | CORE-25 |
| 11 删除账户 | 300 s 内重新认证；生产数据 24 h、备份 30 天；保留例外 | 采纳 | 合规必需 | CORE-25 |
| 11 导出与恢复 | 默认不含识别历史；合并或替换两种恢复 | 采纳 | 细化 | CORE-27 |
| 11 识别生命周期 | 会话状态机、`pending_cloud_job` 24 h、两阶段 GC、staging、存储配额 | 采纳 | 细化 GC 与断点恢复 | CORE-32 |
| 11 云识别授权 | 每个供应商与政策版本一次功能级同意 + 每次发送前预览；本地 consent_receipt | 部分采纳 | 保留每次显式确认（已确认的逐次授权）；增加功能级同意与回执 | CORE-34 |
| 11 云识别接口 | `/v1/recognition/jobs`、409/429、超时 5/30/30 s、网关清理 ≤ 60 s、结果 ≤ 24 h、UNKNOWN 不自动重付 | 采纳 | 费用与隐私可控 | CORE-33、CORE-34 |
| 11 合规门禁 | 隐私政策、单独同意、未成年人、App 备案、SDK 与域名清单、删除与导出 | 采纳 | 发布前必须满足 | CORE-36、CORE-42 |
| 11 安全验证表 | 各项安全测试 | 采纳 | 拆入对应卡的验收标准 | CORE-21～CORE-28、CORE-32～CORE-34 |
| 11 设备配对 | 扫码 + 6 位码，X25519 + HPKE | 不采纳 | 同 ADR-012，甲方确认不以设备配对为默认（Q3） | CORE-21 |

### A.3.5 资源包与内容（v4 12）

| v4 位置 | 意见摘要 | 判定 | 理由 | 落入的模块卡 |
| --- | --- | --- | --- | --- |
| 12 清单与安装 | manifest 字段、7 步安装、限额、危险路径、TUF 风格元数据（timestamp ≤ 7 天） | 采纳 | 同 RV-06 | CORE-15 |
| 12 课程基线 | 课程标准、教材、大纲与基本要求作为范围依据，冻结规则 | 采纳 | 使覆盖率可计算；甲方确认同济第八版（Q2） | CORE-16 |
| 12 知识点与范围 | kp_id 为最小可判定子句；scope 清单 | 采纳 | 覆盖率口径 | CORE-16 |
| 12 条目字段 | 教材出处、考试范围、要求层级、条件、派生树、易混组等 | 采纳 | 支撑 R04.f、R04.g | CORE-16 |
| 12 版权 | 只存出处与自编改写；NC、CC BY-SA、GFDL 不入包 | 采纳 | 同 ADR-014 | CORE-16 |
| 12 开源调查 | 公式库、数据集、模型、字体与许可，来源 S01–S32 | 采纳 | 调查性内容 | 附录 C |
| 12 模型包 | 模型包字段与许可登记 | 采纳 | 规范性部分 | CORE-35 |
| 12 附录 A | 考研数学知识点矩阵（数一/数二/数三） | 采纳 | 调查性内容 | 附录 C |

### A.3.6 需求追踪与验收（v4 13）

| v4 位置 | 意见摘要 | 判定 | 理由 | 落入的模块卡 |
| --- | --- | --- | --- | --- |
| 13 正确性用例 | DX-01～16、SX-01～08、T-EDIT、T-LIB 等 | 采纳 | 可执行验收 | CORE-09、CORE-11、CORE-14、CORE-37 |
| 13 判分用例 | GX-01～14 及 ≥ 600 条扩充集，99% / 0.5% 阈值 | 采纳 | 可执行验收 | CORE-18 |
| 13 学习验收 | T-SESSION、T-STATS、评分映射、试点（≥ 30 人 × 30 天） | 采纳 | 可执行验收 | CORE-19、CORE-20 |
| 13 内容覆盖 | 数一/二/三覆盖 100%，抽检 max(50, 10%)，严重错误 0、一般 ≤ 2% | 采纳 | 内容质量门禁 | CORE-16 |
| 13 识别与 GC | 识别指标、语料、GC 与云识别异常用例 | 采纳 | 可执行验收 | CORE-32、CORE-33、CORE-34、CORE-35 |
| 13 账户与安全 | T-UNLOCK、T-SYNC、T-AAD、T-SNAPSHOT、T-GUESTMERGE 等 | 采纳 | 可执行验收 | CORE-21、CORE-24、CORE-26 |
| 13 T-PERF | 安装包体积放宽到 70 / 90 MiB | 不采纳 | 与轻量化（R03）及已确认的 Android < 45 MB、Windows ≤ 70 MB 冲突，且无新依据 | CORE-01、CORE-42 |
| 13 T-PERF | P50/P95、基线设备、其他时延预算 | 采纳 | 同 RV-13 | CORE-01、AND-12、WIN-13 |
| 13 可维护性阈值 | 复杂度、unsafe、FFI 规模趋势 | 采纳 | R18 | CORE-41 |
| 13 发布清单 | 发布前检查项 | 采纳 | R23 | CORE-42 |
| 13 编号对照 | 新旧需求编号对照 | 不采纳 | 不采用重新编号，无需对照 | README §5 |

### A.3.7 功能与代码模块映射（v4 14）

| v4 位置 | 意见摘要 | 判定 | 理由 | 落入的模块卡 |
| --- | --- | --- | --- | --- |
| 14 模块划分 | 粗粒度模块（fml-core、fml-study、fml-recognition、fml-assets、fml-store、fml-sync、fml-crypto、contracts、server 等） | 部分采纳 | 采纳 fml-study、fml-sync、fml-crypto、contracts 与 server 的边界；保留细粒度 crate（fml-ast、fml-latex、fml-type 等），因为每张卡须在一次会话内完成 | 01 §3 模块索引 |
| 14 端口清单 | FormulaEngine、Scheduler、Grader、FormulaView、ImageImport、SecureStore 等 | 部分采纳 | 平台端口统一定义在 CORE-04；领域端口以 Rust trait 定义在各卡 | CORE-04 |
| 14 实体清单 | Book、StudyPlan、Attempt、ReviewEvent、ConfusableGroup、ConstantSet、CalculationPlan 等 | 采纳 | 支撑功能近似条款 | CORE-07、CORE-11、CORE-13、CORE-17、CORE-19 |
| 14 SF-01～SF-06 | OIDC、同步、识别网关、TUF 元数据、账户删除、API 版本与恢复目标 | 采纳 | 服务端能力 | CORE-22、CORE-25、CORE-33、CORE-15、CORE-43 |

## A.4 架构决策记录（ADR）

ADR 字段：背景、方案、结论、被否方案的代价、重新评估条件。状态：采纳 / 废弃 / 待定；“采纳（甲方……确认）”为甲方决策，“采纳（修订方决定）”为修订方在既有需求与甲方决策范围内作出的技术决策，甲方可要求重审。新增 ADR 顺延编号，不重排。“模块卡”列只写完整卡号（如 CORE-05、WIN-16），不缩写、不用区间或斜杠，便于脚本按卡号检索；README、AGENTS 与本附录节号等非卡引用放在“；”之后。

### A.4.1 基线 ADR（2026-10-10 确认，v5 保留）

| 编号 | 决策 | 结论 | 被否方案的代价 | 重新评估条件 | 状态 | 模块卡 |
| --- | --- | --- | --- | --- | --- | --- |
| ADR-001 | 核心语言 | Rust 实现全部跨端一致的领域逻辑 | Dart/Kotlin/C# 各写一套：两端结果不一致、测试翻倍 | 出现 Rust 无法覆盖的目标平台 | 采纳 | CORE-01 |
| ADR-002 | UI 框架 | Flutter 共享 UI | 原生双写：工作量约翻倍 | Flutter 停止支持 Windows 或 Android 目标 | 采纳 | CORE-36、CORE-37、CORE-38、CORE-39、CORE-40 |
| ADR-003 | 本地存储 | SQLite（SQLCipher 加密），单用户单库 | 自研文件格式：迁移与一致性风险 | 数据量超过 SQLite 合理范围 | 采纳 | CORE-13 |
| ADR-004 | 记忆算法 | FSRS 成熟实现，不自研 | 自研调度：效果无法验证 | 上游停止维护且有安全问题 | 采纳 | CORE-17 |
| ADR-005 | 排版 | Rust 布局输出 DisplayList，单一契约 | 两套排版：快照与 hit-test 不一致 | 见 ADR-V5-04 | 采纳 | CORE-12 |
| ADR-006 | 资源包 | 签名资源包 + 内置 bootstrap-pack | 资源打进安装包：体积超标；全部外置：首启强制联网 | — | 采纳 | CORE-15、CORE-16 |
| ADR-007 | 私有同步 | 端到端加密，服务端只见密文 | 服务端明文：违背最小化 | — | 采纳 | CORE-21、CORE-25、CORE-26 |
| ADR-008 | 识别隔离 | 统一识别契约，后端可插拔，输出视为不可信 | 绑定单一后端：无法替换 | — | 采纳 | CORE-29 |
| ADR-009 | YOLO | 只在实验分支 `codex/exp-yolo-recognizer`，主线零依赖 | 进入主线：违背原需求 | 达到附录 B 合入门槛且甲方同意 | 采纳 | 附录 B |

### A.4.2 v5 新增 ADR（v5.3 于 2026-10-19 按 D1～D6 确认修订；V5-13、16、18 待定；V5-26～34 为修订方技术决策，v5.3.1 补 V5-32～34）

| 编号 | 决策 | 结论 | 被否方案的代价 | 重新评估条件 | 状态 | 模块卡 |
| --- | --- | --- | --- | --- | --- | --- |
| ADR-V5-01 | 文档与编号 | 按模块卡组织（README + 公共核心 + 两平台 + 附录）；需求编号沿用 R01–R41 并新增 R04.a–R04.j；模块编号不重排 | 重新编号：追踪断裂；长篇专题文档：无法一次交给 AI | — | 采纳 | README；01 §3 |
| ADR-V5-02 | 绑定方式 | Rust 只导出 C ABI（`fml_call`、`fml_submit` 等 8 个函数 + JSON DTO），Dart 用 `dart:ffi` + ffigen 调用；不使用 flutter_rust_bridge | 双绑定面：鸿蒙需再维护一套；代码生成器升级风险 | FFI 开销超出 CORE-01 预算 | 采纳 | CORE-03、AND-01、WIN-01 |
| ADR-V5-03 | 服务端 | 模块化单体：Rust（axum）+ PostgreSQL + 对象存储；OIDC 授权码 + PKCE；`/v1` API | 微服务：运维成本高；无服务端：无法交付云识别与同步 | 负载或团队规模需要拆分 | 采纳 | CORE-22、CORE-25、CORE-33、CORE-43 |
| ADR-V5-04 | 排版路线 | 保留 Rust DisplayList，不采纳 v4 ADR-002 的 Flutter 渲染库路线 | 改用 flutter_math_fork：上游停更风险、与 hit-test/错误定位/快照测试脱节 | DisplayList 在 S1 未达到 CORE-01 布局预算 | 采纳 | CORE-12 |
| ADR-V5-05 | 账户密钥 | AccountDataKey 为 256 位随机数，由恢复码（HKDF）与可选同步密语（Argon2id）包装；服务端可见的登录凭据不参与派生；本机库密钥与识别历史密钥从不上传 | 口令派生根密钥：改口令即需重加密；上传本机密钥：扩大泄露面 | 甲方变更 Q3 结论（改为设备配对默认） | 采纳 | CORE-21、CORE-24 |
| ADR-V5-06 | 识别历史 | 计数单位为识别会话（失败、取消、过期未知均计数）；保留 0–100、默认 5；置顶与已入库豁免；两阶段 GC；不承诺闪存级擦除 | 按图片计数：批量导入时语义混乱；不设豁免：用户无法长期保留需要的识别 | 甲方变更 Q4 结论（改为严格 N） | 采纳 | CORE-32 |
| ADR-V5-07 | 背诵范式 | 功能近似条款 R04.a–R04.j；客观判定为主，三层判分器只输出正确/错误/无法判定；评分由客观结果映射 | 看答案自评：与原型功能不近似，统计不可信 | 试点（§A.6）未达标 | 采纳 | CORE-18、CORE-19、CORE-20 |
| ADR-V5-08 | 状态机位置 | 学习组循环、升级日志、同步合并、识别会话与 GC 均为 Rust sans-I/O 状态机，平台只做 I/O | 状态机写在 Dart：难以跨端一致与单测 | — | 采纳 | CORE-19、CORE-24、CORE-26、CORE-32 |
| ADR-V5-09 | 资源包安全 | 先验签后解包、限额与危险路径拒绝、安全序号防回滚、TUF 风格更新元数据 | 只校验整包签名：路径穿越与压缩炸弹风险 | — | 采纳 | CORE-15 |
| ADR-V5-10 | 同步协议 | Envelope v2、outbox 与业务同事务、`(account_epoch, op_id)` 幂等、先持久化后 ACK、快照 + 增量、墓碑 180 天 | 简单全量上传：不可中断、易重复 | — | 采纳 | CORE-13、CORE-25、CORE-26 |
| ADR-V5-11 | 邮件发信 | 注册与找回口令用 6 位邮箱验证码；服务端经 `EmailSender` 端口发信，默认阿里云邮件推送，腾讯云邮件推送为备用，测试用 Fake 实现；V1 不接入境外发信服务（筛选见 §A.4.3） | 境外长期免费服务：用户邮箱地址出境，需单独同意与出境告知，未成年人信息风险更高，国内邮箱送达不稳定；自建 SMTP：IP 信誉养护成本高，易进垃圾箱 | 境内到达率持续偏低，或按量费用超出预算；改用境外服务须甲方重新确认 | 采纳（甲方 2026-10-18 确认维持境内方案） | CORE-22、CORE-45、CORE-43 |
| ADR-V5-12 | Windows 安装与更新 | 采纳 Inno Setup 6，按用户安装、无需 UAC；固定路径启动器管理版本目录与首启回滚；V1 不产出 MSIX。启动器与安装器分卡交付（WIN-16、WIN-02） | WiX/MSI：按用户安装与自定义卸载窗体实现量大，回滚仍需自建；MSIX：安装目录只读、`%LOCALAPPDATA%` 写入被虚拟化，与启动器和版本子目录机制冲突，侧载需额外信任证书 | 需要上架 Microsoft Store，或企业客户要求 MSI/MSIX 分发 | 采纳（甲方 2026-10-19 确认） | WIN-02、WIN-03、WIN-12 |
| ADR-V5-13 | 本地推理运行时 | 运行时保持待定：M0 用许可清楚的模型实测 ort / MNN 后选一；编码用 FakeEngine + 固定夹具验收管线；真实 ExpRate 与性能由模型交付里程碑 M-MODEL 验收，不阻塞 CORE-35 编码 | `ort`：完整运行时体积大，需裁剪算子；MNN：无官方 Rust 绑定，需维护 C API 绑定 | M0 实测后定案；所选运行时停止维护或在任一端预算不达标 | 待定（M0 定案；正文按推荐方案撰写） | CORE-35 |
| ADR-V5-14 | 身份服务 | 采纳境内自托管 Casdoor（Apache-2.0）；Casdoor 唯一保存登录凭据、签发授权码及令牌；CORE-22 只作业务账户映射、协议适配与验证码门面，CORE-45 经 EmailSender 发境内验证码；版本和扩展能力在 CORE-22 开工时锁定并验收（§A.4.4） | 托管身份服务（IDaaS）：账户与邮箱数据交第三方，境内合规与未成年人数据处理需额外评估，按月活计费；自研协议：安全风险高 | 运维成本超出预算，或甲方指定统一身份平台 | 采纳（甲方 2026-10-19 确认） | CORE-22、CORE-43 |
| ADR-V5-15 | 工具链与关键依赖版本锁定 | 采纳版本锁定机制：S0 CORE-01 开工当天查询官方最新稳定版并选择相互兼容组合，记录查询日期、版本与兼容依据；rust-toolchain.toml 锁 Rust，app/.flutter-version 是 Flutter 唯一来源；app/android/toolchain.versions（AND-01）锁 SDK/AGP/Gradle/Kotlin/NDK/cargo-ndk/CameraX/androidx.biometric，app/windows/toolchain.versions（WIN-01）锁 MSVC/SDK/CMake/Inno，平台文件不重复 Rust/Flutter；tools/toolchain.versions 锁 Python/Node 与 fuzz nightly 日期、cargo-fuzz，tools/requirements.txt 锁 Python 包（v5.3.1 明确文件分工）；SQLCipher、ort 等依赖按首张使用卡开工时锁 Cargo.lock/pubspec.lock；回填本 ADR，升级经 ADR 修订和完整 CI | 不锁定：构建不可复现（CORE-42），AI 生成代码按不同版本的 API 编写导致编译失败 | 依赖出现安全公告（`cargo audit`、OSV）或平台商店要求新版本 SDK | 采纳（甲方 2026-10-19 确认） | CORE-01、CORE-41、CORE-42、AND-01、WIN-01 |
| ADR-V5-16 | 云识别供应商 | 推荐：供应商须满足：境内处理与存储（README §6 Q8）、合同约定不用于训练、图片保留期不超过 CORE-33 策略、支持按请求计量；适配经 `VisionProvider` 端口，每家一个约 120 行的适配器；选定前云识别不对用户开放 | 未选定前上线：无法给出准确的隐私告知（CORE-34 预览页需列出供应商、地域与保留期） | M0 选定后补记厂商、模型与合同要点；价格或条款变化 | 待定（M0 定案；正文按推荐方案撰写） | CORE-33、CORE-34 |
| ADR-V5-17 | 编辑器空位记法 | 采纳草稿专用 \fmlhole → FormulaNode::Hole；正式修订拒绝未填空位，错误 PARSE_HOLE_UNFILLED | 用 `\square` 或 `\Box`：与合法数学符号无法区分；编辑器自建树模型：源码与树两套事实，撤销与同步难以一致 | 需要与外部编辑器互通空位格式 | 采纳（甲方 2026-10-19 确认） | CORE-05、CORE-06、CORE-09、CORE-12、CORE-37 |
| ADR-V5-18 | 服务端托管与云厂商 | 推荐：部署在境内云（README §6 Q8）；服务只依赖 PostgreSQL 与 S3 兼容对象存储接口，不使用厂商专有 SDK；容器化部署（CORE-43）；具体厂商与规格在 M0 选定 | 使用厂商专有服务（如专有消息队列、函数计算）：迁移成本高，测试替身难做 | M0 选定后补记；成本或合规要求变化 | 待定（M0 定案；正文按推荐方案撰写） | CORE-25、CORE-33、CORE-43 |
| ADR-V5-19 | 平台差异的接入方式 | 采纳共享行为与平台接缝：共享 Dart 行为只有一份；平台经 PlatformPorts.platformInstallers 与 FeatureRegistry 登记；共享界面不判断平台 | 平台卡各写一份共享行为：两端逻辑漂移，测试加倍；共享界面内做平台分支：违反 CORE-41 规则，平台卡须修改共享文件 | 某平台出现无法用现有接缝表达的界面差异时，先新增接缝（修订 CORE 卡）再写平台实现 | 采纳（甲方 2026-10-19 确认） | CORE-04、CORE-36、CORE-37、CORE-40、CORE-50、CORE-51、AND-07、AND-08、WIN-03、WIN-04、WIN-05、WIN-06、WIN-07、WIN-08、WIN-09 |
| ADR-V5-20 | HTTP 传输实现 | 采纳 dart:io HttpClient 平台传输，由 NetworkGuard 包装后注入；平台只负责系统证书、静态代理与流式传输 | 原生 OkHttp / WinHTTP：需要大块数据跨通道流式回传与两套取消语义；第三方 HTTP 插件：引入额外依赖与权限 | 需要证书固定、PAC 自动代理或 HTTP/3 时 | 采纳（甲方 2026-10-19 确认） | AND-09、WIN-10、CORE-28 |
| ADR-V5-21 | 复制公式的剪贴板格式 | 一次复制同时写入多种常见格式，由粘贴目标自动选用：纯文本为 LaTeX 源码；MathML（Windows 以 Office 识别的格式名写入，供 Word 等转为可编辑公式）；HTML 片段（内嵌 PNG，alt 为 LaTeX）；SVG；PNG（Windows 另加 CF_DIB 与 text/x-latex；Android 写 text/plain、text/html 与经 FileProvider 的 image/png）；“复制为”菜单单独复制 LaTeX、Unicode 文本、MathML 或图片。格式内容由 Rust（MathML、SVG）与共享 Dart（PNG、HTML）统一生成，平台卡只负责写入；不写应用私有格式，不做复制后自动清空 | 只复制 LaTeX 与图片：粘贴到 Word 只得到图片、无法再编辑；应用私有格式：无外部程序能识别，徒增维护；复制后自动清空：与系统剪贴板历史行为冲突且易误伤用户 | Office 不再识别 MathML 剪贴板格式、出现主流目标需要的新格式（如 OMML）或剪贴板内容被证实泄露隐私时 | 采纳（甲方 2026-10-19 确认，README §6 Q12） | CORE-37、CORE-52、AND-03、WIN-05 |
| ADR-V5-22 | Windows 快捷键默认键位与自定义 | 默认键位按“Word 有默认键则从 Word，LaTeX 编辑器有通行键则从之，二者都没有才用本应用约定”确定（上标 Ctrl+Shift+=、下标 Ctrl+=、插入公式 Alt+=、查找 Ctrl+F、重做 Ctrl+Y 与 Ctrl+Shift+Z）；设置页提供自定义（录制、冲突替换、恢复默认），键位以 WIN-08 `defaultKeymap` 为唯一来源，自定义差异存在设备偏好 `keymap.v1`；撤销、剪贴板、导航键固定，系统与输入法组合键（Ctrl+Space、Shift+Space、Ctrl+.、Ctrl+Alt、Win 组合）不可分配 | 固定键位：习惯 Word 或 LaTeX 编辑器的用户无法改到熟悉的键；允许改撤销与剪贴板键：与系统文本框行为冲突，易误操作；照搬 LaTeX 编辑器的 Ctrl+Space 补全：与中文输入法切换键冲突 | 甲方要求跨设备同步键位、提供多套预设方案，或 Android 端需要实体键盘快捷键时 | 采纳（甲方 2026-10-19 确认，README §6 Q11） | WIN-08、WIN-14、CORE-38 |
| ADR-V5-23 | LaTeX 命令补全与公式库批量操作 | 两项都在共享界面实现、两端一致：补全由 CORE-53 经 CORE-37 `LatexSourceAssist` 接入，候选只来自 CORE-06 白名单子集的数据文件，键入 `\` 或 `\begin{` 自动弹出，不设手动触发键；批量操作由 CORE-54 经 CORE-38 `LibraryListDecorator` 接入，按键沿用文件管理器习惯，Rust 侧 `library.batch` 单个写事务执行、可取消并整批回滚、一次最多 10000 条；同时补齐 CORE-14 的条目元数据修改（`library.update_meta`）与回收站查询（`SearchQuery.trashed`） | 用 Ctrl+Space 手动触发补全：与中文输入法切换键冲突；允许用户自定义宏扩充补全：与 CORE-06 禁止宏定义冲突；批量操作逐条调用单项 op：一万条需上万次跨语言调用且无法整体回滚；只在 Windows 实现：接实体键盘的 Android 设备体验不一致 | 甲方要求自定义片段、补全与列表按键可自定义，或批量导出、批量复制进入 V1 时 | 采纳（甲方 2026-10-19 确认，README §6 Q16） | CORE-14、CORE-37、CORE-38、CORE-53、CORE-54、WIN-08 |
| ADR-V5-24 | 界面设计语言与自适应策略 | 交互取“不背单词”的灵感：一屏一事、主操作在拇指可及区、作答后即时而克制的反馈、低打扰；视觉为原创（5 套以传统颜料命名的预设主题色、“公式台面”展示区、线性图标与系统黑体），不复制原型的配色、图标、插画与版式；两端共用 CORE-55 的一套令牌、组件与页面布局，布局只按窗口宽度分档（< 600、600–959、≥ 960）与矮高度（高 < 480）决定，控件密度只按输入方式（touch、pointer、stylus）决定，共享界面不判断平台；Android 手机与平板都随系统旋转，平板指最短边 ≥ 600 dp（README §6 Q17、Q18）；主题色 5 套、外观模式浅色 / 深色 / 跟随系统，按设备保存、不同步（Q19、Q20），所有组合满足 WCAG 2.1 AA；平台差异只经 AND-13、WIN-15 实现的接缝接入（输入方式、触感、动效缩放、偏好存储、系统栏与标题栏跟随） | Android 用 Material、Windows 用 Fluent 各自原生：两套组件、两套黄金图与文案，页面卡要么做平台分支（违反 CORE-01 依赖规则 5 与 ADR-V5-19）要么写两遍，同一用户在两端看到不同的作答反馈，违背双端风格统一（R42.d），Fluent 还需引入第三方包；Android 12+ 动态取色：主题色由壁纸决定，对比度与语义色（正确 / 错误 / 掌握度）无法预先验证，可能与壁纸色相近而误读，Windows 无对应能力，两端外观不一致，且与“可选 4～6 套主题色”重复；手机锁竖屏：只需一套竖屏布局、实现最省，但外接键盘、支架与横握时无法使用，与 Q17 冲突，拍照页单独锁竖屏会在旋转时来回闪烁；按平台而非尺寸布局：Windows 窄窗口、Android 平板横屏与折叠屏展开都得不到合适布局，只能继续加分支；照搬原型视觉：版权与商标风险，且单词卡版式不适合公式 | 甲方要求动态取色或品牌色、主导航入口超过 4 个、试点（§A.6）中主操作可达性或判定反馈理解率不达标，或新增平台需要新的输入方式时 | 采纳（甲方 2026-10-19 确认，README §6 Q17～Q20；色值、令牌与布局细则以 CORE-55 为准） | CORE-55、CORE-36、CORE-37、CORE-38、CORE-39、CORE-40、CORE-47、CORE-48、CORE-49、CORE-50、CORE-51、CORE-52、CORE-53、CORE-54、AND-05、AND-13、WIN-06、WIN-15 |
| ADR-V5-25 | 界面性能预算 | 采纳 CORE-01 的五行界面预算，M0 实测作为达标证据而非另行采纳前提；Windows 集成测试使用 Profile，Release 外部采样验证发布性能（WIN-13）；未达标记缺陷并复评本 ADR | 不设界面指标、只做“流畅”主观验收：无法回归，退化到发布后才被发现；统一按一帧（16 ms）设硬阈值：判分与排版本身已占 25–50 ms，中端 Android 无法达成，只能用骨架屏掩盖；只在 Windows 测：中端 Android 才是瓶颈，结论不可代表两端 | M0 基准设备实测任一行连续 3 轮不达标，或需求负责人更换基准设备时 | 采纳（甲方 2026-10-19 确认） | CORE-01、CORE-39、CORE-55、AND-12、WIN-13 |
| ADR-V5-26 | S1 数据与领域编排 | 内置最小数据和 EngineContext 归 CORE-56（fml-ffi）；ConstantValue 下沉 CORE-05，领域算法不放宽依赖；CORE-28 整体前移 S2，经 GuardContext 注入账户，后续功能自登记钩子 | 等 S4 包才初始化：S1/S2 无法验收；领域引入解析器：违反依赖边界 | 数据或上下文无法在约 450 行内交付时先拆卡 | 采纳（修订方决定） | CORE-05、CORE-09、CORE-10、CORE-28、CORE-36、CORE-56 |
| ADR-V5-27 | 跨卡格式与精确数值 | AST 字段穷举、确定性 ID 归 CORE-05，WrapRecord 确定性 CBOR 归 CORE-21；Rational 使用 i128，JSON 以十进制字符串传输；RecognitionMode wire 归 CORE-33 | i64 无法表示 SI 定义值；各卡自定编码破坏备份与同步 | 真实数据超 i128 或 schema 升级时评估 | 采纳（修订方决定） | CORE-02、CORE-05、CORE-08、CORE-14、CORE-21、CORE-25、CORE-33 |
| ADR-V5-28 | 持久化与同步真值 | 档案事务提交业务/时钟/outbox；跨设备无全局事件序，缓存变更代数失效全算；升级以档案journal为准补投影设备注册表；包元数据全设备一库；历史密钥只存平台槽位，SessionKey独立随机并AEAD包装 | 跨SQLite文件假原子、账户级包安全水位或明文历史密钥会造成恢复/防回滚冲突 | 数据规模导致全量统计不可达预算时评估向量缓存 | 采纳（修订方决定） | CORE-13、CORE-14、CORE-15、CORE-20、CORE-24、CORE-26、CORE-32 |
| ADR-V5-29 | FSRS API 与状态包装 | 算法基准固定 fsrs=6.6.2，使用FSRS::new/next_states/memory_state、自由函数fsrs::compute_parameters(ComputeParametersInput)与FSRS::evaluate（留出集log-loss）；学习状态按CORE-17表由项目包装，不引入rs-fsrs；该版本正常依赖为itertools/log/ndarray/priority-queue/rand/rayon/serde/snafu/strum，Burn仅dev-dependency（官方docs.rs核实2026-10-19；v5.3.1订正API形态与依赖清单），包体仍测产物。此算法/向量固定版是V5-15通用最新稳定规则的明确例外，升级先修此ADR及向量 | 照抄不存在的整套调度API无法生成FS向量；另引状态机破坏同日重复规则 | Q34改变或库升级时重审，真实实现补锁文件与独立FS参照输出 | 采纳（修订方决定） | CORE-17；README Q34 |
| ADR-V5-30 | Dart分层、网络构造与主题入口 | ui只放Widget/绘制，VM/用例/DTO在lib特性目录，composition负责构造；网络构造名单唯一文件归CORE-01；FmlTheme.of返回8项聚合FmlTokens，缺扩展明确失败 | 放宽ui绑定会让平台/传输渗入，双扫描白名单会误伤平台实现 | 新平台或新主题令牌时修订对应契约 | 采纳（修订方决定） | CORE-01、CORE-28、CORE-37、CORE-38、CORE-39、CORE-40、CORE-41、CORE-46、CORE-47、CORE-48、CORE-49、CORE-50、CORE-51、CORE-52、CORE-53、CORE-54、CORE-55；AGENTS |
| ADR-V5-31 | Windows启动与安装时序 | 启动器独立WIN-16、互斥+原子文件+journal补偿；首帧托盘/健康早于解锁；安装前持句柄等待旧进程；Profile集成与Release外部采样；参数按Flutter模板传Dart main，协议1常规更新不覆盖启动器；v5.3.1：备份保留到档案打开确认（opened），返回码10退回pending，控制文件只由启动器写且逐字节定义 | order95健康会因用户等待误回滚；首帧即删备份使迁移失败无法回退；恢复失败不能启动损坏库 | 启动器协议升级、恢复范围或健康定义改变时重审 | 采纳（修订方决定） | CORE-04、CORE-36；WIN-01、WIN-02、WIN-03、WIN-06、WIN-09、WIN-13、WIN-16；补充见§A.4.5 |
| ADR-V5-32 | Casdoor 能力差异的补齐方式 | 刷新只经 CORE-22 令牌代理（Casdoor 对授权码令牌刷新要求 client_secret，仅服务端持有）；重放检测与整族吊销由业务库 auth_refresh_family/auth_refresh_used（只存 HMAC）实现；不依赖 sid；auth_time 只取授权码换得的令牌，刷新所得令牌缺 auth_time 时敏感接口按超时处理并 prompt=login 重登；TokenFormat 固定 JWT-Custom 且不含个人信息 | 等待上游补齐：上线无期；改用 Keycloak：见 §A.4.4 代价；代理不存状态：无法吊销整族 | Casdoor 原生提供刷新令牌族吊销与刷新保留 auth_time，或更换身份服务时 | 采纳（修订方决定，待甲方追认；依据见 §A.4.6） | CORE-22、CORE-23、CORE-25、CORE-43 |
| ADR-V5-33 | 整库回退后的设备身份 | 本地库被整体恢复（WIN-16 回滚、备份恢复）后，同步客户端在拉到本设备 device_seq 大于本地的 envelope 或推送遇本设备 op_id CONFLICT 时，于同一合并事务中更换 device_id（device_seq 归零、lamport 取已见最大值）；字段时钟 (counter, device_id) 完全相同而值不同时取字段规范 JSON 的 BLAKE3 较大者 | 启动器提交前禁网：首帧后钩子无法保证；回滚时清空同步状态重新全量：丢失回滚后本机写入且流量大 | 引入服务端设备登记或改变时钟格式时 | 采纳（修订方决定） | CORE-13、CORE-26；WIN-16、CORE-27 |
| ADR-V5-34 | 界面依赖视图与路由位置 | AppDeps 只在 composition 与 app/lib/<feature>/ 使用；路由函数放各特性目录 routes.dart，由 app/lib/composition/routes.dart 聚合；ui/ 只接收 UiDeps、VM、DTO 与回调，CORE-41 DEP-5 扫描 | 继续把 AppDeps 传入页面：CoreBinding/PlatformPorts 渗入 ui；每页单独注入：组装样板过多 | 引入新的状态管理框架时 | 采纳（修订方决定） | CORE-36、CORE-38、CORE-39、CORE-40、CORE-41、CORE-46、CORE-47、CORE-48、CORE-49、CORE-50、CORE-51 |

| ADR-V5-35 | P1 职责拆分 | 保留原编号，新增 CORE-57～CORE-68及AND-14，材料工具、组件/编辑、库工具/草稿、API/账户页/控制器、墨迹、同步快照各单一构建职责；旧消费者同步依赖与阶段，fml-store 持 I/O、fml-sync 保持纯规则 | 顶格单卡跨多个子系统会迫使编码会话再改契约 | 实现估算超500行先继续拆卡 | 采纳（修订方决定） | CORE-22、CORE-23、CORE-26、CORE-36、CORE-37、CORE-38、CORE-40、CORE-55、CORE-57、CORE-58、CORE-59、CORE-60、CORE-61、CORE-62、CORE-63、CORE-64、CORE-65、CORE-66、CORE-67、CORE-68、AND-14 |

| ADR-V5-36 | Android API 分档与导入所有权 | 认证器按 API 分档、权限白名单按来源卡启用；CORE-04 明确导入批次时限；MainActivity 模块化、S0 正式 Unsupported 桩；官方依据见 §A.4.7 | 省略 API 条件会在旧系统抛错；发布引用 test Fake 无法构建 | AndroidX 或 SDK 升级，M0 探针不通过 | 采纳（修订方决定） | CORE-04、AND-01、AND-02、AND-03、AND-05、AND-06、AND-08、AND-12 |

| ADR-V5-37 | Windows runner与输入/发布协议 | 平台线程统一派发、可注销窗口委托、FocusManager早期按键入口；签名叶证书指纹白名单与PDB归档；Windows Hello密钥机制未核实保持M0阻断 | 工作线程直接回复/根Focus优先/仅CN信任均不可作为保证 | 引擎/SDK升级或设备探针失败 | 采纳（修订方决定；外部前提见A.4.8） | CORE-36、WIN-01、WIN-03、WIN-07、WIN-08、WIN-12、WIN-15 |

### A.4.3 邮件发信供应商筛选（2026-10-18）

筛选条件：支持 API 或 SMTP 发送事务邮件、有免费额度、可替换。用量估算：每次注册约 1～2 封，找回口令另计。

| 供应商 | 免费额度 | 数据地域 | 结论 | 来源 |
| --- | --- | --- | --- | --- |
| 阿里云邮件推送（DirectMail） | 每个主账户共 2000 封（一次性），每天最多 200 封；超出按量计费 | 境内 | 默认通道 | [计费说明](https://www.alibabacloud.com/help/zh/directmail/latest/billing-methods) |
| 腾讯云邮件推送（SES） | 每个账号共 1000 封（一次性，不限有效期）；超出按日后付费 | 境内 | 备用通道 | [计费概述](https://cloud.tencent.com/document/product/1288/47930) |
| Brevo | 每天 300 封，长期免费；账户需审核后才能发送 | 境外 | 不接入 | [Pricing](https://www.brevo.com/pricing/) |
| Resend | 每月 3000 封、每天 100 封，长期免费 | 境外 | 不接入 | [Pricing](https://resend.com/pricing) |
| Mailjet | 每天 200 封、每月 6000 封（第三方实测；官网定价页未能访问核实） | 境外 | 不接入 | [第三方对比](https://www.cunzhangblog.com/emailsend) |
| SMTP2GO | 每月 1000 封，长期免费 | 境外 | 不接入 | [Pricing](https://www.smtp2go.com/pricing/) |
| Mailgun | 每天 100 封 | 境外 | 不接入 | [Free plan](https://help.mailgun.com/hc/en-us/articles/203068914-What-does-the-Free-plan-offer) |
| MailerSend | 每月 500 封，需填写信用卡 | 境外 | 不接入 | [Pricing](https://www.mailersend.com/pricing) |
| Postmark | 每月 100 封，仅供联调测试 | 境外 | 不接入 | [Pricing](https://postmarkapp.com/pricing) |

结论：境内两家的免费额度都是一次性的，合计约 3000 封，用完后转按量付费；长期免费的都是境外服务。按 README §6 Q7（含未成年人）与 Q8（数据境内）的口径，V1 只接境内两家。甲方已于 2026-10-18 确认维持境内方案；免费额度用完后按量付费，上线预算需包含这部分费用。今后若改用境外服务，须甲方重新确认，届时新增一个 `EmailSender` 实现并修订本节与 ADR-V5-11，同时在隐私政策中增加出境告知与单独同意。额度与价格以各供应商控制台为准，上线前复核。

### A.4.4 v5.3 决策与身份服务筛选（2026-10-19）

D1：采纳开工时锁定规则（V5-15）；D2：Casdoor（V5-14）；D3：Fake 验收编码、M-MODEL 验收真实模型（V5-13）；D4：Inno Setup 6（V5-12）；D5：非采购方案采纳，V5-13/16/18 经 Fake 隔离；D6：文档 v5.3，仅本地 main 按组提交，不推送、不打标签。以上均由甲方在本轮逐项确认。

| 候选 | 许可与简中 | 账户与 OIDC | 境内发信接缝 | 资源与维护评估 |
| --- | --- | --- | --- | --- |
| Casdoor（采用） | Apache-2.0；含中文 UI | 邮箱口令、验证码、找回、PKCE；具体版本需契约验收 | 邮件 provider；本项目验证码经 CORE-45，不启用绕过该门面的公共注册/找回路径 | Go 服务加数据库；组件少，预计维护成本最低，尚无本项目压测数据 |
| Keycloak | Apache-2.0；支持本地化 | 注册、验证、找回、PKCE；六位码需流程扩展 | SMTP 或受测 provider 扩展 | 官方建议小型生产容器 2 GB；扩展与 JVM 运维量较大 |
| ZITADEL | 当前主分支 AGPL-3.0；简中覆盖待验收 | 自托管、邮箱口令、验证码与 PKCE | SMTP 或受测通知适配 | 许可与自托管升级需维护，无本项目资源实测 |
| Hydra + Kratos | 两者 Apache-2.0；简中 UI 自行交付 | Hydra 管 OIDC，Kratos 管账户、验证和找回 | 自托管 courier/SMTP 适配 | 两服务及登录同意 UI，组件与自建界面最多 |

各项均可部署在境内；不得据此推定默认无遥测、默认六位码策略或默认支持本项目 auth_time/刷新轮换。CORE-22 开工锁定 Casdoor 版本、镜像 digest 与配置，契约测试覆盖 PKCE、刷新令牌轮换/重放、六位码、找回吊销、auth_time 与 prompt=login；缺项只能用受测适配补齐，变更产品须修订 V5-14。无合格实测证据时仅 Fake 编码通过，真实认证上线被门槛阻断。Casdoor 原生邮件路径必须禁用或指向内部受认证适配器，不能绕过 EmailSender。v5.3.1 按 master 源码核实的能力差异与补齐方式见 §A.4.6 与 ADR-V5-32。

官方核实入口（查询 2026-10-19；实现开工复核具体版本）：[Casdoor 源码与许可证](https://github.com/casdoor/casdoor)、[邮件 provider](https://casdoor.org/docs/provider/email/overview/)、[Keycloak 管理指南](https://www.keycloak.org/docs/latest/server_admin/index.html)、[内存建议](https://www.keycloak.org/server/containers)、[ZITADEL 许可证](https://github.com/zitadel/zitadel/blob/main/LICENSE)、[Hydra](https://github.com/ory/hydra)、[Kratos](https://github.com/ory/kratos)。维护成本为本项目组件数量与定制量的工程判断，不是官方基准。

### A.4.5 ADR-V5-31 Windows启动与恢复补充（2026-10-19）

WIN-16 独立于安装器；WIN-02 消费其制品，WIN-03 仅负责下载与协议。先持进程句柄等待退出，再启动 Inno，保留 AppMutex。firstFrameHooks 独立于顺序解锁/同步；托盘先创建再允许隐藏，健康按版本+本轮 nonce 确认。journal 记录原子单文件动作，进程结束后才恢复，恢复失败保留唯一备份并进入救援，不启动损坏库。

2026-10-19 官方核对：[Inno AppMutex](https://jrsoftware.org/ishelp/topic_setup_appmutex.htm) 在启动时检查互斥；[退出码](https://jrsoftware.org/ishelp/topic_setupexitcodes.htm) 的 5 也包含 Abort，非零均未完成；[MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw) 支持 REPLACE_EXISTING/WRITE_THROUGH；[TerminateProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess) 是异步终止，须再等待进程句柄。它们不提供多文件事务，故定义恢复 journal。

WIN-13 的集成驱动改为 Profile；Release 用外部启动/版本/签名冒烟与日志采样。[Flutter build modes](https://docs.flutter.dev/testing/build-modes) 区分 Profile 分析与 Release 发布，[integration_test 官方驱动示例](https://docs.flutter.dev/testing/integration-tests) 通过测试驱动采集。禁 GPU 以专用矩阵机 Basic Display Adapter 实测并登记，不使用无依据的 FLUTTER_ENGINE_SWITCH 环境变量。工具链锁定后先跑最小驱动探针，未通过不得称矩阵就绪。命令行透传使用[Flutter官方Windows runner模板](https://github.com/flutter/flutter/blob/master/packages/flutter_tools/templates/app/windows.tmpl/runner/main.cpp.tmpl)的GetCommandLineArguments与DartProject.set_dart_entrypoint_arguments，由WIN-01交付Dart main(List<String>)参数快照，不读取VM参数冒充用户命令。

v5.3.1 补充（2026-10-20）：首帧健康只证明壳可呈现，迁移在其后的 order 20 档案打开中发生，故 committed 后不立即删除 db-backup-C 与 app-C，改由 WIN-03 在 CORE-23 AccountController 首次进入 *Unlocked 时调用 `--confirm-opened` 写 opened.json，启动器据此清理；连续 3 次启动未打开则弹原生对话框让用户选择继续或恢复（阈值见 README §6 Q36（待确认））。应用返回码 10 只表示转发，启动器把 journal 退回 pending、删除本轮备份而不恢复，并在验证前用 OpenMutexW 检查 SingleInstance。Inno Pascal 不承担原子写与 journal 判断，普通模式经 `--register-install`、更新模式由 `--install-after-exit` 在 Inno 退出码 0 后登记；启动器 [Files] 按 Inno 默认版本比较替换并以 [CheckForMutexes](https://jrsoftware.org/ishelp/topic_isxfunc_checkformutexes.htm) 跳过运行中的启动器（[Files] 版本比较规则见 [Inno [Files]](https://jrsoftware.org/ishelp/topic_filessection.htm)）。journal、manifest、healthy/opened、命名管道 armed 与 WM_COPYDATA 均给出逐字节格式。`--minimized` 按 [Flutter Windows runner 模板](https://github.com/flutter/flutter/blob/master/packages/flutter_tools/templates/app/windows.tmpl/runner/flutter_window.cpp) 的首帧 Show 回调改为不显示，托盘失败由 WIN-06 firstFrameHooks order 15 兜底显示。整库恢复后的设备身份见 ADR-V5-33。

### A.4.6 Casdoor 能力核实与 ADR-V5-32 依据（2026-10-20）

读取 casdoor/casdoor master 源码（2026-10-20；行号随上游提交漂移，开工锁版本时按 ADR-V5-15 复核）：

| 能力 | 源码事实 | 本项目处理 |
| --- | --- | --- |
| 授权码 + PKCE | 校验 code_verifier（object/token_oauth.go 授权码分支） | 直接使用 |
| prompt=login / max_age | controllers/auth.go 调用 object.IsSessionAuthFresh：prompt 含 login 或会话认证时间超过 max_age 时要求重新输入凭据（object/token_oauth_util.go） | 直接使用，契约测试确认 |
| auth_time | 授权码路径把会话认证时间写入访问令牌与 ID token（jwtTokenOptions.AuthTime>0 时）；RefreshToken 调用 generateJwtToken 不带该选项，刷新所得令牌没有 auth_time | 敏感接口缺 auth_time 按超时处理 |
| sid | 令牌声明中没有 sid；Token 表的 SessionId 只在库内随刷新沿用 | 不依赖 sid，改用令牌族表 |
| 刷新轮换与重放 | 默认删除旧令牌（DisableRefreshRotation=false）；旧令牌再用只返回 “refresh token is invalid or revoked”，不吊销后继令牌 | 代理令牌族表吊销整族 |
| 刷新需 client_secret | checkRefreshClientSecret：authorization_code 与 token-exchange 授权得到的令牌，刷新时必须带正确 client_secret | 刷新只能经 CORE-22 代理，族表不会被绕过 |
| 令牌内容 | JWT 格式内嵌整个用户对象；JWT-Empty 的 UserShort 仍含 email、phone、displayName；JWT-Custom 按 tokenFields 选择字段 | 固定 JWT-Custom，契约测试断言无个人信息 |
| 有效期 | Application.ExpireInHours、RefreshExpireInHours 为小时（float64），轮换时新刷新令牌重新计时 | 0.25 与 720，即 15 min 与闲置 30 天 |

出处：[object/token_oauth_util.go](https://github.com/casdoor/casdoor/blob/master/object/token_oauth_util.go)、[object/token_jwt.go](https://github.com/casdoor/casdoor/blob/master/object/token_jwt.go)、[object/token_oauth.go](https://github.com/casdoor/casdoor/blob/master/object/token_oauth.go)、[controllers/auth.go](https://github.com/casdoor/casdoor/blob/master/controllers/auth.go)、[object/application.go](https://github.com/casdoor/casdoor/blob/master/object/application.go)。

用户可见行为不变：敏感操作本来就要求 300 s 内交互登录（刷新从不更新 auth_time）；刷新令牌被重放时整族失效，用户需重新登录，这是 OAuth 安全实践的常规结果。

### A.4.7 P1 Android 官方事实待核实清单（2026-10-20）

本轮官方Android页面请求超时，无正文证据；以下是核对入口，不构成已核实声明。H4的API分档/页对齐规范仍需M0锁定版本下验证，未验证前不提升AND卡就绪等级。

- [AndroidX PromptInfo](https://developer.android.com/reference/androidx/biometric/BiometricPrompt.PromptInfo.Builder)：28–29 不支持 STRONG 与设备凭据组合；[BiometricPrompt](https://developer.android.com/reference/android/hardware/biometrics/BiometricPrompt) 的 CryptoObject 约束分 API，不把非加密提示等同密钥认证。
- [多选契约](https://developer.android.com/reference/androidx/activity/result/contract/ActivityResultContracts.PickMultipleVisualMedia)：多选最小2；系统/SAF fallback 的数量行为仍需返回后校验，不信任供应方遵守上限。
- AndroidX core 主干清单读取未发现动态接收器权限；不能用主干替代锁定版合并清单。以锁定依赖生成的 merged manifest/依赖AAR为M0证据，若引入该signature权限须保留，未引入则不强加。
- [16 KB 页支持](https://developer.android.com/guide/practices/page-sizes)：r28 默认对齐，r27 需显式支持；仍检查每个第三方 .so 与 Rust 产物。真机/ROM 及锁定 AndroidX 组合未实测，保留 M0 外部前提，不将官方 API 存在等同交付验证。

### A.4.8 Windows runner、按键与发布（ADR-V5-37，2026-10-20）

采用 FocusManager early handler、平台线程结果队列与证书指纹白名单。已读取 Flutter 3.35.7 的 [focus_manager.dart](https://github.com/flutter/flutter/blob/3.35.7/packages/flutter/lib/src/widgets/focus_manager.dart) 和 [hardware_keyboard.dart](https://github.com/flutter/flutter/blob/3.35.7/packages/flutter/lib/src/services/hardware_keyboard.dart)：early handler 在焦点链之前，HardwareKeyboard 广播全部 handler，不短路。锁定 Flutter 版本必须回归此行为。

官方依据：[平台通道线程](https://docs.flutter.dev/platform-integration/platform-channels)、[指针通知](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerpointerdevicenotifications)、[MSVC DEBUG](https://learn.microsoft.com/en-us/cpp/build/reference/debug-generate-debug-info?view=msvc-170)。指针/子HWND、1809 Hello interop 和扩展解码的实际设备行为列为 M0 外部前提；不得用 API 文档替代真机结果。签名格式由 WIN-12 所有，WIN-03 只消费生成的 pin 集合。关联 CORE-36/58、WIN-01/03/08/12/15。

## A.5 开发前冻结清单

进入大规模 UI 或内容录入前必须冻结以下契约，未冻结前不得开始，否则后期返工成本会远高于文档修订成本：

1. `FormulaNode` / `FormulaRevision`（CORE-05）、类型与量纲（CORE-09）、DisplayList（CORE-12）、识别契约（CORE-29）。
2. C ABI 头文件与 DTO 外壳（CORE-03）、平台端口（CORE-04）。
3. 本地数据库 schema v1 与迁移策略（CORE-13）。
4. 资源包 manifest 与签名公钥分发方式（CORE-15）。
5. 游客升级与账户密钥包装流程（CORE-21、CORE-24）。
6. V1 性能与隐私验收指标（CORE-01、CORE-28）。
7. 云识别网关与供应商适配契约（CORE-33），以及四类内容包的范围清单（CORE-16）。
8. 组装层与平台接缝（CORE-04 `composition/` 与 `entry.dart`、CORE-36 `shell_ext.dart` 与门面、CORE-37/40/50 的接缝接口，ADR-V5-19）。

## A.6 试点与复测记录

学习效果试点（CORE-20）、性能基线（AND-12、WIN-13）、识别指标基线（CORE-35）等结果按下表追加记录，不覆盖旧记录。

| 日期 | 项目 | 版本 | 环境与样本 | 结果 | 结论与后续动作 |
| --- | --- | --- | --- | --- | --- |
| — | （尚无记录） | — | — | — | — |

Windows事实核实补充（2026-10-20，ADR-V5-37）：GetSystemMetrics文档说明SM_MAXIMUMTOUCHES为0时无触控，Slate指标不能单独证明有触屏（https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getsystemmetrics）；WIN-15先检查触点。已读取RequestSignAsync（https://learn.microsoft.com/en-us/uwp/api/windows.security.credentials.keycredential.requestsignasync?view=winrt-26100）与IUserConsentVerifierInterop（https://learn.microsoft.com/en-us/windows/win32/api/userconsentverifierinterop/nn-userconsentverifierinterop-iuserconsentverifierinterop）；后者仅验证HWND API，不能推出KeyCredential签名的interop或稳定密钥恢复。WIN-07保留M0阻断并移除签名哈希可恢复密钥假设。

2026-10-20 P1独立复核补证（ADR-V5-36 Android宿主）：[FlutterActivity主干源码](https://raw.githubusercontent.com/flutter/engine/main/shell/platform/android/io/flutter/embedding/android/FlutterActivity.java)、[BiometricPrompt主干源码](https://raw.githubusercontent.com/androidx/androidx/androidx-main/biometric/biometric/src/main/java/androidx/biometric/BiometricPrompt.java)；MainActivity/AndroidChannelModule统一FlutterFragmentActivity。来源仅证明主干API形态，项目锁版AndroidX/Flutter ActivityResult及认证探针仍M0阻断；26–29时效密钥实际认证组合未核实，不降级安全。
