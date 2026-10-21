# CORE-32 测试方案

> 来源卡：[S5_CORE-32_扩展.md](../../core/S5_CORE-32_扩展.md)。

**验收标准**
- [R24][R27][R33] ensure在status/unwrap/provide、轮换在begin/wrap/commit的每个await后分别切换A→null→B（含同profile不同handle）：B的provide/commit计数零、A明文Uint8List及副本全部清零、不因世代过期对B执行clear轮换。null开始时端口/FFI调用零次。
- [R27][R33] 并发ensure同handle仅一次status/unwrap/provide；ensure→clearAll→ensure用同一队列有确定顺序，最多一次rotate_begin在途。beforeClose先阻止排队新任务再await在途，未提交不启动下一步commit，已提交只等结果；drain失败阻止native close。
- [R27] 注入unwrap/wrap/provide/commit各异常均finally清零；非密钥失效类异常不clear历史；RECOG_HISTORY_KEY_UNAVAILABLE只对同仍current世代ensure后重试原业务一次。不可变String不作为可清零证据；Rust纯模型不因Dart依赖CORE-65而依赖fml-store/平台。

- [R33][R40] 状态合法表：对 11×11 全部 (from, to) 组合调用 validate_transition，恰好表中各边通过、其余 RECOG_TRANSITION_INVALID；networked=false时不能Authorized；Fake HistoryRepo 契约测试中 transition 目标为 Deleting/Purged 一律拒绝、payload.networked 为 None 时 Preview→Authorized 被拒。未知远端保留只查询，不重新提交的状态语义。
- [R27][R35] Fake CoreBinding/平台密钥验证HistoryKeyUnlocker：loaded直接false，version0轮换clear=false；失效/不匹配轮换clear=true返回true；ensure前后ProfileSession变化丢弃/清零，重试最多一次。
- [R27] 解锁器wrap后/commit前失败不改已提交版本；锁定后不提供旧密钥；真实SQL/WAL/GC/崩溃恢复集成验收迁CORE-85。
- [R36] 结果编解码：含 ast=None、validation=None、多诊断、多 symbol_spans、score 为 0.0 与 1.0 的 SessionResult 经 encode_result→decode_result 相等；输出为无空白 UTF-8 JSON 且键序固定（与夹具逐字节相同）；format_version=2、截断、非 JSON 输入报 RECOG_IMAGE_LOST。
- [R36] AAD 表：四类对象（keycheck、session、asset 各 kind、result）的 aad_cbor 字节与夹具逐字节相同；同一会话不同 AssetKind、不同会话同一 kind 的 AAD 互不相同。
