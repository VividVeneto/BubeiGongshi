### CORE-96 在线资源包信任元数据适配

**目标**：以成熟TUF客户端验证在线更新元数据，维持时效与单调安全状态；当前外部适配前提未闭合。

**范围**
- 包含：root/targets/snapshot/timestamp适配、到期/时间/datastore/逐版root轮换核实；verify_update_metadata与pack.check_updates完整调用点/处理/登记；验证后经95持久化SecurityState。
- 不包含：自研TUF；HTTP下载（平台卡/CORE-43/51）；离线包安全内核（CORE-15）；设备安装/高水位持久化内核（CORE-95）。

**依赖**：CORE-01、CORE-02、CORE-03、CORE-15、CORE-95

**接口契约**

```rust
// crates/fml-pack/src/update.rs；共享类型由CORE-15定义
pub fn verify_update_metadata(meta: &UpdateMetadata, root: &TrustRoot, now_ms: i64, last_seen: &SecurityState) -> Result<Vec<PackOffer>, FmlError>;
```

- 在线更新元数据：服务端发布带 root/targets/snapshot/timestamp 角色的 TUF 风格元数据，timestamp 有效期 ≤ 7 天；使用成熟 TUF 客户端实现，不自研协议；过期或时钟异常时暂停在线更新，已安装内容照常可用。
- FFI op：pack.check_updates（call，请求UpdateMetadata四角色base64，由平台下载；响应[PackOffer]）。本卡唯一拥有调用点、DTO处理与登记；验证后通过CORE-95设备meta接口持久化新SecurityState，再返回Offer，不能先发布结果后写水位。
- PACK_METADATA_EXPIRED、PACK_EPOCH_ROLLBACK及PACK_*签名/兼容错误唯一定义在CORE-15，本卡只引用；timestamp过期或本机时间早于last_seen_ms超过24h为PACK_METADATA_EXPIRED，元数据版本回退为PACK_EPOCH_ROLLBACK。错误时已安装内容照常可用。

TUF 适配核实状态（A-32）：当前 `verify_update_metadata(now_ms)` 与 tough 内部时钟/datastore 的可替换性没有完成验证；此函数不能作为已闭合 sans-I/O 签名编码。M0须锁定tough版本并用官方源码验证load/expiration/datastore/逐版root轮换，提交可运行适配fixture后修订签名；在此之前CORE-96在线更新部分为外部前提阻断，不得关过期检查或自研TUF绕过。离线包验签不受此未决项阻止。

**实现约束**
- 原now_ms签名仅记录待核实边界，不代表tough已支持sans-I/O；M0锁版、官方源码证据、可运行适配fixture及必要契约修订全部通过后才进入编码/验收。fixture是验证成本，不计实现规模。禁止关过期检查或自研协议绕过。
- TUF可信root轮换/过期/版本号不回退是完整职责，不以只有四角色JSON验签代替TUF；CORE-95只提供设备高水位持久化，不反向调用本卡。
- tough版本按ADR-V5-15锁Cargo.lock；签名公钥来源CORE-16/43，敏感私钥不进入客户端。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-96_TEST.md](../Test/core/S4_CORE-96_TEST.md)；修改本卡功能时同步修改该文件。

**规模**：条件估算约120行；主包 `crates/fml-pack/src/update.rs` 100行，附属 `crates/fml-ffi/src/ops/pack.rs` 的pack.check_updates调用/处理/登记20行（从95转归，总1090守恒）。外部前提闭合后单阶段独立构建测试；闭合前不得报告已实现/已验收；元数据/fixture/生成物/自测不计。
