### CORE-21 密钥体系与加密原语

**目标**：集中实现全部密钥的生成、派生、包装与 AEAD 加解密，其他模块只调用本 crate，不直接使用密码学库。

**范围**
- 包含：密钥层次与类型、随机性端口 `SecureRandom`（只定义 trait 与确定性假实现，不含 OS 实现）、AEAD、Argon2id、HKDF、恢复码编解码、包装记录格式、AAD 的确定性 CBOR 编码、零化、测试向量。
- 不包含：平台密钥的保存（经 CORE-04 `SecureKeyValueStore`，由 AND-06、WIN-07 实现）；账户状态机（CORE-23）；同步协议（CORE-26）。

**依赖**：CORE-01、CORE-02、CORE-04

**接口契约**

密钥层次：

```text
平台密钥（Android Keystore / Windows DPAPI，经 SecureKeyValueStore）
  ├─ 包装 DbKey（每个本地账户一把，CORE-13）
  ├─ 包装 RecognitionHistoryKey（每个本地账户一把）→ 包装每个识别会话的 SessionKey
  └─ 资源包为签名公开内容，不引入未定义的 ResourcePackCacheKey
AccountDataKey（仅注册账户；256 位随机数，不由口令派生）
  ├─ 由 RecoveryKey 包装（恢复码 → HKDF）
  ├─ 由 SyncPassphraseKey 包装（同步密语 → Argon2id；可选）
  └─ 派生 UserFormulaKey / StudyDataKey / UserSettingsKey / BackupKey，以及 KeyPurpose::SyncSnapshot 用途的快照密钥（HKDF，info 区分用途）
```

