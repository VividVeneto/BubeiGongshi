# CORE-44 测试方案

> 来源卡：[S7_CORE-44_发布.md](../../core/S7_CORE-44_发布.md)（鸿蒙预留与 C 头文件消费者验证）。本文件是该卡“验收标准”字段的全文，按卡片编程时直接引用；修改卡片功能时同步修改本文件，卡片因阶段变化改名时本文件同步改名（`S编号_卡号_TEST.md`）。工具按卡片中的引用把本文件自“**验收标准**”行起的内容原样拼回卡片，本行以上不拼回。

**验收标准**
- [R02] CI 的 ohos-smoke 作业中 `build.sh --target ohos` 成功，`libfmlcore.so` 导出 `fmlcore.h` 声明的全部函数；人为引入一个只支持 Windows 的依赖后作业失败并阻止合并；片段以变更单交接（本卡不改 ci.yml），作业只出现一次、needs 只引用 lint/test、步骤含 toolchain.py 前置；重复 job 键或悬空 needs 的片段被 CORE-41 拒绝合入（合入校验归 CORE-41，人工 checklist 记录）。
- [R02] `build.sh --target host` 运行 `consumer.c` 五个步骤全部通过并打印OK，固定非零32hex请求在成功响应回显；未知op的外层/内层错误trace均与请求一致；全零trace被拒且返回非零一致fallback，不能只检查错误码而漏trace；受限字段提取器分别定位外层/error.trace_id并校验32小写hex/非零/相等，对缺失、重复、缓冲越界的合成响应必须拒绝；AddressSanitizer不报告泄漏或越界。
- [R02] 删除 `OHOS_NDK_HOME` 后 `build.sh` 以退出码 2 结束并提示缺失的环境变量。
