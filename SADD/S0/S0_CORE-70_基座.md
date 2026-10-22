### CORE-70 SADD结构与验收索引门禁

**目标**：从唯一文档源校验模块结构、追踪与验收作业索引；机械规则复用既有文档工具，本卡只补其未覆盖的增量规则，不为同一事实写第二套判据。

**范围**
- 包含：SADD-1 的七字段与章节结构、SADD-6 需求双向追踪、SADD-7 文档链接、SADD-8 错误表结构、SADD-9/10 材料输入、SADD-11 Q 影响列、SADD-12 D.10/D.12 证据适配；`tools/ci/acceptance_jobs.json` 容器定义与校验；发布门禁 `--release`。
- 复用（不重写、不计本卡规模、不输出 finding）：SADD-1 的规模数字与索引一致、SADD-2 卡 ID 唯一、SADD-3 依赖方向与无环、SADD-4 阶段不倒置、SADD-5 §3 索引/依赖图/阶段一致、SADD-8 的错误码跨卡唯一，由 README §7.1 的文档工具项承担（`tools/DTOcheck/cards.mjs` 的 CARD-01～10、GRAPH-01～05、STAGE-01～03、README-01～07、MIG-01～02、VER-01，`tools/DTOcheck/xref.mjs` 的 XREF-01～04，`tools/DTOcheck/dto.mjs` 的 DTO-06/18，`tools/sadd/layout.mjs` 的 LAYOUT-01～07）。两套规则不相交，故 finding 不合并去重、互不验收：CI 中是两个独立步骤（`dtocheck` 与本卡 `check-sadd`），失败判定各取自身退出码，本卡不得为同一事实复制判据。上列规则并入本卡时删除原工具中的实现，并按并入行数计本卡规模（README §7.1）。SADD-5 的归属判据：每卡只在按卡号前缀确定的那份 `00-总览.md`（`core/`、`and/`、`win/` 三份，S0 卡不另建总览）的 §3 表中出现一次，名称、依赖、规模与该行一致（CARD-02～05），阶段取该总览 §2 阶段表（STAGE-01～03）。
- 不包含：语义评级与独立复核（CORE-76）、材料生成（CORE-57）、DTO/schema 字段校验（DTOcheck 与 CORE-100）；D.9 历史评审批次的意见覆盖无稳定编号格式、机器判定会误报，本卡不做（需机器覆盖时由 CORE-76 audit 扩展，另立变更单）。

**依赖**：CORE-01、CORE-02、CORE-57、CORE-76、CORE-100

**接口契约**
node tools/sadd/structure.mjs --sadd SADD [--material <目录>] --out <目录>；Python入口tools/ci/check_sadd.py仅转发参数并保留退出码。输出structure.json（`{version:1, cards, findings:[{rule,card,file,line,message}], ops:[{op,owner,mode}], owners:[{kind,key,owner,point}]}`，忽略时间字段后字节稳定、不含绝对路径）与终端逐条Finding行 `<file>:<line>: <rule> <message>`（排序按 card、rule、file、line，末行另给简明计数）；0无error、1违例、2读写/解析错误（缺文件、缺目录、JSON损坏）。SADD-1的七字段：每卡须按序含 目标/范围/依赖/接口契约/实现约束/验收标准/规模 七项，范围须含“包含”与“不包含”子项，缺项、重复或顺序颠倒为违例。代码围栏与 HTML 注释内出现的字段字样不算字段，不得据此判缺项或重复。SADD-6需求双向追踪：README §5 每个[Rxx]至少被一张卡的测试方案条目引用，测试方案引用的[Rxx]必须在§5存在；只改追踪表而保持卡数不变、替换未知卡ID仍失败。SADD-7文档链接：卡内相对链接目标必须在SADD内存在（指向仓库其他目录的链接只要求文件存在）。SADD-8错误表结构：错误表首三列固定为“错误码、级别、可重试”，第4列起为说明性尾列且名称须以“触发条件”开头（如“触发条件与界面行为”），定义HTTP映射的服务端op卡须在其错误表含“HTTP”列，级别只取error/warning、可重试只取是/否，同表同码重复或缺列为违例。SADD-9卡引用来源在材料中：`--material`指向与CORE-57 report.json同结构的目录，逐卡核对被引符号的收录/省略来源；未给该参数时SADD-9/10记pending并打印`SKIP pending SADD-9`，目录不可读或报告损坏退出2，不得记为通过。SADD-10报告本地未收录/未知符号（启发式warning，不替语义）。SADD-11核对Q影响列与正文一致（只核实际依赖；说明性引用可带分类理由）。SADD-12校验D.10唯一行/等级/状态与D.12最新有效复核：调用CORE-76的validateCurrent与stats输出并把其findings原样并入本卡findings（本卡不重复判定等级、旗标与结论），只追加D.10唯一行、就绪串写法与D.12可读表卡ID的机械核对；统计由stats.mjs生成后--check比较。

