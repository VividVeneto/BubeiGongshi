# CORE-14 测试方案

> 来源卡：[S3_CORE-14_功能.md](../../core/S3_CORE-14_功能.md)（公式条目、修订与单位仓储）。本文件是该卡验收标准全文；修改范围时同步修改，工具从下方验收标准行起拼回。

**验收标准**
- [R11] 修订：编辑预置条目生成用户修订；历史列表正确；恢复旧版生成新修订而历史不变。
- [R14] 修改符号量纲声明后，依赖它的派生修订被标记待重校，旧修订保留。
- [R16] 母修订删除后，派生修订转为独立修订并带提示。
- [R04] 回收站条目 30 天后被 `purge_expired` 物理删除并写入 tombstone；30 天内可恢复（以注入时钟测 29 天 23 小时可恢复、30 天后删除）。
- [R11] 元数据：update_meta不生成修订；标签[" 期末 ","期末"]规范化为["期末"]，21个标签报LIB_TAGS_LIMIT，非法事务不改变条目。
- [R15] 自定义单位写入后关闭重开账户，list_user与convert结果不变；切换账户不串单位；失败事务不改变注册表，提交后刷新失败不使用旧注册表计算。
- [R11] 投影：PackCatalog Fake 返回 2 个条目，投影后 item 带 requirement_level 与 pack_extras_json，缓存修订 ID 等于 `pack_cache_revision_id` 向量；只改其中一个条目内容时，另一条目的缓存修订 ID 不变。
- [R11][R15] 分阶段：先构建条目/修订/恢复与回收站；再启用单位/待重校/投影与codec/applier，两阶段各自测试，无对CORE-79或fml-ffi的反向依赖。
- [R28] 五类codec/applier用CORE13 Fake上下文测试稳定枚举、预置排除、Delete/旧Upsert防复活、Duplicate零写和Invalid/存储Err区分；不反向调用CORE26。远端标题/标签字段分别合并，tags数组单字段时钟收敛，FTS/派生索引与业务同事务，无回声outbox。
- [R11][R14] FakeAnalyzer收到source、symbols.decls、profile、conditions、empirical=false与同事务只读conn/cancel；上传AST/Validation不作为缓存事实，输出ast=None隔离，有AST的Invalid草稿保留；重建ast_hash/symbol_binding/derived索引，重放同ID不因引擎缓存差异拒绝。
- [R15] 用户单位全集允许前向引用；重定义/删除造成引用断裂、环、非法offset及溢出时DB/clock/outbox不变，成功后释放临时base借用再发布User层；发布失败拒绝引擎，mark_unavailable失败不吞。
