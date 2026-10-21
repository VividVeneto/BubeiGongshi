### CORE-16 内容管线与课程内容包

**目标**：提供把公式内容源数据校验、审校记录、去重、打包并签名的工具链，并规定四类课程内容包与 bootstrap 包的内容结构和发布门槛。

**范围**
- 包含：`packs/` 源数据目录规范、条目 schema、`tools/content/fmlcontent` 命令行工具（校验、覆盖率报告、去重、抽检抽样、构建、签名）、包 ID 清单、内容发布门槛。
- 不包含：内容本身的编写（按批次作为数据任务执行，不计入代码规模）；开源资源调查（附录 C）。

**依赖**：CORE-01、CORE-02、CORE-05、CORE-06、CORE-07、CORE-08、CORE-09、CORE-15

**接口契约**

包 ID：

| 包 | 内置 | 内容 |
| --- | --- | --- |
| `bootstrap-pack` | 必须内置 | 最小数学字体、符号表（ISO 80000-2 与国内记号）、SI 单位与常用单位、常数集（exact 与 textbook）、国内默认与 ISO 记号方案、简体中文消息与朗读资源、少量示例 |
| `content-high-school-math` | 下载 | 高中数学：函数、三角、数列、立体几何、解析几何、概率统计、导数及其应用；积分按课程范围标记 |
| `content-high-school-physics` | 下载 | 高中物理：力学、电磁学、热学、光学、近代物理基础 |
| `content-university-math` | 下载 | 高等数学（同济版教材范围）+ 考研数学数一、数二、数三并集（含线性代数、概率论与数理统计），以 `exam_scope` 区分，不物理删除 |
| `content-university-physics` | 下载 | 大学物理公共课主流板块 |
| `font-extension` | 下载 | 扩展字形 |
| `model-recognition-*` | 下载 | 本地识别模型（格式见 CORE-35） |

源数据目录：`packs/<pack_id>/{manifest.base.yaml, scope.yaml, items/*.yaml, questions/*.yaml, books/*.yaml, notation/, constants/, symbols/, LICENSES.yaml}`。

条目（`items/*.yaml`）必填字段：`key`、`title`、`latex`、`symbol_decls`、`unit_hints`、`education_level`（high_school / university）、`textbook_refs[]`（教材 ID、版次、章、节、页）、`syllabus_id` 与 `syllabus_year`（考研条目）、`kp_ids[]`、`exam_scope` ⊆ {数一, 数二, 数三}、`scope_note`、`scope_origin`（both / textbook_only / syllabus_only）、`requirement_level`（了解 / 理解 / 掌握 / 会用）、`conditions[]`、`notation_profile_ids[]`、`constant_refs[]`、`wording_source` 与 `wording_license`、`provenance`、`review`（author、reviewer、reviewed_at、revision、disagreements；author ≠ reviewer）。选填教学字段：`explanation`、`symbol_notes[]`、`equivalent_forms[]`、`derivation_ref`（派生树）、`confusable_group_id`、`prerequisites[]`、`pitfalls[]`、`example_refs[]`（只存出处索引）、`exam_frequency`（含统计方法与年份，否则留空）。未审字段不显示；“不适用”写 `not_applicable`，与空值区分。

题目（`questions/*.yaml`）：`type`、`stem`、`answer_latex`、`distractors[]`（每个带错误类型：漏系数、正负号、指数、分子分母颠倒、量纲不一致）、`given_constants`、`sig_figs`、`required_form`（可选）。

主要字段的类型与取值（其余字段为字符串或字符串数组，均 UTF-8，单个字符串 ≤ 4000 字符）：

