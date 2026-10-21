# CORE-85 测试方案

> 来源卡：[S5_CORE-85_扩展.md](../../core/S5_CORE-85_扩展.md)（识别会话状态机与历史 GC）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R33] GC 用例：`keep_last` = 0、1、5、100 时连续完成 N + 3 次识别，保留集合等于序号最大的 N 个普通会话 + 全部 Pinned/Adopted 会话。
- [R34] 设置 −1 与 101 被界面、FFI 与 `recognition_counter` 的 CHECK 约束三处拒绝（`keep_last` 0–100，`history_disk_cap_mb` 50–2000，越界值直接 SQL 写入亦失败）；0 与 100 可设置。
- [R35] 新建账户的默认 `keep_last` 为 5。
- [R36] 保留的会话可查看确认图、上传图、候选与校正结果；被清理的会话所有文件与密钥均不存在（磁盘扫描与数据库检查）。
- [R36] Purged 数据库检查（真实 SQLite 事务）：阶段一后该会话 `state = Deleting` 且 `session_key_wrap`、`result_sealed`、`quality_json` 为 NULL、`pending_cloud_job` 无该行；阶段二后 `state = Purged`、`purged_ms = now_ms`、`recognition_asset` 无该行、元数据保留；`now_ms` 推进到 `purged_ms + 7 天 − 1 ms` 时行仍在、`+ 0 ms` 时被删，删后新建会话的 `seq` 仍大于被删行的 `seq`；非 `Deleting/Purged` 行写入 NULL 包装被 CHECK 拒绝；`rotate_commit(clear = true)` 后全部既有会话同样如此。
- [R36] 故障注入：阶段一提交前、后及阶段二每步之间杀进程，重启后会话要么完整保留要么按阶段继续，无“有包装无密文/有密文无包装”的中间态可读。
- [R33] 故障注入：GC 各步骤之间杀进程、文件被占用、磁盘满，重启后最终一致且无孤儿文件；调小 N 与识别完成并发时结果正确。
- [R40] 已提交云端的会话在进程重启后保持 RUNNING/UNKNOWN_REMOTE，经状态查询收敛，不重新提交（与 CORE-34 联测）。
- [R27] 一键清空后历史目录为空、历史密钥已轮换、WAL 中无残留记录。

- [R27][R35] 明文 SQL 扫描无 32 字节历史密钥（只有平台包装值与 `key_check`）；锁定时无法读历史，解锁后 `ensure()` 装入即可读，未装入时 `recog.history.list` 返回 `RECOG_HISTORY_KEY_UNAVAILABLE`；将 A 会话包装换给 B 时 AAD 失败；Fake `SecureKeyValueStore` 注入别名失效时 `ensure()` 返回 true 且旧会话全部进入 `Deleting`；轮换在 `wrap` 后、`rotate_commit` 前与提交后各杀一次进程，重启后遵从已提交版本且旧会话不可恢复。