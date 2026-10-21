# CORE-79 测试方案

> 来源卡：[S3_CORE-79_功能.md](../../core/S3_CORE-79_功能.md)（公式检索、差异与导入）。本文件是该卡验收标准全文；修改范围时同步修改，工具从下方验收标准行起拼回。

**验收标准**
- [R11] T-LIB：用 `tools/perf` 生成的 10000 条公式、50000 张卡测试库，`library.search` 首屏（`page_size = 50`）满足 CORE-01 全局资源预算表“公式库搜索首屏（10000 条）”行；测量方法：同一查询集 100 次取 P95。
- [R11] 修订差异：对CORE-14持久化的两修订，源码unified diff与AST节点Added/Removed/Changed路径正确，不修改历史；不依赖第三方diff crate。
- [R04][R04.j] LaTeX/CSV 导入逐行给出校验报告，失败行不入库：10 行 CSV（含 2 行 LaTeX 语法错、1 行量纲冲突）→ `accepted = 7`，`rejected` 行号为对应行；5001 行 CSV 返回 `LIB_IMPORT_TOO_LARGE`。
- [R11] `library.substitution_pool` 对给定槽位返回的候选不含回收站条目与草稿修订。
- [R11] 元数据更新后搜索标签立即命中，不生成修订；trashed=true只返回回收站条目。
- [R11] 中文子串：条目“动能定理/机械能守恒”分别用“动能”“能定”“机械能”“能守恒”命中；单字“能”匹配两条；查询“%”只匹配字面百分号，英文大小写一致，组合筛选与分页顺序稳定。
- [R11] 大小写折叠边界：LIKE 路径只折叠 ASCII（SQLite 内置规则），trigram 路径按其 Unicode 折叠；向量固定：“Ab”命中“ab”；“É”不命中“é”（1～2 个标量走 LIKE，只折叠 ASCII）；“Énergie”命中“énergie”（≥3 个标量走 trigram，按 Unicode 折叠）；写入 `tests/fixtures/library/search.yaml`。
- [R11][R14] 使用Fake RevisionAnalyzer验证导入行号/诊断；fml-ffi薄适配复用CORE-56分析，snapshot失败、unavailable、expected_generation不符均不运行算法；同步重解析可复用同一实现，fml-store不依赖fml-ffi。
