### CORE-72 云识别运维与熔断解除

**目标**：在账务核对后可审计地解除供应商预算熔断。

**范围**
- 包含：从CORE-33拆出的clear_recognition_breaker.sql、受控调用脚本、事务测试与操作checklist。
- 不包含：网关/worker/计费（CORE-33）、监控部署（CORE-43，下游说明，非契约）；不添加公网管理端点。

**依赖**：CORE-01、CORE-02、CORE-22、CORE-33

**接口契约**
psql --set=ON_ERROR_STOP=1 --set=provider_id=<已配置id> --set=day=YYYY-MM-DD --set=operator=<1～64字符审计代号> -f server/ops/clear_recognition_breaker.sql。参数仅用psql的SQL字面量引用，不拼SQL；数据库凭据从受控环境读取、不打印。事务锁住recognition_budget(day)及该供应商当日breaker行；已解除幂等返回0且不改原操作者；未解除则写cleared_at/cleared_by，仅该day不存在其他未解除行时设breaker_open=false；不改变spent_units/reserved_units/overrun_units。输入无效/未知provider或日期无记录返回非零。预算仍耗尽时后续POST仍按CORE-33配额拒绝，解除不是赠送额度。

**实现约束**
- 只供运维经数据库受控账号执行；不可写用户图片/识别文本；先核对UNKNOWN/迟到回执再解除。
- 逐文件估算：SQL50、参数预检/受控调用50、PostgreSQL容器测试100、checklist20，合计220；文档不计代码行。
- 外部前提：CORE-33迁移与测试PostgreSQL；真实运维账号/供应商对账由甲方提供。

**验收标准**
- [R40][R19] 两供应商同day熔断：清A后预算仍熔断，清B后关闭标志；重跑不改审计记录，异常事务回滚，跨day互不影响；真实预算未充足时POST仍失败。

**规模**：约 220 行；主包 `server/`（ops/脚本与同构建单元数据库测试）。

