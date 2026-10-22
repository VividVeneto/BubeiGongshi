# CORE-98 测试方案

> 来源卡：[S6_CORE-98_扩展.md](../../core/S6_CORE-98_扩展.md)（账户密钥网络生命周期）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**

- [R28] 三端点形状：`fetchRecords` 对 `200 {min_key_version, records:[{key_version, wrap_kind, record_base64, created_at}]}` 逐字段映射（`min_key_version ≥ 1`、`wrap_kind` 只认 `recovery_code|sync_passphrase`、其他值抛 FormatException、`created_at` 原样保留）；`uploadWrapRecord` 发 `PUT /v1/keys/{key_version}/{wrap_kind}` 且请求体只有 `record_base64`；`raiseMinKeyVersion` 发 `POST /v1/keys/min-version` 且体为 `{"min_key_version":n}`；用假 transport 断言除此之外没有任何 keys 请求，KeysApi 不对外导出。
- [R28] 错误边界原样透传：`413 SYNC_PAYLOAD_TOO_LARGE`、`409 SYNC_KEY_VERSION_REJECTED`、`404 SYNC_NOT_FOUND`、`AUTH_TOKEN_EXPIRED`（首次401刷新后重试一次，仍失败抛 `AUTH_REAUTH_REQUIRED`）、`CRYPTO_PASSPHRASE_WEAK`、`SYNC_UPGRADE_KEY_FAILED`、`SYNC_KEY_MISSING` 与 `NET_*` 均以原错误码上抛，不被吞咽或改写为成功/自定义码；本卡不新增错误码。
- [R28] min-version 正常与失败：服务端现值更大时 `204` 视为成功且不发第二次请求（幂等）；请求值小于现值时 `409 SYNC_KEY_VERSION_REJECTED` 上抛；提升失败不重试、不删除本地旧版本包装行，界面提示“已有更新版本”。
- [R28] 会话屏障：对 A→closing/null→B（含同 profileId 不同 handle）在 `GET/import`、`wrap/PUT`、`DELETE/rotate/upload/reencrypt`、`raiseMinKeyVersion` 前后逐步设 await 屏障；所有后续调用仍只可能属于捕获的 A，不向 B 导入密钥、上传包装或提升最小版本，A 的恢复码不出现在 B。
- [R28] HTTP 取消与排空：`stopAndDrain` 先禁止新步骤并取消在途请求，链条中断后不再发后续 PUT/reencrypt；已发出的 `raiseMinKeyVersion` 结果未知时只按原档案幂等恢复，不向 B 重发；注入排空失败时宿主保持 closing/null，不释放 A、不打开 B，重试只补未完清理。
- [R28] 恢复与口令路径：`restoreOnNewDevice` 的 `records` 与服务端 `record_base64` 字节相同（原样转交 `account.import_account_key`），`account_id` 取自 `account.profiles` 中本会话对应档案；`setSyncPassphrase` 走 `account.wrap_with_passphrase` → `PUT sync_passphrase`，不写 `account_key_wrap`、不缓存口令，`CRYPTO_PASSPHRASE_WEAK` 透传到输入框。
- [R28] 设备吊销轮换：`DELETE /v1/devices/{id}` → `account.rotate_account_key` → `PUT` 新版本 `recovery_code` → `sync.reencrypt` → 返回新恢复码；断言全程零次 push 与零次 min-version，新版本只有 `recovery_code` 包装（无 `sync_passphrase`）；中断重入：DELETE 已 204 时先 `GET /v1/devices` 确认已吊销再跳过，PUT 已完成时 `fetchRecords` 命中后不重复上传。
- [R28] 秘密与安装：输入/unwrap/FFI 编码形成的可变字节副本在成功、异常、取消、过代各路径均为零；`installKeys` 在 sessions/ApiClient 缺失时抛 StateError、齐全时登记 KeyService 与 `keys.lifecycle` beforeClose；依赖图断言本卡不 import 同步实现卡（CORE-46，下游说明，非契约）；同 handle 重复调用单飞。