| 字段 | 类型与取值 | 必填 |
| --- | --- | --- |
| `key` | `^[a-z0-9_.-]{3,80}$`，包内唯一；与 `pack_id` 一起生成 UUIDv5 条目 ID（CORE-05） | 是 |
| `latex` | CORE-06 可解析的 LaTeX | 是 |
| `symbol_decls` | `[SymbolDecl]`（CORE-05 字段的 YAML 写法） | 是（可为空数组） |
| `education_level` | `high_school` 或 `university` | 是 |
| `textbook_refs[]` | `{textbook_id, edition, chapter, section, page}`；`textbook_id` 如 `TJ-GS-8` | 是（考研专属条目可空） |
| `exam_scope` | `[shu1 | shu2 | shu3]` 的子集；YAML 中用拼音代号，界面显示数一、数二、数三 | 大学数学条目必填 |
| `requirement_level` | `liaojie | lijie | zhangwo | huiyong`（了解、理解、掌握、会用） | 是 |
| `scope_origin` | `both | textbook_only | syllabus_only` | 是 |
| `review` | `{author, reviewer, reviewed_at (YYYY-MM-DD), revision (整数), disagreements[]}`，`author ≠ reviewer` | 是 |
| `exam_frequency` | `{count, years: [YYYY], method}` 或省略 | 否 |

- 命令退出码：`0` 通过；`1` 存在校验错误（逐条输出 `<文件>:<行> <错误码> <消息>`）；`2` 用法或 I/O 错误。`validate` 与 `coverage` 另写 `dist/<pack_id>.report.json`（`{pack_id, items, verified, errors[], coverage: {kp_total, kp_covered, by_exam_scope: {shu1, shu2, shu3}}}`）。
- 内容错误码在下表唯一定义，owner=CORE-16，先登记 CORE-02 registry 后生成；CLI 退出码仍为上述 0/1/2，不把错误码另映射为进程返回值。解析与量纲错误复用 CORE-06/08/09 的 `PARSE_`、`UNIT_`、`TYPE_` 码并原样输出，不重定义级别/重试性。

| 错误码 | 级别 | 可重试 | 触发条件 |
| --- | --- | --- | --- |
| `CONTENT_FIELD_MISSING` | error | 否 | 源条目或题目缺必填字段；审校人和许可缺失优先采用下列专用码 |
| `CONTENT_FIELD_INVALID` | error | 否 | 字段类型、枚举、格式、取值或引用不满足本卡源模型约束 |
| `CONTENT_DUPLICATE` | error | 否 | 同类条目跨文件 key 重复，或规范 AST 哈希 + 条件 + 符号映射去重键重复 |
| `CONTENT_LICENSE_FORBIDDEN` | error | 否 | 存在本卡禁止的 CC BY-SA、GFDL、NC 等许可 |
| `CONTENT_LICENSE_MISSING` | error | 否 | 缺来源许可登记或必要许可文件/字段 |
| `CONTENT_REVIEW_INVALID` | error | 否 | 缺审校人或 author = reviewer |
| `CONTENT_NOT_VERIFIED` | error | 否 | CORE-09 校验结果非 Verified，不得出卡 |

- 签名：`sign` 读取 PKCS#8 PEM 格式的 Ed25519 私钥（路径由 `--key` 指定，不入库），写出 `manifest.sig` 并重新打包。

命令：

```text
fmlcontent validate packs/<id>          # 解析、绑定、量纲校验、字段完整性、许可、去重；非 Verified 条目不得出卡
fmlcontent coverage packs/<id>          # 按 scope.yaml 的知识点清单输出覆盖率与缺项
fmlcontent sample   packs/<id> --batch <n>  # 按 max(50, 10%) 随机抽检样本，供第三人审核
fmlcontent build    packs/<id> -o dist/ # 生成 manifest 与 entries
fmlcontent sign     dist/<file> --key-id <id>   # 只在离线签名机执行
```

构建产物 EntryType JSON schema=1（UTF-8，deny_unknown_fields；所有文件顶层 {schema:1,entries:[...]}，无重复 key，条目 key 与 manifest.logical_id 对应）：

