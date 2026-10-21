### CORE-68 同步 Envelope 共享线类型

**目标**：端侧与服务端复用唯一Envelope类型与序列化向量。

**范围**
- 包含：fml-sync-proto纯数据结构、序列化与边界校验。
- 不包含：网络、数据库、合并和加解密；消费方CORE-25/26为下游说明，非契约。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-21

**接口契约**
```rust
// crates/fml-sync-proto/src/lib.rs，derive Serialize/Deserialize，deny_unknown_fields
pub fn to_canonical_json(e: &Envelope) -> Vec<u8>;   // 规范 JSON：紧凑无空白、键按结构字段顺序、Option 省略、不转义 `/`（即 serde_json::to_vec）；CORE-26 批次元素字节与 CORE-25 请求体计量的唯一编码
pub struct Envelope {
 pub envelope_version: u8, pub kind: String, pub account_epoch: u32,
 pub op_id: Uuid, pub device_id: Uuid, pub device_seq: u64, pub key_version: u32,
 pub entity_type: String, pub entity_id: String, pub revision_id: Option<String>,
 pub schema_version: u16, pub aad_version: u16, pub purpose: String,
 pub nonce: String, pub ciphertext: String, pub ciphertext_hash: String,
}
```
wire: version=2/kind=event；UUID小写带连字符；nonce标准base64解码24字节，ciphertext标准base64解码≤256KiB且含tag，hash为SHA256(ciphertext原始字节)的小写64hex；purpose为CORE-21 KeyPurpose蛇形；Option省略。device_seq≤i64::MAX，其他整数非负且按Rust位宽；entity_type为业务实体名、entity_id为对应CORE-05 UUID（允许确定性UUID，不限随机）；revision_id仅formula_revision需要。JSON键按结构字段顺序输出，非规范输入键序可读。
`contracts/vectors/envelope-v2.json` 保存成功/未知字段/错误base64/越界向量；HTTP与FFI均复用，不复制Rust镜像。

**实现约束**
- 只依赖serde/uuid及纯校验，不访问时钟、文件、网络或Store。
- server与端侧同用本crate；未知entity_type隔离策略归调用方。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-68_TEST.md](../Test/core/S6_CORE-68_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约160行；主包crates/fml-sync-proto/，附属contracts/vectors/envelope-v2.json为数据0行；无分阶段；端侧/服务端调用点由各消费者编写，未知entity_type隔离由调用方处理，不计本卡。 单阶段可独立构建测试；只计本卡实现及本卡编写的附属接入，不计数据/生成物/自测。

