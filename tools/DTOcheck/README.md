# DTOcheck：契约与模块卡一致性检查

纯 Node 标准库实现（无第三方依赖），用来替代已清理的临时脚本（check.mjs / xref.mjs / validate-dto.py）。`pack.mjs` 的卡片解析（`tools/sadd/pack.mjs` 的 `load`）被直接复用；读取文档统一经 `tools/sadd/layout.mjs`，同时支持旧的三份文档与拆分后的 `S0/`、`core/`、`and/`、`win/` 布局（按 `00-总览.md` 中的卡片标记逐字节拼回）。

## 用法

```text
node tools/DTOcheck/run.mjs [--strict] [--json] [--verbose] [--only dto,cards,xref]
node tools/DTOcheck/dto.mjs   [--root DIR]            # contracts/dto 与 contracts/vectors
node tools/DTOcheck/cards.mjs [--sadd DIR]            # 模块卡 ↔ 索引 ↔ 依赖图 ↔ 阶段 ↔ README
node tools/DTOcheck/xref.mjs  [--baseline FILE] [--update-baseline FILE]
node --test tools/DTOcheck/*.test.mjs                 # 本工具自身的测试
```

退出码：0 通过；1 有 error（`--strict` 时 warning 也算）；2 工具自身异常。

## 检查内容

| 工具 | 检查 | 代号 |
| --- | --- | --- |
| dto | manifest：op 唯一与命名、owner 是现行卡、scope/mode/status、ready 必有 schema 与示例、pending 必有 blocked_reason、error_codes 唯一且有序 | DTO-01～09 |
| dto | manifest 阶段：每条必须带 `stage`（S0～S7），传入卡片阶段表时还须等于 owner 卡在 §2 实施阶段表中的阶段（唯一来源，检查器不猜） | DTO-22～23 |
| dto | manifest 引擎快照集合：ready 必须显式 `reads_engine_snapshot` 布尔值，且与该 op 是否含 `ENGINE_UNAVAILABLE` 双向一致；pending 不得声明 | DTO-24 |
| dto | manifest 条目字段冻结：ready 只准 `reads_engine_snapshot`、pending 只准 `blocked_reason` 作为状态相关键，其余未知键失败 | DTO-25 |
| dto | op 的错误集合来源：每个码必须在现行卡的“错误码”定义表恰好注册一次（未注册/重复归属都是硬错误）；CORE-03 的信封/句柄/取消码不得写入 op 的业务集合 | DTO-06、DTO-18 |
| dto | schema：$schema/title、关键字白名单、required ⊆ properties、对象必须 additionalProperties:false、整数范围（超过 2^53-1 登记为 i64 字段，超过 i64 报错）、pattern/format 合法、$ref 可解析、孤儿 schema | DTO-10～17 |
| dto | 示例按自带 schema 校验（类型、必填、额外字段、格式、范围、oneOf、prefixItems）；x-sensitive 与 manifest.sensitive_paths 一致 | DTO-12～14 |
| dto | contracts/vectors：JSON 合法；云识别幂等键按 UUIDv5 重算 | DTO-20～21 |
| cards | 卡号重复；§3 索引的名称/依赖/规模与卡正文一致；规模 ≤ 500、不含“另计”、多构建单元必须声明附属；依赖存在且无环 | CARD-01～10 |
| cards | 依赖图（mermaid）节点标签、边 ⊆ 依赖字段、每条直接依赖可达（CORE-01/02 除外）；实施阶段唯一且依赖不晚于自身 | GRAPH-01～05、STAGE-01～03 |
| cards | 迁移序号：`crates/fml-store/migrations/` 直接子文件与 `server/migrations/` 中序号 <0100 的 `NNNN_名.sql` 须对应归属卡 CORE-NNNN 且该卡正文声明此文件（CORE-13：V1 发布前序号取归属卡编号）；同目录序号不得重复；`registry/` 与其他 crate 的独立库迁移不查 | MIG-01～02 |
| cards | README §8.6：每卡一行、名称与阶段一致、卡数/分类统计句/小节标题；各文件版本号一致 | README-01～07、VER-01 |
| cards | 拆分布局：文件名为 `S编号_卡号_分组.md` 且分组在 8 个之内；S 编号等于实施阶段；S0 阶段的卡在 `S0/`，其余按卡号前缀在 `core/`、`and/`、`win/`；卡片文件只含一张卡且以其标题开头；每张卡在对应总览中恰有一个标记 | LAYOUT-01～05 |
| xref | 错误码在多张卡的“错误码”表中重复定义;`contracts/policies/shared-writes.json` 的 error 登记与卡内定义必须一致（owner 不符、卡内有定义却未登记、登记了无定义的码）——均为硬错误 | XREF-01～04 |
| xref | 启发式候选（未定义错误码、未定义类型、跨卡使用未声明依赖的类型、多卡定义的类型、未登记的 op 名）：有基线时只对“新增”报错 | XREF-NEW-* |

xref 的候选是启发式的，不能当作缺陷清单，也不能整体忽略：基线 `baseline/xref.json` 记录当前已知候选，**只允许减少**。新增候选先判断是真缺陷（修文档）还是误报（枚举变体同名、注释中的类型名等），确认后再 `--update-baseline`。

## 与正式门禁的关系

- 这是 SADD 文档与契约的检查，不是产品 CI。与 CORE-70 规划的 `tools/sadd/structure.mjs`（SADD-1～12）、CORE-67 的 `gen_dto.py` 有重叠；这些正式工具交付后，本目录的对应检查应并入它们，并删除本目录。
- 提交前请运行 `node tools/DTOcheck/run.mjs`（AGENTS.md 与 README §8.1 已列入）。
- `tools/sadd/`（pack、audit、stats、reservations、current）仍是材料、统计与就绪证据的正式入口，本工具不改写任何文件（`--update-baseline` 只写你指定的基线文件）。
- 未覆盖：Rust/Dart 编译、DTO 生成器（CORE-67 的 `gen_dto.py`）、字段语义是否合理、示例以外的向量。
- 未覆盖（等待所有者实现）：逐 op 期望错误集合的**双向比对**。对照源是 op 所有者卡的逐 op 错误镜像（`| op | 代码 |` 行或等效内联句），不是 registry——registry 只是码字典，REG-01 管字典与所有者卡表的逐列一致与双向全集（ADR-V5-55）。当前 DTO-06 只做“码已注册且归属唯一”、DTO-18 只拒 CORE-03 码，尚无“卡行 ↔ `error_codes`”的回向检查；registry.yaml 亦未创建（CORE-02 未实现）。本工具不把 manifest 与自身比、不自建第三份逐 op 期望，该回向比对落地后写在本工具，不在 `dto_schema.py` 里再写一遍。
