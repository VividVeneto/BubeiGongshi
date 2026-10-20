# CORE-01 测试方案

> 来源卡：[S0_CORE-01_基座.md](../../S0/S0_CORE-01_基座.md)（仓库骨架与工程约定）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R18][R23] 干净检出后 仅对本卡仓库骨架运行`cargo build --workspace`和`flutter analyze`成功；平台构建由AND-01/WIN-01验收，依赖检查脚本由CORE-69验收，不是本卡交付前置。
- [R18] 锁定文件齐全：上述 4 个文件存在、内容可解析且各含查询日期与版本；ADR-V5-15 已回填。CI 只读取这些文件版本的集成断言由 CORE-41 验收，不是本卡交付前置。
- [R20] `cargo doc --workspace` 无 missing_docs 告警；`dart analyze` 无 `public_member_api_docs` 告警。
- [R22] 核对main的 `Cargo.toml`、`pubspec.yaml`、`crates/`无YOLO实现、权重或依赖；CORE-42后续发布检查安装产物，脚本实现不计本卡。
