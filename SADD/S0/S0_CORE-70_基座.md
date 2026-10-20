### CORE-70 SADD结构与验收索引门禁

**目标**：从唯一文档源校验模块结构、追踪与验收作业索引。

**范围**
- 包含：从CORE-41拆出的SADD-1～12与acceptance_jobs.json校验；结构报告、D.9意见覆盖及D.10/D.12一致性。
- 不包含：语义评级或独立复核，材料生成归CORE-57。

**依赖**：CORE-01、CORE-02、CORE-57、CORE-67、CORE-76

**接口契约**
node tools/sadd/structure.mjs --sadd SADD --out <目录>；Python入口tools/ci/check_sadd.py仅转发参数并保留退出码。输出structure.json（cards、逐规则findings、op/owner清单）及简明终端计数；0无error、1违例、2读写/解析错误。SADD-1～8依次校验七字段/规模、卡ID唯一、依赖方向与无环、阶段不倒置、§1/§2/§3一致、需求双向追踪、文档链接、错误表唯一与统一列；不能用卡数相同替代ID集合一致。SADD-9检查卡引用来源在材料中；10报告本地未收录/未知符号（启发式warning，不替语义）；11核对Q影响列与正文（仅实际依赖；说明性引用可带分类理由）；12校验D.10唯一行/等级/状态与D.12最新有效复核，统计由stats.mjs生成后--check比较。既往历史行不覆盖当前行；a～g或S1～S6任一非通过不能标就绪。

acceptance_jobs.json由CORE-41创建空版本1文件，本卡定义并校验每行{card,requirement,criterion,stage,environment,target,status}，environment取host-rust/host-widget/android-host/windows-host/manual/content；status取active/pending-target。业务卡逐验收条目追加；不存在的业务目标只允许pending-target并打印SKIP pending，已存在目标失败不能SKIP，--release任一pending-target/无人工证据失败。业务目标不成为本S0卡的前置。

PR6现行等级/就绪证据核对调用CORE-76，本卡只检查发布验收清单覆盖与D.12可读表/复核JSON的卡ID一致，不重复实现统计器。

**实现约束**
- 卡解析复用CORE-57 load，就绪证据与统计复用CORE-76 current/stats；保留错误行号；DDL/DTO字段缺陷只能人工语义复核。
- 逐文件估算：结构/阶段/追踪180、op及记录规则80、验收清单60、测试100，附属Python转发20，合计440；temp版check.mjs只作迁移参考，不能不经测试直接宣称全部规则已实现。
- 外部前提：锁定Node/Python；不要求产品crate/设备先实现。

**验收标准**：测试方案全文见 [Test/S0/S0_CORE-70_TEST.md](../Test/S0/S0_CORE-70_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 340 行；主包 `tools/sadd/`（不含测试约100行），附属 `tools/ci/check_sadd.py`（20行转发）。