```rust
// crates/fml-crypto/src/lib.rs
pub struct SecretKey(Zeroizing<[u8; 32]>);
impl SecretKey {
    pub fn from_bytes(bytes: Zeroizing<[u8; 32]>) -> Self; // 接管已验证的固定长度缓冲
    pub fn as_bytes(&self) -> &[u8; 32]; // 显式借用；不得序列化/记录，复制方负责零化
}
pub enum KeyPurpose { UserFormula, StudyData, UserSettings, Backup, SyncSnapshot }
// HKDF：salt 为空，info = "fml/v1/" + 蛇形小写 purpose + "/" + key_version（十进制），输出 32 字节
pub struct Sealed { pub version: u8 /* 1 */, pub nonce: [u8; 24], pub ciphertext: Vec<u8> /* 含 16 字节标签 */ }
// 字节形式：version(1) ‖ nonce(24) ‖ ciphertext；长度 < 41 或 version != 1 → CRYPTO_DECRYPT_FAILED
impl Sealed { pub fn to_bytes(&self) -> Vec<u8>; pub fn from_bytes(bytes: &[u8]) -> Result<Self, FmlError>; }
pub enum WrapKind { Platform, RecoveryCode, SyncPassphrase, ExportPassword }
pub struct AadFields { pub domain: String /* 如 "sync.entity"、"backup.chunk" */, pub account_id: Option<Uuid>,
                       pub entity_type: Option<String>, pub entity_id: Option<String>, pub key_version: u32, pub format_version: u16 }
// CBOR：map，整数键 1..6 依次对应上述字段，缺省字段省略，键升序，最短整数编码，UUID 为 16 字节字节串
pub trait SecureRandom { fn fill(&mut self, buf: &mut [u8]) -> Result<(), FmlError>; } // 失败 → CRYPTO_RNG_FAILED；OS 实现 OsRandom 在 CORE-23，本 crate 不依赖 getrandom
pub fn random_key(rng: &mut dyn SecureRandom) -> Result<SecretKey, FmlError>;  // 32 字节
pub fn derive_subkey(root: &SecretKey, purpose: KeyPurpose, key_version: u32) -> SecretKey; // HKDF-SHA256
pub fn seal(key: &SecretKey, plaintext: &[u8], aad: &[u8], nonce: &[u8; 24]) -> Sealed; // XChaCha20-Poly1305，纯函数；同一密钥下 nonce 不得复用，由调用方保证
pub fn seal_with_rng(rng: &mut dyn SecureRandom, key: &SecretKey, plaintext: &[u8], aad: &[u8]) -> Result<Sealed, FmlError>; // 从 rng 取 24 字节 nonce 后调用 seal
pub fn open(key: &SecretKey, sealed: &Sealed, aad: &[u8]) -> Result<Zeroizing<Vec<u8>>, FmlError>;
pub struct WrapRecord { pub wrap_kind: WrapKind /* Platform|RecoveryCode|SyncPassphrase|ExportPassword */,
                        pub key_version: u32, pub kdf: Option<KdfParams>, pub salt: Option<[u8; 16]>,
                        pub sealed: Sealed, pub created_at_ms: i64 }
impl WrapRecord { pub fn to_bytes(&self) -> Vec<u8>; pub fn from_bytes(bytes: &[u8]) -> Result<Self, FmlError>; }
pub fn wrap(rng: &mut dyn SecureRandom, kek: &SecretKey, key: &SecretKey, kind: WrapKind, key_version: u32, now_ms: i64) -> Result<WrapRecord, FmlError>; // rng 只用于 nonce
pub fn unwrap(kek: &SecretKey, rec: &WrapRecord) -> Result<SecretKey, FmlError>;
pub struct RecoveryCode(Zeroizing<String>);  // 128 位随机 → 26 个 Crockford Base32 数据字符（首字符 0–7）+ 1 个 Crockford mod 37 校验字符，共 27 个；显示为 4-4-4-4-4-4-3 分组；输入时忽略空格与连字符，大小写不敏感，I/L→1、O→0
impl RecoveryCode { pub fn as_str(&self) -> &str; } // 规范27字符，无分隔符；显示分组由调用方完成
pub fn new_recovery_code(rng: &mut dyn SecureRandom) -> Result<(RecoveryCode, SecretKey), FmlError>;
pub fn recovery_key(code: &str) -> Result<SecretKey, FmlError>;          // 校验位错误 → CRYPTO_RECOVERY_CODE_FORMAT
pub struct KdfParams { pub m_kib: u32 /* ≥ 65536 */, pub t: u32 /* ≥ 3 */, pub p: u32 /* 4 */ }
pub fn passphrase_key(pass: &str, salt: &[u8; 16], params: &KdfParams) -> Result<SecretKey, FmlError>; // Argon2id
pub fn check_passphrase_policy(pass: &str) -> Result<(), FmlError>;     // ≥ 12 个 Unicode 字符（NFC 后计数）；不在内置常见口令表中；不全为同一字符
pub fn aad_cbor(fields: &AadFields) -> Vec<u8>;                          // RFC 8949 确定性 CBOR
```

