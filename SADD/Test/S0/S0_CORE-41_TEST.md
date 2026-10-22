# CORE-41 测试方案

> 来源卡：[S0_CORE-41_基座.md](../../S0/S0_CORE-41_基座.md)（CI 门禁与可维护性度量）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18] 聚合测试用固定脚本stub分别返回0/1/2，验证run_all按manifest顺序执行全部项、退出码2优先于1、pending单列且不记通过；stub返回3、超时或解释器缺失均总退出2；manifest版本非1、id重复、argv[0]非python/node退出2；含`;`与`*`的参数原样传给stub（不经shell、不展开）。不在本卡重测扫描规则。
- [R19] stub输出`crates/a/src/x.rs:12: DEP-1 msg`时，run_all.json该步保留此行原文与id/owner/exit；终端最后一行为`run_all: <n> steps, <e> error, <f> fail, <p> pending`；同一输入两次运行的run_all.json忽略时间字段后字节相同。
- [R18] manifest.json包含全部初始步骤（reservations、check-deps、check-privacy、check-unsafe、check-abi、check-errors、check-sadd、sadd-stats、sadd-selftest、dtocheck、core-sources、maint-report）且owner为对应卡；被删除的脚本路径记pending-target并写入pending.json，加--release时总退出1；check-sadd仅在--release时追加--release。
- [R18] CI配置校验lint/test/checks/build/deny的needs链与deny作业运行cargo deny check；weekly含schedule与workflow_dispatch并归档maint.md/同名JSON（--previous取上周构件）、cargo audit JSON与fuzz崩溃目录；stub MAINT-1 warning输出annotation而不发评论，失败规则沿唯一所有者脚本报告。
- [R18] maint-report步骤argv含`--lcov build/coverage/core.lcov --core-sources build/coverage/core-sources.json`；stub因缺输入返回2时总退出2，不记SKIP或pending。
- [R18] core_sources.py在临时git仓库夹具中：只收录已跟踪的crates/fml-ast/src/lib.rs等协议内文件，排除tests/fixtures路径分量、*.g.rs、未跟踪文件与crates/fml-store；paths按字节序去重；无匹配文件时写空paths、退出0并在pending.json登记；非git目录退出2。
- [R18] 工具链版本断言（承接 CORE-01）：toolchain.py以env与json格式输出全部九个版本键；夹具中的cargo_deny=沿CORE-01已锁版本读取而不改写，本卡首用cargo_audit=/cargo_llvm_cov=登记在同一锁文件后读取，删除cargo_deny=等任一必需键或锁文件退出2；CI配置不含硬编码的Rust/Flutter/Python/Node/cargo工具版本，只经toolchain.py解析；在测试副本中改写`app/.flutter-version`后解析出的Flutter版本随之变化。
- [R18] CODEOWNERS解析：crates/fml-crypto/、crates/fml-sync/、contracts/各至少两名不同所有者；分支保护（required approvals=2、CODEOWNERS审阅、五个required checks）列为manual checklist，未签字不记通过。
- [R18] 初始tools/ci/acceptance_jobs.json等于`{version:1,rows:[]}`并通过CORE-70校验；contracts/policies/shared-writes.json含ci.yml的CORE-41单写登记且reservations design校验通过。
- [R19] required_stage=S0允许未启用业务目标以pending归档，存在的目标失败不能SKIP；发布required_stage=S7遇pending/无签字/无设备返回1，清单缺验收行也失败（解析/覆盖规则归CORE-70）。
- [R19] weekly fuzz步骤用产生崩溃的stub目标：作业失败，崩溃输入作为构件归档且路径写入作业摘要；无崩溃时作业通过。
