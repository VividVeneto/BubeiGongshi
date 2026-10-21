### CORE-101 识别存储压力与档案守护

**目标**：在识别历史密钥已就绪的当前档案上检查存储压力，按既有阈值触发 GC 并提供只读 UI 状态。

**范围**
- 包含：由 CORE-50 完整拆出的 StorageStatus、installStorageGuard、空闲容量检查、GC、按 handle 单飞/节流水位、ProfileHooks order55、前后台/低内存订阅与关闭排空。
- 不包含：识别候选/历史 VM 或 UI；历史保留设置；GC/历史密钥的核心实现（CORE-32）；识别流程；平台文件端口实现。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-04、CORE-32、CORE-36、CORE-65

**接口契约**

```dart
// app/lib/recognition/storage_guard.dart
final class StorageStatus extends ValueNotifier<bool> { StorageStatus() : super(false); }
// true = 当前档案存储紧张；消费者只能作为 ValueListenable<bool> 订阅，不能写 value。
// app/lib/recognition/install_storage_guard.dart
void installStorageGuard(CompositionContext ctx);
```

- installStorageGuard 从 ctx.features.require<ProfileSessionSource>() 与 ctx.features.require<HistoryKeyUnlocker>() 取得已登记实例，使用 ctx.ports.files/ctx.ports.lifecycle；构造唯一 StorageStatus 并登记于 FeatureRegistry，不缓存 root CoreBinding。前置实例不存在时按 FeatureRegistry 的既有缺失规则停止安装，不降级跳过密钥解锁。
- 通过 CORE-36 ProfileHooks.add(55, 'recognition.storage', hook) 登记每个新 handle 的检查；不是普通 StartupHook。sessions.addBeforeClose 以 recognition.storage 登记内部停止/排空回调。installStorageGuard 的 featureInstallers 片段由 CORE-36 聚合维护者单写合入，必须在 HistoryKeyUnlocker 已登记之后；本卡不依赖识别 UI/流程卡，不复制安装它们。进程/首帧启动钩子不因档案切换重跑。
- 全进程只保留一份 ports.lifecycle.events() 订阅，对 resumed 与 lowMemory 执行同一检查；每个入口先捕获 sessions.current，null 不执行 ensure/FFI/GC。身份比较为 session 对象身份与 handle，同时防止同 profileId 重开时复用旧代。节流水位与进行中 Future 均按 handle 隔离，同 handle 检查单飞；两次检查开始间隔至少10分钟，新 handle 的第一次不被旧档案水位跳过，失败不伪造已清理状态。
- 检查链：await keys.ensure() → 仍同代才 await ports.files.freeBytes() → 仍同代且 <500 MiB 时取调用边界一次 UTC 毫秒 now_ms，await session.core.submit('recog.gc', {'now_ms': now_ms}) 的任务完成 → 仍同代才置 StorageStatus=true。恰为500 MiB不触发GC；恢复到≥600 MiB置false，500≤空闲<600 MiB维持原状态。ensure 返回 true 表示因平台密钥失效/库与密钥不匹配已完成 clear=true 轮换并清空历史，false 表示无需该恢复清空；两者均为正常返回，继续检查（不是软件密钥后端警告，也不是解锁失败）；抛错则不继续GC。不改 CORE-32 GC/Pin/保留算法。
- 每个文件/密钥/FFI await 后与后续调用/状态发布前复核身份+handle；changes(null) 同步拒绝新检查并置状态false，旧 A 迟到结果不向 B 发 GC 或改变 B 状态。none 作用域 freeBytes 结果也受代际栅栏约束。
- beforeClose 的同步前缀先禁止该 handle 新检查/重试并发出任务取消，再等待 ensure、freeBytes、在途 GC/必要暂存资源清理全部落定，最后释放该 handle 的 Future/水位/回调引用。其他 beforeClose 停止前缀都先由宿主调用再统一 await，不等待尚未发出的取消。已提交 GC 不声称回滚，必须等事务完成；排空失败上抛，CORE-65 保持 closing/null、不释放旧句柄、不打开新档案，显式重试仅补未完成清理。仅清理本守护持有的暂存副本，不删除持久历史图片或其他消费者的文件。
- UI契约：StorageStatus=true 时识别页显示“存储空间不足，已清理识别缓存；可在设置中减少保留的识别记录”，提供 /settings/history 跳转；false/null 隐藏。UI不执行检查或修改水位，消费者只读订阅。本卡无 Widget、无 UI/流程反向依赖。
- 错误仅复用 CORE-04 平台错误及 CORE-32 历史/密钥/GC错误，取消沿 CORE-03 既有通道；无新增业务码、schema或op。失败不得把“已清理”状态置true，日志遵循 CORE-02 脱敏。

**验收标准**：测试方案全文见 [Test/core/S5_CORE-101_TEST.md](../Test/core/S5_CORE-101_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约140行，单阶段；app/lib/recognition/storage_guard.dart 中状态5、检查/阈值/now_ms/单飞水位/GC70、生命周期/代际栅栏/关闭排空40，app/lib/recognition/install_storage_guard.dart及本卡聚合接入25。完整迁自CORE-50的110行加生命周期30；CORE-50剩710，总计850。密钥与GC核心、平台端口、UI、测试/夹具/生成物均不计本卡。可用Fake端口/会话源/核心独立构建并验证，不依赖CORE-50或识别流程实现。

**拆卡就绪门禁**：本卡由CORE-50拆出；尚未独立整卡复核，未达到编码就绪，不继承母卡等级或consumerConfirmation。需求R33、图/阶段/索引、installer/profile55唯一owner及附录D由聚合维护者同步；同步与非作者复核完成前不能注册产品实现或声称验收通过。