- `SecretKey`/`RecoveryCode` 不实现 Serialize/Deserialize、Clone/Copy、Display；Debug 仅输出类型名与 `[REDACTED]`，不含长度以外的秘密。`from_bytes` 只接收32字节，外部变长/base64输入必须先校验；DbKey/解密明文转密钥时在Zeroizing缓冲内检查长度再复制，不以公开裸Vec/String长期保存。恢复码的规范字符串和解码的16字节熵在派生结束后零化；读取 `as_str` 是敏感出口，由CORE-24/界面按现有一次展示/不得日志上传规则使用。
- 恢复码派生固定为 HKDF-SHA256：IKM 为规范解码所得原始16字节（不是27字符文本），salt为空，info为UTF-8 `fml/v1/recovery`，输出32字节；`new_recovery_code` 与 `recovery_key` 复用同一编解码/派生路径。校验辅助函数在本crate内部供单元测试调用，只校验/解码、不做HKDF，不另增跨卡公开协议。
- 随机性规则（ADR-V5-41）：本 crate 不访问 OS，所有随机字节（密钥、nonce、盐、恢复码）都经 `SecureRandom`；rng 返回错误一律映射 `CRYPTO_RNG_FAILED` 并向上传播，禁止回退到其他随机源或以全零字节继续。`FixedRandom` 是本卡 `tests/common/mod.rs` 的测试替身（私有字节缓冲+当前位置，`new(bytes: Vec<u8>) -> Self`），按序吐出给定字节，字节耗尽也返回 `CRYPTO_RNG_FAILED`，不导出生产API/特性；其他卡按同一trait写自己的测试替身，不假设能导入本卡测试模块。口令包装的 16 字节盐由调用方先用 rng 取得再传入 `wrap_with_params`。
- 口令在派生前做 Unicode NFC 规范化，UTF-8 编码后输入 Argon2id；`KdfParams` 默认 `m_kib = 65536, t = 3, p = 4`。
- 错误码（本卡唯一定义）：

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `CRYPTO_DECRYPT_FAILED` | error | 否 | 认证标签/AAD/版本/长度/编码无效；不区分原因 |
| `CRYPTO_KEY_VERSION_UNKNOWN` | error | 否 | 使用方在本地 key_version→根密钥表查无所需版本时构造（如CORE-26/备份调用者）；本crate的纯AEAD/HKDF不查询表，也不凭单个SecretKey猜测版本 |
| `CRYPTO_RECOVERY_CODE_FORMAT` | warning | 否 | 恢复码字符、长度、首字符或校验位非法 |
| `CRYPTO_PASSPHRASE_WEAK` | warning | 否 | 违反口令策略 |
| `CRYPTO_KDF_MEMORY` | error | 否 | 当前内存不足以执行指定 Argon2id 参数 |
| `CRYPTO_PARAM_INVALID` | error | 否 | 非口令类 WrapKind 或 KDF 参数越界 |
| `CRYPTO_RNG_FAILED` | error | 是 | 调用方提供的 `SecureRandom` 返回错误或字节耗尽（含 `random_key`、`seal_with_rng`、`wrap`、`new_recovery_code`） |

测试向量（`crates/fml-crypto/tests/vectors/`，期望值取自标准文档，不由本实现生成）：KV-02～04通过私有单元测试直接调用选定上游HKDF原语，以标准IKM/salt/info/L=42验证；KV-05通过私有上游Argon2id原语测试保留标准secret/AD及小内存参数。两者不是对生产 `derive_subkey`/`passphrase_key` 的直接测试，不为跑KAT放宽生产API参数；另外对本卡固定用途/参数API写独立golden与边界测试。KV-06/07及WR向量的人工计算和独立复核证据随数据交付，不由待测实现再生成“期望”。

| 编号 | 对象 | 来源 |
| --- | --- | --- |
| KV-01 | XChaCha20-Poly1305 AEAD | draft-irtf-cfrg-xchacha 附录 A.3.1 示例 |
| KV-02～04 | HKDF-SHA256 | RFC 5869 附录 A.1–A.3 |
| KV-05 | Argon2id | RFC 9106 第 5.3 节 |
| KV-06 | Crockford Base32 与 mod 37 校验 | 自编：全 0 密钥、全 1 密钥、随机 3 例，期望值人工按规范计算并双人复核 |
| KV-07 | AAD CBOR | 自编：全字段、只含必填字段、UUID 字段 3 例，期望字节人工编码并用 RFC 8949 附录 A 的编码规则复核 |

WrapRecord wire v1（≤4096 B，严格 RFC 8949 确定性 CBOR；读入非最短编码、重复/未知键、不定长、尾随字节或长度不符均 CRYPTO_DECRYPT_FAILED）：

