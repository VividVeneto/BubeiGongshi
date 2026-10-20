# CORE-34 测试方案

> 来源卡：[S5_CORE-34_扩展.md](../../core/S5_CORE-34_扩展.md)（云识别客户端与授权回执）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R40] 端到端（Fake 服务端）：注册用户首次使用出现功能级同意；每次识别出现预览确认；确认后提交 → 查询 → 候选进入后处理（CORE-31）→ 校正 → 保存；会话状态依次为 Preview、Authorized、Running、Succeeded。
- [R26] 游客在任何入口都看不到云识别；直接调用 `fetchPolicy` 或 `submit` 抛 `RECOG_BACKEND_NOT_ALLOWED` 且 Fake 传输层无请求；`recog.backends` 对游客不含远程后端。
- [R40] 重复点击“上传识别”、提交后杀进程再启动、取消后重启、令牌过期、配额不足（429）均不产生第二个 job（Fake 服务端按幂等键计数为 1）；费用状态可解释（显示 `billed`）。
- [R31] 上传的字节与预览图哈希一致，且无元数据；预览后改裁剪再提交得到 `CLOUD_PREVIEW_STALE`。
- [R40] `verify`：同一令牌第二次校验为 false；哈希不符为 false；过期为 false。
- [R40] `policy_version` 变化后需重新同意；声明未满 14 周岁且未经监护人确认时不发起同意请求，云识别入口禁用。
- [R40] `FakeAppLifecycle` 发出 `paused` 后 5 分钟（假时钟）内 `FakeHttpTransport` 无 `GET /v1/recognition/jobs/{id}` 请求；发出 `resumed` 后立即查询一次；全程只有一次 `POST /v1/recognition/jobs`。

- [R26][R40] Fake：上传POST返回401→刷新成功→旧token第二次verify=false且无自动POST；用户再次确认得到不同tokenId，第二次POST的Idempotency-Key与首次相同、token不同，服务端job/供应商计费各1。超时、重启、拒绝确认、改图分别断言无自动上传/空令牌表/无请求/新幂等键。

- [R40][R19] cloud-idempotency-v1三个固定输入产生对应UUID；同session/hash在401重新确认、进程重启后逐字相同，改变session或hash产生不同键；不使用随机namespace。
