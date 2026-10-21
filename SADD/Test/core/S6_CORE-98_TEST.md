# CORE-98 测试方案

> 来源卡：[S6_CORE-98_扩展.md](../../core/S6_CORE-98_扩展.md)（账户密钥网络生命周期）。本文件是该卡“验收标准”字段的全文；修改卡片功能时同步修改本文件。工具按卡片中的引用把本文件自“**验收标准**”行起拼回卡片。

**验收标准**

- [R25][R28] 构造 DefaultKeyService(sessions: sessions, api: api)，安装登记 keys.lifecycle beforeClose，不依赖 CORE-46。null/锁定不发网络/档案 op；对 A→closing/null→B（含同 profileId 不同 handle）逐步设 GET/import、wrap/PUT、DELETE/rotate/upload/reencrypt/prepare_push/POST/ack/min-version await 屏障，所有后续调用仍只可能属于捕获的 A，不向 B 写密钥/包装/批次或提升最小版本。
- [R25][R28] 同 handle 重复点击单飞、密钥变更串行；关闭的同步前缀先取消并禁止新步骤，等待在途本地事务实际结束后才 close A。已提交轮换保留可重入状态，未推完重加密绝不发 min-version；已发 min-version 响应丢失后只按原档案幂等恢复，不能向 B 重发。
- [R25][R28] 注入 HTTP取消/FFI排空失败：所有关闭停止前缀仍启动，宿主保持 closing/null，A 未释放/B未打开，显式重试只补未完清理。输入、unwrap、FFI编码的可变秘密字节副本在成功/失败/取消/过代均为零；不可变恢复码/口令不再引用，迟到恢复码不显示于 B，无敏感日志。
- [R28] 设备吊销：`rotateAfterRevoke` 后服务端 `min_key_version` 上升，旧版本密文推送被拒，另一设备用新恢复码恢复后可继续同步（该设备恢复前持有的旧版本未结算批次在下一次 `sync.prepare_push` 被作废重建，推送不再被拒）。
- [R28] 新设备GET包装→import，设置同步密语wrap→PUT；服务端只有包装与密文，恢复码/口令/密钥不进日志或崩溃报告。
- [R28] 轮换任一步网络失败不提前提升min_key_version；重加密批次推完才POST最小版本，响应丢失可重入；受限轮换排空不import或调用CORE-46协调器，本卡可先独立构建。