| 整数键 | 字段 | CBOR 类型/约束 |
| --- | --- | --- |
| 1 | wire_version | uint，固定1 |
| 2 | wrap_kind | uint，Platform=0、RecoveryCode=1、SyncPassphrase=2、ExportPassword=3；线上名称分别 platform/recovery_code/sync_passphrase/export_password |
| 3 | key_version | uint，1..u32::MAX |
| 4 | kdf | map {1:m_kib,2:t,3:p}，整数键升序；只允许口令两种 kind，默认 65536/3/4，m_kib ≤131072、t≤10、p=4 |
| 5 | salt | bstr16；与键4 同时出现，其他 kind 两键都省略 |
| 6 | sealed | bstr：CORE-21 Sealed::to_bytes（version1+nonce24+ciphertext含tag16）；被包装明文固定32 B，实际长度73 B |
| 7 | created_at_ms | int64，UTC 毫秒 |

字段键按1..7递增，缺省4/5省略、不编码 null。unwrap 的 AAD 为 aad_cbor，domain="key.wrap/v1/<wrap_kind线上名>"，account/entity字段省略，key_version 与记录一致、format_version=1，防替换 kind/version；口令包装先由调用方 CSPRNG 提供 salt，passphrase_key 派生后，wrap_with_params(rng,kek,key,kind,version,kdf,salt,now_ms) 写入全部参数；非口令 `wrap(rng,kek,key,kind,key_version,now_ms)` 只接受 Platform/RecoveryCode，kdf/salt=None；口令两种kind传入该函数返回 CRYPTO_PARAM_INVALID。`wrap_with_params` 只接受 SyncPassphrase/ExportPassword，签名为 `pub fn wrap_with_params(rng: &mut dyn SecureRandom, kek: &SecretKey, key: &SecretKey, kind: WrapKind, version: u32, kdf: KdfParams, salt: [u8;16], now_ms: i64) -> Result<WrapRecord,FmlError>;`。版本0在包装入口为CRYPTO_PARAM_INVALID；unwrap先按from_bytes等价结构校验再解密（含32字节明文检查），错误一律CRYPTO_DECRYPT_FAILED。Platform=0保留此格式与纯SecretKey KEK包装能力；Android Keystore/Windows DPAPI的CORE-04平台blob不是WrapRecord，调用者不得假设能在本crate解封平台blob，也不得把platform记录上传账户密钥端点。所有者提供此受测函数，不允许外卡手工补字段。

WR-NEG-01 最小语法向量（sealed 为41 B空明文，故 from_bytes 必须拒绝长度，给解码器反例）：`a501010201030106582901000000000000000000000000000000000000000000000000000000000000000000000000000000000700`。
WR-01 正例 = map(5): 1→1,2→1,3→1,6→bstr(0x01+24个0x00+48个0x00),7→0；其确切十六进制为 `a5010102010301065849010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000700`。这里只验格式往返，不声称全零密文通过 AEAD 验证。WR-02 在 WR-01 加4→{1:65536,2:3,3:4}、5→16个0x01且kind=2；测编码字节与独立 RFC 编码器一致、解码再编码相同。

`contracts/vectors/wrap-v1.json` 由本卡创建并维护，是跨CORE-24/26/27/32调用者的只读wire向量来源；顶层固定 `schema:1, wrap_version:1, aad_version:1, vectors:[{id, hex, valid}]`，id唯一，hex小写偶数长度，WR-NEG-01 valid=false、WR-01/WR-02 valid=true，其余非最短/未知键等负例使用唯一WR-NEG-*标识。valid仅指WrapRecord结构解码，不代表AEAD验证成功；真正认证篡改测试另用本卡固定AEAD向量。数据由独立编码/复核产生，当前尚未创建就保持未交付，不以文内向量冒充文件。

