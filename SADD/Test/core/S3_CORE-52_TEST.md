# CORE-52 测试方案

> 来源卡：[S3_CORE-52_引擎.md](../../core/S3_CORE-52_引擎.md)（公式导出内核与剪贴板负载契约）。本文件是该卡“验收标准”字段的全文；修改功能时同步更新。工具自“**验收标准**”行起拼回卡片。

**验收标准**
- [R08] 语料全部可解析公式导出的 MathML 能被 `roxmltree` 解析，元素只属于 MathML Core；`a\cdot b`、`a\times b`、`ab` 分别得到 ·、×、`&#x2062;`；`\frac{a}{b}` 与 `a/b` 分别得到 `mfrac` 与 `<mo>/</mo>`；附带的 annotation 等于原 LaTeX。
- [R08] SVG 只含允许的元素；`<path>` 数等于 DisplayList 中 Glyph 与 Path 命令数之和，`<rect>` 数等于 Rule 数；`<title>` 为 LaTeX 原文。
- [R10] 源码中的<、&、双引号在MathML与SVG中均被转义；SVG输出无<script、on*=属性及http:/https:链接。
- [R08] export.formula单一格式失败仅进入omitted，其他格式保留；纯FormulaClipboardPayload/Writer可被平台假实现消费，不导入复制服务。
