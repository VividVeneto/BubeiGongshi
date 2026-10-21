### CORE-83 游客并入已有账户

**目标**：在保留游客源库的前提下，将其数据按可重入映射导入本机已有账户档案。

**范围**
- 包含：跨库稳定遍历、派生ID去重、随机ID重映射/引用修复、可能重复报告、目标cursor与account.upgrade_merge处理。
- 不包含：升级日志/账户密钥/注册表投影（CORE-24）；网络协调（CORE-99，下游说明）；普通同步合并（CORE-26，下游说明）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-05、CORE-13、CORE-14、CORE-17、CORE-24

**接口契约**

```rust
// crates/fml-store/src/sync/merge_guest.rs
pub fn merge_guest(source: &Store /* 游客档案，只开读事务 */, target: &Store /* 本机已有的目标账户档案，经其单写者写入 */,
                   j: &mut UpgradeJournal) -> Result<MergeReport, FmlError>;
    // MergeInto 且本机已有目标档案时，Commit 步骤由本函数完成（代替 advance(Commit)）；可重入，进度记在目标库 journal
pub struct MergeReport { pub imported: u32, pub already_present: u32, pub possible_duplicates: Vec<Uuid> /* 规范 AST 哈希相同的用户自建条目 */ }
// 预置条目/模板去重的 ID 只调用 CORE-05 pack_item_id / pack_template_id，不在本卡定义命名空间。
```

- 并入已有账户（MergeInto）：本机已有该账户档案时，游客库数据以新的不可变修订与事件写入该账户档案库（经 `enqueue_outbox`），游客档案在 Done 后保留，由用户确认后删除；本机无该账户档案时游客档案直接转为该账户档案，远端数据由首次同步拉取后按 CORE-26 规则合并。去重规则：预置内容派生的条目与卡片用 CORE-05 的 pack_item_id/card_id，两端相同即同一对象；复习事件按 `event_id` 去重；用户自建公式按规范 AST 哈希（CORE-05）相同时生成“可能重复”提示，不自动合并；随机 ID 冲突时为游客侧对象重新生成 ID 并更新所有引用。

| op | 请求 | 响应 | 说明 |
| --- | --- | --- | --- |
| `account.upgrade_merge` | `{ target_profile_id, target_db_key }` | `{ report }` | submit；来源为信封profile_handle指向的游客库，本操作以target_profile_id校验并临时打开目标库；不替换交互会话；完成/失败/取消后关闭目标并清零target_db_key |

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `SYNC_MERGE_CONFLICT` | warning | 否 | 随机 ID 冲突且重映射后仍冲突（理论上不应发生，记录并中止该步） |

MergeInto 使用两个 Store 时不得声称跨库事务：`merge_guest` 把来源 profile_id、目标 profile_id、cursor、导入映射记到目标 journal；目标库按稳定源对象ID幂等导入并生成 outbox，全部成功后写 LocalCommitted；源库不改不删。失败重进重复的对象不再生成事件，未 Done 不展示部分目标结果。暂时打开第二个库只用于本操作，锁按 profile_id 字节序获取；目标密钥由协调器先经平台解包后注入，不跨库读明文密钥。

**实现约束**
- 源Store只读；目标单写者使用CORE-13 WriteTx/enqueue_outbox并显式changed_fields；枚举/重试使用CORE-13 list_entity_ids与requeue_outbox，不伪造字段时钟。目标升级cursor/映射使用CORE-24 journal接缝，完成后其投影恢复规则不变。
- account.upgrade_merge为profile scope，来源为信封游客handle；target_db_key与所有Secret均x-sensitive，临时打开目标仅用于本操作，完成/错误/取消关闭清零，不更换交互ProfileSession。
- 不宣称跨库事务，不删游客数据；Done后由用户确认删除，重进不重复创建事件。预置ID使用CORE-05，不定义新命名空间。
- 无网络，不上传DbKey/历史密钥或识别历史/cache；保持CORE-24升级写暂停与LocalCommitted后不回退规则。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-83_TEST.md](../Test/core/S6_CORE-83_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：约265行；主包`crates/fml-store/src/sync/merge_guest.rs`，附属`crates/fml-ffi/src/ops/upgrade.rs`中account.upgrade_merge处理与登记；DDL/自测不计。
