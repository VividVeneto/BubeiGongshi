# CORE-34 测试方案

> 来源卡：[S5_CORE-34_扩展.md](../../core/S5_CORE-34_扩展.md)（云识别客户端与授权回执）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**

- [R25][R26][R40] installCloud 将同一 DefaultCloudRecognitionService 登记为 CloudRecognitionService/ConsentVerifier，只有既有 CORE-28 NetworkGuard；ProfileHooks order60 每新 handle 先 fetchPolicy 再 resumePending 一次，游客/null 无查询/登记，普通进程/首帧钩子不重跑。null 时 resumePending=0，其余业务入口 StateError 且无 HTTP/FFI。
- [R25][R40] Fake 屏障逐个覆盖 policy/consent、session.get、fit_for_upload、哈希、submit POST、pending.record、watch GET 与后处理 await。A→closing/null 同步废止令牌，verify=false；重开相同 profileId 新 handle 时旧 preview/token/job 缓存仍无效，A 迟到 job 不写 B pending/后处理/政策/状态。未知提交结果只保留 A pending 以后 GET，不自动再 POST。
- [R25][R40] 令 submit 响应迟到并产生旧 job：stopAndDrain 的同步前缀先停轮询/发取消，再等待旧请求并走旧注册上下文 cloudControl 清理；旧 access token 只用于取消，不 refresh、不新上传。先启动所有 beforeClose 再等待，早注册的 ProfileHooks/RecognitionFlow 等待旧云任务不死锁。清理失败保持 closing/null、A 原生句柄有效、B 未 open；重试不重复已完成清理、不重复付费。
- [R25][R31] 关闭后 resumed 不复活 A watch，B 仅恢复 B pending；暂存图只删当前服务持有副本。所有可变敏感字节副本在成功/异常/取消/过代 finally 清零，令牌表及不可变字符串引用释放；日志不含 token/图片/秘密。
- [R40] 端到端（Fake 服务端）：注册用户首次使用出现功能级同意；每次识别出现预览确认；确认后提交 → 查询 → 候选进入后处理（CORE-31）→ 校正 → 保存；会话状态依次为 Preview、Authorized、Running、Succeeded。
- [R26] 游客在任何入口都看不到云识别；直接调用 `fetchPolicy` 或 `submit` 抛 `RECOG_BACKEND_NOT_ALLOWED` 且 Fake 传输层无请求；`recog.backends` 对游客不含远程后端。
- [R40] 重复点击“上传识别”、提交后杀进程再启动、取消后重启、令牌过期、配额不足（429）均不产生第二个 job（Fake 服务端按幂等键计数为 1）；费用状态可解释（显示 `billed`）。
- [R31] 上传的字节与预览图哈希一致，且无元数据；预览后改裁剪再提交得到 `CLOUD_PREVIEW_STALE`。
- [R40] `verify`：同一令牌第二次校验为 false；哈希不符为 false；过期为 false。
- [R40] `policy_version` 变化后需重新同意；声明未满 14 周岁且未经监护人确认时不发起同意请求，云识别入口禁用。
- [R40] `FakeAppLifecycle` 发出 `paused` 后 5 分钟（假时钟）内 `FakeHttpTransport` 无 `GET /v1/recognition/jobs/{id}` 请求；发出 `resumed` 后立即查询一次；全程只有一次 `POST /v1/recognition/jobs`。

- [R26][R40] Fake：上传POST返回401→刷新成功→旧token第二次verify=false且无自动POST；用户再次确认得到不同tokenId，第二次POST的Idempotency-Key与首次相同、token不同，服务端job/供应商计费各1。超时、重启、拒绝确认、改图分别断言无自动上传/空令牌表/无请求/新幂等键。

- [R40][R19] cloud-idempotency-v1三个固定输入产生对应UUID；同session/hash在401重新确认、进程重启后逐字相同，改变session或hash产生不同键；不使用随机namespace。
