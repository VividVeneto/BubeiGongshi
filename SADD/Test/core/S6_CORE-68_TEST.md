# CORE-68 测试方案

> 来源卡：[S6_CORE-68_扩展.md](../../core/S6_CORE-68_扩展.md)（同步 Envelope 共享线类型）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R28] 两侧读同一向量，规范序列化字节相同（`to_canonical_json` 与向量中的规范字节逐字节一致，且全部字符串字段为不需转义的 ASCII）；非法base64/nonce长度/哈希/整数越界拒绝；不因UUID为v5拒绝。
- [R28] 向量逐条：`contracts/vectors/envelope-v2.json`（内容见下表）的每个用例经 `from_json` 得到期望结果（ok、`Invalid{field}` 字段名逐一比对、TooLarge、HashMismatch）；ok 用例的 `to_canonical_json` 输出与规范字节逐字节一致，且 `from_json(to_canonical_json(e)) == e`；CORE-25（server/tests）与 CORE-26（fml-store 测试）各自读取同一文件。
- [R28] 首错顺序：同时破坏 account_epoch 与 nonce 时只报 `account_epoch`；破坏 nonce 与哈希时报 `nonce`。
- [R28] 线类型：PushItemResult 序列化为带 `status:"ACK"|"CONFLICT"` 的扁平对象，未知 status 与多余字段反序列化失败；PushRequest/PushResponse/PullResponse 往返相等，PullResponse 中的 Envelope 不在反序列化时自动 validate（由调用方逐个 validate 并隔离）。
- [R19] 依赖检查：`cargo metadata` 显示 fml-sync-proto 的直接依赖仅 serde、serde_json、uuid、base64、sha2。

**Envelope v2 向量清单**（CORE-68 编码会话据此建立 `contracts/vectors/envelope-v2.json`，version 1，按 CORE-02 共享格式清单由实现卡创建；用例名即向量 name）。base_json 为下列规范字节（ciphertext 为字节 0x00..0x13、nonce 为字节 0xa0..0xb7）：

`{"envelope_version":2,"kind":"event","account_epoch":1,"op_id":"00000000-0000-4000-8000-000000000011","device_id":"00000000-0000-4000-8000-000000000022","device_seq":1,"key_version":1,"entity_type":"local_setting","entity_id":"ui.theme","schema_version":1,"aad_version":1,"purpose":"user_settings","nonce":"oKGio6SlpqeoqaqrrK2ur7CxsrO0tba3","ciphertext":"AAECAwQFBgcICQoLDA0ODxAREhM=","ciphertext_hash":"e7aebf577f60412f0312d442c70a1fa6148c090bf5bab404caec29482ae779e8"}`

| 用例 | 相对 base_json 的输入 | 期望 |
| --- | --- | --- |
| ok_setting | 基准输入（即 base_json） | ok |
| ok_formula_revision_v5_op_id_max_seq_reordered_keys | `formula_revision`、op_id 为 v5 `6ba7b810-9dad-51d1-80b4-00c04fd430c8`、entity_id=revision_id=`00000000-0000-4000-8000-0000000000aa`、purpose `user_formula`、device_seq=9223372036854775807，键序完全倒置；规范字节为同字段按声明顺序输出 | ok |
| ok_setting_revision_id_null | 新增 `revision_id: null` | ok，规范字节等于 base_json（null 视为缺省并省略） |
| ok_ciphertext_max | ciphertext 改为 262144 个 0x00 字节的标准 base64，哈希按其重算 | ok |
| too_large_ciphertext | ciphertext 改为 262145 个 0x00 字节的标准 base64，哈希按其重算 | TooLarge |
| unknown_field | extra=`1` | Invalid{`$`} |
| duplicate_field | base_json 末尾重复 `"kind":"event"` | Invalid{`$`} |
| envelope_version_1 | envelope_version=`1` | Invalid{`envelope_version`} |
| kind_snapshot | kind=`"snapshot"` | Invalid{`kind`} |
| account_epoch_zero | account_epoch=`0` | Invalid{`account_epoch`} |
| op_id_uppercase | op_id=`"00000000-0000-4000-8000-0000000000AA"` | Invalid{`op_id`} |
| op_id_nil | op_id=`"00000000-0000-0000-0000-000000000000"` | Invalid{`op_id`} |
| device_seq_over_i64 | device_seq 原文为 9223372036854775808 | Invalid{`device_seq`} |
| device_seq_zero | device_seq=`0` | Invalid{`device_seq`} |
| key_version_zero | key_version=`0` | Invalid{`key_version`} |
| entity_type_uppercase | entity_type=`"Setting"` | Invalid{`entity_type`} |
| entity_id_escape_char | entity_id=`"ui/theme"` | Invalid{`entity_id`} |
| revision_id_on_setting | revision_id=`"00000000-0000-4000-8000-0000000000aa"` | Invalid{`revision_id`} |
| revision_id_not_entity_id | — | Invalid{`revision_id`} |
| formula_revision_missing_revision_id | — | Invalid{`revision_id`} |
| schema_version_zero | schema_version=`0` | Invalid{`schema_version`} |
| purpose_backup | purpose=`"backup"` | Invalid{`purpose`} |
| nonce_23_bytes | nonce=`"oKGio6SlpqeoqaqrrK2ur7CxsrO0tbY="` | Invalid{`nonce`} |
| nonce_25_bytes | nonce=`"oKGio6SlpqeoqaqrrK2ur7CxsrO0tba3uA=="` | Invalid{`nonce`} |
| nonce_urlsafe | nonce=`"-_v7-_v7-_v7-_v7-_v7-_v7-_v7-_v7"` | Invalid{`nonce`} |
| ciphertext_15_bytes | ciphertext=`"AQIDBAUGBwgJCgsMDQ4P"`；ciphertext_hash=`"36030fcc7e566294905b49a720eb45bf962209d2ee1c9b73e2b7bc7ae8830376"` | Invalid{`ciphertext`} |
| ciphertext_noncanonical_trailing_bits | ciphertext=`"AAECAwQFBgcICQoLDA0ODxAREhN="` | Invalid{`ciphertext`} |
| hash_uppercase | ciphertext_hash=`"E7AEBF577F60412F0312D442C70A1FA6148C090BF5BAB404CAEC29482AE779E8"` | Invalid{`ciphertext_hash`} |
| hash_mismatch | ciphertext_hash=`"2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"` | HashMismatch |
