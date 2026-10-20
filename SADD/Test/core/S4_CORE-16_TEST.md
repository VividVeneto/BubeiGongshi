# CORE-16 测试方案

> 来源卡：[S4_CORE-16_功能.md](../../core/S4_CORE-16_功能.md)（内容管线与课程内容包）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R05] 自有最小夹具覆盖四类包：validate对合法条目通过、空包按发布校验拒绝；coverage生成可复现计数。真实四包非空交付归M-CONTENT，不计作工具编码完成条件。
- [R39] 高中数学、高中物理两个包的 `education_level` 全为 `high_school`，`validate` 对混入 `university` 条目的高中包报 `CONTENT_FIELD_INVALID`。
- [R05] 用固定scope与已审/审核中/未审夹具，coverage分科分母为冻结scope知识点数，分子只含已审覆盖点；空分母输出pending而非100%，计数与预期一致。真实三科100%归M-CONTENT。
- [R05] 工具对固定抽检报告验证抽检数不少于min(批量数,max(50,ceil(批量数×10%)))、抽检人与作者/审校者不同、严重错误为0且一般错误率≤2%；缺报告或不达标拒绝发布标记。真实抽检由M-CONTENT执行。
- [R21] 每个包的 `LICENSES.yaml` 列出全部来源与许可；`validate` 对缺许可、缺来源或含禁用许可的条目报错。
- [R30] 工具夹具产物保留教育阶段、教材版本与考试范围标签，roundtrip后字段不变；应用内检索归CORE-38、双端加载归AND-12/WIN-13，真实发布内容归M-CONTENT。
- [R19] 工具单元测试：故意错误的样例条目（量纲错误、重复、缺审校人、author = reviewer）全部被拒。
- [R04][R04.f][R04.g] 条目的 `exam_scope`、`requirement_level`、`derivation_ref` 与 `confusable_group_id` 经 `validate` 校验（引用不存在的派生条目或易混组报 `CONTENT_FIELD_INVALID`）；按数一、数二、数三筛选出卡的条目集合与覆盖率报告一致。

- [R04.c] validate拒绝用于辨识题的条目缺distractors、error_type、review.reviewer，或author=reviewer，输出CONTENT_REVIEW_INVALID/CONTENT_FIELD_MISSING；人工双人审校流程由内容负责人执行，审校记录随包发行。
