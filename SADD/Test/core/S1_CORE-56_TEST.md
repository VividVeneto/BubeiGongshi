# CORE-56 测试方案

> 来源卡：[S1_CORE-56_引擎.md](../../core/S1_CORE-56_引擎.md)（内置引擎数据与上下文编排）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R12][R13][R09] 无账户且断网，fml_call 对 F=ma、m=2 kg、a=3 m/s² 得 6 N 并产生非空 DisplayList；cn-default/iso 可切换；无需 S4 文件。
- [R12] c 同时有 given=3e8、教材=3e8、Exact=299792458 时取 given；去掉 given 取教材，再去掉教材取 Exact，constants_used 保留来源。
- [R19] 在途任务持 generation=0 时 `set_layer` 成功返回 1，新请求用 1，旧任务仍读 0；损坏层返回 `ENGINE_DATA_INVALID` 且 generation 与层集合不变。
- [R19] 叠加向量 `contracts/vectors/engine-data-v1/compose.yaml` 全部通过，至少覆盖：Pack 替换内置单位、Pack 改变内置单位量纲被拒、两包同 ID 冲突、User 层含非 `user:` 单位、移除 Pack 层后恢复内置值、追加字体后内置字体下标不变。
- [R19] `mark_unavailable` 后 `calc.evaluate` 返回 `ENGINE_UNAVAILABLE`；随后 `set_layer` 成功即恢复，结果使用新层。
- [R19] 并发：8 个线程循环调用 `engine.check`/`calc.evaluate`，1 个写者交替 `set_layer`/`remove_layer` 1000 次，无死锁，每个线程观测到的 generation 单调不减；安装由同一数据生成的 bootstrap 引擎层后，语料的 `engine.check` 结果与 DisplayList 与安装前逐字节一致。

- [R18] 同pack_id从v1升级v2（复用同一单位/字体ID）只保留一个Pack层并更新内容；v2无效时旧快照/generation不变；不同pack_id冲突仍拒绝。

- [R19] 以代数MAX-1夹具成功发布到MAX，再set_layer/remove_layer/mark_unavailable分别返回ENGINE_UNAVAILABLE；Arc与代数不再变化、无通知，后续snapshot和业务op拒绝，generation查询available=false；在途旧Arc可完成，重建实例恢复。
