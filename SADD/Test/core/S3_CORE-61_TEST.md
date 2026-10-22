# CORE-61 测试方案

> 来源卡：[S3_CORE-61_功能.md](../../core/S3_CORE-61_功能.md)（公式草稿仓储）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R08] 同键覆盖、缺键Rust返回None、FFI ok为{}（不是null，也不是{draft:null}）、删除幂等；中途失败事务回滚，重开库读取源码、声明、标题一致。
- [R08] source_latex恰65536 UTF-8字节put成功、65537字节返回LIB_DRAFT_INVALID且原草稿不变；draft_key为`item:`加大写UUID、`foo`、`new`带item_id、`item:<u>`的item_id不等于u时均返回LIB_DRAFT_INVALID；title与subject为空串可写入并原样读回。
- [R08] put/delete后sync_outbox无新增行；按CORE-13备份导出的内容不含formula_draft行；条目移入回收站后其草稿仍可get，draft_delete后消失。
- [R08] user_decls为空列表与含多个SymbolDecl时JSON往返相等；同key并发两次put，get得到后提交的那次。
- [R08] 已执行到0078的库按CORE-13乱序补执行规则执行0061_formula_draft.sql成功，且重复打开不再执行。
- [R08] 能力清单中draft_get为call、draft_put/draft_delete为submit，以call调用put返回FFI_UNKNOWN_OP；三op请求/响应示例经CORE-67生成的DTO解析与序列化后字节一致（schema提交后启用，此前记pending-target）。
