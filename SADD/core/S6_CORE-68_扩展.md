### CORE-68 同步 Envelope 共享线类型

**目标**：端侧与服务端复用唯一Envelope类型与序列化向量。

**范围**
- 包含：fml-sync-proto纯数据结构（Envelope 与 push/pull 线类型）、规范序列化、解析与边界校验（validate/from_json）。
- 不包含：网络、数据库、合并和加解密；消费方CORE-25/26为下游说明，非契约。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-21（CORE-05 只提供 entity_id 取值约定、CORE-21 只提供 KeyPurpose 蛇形名，均为语义依赖：本 crate 不依赖 fml-ast/fml-crypto，蛇形名在本卡以字面量列出，CORE-21 改名须经 §8.4 变更单同步本卡与向量）

**接口契约**
```rust
// crates/fml-sync-proto/src/lib.rs
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)] #[serde(deny_unknown_fields)]
pub struct Envelope {
 pub envelope_version: u8, pub kind: String, pub account_epoch: u32,
 pub op_id: Uuid, pub device_id: Uuid, pub device_seq: u64, pub key_version: u32,
 pub entity_type: String, pub entity_id: String,
 #[serde(skip_serializing_if = "Option::is_none")] pub revision_id: Option<String>,
 pub schema_version: u16, pub aad_version: u16, pub purpose: String,
 pub nonce: String, pub ciphertext: String, pub ciphertext_hash: String,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum EnvelopeError { Invalid { field: &'static str }, TooLarge, HashMismatch }
impl Envelope { pub fn validate(&self) -> Result<(), EnvelopeError>; }   // 按下列字段域逐项检查
pub fn from_json(bytes: &[u8]) -> Result<Envelope, EnvelopeError>;   // 单个 Envelope 的严格解析 + validate
pub fn push_request_from_json(bytes: &[u8]) -> Result<PushRequest, EnvelopeError>;   // 服务端 push 请求体唯一入口：外层语法/未知字段为 Invalid{"$"}，元素按序走 from_json 规则，返回第一处元素错误
pub fn to_canonical_json(e: &Envelope) -> Vec<u8>;   // 规范 JSON：紧凑无空白、键按结构字段顺序、Option 省略、不转义 `/`（即 serde_json::to_vec，字段类型保证不失败）；CORE-26 批次元素字节与 CORE-25 请求体计量的唯一编码

// push/pull 线类型（HTTP 请求体与响应体的唯一定义；CORE-25 路由与 CORE-26 客户端共用）
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)] #[serde(deny_unknown_fields)]
pub struct PushRequest { pub envelopes: Vec<Envelope> }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)] #[serde(tag = "status", deny_unknown_fields)]
pub enum PushItemResult {
 #[serde(rename = "ACK")] Ack { op_id: Uuid, server_seq: u64 },
 #[serde(rename = "CONFLICT")] Conflict { op_id: Uuid },
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)] #[serde(deny_unknown_fields)]
pub struct PushResponse { pub results: Vec<PushItemResult>, pub account_epoch: u32 }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)] #[serde(deny_unknown_fields)]
pub struct PullResponse { pub envelopes: Vec<Envelope>, pub next_cursor: String, pub has_more: bool, pub account_epoch: u32 }
```
字段域（validate 按结构字段顺序检查，返回第一处错误；`Invalid.field` 为字段名）：envelope_version==2；kind=="event"；account_epoch≥1；op_id/device_id 为小写带连字符的非 nil UUID（任意版本，允许确定性 v5）；device_seq 1..=i64::MAX；key_version≥1；entity_type 匹配 `^[a-z][a-z0-9_]{0,63}$`；entity_id 匹配 `^[a-z0-9][a-z0-9_.-]{0,127}$`（不透明标识：UUID 实体为 CORE-05 小写 UUID，设置实体为 CORE-26 local_setting 键；按 entity_type 区分取值形态由 CORE-26 实体编解码检查，本卡只查字符集与长度）；revision_id 仅当 entity_type=="formula_revision" 时出现且等于 entity_id，其他类型出现即非法；schema_version≥1、aad_version≥1；purpose ∈ {user_formula, study_data, user_settings}（CORE-21 KeyPurpose 同步用途蛇形名）；nonce 为规范标准 base64（含填充、无空白、填充位为零）解码恰 24 字节；ciphertext 为规范标准 base64、解码 16..=262144 字节（含 16 字节 tag），超过 262144 返回 TooLarge，其余格式错误为 Invalid；ciphertext_hash 匹配 `^[0-9a-f]{64}$`（否则 Invalid），且等于 SHA-256(ciphertext 解码字节) 否则返回 HashMismatch。
from_json：先反序列化到 crate 私有镜像（op_id/device_id 为字符串、整数为 u64，同样 deny_unknown_fields），JSON 语法错误、未知字段、重复字段、缺字段、类型不符或整数超 u64 均为 `Invalid{field:"$"}`；随后按字段顺序转换并检查，整数超出 Rust 位宽、UUID 非规范形式报对应字段。非规范键序可读，输出始终规范键序。Envelope 的 derive Deserialize 不做域校验（用于 PullResponse 与 CORE-78（下游说明，非契约）已持久化批次的读取）；对已构造的结构 validate 检查除 UUID 文本形式外的全部字段域（Uuid 类型序列化恒为规范小写），UUID 文本形式只在 from_json/push_request_from_json 检查。
错误映射（调用方执行，本卡不定义错误码）：服务端 CORE-25 把 Invalid 映射为 SYNC_ENVELOPE_INVALID（400）、TooLarge 为 SYNC_PAYLOAD_TOO_LARGE（413）、HashMismatch 为 SYNC_HASH_MISMATCH（400）；端侧 CORE-26 对 pull 到的任一错误隔离该 Envelope 并记 SYNC_QUARANTINED。
`contracts/vectors/envelope-v2.json`（version 1，由本卡编码会话按测试方案的向量清单创建）保存成功、规范字节、未知/重复字段、各字段越界、base64 非规范、TooLarge 与 HashMismatch 向量；输入中 `revision_id: null` 视为缺省；HTTP 与 FFI 均复用，不复制 Rust 镜像。push/pull 线类型的 JSON Schema 镜像为 `contracts/dto/types.schema.json` 的 `$defs` Envelope、PushItemResult、PullPage，所有者为本卡。

**实现约束**
- 外部 crate 只依赖 serde、serde_json、uuid、base64、sha2（外部前提：版本按 CORE-01 锁定），不访问时钟、文件、网络或Store。
- server与端侧同用本crate；未知entity_type隔离策略归调用方。

**验收标准**：测试方案全文见 [Test/core/S6_CORE-68_TEST.md](../Test/core/S6_CORE-68_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约260行（Envelope 与线类型约 70、validate/from_json 与私有镜像约 150、规范序列化约 40）；主包crates/fml-sync-proto/，附属contracts/vectors/envelope-v2.json为数据0行；无分阶段；端侧/服务端调用点由各消费者编写，未知entity_type隔离由调用方处理，不计本卡。 单阶段可独立构建测试；只计本卡实现及本卡编写的附属接入，不计数据/生成物/自测。

