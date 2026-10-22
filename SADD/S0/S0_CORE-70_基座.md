### CORE-70 SADD结构与验收索引门禁

**目标**：从唯一文档源校验模块结构、追踪与验收作业索引。

**范围**
- 包含：从CORE-41拆出的SADD-1～12与acceptance_jobs.json校验；结构报告、D.9意见覆盖及D.10/D.12一致性。
- 不包含：语义评级或独立复核，材料生成归CORE-57。

**依赖**：CORE-01、CORE-02、CORE-57、CORE-67、CORE-76

**接口契约**
node tools/sadd/structure.mjs --sadd SADD --out <目录>；Python入口tools/ci/check_sadd.py仅转发参数并保留退出码。输出structure.json（cards、逐规则findings、op/owner清单）及简明终端计数；0无error、1违例、2读写/解析错误。SADD-1～8依次校验七字段/规模、卡ID唯一、依赖方向与无环、阶段不倒置、§1/§2/§3一致、需求双向追踪、文档链接、错误表唯一与统一列；不能用卡数相同替代ID集合一致。SADD-9检查卡引用来源在材料中；10报告本地未收录/未知符号（启发式warning，不替语义）；11核对Q影响列与正文（仅实际依赖；说明性引用可带分类理由）；12校验D.10唯一行/等级/状态与D.12最新有效复核，统计由stats.mjs生成后--check比较。既往历史行不覆盖当前行；a～g或S1～S6任一非通过不能标就绪。

acceptance_jobs.json由CORE-41创建为{version:1,rows:[]}；本卡定义该容器：顶层只含version与rows，version必须为1，(card,criterion,environment)为唯一键，JSON损坏、版本非1或顶层缺字段退出2，重复键、行缺字段或取值越界为违例退出1；本卡校验rows每行{card,requirement,criterion,stage,environment,target,status}，environment取host-rust/host-widget/android-host/windows-host/manual/content；status取active/pending-target；stage取S0～S7（README §2实施阶段），取未列值退出1。业务卡逐验收条目追加；不存在的业务目标只允许pending-target并打印SKIP pending，已存在目标失败不能SKIP。

发布门禁（`check_sadd.py --release` 的唯一定义；CORE-41 只透传 release_args 并聚合退出码）：带 `--release` 时在结构校验之后固定以 required_stage=S7 判定——清单缺 `stage=S7` 的发布验收行、任一行 `status=pending-target`、或 `status=active` 但 `target` 不存在，均退出1并在报告列出 (card,criterion,environment) 与原因；不带 `--release` 时只做容器与结构校验，pending-target 合法。设备可用性、发布凭据与人工签字属发布 checklist（manual，由发布执行人核对并归档证据），脚本不读取、不推断，不因文件存在即记为已签字。业务目标不成为本S0卡的前置。

PR6现行等级/就绪证据核对调用CORE-76，本卡只检查发布验收清单覆盖与D.12可读表/复核JSON的卡ID一致，不重复实现统计器。

**实现约束**
- 卡解析复用CORE-57 load，就绪证据与统计复用CORE-76 current/stats；保留错误行号；DDL/DTO字段缺陷只能人工语义复核。
- 逐组件实现估算：结构/阶段/追踪210、op及记录规则70、验收清单与发布门禁（stage枚举、--release三类拒绝）100、CORE-57/76证据适配65、附属Python转发/CI调用20，合计465；测试不计。temp版check.mjs只作迁移参考，不能不经测试直接宣称全部规则已实现。
- 外部前提：锁定Node/Python；不要求产品crate/设备先实现。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-70_TEST.md](../Test/S0/S0_CORE-70_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约465行；tools/sadd/structure.mjs及本卡编写的证据适配、tools/ci/check_sadd.py与CI调用行；复用CORE-57/76输出而不重复计其实现；不计自测、夹具、验收方案/schema数据与生成物，亦不计README §7.1排除的DTOcheck工具实现。

