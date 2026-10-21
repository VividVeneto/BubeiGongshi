# CORE-86 测试方案

> 来源卡：[S3_CORE-86_界面.md](../../core/S3_CORE-86_界面.md)（计算链计划、界面与仓储）。本文件是该卡验收标准全文；修改范围时同步修改，工具从下方验收标准行起拼回。

**验收标准**
- [R12] 计算链：两步计划（`v = a t` 输出 v 接 `E_k = \frac{1}{2} m v^2`）运行、保存、重开后运行结果一致；保存事务写出一条 calculation_plan outbox，重开可读（S3验收）；跨设备断言由CORE-46在S6联测执行。
- [R42.e][R42.b] 12步链滚到第8步，360×800↔800×360往返3次保持PlanVm/页面State、输入/feed、结果与滚动偏移，derive.run_plan调用次数不因旋转增加；textScaler=2.0下tester.takeException()为null，值/单位/区间不截断；唯一primary为“运行”，矮高度位于右侧操作区底部。
- [R12] calcPlanRoutes独立注册/calc/plan；library.plan_put/list/delete按原body/ok、UUIDv7重试与1..100名称/1..20步约束；空库list返回{"plans":[]}；calculation_plan迁移0086，codec/applier/墓碑/outbox均归本卡。
- [R16] 上一步输出只接量纲相同的下步输入；保存前先运行，失败步骤定位且不保存；共享页面不取CoreBinding/HTTP、不判断平台。
