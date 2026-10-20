# WIN-12 测试方案

> 来源卡：[S7_WIN-12_发布.md](../../win/S7_WIN-12_发布.md)（代码签名与发布检查）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R01] `verify_signatures.ps1` 对构建输出与安装器全部通过；把一个未签名 DLL 放入目录后退出 1。
- [R03] 安装器超过 70 MB 时 `check_artifacts.py` 退出 1；含 `.pdb` 时退出 1。
- [R23] 发布目录含 `dist\symbols\<v>\` 与其 SHA256SUMS、`dist\windows\update.json`；`update.json` 的 sha256 与安装器一致，且被 WIN-03 `check()` 正确解析。
- [R40] 在构建输出中放入含测试 API Key 字符串的文件，`check_artifacts.py` 退出 1。
- [R23] 未设置签名变量且未给 `-Unsigned` 时 `build_release.ps1` 退出 2 并说明缺少的变量。