| EntryType | entries 每元素 |
| --- | --- |
| formula_items | {key,title,subject,course?,tags:[],revision:CORE-05 FormulaRevision,requirement_level,templates:[],distractors:[{latex,error_type,reviewed_by,reviewed_at}],reviewed_by,reviewed_at,content_hash}；revision.id在算完content_hash后按CORE-05由条目ID与该hash派生，源中已有值必须与重算值相等；不得参与自身hash；其余revision UUID按 CORE-05，ast为规范JSON，ast_hash经工具重算比对；error_type 取 漏系数/正负号/指数/分子分母颠倒/量纲不一致，与 CORE-19 的 Distractor.error_type 同名同值；reviewed_at 为 YYYY-MM-DD（需要毫秒的消费者取该日 UTC 0 时）；content_hash = 去掉content_hash及revision.id（派生ID）字段后该元素规范 JSON（CORE-05 规则）的 BLAKE3 小写十六进制，即 CORE-14 `PackFormulaEntry.content_hash` 与 CORE-05 `pack_cache_revision_id` 的输入 |
| units | CORE-56 引擎数据的 `units.json` 与 `kinds.json`；源 YAML 的 source_ref、exact 只供 validate，不进产物 |
| notation | CORE-56 引擎数据的 `profiles.json` |
| constants | CORE-56 引擎数据的 `constants.json`；来源与版本必填 |
| fonts | 二进制字体 + CORE-56 `fonts.json`（`{id,file,blake3,spdx,license_file}`），不把字体塞 JSON |
| model / lexicon | 模型二进制 / UTF-8词表，具体配置归 CORE-35，不由内容工具猜测模型结构 |
| metadata | {key,value:object}，按 logical_id 指定 schema；book 元数据归本卡课程源字段，model-config 转交 CORE-35 校验 |

validate 对同类条目跨文件 key 也查重，构建后 roundtrip 与源数据含义一致。units/notation/constants/fonts 四类合起来就是一层 CORE-56 引擎数据（含其 `manifest.json`），格式只由 CORE-56 定义，build 先用 CORE-56 `compose` 与内置层试合成，失败即构建失败；bootstrap 包的这四类从 `crates/fml-ffi/assets/engine-v1/` 生成。公式映射到账号库由 CORE-14 PackCatalog 投影负责，不由工具生成用户库文件。

产品约束追踪：见README §6 Q40；已确认事项按确认值，待确认事项保持暂行默认，不由编码会话自行改产品取舍。

**实现约束**
- 工具复用核心 crate（直接链接 `fml-latex`、`fml-type` 等），不得另写一套解析或量纲逻辑。
- 去重键：规范 AST 哈希 + 条件 + 符号映射。
- 版权：公式本身不受著作权保护，但教材与真题的表述受保护，只存出处与自编改写；CC BY-SA、GFDL 与任何 NC 许可的内容不得入包；字体逐个登记许可。LLM 起草的内容与人工内容同等审校，并记录工具与版本。来源与许可调查见附录 C。
- 范围清单：每个课程包的 `scope.yaml` 列出知识点（`kp_id`，最小可判定子句）、适用科目、要求层级与依据页码；高中依据现行普通高中课程标准的必修与选择性必修；高等数学依据同济版《高等数学》第八版（甲方确认，README §6 Q2）与当年考研数学考试大纲；大学物理依据《理工科类大学物理课程教学基本要求》（版本以附录 C 核实记录为准）。
- 签名私钥只存在于离线签名机；CI 只做未签名构建与校验。
- 外部前提：YAML 解析 crate、命令行解析 crate 版本按 ADR-V5-15 由首张使用卡开工时锁入 `Cargo.lock`；离线签名机与首个 `key_id` 由甲方指定的发布负责人保管（CORE-43 记录）；各课程包内容按批次作为数据任务编写，不阻塞本卡编码。

**验收标准**：测试方案全文见 [Test/core/S4_CORE-16_TEST.md](../Test/core/S4_CORE-16_TEST.md)；修改本卡功能时同步修改该文件（工具按此引用把它拼回本卡）。

**规模**：约 525 行（工具代码，内容数据与签名密钥不计）；`tools/content/`。分阶段：① 内容源模型与校验（CLI 框架、源模型与加载、字段/许可/去重校验、Verified 门控、覆盖率报告与抽检，约 365）；② 内容包构建与签名（build 打包与引擎数据生成、roundtrip、sign 及子命令登记，约 160）。

