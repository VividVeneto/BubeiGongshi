# CORE-52 测试方案

> 来源卡：[S3_CORE-52_引擎.md](../../core/S3_CORE-52_引擎.md)（公式复制格式与富格式导出）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R08] 语料全部可解析公式导出的 MathML 能被 `roxmltree` 解析，元素只属于 MathML Core；`a\cdot b`、`a\times b`、`ab` 分别得到 ·、×、`&#x2062;`；`\frac{a}{b}` 与 `a/b` 分别得到 `mfrac` 与 `<mo>/</mo>`；附带的 annotation 等于原 LaTeX。
- [R08] SVG 只含允许的元素；`<path>` 数等于 DisplayList 中 Glyph 与 Path 命令数之和，`<rect>` 数等于 Rule 数；`<title>` 为 LaTeX 原文。
- [R08] 单元测试（登记假写入器）：五种选择得到的负载字段与“格式组合”表逐格一致；含 `\fmlhole` 时“自动”只含 text 与 latex，`formatsFor` 只含 auto 与 latex；未登记写入器时调用 `clipboard.writeText`。
- [R10] 源码中的 `<`、`&`、`"` 在 MathML、SVG 与 HTML 中均被转义；HTML 与 SVG 输出中不出现 `<script`、`on*=` 属性与 `http:`/`https:` 链接。
- [R20] 复制后检查日志目录，不含公式源码与导出内容。
- [R03] 性能：按CORE-01预算表“公式复制”行，由AND-12/WIN-13在S7真机测量；本卡Fake只验证负载与时序，不计真机完成条件。

- [R08][R19] 相同源码/方案但不同声明、格式或同ID新字体不能命中旧导出；一次复制的display/SVG/PNG代数一致，更新竞态按CORE-73重试，第二次竞态返回可重试错误且剪贴板未写旧图片。
