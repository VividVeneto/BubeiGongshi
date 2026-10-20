# CORE-41 测试方案

> 来源卡：[S0_CORE-41_基座.md](../../S0/S0_CORE-41_基座.md)（CI 门禁与可维护性度量）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R19] 聚合测试用固定脚本stub分别返回0/1/2，验证run_all执行全部manifest项、保留Finding、退出码2优先于1、pending单列且不记通过；不在本卡重测扫描规则。
- [R18] CI配置校验lint/test/checks/build/deny依赖及weekly产物存在；stub MAINT-1 warning输出annotation而不发评论，失败规则沿唯一所有者脚本报告。
- [R18] 工具链版本断言（承接 CORE-01）：CI 配置不含硬编码的 Rust/Flutter/Python/Node 版本，只从 CORE-01 锁定文件解析；在测试副本中改写 `app/.flutter-version` 后，CI 解析出的 Flutter 版本随之变化。
- [R19] required_stage=S0允许未启用业务目标以pending归档，存在的目标失败不能SKIP；发布required_stage=S7遇pending/无签字/无设备返回1，清单缺验收行也失败（解析/覆盖规则归CORE-70）。
