# CORE-102 测试方案

> 来源卡：[S2_CORE-102_功能.md](../../core/S2_CORE-102_功能.md)（同步读取入口与写门）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R28] `read_entity` 返回规范化 body 与同一事务的字段时钟：已登记的存活实体读出的 `entity`/`clocks` 与该实体最新一条 outbox 明文 `{"entity":…,"clocks":…}` 逐字节等值；未登记类型 → `STORE_CORRUPT`；存活实体无任何 `field_clock` 行 → `STORE_CORRUPT`（不补写时钟、不新建注册项）；实体已删除（codec 回读为 None）→ `Ok(None)`，删除信息只能从 `list_tombstones` 取得。在 `Store.write` 事务内与 `Store.read` 事务内调用结果一致。
- [R28] `read_field_clocks` 返回该实体全部字段时钟，字段名到 `FieldClock{counter, device_id}` 一一映射，含 `__entity`/`__deleted`；无行返回空映射而非错误；调用后库无任何写入（前后 `PRAGMA data_version`/`total_changes` 不变）。
- [R28] `list_tombstones`：只返回 `deleted_at_ms >= now_ms - TOMBSTONE_TTL_MS` 的行，边界值相等时包含、少 1 ms 时排除；结果按 `(entity_type, entity_id)` UTF-8 升序稳定；每行附该实体全部字段时钟（含 `__deleted`）；`now_ms <= 0` → `FFI_BAD_ARG`；调用不删除、不改写任何墓碑（清理仍归 CORE-13 `purge_tombstones`）。
- [R28] `read_sync_cursor`：`sync_cursor` 无行 → `Ok(None)`；有行时 `cursor`/`epoch`/`updated_at_ms` 与行值逐个相等；读快照隔离：同一读事务内另一写者提交新游标后，本事务重复读取仍返回进入事务时的值。
- [R28] `set_sync_cursor` 单调与副作用：无行首次写入 `written=true`；同 epoch 且 `order` 判 `Less` 时写新值与 `updated_at_ms=now_ms`；`Equal`/`Greater` 时 `written=false`、行与 `updated_at_ms` 均不变；行 `epoch` 与 `next.epoch` 不同 → `STORE_CORRUPT` 且行不变；每次调用后 `sync_outbox`、`local_clock`（lamport/device_seq）、`field_clock` 与 `local_setting.stats_generation` 全部不变。
- [R28] `set_sync_cursor` 失败路径：`CursorOrder::compare` 返回 `Err` 时原样上抛（错误码、diagnostics 不被本卡改写），行不变；同一事务内先写游标再注入后续失败 → 提交与回滚各跑一遍，回滚后游标为旧值、行数不变，事务内不出现部分写入。
- [R28] `clear_sync_cursor`：有该 `stream` 行时返回 `true` 并删除，无行返回 `false`；只影响 `sync_cursor` 一行，`sync_outbox`/`tombstone`/`field_clock` 不变；同事务回滚后行仍在。
- [R28] 写门：`pause_writes` 后 `write_gated` 在进入写队列前返回登记模板的克隆（错误码与 diagnostics 与登记值相同），不排队、不产生 `STORE_BUSY`、不消耗 5 s 超时，命令闭包体一次也不执行；门打开时 `write_gated` 与 `Store::write` 对同一条命令的结果与回滚语义相同；`resume` 后恢复；未 `resume` 的 `WriteGate` 被 Drop 亦恢复；两次嵌套暂停只有最外层释放后 `write_gate()` 才回到 `Open`；已暂停时以另一错误码再 `pause_writes` → `STORE_CORRUPT` 且原登记不变。
- [R27] 门的作用面：暂停期间 `Store.read`、`read_entity`/`read_field_clocks`/`list_tombstones`/`read_sync_cursor`、`integrity_check` 与 `close` 全部照常工作；`Store::write` 在暂停期间仍可执行（供 CORE-13/CORE-24 的基础设施与升级步骤）；门状态全在进程内，重开 `Store` 后为 `Open`。
- [R18] 单一来源与静态约束：本卡不新增迁移文件、`SCHEMA_VERSION` 不变，`field_clock`/`sync_cursor`/`tombstone` 的 `CREATE TABLE` 仍只出现在 `crates/fml-store/migrations/0013_core.sql`；消费方源码中不出现直接读写这三张表的 SQL 文本（对 `crates/fml-store/src/sync/`、`crates/fml-ffi/src/ops/` 做 grep 断言，只允许本卡模块与 CORE-13 的表策略/写入路径命中）；`Cargo.toml` 不新增依赖。
- [R19] 坏行定位与脱敏：`sync_cursor.cursor` 非文本或 `epoch` 超出 `u32`、`field_clock.counter` 越界、`tombstone.deleted_at_ms` 非整数时返回 `STORE_CORRUPT`，原行保留（不修复、不删除），错误中只含表名与定位信息，不回显行内容或游标原文。
