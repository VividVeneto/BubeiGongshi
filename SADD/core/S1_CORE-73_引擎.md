### CORE-73 引擎代数查询与缓存失效通知

**目标**：将CORE-56快照generation以可查询、可等待的协议交给Dart缓存消费者。

**范围**
- 包含：engine.generation、engine.wait_generation、EngineGenerationSource及绑定接线；只观察既有快照。
- 不包含：EngineContext层合成与发布（CORE-56）、结果/字形缓存实现（消费方，下游说明，非契约）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-56

**接口契约**
两个op均none scope、v1。engine.generation为call：body={}，ok={generation:string,available:bool}；generation为CORE-56的u64十进制字符串，无前导零，初值"0"。engine.wait_generation为submit：body={after:string,wait_ms:u32}（1～1000），ok={generation:string,available:bool,changed:bool}；当前generation≠after立即返回，否则等发布通知或超时；超时changed=false，取消沿用CORE-03且无回调，通知只代表当前快照，不重放每次更新。持锁只取快照，锁外唤醒等待者；多个更新可合并，绝不回退。提交器每主绑定最多一个等待，纳入64任务上限；不得把等待放UI同步线程。CORE-56发布后在锁外通知条件变量，generation耗尽返回ENGINE_UNAVAILABLE，不回绕。

Dart源（app/lib/binding/engine_generation.dart）：abstract interface class EngineGenerationSource { String? get current; Stream<String> get changes; Future<String> refresh(); Future<void> close(); }；由主绑定创建单实例，首次refresh后串行wait_generation循环，处理CORE-03.engineGenerations得到的代数；用BigInt比较只递增，changes首个事件是当前值，相同值不重复，通知失败将current置null并停用缓存直到refresh成功。跨isolate通过主源消息通知失效，worker本身也在命中缓存前query，不能只依赖消息时序。缓存调用engine/typeset/export时给CORE-03的expected_generation；处理层以同一Arc完成整个parse/bind/check/layout链路，成功信封engine_generation必须等于期望。缓存读取前refresh；执行中更新导致返回旧代数时不缓存、不展示并重试一次；再次变化则返回可重试ENGINE_UNAVAILABLE。通知用于及时清空，query+期望值验证用于防漏通知。

engine.generation例ok={"generation":"2","available":true}；wait body={"after":"1","wait_ms":1000}，ok={"generation":"2","available":true,"changed":true}。available=false时不取缓存，沿用CORE-56 ENGINE_UNAVAILABLE错误码，不创建第二错误定义。共享格式fixtures为contracts/vectors/engine-generation-v1.json。

FFI错误镜像（不重定义代码；通用信封错误见CORE-03）：

| op | 本卡业务/诊断代码及依赖透传 |
| --- | --- |
| engine.generation | 无业务错误；通用信封错误仍适用 |
| engine.wait_generation | 无业务错误；通用信封错误仍适用 |

CORE-56 mark_unavailable返回Result<u64,FmlError>；只有Ok才唤醒代数变更等待者，Err(ENGINE_UNAVAILABLE)不制造新代数。refresh必须查询available，available=false清缓存并拒绝算法调用；耗尽只可重建实例恢复，不循环重试。

engine.generation/wait_generation读取CORE-56 generation_status，exhausted或unavailable时available=false；相同generation也必须应用available变化，refresh不可仅比较代数字符串。耗尽不通知代数变化，最长等待超时后查询得到available=false。

**实现约束**
- 逐文件估算：原生查询/等待95、CORE-56发布通知附属20、Dart源与接线120，合计235；不得为通知新增C导出或全局活动账户。
- 外部前提：CORE-01锁Rust/Dart；无网络/新第三方库；profile切换先移除旧User层并发布代数，再注入新层。

**验收标准**：测试方案全文见 [Test/core/S1_CORE-73_TEST.md](../Test/core/S1_CORE-73_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 235 行；主包 `crates/fml-ffi/`（generation/wait_generation op 与 CORE-56 发布通知接点，约 115 行），附属 `app/lib/binding/engine_generation.dart` 与主绑定接线（约 120 行）；向量为数据。

