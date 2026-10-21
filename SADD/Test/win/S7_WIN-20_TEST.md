# WIN-20 测试方案

> 来源卡：[S7_WIN-20_发布.md](../../win/S7_WIN-20_发布.md)。

**验收标准**
- [R23] journal、manifest、healthy/opened、update-failed与原黄金文件逐字节一致；截断、缺键、未知键、schema=2、非法SemVer/nonce/范围一律失败且不改文件。
- [R23][R27] 故障文件系统逐提交点注入写/flush/rename/回读中断；备份验证前不删旧快照，SHA/大小不符不提升为有效备份；路径逃逸、重解析点不接触外部目标。
- [R27] none→moved-failed→restored各步骤任一文件操作中断后重启续做，完整恢复hash与快照一致，不出现混合库；failed-N保留规则不变。
- [R23][R27] rename共享冲突按5次/200ms重试，耗尽保留journal/C/备份/失败库；在无匹配opened且未恢复核验前拒绝删除唯一备份；清理失败下次可重试。
- [R23][R27] read_journal缺失返回nullopt、损坏抛StorageFailure且不改文件；控制read/write/remove验证严格格式与白名单、缺失删除幂等及拒删current；Fake端口覆盖WIN-16所需current/pending/healthy/opened访问。转发10且现库清单/哈希未变才撤回备份，任一变化拒删唯一快照。
