# CORE-19 测试方案

> 来源卡：[S4_CORE-19_功能.md](../../core/S4_CORE-19_功能.md)（学习会话与组学习循环）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R04][R04.a][R04.b][R04.d][R04.e] T-SESSION：默认组 10 条、K = 3 与 K = 1、5 通过，K = 0、6 返回 `STUDY_K_OUT_OF_RANGE`；复习卡 K = 1；答错插回本组靠后第 3 位；组后默写全部或只默写错题；默写错误进入次日错题复习；跳过、暂停、关闭题型；23 h 59 min 续学成功、24 h 01 min 返回 `STUDY_SESSION_EXPIRED`；同一组在两台设备完成后结果一致。
- [R04][R04.j] 自建公式书：创建含 3 章、20 个条目引用的用户书并按其定计划出卡；删除书不删除条目。
- [R04] 评分映射单元测试覆盖表中每一行，含“判对少于 10 次不判 Easy”。
- [R04][R04.h] 申诉生成纠正事件（`correction_of` 指向原事件）、原事件保留，排程按纠正后重算。
- [R04] 边界 op：Undetermined 作答返回 `NeedSelfRate` 且未写 Attempt；`SelfRated` 后写入一条 `self_knew` 有值的 Attempt；`QuestionView` 序列化结果不含标准答案；对内容包书调用 `study.books.delete` 返回 `STUDY_BOOK_READ_ONLY`。
- [R04] 端到端（集成测试，Fake 端口）：选书 → 定计划 → 组学习 → 组后默写 → 次日复习全流程离线可完成。

- [R04.c] 固定QuestionSource+seed连跑两次options完全相同，所有非正确项均能回溯已审校Distractor及error_type；少于所需项改输入题，未审校源拒绝出题。