op/owner清单来源：`contracts/dto/manifest.json`（op→owner、mode，条目形状归CORE-100）与`contracts/policies/shared-writes.json`（entries的kind/key/owner/point登记）；缺文件或JSON损坏退出2。本卡只抄录清单与所列字段，不比对两文件语义（比对归DTOcheck的XREF-01～04与DTO-06）。两个清单当前为空时 `ops`/`owners` 输出空数组，不判失败、不造条目。

acceptance_jobs.json由CORE-41创建（下游说明，非契约）为`{version:1,rows:[]}`；本卡定义该容器：顶层只含version与rows，version必须为1，(card,criterion,environment)为唯一键，JSON损坏、版本非1或顶层缺字段退出2，重复键、行缺字段或取值越界为违例退出1。rows每行为`{card, requirement, criterion, stage, environment, target, status}`：requirement取[Rxx]；criterion为字符串，等于卡内验收条目序号（从1起，按测试方案中以“- [Rxx]”开头的行顺序计数），与card、environment组成唯一键；environment取host-rust/host-widget/android-host/windows-host/manual/content；status取active/pending-target；stage取S0～S7，语义为该验收条目生效的实施阶段，须等于card在00-总览§2实施阶段表中的阶段，取未列值或与阶段表不符退出1。target为带前缀字符串：`path:<仓库相对POSIX路径>`要求存在且为普通文件（目录、断链符号链接不算，符号链接按解析后目标判定）；`job:<作业名>`要求是`.github/workflows/ci.yml`顶层的jobs键。缺前缀、路径不存在、作业名不存在都算目标不存在：不存在的业务目标只允许pending-target并打印`SKIP pending <card>: <target>`，已存在目标失败不能SKIP。

发布门禁（`check_sadd.py --release` 的唯一定义；CORE-41 只透传 release_args 并聚合退出码，下游说明，非契约）：带 `--release` 时在结构校验之后固定以 stage=S7 判定——rows 中 `stage=S7` 的行集合为发布验收基数，该集合为空、集合内任一行 `status=pending-target`、或 `status=active` 但 `target` 不存在，均退出1并在报告列出 (card,criterion,environment) 与原因；不带 `--release` 时只做容器与结构校验，pending-target 合法。设备可用性、发布凭据与人工签字属发布 checklist（manual，由发布执行人核对并归档证据），脚本不读取、不推断，不因文件存在即记为已签字。业务目标不成为本S0卡的前置。

**实现约束**
- 卡解析复用CORE-57 load，就绪证据与统计复用CORE-76 current/stats/validateCurrent；保留错误行号；DDL/DTO字段缺陷只能人工语义复核。
- 逐组件实现估算：七字段/文档链接/需求追踪/Q影响列175（SADD-1、6、7、11）、错误表结构与材料输入115（SADD-8、9、10）、验收清单容器与发布门禁105（stage语义、criterion、target两类、--release三类拒绝）、CORE-57/76证据适配与去重口径50，合计445；测试不计。temp版check.mjs只作迁移参考，不能不经测试直接宣称全部规则已实现。
- 外部前提：锁定Node/Python；不要求产品crate/设备先实现。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-70_TEST.md](../Test/S0/S0_CORE-70_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约465行；主包 `tools/sadd/structure.mjs` 约445行（按上列四项估算），附属 `tools/ci/check_sadd.py` 约20行与 `ci.yml` 调用片段（片段按 §8.4 共享写入点由 CORE-41 合入、本卡不编辑该文件；下游说明，非契约）；复用CORE-57/76与文档工具项的既有实现不计，自测、夹具、report数据与生成物不计。
