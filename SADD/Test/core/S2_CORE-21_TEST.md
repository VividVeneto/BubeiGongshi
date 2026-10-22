# CORE-21 测试方案

> 来源卡：[S2_CORE-21_账户.md](../../core/S2_CORE-21_账户.md)（密钥体系与加密原语）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R28] 测试向量：KV-01～KV-07 全部通过；KV-01以标准固定nonce调用生产seal，KV-02～04以私有上游原语跑标准可变salt/info/L KAT，KV-05以私有Argon2id原语跑标准secret/AD/小参数KAT；生产derive_subkey/recovery_key/passphrase_key分别用独立golden与严格参数界限验证，不改生产API迎合KAT；篡改密文、AAD 或 nonce 任一字节均返回 `CRYPTO_DECRYPT_FAILED`。
- [R28] 随机端口：`FixedRandom` 给定字节时 `random_key`、`new_recovery_code`、`wrap` 结果确定；rng 返回错误或字节耗尽时四个函数（含 `seal_with_rng`）均返回 `CRYPTO_RNG_FAILED`，不 panic；`cargo tree -p fml-crypto --edges normal,build` 不含 `getrandom`（可由依赖图检查脚本断言）。
- [R28] 恢复码：固定熵序列生成10万个，as_str均为规范27字符且可还原原始128位熵；不把测试伪熵当生产熵证明。对每个规范码做全部非原字符替换（数据位32符号、校验位37符号）及不等相邻字符交换，私有纯校验函数均拒绝；相同字符交换是恒等变换、I/L/O等规范同义输入允许通过，不计漏检。纯校验批量测试不调用HKDF；另取固定0/全1/3个独立样本逐字节验证HKDF(原始16字节,空salt,info=fml/v1/recovery,32)及new_recovery_code/recovery_key一致。
- [R28] T-UNLOCK（S7 真机 benchmark / 手动 checklist，由两平台性能卡收集设备、构建、原始30次样本与统计；不计本卡自动化完成条件）：同步密语解锁（默认 `KdfParams`）在 CORE-01 登记的 Android 基准设备上 P95 ≤ 2 s，内存峰值 ≤ 128 MiB（本卡安全约束，不属于 CORE-01 预算表的性能指标）；测量方法：release 构建 30 次。
- [R19] 静态检查：工作区内除本 crate 外无代码直接依赖密码学库（chacha20poly1305、argon2、hkdf、sha2、getrandom）。CORE-01 的 `dep-allow.yaml` 只管本仓库包间依赖、不覆盖第三方包，故本卡在 `crates/fml-crypto/tests/dep_policy.rs` 自带检查：解析 `cargo metadata --format-version 1` 的工作区成员直接依赖（normal/build/dev 及 target 条件），除 `fml-crypto` 外出现上述任一包名即失败（`getrandom` 另允许 CORE-23 的 OsRandom 所在包）；`fml-crypto` 的正常/构建依赖闭包不含 getrandom 由同一测试对 resolve 图断言（等价 `cargo tree -p fml-crypto --edges normal,build`）。deny.toml 未交付前不以 cargo deny 代替。
- [R27] 日志与崩溃报告扫描测试：注入已知密钥字节后，日志、复现包中零命中。

- [R28] WR-01/02 字节往返；WR-NEG-01、乱序键/非最短/重复键/错误 salt 长度均拒绝；改变 kind/version 后 unwrap 标签校验失败。
- [R28][R27] SecretKey以Zeroizing32字节构造/as_bytes借用，Sealed显式编码解码（坏版本/短长度拒绝）；RecoveryCode只经as_str敏感出口取规范文本。编译失败样例证明秘密类型无Clone/Copy/Serialize/Deserialize/Display，Debug脱敏，不依赖释放后读内存的未定义行为“验证零化”。恢复码及解码熵临时缓冲使用Zeroizing，零化路径做源码/类型审计；日志扫描不输出密钥、恢复码、passphrase。
- [R28] wrap只接受非口令kind，wrap_with_params只接受口令kind；错误kind/版本0/越界参数明确拒绝；解封后非32字节统一CRYPTO_DECRYPT_FAILED。Platform值0结构往返保留，但平台DPAPI/Keystore blob不冒充WrapRecord，账户上传只允许既有恢复码/同步密语种类。CRYPTO_KDF_MEMORY不可重试且不降安全参数，`CRYPTO_KEY_VERSION_UNKNOWN` 为预留码（本 crate 不产生；现有消费方缺所需密钥时用 CORE-24 的 `SYNC_KEY_MISSING`，该码仅作未来轮换预留），纯函数不伪装查表。
- [R28] wrap-v1.json顶层版本、唯一id及WR正负例均与卡片固定字节一致，独立编码器/人工复核证据齐备；仅结构valid的全零密文不得被报告为AEAD成功。向量/常见口令表若未交付或许可未确认则阻断相应验收，不以空数据通过。
- [R28] 口令策略与派生（CO-29）：check_passphrase_policy 对 11/12 个 NFC 字符（NFD 输入按 NFC 计数）、全同字符、测试样例表中口令（大小写不同）分别返回 CRYPTO_PASSPHRASE_WEAK/通过/WEAK/WEAK；同一口令的 NFC 与 NFD 形式经 passphrase_key 得到相同密钥；KdfParams m_kib=65535、131073、t=2、t=11、p=3 各返回 CRYPTO_PARAM_INVALID，边界 65536/131072/3/10/4 接受；Argon2 分配失败（私有原语注入）映射 CRYPTO_KDF_MEMORY 且不降参数重试。
- [R28] 子密钥与 AAD：derive_subkey 对 5 个 KeyPurpose × key_version {1,2} 的 10 个输出两两不同且 info 串逐字等于卡片规则；aad_cbor 对只含 domain/key_version/format_version 的 AadFields 省略键 2/3/4；Sealed::from_bytes 对 40 字节与 version=2 输入返回 CRYPTO_DECRYPT_FAILED；WrapRecord::from_bytes 对 4097 字节输入、key_version=0 拒绝，key_version=u32::MAX 往返。
