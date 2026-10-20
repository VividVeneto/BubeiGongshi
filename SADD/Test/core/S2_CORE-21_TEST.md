# CORE-21 测试方案

> 来源卡：[S2_CORE-21_账户.md](../../core/S2_CORE-21_账户.md)（密钥体系与加密原语）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R28] 测试向量：KV-01～KV-07 全部通过（KV-01 直接以标准示例的固定 nonce 调用 `seal`，逐字节匹配）；篡改密文、AAD 或 nonce 任一字节均返回 `CRYPTO_DECRYPT_FAILED`。
- [R28] 随机端口：`FixedRandom` 给定字节时 `random_key`、`new_recovery_code`、`wrap` 结果确定；rng 返回错误或字节耗尽时四个函数（含 `seal_with_rng`）均返回 `CRYPTO_RNG_FAILED`，不 panic；`cargo tree -p fml-crypto` 不含 `getrandom`（可由依赖图检查脚本断言）。
- [R28] 恢复码：生成 10 万个均为 27 字符且校验通过；对每个样本做全部单字符替换与相邻交换，均被校验字符发现（返回 `CRYPTO_RECOVERY_CODE_FORMAT`）。
- [R28] T-UNLOCK（S7 真机 benchmark / 手动 checklist，由两平台性能卡收集设备、构建、原始30次样本与统计；不计本卡自动化完成条件）：同步密语解锁（默认 `KdfParams`）在 CORE-01 登记的 Android 基准设备上 P95 ≤ 2 s，内存峰值 ≤ 128 MiB（本卡安全约束，不属于 CORE-01 预算表的性能指标）；测量方法：release 构建 30 次。
- [R19] 静态检查：工作区内除本 crate 外无代码直接依赖密码学库（`cargo deny` 规则或依赖图检查）。
- [R27] 日志与崩溃报告扫描测试：注入已知密钥字节后，日志、复现包中零命中。

- [R28] WR-01/02 字节往返；WR-NEG-01、乱序键/非最短/重复键/错误 salt 长度均拒绝；改变 kind/version 后 unwrap 标签校验失败。