依据：[RFC 8949 §4.2](https://www.rfc-editor.org/rfc/rfc8949#section-4.2)。

```rust
pub fn wrap_with_params(rng: &mut dyn SecureRandom, kek: &SecretKey, key: &SecretKey, kind: WrapKind, version: u32,
    kdf: KdfParams, salt: [u8;16], now_ms: i64) -> Result<WrapRecord, FmlError>;
```
该函数只接受 SyncPassphrase/ExportPassword，校验参数范围；其他 kind 或 KDF 参数越界返回 `CRYPTO_PARAM_INVALID`（调用方编程错误，不与解密失败混用）。

产品约束追踪：见README §6 Q3；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 只使用经审计的库（RustCrypto 的 chacha20poly1305、argon2、hkdf 与 sha2；无实际哈希用途不添加blake3依赖）；禁止自研密码算法与自研 PAKE。确定性 CBOR 只需上述字段类型，自写最小编码器，不引入通用 CBOR 库。
- 外部前提：上述 crate 与 `zeroize` 版本按 ADR-V5-15 由首张使用卡开工时锁入 `Cargo.lock`（`getrandom` 只由 CORE-23 的 `OsRandom` 依赖，不进入本crate正常/构建依赖闭包；chacha20poly1305等禁用默认隐式熵源特性，仅启用所需alloc/纯算法特性，按锁定版本核查；测试工具的dev依赖另报告，不能把它当生产依赖）；常见口令表（`crates/fml-crypto/data/common-passwords.txt`，每行一个 NFC 小写口令，≤ 100 KiB，`include_str!` 编译进 crate）的来源 URL、许可与 BLAKE3 在 M0 登记于附录D 本卡外部前提行；登记前该文件不交付、相应验收阻断，策略逻辑单元测试改用 `#[cfg(test)]` 内置 10 条固定样例表，不以空表通过。比对时口令先 NFC 再按 Unicode 小写折叠。本表只用于客户端同步密语/导出口令策略，与 CORE-22 服务端登录口令表（`AUTH_PASSWORD_WEAK`）相互独立，不共用文件、不要求一致（登录口令与端到端密钥无派生关系）。
- 服务端可见的登录凭据永远不作为端到端加密密钥或其派生来源；同步密语只在客户端使用，从不上传。
- 恢复码使用 HKDF（其熵已足够，不再做慢 KDF）；只显示一次，服务端不保存恢复码或其可离线验证的哈希，只保存它包装的密钥记录。
- Argon2id 参数下限 m = 64 MiB、t = 3、p = 4，盐 128 位；内存占用上限 128 MiB；低内存设备不得降到下限以下，改为提示“改用恢复码”。
- 每类数据使用独立子密钥，可单独删除识别历史；密钥材料不得写入普通 SQLite 表、日志与复现包；内存中用 `Zeroizing` 尽力清零。
- 密钥轮换：更换同步密语或重新生成恢复码只重新包装；设备吊销或怀疑泄露时生成新 AccountDataKey，`key_version` + 1，重新加密快照（由 CORE-26 执行）。所有包装记录带 `key_version` 与创建时间，旧包装在用户确认后过期。
- 云识别供应商 API Key 与本 crate 无关，只在服务端（CORE-33）。

**验收标准**：测试方案全文见 [Test/core/S2_CORE-21_TEST.md](../Test/core/S2_CORE-21_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 555 行，分阶段：① `crates/fml-crypto/src/` 密钥类型/访问器/AEAD/HKDF/随机端口约160、确定性CBOR与WrapRecord/AAD约210，共370；可独立构建并通过AEAD/HKDF上游KAT、非口令wrap及所有kind的纯wire编解码测试；② 同目录恢复码编解码/派生/零化约105、Argon2id/口令策略约80，共185，依赖第一阶段，独立运行恢复码KAT、参数上下界与生产派生测试，不以未实现KDF阻断第一阶段纯wire验收。测试代码/向量与常见口令表数据不计；比原475增加的80行明确覆盖访问/校验/零化边界及两类包装入口，独立复估未完成不得宣称规模已验收。

